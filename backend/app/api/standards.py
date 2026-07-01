from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_db
from app.models.standard import Standard, Framework
from app.models.requirement import Requirement
from app.schemas.standard import StandardRead, FrameworkRead, RequirementRead

router = APIRouter()

@router.get("/standards", response_model=List[StandardRead])
async def get_standards(db: AsyncSession = Depends(get_db)):
    from sqlalchemy.orm import selectinload
    result = await db.execute(select(Standard).options(selectinload(Standard.frameworks)))
    standards = result.scalars().all()
    # Dummy mock for now, assuming empty DB
    if not standards:
        return [StandardRead(id="ITSAR", name="Indian Telecom Security Assurance Requirements", version="2.0")]
    return standards

@router.get("/standards/{standard_id}/frameworks", response_model=List[FrameworkRead])
async def get_frameworks(standard_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Framework).where(Framework.standard_id == standard_id))
    frameworks = result.scalars().all()
    if not frameworks:
        if standard_id == "ITSAR":
            return [
                FrameworkRead(id="ITSAR-ROUTER", standard_id="ITSAR", name="IP Router", description="IP Router security requirements", equipment_type="ip_router"),
                FrameworkRead(id="ITSAR-LAN", standard_id="ITSAR", name="LAN Switch", description="LAN Switch security requirements", equipment_type="lan_switch")
            ]
        raise HTTPException(status_code=404, detail="Standard not found")
    return frameworks

@router.get("/frameworks/{framework_id}/requirements", response_model=List[RequirementRead])
async def get_requirements(framework_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Requirement).where(Requirement.framework_id == framework_id))
    requirements = result.scalars().all()
    return requirements
