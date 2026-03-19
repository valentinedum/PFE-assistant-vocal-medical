from time import time
from fastapi import FastAPI, UploadFile, File, Request, Form, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from postgres import Postgres
import mlflow
import whisper
import tempfile
import os
from dialogue_manager import process_intent
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

# Définition des métriques techniques
REQUEST_COUNT = Counter("api_requests_total", "Total des requêtes API", ["method", "endpoint"])
REQUEST_LATENCY = Histogram("api_request_latency_seconds", "Latence des requêtes API")

# Définition des métriques métiers (Base de données)
APPOINTMENTS_BOOKED = Gauge("appointments_booked_total", "Total des rendez-vous réservés")
OCCUPATION_RATE = Gauge("slot_occupation_rate", "Taux d'occupation des créneaux (0-100)")

# Définition des métriques métiers (Machine Learning)
INTENT_CLASSIFICATION_ACCURACY = Gauge("intent_classification_accuracy", "Accuracy du modèle d'intentions")
INTENT_CLASSIFICATION_F1 = Gauge("intent_classification_f1_score", "F1-Score du modèle d'intentions")

app = FastAPI(title="Assistant Vocal Médical API", version="0.5.0")

# --- CONFIGURATIONS MODELES---
mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000"))
MODEL_PATH = os.getenv("MODEL_PATH", "models:/medical_intent_classifier/Production")
INTENT_CONFIDENCE_THRESHOLD = 0.4
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")


# --- CHARGEMENT MODELE WHISPER ---
print("Chargement du modèle Whisper...")
whisper_model = whisper.load_model(WHISPER_MODEL)
print("Modèle Whisper chargé !")


# --- ROUTES API ---
@app.middleware("http")
async def monitor_requests(request: Request, call_next):
    # Exclure les scrapes Prometheus du monitoring
    if request.url.path == "/metrics":
        return await call_next(request)
    
    start_time = time()

    response = await call_next(request)
    latency = time() - start_time
    
    endpoint = request.url.path
    method = request.method
    
    REQUEST_COUNT.labels(method=method, endpoint=endpoint).inc()
    REQUEST_LATENCY.observe(latency)
    
    return response

@app.get("/")
def read_root():
    return FileResponse("/app/static/index.html")

@app.get("/health")
def health_check():
    return {"status": "ok"}

def update_business_metrics():
    """Met à jour les métriques à partir de la base de données"""
    try:
        db = Postgres("postgresql://user:password@db:5432/medical_db")
        
        # 1. Total des rendez-vous
        booked = db.one("SELECT COUNT(*) FROM appointments;")
        APPOINTMENTS_BOOKED.set(booked if booked else 0)
        
        # 2. Taux d'occupation
        total_slots = db.one("SELECT COUNT(*) FROM slots;")
        if total_slots and total_slots > 0:
            rate = (float(booked if booked else 0) / float(total_slots)) * 100
            OCCUPATION_RATE.set(rate)
            
        # 3. Métriques MLflow (Classification)
        try:
            runs = mlflow.search_runs(experiment_names=["medical_intent_classification"], max_results=1)
            if not runs.empty:
                latest_run = runs.iloc[0]
                acc = latest_run.get('metrics.accuracy', 0)
                f1 = latest_run.get('metrics.f1_score', 0)
                INTENT_CLASSIFICATION_ACCURACY.set(acc * 100)
                INTENT_CLASSIFICATION_F1.set(f1 * 100)
        except Exception as e:
            print(f"Erreur chargement MLflow: {e}")
            
    except Exception as e:
        print(f"Erreur lors de la maj des métriques métiers: {e}")

@app.get("/metrics")
def metrics():
    update_business_metrics()
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

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
def predict_intent(text: str, context : str = None):
    """Prédit l'intention et exécute l'action correspondante avec réponse vocale."""
    model = mlflow.sklearn.load_model(MODEL_PATH)
    intent = model.predict([text])[0]
    # Seuil de confiance : si le modèle n'est pas sûr, c'est off_topic
    if hasattr(model, 'predict_proba'):
        proba = model.predict_proba([text])[0]
        if max(proba) < INTENT_CONFIDENCE_THRESHOLD:
            intent = "off_topic"
            
    result = process_intent(intent, text, context)
    return result

@app.post("/transcribe")
def transcribe_audio(file: UploadFile = File(...), context : str = Form(None)):
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

        # Seuil de confiance
        if hasattr(model, 'predict_proba'):
            proba = model.predict_proba([text])[0]
            if max(proba) < INTENT_CONFIDENCE_THRESHOLD:
                intent = "off_topic"

        # Traitement via le dialogue manager (action + TTS)
        response = process_intent(intent, text, context)
        return response
    finally:
        os.unlink(tmp_path)

# --- FICHIERS STATIQUES (front-end) ---
app.mount("/static", StaticFiles(directory="/app/static"), name="static")
