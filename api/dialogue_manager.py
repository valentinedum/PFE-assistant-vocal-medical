"""
Dialogue Manager - Gère la logique métier selon l'intention détectée.
Chaque intention déclenche une action spécifique (réservation, annulation, etc.)
et génère une réponse vocale via TTS.
"""

import re
from datetime import datetime, timedelta
from postgres import Postgres
from gtts import gTTS
import tempfile
import os
import base64

DB_URL = "postgresql://user:password@db:5432/medical_db"


def get_db():
    return Postgres(DB_URL)


def process_intent(intent: str, transcription: str) -> dict:
    """
    Point d'entrée principal : selon l'intention, exécute l'action et retourne
    une réponse texte + audio (base64).
    """
    # Correction de l'intention par mots-clés (filet de sécurité si le modèle ML se trompe)
    intent = refine_intent(intent, transcription)

    handlers = {
        "book_appointment": handle_book_appointment,
        "cancel_appointment": handle_cancel_appointment,
        "medical_urgency": handle_medical_urgency,
        "info_practical": handle_info_practical,
        "off_topic": handle_off_topic,
    }

    handler = handlers.get(intent, handle_off_topic)
    result = handler(transcription)

    # Générer l'audio TTS
    audio_base64 = generate_tts(result["response"])

    return {
        "intent": intent,
        "transcription": transcription,
        "response": result["response"],
        "action": result.get("action"),
        "details": result.get("details"),
        "audio": audio_base64,
    }


