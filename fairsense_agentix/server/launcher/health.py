"""HTTP health-check polling for backend and frontend servers."""

import logging
import subprocess
import time
from typing import Optional

import requests


logger = logging.getLogger(__name__)


def _log_debug(verbose: bool, msg: str, *args: object) -> None:
    """Emit a DEBUG log only when verbose=True."""
    if verbose:
        logger.debug(msg, *args)


def wait_for_backend(  # noqa: PLR0912
    proc: Optional[subprocess.Popen],
    port: int,
    *,
    verbose: bool,
    timeout: int = 120,
) -> bool:
    """Wait for backend to respond to health checks.

    Tries both localhost and 127.0.0.1 for maximum compatibility
    ("localhost" may resolve to ::1 on some systems while the backend binds IPv4).

    Parameters
    ----------
    proc : subprocess.Popen | None
        Backend process handle (used to detect early exit)
    port : int
        Backend port to poll
    verbose : bool
        Whether to emit debug-level polling logs
    timeout : int, default=120
        Maximum seconds to wait

    Returns
    -------
    bool
        True if backend is ready, False if timeout or process died
    """
    urls = [
        f"http://localhost:{port}/v1/health",
        f"http://127.0.0.1:{port}/v1/health",
    ]
    start_time = time.time()

    _log_debug(verbose, "Starting health checks with %ss timeout", timeout)
    _log_debug(verbose, "URLs to try: %s", urls)

    attempt = 0
    while time.time() - start_time < timeout:
        attempt += 1

        # Check if backend process is still alive
        if proc:
            poll_status = proc.poll()
            if poll_status is not None:
                logger.warning(
                    "Backend process exited with code %s (health check aborted)",
                    poll_status,
                )
                return False

            if attempt % 5 == 1:
                _log_debug(
                    verbose,
                    "Attempt %s - backend PID %s running",
                    attempt,
                    proc.pid,
                )

        for url in urls:
            try:
                if attempt <= 3:
                    _log_debug(verbose, "Trying: %s", url)
                response = requests.get(url, timeout=2)
                if response.status_code == 200:
                    _log_debug(
                        verbose,
                        "Health check success: %s %s",
                        response.status_code,
                        url,
                    )
                    return True
            except requests.exceptions.ConnectionError:
                if attempt <= 3:
                    _log_debug(verbose, "Server not ready")
            except requests.exceptions.Timeout:
                if attempt <= 3:
                    _log_debug(verbose, "Request timeout (server slow to respond)")
            except requests.exceptions.RequestException as e:
                if attempt <= 3:
                    _log_debug(
                        verbose,
                        "Request error: %s: %s",
                        type(e).__name__,
                        e,
                    )

        time.sleep(1)

    _log_debug(verbose, "Health check TIMEOUT after %ss", timeout)
    if proc:
        _log_debug(verbose, "Backend process status: %s", proc.poll())
    return False


def wait_for_frontend(port: int, *, timeout: int = 30) -> bool:
    """Wait for frontend to respond to requests.

    Tries both localhost and 127.0.0.1 for maximum compatibility.

    Parameters
    ----------
    port : int
        Frontend port to poll
    timeout : int, default=30
        Maximum seconds to wait

    Returns
    -------
    bool
        True if frontend is ready, False if timeout
    """
    urls = [
        f"http://localhost:{port}",
        f"http://127.0.0.1:{port}",
    ]
    start_time = time.time()

    while time.time() - start_time < timeout:
        for url in urls:
            try:
                response = requests.get(url, timeout=2)
                if response.status_code == 200:
                    return True
            except requests.exceptions.RequestException:
                pass  # Try next URL or wait
        time.sleep(1)

    return False
