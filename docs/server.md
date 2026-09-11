# Server Guide

This guide covers running the FastAPI backend and React UI for FairSense-AgentiX, including the programmatic server launcher and manual startup.

---

## Quick Start (Programmatic Launcher)

Start both the FastAPI backend and React frontend with a single call:

```python
from fairsense_agentix import server

server.start()
```

This will:

- Start FastAPI backend on http://localhost:8000
- Start React UI on http://localhost:5173
- Auto-open your browser
- Wait for both services to be ready (health checks)
- Gracefully shutdown on Ctrl+C

!!! note "Source checkout vs. `pip install`"
    The React UI lives in `ui/` in the git repository and is **not** included in the PyPI wheel. From a `pip install fairsense-agentix` environment, `server.start()` runs the backend only (it prints a notice and the API docs URL); to use the web UI, clone the repository and install Node.js. `server.start(ui=False)` requests backend-only mode explicitly.

Options: `port`, `ui_port`, `open_browser`, `verbose`, `reload`, `ui`, `frontend_timeout` (seconds to wait for Vite; default 60).

---

## Manual Startup

### Backend only

```bash
# Reads FAIRSENSE_API_HOST / FAIRSENSE_API_PORT / FAIRSENSE_API_RELOAD from the environment
python -m fairsense_agentix.service_api

# Or with uvicorn directly (note: uvicorn ignores FAIRSENSE_API_HOST/PORT — pass them here)
uv run uvicorn fairsense_agentix.service_api.server:app --host 127.0.0.1 --port 8000 --reload
```

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### React UI (after backend is running)

```bash
cd ui
npm install
npm run dev
```

Set `VITE_API_BASE` to your backend URL (default: `http://localhost:8000`).

---

## Launcher Usage

### Custom Ports

```python
server.start(port=9000, ui_port=3000)
```

### Development Mode (Auto-Reload)

```python
server.start(reload=True)
```

Backend auto-reloads when you edit prompts in `fairsense_agentix/prompts/templates/`, modify `.env`, or change tool parameters.

### Headless (No Browser)

```python
server.start(open_browser=False)
```

---

## Configuration Options

```python
def start(
    port: int = 8000,          # FastAPI backend port
    ui_port: int = 5173,       # React UI port (Vite default)
    open_browser: bool = True, # Auto-open browser
    verbose: bool = True,      # Stream logs to stdout
    reload: bool = False       # Enable auto-reload
) -> None:
```

---

## Requirements

- **Python 3.12** with fairsense-agentix installed (`uv sync` or `pip install -e .`) — 3.13 not yet supported
- **Node.js 20+** and npm for the React UI

---

## Troubleshooting

### Backend failed to start on port 8000

Port may be in use. Check and free it:

```bash
# macOS/Linux
lsof -i :8000

# Windows
netstat -ano | findstr :8000
```

Or use another port: `server.start(port=9000)`.

### Frontend failed to start on port 5173

Install UI dependencies:

```bash
cd ui
npm install
```

Or use another port: `server.start(ui_port=3000)`.

### Backend startup is slow (30–45s)

Normal on first run. The backend loads LLM clients, embedding models (~90MB), FAISS indexes, and optionally OCR/caption models. Later starts are much faster (~5–10s).

---

## Testing

Run server launcher tests:

```bash
uv run pytest tests/test_server_launcher.py -v
```

Manual check:

```bash
uv run python examples/launch_server.py
```

Then verify the browser opens, the UI loads, and a text analysis works; press Ctrl+C to stop both servers.

---

## See Also

- [Getting Started](getting_started.md) – Installation and configuration
- [API Reference](api.md) – REST and Python API
- [API docs (when running)](http://localhost:8000/docs)
