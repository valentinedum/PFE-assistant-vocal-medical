from fastapi import FastAPI
from pydantic import BaseModel
from postgres import Postgres
import mlflow
import os

from dialogue.router import run_dialogue_logic

app = FastAPI(title="Assistant Vocal Médical API", version="0.3.0")

# --- CONFIGURATION ---
mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000"))
MODEL_PATH = os.getenv("MODEL_PATH", "models:/medical_intent_classifier/Production")


class DialogueRequest(BaseModel):
    text: str


@app.get("/")
def read_root():
    return {"status": "alive", "version": "0.3.0"}


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


@app.post("/dialogue")
def dialogue(request: DialogueRequest):
    """Endpoint complet : Intent Classification + Dialogue Logic"""
    try:
        # 1. Prédire l'intent
        model = mlflow.sklearn.load_model(MODEL_PATH)
        intent = model.predict([request.text])[0]

        # 2. Exécuter la logique de dialogue
        response = run_dialogue_logic(request.text, intent)

        return {"text": request.text, "intent": intent, "response": response}
    except Exception as e:
        return {"error": str(e), "text": request.text}
