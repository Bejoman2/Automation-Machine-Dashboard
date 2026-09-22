from datetime import datetime, date, time, timedelta
from sqlalchemy.orm import Session
from ..models import Shift


def shift_window(shift: Shift, selected_date: date):
    start = datetime.combine(selected_date, shift.start_time)
    end_date = selected_date
    if shift.end_time <= shift.start_time:
        end_date = selected_date + timedelta(days=1)
    end = datetime.combine(end_date, shift.end_time)
    return start, end


def find_shift_for_timestamp(db: Session, ts: datetime):
    shifts = db.query(Shift).filter(Shift.is_active == True).all()
    for shift in shifts:
        # Test the same date and previous date to support overnight shifts.
        for d in (ts.date(), ts.date() - timedelta(days=1)):
            start, end = shift_window(shift, d)
            if start <= ts < end:
                return shift, start, end
    return None


def hour_bucket(ts: datetime, start: datetime):
    minutes = int((ts - start).total_seconds() // 60)
    return start + timedelta(hours=minutes // 60)
