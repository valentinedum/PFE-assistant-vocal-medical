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

TIME_WORDS = {
    "midi": 12, "minuit": 0,
    "une": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5,
    "six": 6, "sept": 7, "huit": 8, "neuf": 9, "dix": 10,
    "onze": 11, "douze": 12, "treize": 13, "quatorze": 14,
    "quinze": 15, "seize": 16, "dix-sept": 17, "dix-huit": 18,
}

INFO_KEYWORD_MAP = {
    "horaire": "hours", "heure": "hours", "ouvert": "hours",
    "adresse": "address", "où": "address", "situe": "address",
    "téléphone": "phone", "numéro": "phone", "appeler": "phone",
    "tarif": "price", "prix": "price", "coût": "price",
    "parking": "parking", "garer": "parking",
    "médecin": "specialists", "docteur": "specialists", "équipe": "specialists",
}


def fuzzy_match_day(text: str) -> str | None:
    """Trouve le jour français le plus proche malgré les erreurs de transcription."""
    text = text.lower().strip()
    if text in FRENCH_DAYS:
        return text
    matches = get_close_matches(text, FRENCH_DAYS.keys(), n=1, cutoff=0.7)
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
        name = name[4:]
    elif name.startswith("Dr."):
        name = name[3:]
    return name.capitalize()


def get_slot_id(doctor_id, day_num, hour, is_booked):
    result = db.one(
        "SELECT id FROM slots WHERE doctor_id = %s AND day_of_week = %s AND hour = %s AND is_booked = %s LIMIT 1;",
        (doctor_id, day_num, hour, is_booked),
    )
    if result:
        return result if isinstance(result, int) else result[0]
    return None

def find_doctor_id(name):
    for search in [name, f"Dr. {name}"]:
        result = db.one("SELECT id FROM doctors WHERE LOWER(name) = LOWER(%s);", (search,))
        if result:
            return result if isinstance(result, int) else result[0]
    return None


def get_doctors_list():
    doctors = db.all("SELECT name, specialty FROM doctors;")
    if not doctors:
        return None
    return ", ".join([
        f"{d.name if hasattr(d, 'name') else d[0]} ({d.specialty if hasattr(d, 'specialty') else d[1]})"
        for d in doctors
    ])


def get_clinic_info(key):
    result = db.one("SELECT value FROM clinic_info WHERE key = %s;", (key,))
    if result:
        return result if isinstance(result, str) else result[0]
    return None


def guess_info_type(text):
    text_lower = text.lower()
    for keyword, info_type in INFO_KEYWORD_MAP.items():
        if keyword in text_lower:
            return info_type
    return None



class MissingInfoError(Exception):
    """Erreur levée quand des infos sont manquantes pour un RDV."""
    def __init__(self, missing_fields: list[str]):
        self.missing_fields = missing_fields
        super().__init__(", ".join(missing_fields))


def validate_and_parse_slots(slots):
    missing = []

    # Jour
    date_raw = (slots.get("date") or "").lower().strip()
    matched_day = fuzzy_match_day(date_raw) if date_raw else None
    if not matched_day:
        missing.append("le jour (lundi, mardi, etc.)")

    # Heure
    hour = parse_time(slots.get("heure"))
    if hour is None:
        missing.append("l'heure (ex: 14h, midi)")

    # Docteur
    name = (slots.get("praticien") or "").strip()
    doctor_id = None
    if not name:
        missing.append("le nom du médecin")
    else:
        doctor_id = find_doctor_id(name)
        if doctor_id is None:
            rows = db.all("SELECT name FROM doctors;")
            noms = ", ".join([r if isinstance(r, str) else r[0] for r in rows])
            missing.append(f"le nom du médecin (disponibles : {noms})")

    if missing:
        raise MissingInfoError(missing)

    return FRENCH_DAYS[matched_day], hour, doctor_id, clean_doctor_name(name)
