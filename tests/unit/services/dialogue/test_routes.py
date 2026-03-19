import pytest
from unittest.mock import patch

from services.dialogue.routes import (
    handle_appointment, 
    handle_cancel_appointment, 
    handle_emergency, 
    handle_info
)
from services.dialogue.utils import MissingInfoError

# ==========================================
# 1. FIXTURES 
# ==========================================
@pytest.fixture
def mock_validate():
    """Simule une validation parfaite pour tous les tests."""
    with patch("services.dialogue.routes.validate_and_parse_slots") as mock:
        mock.return_value = (0, 10, 1, "Maison")
        yield mock

@pytest.fixture
def mock_get_slot():
    """Simule la recherche d'un créneau en BDD (ID 42 trouvé par défaut)."""
    with patch("services.dialogue.routes.get_slot_id") as mock:
        mock.return_value = 42
        yield mock

@pytest.fixture
def mock_doctors_list():
    """Simule la récupération de la liste des médecins en BDD."""
    with patch("services.dialogue.routes.get_doctors_list") as mock:
        mock.return_value = "Dr. Dupont (Cardiologue), Dr. Martin (Dermatologue)"
        yield mock

@pytest.fixture
def mock_clinic_info():
    """Simule la récupération d'une info du cabinet en BDD."""
    with patch("services.dialogue.routes.get_clinic_info") as mock:
        mock.return_value = "123 rue de la Santé"
        yield mock


# ==========================================
# 2. TESTS : Prise de Rendez-vous
# ==========================================
def test_handle_appointment_phase_1(mock_db, mock_validate, mock_get_slot, dummy_slots):
    """Phase 1 : On demande un RDV (Pas d'écriture en base)."""
    result = handle_appointment(dummy_slots, confirmation=False)
    
    assert result["needs_confirmation"] is True
    assert "est disponible" in result["message"]
    mock_db.run.assert_not_called()

def test_handle_appointment_phase_2(mock_db, mock_validate, mock_get_slot, dummy_slots):
    """Phase 2 : L'utilisateur dit OUI (Écriture en base)."""
    result = handle_appointment(dummy_slots, confirmation=True)
    
    assert result["needs_confirmation"] is False
    assert "confirmé" in result["message"]
    assert mock_db.run.call_count == 2

def test_handle_appointment_unavailable(mock_db, mock_validate, mock_get_slot, dummy_slots):
    """Test le cas où le créneau n'existe pas ou est déjà pris."""
    mock_get_slot.return_value = None  # On écrase le comportement par défaut juste pour ce test
    
    result = handle_appointment(dummy_slots, confirmation=False)
    
    assert result["needs_confirmation"] is False
    assert "n'est pas disponible" in result["message"]

@patch("services.dialogue.routes.get_availabilities")
def test_handle_appointment_missing_info(mock_get_avail, mock_validate, mock_db, dummy_slots):
    """Cas où il manque une info (ex: heure), mais on peut proposer des dispos."""
    mock_validate.side_effect = MissingInfoError(["heure"])
    mock_get_avail.return_value = "Les premières disponibilités pour Maison sont à 14h."
    
    result = handle_appointment(dummy_slots, confirmation=False)
    
    assert "Les premières disponibilités pour Maison" in result["message"]
    assert result["needs_confirmation"] is False

def test_handle_appointment_general_exception(mock_validate, dummy_slots):
    """Test le crash total de la prise de RDV."""
    mock_validate.side_effect = Exception("Erreur système")
    result = handle_appointment(dummy_slots, confirmation=False)
    assert "Erreur de prise de rendez-vous: Erreur système" in result["message"]


# ==========================================
# 3. TESTS : Annulation
# ==========================================
def test_handle_cancel_appointment_phase_1(mock_db, mock_validate, mock_get_slot, dummy_slots):
    """Vérifie la demande d'annulation (Phase 1 : en attente de confirmation)."""
    result = handle_cancel_appointment(dummy_slots, confirmation=False)
    
    assert result["needs_confirmation"] is True
    assert "Dites 'oui' pour confirmer" in result["message"]
    mock_db.run.assert_not_called()

def test_handle_cancel_appointment_phase_2(mock_db, mock_validate, mock_get_slot, dummy_slots):
    """Vérifie la suppression réelle en base (Phase 2)."""
    result = handle_cancel_appointment(dummy_slots, confirmation=True)
    
    assert result["needs_confirmation"] is False
    assert "annulé" in result["message"]
    assert mock_db.run.call_count == 2 

def test_handle_cancel_appointment_missing_info(mock_validate, dummy_slots):
    """L'utilisateur veut annuler mais n'a pas donné l'heure."""
    mock_validate.side_effect = MissingInfoError(["heure"])
    result = handle_cancel_appointment(dummy_slots, confirmation=False)
    assert "Il me manque des informations pour annuler" in result["message"]

def test_handle_cancel_appointment_general_exception(mock_validate, dummy_slots):
    """Crash total lors de l'annulation."""
    mock_validate.side_effect = Exception("Crash base de données")
    result = handle_cancel_appointment(dummy_slots, confirmation=False)
    assert "Erreur d'annulation: Crash base de données" in result["message"]

# ==========================================
# 4. TESTS : Urgences et Infos
# ==========================================
def test_handle_emergency():
    """Vérifie que l'urgence donne bien le numéro du SAMU."""
    result = handle_emergency("au secours")
    assert "15" in result
    assert "SAMU" in result

def test_handle_info_address(mock_clinic_info):
    """Vérifie que les informations du cabinet sont bien renvoyées."""
    result = handle_info("Où est le cabinet ?", "address")
    assert "123 rue de la Santé" in result
    
def test_handle_info_specialists(mock_doctors_list):
    """Vérifie que la liste des médecins est bien renvoyée."""
    result = handle_info("Quels sont les médecins disponibles ?", "specialists")
    assert "Dr. Dupont" in result
    assert "Cardiologue" in result
    assert "Dr. Martin" in result
    assert "Dermatologue" in result

@patch("services.dialogue.routes.guess_info_type")
def test_handle_info_general_exception(mock_guess):
    """Crash total du gestionnaire d'infos."""
    mock_guess.side_effect = Exception("Erreur bizarre")
    result = handle_info("test", "unknown")
    assert "Erreur: Erreur bizarre" in result