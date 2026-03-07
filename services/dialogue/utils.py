from difflib import get_close_matches
from postgres import Postgres

db = Postgres("postgresql://user:password@db:5432/medical_db")

FRENCH_DAYS = {
    "lundi": 1,
    "mardi": 2,
    "mercredi": 3,
    "jeudi": 4,
    "vendredi": 5,
    "samedi": 6,
    "dimanche": 0,
}

# Mots français pour les heures spéciales et les nombres
TIME_WORDS = {
    "midi": 12, "minuit": 0,
    "une": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5,
    "six": 6, "sept": 7, "huit": 8, "neuf": 9, "dix": 10,
    "onze": 11, "douze": 12, "treize": 13, "quatorze": 14,
    "quinze": 15, "seize": 16, "dix-sept": 17, "dix-huit": 18,
}


def fuzzy_match_day(text: str) -> str | None:
    """Trouve le jour français le plus proche malgré les erreurs de transcription."""
    text = text.lower().strip()
    if text in FRENCH_DAYS:
        return text
    # Correspondance approximative (seuil 0.5 pour tolérer les grosses fautes)
    matches = get_close_matches(text, FRENCH_DAYS.keys(), n=1, cutoff=0.5)
    return matches[0] if matches else None


def parse_time(time_text):
    if time_text is None:
        return None
    text = str(time_text).lower().strip()

    # Vérifier les mots spéciaux (midi, minuit, quinze, etc.)
    for word, hour in TIME_WORDS.items():
        if word in text:
            return hour

    # Format HH:MM ou HHhMM
    import re
    match = re.search(r'(\d{1,2})\s*[h:]', text)
    if match:
        return int(match.group(1))

    # Nombre seul (ex: "15")
    match = re.search(r'^(\d{1,2})$', text)
    if match:
        return int(match.group(1))

    return None


def clean_doctor_name(name):
    if name is None:
        return ""
    if name.startswith("Dr. "):
        return name[4:]
    if name.startswith("Dr."):
        return name[3:]
    return name


def get_slot_id(doctor_id, day_num, hour, is_booked):
    result = db.one(
        "SELECT id FROM slots WHERE doctor_id = %s AND day_of_week = %s AND hour = %s AND is_booked = %s LIMIT 1;",
        (doctor_id, day_num, hour, is_booked),
    )
    if result:
        return result if isinstance(result, int) else result[0]
    return None


def validate_and_parse_slots(slots):
    # Nettoyer la date
    date = slots.get("date")
    if date is None:
        date = ""
    date = date.lower().strip()

    # Correspondance approximative pour tolérer les erreurs de transcription
    matched_day = fuzzy_match_day(date)
    if matched_day is None:
        raise ValueError(f"Jour invalide: {date}")
    date = matched_day

    # Valider l'heure
    hour = parse_time(slots.get("heure"))
    if hour is None:
        raise ValueError(f"Heure invalide: {slots.get('heure')}")

    # Valider le docteur
    raw_doctor_name = slots.get("praticien")
    doctor_result = db.one(
        "SELECT id FROM doctors WHERE name = %s;", (raw_doctor_name,)
    )

    # If not found, try with "Dr. " prefix
    if doctor_result is None:
        search_name = f"Dr. {raw_doctor_name}"
        doctor_result = db.one(
            "SELECT id FROM doctors WHERE name = %s;", (search_name,)
        )

    if doctor_result is None:
        raise ValueError(f"Docteur introuvable: {raw_doctor_name}")

    doctor_id = doctor_result if isinstance(doctor_result, int) else doctor_result[0]
    doctor_name = clean_doctor_name(raw_doctor_name)

    return FRENCH_DAYS[date], hour, doctor_id, doctor_name
