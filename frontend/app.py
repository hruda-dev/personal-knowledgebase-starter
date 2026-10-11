"""Standalone Streamlit app with persistent local Qdrant storage."""
import sys
from pathlib import Path

import streamlit as st

root = Path(__file__).resolve().parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from backend.services import ingestion, registry
from backend.services.rag import answer_question

st.set_page_config(page_title="Personal Knowledgebase AI", page_icon="📚")
st.title("personal knowledgebase ai")
st.caption("upload your knowledge, then ask questions grounded in it")


def show_sources(sources):
    if sources:
        with st.expander("retrieved passages"):
            for source in sources:
                page = f", page {source['page']}" if source.get("page") else ""
                st.markdown(f"**[{source['index']}] {source['filename']}{page}**")
                st.caption(source["excerpt"])


with st.sidebar:
    st.header("your knowledge")
    files = st.file_uploader("upload pdf, txt, or md", type=["pdf", "txt", "md"], accept_multiple_files=True)
    if st.button("index files", disabled=not files):
        for file in files or []:
            try:
                with st.spinner(f"indexing {file.name}..."):
                    result = ingestion.ingest_file(file.name, file.getvalue())
                st.success(f"indexed {file.name} ({result['chunks']} chunks)")
            except Exception as exc:
                st.error(f"{file.name}: {exc}")

    with st.expander("add text manually"):
        title = st.text_input("title")
        body = st.text_area("content", height=150)
        if st.button("save text"):
            try:
                with st.spinner("indexing text..."):
                    ingestion.ingest_text(title, body)
                st.success("text indexed")
            except Exception as exc:
                st.error(str(exc))

    st.subheader("indexed sources")
    try:
        sources = registry.list_documents()
        if not sources:
            st.caption("no sources yet")
        for entry in sources:
            col1, col2 = st.columns([4, 1])
            col1.caption(f"{entry['filename']} ({entry['chunk_count']} chunks)")
            if col2.button("×", key=f"delete-{entry['id']}", help="delete document"):
                if ingestion.delete_document(entry["id"]):
                    st.rerun()
                else:
                    st.error("Document no longer exists.")
    except Exception as exc:
        st.error(f"Could not load or update documents: {exc}")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        show_sources(message.get("sources"))

prompt = st.chat_input("ask something about your knowledgebase")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        try:
            if len(prompt) > 2000:
                raise ValueError("Questions must be at most 2000 characters.")
            if not registry.list_documents():
                result = {"answer": "Upload and index a document first.", "sources": []}
            else:
                with st.spinner("searching your knowledgebase..."):
                    result = answer_question(prompt)
            st.markdown(result["answer"])
            show_sources(result["sources"])
            st.session_state.messages.append(
                {"role": "assistant", "content": result["answer"], "sources": result["sources"]}
            )
        except Exception as exc:
            st.error(f"chat failed: {exc}")
