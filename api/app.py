from fastapi import FastAPI

app = FastAPI(title="Assistant Vocal Médical API", version="0.1.0")

@app.get("/")
def read_root():
    return {"status": "alive", "version": "0.1.0"}

@app.get("/health")
def health_check():
    return {"status": "ok"}