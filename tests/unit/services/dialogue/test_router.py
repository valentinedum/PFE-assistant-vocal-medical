from unittest.mock import patch, MagicMock
from services.dialogue.router import run_dialogue_logic
import pytest
import json

# ==========================================
# 1. FIXTURES 
# ==========================================
@pytest.fixture
def mock_router_deps():
    """Prépare les dépendances et FORCE le remplacement dans le dictionnaire de routage."""
    with patch("services.dialogue.router.handle_emergency") as m_emerg, \
         patch("services.dialogue.router.handle_info") as m_info, \
         patch("services.dialogue.router.handle_appointment") as m_appo, \
         patch("services.dialogue.router.extract_confirmation") as m_conf, \
         patch("services.dialogue.router.extract_clinic_info") as m_ext_info, \
         patch("services.dialogue.router.extract_slots_with_ollama") as m_extract :
        
        # On redéfinit le dictionnaire de handlers pour s'assurer que nos mocks sont utilisés
        new_handlers = {
            "book_appointment": m_appo,
            "medical_urgency": m_emerg,
        }
        
        with patch.dict("services.dialogue.router.ACTION_HANDLERS", new_handlers, clear=False):
            yield {
                "emergency": m_emerg,
                "info": m_info,
                "appointment": m_appo,
                "confirmation": m_conf,
                "clinic_info": m_ext_info,
                "extract_slots": m_extract
            }

# ==========================================
# 2. TESTS : Logique de Routage simple
# ==========================================
def test_router_emergency(mock_router_deps):
    """Test simple : L'urgence."""
    mock_router_deps["emergency"].return_value = "Appelez le 15"
    
    result = run_dialogue_logic("J'ai mal", intent="medical_urgency")
    
    assert result["response"] == "Appelez le 15"
    assert result["context"] is None

def test_router_info(mock_router_deps):
    """Test simple : L'info."""
    mock_router_deps["clinic_info"].return_value = {"requested_info": "adress"}
    mock_router_deps["info"].return_value = "Le cabinet est ouvert de 9h à 18h"
    
    result = run_dialogue_logic("Quels sont vos horaires ?", intent="info_practical")
    
    assert result["response"] == "Le cabinet est ouvert de 9h à 18h"
    assert result["context"] is None

def test_router_off_topic(mock_router_deps):
    """Test simple : Un intent non géré."""
    result = run_dialogue_logic("Je veux parler de la météo", intent="off_topic")
    
    assert "Désolé, je ne suis pas sûr de comprendre" in result["response"]
    assert result["context"] is None

# ==========================================
# 3. TESTS : Logique de confirmation (le cœur du routeur)
# ==========================================
def test_router_confirm_yes(mock_router_deps, dummy_slots):
    """On vérifie que le 'Oui' valide bien le contexte."""
    context = json.dumps({"type": "book_appointment", "slots": dummy_slots})
    mock_router_deps["confirmation"].return_value = {"confirmation": "oui"}
    mock_router_deps["appointment"].return_value = {"message": "RDV OK", "needs_confirmation": False}
    
    result = run_dialogue_logic("Oui", intent="handle_appointment", context_json=context)
    
    assert "RDV OK" in result["response"]
    assert result["context"] is None

def test_router_confirm_no(mock_router_deps):
    """On vérifie que le 'Non' annule tout."""
    context = json.dumps({"type": "book_appointment", "slots": {}})
    mock_router_deps["confirmation"].return_value = {"confirmation": "non"}
    
    result = run_dialogue_logic("Non", intent=any, context_json=context)
    
    assert "non confirmé" in result["response"].lower()
    assert result["context"] is None

def test_router_confirm_invalid(mock_router_deps):
    """On vérifie que les confirmations invalides ne cassent pas le contexte."""
    context = json.dumps({"type": "book_appointment", "slots": {}})
    mock_router_deps["confirmation"].return_value = {"confirmation": "peut-être"}
    
    result = run_dialogue_logic("Peut-être", intent=any, context_json=context)
    
    assert "Je n'ai pas compris votre confirmation" in result["response"]
    assert result["context"] == context  # Le contexte doit être conservé pour une nouvelle tentative de confirmation

def test_router_request_needs_confirmation(mock_router_deps, dummy_slots):
    """
    Test de la PHASE 1 : L'utilisateur demande un RDV.
    Le routeur doit renvoyer une demande de confirmation ET un contexte JSON.
    """
    mock_router_deps["extract_slots"].return_value = dummy_slots
    mock_router_deps["appointment"].return_value = {
        "message": "Souhaitez-vous confirmer pour lundi à 10h ?",
        "needs_confirmation": True  
    }
    
    result = run_dialogue_logic("Je veux un RDV lundi", intent="book_appointment")

    assert "Souhaitez-vous confirmer" in result["response"]
    assert result["context"] == json.dumps({"type": "book_appointment", "slots": dummy_slots})
