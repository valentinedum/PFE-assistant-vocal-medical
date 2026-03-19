"""
Dialogue Manager - Pipeline STT → Intent → Dialogue (LLM) → TTS.
Délègue la logique de dialogue aux services (Ollama extraction + routes),
et conserve le raffinement d'intention par mots-clés ainsi que la génération TTS.
"""

import re
from gtts import gTTS
import tempfile
import os
import base64

from services.dialogue.router import run_dialogue_logic


def process_intent(intent: str, transcription: str, context: str = None) -> dict:
    """
    Point d'entrée principal : raffine l'intention, exécute la logique de dialogue
    via les services (Ollama extraction + routes), et génère la réponse vocale TTS.
    """
    # Correction de l'intention par mots-clés (filet de sécurité si le modèle ML se trompe)
    intent = refine_intent(intent, transcription)

    # Exécuter la logique de dialogue via les services (Ollama + routes DB)
    dialogue_result = run_dialogue_logic(transcription, intent, context)
    response_text = dialogue_result.get("response")
    new_context = dialogue_result.get("context")
    final_intent = dialogue_result.get("intent", intent)

    # Générer l'audio TTS
    audio_base64 = generate_tts(response_text)

    return {
        "intent": final_intent,
        "transcription": transcription,
        "response": response_text,
        "audio": audio_base64,
        "context": new_context
    }


def refine_intent(intent: str, transcription: str) -> str:
    """
    Vérifie et corrige l'intention du modèle ML à l'aide de mots-clés.
    Utile quand Whisper transcrit mal et que le modèle se trompe.
    """
    text_lower = transcription.lower()

    # Mots-clés forts pour l'annulation
    cancel_keywords = ["annuler", "annulation", "annule", "supprimer",
                       "enlever", "retirer", "décommander"]
    for kw in cancel_keywords:
        if kw in text_lower:
            return "cancel_appointment"

    # Mots-clés forts pour l'urgence
    urgency_keywords = ["urgence", "urgent", "samu", "saigne",
                        "respire plus", "inconscient", "malaise"]
    for kw in urgency_keywords:
        if kw in text_lower:
            return "medical_urgency"
    # Numéros d'urgence : seulement si PAS suivi de "h" (pour ne pas matcher "15h")
    if re.search(r'\b15\b(?!\s*[hH])', text_lower) or re.search(r'\b112\b', text_lower):
        return "medical_urgency"

    # Mots-clés forts pour les infos pratiques
    info_keywords = ["horaire", "adresse", "où", "téléphone", "numéro",
                     "tarif", "prix", "parking", "ouvert"]
    for kw in info_keywords:
        if kw in text_lower:
            return "info_practical"

    return intent


# --- TTS ---

def generate_tts(text: str) -> str:
    """Génère un fichier audio TTS et retourne le contenu en base64."""
    try:
        tts = gTTS(text=text, lang="fr")
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tts.save(tmp.name)
            tmp_path = tmp.name

        with open(tmp_path, "rb") as f:
            audio_bytes = f.read()

        os.unlink(tmp_path)
        return base64.b64encode(audio_bytes).decode("utf-8")
    except Exception as e:
        print(f"Erreur TTS: {e}")
        return None
