from services.extraction.ollama_client import extract_slots_with_ollama, extract_clinic_info, extract_confirmation

def test_extract_slots_nominal(mock_ollama, dummy_slots):
    """Test classique : l'IA extrait bien les infos."""
    mock_ollama.chat.completions.create.return_value.dict.return_value = dummy_slots

    result = extract_slots_with_ollama("Je voudrais un rendez-vous lundi à 10h avec le docteur Maison")

    assert result["date"] == "lundi"
    assert result["heure"] == "10:00"
    assert result["praticien"] == "Maison"

def test_extract_slots_security_hallucination(mock_ollama):
    """Test de sécurité : l'IA invente un jour absent du texte."""
    mock_ollama.chat.completions.create.return_value.dict.return_value = {
        "date": "lundi", "heure": None, "praticien": None
    }

    result = extract_slots_with_ollama("Je veux un rendez-vous")

    assert result["date"] is None
    assert result["heure"] is None

def test_ollama_slots_exception(mock_ollama):
    """Vérifie que si Ollama crash, le code renvoie du vide au lieu de planter."""
    mock_ollama.chat.completions.create.side_effect = Exception("Ollama Timeout")
    
    result = extract_slots_with_ollama("RDV demain")
    
    assert result == {"date": None, "heure": None, "praticien": None}

def test_ollama_extract_clinic_info(mock_ollama):
    """Vérifie que l'extraction d'infos du cabinet fonctionne."""
    mock_ollama.chat.completions.create.return_value.dict.return_value = {"requested_info": "address"}
    
    result = extract_clinic_info("Où est le cabinet ?")
    
    assert result["requested_info"] == "address"

def test_extract_confirmation(mock_ollama):
    """Vérifie l'extraction du oui/non."""
    mock_ollama.chat.completions.create.return_value.dict.return_value = {"confirmation": "oui"}
    
    result = extract_confirmation("Oui c'est parfait")
    
    assert result["confirmation"] == "oui"