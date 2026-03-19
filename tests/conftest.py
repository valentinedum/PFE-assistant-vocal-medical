import pytest
from unittest.mock import MagicMock, patch

@pytest.fixture
def mock_db():
    mock_db = MagicMock()
    with patch("services.dialogue.utils.get_db", return_value=mock_db):
        yield mock_db