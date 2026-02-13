import pandas as pd
import os
from sklearn.model_selection import train_test_split


os.makedirs("data/processed", exist_ok=True)

print("Préparation des données...")

# Charger les données brutes
try:
    df = pd.read_csv("data/raw/data.csv")
    print(f"Données brutes chargées : {len(df)} lignes")
except FileNotFoundError:
    print("Erreur : data/raw/data.csv introuvable !")
    exit(1)


df = df.dropna(subset=['text', 'intent'])
print(f"Données nettoyées : {len(df)} lignes")

# Diviser en train/test (80/20)
train_df, test_df = train_test_split(df, test_size=0.2, random_state=42)

# Sauvegarder
train_df.to_csv("data/processed/train.csv", index=False)
test_df.to_csv("data/processed/test.csv", index=False)

print(f"✓ Train set : {len(train_df)} lignes")
print(f"✓ Test set : {len(test_df)} lignes")
print("Données préparées avec succès !")
