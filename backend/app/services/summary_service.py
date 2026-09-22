from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_
from ..models import ProductionRecord, Target, Shift
from .shift_service import shift_window


def normalize_result(value):
    return (value or "").strip().upper()


def get_summary(db: Session, shift_id: int, selected_date: date):
    shift = db.get(Shift, shift_id)
    if not shift:
        return None
    start, end = shift_window(shift, selected_date)
    records = (
        db.query(ProductionRecord)
        .filter(and_(ProductionRecord.timestamp >= start, ProductionRecord.timestamp < end))
        .order_by(ProductionRecord.timestamp)
        .all()
    )

    total = len(records)
    ok = sum(1 for r in records if normalize_result(r.final_result) == "OK")
    ng = total - ok

    target = (
        db.query(Target)
        .filter(Target.shift_id == shift_id, Target.date == selected_date)
        .first()
    )
    target_qty = target.target_qty if target else None
    achievement = (ok / target_qty * 100) if target_qty else None

    buckets = []
    cursor = start
    while cursor < end:
        next_hour = cursor.replace(minute=0, second=0, microsecond=0)
        if next_hour < cursor:
            from datetime import timedelta
            next_hour += timedelta(hours=1)
        else:
            next_hour = cursor + __import__("datetime").timedelta(hours=1)

        bucket_records = [r for r in records if cursor <= r.timestamp < next_hour]
        btotal = len(bucket_records)
        bok = sum(1 for r in bucket_records if normalize_result(r.final_result) == "OK")
        buckets.append({
            "hour": cursor.strftime("%H:%M"),
            "start": cursor.isoformat(),
            "ok": bok,
            "ng": btotal - bok,
            "total": btotal,
        })
        cursor = next_hour

    return {
        "shift": {"id": shift.id, "name": shift.name, "start": start.isoformat(), "end": end.isoformat()},
        "total": total,
        "ok": ok,
        "ng": ng,
        "target": target_qty,
        "achievement": achievement,
        "hourly": buckets,
    }
