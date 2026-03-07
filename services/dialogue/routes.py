from postgres import Postgres
from services.dialogue.utils import validate_and_parse_slots, get_slot_id

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
    except Exception as e:
        error_msg = str(e)
        return f"Erreur de prise de rendez-vous: {error_msg}"


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
    except Exception as e:
        error_msg = str(e)
        return f"Erreur d'annulation: {error_msg}"


def handle_info(user_text, info_type):
    try:
        # Médecins / spécialistes
        if info_type == "specialists":
            specialists = db.all("SELECT name, specialty FROM doctors;")
            if not specialists:
                return "Aucun médecin disponible."

            doctors_list = []
            for doctor in specialists:
                name = doctor.name if hasattr(doctor, 'name') else doctor["name"]
                specialty = doctor.specialty if hasattr(doctor, 'specialty') else doctor["specialty"]
                doctors_list.append(f"Dr. {name} ({specialty})")

            return "Nos médecins : " + ", ".join(doctors_list)

        # Info connue (address, hours, phone, price, parking)
        if info_type in INFO_TYPES:
            type_info, label = INFO_TYPES[info_type]
            result = db.one("SELECT value FROM clinic_info WHERE key = %s;", (type_info,))

            if result:
                value = result if isinstance(result, str) else result[0]
                return f"{label} {value}"
            else:
                return f"{info_type} non disponible"

        # Fallback : type non reconnu → essayer de deviner depuis le texte original
        text_lower = user_text.lower()
        keyword_map = {
            "horaire": "hours", "heure": "hours", "ouvert": "hours",
            "adresse": "address", "où": "address", "situe": "address",
            "téléphone": "phone", "numéro": "phone", "appeler": "phone",
            "tarif": "price", "prix": "price", "coût": "price",
            "parking": "parking", "garer": "parking",
            "médecin": "specialists", "docteur": "specialists", "équipe": "specialists",
        }
        for keyword, fallback_type in keyword_map.items():
            if keyword in text_lower:
                return handle_info(user_text, fallback_type)

        return "Information non disponible."
    except Exception as e:
        return f"Erreur: {str(e)}"
