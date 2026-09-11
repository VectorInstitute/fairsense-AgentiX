# FairSense-AgentiX

**An agentic fairness and AI-risk analysis platform developed by the [Vector Institute](https://vectorinstitute.ai/).**

[![code checks](https://github.com/VectorInstitute/fairsense-agentix/actions/workflows/code_checks.yml/badge.svg)](https://github.com/VectorInstitute/fairsense-agentix/actions/workflows/code_checks.yml)
[![integration tests](https://github.com/VectorInstitute/fairsense-agentix/actions/workflows/integration_tests.yml/badge.svg)](https://github.com/VectorInstitute/fairsense-agentix/actions/workflows/integration_tests.yml)
[![docs](https://github.com/VectorInstitute/fairsense-agentix/actions/workflows/docs.yml/badge.svg)](https://github.com/VectorInstitute/fairsense-agentix/actions/workflows/docs.yml)
[![codecov](https://codecov.io/github/VectorInstitute/fairsense-agentix/graph/badge.svg?token=83MYFZ3UPA)](https://codecov.io/github/VectorInstitute/fairsense-agentix)
![GitHub License](https://img.shields.io/github/license/VectorInstitute/fairsense-agentix)

---

FairSense-AgentiX is an intelligent bias detection and risk assessment platform that uses **agentic AI workflows** to analyze text, images, and datasets for fairness concerns. Unlike traditional ML classifiers, FairSense employs a reasoning agent that plans, selects tools, critiques outputs, and refines them iteratively.

## ✨ Key Features

- 🤖 **Agentic Reasoning** - ReAct loop with dynamic tool selection and self-critique
- 🔍 **Multi-Modal Analysis** - Text bias detection, image bias detection, and AI risk assessment
- 🛠️ **Flexible Tool Ecosystem** - OCR, Vision-Language Models, embeddings, FAISS, and LLMs
- 🌐 **Production-Ready APIs** - FastAPI REST API + WebSocket streaming + React UI
- ⚙️ **Highly Configurable** - Swap LLM providers, tools, and models on the fly

## 📦 Installation

### From PyPI (Recommended)

```bash
pip install fairsense-agentix
```

#### Optional: PaddleOCR backend

The default OCR backend is Tesseract (CPU-friendly, no extra setup). For GPU-accelerated PaddleOCR (higher accuracy on rotated/complex text), install the `paddle` extra:

```bash
pip install fairsense-agentix[paddle]
```

This pulls in `paddlepaddle`, which has platform-specific wheels and is much heavier — only install if you need it. Once installed, set `FAIRSENSE_OCR_TOOL=paddleocr` (or `auto` to let the runtime pick based on GPU availability).

### From Source

```bash
git clone https://github.com/VectorInstitute/fairsense-agentix.git
cd fairsense-agentix
uv sync
source .venv/bin/activate
```

### Requirements

- **Python 3.12** (3.13 not yet supported)
- **4GB+ RAM** (for ML models)
- **API key** for OpenAI or Anthropic (for LLM functionality)

## 🚀 Quick Start

First point FairSense at a real LLM provider. The default provider is `fake` — it lets the package import and the tests run without an API key, but in that mode every result is a **synthetic placeholder**, not a real analysis (FairSense warns at construction, sets `result.metadata.mock_mode = True`, and prefixes `result.warnings` with `MOCK MODE`).

```bash
export FAIRSENSE_LLM_PROVIDER=openai   # or: anthropic
export FAIRSENSE_LLM_API_KEY=sk-...
```

```python
from fairsense_agentix import FairSense

# Initialize the engine
engine = FairSense()

# Analyze text for bias
result = engine.analyze_text(
    "We're looking for a young, energetic developer to join our startup team."
)

print(f"Bias detected: {result.bias_detected}")
print(f"Risk level: {result.risk_level}")
for instance in result.bias_instances:
    print(f"  - {instance['type']} ({instance['severity']}): {instance['text_span']}")
```

**Full Documentation:** [https://vectorinstitute.github.io/fairsense-agentix/](https://vectorinstitute.github.io/fairsense-agentix/)

---

## 🧑🏿‍💻 Developing

### Installing dependencies

The development environment can be set up using
[uv](https://github.com/astral-sh/uv?tab=readme-ov-file#installation). Hence, make sure it is
installed and then run:

```bash
uv sync
source .venv/bin/activate
```

In order to install dependencies for testing (codestyle, unit tests, integration tests),
run:

```bash
uv sync --dev
source .venv/bin/activate
```

In order to exclude installation of packages from a specific group (e.g. docs),
run:

```bash
uv sync --no-group docs
```
## Getting Started

### Run the FastAPI service

```bash
python -m fairsense_agentix.service_api          # honours FAIRSENSE_API_HOST / PORT
# or: uv run uvicorn fairsense_agentix.service_api.server:app --host 127.0.0.1 --reload
```

Endpoints (all under `/v1/...`):

| Route | Description |
| --- | --- |
| `POST /analyze` | JSON payload with `content`, optional `input_type`, `options` |
| `POST /analyze/upload` | `multipart/form-data` for images |
| `POST /batch` & `GET /batch/{id}` | Submit + inspect batch jobs |
| `GET /health` | Health probe (reports `llm_provider` and `mock_mode`) |
| `POST /shutdown` | Stop the server — disabled by default, see configuration below |
| `WS /stream/{run_id}` | Stream telemetry/agent events for a run |

The API auto-detects text/image/CSV inputs, but you can override by setting `input_type` to `bias_text`, `bias_image`, or `risk`.

### Run the Claude-inspired UI

The UI lives in `ui/` in this repository (it is not part of the PyPI wheel) and needs Node.js:

```bash
cd ui
npm install
npm run dev
```

Or start backend + UI together from the checkout with `python -c "from fairsense_agentix import server; server.start()"`.

Set `VITE_API_BASE` (defaults to `http://localhost:8000`) to point at the API. The UI provides:

- Unified input surface (text field + drag/drop image upload)
- Live agent timeline sourced from telemetry events
- Downloadable HTML highlights and risk tables
- Launchpad for batch jobs

### Key configuration knobs

Configure via environment variables (see `.env` for the full list). Most relevant:

| Variable | Description |
| --- | --- |
| `FAIRSENSE_LLM_PROVIDER` | `openai`, `anthropic`, or `fake` (mock mode — synthetic results, testing only) |
| `FAIRSENSE_LLM_MODEL_NAME` | e.g. `gpt-4`, `claude-3-5-sonnet` |
| `FAIRSENSE_LLM_API_KEY` | Provider API key |
| `FAIRSENSE_LLM_BASE_URL` | Endpoint override for `openai` — point at an OpenAI-compatible server such as Ollama (`http://localhost:11434/v1`) |
| `FAIRSENSE_OCR_TOOL` | `auto`, `tesseract`, `paddleocr`, `fake` |
| `FAIRSENSE_API_HOST` | Bind address (default `127.0.0.1`; set `0.0.0.0` to expose, e.g. in a container) |
| `FAIRSENSE_API_CORS_ORIGINS` | Allowed CORS origins (default: local Vite dev server; `["*"]` to allow any) |
| `FAIRSENSE_API_ENABLE_SHUTDOWN_ENDPOINT` | Expose `POST /v1/shutdown` (default `false`; the launcher enables it) |
| `FAIRSENSE_API_SHUTDOWN_TOKEN` | Secret for `X-Shutdown-Token`; without it shutdown is loopback-only |
| `FAIRSENSE_CAPTION_MODEL` | `auto`, `blip2`, `blip`, `fake` |
| `FAIRSENSE_ENABLE_REFINEMENT` | enables evaluator-driven retries (default `true`) |
| `FAIRSENSE_EVALUATOR_ENABLED` | toggles Phase 7 evaluators |
| `FAIRSENSE_BIAS_EVALUATOR_MIN_SCORE` | passing score (0–100, default 75) |

All settings can be overridden at runtime:

```bash
FAIRSENSE_LLM_PROVIDER=anthropic \
FAIRSENSE_LLM_MODEL_NAME=claude-3-5-sonnet-20241022 \
uv run uvicorn fairsense_agentix.service_api.server:app
```

### Running tests

```bash
uv run pytest
```

During test collection we automatically override any `.env` values that point at
real providers/devices so the suite always uses the lightweight `fake`
toolchain. This guarantees deterministic, offline-friendly tests even if you
have `FAIRSENSE_LLM_PROVIDER=openai` (or Anthropic) configured locally. To opt-in
to exercising the real stack, export `FAIRSENSE_TEST_USE_REAL=1` before running
pytest.

## Acknowledgments

Resources used in preparing this research were provided, in part, by the Province of Ontario, the Government of Canada through CIFAR, and companies sponsoring the Vector Institute.

This research was funded by the European Union's Horizon Europe research and innovation programme under the AIXPERT project (Grant Agreement No. 101214389).

## Contributing
If you are interested in contributing to the library, please see
[CONTRIBUTING.md](CONTRIBUTING.md). This file contains many details around contributing
to the code base, including development practices, code checks, tests, and more.

For support or collaborations: shaina.raza@vectorinstitute.ai
