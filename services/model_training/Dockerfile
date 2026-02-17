FROM python:3.9-slim

WORKDIR /workspace

# Copier tous les fichiers nécessaires
COPY . .

# Installer les dépendances
RUN pip install --no-cache-dir -r services/model_training/requirements.txt

# Lancer le training
CMD ["python", "services/model_training/train.py"]
