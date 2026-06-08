import chromadb
import re
import time
import mlflow
from pathlib import Path

CHROMA_PATH = "data/chroma_db"
COLLECTION_NAME = "reglas_lse"

client = chromadb.PersistentClient(path=CHROMA_PATH)


def chunk_by_section(text: str) -> list[str]:
    sections = re.split(r'\n(?=\d+\.\s+[A-ZÁÉÍÓÚ])', text)
    return [s.strip() for s in sections if s.strip()]


@mlflow.trace(name="indexer")
def index_document(file_path: str, source_name: str) -> None:
    from sentence_transformers import SentenceTransformer
    embedding_model = SentenceTransformer("all-MiniLM-L6-v2", local_files_only=True)

    start_time = time.time()
    text = Path(file_path).read_text(encoding="utf-8")
    chunks = chunk_by_section(text)

    collection = client.get_or_create_collection(name=COLLECTION_NAME)
    collection.delete(where={"source": source_name})

    embeddings = embedding_model.encode(chunks).tolist()

    collection.add(
        documents=chunks,
        embeddings=embeddings,
        ids=[f"{source_name}_{i}" for i in range(len(chunks))],
        metadatas=[{"source": source_name} for _ in chunks]
    )

    latency = time.time() - start_time

    span = mlflow.get_current_active_span()
    if span:
        span.set_attributes({
            "source": source_name,
            "chunks_indexed": len(chunks),
            "indexing_latency_seconds": round(latency, 3)
        })

    print(f"Indexados {len(chunks)} chunks de '{source_name}'")


def index_all(documents_dir: str = "data/rag_documents") -> None:
    for file_path in Path(documents_dir).glob("*.txt"):
        index_document(str(file_path), file_path.stem)