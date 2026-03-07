FROM python:3.9-slim

WORKDIR /app

# Installation de ffmpeg (requis par Whisper)
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Installation des dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code
COPY . .

# Lancement de l'API
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]