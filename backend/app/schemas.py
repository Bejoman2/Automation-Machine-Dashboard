from datetime import datetime, date, time
from pydantic import BaseModel, ConfigDict


class ShiftBase(BaseModel):
    name: str
    start_time: time
    end_time: time
    is_active: bool = True

class ShiftCreate(ShiftBase): pass
class ShiftOut(ShiftBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class TargetBase(BaseModel):
    shift_id: int
    date: date
    target_qty: int

class TargetCreate(TargetBase): pass
class TargetOut(TargetBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class StationBase(BaseModel):
    name: str
    sequence_order: int
    is_active: bool = True

class StationCreate(StationBase): pass
class StationOut(StationBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class SourceBase(BaseModel):
    station_id: int
    csv_folder_path: str

class SourceCreate(SourceBase): pass
class SourceOut(SourceBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class CorrectionCreate(BaseModel):
    production_record_id: int | None = None
    field_changed: str
    new_value: str
    reason: str
    corrected_by: str


class CorrectionOut(CorrectionCreate):
    id: int
    correction_datetime: datetime
    old_value: str
    corrected_at: datetime
    model_config = ConfigDict(from_attributes=True)
