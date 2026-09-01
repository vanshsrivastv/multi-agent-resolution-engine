from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

COLLECTION_NAME = "tech_docs"
VECTOR_SIZE = 384


def get_client() -> QdrantClient:
    # Without an explicit timeout, the client can hang far longer than our
    # own retry backoff expects when Qdrant is unreachable.
    return QdrantClient(url="http://localhost:6333", timeout=5)


def ensure_collection(client: QdrantClient) -> None:
    if not client.collection_exists(COLLECTION_NAME):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
