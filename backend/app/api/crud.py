from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Shift, Target, Station, StationOutputSource, CsvColumnMapping, ManualCorrection, ProductionRecord
from ..schemas import *

router = APIRouter(prefix="/api", tags=["CRUD"])


def crud_routes(model, schema_create, name):
    # kept as a conceptual helper; explicit routes below make API docs clearer.
    pass


@router.get("/shifts", response_model=list[ShiftOut])
def list_shifts(db: Session = Depends(get_db)):
    return db.query(Shift).order_by(Shift.start_time).all()

@router.post("/shifts", response_model=ShiftOut)
def create_shift(data: ShiftCreate, db: Session = Depends(get_db)):
    obj = Shift(**data.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

@router.put("/shifts/{id}", response_model=ShiftOut)
def update_shift(id: int, data: ShiftCreate, db: Session = Depends(get_db)):
    obj = db.get(Shift, id)
    if not obj: raise HTTPException(404, "Shift not found")
    for k,v in data.model_dump().items(): setattr(obj,k,v)
    db.commit(); db.refresh(obj); return obj

@router.delete("/shifts/{id}")
def delete_shift(id: int, db: Session = Depends(get_db)):
    obj = db.get(Shift,id)
    if not obj: raise HTTPException(404,"Shift not found")
    db.delete(obj); db.commit(); return {"ok":True}


@router.get("/targets", response_model=list[TargetOut])
def list_targets(db: Session = Depends(get_db)):
    return db.query(Target).order_by(Target.date.desc()).all()

@router.post("/targets", response_model=TargetOut)
def create_target(data: TargetCreate, db: Session = Depends(get_db)):
    obj = Target(**data.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj

@router.put("/targets/{id}", response_model=TargetOut)
def update_target(id: int, data: TargetCreate, db: Session = Depends(get_db)):
    obj=db.get(Target,id)
    if not obj: raise HTTPException(404,"Target not found")
    for k,v in data.model_dump().items(): setattr(obj,k,v)
    db.commit(); db.refresh(obj); return obj

@router.delete("/targets/{id}")
def delete_target(id:int, db:Session=Depends(get_db)):
    obj=db.get(Target,id)
    if not obj: raise HTTPException(404,"Target not found")
    db.delete(obj); db.commit(); return {"ok":True}


@router.get("/stations", response_model=list[StationOut])
def list_stations(db:Session=Depends(get_db)):
    return db.query(Station).order_by(Station.sequence_order).all()

@router.post("/stations", response_model=StationOut)
def create_station(data:StationCreate, db:Session=Depends(get_db)):
    obj=Station(**data.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj

@router.put("/stations/{id}", response_model=StationOut)
def update_station(id:int,data:StationCreate,db:Session=Depends(get_db)):
    obj=db.get(Station,id)
    if not obj: raise HTTPException(404,"Station not found")
    for k,v in data.model_dump().items(): setattr(obj,k,v)
    db.commit(); db.refresh(obj); return obj

@router.delete("/stations/{id}")
def delete_station(id:int,db:Session=Depends(get_db)):
    obj=db.get(Station,id)
    if not obj: raise HTTPException(404,"Station not found")
    db.delete(obj); db.commit(); return {"ok":True}


@router.get("/sources", response_model=list[SourceOut])
def list_sources(db:Session=Depends(get_db)):
    return db.query(StationOutputSource).all()

@router.post("/sources", response_model=SourceOut)
def create_source(data:SourceCreate,db:Session=Depends(get_db)):
    obj=StationOutputSource(**data.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj

@router.put("/sources/{id}", response_model=SourceOut)
def update_source(id:int,data:SourceCreate,db:Session=Depends(get_db)):
    obj=db.get(StationOutputSource,id)
    if not obj: raise HTTPException(404,"Source not found")
    for k,v in data.model_dump().items(): setattr(obj,k,v)
    db.commit(); db.refresh(obj); return obj

@router.delete("/sources/{id}")
def delete_source(id:int,db:Session=Depends(get_db)):
    obj=db.get(StationOutputSource,id)
    if not obj: raise HTTPException(404,"Source not found")
    db.delete(obj); db.commit(); return {"ok":True}


@router.get("/corrections", response_model=list[CorrectionOut])
def list_corrections(db:Session=Depends(get_db)):
    return db.query(ManualCorrection).order_by(ManualCorrection.corrected_at.desc()).all()

@router.post("/corrections", response_model=CorrectionOut)
def create_correction(data:CorrectionCreate,db:Session=Depends(get_db)):
    rec = db.get(ProductionRecord, data.production_record_id) if data.production_record_id else None
    old = ""
    if rec:
        if not hasattr(rec, data.field_changed):
            raise HTTPException(400, "Invalid field")
        old = str(getattr(rec, data.field_changed))
        setattr(rec, data.field_changed, data.new_value)
    obj=ManualCorrection(
        production_record_id=data.production_record_id,
        field_changed=data.field_changed,
        old_value=old,
        new_value=data.new_value,
        reason=data.reason,
        corrected_by=data.corrected_by,
    )
    db.add(obj); db.commit(); db.refresh(obj); return obj

@router.get("/sources/{id}/mapping", response_model=CsvMappingOut | None)
def get_source_mapping(id: int, db: Session = Depends(get_db)):
    source = db.get(StationOutputSource, id)
    if not source:
        raise HTTPException(404, "Source not found")
    return source.mapping

@router.put("/sources/{id}/mapping", response_model=CsvMappingOut)
def save_source_mapping(id: int, data: CsvMappingCreate, db: Session = Depends(get_db)):
    source = db.get(StationOutputSource, id)
    if not source:
        raise HTTPException(404, "Source not found")
    mapping = source.mapping
    if mapping is None:
        mapping = CsvColumnMapping(source_id=id, **data.model_dump())
        db.add(mapping)
    else:
        for k, v in data.model_dump().items():
            setattr(mapping, k, v)
    db.commit(); db.refresh(mapping)
    return mapping
