"""Turn an uploaded document into metadata-tagged Qdrant points."""
from pathlib import Path
from uuid import uuid4

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import models

from backend import config
from backend.services import registry
from backend.services.pdf_parser import parse_pdf
from backend.services.store import get_embeddings, get_store

ALLOWED_TYPES = {".pdf", ".txt", ".md"}
MAX_FILE_BYTES = 10 * 1024 * 1024
splitter = RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=150)


def parse_file(filename: str, file_bytes: bytes, document_id: str) -> list[Document]:
    safe_name = Path(filename.replace("\\", "/")).name
    suffix = Path(safe_name).suffix.lower()
    if suffix not in ALLOWED_TYPES:
        raise ValueError("Unsupported file type. Use PDF, TXT, or MD.")

    if suffix == ".pdf":
        from langchain_experimental.text_splitter import SemanticChunker

        docs = parse_pdf(safe_name, file_bytes, document_id)
        chunks = SemanticChunker(
            get_embeddings(), breakpoint_threshold_type="percentile",
            breakpoint_threshold_amount=95,
        ).split_documents(docs) if docs else []
    else:
        try:
            content = file_bytes.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError("Text and Markdown files must be UTF-8 encoded.") from exc
        docs = [Document(page_content=content, metadata={"filename": safe_name, "document_id": document_id})]
        chunks = splitter.split_documents(docs)

    if not chunks:
        raise ValueError("No readable text found in this file.")
    for chunk_index, chunk in enumerate(chunks):
        chunk.metadata["chunk_index"] = chunk_index
    return chunks


def ingest_file(filename: str, data: bytes) -> dict:
    if len(data) > MAX_FILE_BYTES:
        raise ValueError("Maximum file size is 10 MB.")
    document_id = str(uuid4())
    chunks = parse_file(filename, data, document_id)
    get_store().add_documents(chunks, ids=[str(uuid4()) for _ in chunks])
    registry.add_document(document_id, chunks[0].metadata["filename"], len(chunks))
    return {"document_id": document_id, "chunks": len(chunks)}


def ingest_text(title: str, content: str) -> dict:
    if not title.strip() or not content.strip():
        raise ValueError("Title and content cannot be blank.")
    if len(content) > MAX_FILE_BYTES:
        raise ValueError("Text content is too large.")
    return ingest_file(f"{title.strip()}.txt", content.encode("utf-8"))


def delete_document(document_id: str) -> bool:
    if not registry.has_document(document_id):
        return False
    store = get_store()
    store.client.delete(
        collection_name=config.QDRANT_COLLECTION,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="metadata.document_id",
                        match=models.MatchValue(value=document_id),
                    )
                ]
            )
        ),
        wait=True,
    )
    registry.remove_document(document_id)
    return True
