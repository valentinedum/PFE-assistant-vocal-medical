from fastapi import FastAPI
from postgres import Postgres

app = FastAPI(title="Assistant Vocal Médical API", version="0.1.0")

@app.get("/")
def read_root():
    return {"status": "alive", "version": "0.1.0"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/appointments")
def get_appointments():
    db = Postgres("postgresql://user:password@db:5432/medical_db")
    slots = db.all("SELECT * FROM slots WHERE is_booked = FALSE;")
    return {"available_slots": slots}