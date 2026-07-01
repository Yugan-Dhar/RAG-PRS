import pytest
from app.ingestion.standards.itsar_adapter import ITSARAdapter

def test_itsar_adapter_load_framework(tmp_path):
    # Create mock JSON
    data_dir = tmp_path / "frameworks"
    data_dir.mkdir()
    
    mock_json = data_dir / "itsar_ip_router.json"
    mock_json.write_text('{"requirements": [{"req_id": "R1", "text": "SSH shall be supported."}]}')
    
    adapter = ITSARAdapter(data_dir=str(data_dir))
    reqs = adapter.load_framework("ITSAR", "ITSAR-ROUTER")
    
    assert len(reqs) == 1
    assert reqs[0]["req_id"] == "R1"
    
def test_itsar_adapter_invalid_standard():
    adapter = ITSARAdapter()
    with pytest.raises(ValueError):
        adapter.load_framework("NIST", "xyz")
