import instructor
from difflib import get_close_matches
from pydantic import BaseModel, Field
from typing import Optional
from prometheus_client import Counter

_client = None

EXTRACTION_TOTAL = Counter("extraction_attempts_total", "Nombre total de tentatives d'extraction des slots")
EXTRACTION_SUCCESS = Counter("extraction_success_total", "Nombre d'extractions réussies des slots")

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

class ConfirmationResponse(BaseModel):
    confirmation: Optional[str] = Field(None, description="Valeur 'oui', 'non' ou None")

# Fonction d'extraction des slots de rendez-vous et d'informations du cabinet à l'aide d'Ollama
def extract_slots_with_ollama(text):
    EXTRACTION_TOTAL.inc()
    try:
        client = get_instructor_client()

        # Instruction pour Ollama
        prompt = """Tu es un extracteur d'informations de rendez-vous médical. Analyse le texte et extrais UNIQUEMENT les informations EXPLICITEMENT présentes.

                    Texte: {text}

                    Règles STRICTES:
                    - date: UNIQUEMENT un jour de la semaine (lundi/mardi/mercredi/jeudi/vendredi/samedi/dimanche) SI et SEULEMENT SI le patient le mentionne explicitement. Corrige les fautes de transcription (ex: "veut dit" → "vendredi"). Si AUCUN jour n'apparaît dans le texte → None.
                    - heure: format HH:MM. Convertis: "midi" → "12:00", "15h" → "15:00", "dix heures" → "10:00". Si AUCUNE heure n'apparaît → None.
                    - praticien: nom de famille uniquement (sans "Dr." ni "docteur"). Si AUCUN nom n'apparaît → None.

                    Exemples:
                    - "RDV avec Dr Robert mardi à 14h" → date: "mardi", heure: "14:00", praticien: "Robert"
                    - "RDV avec Dr Robert à 15h" → date: None, heure: "15:00", praticien: "Robert"
                    - "RDV mardi à 10h" → date: "mardi", heure: "10:00", praticien: None
                    - "Je veux un rendez-vous" → date: None, heure: None, praticien: None

                    NE DEVINE JAMAIS. Si l'info n'est pas dans le texte, retourne None."""

        # On envoie à Ollama
        response = client.chat.completions.create(
            model="mistral",
            messages=[{"role": "user", "content": prompt.format(text=text)}],
            response_model=SlotsInfo,  # Force à retourner SlotsInfo
        )

        result = response.dict()
        
        # Sécurité : Ollama invente parfois un jour — vérifier qu'il existe dans le texte
        if result.get("date"):
            jours = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
            mots = text.lower().split()
            if not any(get_close_matches(mot, jours, n=1, cutoff=0.7) for mot in mots):
                result["date"] = None

        # Sécurité : vérifier que l'heure existe dans le texte
        if result.get("heure"):
            import re
            text_lower = text.lower()
            mots_heure = ["midi", "minuit", "heure", "heures"]
            has_time_word = any(m in text_lower for m in mots_heure)
            has_time_number = bool(re.search(r'\d{1,2}\s*[h:]', text_lower)) or bool(re.search(r'\b\d{1,2}\b.*heure', text_lower))
            if not has_time_word and not has_time_number:
                result["heure"] = None
        
        EXTRACTION_SUCCESS.inc()

        return result

    except Exception as e:
        print(f"Erreur Ollama: {e}")
        return {"date": None, "heure": None, "praticien": None}


def extract_clinic_info(text):
    EXTRACTION_TOTAL.inc()
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

        EXTRACTION_SUCCESS.inc()

        return response.dict()

    except Exception as e:
        print(f"Erreur Ollama: {e}")
        return {"requested_info": "other"}


def extract_confirmation(text: str):
        """Extrait uniquement une confirmation explicite (oui/non) à partir du texte.

        À appeler par exemple après avoir proposé un créneau :
        - "Oui, jeconfirme le rendez-vous"       → confirmation="oui"
        - "Non, je ne veux pas ce rendez-vous"   → confirmation="non"
        - "Je ne sais pas" / question            → confirmation=None
        """

        EXTRACTION_TOTAL.inc()
        try:
                client = get_instructor_client()

                prompt = """Tu es un extracteur de confirmation pour des rendez-vous médicaux.

                                        Texte: {text}

                                        Ta tâche est de dire si la personne CONFIRME ou REFUSE une action
                                        sur un rendez-vous déjà proposé.

                                        Règles :
                                        - Si la personne dit clairement qu'elle confirme / valide / garde / est d'accord
                                            → confirmation = "oui".
                                        - Si la personne dit clairement qu'elle annule / refuse / ne veut pas / ne confirme pas
                                            → confirmation = "non".
                                        - Si ce n'est ni clairement oui ni clairement non (question, hésitation, autre)
                                            → confirmation = None.

                                        NE DEVINE JAMAIS. Si ce n'est pas évident, mets None."""

                response = client.chat.completions.create(
                        model="mistral",
                        messages=[{"role": "user", "content": prompt.format(text=text)}],
                        response_model=ConfirmationResponse,
                )

                EXTRACTION_SUCCESS.inc()

                return response.dict()

        except Exception as e:
                print(f"Erreur Ollama (confirmation): {e}")
                return {"confirmation": None}

