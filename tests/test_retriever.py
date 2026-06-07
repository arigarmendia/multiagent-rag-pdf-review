import chromadb
from pydantic import BaseModel

CHROMA_PATH = "data/chroma_db"
COLLECTION_NAME = "reglas_lse"

_embedding_model = None
client = chromadb.PersistentClient(path=CHROMA_PATH)


class RetrievedChunk(BaseModel):
    content: str
    source: str
    distance: float


def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedding_model


def retrieve(query: str, k: int = 3) -> list[RetrievedChunk]:
    collection = client.get_or_create_collection(name=COLLECTION_NAME)
    embedding_model = get_embedding_model()
    query_embedding = embedding_model.encode([query]).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=k,
        include=["documents", "metadatas", "distances"]
    )

    chunks = []
    for doc, metadata, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    ):
        chunks.append(RetrievedChunk(
            content=doc,
            source=metadata.get("source", ""),
            distance=round(distance, 4)
        ))

    return chunks