from uuid import uuid4

import pytest
from unittest.mock import Mock
from langchain_core.documents import Document

from backend import config
from backend.services import ingestion
from backend.services.ingestion import parse_file


def test_plain_text_is_chunked_with_metadata():
    doc_id = str(uuid4())
    chunks = parse_file("notes.txt", b"The project uses Qdrant for vector search.", doc_id)
    assert len(chunks) == 1
    assert chunks[0].metadata["document_id"] == doc_id
    assert chunks[0].metadata["filename"] == "notes.txt"
    assert chunks[0].metadata["chunk_index"] == 0


def test_reject_empty_files():
    with pytest.raises(ValueError, match="No readable text"):
        parse_file("empty.md", b"", str(uuid4()))


def test_reject_unsupported_files():
    with pytest.raises(ValueError, match="Unsupported file type"):
        parse_file("bad.exe", b"something", str(uuid4()))


def test_pdf_requires_llamacloud_key(monkeypatch):
    monkeypatch.setattr(config, "LLAMA_CLOUD_API_KEY", "")
    with pytest.raises(ValueError, match="LLAMA_CLOUD_API_KEY"):
        parse_file("notes.pdf", b"pdf", "doc-id")


def test_pdf_markdown_uses_semantic_chunks_and_preserves_pages(monkeypatch):
    import langchain_experimental.text_splitter as semantic_module

    monkeypatch.setattr(config, "LLAMA_CLOUD_API_KEY", "test-key")
    parser = Mock(return_value=[Document(
        page_content="# Topic\nMarkdown content.",
        metadata={"filename": "notes.pdf", "page": 2, "document_id": "doc-id"},
    )])
    monkeypatch.setattr(ingestion, "parse_pdf", parser)
    embeddings = Mock()
    monkeypatch.setattr(ingestion, "get_embeddings", lambda: embeddings)
    semantic = Mock()
    semantic.split_documents.side_effect = lambda docs: docs
    semantic_factory = Mock(return_value=semantic)
    monkeypatch.setattr(semantic_module, "SemanticChunker", semantic_factory)

    chunks = parse_file("../../notes.pdf", b"pdf", "doc-id")

    assert chunks[0].page_content == "# Topic\nMarkdown content."
    assert chunks[0].metadata == {
        "filename": "notes.pdf", "page": 2,
        "document_id": "doc-id", "chunk_index": 0,
    }
    parser.assert_called_once_with("notes.pdf", b"pdf", "doc-id")
    assert semantic_factory.call_args.args == (embeddings,)
    assert semantic_factory.call_args.kwargs["breakpoint_threshold_amount"] == 95
