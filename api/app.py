from fastapi import FastAPI
from postgres import Postgres
import mlflow
import os

app = FastAPI(title="Assistant Vocal Médical API", version="0.2.0")

# --- CONFIGURATION ---
mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000"))
MODEL_PATH = os.getenv("MODEL_PATH", "models:/medical_intent_classifier/Production")

@app.get("/")
def read_root():
    return {"status": "alive", "version": "0.2.0"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/appointments")
def get_appointments():
    db = Postgres("postgresql://user:password@db:5432/medical_db")
    slots = db.all("SELECT * FROM slots WHERE is_booked = FALSE;")
    return {"available_slots": slots}

@app.post("/predict")
def predict_intent(text: str):
    model = mlflow.sklearn.load_model(MODEL_PATH)
    intent = model.predict([text])[0]
    return {"intent": intent}