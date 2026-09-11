# User Guide

This guide provides detailed examples and best practices for using FairSense-AgentiX in your applications.

---

## Overview

FairSense-AgentiX provides three main analysis workflows:

1. **Text Bias Detection** - Analyze written content for fairness issues
2. **Image Bias Detection** - Analyze visual content for representation problems
3. **Risk Assessment** - Evaluate ML deployment scenarios for compliance risks

Each workflow uses an **agentic reasoning system** that:
- Plans its analysis strategy
- Selects appropriate tools dynamically
- Iteratively refines outputs based on self-critique
- Provides full transparency via event telemetry

---

## Text Bias Analysis

### Basic Usage

```python
from fairsense_agentix import FairSense

engine = FairSense()

text = """
We need a rockstar developer who's a cultural fit for our young,
dynamic team. Must be willing to work long hours and weekends.
"""

result = engine.analyze_text(text)

# Access results
print(f"Bias Detected: {result.bias_detected}")
print(f"Risk Level: {result.risk_level}")
print(f"Summary: {result.summary}")

# Iterate through bias instances (each is a dict, not an object)
for instance in (result.bias_instances or []):
    print(f"\nType: {instance.get('type')}")
    print(f"Severity: {instance.get('severity')}")
    print(f"Text: '{instance.get('text_span')}'")
    print(f"Explanation: {instance.get('explanation')}")
```

### Understanding the Result Object

The `BiasResult` object contains:

| Field | Type | Description |
|-------|------|-------------|
| `status` | `str` | Execution status: `success`, `failed`, or `partial` |
| `bias_detected` | `bool \| None` | Whether any bias was found |
| `risk_level` | `str \| None` | Overall severity: `low`, `medium`, `high` |
| `summary` | `str \| None` | High-level explanation of findings |
| `bias_instances` | `list[dict] \| None` | Detailed bias findings (list of dicts) |
| `highlighted_html` | `str \| None` | HTML with color-coded highlights |
| `metadata` | `ResultMetadata` | Execution details (time, model, workflow ID) |
| `errors` | `list[str]` | Error messages (empty if successful) |
| `warnings` | `list[str]` | Warning messages (empty if none) |

For image analysis, the result also includes `caption_text`, `ocr_text`, `merged_text`, and `image_base64`. See the [API Reference](api.md).

**`bias_instances` dict keys:**

Each item in `result.bias_instances` is a `dict` with these keys (use `.get(...)` for safe access):

| Key | Type | Description |
|-----|------|-------------|
| `type` | `str` | Bias category: `gender`, `age`, `racial`, `disability`, `socioeconomic` |
| `severity` | `str` | Impact level: `low`, `medium`, `high` |
| `text_span` | `str` | The problematic text excerpt |
| `explanation` | `str` | Why this is biased |

### Advanced: Highlighted HTML Output

FairSense generates color-coded HTML for easy visualization:

```python
result = engine.analyze_text(text)

# Save highlighted version
with open("analysis_output.html", "w") as f:
    f.write(result.highlighted_html)

# Or display in Jupyter
from IPython.display import HTML
HTML(result.highlighted_html)
```

The HTML uses color coding:

- 🟥 **Red** - Gender bias
- 🟧 **Orange** - Age bias
- 🟨 **Yellow** - Racial bias
- 🟦 **Blue** - Disability bias
- 🟪 **Purple** - Socioeconomic bias

### Common Use Cases

#### Job Postings

```python
job_posting = """
Job Title: Senior Software Engineer

Requirements:
- Recent CS graduate preferred
- Native English speaker
- Must be able to work in a fast-paced environment
- Looking for someone who's a culture fit
"""

result = engine.analyze_text(job_posting)

# Check for hiring-related biases
for instance in (result.bias_instances or []):
    if instance.get("type") in ["age", "racial"]:
        print(f"⚠️  Legal Risk: {instance.get('text_span')}")
        print(f"   Explanation: {instance.get('explanation')}")
```

#### Marketing Copy

```python
ad_copy = """
Our product is designed for busy moms who need quick solutions
to help them manage their households while looking their best.
"""

result = engine.analyze_text(ad_copy)

# Identify gender stereotyping
gender_biases = [
    i for i in (result.bias_instances or []) if i.get("type") == "gender"
]
print(f"Found {len(gender_biases)} gender-related issues")
```

#### Content Moderation

