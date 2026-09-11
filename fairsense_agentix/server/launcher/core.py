"""ServerLauncher orchestrator and public start() entry point."""

import logging
import signal
import subprocess
import sys
import time
import webbrowser
from typing import Optional

from fairsense_agentix.logging_config import ensure_root_logging
from fairsense_agentix.server.launcher.health import wait_for_backend, wait_for_frontend
from fairsense_agentix.server.launcher.messages import (
    print_backend_only_notice,
    print_backend_troubleshooting,
    print_banner,
    print_frontend_troubleshooting,
    print_nodejs_install_instructions,
    print_ready_message,
)
from fairsense_agentix.server.launcher.processes import (
    find_ui_dir,
    kill_port,
    start_backend,
    start_frontend,
)


logger = logging.getLogger(__name__)


class ServerLauncher:
    """Manages backend and frontend server processes.

    This class handles the full lifecycle of both servers:
    1. Start backend (FastAPI + uvicorn)
    2. Health check backend (/v1/health endpoint)
    3. Start frontend (React + Vite dev server)
    4. Health check frontend (HTTP GET /)
    5. Open browser (optional)
    6. Wait for user interrupt (Ctrl+C)
    7. Graceful shutdown

    Parameters
    ----------
    backend_port : int, default=8000
        Port for FastAPI backend
    frontend_port : int, default=5173
        Port for React UI (Vite default)
    open_browser : bool, default=True
        Auto-open browser when ready
    verbose : bool, default=True
        Stream backend/frontend logs to stdout (False = status only)
    reload : bool, default=False
        Enable uvicorn auto-reload (for prompt/config customization)
    ui : bool, default=True
        Also start the React UI. Automatically disabled (with a notice) when
        the ``ui/`` source directory is not present, e.g. for a PyPI install.
    frontend_timeout : int, default=60
        Seconds to wait for the Vite dev server to answer before giving up.
        Cold starts on network filesystems can take longer than the default.

    Examples
    --------
    >>> launcher = ServerLauncher()
    >>> launcher.start()
    >>> launcher.wait()  # Blocks until Ctrl+C
    """

    def __init__(  # noqa: PLR0913 -- mirrors the public start() options
        self,
        backend_port: int = 8000,
        frontend_port: int = 5173,
        open_browser: bool = True,
        verbose: bool = True,
        reload: bool = False,
        ui: bool = True,
        frontend_timeout: int = 60,
    ) -> None:
        """Initialize launcher with configuration."""
        self.backend_port = backend_port
        self.frontend_port = frontend_port
        self.open_browser = open_browser
        self.verbose = verbose
        self.reload = reload
        self.ui = ui
        self.frontend_timeout = frontend_timeout

        # So logger.debug() from _log_debug() is emitted when verbose=True
        # (parent logger is INFO)
        logger.setLevel(logging.DEBUG if verbose else logging.INFO)

        self.backend_proc: Optional[subprocess.Popen] = None
        self.frontend_proc: Optional[subprocess.Popen] = None

        self._setup_signal_handlers()

    def _log_debug(self, msg: str, *args: object) -> None:
        """Log at DEBUG only when verbose=True (keeps quiet mode clean)."""
        if self.verbose:
            logger.debug(msg, *args)

    def _setup_signal_handlers(self) -> None:
        """Register signal handlers for graceful shutdown on Ctrl+C."""
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

    def _handle_shutdown(self, _signum: int, _frame: object) -> None:
        """Handle shutdown signals (SIGINT/SIGTERM)."""
        logger.info("🛑 Shutting down servers...")
        self.stop()
        sys.exit(0)

    def start(self) -> tuple[subprocess.Popen, Optional[subprocess.Popen]]:
        """Start the backend and, when the UI source is available, the frontend.

        The React UI lives in ``ui/`` at the repository root and is not part of
        the published wheel. From a PyPI install the launcher therefore runs in
        backend-only mode and says so, instead of failing.

        Returns
        -------
        tuple[subprocess.Popen, subprocess.Popen | None]
            Backend process handle, and frontend handle (``None`` in
            backend-only mode)
        """
        print_banner()
        self._start_backend_with_health_check()

        if self.ui and find_ui_dir() is None:
            print_backend_only_notice(self.backend_port)
            self.ui = False

        if self.ui:
            self._start_frontend_with_health_check()
            self._open_browser_if_enabled()
            print_ready_message(self.backend_port, self.frontend_port)
        else:
            print_ready_message(self.backend_port, None)

        assert self.backend_proc is not None, "Backend process must be set"
        return self.backend_proc, self.frontend_proc

    def _start_backend_with_health_check(self) -> None:
        """Start backend and wait for it to be ready."""
        logger.info("▶️  Starting backend on port %s...", self.backend_port)
        try:
            self.backend_proc = start_backend(
                self.backend_port,
                reload=self.reload,
                verbose=self.verbose,
            )
        except Exception as e:
            logger.error("❌ Failed to start backend: %s", e)
            self.stop()
            sys.exit(1)

        logger.info(
            "⏳ Waiting for backend to be ready (preloading models, 1-2 minutes)...",
        )
        logger.info("   Initial startup delay before health checks: 10 seconds...")
        time.sleep(10)

        if not wait_for_backend(
            self.backend_proc,
            self.backend_port,
            verbose=self.verbose,
        ):
            print_backend_troubleshooting(self.backend_port)
            self.stop()
            sys.exit(1)
        logger.info("✅ Backend ready")

    def _start_frontend_with_health_check(self) -> None:
        """Start frontend and wait for it to be ready."""
        logger.info("▶️  Starting frontend on port %s...", self.frontend_port)
        try:
            self.frontend_proc = start_frontend(
                self.backend_port,
                self.frontend_port,
                verbose=self.verbose,
            )
        except FileNotFoundError:
            print_nodejs_install_instructions()
            self.stop()
            sys.exit(1)
        except Exception as e:
            logger.error("❌ Failed to start frontend: %s", e)
            self.stop()
            sys.exit(1)

        logger.info(
            "⏳ Waiting for frontend to be ready (up to %ss)...",
            self.frontend_timeout,
        )
        if not wait_for_frontend(self.frontend_port, timeout=self.frontend_timeout):
            print_frontend_troubleshooting(self.frontend_port)
            self.stop()
            sys.exit(1)
        logger.info("✅ Frontend ready")

    def _open_browser_if_enabled(self) -> None:
        """Open browser if configured to do so."""
        if self.open_browser:
            logger.info(
                "🌐 Opening browser at http://localhost:%s",
                self.frontend_port,
            )
            time.sleep(1)
            webbrowser.open(f"http://localhost:{self.frontend_port}")

    def stop(self) -> None:
        """Stop both servers gracefully and clean up ports.

        Sends SIGTERM to processes and waits up to 5 seconds for clean exit.
        If processes don't exit cleanly, kills them and cleans up ports.
        """
        if self.frontend_proc:
            try:
                if self.frontend_proc.poll() is None:
                    self.frontend_proc.terminate()
                    try:
                        self.frontend_proc.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        self.frontend_proc.kill()
                        self.frontend_proc.wait(timeout=1)
                        kill_port(self.frontend_port, verbose=self.verbose)
            except Exception:
                pass  # Best effort cleanup

        if self.backend_proc:
            try:
                if self.backend_proc.poll() is None:
                    self.backend_proc.terminate()
                    try:
                        self.backend_proc.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        self.backend_proc.kill()
                        self.backend_proc.wait(timeout=1)
                        kill_port(self.backend_port, verbose=self.verbose)
            except Exception:
                pass  # Best effort cleanup

        logger.info("✅ Servers stopped")

    def wait(self) -> None:
        """Block until processes exit or user interrupts (Ctrl+C).

        If backend exits (e.g., via shutdown endpoint), automatically stops frontend.
        """
        try:
            if self.backend_proc:
                self.backend_proc.wait()
                logger.info("🛑 Backend process exited")

                if self.frontend_proc and self.frontend_proc.poll() is None:
                    logger.info("🛑 Shutting down frontend...")
                    self.stop()
                return

            if self.frontend_proc:
                self.frontend_proc.wait()
        except KeyboardInterrupt:
            logger.info("🛑 Shutting down servers...")
            self.stop()


