"""Run the FastAPI backend with settings from the environment.

Usage::

    python -m fairsense_agentix.service_api

Reads ``FAIRSENSE_API_HOST`` / ``FAIRSENSE_API_PORT`` / ``FAIRSENSE_API_RELOAD``
(via :class:`~fairsense_agentix.configs.settings.Settings`), unlike the bare
``uvicorn`` CLI which ignores them. This is what the server launcher runs, and it
works from an installed wheel — no repository checkout required.
"""

from __future__ import annotations

import logging
import sys


logger = logging.getLogger(__name__)


def main() -> int:
    """Start uvicorn with the configured host/port; return a process exit code."""
    from fairsense_agentix.logging_config import ensure_root_logging  # noqa: PLC0415

    try:
        import uvicorn  # noqa: PLC0415

        from fairsense_agentix.configs.settings import settings  # noqa: PLC0415

        ensure_root_logging(getattr(logging, settings.log_level))

        logger.info("=" * 70)
        logger.info("Starting FairSense AgentiX Server")
        logger.info("=" * 70)
        logger.info("Host: %s", settings.api_host)
        logger.info("Port: %s", settings.api_port)
        logger.info("Reload: %s", settings.api_reload)
        logger.info("LLM Provider: %s", settings.llm_provider)
        logger.info("=" * 70)

        uvicorn.run(
            "fairsense_agentix.service_api.server:app",
            host=settings.api_host,
            port=settings.api_port,
            reload=settings.api_reload,
            log_level="info",
        )
    except KeyboardInterrupt:
        ensure_root_logging()
        logger.info("Server stopped by user")
        return 0
    except Exception:
        ensure_root_logging()
        logger.exception("Failed to start server")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