```python
user_comment = """
This feature is so easy to use, even my grandma could figure it out!
"""

result = engine.analyze_text(user_comment)

if result.bias_detected:
    print(f"⚠️  Flagged for review: {result.summary}")
```

---

## Image Bias Analysis

### Basic Usage

```python
from fairsense_agentix import FairSense

engine = FairSense()

# Load image file
with open("team_photo.jpg", "rb") as f:
    image_bytes = f.read()

result = engine.analyze_image(image_bytes)

# Access results — image-specific fields are caption_text and ocr_text
print(f"Caption: {result.caption_text}")
print(f"OCR Text: {result.ocr_text}")
print(f"Bias Detected: {result.bias_detected}")
print(f"Risk Level: {result.risk_level}")
print(f"Summary: {result.summary}")

# Bias instances for images (each is a dict with the same keys as text bias)
for instance in (result.bias_instances or []):
    print(f"\nType: {instance.get('type')}")
    print(f"Severity: {instance.get('severity')}")
    print(f"Text: '{instance.get('text_span')}'")
    print(f"Explanation: {instance.get('explanation')}")
```

### Image Result Object

`analyze_image()` returns a `BiasResult` (the same type as `analyze_text()`). The image-specific fields populated are:

| Field | Type | Description |
|-------|------|-------------|
| `caption_text` | `str \| None` | Generated image caption from the VLM |
| `ocr_text` | `str \| None` | Text extracted from the image via OCR |
| `merged_text` | `str \| None` | Combined OCR + caption text used for analysis |
| `image_base64` | `str \| None` | Base64-encoded image with data URL (for UI display) |

All other fields (`status`, `bias_detected`, `risk_level`, `summary`, `bias_instances`, `highlighted_html`, `metadata`, `errors`, `warnings`) work the same as for text analysis. See the [API Reference](api.md) for the full schema.

### Working with Different Image Sources

#### From File

```python
with open("advertisement.png", "rb") as f:
    result = engine.analyze_image(f.read())
```

#### From URL

```python
import requests

url = "https://example.com/marketing-image.jpg"
image_bytes = requests.get(url).content
result = engine.analyze_image(image_bytes)
```

#### From PIL Image

```python
from PIL import Image
import io

# Load and process PIL image
pil_image = Image.open("photo.jpg")

# Convert to bytes
buffer = io.BytesIO()
pil_image.save(buffer, format="JPEG")
image_bytes = buffer.getvalue()

result = engine.analyze_image(image_bytes)
```

### Common Use Cases

#### Stock Photo Auditing

```python
import os

# Analyze a directory of stock photos
for filename in os.listdir("stock_photos/"):
    if filename.endswith((".jpg", ".png")):
        with open(f"stock_photos/{filename}", "rb") as f:
            result = engine.analyze_image(f.read())

        if result.bias_detected:
            print(f"\n⚠️  {filename}")
            print(f"   Risk: {result.risk_level}")
            print(f"   Issue: {result.summary}")
```

#### Marketing Material Review

```python
# Check ad campaign images
campaign_images = ["ad_1.jpg", "ad_2.jpg", "ad_3.jpg"]

issues = []
for img_path in campaign_images:
    with open(img_path, "rb") as f:
        result = engine.analyze_image(f.read())

    if result.risk_level in ["medium", "high"]:
        issues.append({
            "file": img_path,
            "issues": result.bias_instances,
            "caption": result.caption_text,
            "ocr_text": result.ocr_text,
        })

# Generate report
if issues:
    print(f"Found {len(issues)} images needing review")
```

---

## Risk Assessment

### Basic Usage

```python
from fairsense_agentix import FairSense

engine = FairSense()

scenario = """
We're deploying a loan approval system that uses historical data
from the past 10 years. The model uses applicant income, credit score,
employment history, and zip code to predict default risk.
"""

result = engine.assess_risk(scenario)

# Access results — RiskResult uses `status`, not `risk_level`
print(f"Status: {result.status}")
if result.errors:
    print(f"Errors: {result.errors}")
print(f"Total Risks Identified: {len(result.risks)}")

# Top risks (each is a dict — use .get() for safe access)
for risk in result.risks[:5]:
    risk_id = risk.get("id") or risk.get("risk_id", "")
    description = risk.get("description") or risk.get("text", "")
    print(f"\n[{risk_id}] (Relevance: {risk.get('score', 0):.2f})")
    print(f"  Category: {risk.get('category')}")
    print(f"  Description: {description}")
```

### Risk Result Object

