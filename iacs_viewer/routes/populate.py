"""
Data catalog & download manager.
Fetches available IACS datasets from Zenodo and downloads them in the background.
Supports partial extraction retry for failed files.
"""
import os
import time
import threading
from zipfile import ZipFile, BadZipFile
from flask import Blueprint, jsonify, request, current_app, Response
import requests
import json

bp = Blueprint('populate', __name__)

ZENODO_RECORD_URL = "https://zenodo.org/api/records/15692199"
SPATIAL_EXTENSIONS = ('.geoparquet', '.parquet', '.gpkg', '.geojson')

_downloads = {}
_downloads_lock = threading.Lock()


def _get_data_dir():
    return current_app.config.get('DATA_DIR',
        os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'data'))


def _list_local_files(data_dir):
    local = set()
    for root, _dirs, files in os.walk(data_dir):
        for f in files:
            local.add(f)
    return local


def _get_zip_spatial_members(zip_path):
    """List spatial file members inside a zip. Returns list of member names."""
    try:
        with ZipFile(zip_path) as zf:
            return [m for m in zf.namelist() if m.endswith(SPATIAL_EXTENSIONS)]
    except (BadZipFile, Exception):
        return []


@bp.route('/catalog', methods=['GET'])
def catalog():
    try:
        resp = requests.get(ZENODO_RECORD_URL, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return jsonify({"error": f"Failed to reach Zenodo: {str(e)}"}), 502

    data_dir = _get_data_dir()
    local_files = _list_local_files(data_dir)

    files = []
    for f in data.get('files', []):
        name = f['key']
        size_bytes = f['size']

        status = 'available'
        progress = 0
        extracted_files = []
        failed_files = []

        # Check active downloads first
        with _downloads_lock:
            if name in _downloads and _downloads[name]['status'] in ('downloading', 'extracting'):
                status = _downloads[name]['status']
                progress = _downloads[name].get('progress', 0)
                files.append({
                    'name': name, 'size_bytes': size_bytes,
                    'size_mb': round(size_bytes / 1024 / 1024, 1),
                    'url': f['links']['self'],
                    'checksum': f.get('checksum', ''),
                    'status': status, 'progress': progress,
                    'extracted_files': [], 'failed_files': [],
                })
                continue

        # Check zip on disk
        zip_path = os.path.join(data_dir, name)
        if name in local_files and name.endswith('.zip') and os.path.exists(zip_path):
            members = _get_zip_spatial_members(zip_path)
            if members:
                for m in members:
                    bn = os.path.basename(m)
                    if bn in local_files:
                        extracted_files.append(bn)
                    else:
                        failed_files.append(bn)

                if len(extracted_files) == len(members):
                    status = 'extracted'
                    progress = 100
                elif len(extracted_files) > 0:
                    status = 'partial'
                    progress = round(len(extracted_files) / len(members) * 100)
                else:
                    status = 'downloaded'
                    progress = 100
            else:
                status = 'downloaded'
                progress = 100

        # Check download history for errors
        with _downloads_lock:
            if name in _downloads:
                dl = _downloads[name]
                if dl['status'] == 'error' and status == 'available':
                    status = 'error'
                elif dl['status'] == 'extracted' and status != 'extracted':
                    # Re-check: download said extracted but files may be there now
                    pass
                if dl.get('failed_files'):
                    failed_files = list(set(failed_files) | set(dl['failed_files']))

        files.append({
            'name': name,
            'size_bytes': size_bytes,
            'size_mb': round(size_bytes / 1024 / 1024, 1),
            'url': f['links']['self'],
            'checksum': f.get('checksum', ''),
            'status': status,
            'progress': progress,
            'extracted_files': extracted_files,
            'failed_files': failed_files,
        })

    files.sort(key=lambda x: x['name'])
    return jsonify({
        'record_id': data.get('id'),
        'title': data.get('metadata', {}).get('title', 'IACS Dataset'),
        'files': files,
        'total_size_gb': round(sum(f['size_bytes'] for f in files) / 1024 ** 3, 1),
    })


@bp.route('/download', methods=['POST'])
def start_download():
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
            'status': 'downloading', 'progress': 0,
            'downloaded_bytes': 0, 'total_bytes': 0, 'speed_bps': 0,
            'error': None, 'started_at': time.time(),
            'extracted_files': [], 'failed_files': [],
        }

    threading.Thread(target=_download_worker, args=(name, url, data_dir), daemon=True).start()
    return jsonify({"status": "started", "name": name})


@bp.route('/extract', methods=['POST'])
def extract_zip():
    """Extract a zip. Optionally pass 'files' array to extract only specific members."""
    body = request.get_json()
    if not body or 'name' not in body:
        return jsonify({"error": "Missing 'name'"}), 400

    name = body['name']
    only_files = body.get('files')  # optional: list of specific filenames to re-extract
    data_dir = _get_data_dir()
    zip_path = os.path.join(data_dir, name)

    if not os.path.exists(zip_path):
        return jsonify({"error": "Zip file not found"}), 404

    with _downloads_lock:
        _downloads[name] = {
            'status': 'extracting', 'progress': 100,
            'downloaded_bytes': os.path.getsize(zip_path),
            'total_bytes': os.path.getsize(zip_path),
            'speed_bps': 0, 'error': None, 'started_at': time.time(),
            'extracted_files': [], 'failed_files': [],
        }

    threading.Thread(
        target=_extract_worker, args=(name, zip_path, data_dir, only_files), daemon=True
    ).start()
    return jsonify({"status": "extracting", "name": name})


