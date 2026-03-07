import instructor
from pydantic import BaseModel, Field
from typing import Optional

_client = None


# Récupère un client singleton pour interagir avec Ollama (instructor)
def get_instructor_client():
    global _client
    if _client is None:
        from openai import OpenAI

        _client = instructor.from_openai(
            OpenAI(base_url="http://ollama:11434/v1", api_key="ollama"),
            mode=instructor.Mode.MD_JSON,  # Force le format de réponse en JSON pour faciliter le parsing
        )
    return _client


# Modèles de données pour les réponses d'Ollama
class SlotsInfo(BaseModel):
    date: Optional[str] = Field(
        None, description="Date du RDV (ex: 'lundi', '5 mars', 'demain')"
    )
    heure: Optional[str] = Field(None, description="Heure du RDV au format HH:MM")
    praticien: Optional[str] = Field(None, description="Nom du médecin/docteur")


class ClinicInfoType(BaseModel):
    requested_info: str = Field(
        ..., description="Type: address, hours, phone, specialists, price, parking"
    )


# Fonction d'extraction des slots de rendez-vous et d'informations du cabinet à l'aide d'Ollama
def extract_slots_with_ollama(text):
    try:
        client = get_instructor_client()

        # Instruction pour Ollama
        prompt = """Extrait les infos de rendez-vous du texte client:
                    Texte: {text}

                    Retourne EXACTEMENT:
                    - date: jour ou date textuelle
                    - heure: format HH:MM
                    - praticien: nom du médecin

                    Si une info manque, laisse None."""

        # On envoie à Ollama
        response = client.chat.completions.create(
            model="mistral",
            messages=[{"role": "user", "content": prompt.format(text=text)}],
            response_model=SlotsInfo,  # Force à retourner SlotsInfo
        )

        return response.dict()

    except Exception as e:
        print(f"Erreur Ollama: {e}")
        return {"date": None, "heure": None, "praticien": None}


def extract_clinic_info(text):
    try:
        client = get_instructor_client()

        # Instruction pour Ollama
        prompt = """Identifie quel type d'info le client demande sur le CABINET:
                    Texte: {text}

                    Types possibles:
                    - address: adresse/localisation
                    - hours: horaires d'ouverture
                    - phone: numéro de téléphone
                    - specialists: médecins/spécialités
                    - price: tarifs
                    - parking: parking
                    - other: autre

                    Retourne le type identifié."""

        # On envoie à Ollama
        response = client.chat.completions.create(
            model="mistral",
            messages=[{"role": "user", "content": prompt.format(text=text)}],
            response_model=ClinicInfoType,  # Force à retourner ClinicInfoType
        )

        return response.dict()

    except Exception as e:
        print(f"Erreur Ollama: {e}")
        return {"requested_info": "other"}
