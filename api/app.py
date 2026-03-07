from fastapi import FastAPI, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from postgres import Postgres
import mlflow
import whisper
import tempfile
import os
from dialogue_manager import process_intent

app = FastAPI(title="Assistant Vocal Médical API", version="0.4.0")

# --- CONFIGURATION ---
mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000"))
MODEL_PATH = os.getenv("MODEL_PATH", "models:/medical_intent_classifier/1")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")

# --- CHARGEMENT MODELE WHISPER ---
print("Chargement du modèle Whisper...")
whisper_model = whisper.load_model(WHISPER_MODEL)
print("Modèle Whisper chargé !")

# --- ROUTES API ---
@app.get("/")
def read_root():
    return FileResponse("/app/static/index.html")

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/appointments")
def get_appointments():
    db = Postgres("postgresql://user:password@db:5432/medical_db")
    slots = db.all(
        "SELECT s.id, s.start_time, d.name as doctor_name, d.specialty "
        "FROM slots s JOIN doctors d ON s.doctor_id = d.id "
        "WHERE s.is_booked = FALSE ORDER BY s.start_time;"
    )
    return {"available_slots": slots}

@app.post("/predict")
def predict_intent(text: str):
    """Prédit l'intention et exécute l'action correspondante avec réponse vocale."""
    model = mlflow.sklearn.load_model(MODEL_PATH)
    intent = model.predict([text])[0]
    result = process_intent(intent, text)
    return result

@app.post("/transcribe")
def transcribe_audio(file: UploadFile = File(...)):
    """Reçoit un fichier audio, le transcrit, prédit l'intention et exécute l'action."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(file.file.read())
        tmp_path = tmp.name

    try:
        # Transcription avec Whisper
        result = whisper_model.transcribe(tmp_path, language="fr")
        text = result["text"].strip()

        # Prédiction de l'intention
        model = mlflow.sklearn.load_model(MODEL_PATH)
        intent = model.predict([text])[0]

        # Traitement via le dialogue manager (action + TTS)
        response = process_intent(intent, text)
        return response
    finally:
        os.unlink(tmp_path)

# --- FICHIERS STATIQUES (front-end) ---
app.mount("/static", StaticFiles(directory="/app/static"), name="static")