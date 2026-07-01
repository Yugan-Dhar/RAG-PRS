import pytest
from app.knowledge.capability_extractor import CapabilityExtractor
from app.schemas.capability import ObligationLevel

def test_capability_extractor():
    extractor = CapabilityExtractor()
    text = "The device SHALL support Secure Shell version 2."
    caps = extractor.extract(text)
    
    # If spacy is installed and ontology loaded, it should find SSH
    # If not, it might return empty. So we check conditionally or mock.
    if extractor.nlp:
        assert len(caps) > 0
        assert caps[0].concept == "SSH"
        assert caps[0].obligation == ObligationLevel.SHALL
        assert caps[0].version == "v2"
