FROM python:3.10-slim

WORKDIR /app

# Installation de ffmpeg (requis par Whisper)
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Installation des dépendances lourdes en CPU (cachées séparément)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir openai openai-whisper mlflow scikit-learn

# Installation des autres dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code
COPY . .

# Lancement de l'API
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]