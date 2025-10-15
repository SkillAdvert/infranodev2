"""FastAPI application factory."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.routes.financial import router as financial_router


def create_app() -> FastAPI:
    app = FastAPI(title="Infranodal API", version="2.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(financial_router)
    return app


__all__ = ["create_app"]
