from datetime import datetime, time, date
from sqlalchemy import String, Integer, Boolean, DateTime, Date, Time, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base


class Shift(Base):
    __tablename__ = "shifts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Target(Base):
    __tablename__ = "targets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shift_id: Mapped[int] = mapped_column(ForeignKey("shifts.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    target_qty: Mapped[int] = mapped_column(Integer, nullable=False)
    shift = relationship("Shift")


class Station(Base):
    __tablename__ = "stations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class StationOutputSource(Base):
    __tablename__ = "station_output_sources"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    station_id: Mapped[int] = mapped_column(ForeignKey("stations.id"), nullable=False)
    csv_folder_path: Mapped[str] = mapped_column(Text, nullable=False)
    station = relationship("Station")


class ProductionRecord(Base):
    __tablename__ = "production_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    crack_result: Mapped[str] = mapped_column(String(30), default="")
    final_result: Mapped[str] = mapped_column(String(30), default="")
    source_file: Mapped[str] = mapped_column(String(500), default="")
    source_row: Mapped[int] = mapped_column(Integer, default=0)


class ManualCorrection(Base):
    __tablename__ = "manual_corrections"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    production_record_id: Mapped[int | None] = mapped_column(ForeignKey("production_records.id"), nullable=True)
    correction_datetime: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    field_changed: Mapped[str] = mapped_column(String(100), nullable=False)
    old_value: Mapped[str] = mapped_column(Text, default="")
    new_value: Mapped[str] = mapped_column(Text, default="")
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    corrected_by: Mapped[str] = mapped_column(String(100), nullable=False)
    corrected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    production_record = relationship("ProductionRecord")
