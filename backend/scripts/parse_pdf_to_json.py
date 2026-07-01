import json
import re
from pathlib import Path

def parse_requirements(text):
    text = text.replace('\r\n', '\n')
    lines = text.split('\n')
    
    sections = {}
    current_sec_id = None
    
    current_req_id = None
    current_req_title = None
    current_req_body = []
    
    in_requirement_body = False
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
            
        # Match section e.g. "Section 2.1: Access and Authorization"
        sec_match = re.match(r'^Section\s+(\d+\.\d+):\s*(.*)$', line)
        if sec_match:
            sec_id = sec_match.group(1)
            sec_title = sec_match.group(2).strip()
            current_sec_id = sec_id
            sections[sec_id] = {
                "id": sec_id,
                "title": sec_title,
                "requirements": []
            }
            in_requirement_body = False
            continue
            
        # Match requirement title e.g. "2.1.1 Authentication for..."
        # But only if it's followed by "Requirement:" on the next line or two
        req_match = re.match(r'^(\d+\.\d+\.\d+(?:\.\d+)?)\s+(.+)$', line)
        if req_match:
            # Check if "Requirement:" is on the next line
            if i + 1 < len(lines) and "Requirement:" in lines[i+1]:
                # Save previous requirement
                if current_req_id and current_sec_id:
                    body_text = '\n'.join(current_req_body).strip()
                    sections[current_sec_id]["requirements"].append({
                        "id": current_req_id,
                        "title": current_req_title,
                        "text": body_text,
                        "keywords": current_req_title.split() + body_text.split()[:20]
                    })
                
                # Start new requirement
                current_req_id = req_match.group(1)
                current_req_title = req_match.group(2).strip()
                current_req_body = []
                in_requirement_body = False
                
                # Determine section if current_sec_id is None or mismatched
                parts = current_req_id.split('.')
                sec_id = f"{parts[0]}.{parts[1]}"
                if sec_id not in sections:
                    sections[sec_id] = {
                        "id": sec_id,
                        "title": f"Section {sec_id}",
                        "requirements": []
                    }
                current_sec_id = sec_id
                continue

        if line == "Requirement:":
            in_requirement_body = True
            continue
            
        if in_requirement_body and current_req_id:
            # Stop if we hit something that looks like the next section or [Ref: ...]
            if line.startswith('Section ') and ':' in line:
                pass # Handled by sec_match
            # We can include references in the body text or stop at them. Let's include them.
            current_req_body.append(line)
            
    # Save the last requirement
    if current_req_id and current_sec_id:
        body_text = '\n'.join(current_req_body).strip()
        sections[current_sec_id]["requirements"].append({
            "id": current_req_id,
            "title": current_req_title,
            "text": body_text,
            "keywords": current_req_title.split() + body_text.split()[:20]
        })
        
    return list(sections.values())

with open('scripts/ocr_text.txt', 'r', encoding='utf-8') as f:
    text = f.read()

sections = parse_requirements(text)

final_sections = [s for s in sections if len(s["requirements"]) > 0]

out_data = {
    "id": "ITSAR-ROUTER",
    "name": "ITSAR for IP Router v2.0",
    "description": "Indian Telecom Security Assurance Requirements for IP Routers",
    "sections": final_sections
}

out_path = Path(r"C:\Users\yugan.dhar\OneDrive - Incedo Technology Solutions Ltd\Documents\RAG PRS\backend\app\knowledge\data\itsar_router_v2.json")
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(out_data, f, indent=2)
    
print(f"Successfully wrote {len(final_sections)} sections to JSON")
for s in final_sections:
    print(f" - {s['id']}: {len(s['requirements'])} requirements")

total_reqs = sum(len(s["requirements"]) for s in final_sections)
print(f"\nTotal requirements extracted: {total_reqs}")
