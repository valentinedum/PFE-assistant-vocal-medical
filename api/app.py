from fastapi import FastAPI
from postgres import Postgres
import mlflow

app = FastAPI(title="Assistant Vocal Médical API", version="0.2.0")

# --- CONFIGURATION ---
# Pour simplifier, on utilise un chemin local pour le modèle. En production, ce serait un URI MLflow.
MODEL_PATH = "/mlartifacts/1/models/m-f2df07c11b2b480e8a70ca2a9d1324fb/artifacts"

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