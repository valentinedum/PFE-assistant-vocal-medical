import pytest
from unittest.mock import patch, MagicMock

from services.dialogue.utils import (
    fuzzy_match_day, parse_time, clean_doctor_name, validate_and_parse_slots,
    get_slot_id, find_doctor_id, get_doctors_list, get_clinic_info,
    guess_info_type, get_availabilities, MissingInfoError
)

# ==========================================
# 1. FIXTURES
# ==========================================
@pytest.fixture
def mock_find_doctor():
    """Simule la recherche d'ID de docteur pour isoler la validation."""
    with patch("services.dialogue.utils.find_doctor_id") as mock:
        mock.return_value = 1
        yield mock


# ==========================================
# 2. TESTS : Sans accès à la base de données (logique pure)
# ==========================================
def test_fuzzy_match_day():
    """Vérifie la reconnaissance des jours, même avec des fautes."""
    assert fuzzy_match_day("luni") == "lundi"
    assert fuzzy_match_day("mardii") == "mardi"
    assert fuzzy_match_day("mercredi ") == "mercredi"
    assert fuzzy_match_day("Rendez-vous") is None
    assert fuzzy_match_day("") is None

def test_parse_time():
    """Vérifie l'extraction des heures depuis différents formats."""
    assert parse_time("14h") == 14
    assert parse_time("14:00") == 14
    assert parse_time("15") == 15
    assert parse_time("Midi") == 12
    assert parse_time("minuit ") == 0
    assert parse_time("invalid") is None
    assert parse_time(None) is None

def test_clean_doctor_name():
    """Vérifie le nettoyage du préfixe 'Dr.'."""
    assert clean_doctor_name("Dr. Dupont") == "Dupont"
    assert clean_doctor_name("Dr. dupont") == "Dupont"
    assert clean_doctor_name("Maison") == "Maison"
    assert clean_doctor_name(None) == ""

def test_guess_info_type():
    """Vérifie que les mots-clés renvoient la bonne intention."""
    assert guess_info_type("Quelle est votre adresse ?") == "address"
    assert guess_info_type("Quels sont vos horaires d'ouverture ?") == "hours"
    assert guess_info_type("Quel est le coût ?") == "price"
    assert guess_info_type("Je veux un rendez-vous") is None


# ==========================================
# 3. TESTS : Avec accès à la base de données (simulé via un mock)
# ==========================================
def test_get_slot_id_success(mock_db):
    """Le créneau existe en BDD."""
    mock_db.one.return_value = 42
    assert get_slot_id(1, 1, 10, False) == 42

def test_get_slot_id_not_found(mock_db):
    """Le créneau n'existe pas."""
    mock_db.one.return_value = None
    assert get_slot_id(1, 1, 10, True) is None

def test_find_doctor_id(mock_db):
    """Recherche un médecin (teste le 1er échec puis le succès avec 'Dr.')."""
    mock_db.one.side_effect = [None, 1] 
    assert find_doctor_id("Dupont") == 1
    assert mock_db.one.call_count == 2

def test_get_doctors_list(mock_db):
    """Formatage réussi de la liste des médecins."""
    class FakeDoc:
        def __init__(self): 
            self.name = "Dupont"
            self.specialty = "Généraliste"
            
    mock_db.all.return_value = [FakeDoc()]
    assert get_doctors_list() == "Dupont (Généraliste)"

def test_get_clinic_info(mock_db):
    """Récupère une info du cabinet."""
    mock_db.one.return_value = "123 rue de la Santé"
    assert get_clinic_info("address") == "123 rue de la Santé"


# ==========================================
# 4. TESTS : Validation des Créneaux
# ==========================================
def test_validate_slots_success(mock_find_doctor, mock_db, dummy_slots):
    """Scénario nominal : toutes les infos sont présentes."""
    day_num, hour, doc_id, doc_name = validate_and_parse_slots(dummy_slots)
    
    assert day_num == 1
    assert hour == 10
    assert doc_id == 1
    assert doc_name == "Maison"

def test_validate_slots_missing_day(mock_db, dummy_slots):
    del dummy_slots["date"]
    with pytest.raises(MissingInfoError) as exc:
        validate_and_parse_slots(dummy_slots)
    assert "jour" in str(exc.value)

def test_validate_slots_missing_time(mock_db, dummy_slots):
    del dummy_slots["heure"]
    with pytest.raises(MissingInfoError) as exc:
        validate_and_parse_slots(dummy_slots)
    assert "heure" in str(exc.value)

def test_validate_slots_missing_doctor(mock_db, dummy_slots):
    del dummy_slots["praticien"]
    with pytest.raises(MissingInfoError) as exc:
        validate_and_parse_slots(dummy_slots)
    assert "nom du médecin" in str(exc.value)

def test_validate_slots_unknown_doctor(mock_find_doctor, mock_db):
    """Le médecin demandé n'existe pas, la BDD liste les dispos."""
    mock_find_doctor.return_value = None
    mock_db.all.return_value = [("Maison",), ("Dupont",)] 
    
    slots = {"date": "lundi", "heure": "10h", "praticien": "Inconnu"}
    
    with pytest.raises(MissingInfoError) as exc:
        validate_and_parse_slots(slots)
    
    assert "Maison" in str(exc.value)
    assert "Dupont" in str(exc.value)


# ==========================================
# 5. TESTS : Recherche de Disponibilités
# ==========================================
def test_get_availabilities_unknown_doc(mock_find_doctor, mock_db):
    """Filtre sur un médecin inexistant."""
    mock_find_doctor.return_value = None
    assert get_availabilities({"praticien": "Inconnu"}) is None

def test_get_availabilities_empty_db(mock_find_doctor, mock_db):
    """Aucun créneau dans la base."""
    mock_db.all.return_value = []
    assert get_availabilities({"praticien": "Maison", "date": "lundi"}) is None

@pytest.mark.parametrize("slots, db_results, expected_words", [
    # 1. On a le médecin ET la date
    ({"praticien": "Maison", "date": "lundi"}, [("Maison", 1, 10)], ["Maison", "lundi", "10h"]),
    # 2. On n'a QUE le médecin
    ({"praticien": "Maison"}, [("Maison", 1, 10), ("Maison", 2, 9)], ["lundi", "mardi"]),
    # 3. On n'a QUE la date
    ({"date": "lundi"}, [("Maison", 1, 10), ("Dupont", 1, 9)], ["Maison", "Dupont"])
])

def test_get_availabilities_formats(mock_find_doctor, mock_db, slots, db_results, expected_words):
    """Teste les 3 façons différentes de formater la phrase de réponse."""
    mock_db.all.return_value = db_results
    result = get_availabilities(slots)
    for word in expected_words:
        assert word in result