@bp.route('/download/<name>/cancel', methods=['POST'])
def cancel_download(name):
    with _downloads_lock:
        if name in _downloads and _downloads[name]['status'] == 'downloading':
            _downloads[name]['status'] = 'cancelled'
            return jsonify({"status": "cancelled"})
    return jsonify({"error": "No active download found"}), 404


@bp.route('/downloads/status', methods=['GET'])
def downloads_status():
    with _downloads_lock:
        return jsonify(dict(_downloads))


@bp.route('/downloads/events', methods=['GET'])
def download_events():
    def generate():
        while True:
            with _downloads_lock:
                data = json.dumps(_downloads)
            yield f"data: {data}\n\n"
            with _downloads_lock:
                active = any(d['status'] in ('downloading', 'extracting') for d in _downloads.values())
            if not active:
                time.sleep(0.5)
                with _downloads_lock:
                    data = json.dumps(_downloads)
                yield f"data: {data}\n\n"
                break
            time.sleep(1)
    return Response(generate(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


# ------------------------------------------------------------------
# Workers
# ------------------------------------------------------------------
def _download_worker(name, url, data_dir):
    try:
        resp = requests.get(url, stream=True, timeout=600)
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
                with _downloads_lock:
                    if _downloads[name]['status'] == 'cancelled':
                        break
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    now = time.time()
                    elapsed = now - last_time
                    speed = (downloaded - last_bytes) / elapsed if elapsed >= 1.0 else _downloads.get(name, {}).get('speed_bps', 0)
                    if elapsed >= 1.0:
                        last_time, last_bytes = now, downloaded
                    progress = (downloaded / total * 100) if total else 0
                    with _downloads_lock:
                        _downloads[name].update({
                            'progress': round(progress, 1),
                            'downloaded_bytes': downloaded,
                            'speed_bps': round(speed),
                        })

        with _downloads_lock:
            if _downloads[name]['status'] == 'cancelled':
                try: os.remove(zip_path)
                except OSError: pass
                return

        _extract_worker(name, zip_path, data_dir)

    except Exception as e:
        with _downloads_lock:
            _downloads[name]['status'] = 'error'
            _downloads[name]['error'] = str(e)


def _extract_worker(name, zip_path, data_dir, only_files=None):
    """
    Extract spatial files from zip with per-file error handling.
    only_files: if set, only extract these specific filenames (for retry).
    """
    extracted = []
    failed = []

    try:
        with _downloads_lock:
            _downloads[name]['status'] = 'extracting'

        if not name.endswith('.zip') or not os.path.exists(zip_path):
            with _downloads_lock:
                _downloads[name]['status'] = 'error'
                _downloads[name]['error'] = 'Not a valid zip file'
            return

        with ZipFile(zip_path, 'r') as zf:
            members = [m for m in zf.namelist() if m.endswith(SPATIAL_EXTENSIONS)]

            if only_files:
                # Filter to only requested files (match by basename)
                members = [m for m in members if os.path.basename(m) in only_files]

            for i, member in enumerate(members):
                basename = os.path.basename(member)
                target = os.path.join(data_dir, basename)
                try:
                    with zf.open(member) as src, open(target, 'wb') as dst:
                        while True:
                            chunk = src.read(1024 * 1024)
                            if not chunk:
                                break
                            dst.write(chunk)
                    extracted.append(basename)
                except Exception as e:
                    failed.append(basename)
                    # Clean up partial file
                    try: os.remove(target)
                    except OSError: pass

                # Update progress
                progress = round((i + 1) / len(members) * 100) if members else 100
                with _downloads_lock:
                    _downloads[name]['progress'] = progress
                    _downloads[name]['extracted_files'] = extracted[:]
                    _downloads[name]['failed_files'] = failed[:]

        with _downloads_lock:
            if failed:
                _downloads[name]['status'] = 'partial'
                _downloads[name]['error'] = f'{len(failed)} file(s) failed to extract'
            else:
                _downloads[name]['status'] = 'extracted'
            _downloads[name]['completed_at'] = time.time()
            _downloads[name]['extracted_files'] = extracted
            _downloads[name]['failed_files'] = failed

    except BadZipFile as e:
        with _downloads_lock:
            _downloads[name]['status'] = 'error'
            _downloads[name]['error'] = f'Corrupt zip file: {str(e)}'
    except Exception as e:
        with _downloads_lock:
            _downloads[name]['status'] = 'error'
            _downloads[name]['error'] = str(e)
            _downloads[name]['extracted_files'] = extracted
            _downloads[name]['failed_files'] = failed
