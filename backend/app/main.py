"""FastAPI entrypoint for the GrowthX × Ringg AI buildathon backend."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers import calls, health, webhooks
from .store import store

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Connect the repository (Motor) on startup; close it on shutdown.
    await store.connect()
    yield
    await store.close()


app = FastAPI(
    title="GrowthX × Ringg AI — Backend",
    description=(
        "Triggers Ringg AI outbound voice calls and ingests post-call webhooks "
        "(transcript, recording, analysis). See /docs."
    ),
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

app.include_router(health.router)
app.include_router(calls.router)
app.include_router(webhooks.router)


@app.get("/", tags=["health"])
def root() -> dict:
    return {"service": settings.app_name, "docs": "/docs"}
