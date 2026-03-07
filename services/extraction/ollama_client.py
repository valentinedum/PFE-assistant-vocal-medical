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
        prompt = """Extrait les infos de rendez-vous du texte client.
                    Le texte peut contenir des erreurs de transcription vocale.

                    Texte: {text}

                    Retourne EXACTEMENT:
                    - date: le jour de la semaine en français, UNIQUEMENT parmi : lundi, mardi, mercredi, jeudi, vendredi, samedi, dimanche. Corrige les fautes de transcription (ex: "veut dit" → "vendredi", "mère credi" → "mercredi").
                    - heure: format HH:MM. Convertis les mots en heures : "midi" → "12:00", "minuit" → "00:00", "15h" → "15:00", "9h30" → "09:30", "quinze heures" → "15:00", "dix heures" → "10:00".
                    - praticien: nom de famille du médecin uniquement (sans "Dr." ni "docteur")

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
