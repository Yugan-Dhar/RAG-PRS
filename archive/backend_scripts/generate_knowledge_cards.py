import json
import os
import requests
from pathlib import Path

def generate_knowledge_cards():
    print("Starting Knowledge Card Generation...")
    base_dir = Path(__file__).parent.parent
    input_path = base_dir / "app" / "knowledge" / "data" / "itsar_router_v2.json"
    output_path = base_dir / "app" / "knowledge" / "data" / "itsar_knowledge_cards.json"
    
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    cards = {}
    
    # Iterate over sections and requirements
    for section in data.get("sections", []):
        cat = section.get("title", "")
        for req in section.get("requirements", []):
            req_id = req.get("id")
            title = req.get("title")
            text = req.get("text")
            is_manual = "undertaking" in text.lower() or "self declaration" in text.lower() or "self-declaration" in text.lower()
            
            prompt = (
                "You are an expert security compliance analyst mapping standard requirements to discrete technical concepts.\n"
                f"REQUIREMENT ID: {req_id}\n"
                f"TITLE: {title}\n"
                f"TEXT: {text}\n\n"
                "Extract the following into a valid JSON object exactly as requested. Do NOT output markdown or explanation. Output ONLY JSON.\n"
                "{\n"
                "  \"mandatory_concepts\": [\"array of 2-4 critical, non-negotiable technical requirements or features (e.g., 'SSH', 'RBAC', 'Mutual authentication')\"],\n"
                "  \"optional_concepts\": [\"array of nice-to-have but non-mandatory features\"],\n"
                "  \"prohibited_concepts\": [\"array of explicitly forbidden features if any\"],\n"
                "  \"keywords\": [\"array of 3-5 search keywords\"]\n"
                "}"
            )
            
            if not is_manual:
                print(f"Generating for {req_id}...")
                try:
                    payload = {
                        "model": "llama3.2:latest",
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.0, "num_predict": 500},
                        "format": "json"
                    }
                    resp = requests.post("http://localhost:11434/api/generate", json=payload, timeout=120)
                    resp.raise_for_status()
                    result = resp.json().get("response", "{}")
                    
                    parsed = json.loads(result)
                    mandatory = parsed.get("mandatory_concepts", [])
                    optional = parsed.get("optional_concepts", [])
                    prohibited = parsed.get("prohibited_concepts", [])
                    keywords = parsed.get("keywords", [])
                except Exception as e:
                    print(f"Failed {req_id}: {e}")
                    mandatory, optional, prohibited, keywords = [], [], [], []
            else:
                mandatory, optional, prohibited, keywords = [], [], [], []
                
            card = {
                "id": req_id,
                "title": title,
                "mandatory_concepts": mandatory,
                "optional_concepts": optional,
                "prohibited_concepts": prohibited,
                "manual_review": is_manual,
                "category": cat,
                "keywords": keywords
            }
            cards[req_id] = card
            
            # Sub requirements
            for sub in req.get("sub_requirements", []):
                sub_id = sub.get("id")
                sub_title = sub.get("title")
                sub_text = sub.get("text")
                sub_is_manual = "undertaking" in sub_text.lower() or "self declaration" in sub_text.lower()
                
                sub_prompt = (
                    "You are an expert security compliance analyst mapping standard requirements to discrete technical concepts.\n"
                    f"REQUIREMENT ID: {sub_id}\n"
                    f"TITLE: {sub_title}\n"
                    f"TEXT: {sub_text}\n\n"
                    "Extract the following into a valid JSON object exactly as requested. Do NOT output markdown or explanation. Output ONLY JSON.\n"
                    "{\n"
                    "  \"mandatory_concepts\": [\"array of 2-4 critical, non-negotiable technical requirements or features (e.g., 'SSH', 'RBAC', 'Mutual authentication')\"],\n"
                    "  \"optional_concepts\": [\"array of nice-to-have but non-mandatory features\"],\n"
                    "  \"prohibited_concepts\": [\"array of explicitly forbidden features if any\"],\n"
                    "  \"keywords\": [\"array of 3-5 search keywords\"]\n"
                    "}"
                )
                
                if not sub_is_manual:
                    print(f"Generating for {sub_id}...")
                    try:
                        payload = {
                            "model": "llama3.2:latest",
                            "prompt": sub_prompt,
                            "stream": False,
                            "options": {"temperature": 0.0, "num_predict": 500},
                            "format": "json"
                        }
                        resp = requests.post("http://localhost:11434/api/generate", json=payload, timeout=120)
                        resp.raise_for_status()
                        result = resp.json().get("response", "{}")
                        
                        parsed = json.loads(result)
                        sub_mandatory = parsed.get("mandatory_concepts", [])
                        sub_optional = parsed.get("optional_concepts", [])
                        sub_prohibited = parsed.get("prohibited_concepts", [])
                        sub_keywords = parsed.get("keywords", [])
                    except Exception as e:
                        print(f"Failed {sub_id}: {e}")
                        sub_mandatory, sub_optional, sub_prohibited, sub_keywords = [], [], [], []
                else:
                    sub_mandatory, sub_optional, sub_prohibited, sub_keywords = [], [], [], []
                    
                sub_card = {
                    "id": sub_id,
                    "title": sub_title,
                    "mandatory_concepts": sub_mandatory,
                    "optional_concepts": sub_optional,
                    "prohibited_concepts": sub_prohibited,
                    "manual_review": sub_is_manual,
                    "category": cat,
                    "keywords": sub_keywords
                }
                cards[sub_id] = sub_card
                
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(cards, f, indent=2)
        
    print("Done generating knowledge cards!")

if __name__ == "__main__":
    generate_knowledge_cards()