def refine_intent(intent: str, transcription: str) -> str:
    """
    Vérifie et corrige l'intention du modèle ML à l'aide de mots-clés.
    Utile quand Whisper transcrit mal et que le modèle se trompe.
    """
    text_lower = transcription.lower()

    # Mots-clés forts pour l'annulation
    cancel_keywords = ["annuler", "annulation", "annule", "supprimer", "supprimer",
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


# --- HANDLERS PAR INTENTION ---

def handle_book_appointment(transcription: str) -> dict:
    """Cherche un médecin + créneau et réserve."""
    db = get_db()

    # Chercher le médecin mentionné
    doctor = find_doctor(db, transcription)
    if not doctor:
        doctors = db.all("SELECT name, specialty FROM doctors;")
        doctor_list = ", ".join([f"{d.name} ({d.specialty})" for d in doctors])
        return {
            "response": f"Je n'ai pas identifié le médecin souhaité. "
                        f"Les médecins disponibles sont : {doctor_list}. "
                        f"Veuillez réessayer en précisant le nom du médecin.",
            "action": "doctor_not_found",
        }

    # Extraire le jour et l'heure demandés depuis la transcription
    requested_day, requested_hour = parse_day_and_time(transcription)

    # Chercher le créneau correspondant
    if requested_day is not None and requested_hour is not None:
        # Recherche avec jour + heure précis
        slot = db.one(
            "SELECT s.id, s.start_time FROM slots s "
            "WHERE s.doctor_id = %s AND s.is_booked = FALSE "
            "AND EXTRACT(DOW FROM s.start_time) = %s "
            "AND EXTRACT(HOUR FROM s.start_time) = %s "
            "ORDER BY s.start_time ASC LIMIT 1;",
            (doctor.id, requested_day, requested_hour)
        )
        if not slot:
            # Créneau exact non dispo, proposer le plus proche ce jour-là
            slot = db.one(
                "SELECT s.id, s.start_time FROM slots s "
                "WHERE s.doctor_id = %s AND s.is_booked = FALSE "
                "AND EXTRACT(DOW FROM s.start_time) = %s "
                "ORDER BY s.start_time ASC LIMIT 1;",
                (doctor.id, requested_day)
            )
    elif requested_day is not None:
        # Jour demandé sans heure précise
        slot = db.one(
            "SELECT s.id, s.start_time FROM slots s "
            "WHERE s.doctor_id = %s AND s.is_booked = FALSE "
            "AND EXTRACT(DOW FROM s.start_time) = %s "
            "ORDER BY s.start_time ASC LIMIT 1;",
            (doctor.id, requested_day)
        )
    elif requested_hour is not None:
        # Heure demandée sans jour précis
        slot = db.one(
            "SELECT s.id, s.start_time FROM slots s "
            "WHERE s.doctor_id = %s AND s.is_booked = FALSE "
            "AND EXTRACT(HOUR FROM s.start_time) = %s "
            "ORDER BY s.start_time ASC LIMIT 1;",
            (doctor.id, requested_hour)
        )
    else:
        # Aucune préférence, prendre le prochain disponible
        slot = db.one(
            "SELECT s.id, s.start_time FROM slots s "
            "WHERE s.doctor_id = %s AND s.is_booked = FALSE "
            "ORDER BY s.start_time ASC LIMIT 1;",
            (doctor.id,)
        )

    if not slot:
        return {
            "response": f"Désolé, il n'y a plus de créneaux disponibles pour {doctor.name}. "
                        f"Veuillez réessayer ultérieurement ou choisir un autre jour.",
            "action": "no_slot_available",
        }

    # Réserver le créneau
    db.run(
        "UPDATE slots SET is_booked = TRUE WHERE id = %s;",
        (slot.id,)
    )
    db.run(
        "INSERT INTO appointments (slot_id, doctor_id, transcription) "
        "VALUES (%s, %s, %s);",
        (slot.id, doctor.id, transcription)
    )

    # Formater la date/heure
    dt = slot.start_time
    jour = format_date(dt)
    heure = dt.strftime("%Hh%M")

    return {
        "response": f"Votre rendez-vous avec {doctor.name} a bien été pris en compte "
                    f"pour le {jour} à {heure}. Merci et à bientôt.",
        "action": "appointment_booked",
        "details": {
            "doctor": doctor.name,
            "date": str(dt.date()),
            "time": heure,
            "slot_id": slot.id,
        },
    }


def handle_cancel_appointment(transcription: str) -> dict:
    """Annule le dernier rendez-vous enregistré."""
    db = get_db()

    # Trouver le dernier rdv
    appointment = db.one(
        "SELECT a.id, a.slot_id, a.doctor_id, s.start_time, d.name as doctor_name "
        "FROM appointments a "
        "JOIN slots s ON a.slot_id = s.id "
        "JOIN doctors d ON a.doctor_id = d.id "
        "ORDER BY a.booked_at DESC LIMIT 1;"
    )

    if not appointment:
        return {
            "response": "Aucun rendez-vous trouvé à annuler. "
                        "Vous n'avez pas de rendez-vous enregistré.",
            "action": "no_appointment_found",
        }

    # Libérer le créneau et supprimer le rdv
    db.run("UPDATE slots SET is_booked = FALSE WHERE id = %s;", (appointment.slot_id,))
    db.run("DELETE FROM appointments WHERE id = %s;", (appointment.id,))

    dt = appointment.start_time
    jour = format_date(dt)
    heure = dt.strftime("%Hh%M")

    return {
        "response": f"Votre rendez-vous avec {appointment.doctor_name} "
                    f"du {jour} à {heure} a bien été annulé.",
        "action": "appointment_cancelled",
        "details": {
            "doctor": appointment.doctor_name,
            "date": str(dt.date()),
            "time": heure,
        },
    }


def handle_medical_urgency(transcription: str) -> dict:
    """Redirige vers le SAMU."""
    return {
        "response": "Urgence médicale détectée. Vous allez être redirigé vers le SAMU. "
                    "Veuillez appeler le 15 ou le 112 immédiatement.",
        "action": "redirect_samu",
    }


def handle_info_practical(transcription: str) -> dict:
    """Retourne les infos pratiques selon la demande."""
    db = get_db()
    text_lower = transcription.lower()

    # Détecter si la demande concerne les médecins / docteurs
    doctor_keywords = ["docteur", "médecin", "medecin", "praticien",
                       "spécialiste", "specialiste", "équipe", "soignant"]
    for kw in doctor_keywords:
        if kw in text_lower:
            doctors = db.all("SELECT name, specialty FROM doctors;")
            doctor_list = ", ".join([f"{d.name} ({d.specialty})" for d in doctors])
            return {
                "response": f"Notre équipe médicale est composée de : {doctor_list}.",
                "action": "info_provided",
                "details": {"key": "doctors", "value": doctor_list},
            }

    # Détecter le type d'info demandée
    info_mapping = {
        "horaire": "hours",
        "heure": "hours",
        "ouvert": "hours",
        "adresse": "address",
        "où": "address",
        "situe": "address",
        "localisation": "address",
        "téléphone": "phone",
        "numéro": "phone",
        "appeler": "phone",
        "tarif": "price",
        "prix": "price",
        "coût": "price",
        "combien": "price",
        "payer": "price",
        "parking": "parking",
        "garer": "parking",
        "voiture": "parking",
        "stationner": "parking",
    }

    matched_key = None
    for keyword, info_key in info_mapping.items():
        if keyword in text_lower:
            matched_key = info_key
            break

    if matched_key:
        info = db.one(
            "SELECT value FROM clinic_info WHERE key = %s;",
            (matched_key,)
        )
        if info:
            # db.one() avec SELECT d'une seule colonne retourne directement la valeur (str)
            info_value = info if isinstance(info, str) else info.value
            label_map = {
                "hours": "Nos horaires",
                "address": "Notre adresse",
                "phone": "Notre numéro de téléphone",
                "price": "Nos tarifs",
                "parking": "Informations parking",
            }
            label = label_map.get(matched_key, "Information")
            return {
                "response": f"{label} : {info_value}.",
                "action": "info_provided",
                "details": {"key": matched_key, "value": info_value},
            }

    # Si on ne sait pas quelle info, tout retourner (y compris les médecins)
    all_info = db.all("SELECT key, value FROM clinic_info;")
    clinic_name = next((i.value for i in all_info if i.key == "clinic_name"), "la clinique")
    info_text = ". ".join([
        f"{label_for_key(i.key)} : {i.value}"
        for i in all_info if i.key != "clinic_name"
    ])

    # Ajouter la liste des médecins dans les infos générales
    doctors = db.all("SELECT name, specialty FROM doctors;")
    doctor_list = ", ".join([f"{d.name} ({d.specialty})" for d in doctors])
    info_text += f". Nos médecins : {doctor_list}"

    return {
        "response": f"Voici les informations pratiques de {clinic_name}. {info_text}.",
        "action": "all_info_provided",
    }


def handle_off_topic(transcription: str) -> dict:
    """Demande hors sujet."""
    return {
        "response": "Je n'ai pas compris votre demande. "
                    "Je suis un assistant médical, je peux vous aider à prendre un rendez-vous, "
                    "l'annuler, ou vous donner des informations pratiques sur la clinique. "
                    "Merci de réitérer votre demande.",
        "action": "off_topic",
    }


# --- UTILITAIRES ---

def find_doctor(db, transcription: str):
    """Cherche un médecin mentionné dans la transcription."""
    doctors = db.all("SELECT id, name, specialty FROM doctors;")
    text_lower = transcription.lower()

    for doctor in doctors:
        # Chercher par nom (ex: "House", "Smith", "Cymes")
        name_parts = doctor.name.lower().split()
        for part in name_parts:
            if part not in ("dr.", "dr", "docteur") and part in text_lower:
                return doctor

        # Chercher par spécialité
        if doctor.specialty.lower() in text_lower:
            return doctor

    return None


def parse_day_and_time(transcription: str):
    """
    Extrait le jour de la semaine et l'heure depuis la transcription.
    Retourne (dow, hour) où dow = 1 (lundi) à 5 (vendredi), hour = 9-17.
    Retourne (None, None) si non trouvé.
    """
    text_lower = transcription.lower()

    # Mapping jours → DOW PostgreSQL (1=lundi, 5=vendredi)
    jours_map = {
        "lundi": 1, "mardi": 2, "mercredi": 3,
        "jeudi": 4, "vendredi": 5,
    }

    # Trouver le jour
    requested_day = None
    for jour, dow in jours_map.items():
        if jour in text_lower:
            requested_day = dow
            break

    # Trouver l'heure (ex: "15h", "15h00", "15 heures", "à 9h", "14h30")
    requested_hour = None
    hour_match = re.search(r'(\d{1,2})\s*[hH](?:\s*\d{0,2})?', text_lower)
    if not hour_match:
        hour_match = re.search(r'(\d{1,2})\s*heure', text_lower)
    if hour_match:
        hour = int(hour_match.group(1))
        if 9 <= hour <= 18:
            requested_hour = hour

    return requested_day, requested_hour


def format_date(dt) -> str:
    """Formate une date en français."""
    jours = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
    mois = ["janvier", "février", "mars", "avril", "mai", "juin",
            "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
    return f"{jours[dt.weekday()]} {dt.day} {mois[dt.month - 1]}"


def label_for_key(key: str) -> str:
    """Retourne un label lisible pour une clé d'info pratique."""
    labels = {
        "hours": "Horaires",
        "address": "Adresse",
        "phone": "Téléphone",
        "price": "Tarifs",
        "parking": "Parking",
        "clinic_name": "Nom de la clinique",
    }
    return labels.get(key, key)


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
