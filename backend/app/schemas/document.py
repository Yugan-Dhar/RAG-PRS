from pydantic import BaseModel

class DocumentBase(BaseModel):
    filename: str
    mime_type: str

class DocumentCreate(DocumentBase):
    file_path: str

class DocumentRead(DocumentBase):
    id: str
    status: str

    class Config:
        from_attributes = True

class ChunkRead(BaseModel):
    id: str
    document_id: str
    chunk_index: int
    text: str
    metadata_json: dict

    class Config:
        from_attributes = True
