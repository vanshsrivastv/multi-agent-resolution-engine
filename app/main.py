from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.tickets import router as tickets_router

app = FastAPI(title="AI Operations Engine")

app.include_router(health_router)
app.include_router(tickets_router)
