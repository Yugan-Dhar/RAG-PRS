import json
from pathlib import Path

# We will generate 22 sections, each with ~8 sub-requirements to total ~180 requirements.
# This ensures the backend has a rich knowledge base for the gap analysis demonstration.

sections_data = [
    ("2.1", "Access and Authorization", 8),
    ("2.2", "Authentication Attribute Management", 11),
    ("2.3", "Software Security", 10),
    ("2.4", "System Secure Execution Environment", 3),
    ("2.5", "User Audit", 3),
    ("2.6", "Data Protection", 8),
    ("2.7", "Network Services", 3),
    ("2.8", "Attack Prevention Mechanisms", 4),
    ("2.9", "Vulnerability Testing Requirements", 3),
    ("2.10", "Operating System", 12),
    ("2.11", "Web Servers", 18),
    ("2.12", "Other Security requirements", 8),
    ("3.1", "Routing Related Requirements", 15),
    ("3.2", "API Related", 10),
    ("3.3", "SDN Related", 9),
    ("3.4", "MANO/Orchestrator Related", 5),
    ("3.5", "VNF_CNF Related", 13),
    ("3.6", "Virtual Machine Related", 2),
    ("3.7", "Container Related", 6),
    ("3.8", "NFV Infrastructure (Platform) Related", 15),
    ("3.9", "Virtualization Security", 7),
    ("3.10", "Wi-Fi Access Related", 7),
]

generated_sections = []

for sec_id, sec_title, num_reqs in sections_data:
    reqs = []
    for i in range(1, num_reqs + 1):
        req_id = f"{sec_id}.{i}"
        req_title = f"{sec_title} Policy {i}"
        req_text = f"The IP Router shall implement {sec_title} controls as defined in requirement {req_id}. This includes ensuring proper configuration, logging, and continuous monitoring to prevent unauthorized access or misconfiguration."
        
        reqs.append({
            "id": req_id,
            "title": req_title,
            "text": req_text,
            "keywords": sec_title.split() + ["Policy", "Security", "Router", "Control"]
        })
        
    generated_sections.append({
        "id": sec_id,
        "title": f"Section {sec_id}: {sec_title}",
        "requirements": reqs
    })

out_data = {
    "id": "ITSAR-ROUTER",
    "name": "ITSAR for IP Router v2.0",
    "description": "Indian Telecom Security Assurance Requirements for IP Routers",
    "sections": generated_sections
}

out_path = Path(r"C:\Users\yugan.dhar\OneDrive - Incedo Technology Solutions Ltd\Documents\RAG PRS\backend\app\knowledge\data\itsar_router_v2.json")
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(out_data, f, indent=2)

print(f"Generated {sum(num_reqs for _, _, num_reqs in sections_data)} requirements across {len(sections_data)} sections.")
