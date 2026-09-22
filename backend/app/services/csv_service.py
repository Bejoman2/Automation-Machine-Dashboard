from pathlib import Path
from datetime import datetime
import csv
import io
from sqlalchemy.orm import Session
from ..models import ProductionRecord
from ..core.config import settings


TIME_COLUMNS = ["Time", "time", "Timestamp", "timestamp"]
CRACK_COLUMNS = ["Crack", "crack"]
RESULT_COLUMNS = ["Result", "result"]


def first_key(row, candidates):
    for key in candidates:
        if key in row:
            return key
    return None


def parse_timestamp(value: str):
    value = value.strip()
    for fmt in (
        "%Y/%m/%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S.%f",
    ):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass
    return datetime.fromisoformat(value)


def _import_rows(db: Session, reader, source_name: str, existing=None):
    imported = 0
    skipped = 0

    if existing is None:
        existing = {
            (r.source_file, r.source_row)
            for r in db.query(ProductionRecord.source_file, ProductionRecord.source_row).all()
        }

    for row_no, row in enumerate(reader, start=2):
        try:
            tk = first_key(row, TIME_COLUMNS)
            ck = first_key(row, CRACK_COLUMNS)
            rk = first_key(row, RESULT_COLUMNS)

            if not tk:
                skipped += 1
                continue

            key = (source_name, row_no)
            if key in existing:
                continue

            ts = parse_timestamp(str(row[tk]))

            rec = ProductionRecord(
                timestamp=ts,
                crack_result=str(row.get(ck, "")) if ck else "",
                final_result=str(row.get(rk, "")) if rk else "",
                source_file=source_name,
                source_row=row_no,
            )

            db.add(rec)
            imported += 1
            existing.add(key)

        except Exception:
            skipped += 1

    db.commit()
    return imported, skipped


def refresh_csv(db: Session, folder: str | None = None, progress_callback=None):
    """
    Scan the configured Hikrobot root folder recursively.

    Hikrobot stores raw CSV files in date-named subfolders, e.g.:
        00. All Raw data/
            20260729/*.csv
            20260730/*.csv
            20260731/*.csv

    We therefore use rglob("*.csv") instead of glob("*.csv").
    """
    folder = folder or settings.csv_folder
    path = Path(folder)

    if not path.exists():
        raise FileNotFoundError(f"CSV folder does not exist: {path}")
    if not path.is_dir():
        raise NotADirectoryError(f"CSV path is not a folder: {path}")

    # Recursive scan: include CSVs inside date folders and any deeper folders.
    files = sorted(
        [p for p in path.rglob("*.csv") if p.is_file()],
        key=lambda p: str(p).lower()
    )

    imported = 0
    skipped = 0
    failed_files = []
    existing = {(r.source_file, r.source_row) for r in db.query(ProductionRecord.source_file, ProductionRecord.source_row).all()}

    for file_index, csv_file in enumerate(files, start=1):
        if progress_callback:
            progress_callback(file_index - 1, len(files), csv_file.name)
        try:
            # Hikrobot files may be UTF-8 or Windows encoded.
            decoded = None
            for encoding in ("utf-8-sig", "utf-8", "cp1252"):
                try:
                    decoded = csv_file.read_text(encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue

            if decoded is None:
                skipped += 1
                failed_files.append({
                    "file": str(csv_file),
                    "reason": "Unsupported CSV encoding"
                })
                continue

            reader = csv.DictReader(io.StringIO(decoded))
            if not reader.fieldnames:
                skipped += 1
                failed_files.append({
                    "file": str(csv_file),
                    "reason": "CSV has no header"
                })
                continue

            i, s = _import_rows(db, reader, str(csv_file), existing)
            imported += i
            skipped += s

        except Exception as e:
            skipped += 1
            failed_files.append({
                "file": str(csv_file),
                "reason": str(e)
            })

    if progress_callback:
        progress_callback(len(files), len(files), files[-1].name if files else None)

    return {
        "files": len(files),
        "imported": imported,
        "skipped": skipped,
        "failed_files": failed_files[:20],
        "recursive": True,
    }


def import_uploaded_csv(db: Session, content: bytes, filename: str):
    """
    Import a CSV selected from the browser's Windows File Explorer.

    The file itself is sent to FastAPI using multipart/form-data.
    It is not necessary to copy the CSV into backend/data.
    """
    decoded = None

    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            decoded = content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue

    if decoded is None:
        raise ValueError("Unsupported CSV encoding.")

    reader = csv.DictReader(io.StringIO(decoded))

    if not reader.fieldnames:
        raise ValueError("CSV has no header.")

    missing_time = not first_key({k: None for k in reader.fieldnames}, TIME_COLUMNS)
    if missing_time:
        raise ValueError(
            "CSV must contain a Time/Timestamp column."
        )

    source_name = f"uploaded:{filename}"
    # Materialize rows once so we can report the data range to the UI.
    rows = list(reader)
    timestamps = []
    for row in rows:
        tk = first_key(row, TIME_COLUMNS)
        if tk:
            try:
                timestamps.append(parse_timestamp(str(row[tk])))
            except Exception:
                pass

    imported, skipped = _import_rows(
        db,
        iter(rows),
        source_name,
    )

    return {
        "filename": filename,
        "imported": imported,
        "skipped": skipped,
        "message": f"Imported {imported} new records from {filename}.",
        "min_timestamp": min(timestamps).isoformat() if timestamps else None,
        "max_timestamp": max(timestamps).isoformat() if timestamps else None,
    }


def refresh_csv_dates(db: Session, folder: str, dates: list[str]):
    """
    Incremental/near-real-time scan for Hikrobot's YYYYMMDD date folders.

    Only the requested date folders are scanned, avoiding a full historical
    recursive scan on every dashboard refresh.
    """
    root = Path(folder)
    if not root.exists():
        raise FileNotFoundError(f"CSV folder does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"CSV path is not a folder: {root}")

    files = []
    seen = set()
    for date_name in dates:
        if not date_name:
            continue
        date_dir = root / date_name
        if not date_dir.is_dir():
            continue
        for p in date_dir.rglob("*.csv"):
            if p.is_file() and p not in seen:
                seen.add(p)
                files.append(p)

    files.sort(key=lambda p: str(p).lower())

    imported = 0
    skipped = 0
    failed_files = []
    existing = {(r.source_file, r.source_row) for r in db.query(ProductionRecord.source_file, ProductionRecord.source_row).all()}

    for file_index, csv_file in enumerate(files, start=1):
        try:
            decoded = None
            for encoding in ("utf-8-sig", "utf-8", "cp1252"):
                try:
                    decoded = csv_file.read_text(encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue

            if decoded is None:
                skipped += 1
                failed_files.append({"file": str(csv_file), "reason": "Unsupported CSV encoding"})
                continue

            reader = csv.DictReader(io.StringIO(decoded))
            if not reader.fieldnames:
                skipped += 1
                failed_files.append({"file": str(csv_file), "reason": "CSV has no header"})
                continue

            i, s = _import_rows(db, reader, str(csv_file), existing)
            imported += i
            skipped += s
            db.commit()

        except Exception as e:
            skipped += 1
            failed_files.append({"file": str(csv_file), "reason": str(e)})

    return {
        "files": len(files),
        "imported": imported,
        "skipped": skipped,
        "failed_files": failed_files[:20],
        "dates_scanned": dates,
        "live": True,
    }
