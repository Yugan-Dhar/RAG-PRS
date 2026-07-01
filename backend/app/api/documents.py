from fastapi import APIRouter, UploadFile, File, BackgroundTasks
from typing import List

router = APIRouter()

@router.post("/documents")
async def upload_documents(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...)
):
    # This is a stub for the document ingestion API
    # In full implementation, this saves the file, creates a Document DB record,
    # and triggers a background ingestion task.
    uploaded = []
    for f in files:
        uploaded.append({"filename": f.filename, "status": "pending"})
        # Save file to disk
        # bg_task: parse -> chunk -> embed -> index
    return {"message": "Files queued for ingestion", "documents": uploaded}

@router.get("/documents/{document_id}")
async def get_document_status(document_id: str):
    # Stub
    return {"id": document_id, "status": "completed"}
