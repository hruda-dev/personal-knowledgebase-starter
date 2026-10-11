import json
from unittest.mock import MagicMock, Mock

import pytest
import requests

from backend import config
from backend.services import pdf_parser


def response(payload, status=200):
    return Mock(ok=status < 400, status_code=status, reason="Bad request", json=lambda: payload)


@pytest.fixture
def session(monkeypatch):
    monkeypatch.setattr(config, "LLAMA_CLOUD_API_KEY", "test-key")
    client = MagicMock()
    client.__enter__.return_value = client
    client.post.return_value = response({"id": "job-123", "status": "PENDING"})
    monkeypatch.setattr(pdf_parser.requests, "Session", lambda: client)
    monkeypatch.setattr(pdf_parser.time, "sleep", Mock())
    return client


def test_v2_upload_poll_and_markdown_page_numbers(session):
    session.get.side_effect = [
        response({"job": {"status": "RUNNING"}}),
        response({"job": {"status": "COMPLETED"}, "markdown": {"pages": [
            {"page_number": 1, "success": True, "markdown": ""},
            {"page_number": 2, "success": True, "markdown": "# Notes\n\n| A | B |"},
        ]}}),
    ]
    docs = pdf_parser.parse_pdf("notes.pdf", b"pdf", "doc-123")
    assert len(docs) == 1
    assert docs[0].page_content == "# Notes\n\n| A | B |"
    assert docs[0].metadata == {"page": 2, "filename": "notes.pdf", "document_id": "doc-123"}
    assert session.post.call_args.args == (f"{pdf_parser.PARSE_URL}/upload",)
    kwargs = session.post.call_args.kwargs
    assert kwargs["files"]["file"] == ("notes.pdf", b"pdf", "application/pdf")
    assert json.loads(kwargs["data"]["configuration"])["version"] == "latest"
    assert session.get.call_args.kwargs["params"] == {"expand": "markdown"}
    assert session.get.call_count == 2


@pytest.mark.parametrize("status", ["FAILED", "CANCELLED"])
def test_job_failure_is_reported(session, status):
    session.get.return_value = response({"job": {"status": status, "error_message": "Invalid PDF"}})
    with pytest.raises(ValueError, match="Invalid PDF"):
        pdf_parser.parse_pdf("notes.pdf", b"pdf", "doc")


def test_http_error_detail_is_preserved(session):
    session.post.return_value = response({"detail": "Account requires v2"}, status=403)
    with pytest.raises(ValueError, match="HTTP 403: Account requires v2"):
        pdf_parser.parse_pdf("notes.pdf", b"pdf", "doc")


def test_partial_page_failure_does_not_silently_index(session):
    session.get.return_value = response({"job": {"status": "COMPLETED"}, "markdown": {"pages": [
        {"page_number": 2, "success": False},
    ]}})
    with pytest.raises(ValueError, match="could not parse page 2"):
        pdf_parser.parse_pdf("notes.pdf", b"pdf", "doc")


def test_timeout_is_bounded(session, monkeypatch):
    monkeypatch.setattr(pdf_parser.time, "monotonic", Mock(side_effect=[0, 601]))
    with pytest.raises(ValueError, match="timed out.*job-123"):
        pdf_parser.parse_pdf("notes.pdf", b"pdf", "doc")
    session.get.assert_not_called()


def test_network_error_is_actionable(session):
    session.post.side_effect = requests.ConnectionError("unavailable")
    with pytest.raises(ValueError, match="Check your connection"):
        pdf_parser.parse_pdf("notes.pdf", b"pdf", "doc")
