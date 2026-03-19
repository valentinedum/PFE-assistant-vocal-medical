import pytest
import sys
from unittest.mock import MagicMock, patch

mock_postgres = MagicMock()
sys.modules['postgres'] = mock_postgres

@pytest.fixture
def dummy_slots():
    """Données de test standard disponibles pour tous les fichiers."""
    return {"date": "lundi", "heure": "10:00", "praticien": "Maison"}

@pytest.fixture
def mock_db():
    """Intercepte get_db partout où il a été importé."""
    mock_instance = MagicMock()
    
    with patch("services.dialogue.utils.get_db", return_value=mock_instance), \
         patch("services.dialogue.routes.get_db", return_value=mock_instance):
        
        yield mock_instance

@pytest.fixture
def mock_ollama():
    """Crée un mock universel pour le client instructor d'Ollama."""
    with patch("services.extraction.ollama_client.get_instructor_client") as mock_get:
        client = MagicMock()
        mock_get.return_value = client
        yield client