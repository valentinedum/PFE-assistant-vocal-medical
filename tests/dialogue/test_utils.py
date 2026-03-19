import sys
import os
import pytest
from unittest.mock import patch, MagicMock

from services.dialogue.utils import (
    fuzzy_match_day, parse_time, clean_doctor_name, validate_and_parse_slots, get_slot_id, MissingInfoError,
    find_doctor_id, get_doctors_list, get_clinic_info, guess_info_type,
    FRENCH_DAYS, INFO_KEYWORD_MAP, TIME_WORDS
)

def test_fuzzy_match_day():
    assert fuzzy_match_day("luni") == "lundi"
    assert fuzzy_match_day("mardii") == "mardi"
    assert fuzzy_match_day("mercredi ") == "mercredi"
    assert fuzzy_match_day("Rendez-vous") not in FRENCH_DAYS

def test_parse_time():
    assert parse_time("14h") == 14
    assert parse_time("Midi") == 12
    assert parse_time("minuit ") == 0
    assert parse_time("invalid") is None

def test_clean_doctor_name():
    assert clean_doctor_name("Dr. Dupont") == "Dupont"
    assert clean_doctor_name("Dr. dupont") == "Dupont"
    assert clean_doctor_name(None) == ""

def test_get_slot_id(mock_db):
    mock_db.one.side_effect = [1, None] 
    assert get_slot_id(1, 1, 10, False) == 1
    assert get_slot_id(1, 1, 10, True) == None

def test_guess_info_type():
    assert guess_info_type("Quelle est votre adresse ?") == "address"
    assert guess_info_type("Quels sont vos horaires d'ouverture ?") == "hours"
    assert guess_info_type("Quel est votre numéro de téléphone ?") == "phone"
    assert guess_info_type("Quel est le coût d'une consultation ?") == "price"
    assert guess_info_type("Y a-t-il un parking à proximité ?") == "parking"
    assert guess_info_type("Je voudrais des informations sur les médecins.") == "specialists"

@patch("services.dialogue.utils.find_doctor_id")
def test_validate_slots_success(mock_find_doctor, mock_db):
    mock_find_doctor.return_value = 1
    mock_db.all.return_value = ["Maison"]
    slots = {"date": "lundi", "heure": "10:00", "praticien": "Maison"}
    day_num, hour, doc_id, doc_name = validate_and_parse_slots(slots)
    assert day_num == 1  
    assert hour == 10
    assert doc_id == 1
    assert doc_name == "Maison"