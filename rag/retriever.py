import chromadb
from pydantic import BaseModel
import mlflow
import time

CHROMA_PATH = "data/chroma_db"
COLLECTION_NAME = "reglas_lse"

client = chromadb.PersistentClient(path=CHROMA_PATH)


class RetrievedChunk(BaseModel):
    content: str
    source: str
    distance: float


def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2", local_files_only=True)
    return _embedding_model

_embedding_model = None

RELEVANCE_THRESHOLD = 1.5

@mlflow.trace(name="rag_retriever")
def retrieve(query: str, k: int = 3) -> list[RetrievedChunk]:
    start_time = time.time()
    
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

    latency = time.time() - start_time
    avg_distance = round(sum(c.distance for c in chunks) / len(chunks), 4) if chunks else 0
    hit_count = len([c for c in chunks if c.distance < RELEVANCE_THRESHOLD])
    precision_at_k = round(hit_count / len(chunks), 3) if chunks else 0

    span = mlflow.get_current_active_span()
    if span:
        span.set_attributes({
            "retrieval_latency_seconds": round(latency, 3),
            "chunks_retrieved": len(chunks),
            "avg_distance": avg_distance,
            "hit_count": hit_count,
            "precision_at_k": precision_at_k,
            "relevance_threshold": RELEVANCE_THRESHOLD,
            "query": query
        })

    return chunks