from postgres import Postgres
from services.dialogue.utils import (
    validate_and_parse_slots, get_slot_id, MissingInfoError,
    get_doctors_list, get_clinic_info, guess_info_type,
)

db = Postgres("postgresql://user:password@db:5432/medical_db")

INFO_TYPES = {
    "address": ("address", "Notre cabinet est situé au"),
    "hours": ("hours", "Nos horaires :"),
    "phone": ("phone", "Vous pouvez nous contacter au"),
    "price": ("price", "Tarif :"),
    "parking": ("parking", "Parking :"),
}


def handle_emergency(user_text):
    return "En cas d'urgence, appelez le 15 (SAMU) ou les services d'urgence locaux."


def handle_appointment(slots):
    try:
        day_num, hour, doctor_id, doc_name = validate_and_parse_slots(slots)

        slot_id = get_slot_id(doctor_id, day_num, hour, False)
        if slot_id is None:
            return f"Pas de créneau disponible pour le Dr. {doc_name} ce jour-là."

        db.run("UPDATE slots SET is_booked = TRUE WHERE id = %s;", (slot_id,))
        db.run(
            "INSERT INTO appointments (slot_id, doctor_id, transcription) VALUES (%s, %s, %s);",
            (slot_id, doctor_id, f"{slots.get('date')} {slots.get('heure')} Dr. {doc_name}")
        )

        date_text = slots["date"]
        time_text = slots["heure"]
        return (
            f"Rendez-vous confirmé le {date_text} à {time_text} avec le Dr. {doc_name}."
        )
    except MissingInfoError as e:
        details = ", ".join(e.missing_fields)
        return (
            f"Il me manque des informations pour prendre votre rendez-vous : {details}. "
            f"Merci de préciser le médecin, le jour et l'heure en une seule phrase. "
            f"Par exemple : 'Je voudrais un rendez-vous avec Dr. Robert, mardi à 14h.'"
        )
    except Exception as e:
        return f"Erreur de prise de rendez-vous: {str(e)}"


def handle_cancel_appointment(slots):
    try:
        day_num, hour, doctor_id, doc_name = validate_and_parse_slots(slots)

        slot_id = get_slot_id(doctor_id, day_num, hour, True)
        if slot_id is None:
            return f"Aucun rendez-vous trouvé pour le Dr. {doc_name} ce jour-là."

        db.run("UPDATE slots SET is_booked = FALSE WHERE id = %s;", (slot_id,))
        db.run("DELETE FROM appointments WHERE slot_id = %s;", (slot_id,))

        date_text = slots["date"]
        time_text = slots["heure"]
        return (
            f"Rendez-vous annulé le {date_text} à {time_text} avec le Dr. {doc_name}."
        )
    except MissingInfoError as e:
        details = ", ".join(e.missing_fields)
        return (
            f"Il me manque des informations pour annuler votre rendez-vous : {details}. "
            f"Merci de préciser le médecin, le jour et l'heure en une seule phrase."
        )
    except Exception as e:
        return f"Erreur d'annulation: {str(e)}"


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
