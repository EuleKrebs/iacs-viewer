from flask import Blueprint, jsonify, render_template, flash, request, redirect, url_for
import requests
from iacs_viewer.models.resources import Resources
from iacs_viewer.models.fields import Fields
from iacs_viewer.database import db
from zipfile import ZipFile
import tempfile
from pyarrow.parquet import ParquetFile
from shapely import wkb
import sys

bp = Blueprint('populate', __name__)

@bp.route('/list_resources', methods=['GET'])
def list_resources():
    resources = Resources.query.all()
    result = [
        {"name": resource.name, "url": resource.url}
        for resource in resources
    ]
    return jsonify(result)

@bp.route('/update_resource', methods=['POST'])
def update_resource():
    # Expecting JSON: { "resource_names": ["file1.tif", "file2.tif"] }
    url = "https://zenodo.org/api/records/15692199"
    response = requests.get(url)
    data = response.json()
    added = []
    
    # Update Table
    if 'files' in data:
        resources = Resources.query.all()
        for file in data['files']:
            existing = Resources.query.filter_by(name=file['key']).first()
            if existing:
                # Update the URL if resource exists
                existing.url = file['links']['self']
                added.append(file['key'] + " (updated)")
            else:
                resource = Resources(name=file['key'], url=file['links']['self'])
                db.session.add(resource)
                added.append(file['key'] + " (added)")
        
        db.session.commit()
        #message = "Resources successfully imported"
        #return redirect(f"/populate/popout_message/{quote(message)}")
        popout = "Success"
        return render_template("index.html", popout=popout, resources=resources)
    else:
        popout = "No files found in the response."
        return render_template("index.html", popout=popout, resources=resources)

@bp.route('/download_resource', methods=['POST'])
def download_resource():
    resource_id = request.form.get('map_dwnld')
    
    if not resource_id:
        flash("No resource selected.")
        return redirect(url_for('main.index'))

    resource = Resources.query.get(resource_id)    
    if not resource:
        flash("Resource not found.")
        return redirect(url_for('main.index'))

    # Download the zip file
    response = requests.get(resource.url, stream=True, timeout=180)
    if response.status_code == 200:
        # Progress bar
        total = int(response.headers.get("Content-Length", 0))  # 0 if unknown
        downloaded = 0

        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmpfile:
            # herunterladen der zip Files in eine temp dir
            response.raise_for_status()
            for chunk in response.iter_content(chunk_size=8192):
                if not chunk:
                    continue
                tmpfile.write(chunk)
                downloaded += len(chunk)
                # Progress output
                if total:
                    pct = downloaded * 100 / total
                    sys.stdout.write(
                        f"\rDownloading: {pct:6.2f}% ({downloaded:,}/{total:,} bytes)"
                    )
                else:
                    sys.stdout.write(f"\rDownloading: {downloaded:,} bytes")
                sys.stdout.flush()
            temp_zip_path = tmpfile.name
            # Einlesen der einzelnen parquet files
            with ZipFile(temp_zip_path) as zip:
                filelist = zip.namelist()
                parquet_file = ParquetFile(zip.open(filelist))
                # load parquet into dp in batches
                for batch in parquet_file.iter_batches(batch_size=1000):
                    tab = batch.to_table()
                    df = tab.to_pandas()
                    df['geometry'] = df['geometry'].apply(wkb.loads)
                    # Insert data into db
                    for _, row in df.iterrows():
                        geom = row.get("geometry")
                        geom_wkt = geom.wkt if geom else None
                        field = Fields(
                            id=row.get('id'),
                            field_id=row.get('field_id'),
                            farm_id=row.get('farm_id'),
                            crop_code=row.get('crop_code'),
                            crop_name=row.get('crop_name'),
                            EC_trans_n=row.get('EC_trans_n'),
                            EC_hcat_n=row.get('EC_hcat_n'),
                            EC_hcat_c=row.get('EC_hcat_c'),
                            organic=row.get('organic'),
                            field_size=row.get('field_size'),
                            crop_area=row.get('crop_area'),
                            nation=row.get('nation'),
                            year=row.get('year'),
                            geometry=geom_wkt
                        )
                        db.session.add(field)
        sys.stdout.write("\n")
        # Here you would process the zip file as needed.
        # For demo, let's just add an entry to Fields table.
        field = Fields(name=resource.name, data=response.content)
        db.session.add(field)
        db.session.commit()
        flash(f"Downloaded and added {resource.name} to fields.")
    else:
        flash("Failed to download the resource.")

    return redirect(url_for('main.index'))