| Field | Type | Description |
|-------|------|-------------|
| `status` | `str` | Execution status: `success`, `failed`, or `partial` |
| `risks` | `list[dict]` | Identified risks, sorted by relevance score |
| `rmf_recommendations` | `dict[str, list[dict]]` | NIST AI-RMF recommendations keyed by risk ID |
| `embedding` | `list[float] \| None` | Vector embedding of the scenario |
| `html_table` | `str \| None` | Formatted HTML table of risks + recommendations |
| `csv_path` | `str \| None` | Path to exported CSV file |
| `metadata` | `ResultMetadata` | Execution details |
| `errors` | `list[str]` | Error messages (empty if successful) |
| `warnings` | `list[str]` | Warning messages (empty if none) |

**`risks` dict keys:**

Each item in `result.risks` is a `dict`. Use `.get(...)` for safe access since key names can vary between sources:

| Key | Type | Description |
|-----|------|-------------|
| `id` | `str` | Risk identifier from the source repository (e.g. `RISK0669`) |
| `risk_name` | `str` | Short risk title from the repository |
| `description` | `str` | Full risk description (`text` holds the same value) |
| `category` | `str` | Domain taxonomy label, `"<domain>.<subdomain> > <name>"` (e.g. `1.1 > Unfair discrimination and misrepresentation`) |
| `severity` | `str` | `LOW`, `MEDIUM`, or `HIGH` |
| `score` | `float` | Relevance score (0–1) — FAISS semantic similarity to the query |
| `rank` | `int` | Position in the retrieved list (0 = most relevant) |

**`rmf_recommendations` values:**

`result.rmf_recommendations` maps each risk `id` to a list of recommendation dicts:

| Key | Type | Description |
|-----|------|-------------|
| `id` | `str` | Recommendation identifier (e.g. `RMF0027`) |
| `risk_id` | `str` | Risk the recommendation was authored for |
| `function` | `str` | NIST AI RMF core function: `GOVERN`, `MAP`, `MEASURE`, or `MANAGE` |
| `action` | `str` | Recommended action (`text` holds the same value) |
| `priority` | `str` | `LOW`, `MEDIUM`, or `HIGH` |
| `score` | `float` | Similarity between the risk description and the recommendation |
| `rank` | `int` | Position within the list for that risk |

!!! note "What the recommendations are"
    The recommendations are **not** text extracted from the NIST AI RMF and carry no NIST control identifiers. They are a curated set of action templates, assigned to each repository risk by its domain and mapped onto the four RMF functions, then indexed for retrieval. See `scripts/transform_mit_data.py` for how they are built.

