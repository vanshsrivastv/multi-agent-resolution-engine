import pathlib

from qdrant_client.models import PointStruct

from app.rag.embeddings import embed
from app.rag.vector_store import COLLECTION_NAME, ensure_collection, get_client

DOCS_DIR = pathlib.Path(__file__).resolve().parent.parent / "knowledge_base"


def load_docs() -> list[dict]:
    docs = []
    for path in sorted(DOCS_DIR.glob("*.md")):
        docs.append({"source": path.stem, "text": path.read_text(encoding="utf-8")})
    return docs


def main():
    docs = load_docs()
    vectors = embed([d["text"] for d in docs])

    client = get_client()
    ensure_collection(client)

    points = [
        PointStruct(id=i, vector=vectors[i], payload=docs[i])
        for i in range(len(docs))
    ]
    client.upsert(collection_name=COLLECTION_NAME, points=points)
    print(f"Indexed {len(points)} documents into '{COLLECTION_NAME}'.")


if __name__ == "__main__":
    main()
