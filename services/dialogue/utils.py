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


def parse_time(time_text):
    if time_text is None:
        return None
    text = str(time_text).lower()
    for i in range(len(text)):
        if text[i] in ["h", ":"]:
            return int(text[:i])
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
    date = date.lower()

    if date not in FRENCH_DAYS:
        raise ValueError(f"Jour invalide: {date}")

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
