"""Convert PDFs to page-level Markdown through the LlamaParse v2 REST API."""
import json
import time

import requests
from langchain_core.documents import Document

from backend import config

PARSE_URL = "https://api.cloud.llamaindex.ai/api/v2/parse"
POLL_SECONDS = 2
PARSE_TIMEOUT_SECONDS = 600


def _response_json(response: requests.Response) -> dict:
    if not response.ok:
        try:
            detail = response.json().get("detail", response.reason)
        except ValueError:
            detail = response.reason
        detail = str(detail).replace(config.LLAMA_CLOUD_API_KEY, "[redacted]")
        raise ValueError(f"LlamaParse v2 returned HTTP {response.status_code}: {detail[:500]}")
    return response.json()


def parse_pdf(filename: str, data: bytes, document_id: str) -> list[Document]:
    if not config.LLAMA_CLOUD_API_KEY or config.LLAMA_CLOUD_API_KEY.startswith("replace_"):
        raise ValueError("Set LLAMA_CLOUD_API_KEY in .env.local before uploading PDFs.")

    try:
        with requests.Session() as session:
            session.headers.update({"Authorization": f"Bearer {config.LLAMA_CLOUD_API_KEY}"})
            # The upload endpoint accepts the PDF and configuration in one request.
            created = _response_json(session.post(
                f"{PARSE_URL}/upload",
                files={"file": (filename, data, "application/pdf")},
                data={"configuration": json.dumps({
                    "tier": "agentic", "version": "latest",
                    "output_options": {"markdown": {"tables": {"output_tables_as_markdown": True}}},
                })},
                timeout=60,
            ))
            job_id = created.get("id")
            if not job_id:
                raise ValueError("LlamaParse v2 did not return a parse job ID.")

            deadline = time.monotonic() + PARSE_TIMEOUT_SECONDS
            while time.monotonic() < deadline:
                result = _response_json(session.get(
                    f"{PARSE_URL}/{job_id}", params={"expand": "markdown"}, timeout=60,
                ))
                job = result.get("job") or {}
                status = job.get("status")
                if status == "COMPLETED":
                    return _markdown_documents(result, filename, document_id)
                if status in {"FAILED", "CANCELLED"}:
                    detail = str(job.get("error_message") or status)
                    detail = detail.replace(config.LLAMA_CLOUD_API_KEY, "[redacted]")
                    raise ValueError(f"LlamaParse v2 job {job_id}: {detail[:500]}")
                if status not in {"PENDING", "RUNNING"}:
                    raise ValueError(f"LlamaParse v2 returned an unexpected job status: {status}")
                time.sleep(POLL_SECONDS)
            raise ValueError(f"LlamaParse v2 timed out waiting for job {job_id}. Check its status in LlamaCloud.")
    except requests.RequestException as exc:
        raise ValueError("Could not reach LlamaParse v2. Check your connection and try again.") from exc


def _markdown_documents(result: dict, filename: str, document_id: str) -> list[Document]:
    pages = (result.get("markdown") or {}).get("pages")
    if not isinstance(pages, list):
        raise ValueError("LlamaParse v2 completed without returning Markdown pages.")
    docs = []
    for page in pages:
        page_number = page.get("page_number")
        if page.get("success") is False:
            raise ValueError(f"LlamaParse could not parse page {page_number}; document was not indexed.")
        text = page.get("markdown") or ""
        if not text.strip():
            continue
        if not isinstance(page_number, int) or page_number < 1:
            raise ValueError("LlamaParse v2 returned a Markdown page without a valid page number.")
        docs.append(Document(page_content=text, metadata={
            "filename": filename, "page": page_number, "document_id": document_id,
        }))
    return docs
