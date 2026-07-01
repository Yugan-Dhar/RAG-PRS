from pydantic import BaseModel

class RequirementBase(BaseModel):
    req_id: str
    category: str
    section: str | None = None
    obligation_level: str
    text: str
    expected_capabilities: list = []

class RequirementCreate(RequirementBase):
    pass

class RequirementRead(RequirementBase):
    id: str
    framework_id: str

    class Config:
        from_attributes = True

class FrameworkBase(BaseModel):
    id: str
    name: str
    description: str | None = None
    equipment_type: str

class FrameworkCreate(FrameworkBase):
    pass

class FrameworkRead(FrameworkBase):
    standard_id: str

    class Config:
        from_attributes = True

class StandardBase(BaseModel):
    id: str
    name: str
    version: str | None = None

class StandardCreate(StandardBase):
    pass

class StandardRead(StandardBase):
    frameworks: list[FrameworkRead] = []

    class Config:
        from_attributes = True
