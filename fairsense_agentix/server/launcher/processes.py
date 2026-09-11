"""Subprocess management for backend and frontend server processes."""

import logging
import os
import platform
import subprocess
import sys
from pathlib import Path


logger = logging.getLogger(__name__)


def _log_debug(verbose: bool, msg: str, *args: object) -> None:
    """Emit a DEBUG log only when verbose=True."""
    if verbose:
        logger.debug(msg, *args)


def start_backend(port: int, *, reload: bool, verbose: bool) -> subprocess.Popen:
    """Start FastAPI backend via uvicorn.

    Runs ``python -m fairsense_agentix.service_api`` so it works both from a
    source checkout and from an installed wheel.

    Parameters
    ----------
    port : int
        Port to bind the backend to
    reload : bool
        Enable uvicorn auto-reload
    verbose : bool
        Stream backend logs to stdout (False = suppress)

    Returns
    -------
    subprocess.Popen
        Backend process handle
    """
    env = os.environ.copy()
    env["FAIRSENSE_API_PORT"] = str(port)
    env["FAIRSENSE_API_RELOAD"] = "true" if reload else "false"
    # The bundled UI has a "stop server" button. The endpoint is off by default
    # and, without a token, only accepts loopback clients — so this is safe for
    # the local launcher but never exposed by a plain `uvicorn` deployment.
    env.setdefault("FAIRSENSE_API_ENABLE_SHUTDOWN_ENDPOINT", "true")

    # CRITICAL: Re-enable eager loading for backend subprocess.
    # The parent process has FAIRSENSE_DISABLE_EAGER_LOADING=true
    # (set in server/__init__.py) but backend MUST load models.
    if "FAIRSENSE_DISABLE_EAGER_LOADING" in env:
        del env["FAIRSENSE_DISABLE_EAGER_LOADING"]
        _log_debug(verbose, "Re-enabled eager loading for backend subprocess")

    cmd = [sys.executable, "-m", "fairsense_agentix.service_api"]

    _log_debug(verbose, "Backend command: %s", " ".join(cmd))
    _log_debug(verbose, "Python executable: %s", sys.executable)
    _log_debug(verbose, "Backend port: %s", port)

    _log_debug(verbose, "Starting backend subprocess...")
    if verbose:
        proc = subprocess.Popen(cmd, env=env)
    else:
        proc = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    _log_debug(verbose, "Backend process started with PID: %s", proc.pid)
    _log_debug(verbose, "Process poll status: %s", proc.poll())
    return proc


def find_ui_dir() -> Path | None:
    """Locate the React UI source (``ui/`` at the repository root).

    The UI is not part of the published wheel, so this returns ``None`` for a
    PyPI install; callers should fall back to backend-only mode.
    """
    ui_dir = Path(__file__).parent.parent.parent.parent / "ui"
    return ui_dir if (ui_dir / "package.json").exists() else None


def start_frontend(
    backend_port: int,
    frontend_port: int,
    *,
    verbose: bool,
) -> subprocess.Popen:
    """Start Vite dev server for React UI.

    Parameters
    ----------
    backend_port : int
        Backend port (passed to Vite as VITE_API_BASE)
    frontend_port : int
        Port to bind the frontend to
    verbose : bool
        Stream frontend logs to stdout (False = suppress)

    Returns
    -------
    subprocess.Popen
        Frontend process handle

    Raises
    ------
    FileNotFoundError
        If npm not found or UI directory missing
    RuntimeError
        If npm install fails
    """
    env = os.environ.copy()
    env["VITE_API_BASE"] = f"http://localhost:{backend_port}"

    ui_dir = find_ui_dir()

    if ui_dir is None:
        raise FileNotFoundError(
            "UI directory not found. The web UI ships only with the source "
            "checkout (git clone), not with the PyPI wheel.",
        )

    node_modules = ui_dir / "node_modules"
    if not node_modules.exists():
        logger.info("⚠️  Node modules not found. Installing dependencies...")
        logger.info("   This is a one-time setup (may take 1-2 minutes)...")
        install_proc = subprocess.run(
            ["npm", "install"],
            check=False,
            cwd=str(ui_dir),
            capture_output=not verbose,
        )
        if install_proc.returncode != 0:
            raise RuntimeError(
                "npm install failed. Check your internet connection and try again.",
            )

    cmd = ["npm", "run", "dev", "--", "--port", str(frontend_port), "--strictPort"]

    if verbose:
        proc = subprocess.Popen(cmd, cwd=str(ui_dir), env=env)
    else:
        proc = subprocess.Popen(
            cmd,
            cwd=str(ui_dir),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    _log_debug(verbose, "Frontend process started with PID: %s", proc.pid)
    return proc


def kill_port(port: int, *, verbose: bool) -> None:
    """Kill any process listening on the specified port.

    Fallback cleanup for when processes don't exit cleanly.

    Parameters
    ----------
    port : int
        Port to free up
    verbose : bool
        Whether to emit debug logs
    """
    try:
        system = platform.system()
        if system == "Windows":
            subprocess.run(
                (
                    f'for /f "tokens=5" %a in '
                    f"('netstat -aon ^| findstr :{port}') "
                    f"do taskkill /F /PID %a"
                ),
                check=False,
                shell=True,
                capture_output=True,
            )
        else:
            subprocess.run(
                f"lsof -ti :{port} | xargs kill -9",
                check=False,
                shell=True,
                capture_output=True,
            )
        _log_debug(verbose, "Cleaned up port %s", port)
    except Exception as e:
        logger.warning("Port cleanup warning: %s", e)
