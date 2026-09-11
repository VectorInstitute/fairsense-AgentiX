"""User-facing log output for the server launcher."""

import logging
from typing import Optional


logger = logging.getLogger(__name__)


def print_banner() -> None:
    """Print startup banner."""
    logger.info("=" * 70)
    logger.info("🚀 FairSense-AgentiX Server Launcher")
    logger.info("=" * 70)


def print_ready_message(backend_port: int, frontend_port: Optional[int]) -> None:
    """Print ready message with access URLs (frontend line omitted if None)."""
    logger.info("=" * 70)
    logger.info("✅ FairSense-AgentiX is running!")
    logger.info("=" * 70)
    logger.info("Backend:  http://localhost:%s", backend_port)
    if frontend_port is not None:
        logger.info("Frontend: http://localhost:%s", frontend_port)
    logger.info("API Docs: http://localhost:%s/docs", backend_port)
    logger.info("Press Ctrl+C to stop")
    logger.info("=" * 70)


def print_backend_only_notice(backend_port: int) -> None:
    """Explain that the UI source is absent and only the API will run."""
    logger.warning("⚠️  Web UI source (ui/) not found — running backend only.")
    logger.info("   The React UI ships with the git checkout, not the PyPI wheel.")
    logger.info("   To use it: git clone the repository, install Node.js, and run")
    logger.info("   server.start() from the checkout. The REST API and interactive")
    logger.info("   docs are available now at http://localhost:%s/docs", backend_port)


def print_backend_troubleshooting(port: int) -> None:
    """Print backend troubleshooting instructions."""
    logger.error("❌ Backend failed to start on port %s", port)
    logger.info("💡 Troubleshooting:")
    logger.info("   • Check if port %s is already in use", port)
    logger.info("   • Run: lsof -i :%s  (macOS/Linux)", port)
    logger.info("   • Run: netstat -ano | findstr :%s  (Windows)", port)
    logger.info(
        "   • Check .env file for FAIRSENSE_LLM_API_KEY and other settings",
    )


def print_frontend_troubleshooting(port: int) -> None:
    """Print frontend troubleshooting instructions."""
    logger.error("❌ Frontend failed to start on port %s", port)
    logger.info("💡 Troubleshooting:")
    logger.info("   • Check if port %s is already in use", port)
    logger.info(
        "   • Ensure npm dependencies are installed: cd ui && npm install",
    )
    logger.info(
        "   • Check ui/ directory exists and contains package.json",
    )


def print_nodejs_install_instructions() -> None:
    """Print Node.js installation instructions."""
    logger.error("❌ npm not found")
    logger.info("💡 Install Node.js:")
    logger.info("   • macOS: brew install node")
    logger.info("   • Windows: https://nodejs.org/")
    logger.info("   • Linux: sudo apt install nodejs npm")
