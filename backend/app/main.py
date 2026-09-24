from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.config import settings
from .db import Base, engine, SessionLocal
from .models import Shift, Station
from .api.crud import router as crud_router
from .api.dashboard import router as dashboard_router
from .api.ingestion import router as ingestion_router
from datetime import time

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Automation Machine Dashboard API", version="1.4.0")

origins = [x.strip() for x in settings.cors_origins.split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(crud_router)
app.include_router(dashboard_router)
app.include_router(ingestion_router)

@app.on_event("startup")
def seed():
    db = SessionLocal()
    try:
        if db.query(Shift).count() == 0:
            db.add_all([
                Shift(name="SHIFT 1", start_time=time(7,0), end_time=time(17,0), is_active=True),
                Shift(name="SHIFT 2", start_time=time(17,0), end_time=time(3,0), is_active=True),
            ])
        if db.query(Station).count() == 0:
            db.add_all([
                Station(name=f"STATION {i}", sequence_order=i, is_active=True)
                for i in range(1, 12)
            ])
        db.commit()
    finally:
        db.close()

@app.get("/api/health")
def health():
    return {"status":"online"}

@app.get("/api/build-info")
def build_info():
    return {"backend_version": "V10.2", "features": ["csv_header_autodetect", "column_mapping", "folder_scan", "live_refresh"]}

