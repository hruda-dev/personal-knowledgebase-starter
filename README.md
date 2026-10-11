# Personal Knowledgebase AI

A local, single-user RAG MVP with FastAPI, Streamlit, LangChain, OpenRouter, LlamaParse, and Qdrant.

## Requirements

- Python 3.11 or newer
- An OpenRouter API key with available credits for chat and embeddings
- A LlamaCloud API key for LlamaParse PDF parsing

## Run

On this Windows machine, dependencies are installed at `D:\venvs\pkb` to avoid Windows path-length limits. Start the app from PowerShell with `./run.cmd` (no activation needed).

1. Open a terminal inside this folder.
2. `python -m venv .venv`
3. Activate: macOS/Linux `source .venv/bin/activate`, Windows PowerShell `.\.venv\Scripts\Activate.ps1`.
4. `python -m pip install -r requirements.txt`
5. Copy `.env.example` to `.env.local` and set `OPENROUTER_API_KEY` and `LLAMA_CLOUD_API_KEY`. Existing `.env.local` settings load automatically, ahead of `.env` defaults.
6. `python -m streamlit run frontend/app.py`
7. Open http://localhost:8501.

Streamlit calls the ingestion and chat services directly. No Docker or FastAPI process is required. Qdrant runs embedded in Python and persists vectors under `backend/data/qdrant/`; SQLite stores the source catalog under `backend/data/`. Run only one app process against this local database.

PDF parsing uses the LlamaParse v2 REST API (`/api/v2/parse/upload`) with the `agentic` tier and per-page Markdown output. It uses the existing `LLAMA_CLOUD_API_KEY`; the legacy `llama-parse` SDK is no longer required. Parsing waits up to ten minutes for a job to finish and reports API failures in the app.

The FastAPI endpoints below are optional. To use an external Qdrant server, set `QDRANT_MODE=server` and configure `QDRANT_URL`. Existing server vectors are not copied into the embedded database; re-upload documents when switching storage modes.

## URLs

- Streamlit: http://localhost:8501
- FastAPI OpenAPI: http://localhost:8000/docs
- FastAPI health: http://localhost:8000/health
- Qdrant dashboard: available only with an external Qdrant server

## Endpoints

| Endpoint | Description |
|---|---|
| `GET /health` | API health check |
| `GET /knowledge` | List indexed documents |
| `POST /knowledge/upload` | Upload a PDF, TXT or MD file (`file` multipart field) |
| `POST /knowledge/text` | Add `{ "title": "...", "content": "..." }` |
| `DELETE /knowledge/{document_id}` | Remove a source and all of its vector chunks |
| `POST /chat` | Ask `{ "question": "..." }` |

## Test

`python -m pip install pytest`

`python -m pytest -q`

## Scope and limitations

- Local development only, **not safe to expose to the public internet** without authentication, HTTPS, validation, and rate limits.
- Embedded Qdrant and SQLite persist under `backend/data/`. Deleting this directory erases local indexed documents.
- PDFs are sent to LlamaParse for conversion to Markdown, including scanned PDF support. Markdown pages are split semantically using OpenRouter embeddings at the 95th percentile of sentence dissimilarity; page citations are preserved. UTF-8 TXT and Markdown use character chunking.
- Chat and embeddings use the OpenRouter endpoint with provider-prefixed model IDs (defaults: `openai/gpt-4.1-mini` and `openai/text-embedding-3-small`). LlamaParse uses its separate LlamaCloud key. PDF parsing, semantic splitting, and model calls incur service costs; uploaded PDFs are sent to LlamaCloud and text is sent to OpenRouter.
- Retrieval is dense vector similarity; no hybrid search or reranking yet.
- Chat messages appear for the current Streamlit session; the backend does **not** persist conversation history or resolve follow-up questions using chat history.
- Retrieved passage labels are shown to make grounding auditable. They are not a formal verification of every generated statement.
- Re-uploading an identical file makes a new source; deduplication is not implemented.
- **Do not run `docker compose down -v`** unless you want to delete persisted Qdrant vectors. Deleting `backend/data/` erases SQLite source records.
- Changing the embedding model to one with different dimensions requires re-creating or migrating the collection.

## Suggested next features

Authentication, per-user knowledge isolation, deduplication, progress indication, streaming chat responses, chat history and query rewriting, URL crawling, hybrid retrieval, deployment.

