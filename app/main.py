from fastapi import FastAPI

from app.api.health import router as health_router

app = FastAPI(title="AI Operations Engine")

app.include_router(health_router)
