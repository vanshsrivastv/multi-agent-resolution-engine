from app.rag.embeddings import embed
from app.rag.vector_store import COLLECTION_NAME, get_client


def search(query: str, top_k: int = 3) -> list[dict]:
    client = get_client()
    query_vector = embed([query])[0]

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=top_k,
    ).points

    return [
        {"source": r.payload["source"], "text": r.payload["text"], "score": r.score}
        for r in results
    ]
