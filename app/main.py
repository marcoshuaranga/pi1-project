"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.routers import kedb, metrics, tickets
from app.api.ws import pipeline as ws_pipeline


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Plataforma RAG + KEDB — OITSI-MTC",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(tickets.router)
    app.include_router(kedb.router)
    app.include_router(metrics.router)
    app.include_router(ws_pipeline.router)

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "pi1-rag-kedb"}

    return app


app = create_app()
