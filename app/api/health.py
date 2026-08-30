from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check() -> dict:
    """Simple liveness check: if this responds, the server process is up."""
    return {"status": "ok"}
