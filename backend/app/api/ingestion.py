from pathlib import Path
import threading
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from ..db import get_db, SessionLocal
from ..services.csv_service import refresh_csv, refresh_csv_dates, import_uploaded_csv
from ..models import StationOutputSource

router = APIRouter(prefix="/api", tags=["Ingestion"])


def folder_status(folder_path: str):
    path = Path(folder_path)
    if not path.exists():
        return {
            "connected": False,
            "folder": str(path),
            "files_found": 0,
            "date_folders_found": 0,
            "latest_file": None,
            "message": "Folder does not exist."
        }

    if not path.is_dir():
        return {
            "connected": False,
            "folder": str(path),
            "files_found": 0,
            "date_folders_found": 0,
            "latest_file": None,
            "message": "Path exists but is not a folder."
        }

    # Hikrobot raw data uses date folders such as 20260729.
    date_folders = [
        p for p in path.iterdir()
        if p.is_dir() and p.name.isdigit() and len(p.name) == 8
    ]

    # Count CSV files recursively, including inside date folders.
    files = sorted(
        [p for p in path.rglob("*.csv") if p.is_file()],
        key=lambda p: p.stat().st_mtime
    )
    latest = files[-1] if files else None

    return {
        "connected": True,
        "folder": str(path),
        "files_found": len(files),
        "date_folders_found": len(date_folders),
        "latest_file": str(latest.relative_to(path)) if latest else None,
        "message": (
            "Folder is accessible."
            if files
            else "Folder is accessible, but no CSV files were found in this folder or its subfolders."
        )
    }


_scan_jobs = {}
_scan_lock = threading.Lock()

def _run_scan_job(job_id: str, folder_path: str):
    db = SessionLocal()
    try:
        with _scan_lock:
            _scan_jobs[job_id] = {"status": "running", "current": 0, "total": 0, "file": None, "imported": 0, "skipped": 0, "message": "Scanning CSV files..."}
        def progress(current, total, filename):
            _scan_jobs[job_id].update({"status": "running", "current": current, "total": total, "file": filename, "message": f"Importing {current}/{total}"})
        result = refresh_csv(db, folder=folder_path, progress_callback=progress)
        _scan_jobs[job_id].update({"status": "completed", "current": result["files"], "total": result["files"], "file": None, "imported": result["imported"], "skipped": result["skipped"], "files": result["files"], "message": f"Import complete: {result['imported']} new records from {result['files']} CSV files."})
    except Exception as e:
        _scan_jobs[job_id].update({"status": "error", "message": str(e)})
    finally:
        db.close()

@router.post("/scan-folder/start")
def start_scan_folder(folder_path: str, db: Session = Depends(get_db)):
    status = folder_status(folder_path)
    if not status["connected"]:
        raise HTTPException(400, status["message"])
    active = next(((job_id, j) for job_id, j in _scan_jobs.items() if j.get("status") in ("queued", "running")), None)
    if active:
        active_id, active_job = active
        return {"job_id": active_id, **active_job}
    job_id = str(uuid.uuid4())
    _scan_jobs[job_id] = {"status": "queued", "current": 0, "total": status["files_found"], "file": None, "imported": 0, "skipped": 0, "message": "Scan queued..."}
    threading.Thread(target=_run_scan_job, args=(job_id, folder_path), daemon=True).start()
    return {"job_id": job_id, **_scan_jobs[job_id]}

@router.get("/scan-folder/status/{job_id}")
def scan_folder_status(job_id: str):
    job = _scan_jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Scan job not found.")
    return {"job_id": job_id, **job}


@router.post("/test-folder")
def test_folder(folder_path: str):
    return folder_status(folder_path)


@router.post("/scan-folder")
def scan_folder(folder_path: str, db: Session = Depends(get_db)):
    status = folder_status(folder_path)
    if not status["connected"]:
        raise HTTPException(400, status["message"])
    result = refresh_csv(db, folder=folder_path)
    return {**status, **result}


@router.post("/refresh")
def refresh(db: Session = Depends(get_db)):
    try:
        # The database source is the production configuration of record.
        source = db.query(StationOutputSource).order_by(StationOutputSource.id.desc()).first()
        if source and source.csv_folder_path:
            result = refresh_csv(db, folder=source.csv_folder_path)
            return {"folder": source.csv_folder_path, **result}
        return refresh_csv(db)
    except FileNotFoundError as e:
        raise HTTPException(400, str(e))


@router.post("/import-csv")
async def import_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Please select a CSV file.")
    try:
        content = await file.read()
        return import_uploaded_csv(db, content, file.filename)
    except Exception as e:
        raise HTTPException(400, f"CSV import failed: {e}")


@router.post("/refresh-live")
def refresh_live(date_: str, db: Session = Depends(get_db)):
    """
    Near-real-time refresh. Scans only the selected Hikrobot date folder
    and the following calendar date (needed for overnight shifts).
    """
    from datetime import datetime, timedelta

    try:
        selected = datetime.strptime(date_, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(422, "date_ must use YYYY-MM-DD format.")

    dates = [
        selected.strftime("%Y%m%d"),
        (selected + timedelta(days=1)).strftime("%Y%m%d"),
    ]

    source = db.query(StationOutputSource).order_by(StationOutputSource.id.desc()).first()
    if not source or not source.csv_folder_path:
        raise HTTPException(400, "No CSV source folder has been configured.")

    try:
        result = refresh_csv_dates(db, source.csv_folder_path, dates)
        return {"folder": source.csv_folder_path, **result}
    except (FileNotFoundError, NotADirectoryError) as e:
        raise HTTPException(400, str(e))
