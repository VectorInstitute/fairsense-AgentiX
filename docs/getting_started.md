# Getting Started with FairSense-AgentiX

This guide will walk you through installing FairSense-AgentiX, configuring it, and running your first bias analysis.

---

## Prerequisites

Before you begin, ensure you have:

- **Python 3.12** installed (3.13 not yet supported)
- **[uv](https://docs.astral.sh/uv/)** package manager (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- **API key** for your chosen LLM provider:
  - [Anthropic](https://console.anthropic.com/) for Claude models (recommended)
  - [OpenAI](https://platform.openai.com/api-keys) for GPT models
- **(Optional)** [Node.js 20+](https://nodejs.org/) for running the React UI

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/VectorInstitute/fairsense-agentix.git
cd fairsense-agentix
```

### 2. Set Up Virtual Environment

FairSense-AgentiX uses `uv` for fast, reliable dependency management:

```bash
# Sync all dependencies (includes dev tools, docs, etc.)
uv sync

# Activate the virtual environment
source .venv/bin/activate  # Linux/macOS
# OR
.venv\Scripts\activate  # Windows
```

If you only need the core runtime (no dev tools):

```bash
uv sync --no-group dev --no-group docs
```

### 3. Configure Environment Variables

Create a `.env` file in the project root using either option below.

**Option A: Copy from template (recommended)**

Use the provided `.env.example` as a starting point—it includes all supported variables and comments:

```bash
cp .env.example .env
```

Then edit `.env` and set at least the **required** values (LLM provider, model, and API key). The template documents optional settings (OCR, vision model, caching, etc.).

**Option B: Create an empty file**

```bash
touch .env
```

Then add the variables yourself. At minimum, set:

```bash
# === REQUIRED ===
FAIRSENSE_LLM_PROVIDER=anthropic  # or 'openai'
FAIRSENSE_LLM_MODEL_NAME=claude-3-5-sonnet-20241022
FAIRSENSE_LLM_API_KEY=sk-ant-your-key-here  # Your Anthropic/OpenAI API key

# === OPTIONAL ===
FAIRSENSE_OCR_TOOL=auto
FAIRSENSE_CAPTION_MODEL=auto
```

!!! tip "Configuration Priority"
    Settings are loaded in this order (highest priority first):

    1. **Shell environment variables** (highest priority)
    2. **`.env` file** in project root
    3. **Default values** in `fairsense_agentix/configs/settings.py`

See the [User Guide](user_guide.md#configuration) for full options. If changes in `.env` don't apply, see [Config & Troubleshooting](config_troubleshooting.md).

### 4. Verify Installation

Test that everything is set up correctly:

```python
# Test import
python -c "from fairsense_agentix import FairSense; print('✅ Installation successful!')"
```

---

## Your First Analysis

!!! warning "Configure a real LLM provider first"
    The default `FAIRSENSE_LLM_PROVIDER` is `fake`, which lets the package import and the
    test suite run without an API key. In that mode `FairSense()` still "works" but every
    result is a **synthetic placeholder**, not a real analysis. FairSense flags this in three
    places: a `MockProviderWarning` at construction, `result.metadata.mock_mode == True`,
    and a `MOCK MODE` entry at the top of `result.warnings`. Set a real provider before
    running the examples below:

    ```bash
    export FAIRSENSE_LLM_PROVIDER=openai        # or: anthropic
    export FAIRSENSE_LLM_API_KEY=sk-...
    ```

### Text Bias Detection

Let's start with a simple text bias analysis:

```python
from fairsense_agentix import FairSense

# Initialize the engine (loads models on first run ~30-45s)
engine = FairSense()

# Analyze a job posting for bias
text = """
We're looking for a young, energetic developer to join our
fast-paced startup team. Ideal candidates are recent college
graduates who can handle the demands of a high-pressure environment.
"""

result = engine.analyze_text(text)

# Print results
print(f"Bias Detected: {result.bias_detected}")
print(f"Risk Level: {result.risk_level}")
print(f"Summary: {result.summary}")

# bias_instances is a list of dicts (or None); use dict .get() access
print(f"\nFound {len(result.bias_instances or [])} bias instances:")
for instance in (result.bias_instances or []):
    print(f"  • {instance.get('type')} ({instance.get('severity')})")
    print(f"    Text: \"{instance.get('text_span')}\"")
    print(f"    Reason: {instance.get('explanation')}\n")
```

**Expected Output:**
```
Bias Detected: True
Risk Level: medium
Summary: The text contains age-related bias ("young", "recent college graduates")
         that may exclude experienced candidates...

Found 2 bias instances:
  • age (high)
    Text: "young, energetic"
    Reason: Age-related descriptors that may discourage older applicants

  • age (medium)
    Text: "recent college graduates"
    Reason: Preference for recent graduates excludes experienced professionals
```

!!! info "First Run Performance"
    The first time you run FairSense, it will download and cache:

    - Embedding models (~500MB)
    - FAISS knowledge indices (~100MB)
    - Vision models (if using image analysis, ~2GB)

    Subsequent runs are **instant** (~100-200ms startup).

### Image Bias Detection

Analyze visual content for representation issues:

```python
from fairsense_agentix import FairSense

engine = FairSense()

# Analyze an image file
with open("team_photo.webp", "rb") as f:
    image_bytes = f.read()

result = engine.analyze_image(image_bytes)

# Image-specific fields: caption_text (VLM caption) and ocr_text (extracted text)
print(f"Caption: {result.caption_text}")
print(f"OCR Text: {result.ocr_text}")
print(f"Bias Detected: {result.bias_detected}")
print(f"Risk Level: {result.risk_level}")
print(f"Summary: {result.summary}")

print(f"\nFound {len(result.bias_instances or [])} bias instances:")
for instance in (result.bias_instances or []):
    print(f"  • {instance.get('type')} ({instance.get('severity')})")
    print(f"    Text: \"{instance.get('text_span')}\"")
    print(f"    Reason: {instance.get('explanation')}\n")
```

### Risk Assessment (CSV/Dataset)

Evaluate ML deployment scenarios for fairness risks:

```python
from fairsense_agentix import FairSense

engine = FairSense()

# Describe your deployment scenario
scenario = """
We are deploying a resume screening AI system using a GPT-4 based LLM to rank
job applicants for software engineering roles. The model was fine-tuned on
5 years of historical hiring decisions from our company. The system will
automatically filter out the bottom 80% of applicants before human review.
Applicants are not informed that AI screening is used.
"""

result = engine.assess_risk(scenario)

# RiskResult exposes status (not risk_level), and `risks` is a list of dicts
print(f"Status: {result.status}")
if result.errors:
    print(f"Errors: {result.errors}")

print(f"\nTop Risks:")
for risk in result.risks[:5]:  # Show top 5
    risk_id = risk.get('id') or risk.get('risk_id', '')
    description = risk.get('description') or risk.get('text', '')
    print(f"  • [{risk_id}] (Score: {risk.get('score', 0):.2f})")
    print(f"    Category: {risk.get('category')}")
    print(f"    {description}\n")
```

!!! note "If `status` is `failed`"
    `status: failed` means the agent's quality evaluator rejected the output (e.g., low FAISS similarity scores against the MIT AI Risk Repository). Check `result.errors` for details. Vague or short scenario descriptions tend to produce low similarity; more specific, domain-relevant scenarios — describing the model, training data, deployment context, and human-impact surface — generally produce higher similarity scores and `status: success`.

---

## Using the Web Interface

The easiest way to use FairSense is through the integrated web UI:

### Launch the Server

**Option 1: Python Script**
```python
from fairsense_agentix import server

# Start both backend and frontend
server.start()
# Opens browser automatically at http://localhost:5173
```

**Option 2: Command Line**
```bash
# Using the examples script
python examples/launch_server.py

# Or directly with Python
python -c "from fairsense_agentix import server; server.start()"

# Using uv
uv run python -c "from fairsense_agentix import server; server.start()"
```

**Option 3: Custom Ports**
```python
from fairsense_agentix import server

server.start(
    port=9000,           # Backend API port
    ui_port=3000,        # Frontend UI port
    open_browser=True,   # Auto-open browser
    verbose=True         # Show server logs
)
```

### What the Server Provides

Once running, you'll have access to:

| Component | URL | Description |
|-----------|-----|-------------|
| **React UI** | http://localhost:5173 | Interactive web interface |
| **Backend API** | http://localhost:8000 | REST API endpoints |
| **API Docs** | http://localhost:8000/docs | Interactive Swagger documentation |
| **WebSocket** | ws://localhost:8000/v1/stream/{run_id} | Real-time agent telemetry |

### Using the UI

The web interface has two pages:

**Landing page (`/`)** — Introduces the platform with a hero section, mode cards (click any card to jump directly into that mode), and a how-it-works overview.

**Analysis app (`/analyze`)** — The main tool. Select a mode from the tab bar at the top:

| Mode | Input | What it detects |
|------|-------|-----------------|
| **Bias (Text)** | Paste text | Gender, age, racial, disability, socioeconomic bias |
| **Bias (Image)** | Upload image | Visual stereotypes, underrepresentation |
| **Risk** | Describe an AI deployment | Fairness, security, compliance risks (sourced from MIT AI Risk Repository) |

Each mode includes **clickable demo examples** on the right — select one to pre-fill the input and run a sample analysis immediately.

Once you submit:

1. **Agent Timeline** (left) — live stream of agent reasoning steps
2. **Results Panel** (right) — structured output:
   - Bias mode: scored instances with highlighted text and severity badges
   - Risk mode: top matched risks with category, relevance score, and link to the MIT AI Risk Repository

**Shutdown Button** — top-right of the app page; gracefully stops both servers.

### Shutdown the Server

**From UI:** Click the red "Shutdown" button in the top-right corner

**From Command Line:** Press `Ctrl+C` in the terminal

---

## Configuration Options

### LLM Provider Selection

FairSense supports multiple LLM backends:

```bash
# Use Claude (recommended for best results)
FAIRSENSE_LLM_PROVIDER=anthropic
FAIRSENSE_LLM_MODEL_NAME=claude-3-5-sonnet-20241022
FAIRSENSE_LLM_API_KEY=sk-ant-...

# Use GPT-4
FAIRSENSE_LLM_PROVIDER=openai
FAIRSENSE_LLM_MODEL_NAME=gpt-4
FAIRSENSE_LLM_API_KEY=sk-...

# Use local model (requires Ollama)
FAIRSENSE_LLM_PROVIDER=openai
FAIRSENSE_LLM_BASE_URL=http://localhost:11434/v1
FAIRSENSE_LLM_MODEL_NAME=llama2
```

### Tool Configuration

Control which tools the agent can use:

```bash
# OCR (text extraction from images)
FAIRSENSE_OCR_TOOL=auto           # Auto-select best available
# or: tesseract, paddleocr, fake (testing)

# Vision-Language Model (image understanding)
FAIRSENSE_CAPTION_MODEL=auto      # Auto-select best available
# or: blip2, blip, fake (testing)

# Embedding Model (semantic search)
FAIRSENSE_EMBEDDING_PROVIDER=auto
# or: sentence-transformers, openai
```

### Refinement & Evaluation

Enable/disable the iterative refinement loop:

```bash
# Enable agent self-critique and refinement
FAIRSENSE_ENABLE_REFINEMENT=true
FAIRSENSE_EVALUATOR_ENABLED=true

# Set quality thresholds (0-100)
FAIRSENSE_BIAS_EVALUATOR_MIN_SCORE=75   # Minimum passing score
FAIRSENSE_MAX_REFINEMENT_ITERATIONS=2    # Limit refinement cycles
```

!!! warning "Performance vs. Quality Trade-off"
    - **Refinement ON** (default): Slower but higher quality outputs (~2-3 min per analysis)
    - **Refinement OFF**: Faster but may miss edge cases (~30-60s per analysis)

    For production use, we recommend keeping refinement enabled.

---

## Troubleshooting

### API Key Issues

**Symptom:** `AuthenticationError` or `401 Unauthorized`

**Solution:**
```bash
# Verify your key is set correctly
echo $FAIRSENSE_LLM_API_KEY  # Should show your key

# If empty, set it:
export FAIRSENSE_LLM_API_KEY=your-key-here

# Or add to .env file
echo "FAIRSENSE_LLM_API_KEY=your-key-here" >> .env
```

### Model Download Timeouts

**Symptom:** First run hangs for 5+ minutes

**Cause:** Downloading large embedding/vision models

**Solution:**
1. Be patient - models only download once (~2GB total)
2. Check your internet connection
3. Models are cached in `~/.cache/huggingface/`

### Port Already in Use

**Symptom:** `Address already in use` error

**Solution:**
```bash
# Find process using port 8000
lsof -ti :8000 | xargs kill -9  # Linux/macOS
netstat -ano | findstr :8000    # Windows (then taskkill)

# Or use custom ports
server.start(port=9000, ui_port=3000)
```

### Memory Issues

**Symptom:** `OutOfMemoryError` or system freezes

**Solution:**
```bash
# Use lighter models
FAIRSENSE_CAPTION_MODEL=fake  # Skip vision model loading
FAIRSENSE_OCR_TOOL=tesseract   # Lighter than PaddleOCR

# Or disable refinement to reduce LLM calls
FAIRSENSE_ENABLE_REFINEMENT=false
```

### Import Errors

**Symptom:** `ModuleNotFoundError: No module named 'fairsense_agentix'`

**Solution:**
```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Reinstall dependencies
uv sync

# Verify installation
python -c "import fairsense_agentix; print('✅ Installed')"
```

---

## Next Steps

Now that you have FairSense-AgentiX running, explore:

- **[User Guide](user_guide.md)** - Detailed examples for each workflow (text, image, risk)
- **[API Reference](api.md)** - Full Python API and REST endpoint documentation
- **[Server Guide](server.md)** - Deployment and production setup
- **[Developer Guide](developers.md)** - Contributing and extending FairSense-AgentiX

---

## Getting Help

- **GitHub Issues**: [Report bugs](https://github.com/VectorInstitute/fairsense-agentix/issues)
- **Discussions**: [Ask questions](https://github.com/VectorInstitute/fairsense-agentix/discussions)
- **Documentation**: You're reading it! 📚