def start(  # noqa: PLR0913 -- one keyword per user-facing option
    port: int = 8000,
    ui_port: int = 5173,
    open_browser: bool = True,
    verbose: bool = True,
    reload: bool = False,
    ui: bool = True,
    frontend_timeout: int = 60,
) -> None:
    """Start FairSense-AgentiX with backend and (optionally) frontend servers.

    From a source checkout this launches both the FastAPI backend and the React
    UI development server. The UI is not included in the PyPI package; from an
    installed wheel the launcher runs the backend only and prints the API URL.

    Parameters
    ----------
    port : int, default=8000
        Port for FastAPI backend
    ui_port : int, default=5173
        Port for React UI dev server (Vite default)
    open_browser : bool, default=True
        Automatically open browser when ready
    verbose : bool, default=True
        Stream backend/frontend logs to stdout
        If False, only show status messages (cleaner output)
    reload : bool, default=False
        Enable uvicorn auto-reload on code changes
        Useful for customizing prompts, configs, or tool parameters
        Frontend has built-in hot-reload via Vite
    ui : bool, default=True
        Start the React UI as well. Set False for a backend-only server; it is
        also switched off automatically when ``ui/`` is not present.
    frontend_timeout : int, default=60
        Seconds to wait for the Vite dev server before giving up

    Examples
    --------
    Simple usage (default ports, auto-open browser):

        >>> from fairsense_agentix import server
        >>> server.start()

    Custom ports:

        >>> server.start(port=9000, ui_port=3000)

    Clean output (status only, no logs):

        >>> server.start(verbose=False)

    Development mode with auto-reload:

        >>> server.start(reload=True)
        # Edit prompts/bias_detector.txt -> backend auto-reloads

    Headless mode (no browser):

        >>> server.start(open_browser=False)

    Backend only (API + /docs, no Node.js needed):

        >>> server.start(ui=False)

    Notes
    -----
    - Backend startup takes 30-45s on first run (model preloading)
    - Frontend auto-installs npm dependencies if needed (1-2 min first time)
    - Press Ctrl+C for graceful shutdown
    - The UI requires a source checkout and Node.js/npm (https://nodejs.org/);
      ``pip install fairsense-agentix`` provides the backend only
    """
    ensure_root_logging(logging.DEBUG if verbose else logging.INFO)

    launcher = ServerLauncher(
        backend_port=port,
        frontend_port=ui_port,
        open_browser=open_browser,
        verbose=verbose,
        reload=reload,
        ui=ui,
        frontend_timeout=frontend_timeout,
    )

    launcher.start()
    launcher.wait()
