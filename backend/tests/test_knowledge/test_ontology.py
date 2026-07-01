import pytest
from pathlib import Path
from app.knowledge.ontology import SecurityOntology, get_ontology

def test_ssh_expands_to_authentication():
    ontology = get_ontology()
    expansion = ontology.expand("ssh")
    expanded_labels = [label for label, weight in expansion.expanded_concepts]
    assert "Authentication" in expanded_labels

def test_tls_expands_to_encryption():
    ontology = get_ontology()
    expansion = ontology.expand("tls")
    expanded_labels = [label for label, weight in expansion.expanded_concepts]
    assert "Encryption" in expanded_labels

def test_resolve_alias():
    ontology = get_ontology()
    assert ontology.resolve("secure shell") == "ssh"
    assert ontology.resolve("TLS 1.3") == "tls"
    assert ontology.resolve("Nonexistent") is None

def test_are_related_ssh_management_plane():
    ontology = get_ontology()
    # SSH -> Remote Administration -> Management Plane (2 hops = related)
    assert ontology.are_related("ssh", "management plane") is True
    # Unrelated test
    assert ontology.are_related("ssh", "secure_boot") is False
