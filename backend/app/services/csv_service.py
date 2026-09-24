from pathlib import Path
from datetime import datetime
import csv
import io
from sqlalchemy.orm import Session
from ..models import ProductionRecord, StationOutputSource, CsvColumnMapping
from ..core.config import settings

TIME_COLUMNS = ["Time", "time", "Timestamp", "timestamp", "DateTime", "datetime", "Date Time", "date_time"]
RESULT_COLUMNS = ["Result", "result", "FinalResult", "Final Result", "Inspection Result", "InspectionResult", "Judge", "Output", "Status", "PassFail"]
CRACK_COLUMNS = ["Crack", "crack", "Crack Result", "CrackResult", "CrackResult", "Defect", "DefectCode"]


def normalize_header(value: str) -> str:
    return "".join(ch.lower() for ch in (value or "").strip() if ch.isalnum())


def find_column(fieldnames, candidates):
    if not fieldnames:
        return None
    normalized = {normalize_header(x): x for x in fieldnames if x is not None}
    for candidate in candidates:
        key = normalize_header(candidate)
        if key in normalized:
            return normalized[key]
    return None


def first_nonempty(row):
    for value in row.values():
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def infer_ok_value(rows, output_column: str) -> str:
    values = []
    for row in rows[:100]:
        value = str(row.get(output_column, "")).strip()
        if value and value.upper() not in {"OK", "NG", "PASS", "FAIL", "PASSED", "FAILED"}:
            values.append(value)
    # Prefer conventional values when present.
    for preferred in ("OK", "PASS", "PASSED"):
        if any(str(row.get(output_column, "")).strip().upper() == preferred for row in rows[:100]):
            return preferred
    if values:
        # If only one unique value exists, use it as the OK value; otherwise default to OK.
        unique = list(dict.fromkeys(values))
        if len(unique) == 1:
            return unique[0]
    return "OK"


def recommend_mapping(fieldnames, sample_rows=None):
    sample_rows = sample_rows or []
    timestamp = find_column(fieldnames, TIME_COLUMNS)
    output = find_column(fieldnames, RESULT_COLUMNS)
    crack = find_column(fieldnames, CRACK_COLUMNS)
    if output is None and fieldnames:
        # Do not guess aggressively: choose a likely result-like header by keywords.
        for f in fieldnames:
            n = normalize_header(f)
            if any(token in n for token in ("result", "judge", "status", "passfail", "output")):
                output = f
                break
    if output is None and fieldnames:
        output = fieldnames[-1]
    ok_value = infer_ok_value(sample_rows, output) if output else "OK"
    return {
        "timestamp_column": timestamp or (fieldnames[0] if fieldnames else ""),
        "output_column": output or (fieldnames[0] if fieldnames else ""),
        "crack_column": crack or "",
        "ok_value": ok_value,
    }


