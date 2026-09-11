"""FastAPI surface for FairSense-AgentiX."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import logging config for side effects (suppress verbose HTTP logs)
from fairsense_agentix import (
    FairSense,
    __version__,
    logging_config,  # noqa: F401 (imported for side effects)
)
from fairsense_agentix.configs import settings
from fairsense_agentix.service_api import app_state
from fairsense_agentix.service_api.routes import analyze, batch, health, stream
from fairsense_agentix.services import telemetry
from fairsense_agentix.services.event_bus import AgentEventBus


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: startup warmup and shutdown cleanup.

    Startup Phase:
    - Preloads all models and tools (LLM, OCR, embeddings, FAISS indexes)
    - This takes 30-45s but makes subsequent requests instant
    - Attaches event loop for WebSocket streaming

    Shutdown Phase:
    - Cleanup resources if needed
    """
    # STARTUP: Preload models and tools
    logger.info("🔥 FairSense AgentiX starting up...")
    logger.info("⏳ Preloading models and tools (this takes 30-45s)...")

    app_state.engine = FairSense()
    logger.info("✅ FairSense engine initialized with all models loaded")
    if settings.llm_provider == "fake":
        logger.warning(
            "⚠️  MOCK MODE: FAIRSENSE_LLM_PROVIDER=fake. All analysis results are "
            "synthetic placeholders. Set FAIRSENSE_LLM_PROVIDER and "
            "FAIRSENSE_LLM_API_KEY for real analysis.",
        )

    app_state.event_bus = AgentEventBus(telemetry)
    loop = asyncio.get_running_loop()
    app_state.event_bus.attach_loop(loop)
    logger.info("✅ Event bus attached to event loop")

    logger.info("🚀 Server ready! All requests will be fast now.")

    yield  # Server runs here

    # SHUTDOWN: Cleanup
    logger.info("🛑 Shutting down FairSense AgentiX...")


app = FastAPI(
    title="FairSense AgentiX API",
    version=__version__,
    lifespan=lifespan,
)
# Origins come from FAIRSENSE_API_CORS_ORIGINS (default: local Vite dev server).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(analyze.router)
app.include_router(batch.router)
app.include_router(stream.router)
