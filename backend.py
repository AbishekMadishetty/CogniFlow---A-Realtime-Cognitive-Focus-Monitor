"""
CogniFlow — Cloud Backend API
Catches telemetry data from edge devices and stores it in a relational database.
Built with FastAPI and SQLAlchemy.
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from fastapi.responses import StreamingResponse
import io
import csv
import uvicorn

# ── Database Setup (SQLAlchemy) ───────────────────────────────────────────────
# Using SQLite for local testing. Easily swappable to AWS RDS MySQL later.
SQLALCHEMY_DATABASE_URL = "sqlite:///./cogniflow.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ── Database Model (Table Schema) ─────────────────────────────────────────────
class TelemetryLog(Base):
    __tablename__ = "telemetry_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(String, index=True)
    score = Column(Integer)
    rule_label = Column(String)
    ml_label = Column(String)
    state = Column(String)
    ear = Column(Float)
    variance = Column(Float)
    yawns = Column(Integer)
    eye_closes = Column(Integer)
    activity = Column(String)

# Create the database tables
Base.metadata.create_all(bind=engine)

# ── API Setup (FastAPI) ───────────────────────────────────────────────────────
app = FastAPI(title="CogniFlow Telemetry API", version="1.0")

# Enable CORS so our future Web Dashboard (Phase 3) can communicate with this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ── Pydantic Schema (Data Validation) ─────────────────────────────────────────
# This ensures the incoming JSON strictly matches the expected format
class TelemetryPayload(BaseModel):
    timestamp: str
    score: int
    rule_label: str
    ml_label: str
    state: str
    ear: float
    variance: float
    yawns: int
    eye_closes: int
    activity: str

# ── API Endpoints ─────────────────────────────────────────────────────────────

@app.post("/api/telemetry", status_code=201)
def receive_telemetry(payload: TelemetryPayload, db: Session = Depends(get_db)):
    """Receives a 2-second telemetry payload from the edge engine and saves it."""
    db_log = TelemetryLog(**payload.dict())
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return {"status": "success", "recorded_id": db_log.id}

@app.get("/api/export-csv")
async def export_csv(db: Session = Depends(get_db)): # <--- Added db dependency
    # 1. Fetch all data from the correct table name
    sessions = db.query(TelemetryLog).all() # <--- Changed to TelemetryLog

    # 2. Setup the CSV buffer
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Headers matching your actual database columns
    writer.writerow(["ID", "Timestamp", "Score", "State", "Activity", "Yawns", "Eye_Closes", "ML_Label"])
    
    # 3. Fill the rows
    for s in sessions:
        writer.writerow([
            s.id, 
            s.timestamp, 
            s.score, 
            s.state, 
            s.activity, 
            s.yawns, 
            s.eye_closes, 
            s.ml_label
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=cogniflow_research_report.csv"}
    )


@app.get("/api/sessions")
def get_recent_telemetry(limit: int = 100, db: Session = Depends(get_db)):
    """Fetches historical telemetry data for the Web Dashboard."""
    logs = db.query(TelemetryLog).order_by(TelemetryLog.id.desc()).limit(limit).all()
    return logs


# ── Run the Server ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Starting CogniFlow Backend Server on http://localhost:8000")
    uvicorn.run("backend:app", host="127.0.0.1", port=8000, reload=True)