!!! note "Risk source"
    Risks are retrieved from the [MIT AI Risk Repository](https://airisk.mit.edu/) (V3, 1,340 entries) using semantic similarity search. The `category` field follows the repository's Domain Taxonomy; the number prefix (e.g., `3.1`) identifies the domain and subcategory. A score of `1.0` means the risk is maximally relevant to the described scenario; `0.0` means unrelated.

!!! warning "If `result.status` is `failed`"
    `status: failed` means the agent's quality evaluator rejected the output (e.g., low FAISS similarity scores against the MIT AI Risk Repository). Check `result.errors` for details. Vague or short scenario descriptions tend to produce low similarity; more specific, domain-relevant scenarios — describing the model, training data, deployment context, and human-impact surface — generally produce higher similarity scores and `status: success`.

### CSV Dataset Analysis

For structured data, you can provide CSV content directly:

```python
csv_data = """
age,gender,income,approved
25,M,50000,1
45,F,60000,0
30,M,55000,1
"""

# Describe the context
context = """
This is training data for a loan approval model. The 'approved' column
indicates whether the loan was historically approved (1) or denied (0).
"""

result = engine.assess_risk(context + "\n\n" + csv_data)

# Check for discrimination risks (repository domain 1 = "Discrimination & toxicity")
fairness_risks = [r for r in result.risks if r["category"].startswith("1.")]
print(f"Found {len(fairness_risks)} discrimination-related concerns")
```

### Common Use Cases

#### Pre-Deployment Audit

```python
deployment_plan = """
Model: GPT-4 fine-tuned on customer service transcripts
Use Case: Automated response generation for support tickets
Training Data: 500k customer interactions from 2020-2024
Deployment: Production API serving 10k requests/day
Monitoring: None currently planned
"""

result = engine.assess_risk(deployment_plan)

# Check high-relevance risks (score > 0.7 = strong semantic match)
critical = [r for r in result.risks if r.get("score", 0) > 0.7]
if critical:
    print("🚨 HIGH-RELEVANCE RISKS DETECTED")
    for risk in critical:
        risk_id = risk.get("id") or risk.get("risk_id", "")
        description = risk.get("description") or risk.get("text", "")
        print(f"  • [{risk_id}]: {description}")
```

#### Governance Actions per Risk

```python
result = engine.assess_risk(scenario)

# For each retrieved risk, list the GOVERN-function recommendations
for risk in result.risks:
    recs = result.rmf_recommendations.get(risk["id"], [])
    govern = [rec for rec in recs if rec["function"] == "GOVERN"]
    print(f"\n⚖️  [{risk['id']}] {risk['risk_name']} (score: {risk['score']:.2f})")
    for rec in govern:
        print(f"   - ({rec['priority']}) {rec['action']}")
```

#### Vendor Assessment

```python
vendor_proposal = """
Vendor: ThirdParty ML Inc.
Product: Resume Screening AI
Claims: 95% accuracy, reduces hiring time by 60%
Training Data: Proprietary dataset (details not disclosed)
Explainability: Black-box model
"""

result = engine.assess_risk(vendor_proposal)

# Generate vendor scorecard
avg_score = (
    sum(r.get("score", 0) for r in result.risks) / len(result.risks)
    if result.risks
    else 0
)
print(f"Avg Relevance Score: {avg_score:.2f}")
print(
    f"High-Relevance Concerns: "
    f"{len([r for r in result.risks if r.get('score', 0) > 0.6])}"
)
```

---

## Using the Web Interface

The web UI is the easiest way to run analyses interactively.

### Launch

```bash
python examples/launch_server.py
# Or: python -c "from fairsense_agentix import server; server.start()"
```

This starts the backend API at `http://localhost:8000` and opens the React UI at `http://localhost:5173`.

### Landing Page

When you open the UI you arrive at the **landing page**, which introduces the platform and shows three analysis mode cards (**Bias (Text)**, **Bias (Image)**, **Risk**). Click any card to jump directly to that mode in the analysis app.

The page background features a subtle dot grid and a pink gradient at the top — consistent with the FairSense brand accent colors.

### Analysis App (`/analyze`)

Select a mode from the tab bar at the top:

| Mode | Input | What it detects |
|------|-------|-----------------|
| **Bias (Text)** | Paste or type text | Gender, age, racial, disability, socioeconomic bias |
| **Bias (Image)** | Upload an image | Visual stereotypes, underrepresentation |
| **Risk** | Describe an AI deployment | Fairness, security, compliance risks (MIT AI Risk Repository) |

Each mode includes **clickable demo examples** in the right column — select one to pre-fill the input and run an analysis immediately without typing anything.

### Reading Results

**Bias results** — scored instances listed with the affected text span, bias type badge (color-coded by category), and a plain-language explanation.

**Risk results** — the top semantically matched risks from the [MIT AI Risk Repository](https://airisk.mit.edu/), each showing:

| UI element | Dict key | Notes |
|---|---|---|
| Title | `id` (or `risk_id`) | Risk identifier from the repository |
| Category label | `category` | MIT Domain Taxonomy label, e.g. `3.1 AI system safety failures`. Hover the ⓘ on the first card for a tooltip explaining the taxonomy. |
| Score badge | `score` | Relevance score 0–1 (FAISS semantic similarity). Higher = closer match to your scenario. |
| Description | `description` (or `text`) | Full risk description (academic citations stripped for readability) |

A **"MIT AI Risk Repository ↗"** link in the results header opens the full database for deeper exploration.

### Shutdown

Click the red **Shutdown** button in the top-right corner of the app page to gracefully stop both servers, or press `Ctrl+C` in the terminal.

---

## Configuration

### Environment Variables

All settings can be configured via environment variables or the `.env` file:

```bash
# === Core LLM Settings ===
FAIRSENSE_LLM_PROVIDER=anthropic
FAIRSENSE_LLM_MODEL_NAME=claude-3-5-sonnet-20241022
FAIRSENSE_LLM_API_KEY=your-key-here
FAIRSENSE_LLM_TEMPERATURE=0.7
FAIRSENSE_LLM_MAX_TOKENS=4096

# === Tool Selection ===
FAIRSENSE_OCR_TOOL=auto              # tesseract, paddleocr, fake
FAIRSENSE_CAPTION_MODEL=auto         # blip, blip2, fake
FAIRSENSE_EMBEDDING_PROVIDER=auto    # sentence-transformers, openai

# === Agent Behavior ===
FAIRSENSE_ENABLE_REFINEMENT=true     # Enable self-critique loop
FAIRSENSE_MAX_REFINEMENT_ITERATIONS=2
FAIRSENSE_EVALUATOR_ENABLED=true
FAIRSENSE_BIAS_EVALUATOR_MIN_SCORE=75

# === Performance ===
FAIRSENSE_WORKFLOW_TIMEOUT_SECONDS=300
FAIRSENSE_CACHE_ENABLED=true
FAIRSENSE_CACHE_TTL_SECONDS=3600

# === Server Settings ===
FAIRSENSE_API_HOST=127.0.0.1              # 0.0.0.0 to expose (e.g. in a container)
FAIRSENSE_API_PORT=8000
FAIRSENSE_API_RELOAD=false
FAIRSENSE_API_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
FAIRSENSE_API_ENABLE_SHUTDOWN_ENDPOINT=false
# FAIRSENSE_API_SHUTDOWN_TOKEN=change-me  # required for remote /v1/shutdown
```

### Programmatic Configuration

Settings are read from the environment (and `.env`) **once, when `fairsense_agentix` is first imported**, into a module-level singleton that the tool registry and every workflow share. `FairSense()` takes no arguments; to configure it from code, set the environment variables *before* the import:

```python
import os

os.environ["FAIRSENSE_LLM_PROVIDER"] = "anthropic"
os.environ["FAIRSENSE_LLM_MODEL_NAME"] = "claude-3-5-sonnet-20241022"
os.environ["FAIRSENSE_LLM_API_KEY"] = "sk-ant-..."
os.environ["FAIRSENSE_ENABLE_REFINEMENT"] = "false"  # faster, no critique pass

from fairsense_agentix import FairSense  # noqa: E402  (import after configuring)

engine = FairSense()
```

`Settings()` can still be instantiated directly (e.g. to validate a configuration or inspect defaults), but a new instance is not picked up by an existing engine.

### Per-Analysis Options

Pass options to individual analysis calls:

```python
# Disable refinement for this specific analysis
result = engine.analyze_text(
    text,
    enable_refinement=False,  # Skip self-critique
    max_refinement_iterations=0
)

# Adjust LLM temperature
result = engine.analyze_text(
    text,
    llm_temperature=0.3  # More deterministic
)
```

---

## Batch Processing

Process multiple items efficiently using the batch API:

### Using the Python API

```python
from fairsense_agentix import FairSense

engine = FairSense()

# Prepare batch items
texts = [
    "Job posting 1...",
    "Job posting 2...",
    "Job posting 3...",
]

# Process in batch (runs sequentially with progress tracking)
results = []
for i, text in enumerate(texts, 1):
    print(f"Processing {i}/{len(texts)}...")
    result = engine.analyze_text(text)
    results.append(result)

# Aggregate results
biased_count = sum(1 for r in results if r.bias_detected)
print(f"\n{biased_count}/{len(results)} items flagged")
```

### Using the REST API

```python
import requests
import time

# Submit batch job
batch_request = {
    "items": [
        {"content": "Text 1", "input_type": "bias_text"},
        {"content": "Text 2", "input_type": "bias_text"},
        {"content": "Text 3", "input_type": "bias_text"},
    ]
}

response = requests.post(
    "http://localhost:8000/v1/batch",
    json=batch_request
)
job_id = response.json()["job_id"]

# Poll for completion
while True:
    status_response = requests.get(
        f"http://localhost:8000/v1/batch/{job_id}"
    )
    status = status_response.json()

    print(f"Progress: {status['completed']}/{status['total']}")

    if status["status"] in ["completed", "failed"]:
        break

    time.sleep(5)

# Access results
results = status["results"]
```

---

## REST API Usage

### Analyze Text

```python
import requests

response = requests.post(
    "http://localhost:8000/v1/analyze",
    json={
        "content": "Your text here...",
        "input_type": "bias_text",  # Optional: auto-detected if omitted
        "options": {}  # Optional configuration
    }
)

result = response.json()
print(result["bias_detected"])
```

### Analyze Image (File Upload)

```python
import requests

with open("image.jpg", "rb") as f:
    files = {"file": f}
    data = {"input_type": "bias_image"}

    response = requests.post(
        "http://localhost:8000/v1/analyze/upload",
        files=files,
        data=data
    )

result = response.json()
```

### WebSocket Streaming (Real-Time Events)

```python
import websockets
import asyncio
import json
import requests

async def stream_analysis():
    # Start analysis
    response = requests.post(
        "http://localhost:8000/v1/analyze/start",
        json={"content": "Text to analyze..."}
    )
    run_id = response.json()["run_id"]

    # Connect to event stream
    uri = f"ws://localhost:8000/v1/stream/{run_id}"
    async with websockets.connect(uri) as websocket:
        async for message in websocket:
            event = json.loads(message)

            print(f"[{event['level']}] {event['event']} {event['context']}")

            # Check for completion (result is the full AnalyzeResponse)
            if event["event"] == "analysis_complete":
                result = event["context"]["result"]
                bias = result["bias_result"]
                print(f"\n✅ Complete: {bias['summary']}")
                break
            if event["event"] == "analysis_error":
                print(f"\n❌ Failed: {event['context']['message']}")
                break

asyncio.run(stream_analysis())
```

### Health Check

```python
import requests

response = requests.get("http://localhost:8000/v1/health")
print(response.json())  # {"status": "ok"}
```

---

## Best Practices

### 1. Use Refinement for Critical Applications

```python
# Production: Enable refinement for high-stakes use cases
result = engine.analyze_text(
    job_posting,
    enable_refinement=True,
    max_refinement_iterations=2
)

# Development/Testing: Disable for speed
result = engine.analyze_text(
    test_text,
    enable_refinement=False
)
```

### 2. Cache Results

LLM responses are cached in SQLite (`FAIRSENSE_LLM_CACHE_ENABLED=true`, the default), so re-analysing identical content does not spend API calls:

```bash
FAIRSENSE_LLM_CACHE_ENABLED=true
FAIRSENSE_LLM_CACHE_PATH=.cache/langchain.db
```

### 3. Handle Errors Gracefully

```python
from fairsense_agentix import FairSense

engine = FairSense()

try:
    result = engine.analyze_text(text)
except Exception as e:
    print(f"Analysis failed: {e}")
    # Fallback logic or error reporting
```

### 4. Monitor Execution Time

```python
result = engine.analyze_text(text)

# Check performance
exec_time = result.metadata.execution_time_seconds
print(f"Completed in {exec_time:.2f}s")

if exec_time > 60:
    print("⚠️  Slow analysis - consider disabling refinement")
```

### 5. Aggregate Results for Reporting

```python
# Process multiple documents
results = [engine.analyze_text(doc) for doc in documents]

# Generate summary report
total_biases = sum(len(r.bias_instances or []) for r in results)
avg_risk = sum(1 for r in results if r.risk_level == "high") / len(results)

print(f"Analysis Summary:")
print(f"  Documents: {len(results)}")
print(f"  Total Biases: {total_biases}")
print(f"  High Risk: {avg_risk * 100:.1f}%")
```

---

## Next Steps

- **[API Reference](api.md)** - Complete API documentation
- **[Server Guide](server.md)** - Running the web interface and REST API
- **[GitHub Examples](https://github.com/VectorInstitute/fairsense-agentix/tree/main/examples)** - Additional code samples

---

## Troubleshooting

### "Analysis taking too long"

**Cause:** Refinement loop running multiple iterations

**Solution:**
```python
# Reduce refinement iterations
result = engine.analyze_text(
    text,
    max_refinement_iterations=1
)

# Or disable entirely
result = engine.analyze_text(text, enable_refinement=False)
```

### "Model download failed"

**Cause:** Network issues or disk space

**Solution:**
1. Check internet connection
2. Verify disk space: `df -h ~/.cache/huggingface`
3. Clear cache if needed: `rm -rf ~/.cache/huggingface`

### "API rate limit exceeded"

**Cause:** Too many LLM API calls

**Solution:**
```bash
# Keep the LLM response cache on (default) so repeated inputs are not re-sent
FAIRSENSE_LLM_CACHE_ENABLED=true

# Or run against a local OpenAI-compatible server (Ollama, vLLM, ...)
FAIRSENSE_LLM_PROVIDER=openai
FAIRSENSE_LLM_BASE_URL=http://localhost:11434/v1
FAIRSENSE_LLM_MODEL_NAME=llama3.1
FAIRSENSE_LLM_API_KEY=ollama
```

---

**Need more help?** Check the [Getting Started](getting_started.md) guide or [open an issue](https://github.com/VectorInstitute/fairsense-agentix/issues).
