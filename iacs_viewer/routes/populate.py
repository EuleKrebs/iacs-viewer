"""
Data catalog & download manager.
Fetches available IACS datasets from Zenodo and downloads them in the background.
"""
import os
import sys
import time
import threading
import tempfile
from zipfile import ZipFile
from flask import Blueprint, jsonify, request, current_app, Response
import requests
import json
import glob

bp = Blueprint('populate', __name__)

ZENODO_RECORD_URL = "https://zenodo.org/api/records/15692199"

# In-memory download state (per-process)
_downloads = {}
_downloads_lock = threading.Lock()


def _get_data_dir():
    return current_app.config.get('DATA_DIR',
        os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'data'))


@bp.route('/catalog', methods=['GET'])
def catalog():
    """Fetch available datasets from Zenodo and return enriched list."""
    try:
        resp = requests.get(ZENODO_RECORD_URL, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return jsonify({"error": f"Failed to reach Zenodo: {str(e)}"}), 502

    data_dir = _get_data_dir()
    # Check what's already downloaded
    local_files = set()
    for ext in ('*.gpkg', '*.parquet', '*.zip'):
        for p in glob.glob(os.path.join(data_dir, '**', ext), recursive=True):
            local_files.add(os.path.basename(p))

    files = []
    for f in data.get('files', []):
        name = f['key']
        size_bytes = f['size']

        # Check download status
        status = 'available'
        progress = 0
        with _downloads_lock:
            if name in _downloads:
                status = _downloads[name]['status']
                progress = _downloads[name].get('progress', 0)

        # Check if already extracted (look for derived files)
        base = name.replace('.zip', '')
        extracted = any(lf.startswith(base) and not lf.endswith('.zip') for lf in local_files)
        if extracted:
            status = 'extracted'
            progress = 100
        elif name in local_files:
            status = 'downloaded'
            progress = 100

        files.append({
            'name': name,
            'size_bytes': size_bytes,
            'size_mb': round(size_bytes / 1024 / 1024, 1),
            'url': f['links']['self'],
            'checksum': f.get('checksum', ''),
            'status': status,
            'progress': progress,
        })

    # Sort by name
    files.sort(key=lambda x: x['name'])

    return jsonify({
        'record_id': data.get('id'),
        'title': data.get('metadata', {}).get('title', 'IACS Dataset'),
        'files': files,
        'total_size_gb': round(sum(f['size_bytes'] for f in files) / 1024**3, 1),
    })


@bp.route('/download', methods=['POST'])
def start_download():
    """Start a background download for a dataset file."""
    body = request.get_json()
    if not body or 'name' not in body or 'url' not in body:
        return jsonify({"error": "Missing 'name' and 'url'"}), 400

    name = body['name']
    url = body['url']

    with _downloads_lock:
        if name in _downloads and _downloads[name]['status'] in ('downloading', 'extracting'):
            return jsonify({"error": "Download already in progress"}), 409

    data_dir = _get_data_dir()
    os.makedirs(data_dir, exist_ok=True)

    with _downloads_lock:
        _downloads[name] = {
            'status': 'downloading',
            'progress': 0,
            'downloaded_bytes': 0,
            'total_bytes': 0,
            'speed_bps': 0,
            'error': None,
            'started_at': time.time(),
        }

    # Start background thread
    thread = threading.Thread(
        target=_download_worker,
        args=(name, url, data_dir),
        daemon=True
    )
    thread.start()

    return jsonify({"status": "started", "name": name})


@bp.route('/download/<name>/cancel', methods=['POST'])
def cancel_download(name):
    """Cancel an ongoing download."""
    with _downloads_lock:
        if name in _downloads and _downloads[name]['status'] == 'downloading':
            _downloads[name]['status'] = 'cancelled'
            return jsonify({"status": "cancelled"})
    return jsonify({"error": "No active download found"}), 404


@bp.route('/downloads/status', methods=['GET'])
def downloads_status():
    """Get status of all downloads."""
    with _downloads_lock:
        return jsonify(dict(_downloads))


@bp.route('/downloads/events', methods=['GET'])
def download_events():
    """Server-Sent Events stream for real-time download progress."""
    def generate():
        while True:
            with _downloads_lock:
                data = json.dumps(_downloads)
            yield f"data: {data}\n\n"
            # Check if any downloads are active
            with _downloads_lock:
                active = any(
                    d['status'] in ('downloading', 'extracting')
                    for d in _downloads.values()
                )
            if not active:
                # Send one final update then close
                time.sleep(0.5)
                with _downloads_lock:
                    data = json.dumps(_downloads)
                yield f"data: {data}\n\n"
                break
            time.sleep(1)

    return Response(generate(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


def _download_worker(name, url, data_dir):
    """Background worker to download and extract a dataset."""
    try:
        # Download
        resp = requests.get(url, stream=True, timeout=300)
        resp.raise_for_status()
        total = int(resp.headers.get('Content-Length', 0))

        with _downloads_lock:
            _downloads[name]['total_bytes'] = total

        zip_path = os.path.join(data_dir, name)
        downloaded = 0
        last_time = time.time()
        last_bytes = 0

        with open(zip_path, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=64 * 1024):
                # Check for cancellation
                with _downloads_lock:
                    if _downloads[name]['status'] == 'cancelled':
                        f.close()
                        os.remove(zip_path)
                        return

                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

                    # Calculate speed every second
                    now = time.time()
                    elapsed = now - last_time
                    if elapsed >= 1.0:
                        speed = (downloaded - last_bytes) / elapsed
                        last_time = now
                        last_bytes = downloaded
                    else:
                        speed = _downloads.get(name, {}).get('speed_bps', 0)

                    progress = (downloaded / total * 100) if total else 0

                    with _downloads_lock:
                        _downloads[name].update({
                            'progress': round(progress, 1),
                            'downloaded_bytes': downloaded,
                            'speed_bps': round(speed),
                        })

        # Extract zip
        with _downloads_lock:
            _downloads[name]['status'] = 'extracting'
            _downloads[name]['progress'] = 100

        if name.endswith('.zip'):
            extract_dir = os.path.join(data_dir)
            with ZipFile(zip_path, 'r') as zf:
                # Extract parquet/gpkg files
                for member in zf.namelist():
                    if member.endswith(('.parquet', '.gpkg', '.geojson')):
                        zf.extract(member, extract_dir)

            # Optionally remove zip to save space (keep it for now)
            # os.remove(zip_path)

        with _downloads_lock:
            _downloads[name]['status'] = 'extracted'
            _downloads[name]['progress'] = 100
            _downloads[name]['completed_at'] = time.time()

    except Exception as e:
        with _downloads_lock:
            _downloads[name]['status'] = 'error'
            _downloads[name]['error'] = str(e)
