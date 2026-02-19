import pandas as pd
import mlflow
import mlflow.sklearn
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score

# --- CONFIGURATION ---
TRAIN_PATH = "data/processed/train.csv"
TEST_PATH = "data/processed/test.csv"
MLFLOW_TRACKING_DIR = "http://mlflow:5000"
EXPERIMENT_NAME = "medical_intent_classification"


def train():
    mlflow.set_tracking_uri(MLFLOW_TRACKING_DIR)
    mlflow.set_experiment(EXPERIMENT_NAME)

    print("Chargement des données...")
    try:
        train_df = pd.read_csv(TRAIN_PATH)
        test_df = pd.read_csv(TEST_PATH)
    except FileNotFoundError:
        print("Erreur : Fichiers introuvables !")
        return

    with mlflow.start_run() as run:
        print(f"Run ID: {run.info.run_id}")

        # --- PIPELINE NLP ---
        model = Pipeline(
            [
                (
                    "vectorizer",
                    TfidfVectorizer(ngram_range=(1, 2), max_df=0.95, min_df=1),
                ),
                ("classifier", SVC(probability=True, kernel="linear")),
            ]
        )

        print("Entraînement du modèle...")
        model.fit(train_df["text"], train_df["intent"])

        predictions = model.predict(test_df["text"])
        accuracy = accuracy_score(test_df["intent"], predictions)

        print(f"Accuracy : {accuracy:.2f}")

        mlflow.log_metric("accuracy", accuracy)
        mlflow.sklearn.log_model(model, "model_intent_classifier")

        model_uri = f"runs:/{run.info.run_id}/model_intent_classifier"

        # Enregistre le modèle dans le Model Registry
        mlflow.register_model(model_uri, "medical_intent_classifier")

        print(f"Modèle sauvegardé ! URI : {model_uri}")
        print(f"✅ Modèle enregistré dans le Model Registry")


if __name__ == "__main__":
    train()
