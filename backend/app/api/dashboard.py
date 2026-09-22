from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from ..services.summary_service import get_summary

router = APIRouter(prefix="/api/summary", tags=["Dashboard"])

@router.get("/shift")
def shift_summary(shift_id:int, date_:date, db:Session=Depends(get_db)):
    result = get_summary(db, shift_id, date_)
    if result is None:
        raise HTTPException(404, "Shift not found")
    return result
