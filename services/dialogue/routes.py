from postgres import Postgres
from services.dialogue.utils import (
    validate_and_parse_slots, get_slot_id, MissingInfoError,
    get_doctors_list, get_clinic_info, guess_info_type, get_availabilities
)
from prometheus_client import Counter

db = Postgres("postgresql://user:password@db:5432/medical_db")

# Métriques pour l'extraction via LLM et les actions de dialogue
EXTRACTION_TOTAL = Counter("extraction_attempts_total", "Nombre total de tentatives d'extraction des slots")
EXTRACTION_SUCCESS = Counter("extraction_success_total", "Nombre d'extractions réussies des slots")

ACTION_PROPOSED = Counter("action_proposed_total", "Nombre d'actions proposées pour confirmation", ["action_type"])
ACTION_CONFIRMED = Counter("action_confirmed_total", "Nombre d'actions validées jusqu'au bout", ["action_type"])

INFO_TYPES = {
    "address": ("address", "Notre cabinet est situé au"),
    "hours": ("hours", "Nos horaires :"),
    "phone": ("phone", "Vous pouvez nous contacter au"),
    "price": ("price", "Tarif :"),
    "parking": ("parking", "Parking :"),
}
def handle_emergency(user_text):
    return "En cas d'urgence, appelez le 15 (SAMU) ou les services d'urgence locaux."


def handle_appointment(slots, confirmation=False):
    try:

        if not confirmation:
            EXTRACTION_TOTAL.inc()
        
        day_num, hour, doctor_id, doc_name = validate_and_parse_slots(slots)

        if not confirmation:
            EXTRACTION_SUCCESS.inc()

        slot_id = get_slot_id(doctor_id, day_num, hour, False)
        if slot_id is None:
            return {
                "message": f"Désolé, le créneau du {slots.get('date')} à {slots.get('heure')} n'est pas disponible pour le Dr. {doc_name}.",
                "needs_confirmation": False
            }
        if not confirmation:
            ACTION_PROPOSED.labels(action_type="book_appointment").inc()
            return {
                "message": f"Le créneau du {slots.get('date')} à {slots.get('heure')} est disponible. Dites 'oui' pour confirmer.",
                "needs_confirmation": True 
            }
        
        ACTION_CONFIRMED.labels(action_type="book_appointment").inc()
        db.run("UPDATE slots SET is_booked = TRUE WHERE id = %s;", (slot_id,))
        db.run(
            "INSERT INTO appointments (slot_id, doctor_id, transcription) VALUES (%s, %s, %s);",
            (slot_id, doctor_id, f"{slots.get('date')} {slots.get('heure')} Dr. {doc_name}")
        )

        return {
            "message": f"C'est noté, le rendez-vous est confirmé le {slots.get('date')}.",
            "needs_confirmation": False
        }
    
    except MissingInfoError as e:
        msg = get_availabilities(slots, is_booked=False)
        if msg:
            return {
                "message": msg + " Pour prendre rendez-vous, dites par exemple que vous voulez un rendez-vous et précise le docteur, le jour et l'heure.",
                "needs_confirmation": False
            }
        details = ", ".join(e.missing_fields)
        return {
            "message": f"Il me manque des informations pour prendre le rendez-vous : {details}. Dites que vous voulez un rendez-vous et précise le docteur, le jour et l'heure.",
            "needs_confirmation": False
        }
    except Exception as e:
        return {
            "message": f"Erreur de prise de rendez-vous: {str(e)}",
            "needs_confirmation": False
        }

def handle_cancel_appointment(slots, confirmation=False):
    try:
        if not confirmation:
            EXTRACTION_TOTAL.inc()

        day_num, hour, doctor_id, doc_name = validate_and_parse_slots(slots)

        if not confirmation:
            EXTRACTION_SUCCESS.inc()

        slot_id = get_slot_id(doctor_id, day_num, hour, True)
        if slot_id is None:
            return {
                "message": f"Aucun rendez-vous trouvé pour le Dr. {doc_name} ce jour-là.",
                "needs_confirmation": False
            }

        if not confirmation:
            ACTION_PROPOSED.labels(action_type="cancel_appointment").inc()
            return {
                "message": f"Vous avez un rendez-vous avec le Dr. {doc_name} le {slots.get('date')} à {slots.get('heure')}. Dites 'oui' pour confirmer l'annulation.",
                "needs_confirmation": True
            }
        
        ACTION_CONFIRMED.labels(action_type="cancel_appointment").inc()
        db.run("UPDATE slots SET is_booked = FALSE WHERE id = %s;", (slot_id,))
        db.run("DELETE FROM appointments WHERE slot_id = %s;", (slot_id,))
        return {
            "message": f"Votre rendez-vous avec le Dr. {doc_name} le {slots.get('date')} a été annulé.",
            "needs_confirmation": False
        }
    
    except MissingInfoError as e:
        details = ", ".join(e.missing_fields)
        return {
            "message": f"Il me manque des informations pour annuler votre rendez-vous : {details}. Merci de préciser le médecin, le jour et l'heure en une seule phrase.",
            "needs_confirmation": False
        }
    except Exception as e:
        return {
            "message": f"Erreur d'annulation: {str(e)}",
            "needs_confirmation": False
        }

def handle_info(user_text, info_type):
    try:
        # Médecins / spécialistes
        if info_type == "specialists":
            doctors = get_doctors_list()
            return f"Nos médecins : {doctors}" if doctors else "Aucun médecin disponible."

        # Info connue (address, hours, phone, price, parking)
        if info_type in INFO_TYPES:
            type_info, label = INFO_TYPES[info_type]
            value = get_clinic_info(type_info)
            return f"{label} {value}" if value else f"{info_type} non disponible"

        # Fallback : deviner depuis le texte original
        fallback = guess_info_type(user_text)
        if fallback:
            return handle_info(user_text, fallback)

        return "Information non disponible."
    except Exception as e:
        return f"Erreur: {str(e)}"

