from fastapi import APIRouter, File, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from backend.schemas import TextKnowledgeRequest
from backend.services import ingestion, registry

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("")
def list_knowledge():
    return registry.list_documents()


@router.post("/upload")
async def upload_knowledge(file: UploadFile = File(...)):
    data = await file.read(ingestion.MAX_FILE_BYTES + 1)
    await file.close()
    try:
        return await run_in_threadpool(ingestion.ingest_file, file.filename or "unnamed", data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/text")
def add_text(payload: TextKnowledgeRequest):
    try:
        return ingestion.ingest_text(payload.title, payload.content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{document_id}")
def delete_knowledge(document_id: str):
    if not ingestion.delete_document(document_id):
        raise HTTPException(status_code=404, detail="Document not found")
    return {"deleted": True, "document_id": document_id}
