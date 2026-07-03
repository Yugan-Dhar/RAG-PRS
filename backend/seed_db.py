import json
import asyncio
from app.database import AsyncSessionLocal
from app.models.standard import Standard, Framework
from app.models.requirement import Requirement

async def seed():
    async with AsyncSessionLocal() as db:
        # Check if already seeded
        # ...
        
        s = Standard(id="ITSAR", name="Indian Telecom Security Assurance Requirements", version="2.0")
        db.add(s)
        
        f = Framework(id="ITSAR-ROUTER", standard_id="ITSAR", name="IP Router", description="IP Router", equipment_type="ip_router")
        db.add(f)
        
        f2 = Framework(id="ITSAR-LAN", standard_id="ITSAR", name="LAN Switch", description="LAN Switch", equipment_type="lan_switch")
        db.add(f2)
        
        with open("app/knowledge/data/itsar_router_v2.json", encoding="utf-8") as file:
            data = json.load(file)
            
        for sec in data.get("sections", []):
            for req in sec.get("requirements", []):
                r = Requirement(
                    framework_id="ITSAR-ROUTER",
                    req_id=req["id"],
                    parent_req_id=None,
                    chapter=sec.get("chapter", "CSR"),
                    section_number=sec["id"],
                    section_title=sec["title"],
                    title=req.get("title", ""),
                    obligation_level=req.get("obligation", "SHALL"),
                    text=req.get("text", ""),
                    applicable_router_types=req.get("applicable_router_types", []),
                    required_capability_flags=req.get("required_capability_flags", []),
                    evidence_type=req.get("evidence_type", "technical"),
                    is_prohibition=req.get("is_prohibition", False),
                    compliance_by_undertaking=req.get("compliance_by_undertaking", False),
                    keywords=req.get("keywords", []),
                    cross_references=req.get("cross_references", [])
                )
                db.add(r)
                
                for sub in req.get("sub_requirements", []):
                    sr = Requirement(
                        framework_id="ITSAR-ROUTER",
                        req_id=sub["id"],
                        parent_req_id=req["id"],
                        chapter=sec.get("chapter", "CSR"),
                        section_number=sec["id"],
                        section_title=sec["title"],
                        title=sub.get("title", ""),
                        obligation_level=sub.get("obligation", "SHALL"),
                        text=sub.get("text", ""),
                        applicable_router_types=sub.get("applicable_router_types", []),
                        required_capability_flags=sub.get("required_capability_flags", []),
                        evidence_type=sub.get("evidence_type", "technical"),
                        is_prohibition=sub.get("is_prohibition", False),
                        compliance_by_undertaking=sub.get("compliance_by_undertaking", False),
                        keywords=sub.get("keywords", []),
                        cross_references=sub.get("cross_references", [])
                    )
                    db.add(sr)
                    
        with open("app/knowledge/data/itsar_lan_switch_v1.json", encoding="utf-8") as file:
            data_lan = json.load(file)
            
        for sec in data_lan.get("sections", []):
            for req in sec.get("requirements", []):
                r = Requirement(
                    framework_id="ITSAR-LAN",
                    req_id=req["id"],
                    parent_req_id=None,
                    chapter=sec.get("chapter", "CSR"),
                    section_number=sec["id"],
                    section_title=sec["title"],
                    title=req.get("title", ""),
                    obligation_level=req.get("obligation", "SHALL"),
                    text=req.get("text", ""),
                    applicable_router_types=req.get("applicable_router_types", []),
                    required_capability_flags=req.get("required_capability_flags", []),
                    evidence_type=req.get("evidence_type", "technical"),
                    is_prohibition=req.get("is_prohibition", False),
                    compliance_by_undertaking=req.get("compliance_by_undertaking", False),
                    keywords=req.get("keywords", []),
                    cross_references=req.get("cross_references", [])
                )
                db.add(r)
                
                for sub in req.get("sub_requirements", []):
                    sr = Requirement(
                        framework_id="ITSAR-LAN",
                        req_id=sub["id"],
                        parent_req_id=req["id"],
                        chapter=sec.get("chapter", "CSR"),
                        section_number=sec["id"],
                        section_title=sec["title"],
                        title=sub.get("title", ""),
                        obligation_level=sub.get("obligation", "SHALL"),
                        text=sub.get("text", ""),
                        applicable_router_types=sub.get("applicable_router_types", []),
                        required_capability_flags=sub.get("required_capability_flags", []),
                        evidence_type=sub.get("evidence_type", "technical"),
                        is_prohibition=sub.get("is_prohibition", False),
                        compliance_by_undertaking=sub.get("compliance_by_undertaking", False),
                        keywords=sub.get("keywords", []),
                        cross_references=sub.get("cross_references", [])
                    )
                    db.add(sr)
        
        await db.commit()
        print("Database seeded!")

asyncio.run(seed())
