"""Connect LangChain to a persistent Qdrant collection (dense vector search)."""
from functools import lru_cache

from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient, models

from backend import config

@lru_cache(maxsize=1)
def get_embeddings() -> OpenAIEmbeddings:
    if not config.OPENROUTER_API_KEY or config.OPENROUTER_API_KEY.startswith("replace_"):
        raise RuntimeError("Set OPENROUTER_API_KEY in the .env file before uploading or chatting.")
    return OpenAIEmbeddings(
        model=config.EMBEDDING_MODEL,
        api_key=config.OPENROUTER_API_KEY,
        base_url=config.OPENROUTER_BASE_URL,
        check_embedding_ctx_length=False,
    )


@lru_cache(maxsize=1)
def get_store() -> QdrantVectorStore:
    embeddings = get_embeddings()

    if config.QDRANT_MODE == "local":
        config.QDRANT_PATH.mkdir(parents=True, exist_ok=True)
        client = QdrantClient(path=str(config.QDRANT_PATH))
    elif config.QDRANT_MODE == "server":
        client = QdrantClient(url=config.QDRANT_URL, api_key=config.QDRANT_API_KEY or None)
    else:
        raise ValueError("QDRANT_MODE must be local or server.")
    if not client.collection_exists(config.QDRANT_COLLECTION):
        client.create_collection(
            collection_name=config.QDRANT_COLLECTION,
            vectors_config=models.VectorParams(
                size=len(embeddings.embed_query("embedding dimension probe")),
                distance=models.Distance.COSINE,
            ),
        )

    return QdrantVectorStore(
        client=client,
        collection_name=config.QDRANT_COLLECTION,
        embedding=embeddings,
    )
