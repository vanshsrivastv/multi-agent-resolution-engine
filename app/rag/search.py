from langsmith import traceable
from qdrant_client.http.exceptions import ResponseHandlingException

from app.rag.embeddings import embed
from app.rag.vector_store import COLLECTION_NAME, get_client
from app.retry import with_retries

# Connection-level failures (Qdrant temporarily unreachable) are worth a
# retry; there's no equivalent of a "bad request" from this call shape.
QDRANT_TRANSIENT = (ResponseHandlingException,)


@traceable(run_type="retriever", name="qdrant_search")
def search(query: str, top_k: int = 3) -> list[dict]:
    client = get_client()
    query_vector = embed([query])[0]

    def _call():
        return client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=top_k,
        ).points

    # Capped at 2 attempts (not the default 3): each attempt against a
    # genuinely unreachable Qdrant takes several seconds regardless of our
    # own timeout setting, so 3 attempts made a real outage escalate too
    # slowly (confirmed by testing - ~20s vs ~10-13s with 2).
    results = with_retries(_call, QDRANT_TRANSIENT, max_attempts=2)

    return [
        {"source": r.payload["source"], "text": r.payload["text"], "score": r.score}
        for r in results
    ]