def decode_bytes(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("Unsupported CSV encoding.")


def read_csv_header_file(csv_file: Path):
    decoded = decode_bytes(csv_file.read_bytes())
    reader = csv.DictReader(io.StringIO(decoded))
    if not reader.fieldnames:
        raise ValueError("CSV has no header.")
    rows = []
    for _, row in zip(range(10), reader):
        rows.append(dict(row))
    return list(reader.fieldnames), rows


def latest_csv_file(folder: str) -> Path | None:
    root = Path(folder)
    files = [p for p in root.rglob("*.csv") if p.is_file()]
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


def parse_timestamp(value: str):
    value = value.strip()
    for fmt in (
        "%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S.%f",
        "%Y/%m/%d %H:%M", "%Y-%m-%d %H:%M",
    ):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass
    return datetime.fromisoformat(value)


def get_mapping(db: Session, source_id: int | None = None):
    if source_id:
        return db.query(CsvColumnMapping).filter(CsvColumnMapping.source_id == source_id).first()
    source = db.query(StationOutputSource).order_by(StationOutputSource.id.desc()).first()
    return source.mapping if source else None


def _import_rows(db: Session, reader, source_name: str, mapping: CsvColumnMapping | dict | None, existing=None):
    imported = 0
    skipped = 0
    if existing is None:
        existing = {(r.source_file, r.source_row) for r in db.query(ProductionRecord.source_file, ProductionRecord.source_row).all()}

    for row_no, row in enumerate(reader, start=2):
        try:
            if mapping:
                tk = mapping.timestamp_column if hasattr(mapping, "timestamp_column") else mapping.get("timestamp_column", "")
                rk = mapping.output_column if hasattr(mapping, "output_column") else mapping.get("output_column", "")
                ck = mapping.crack_column if hasattr(mapping, "crack_column") else mapping.get("crack_column", "")
            else:
                tk = find_column(row.keys(), TIME_COLUMNS)
                rk = find_column(row.keys(), RESULT_COLUMNS)
                ck = find_column(row.keys(), CRACK_COLUMNS)

            if not tk or tk not in row or not str(row.get(tk, "")).strip():
                skipped += 1
                continue
            if not rk or rk not in row:
                skipped += 1
                continue

            key = (source_name, row_no)
            if key in existing:
                continue

            ts = parse_timestamp(str(row[tk]))
            rec = ProductionRecord(
                timestamp=ts,
                crack_result=str(row.get(ck, "")) if ck else "",
                final_result=str(row.get(rk, "")),
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


def refresh_csv(db: Session, folder: str | None = None, progress_callback=None, mapping=None):
    folder = folder or settings.csv_folder
    path = Path(folder)
    if not path.exists(): raise FileNotFoundError(f"CSV folder does not exist: {path}")
    if not path.is_dir(): raise NotADirectoryError(f"CSV path is not a folder: {path}")
    files = sorted([p for p in path.rglob("*.csv") if p.is_file()], key=lambda p: str(p).lower())
    if mapping is None: mapping = get_mapping(db)
    imported = skipped = 0
    failed_files = []
    existing = {(r.source_file, r.source_row) for r in db.query(ProductionRecord.source_file, ProductionRecord.source_row).all()}
    for file_index, csv_file in enumerate(files, start=1):
        if progress_callback: progress_callback(file_index - 1, len(files), csv_file.name)
        try:
            decoded = decode_bytes(csv_file.read_bytes())
            reader = csv.DictReader(io.StringIO(decoded))
            if not reader.fieldnames:
                skipped += 1; failed_files.append({"file": str(csv_file), "reason": "CSV has no header"}); continue
            active_mapping = mapping
            if active_mapping is None:
                active_mapping = recommend_mapping(reader.fieldnames)
            i, s = _import_rows(db, reader, str(csv_file), active_mapping, existing)
            imported += i; skipped += s
        except Exception as e:
            skipped += 1; failed_files.append({"file": str(csv_file), "reason": str(e)})
    if progress_callback: progress_callback(len(files), len(files), files[-1].name if files else None)
    return {"files": len(files), "imported": imported, "skipped": skipped, "failed_files": failed_files[:20], "recursive": True}


def import_uploaded_csv(db: Session, content: bytes, filename: str, mapping=None):
    decoded = decode_bytes(content)
    reader = csv.DictReader(io.StringIO(decoded))
    if not reader.fieldnames: raise ValueError("CSV has no header.")
    rows = list(reader)
    if mapping is None: mapping = recommend_mapping(reader.fieldnames, rows)
    timestamps = []
    tk = mapping["timestamp_column"] if isinstance(mapping, dict) else mapping.timestamp_column
    for row in rows:
        try: timestamps.append(parse_timestamp(str(row.get(tk, ""))))
        except Exception: pass
    imported, skipped = _import_rows(db, iter(rows), f"uploaded:{filename}", mapping)
    return {"filename": filename, "imported": imported, "skipped": skipped, "message": f"Imported {imported} new records from {filename}.", "min_timestamp": min(timestamps).isoformat() if timestamps else None, "max_timestamp": max(timestamps).isoformat() if timestamps else None}


def refresh_csv_dates(db: Session, folder: str, dates: list[str], mapping=None):
    root = Path(folder)
    if not root.exists(): raise FileNotFoundError(f"CSV folder does not exist: {root}")
    if not root.is_dir(): raise NotADirectoryError(f"CSV path is not a folder: {root}")
    files=[]; seen=set()
    for date_name in dates:
        date_dir=root/date_name
        if not date_dir.is_dir(): continue
        for p in date_dir.rglob("*.csv"):
            if p.is_file() and p not in seen: seen.add(p); files.append(p)
    files.sort(key=lambda p: str(p).lower())
    if mapping is None: mapping = get_mapping(db)
    imported=skipped=0; failed_files=[]
    existing={(r.source_file,r.source_row) for r in db.query(ProductionRecord.source_file,ProductionRecord.source_row).all()}
    for csv_file in files:
        try:
            decoded=decode_bytes(csv_file.read_bytes())
            reader=csv.DictReader(io.StringIO(decoded))
            if not reader.fieldnames:
                skipped+=1; failed_files.append({"file":str(csv_file),"reason":"CSV has no header"}); continue
            active_mapping=mapping or recommend_mapping(reader.fieldnames)
            i,s=_import_rows(db,reader,str(csv_file),active_mapping,existing)
            imported+=i; skipped+=s
        except Exception as e:
            skipped+=1; failed_files.append({"file":str(csv_file),"reason":str(e)})
    return {"files":len(files),"imported":imported,"skipped":skipped,"failed_files":failed_files[:20],"dates_scanned":dates,"live":True}
