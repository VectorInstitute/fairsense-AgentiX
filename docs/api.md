# API Reference

This page documents the complete FairSense-AgentiX API, including the Python API and REST API endpoints.

---

## Python API

The Python API provides a clean, Pydantic-based interface for bias detection and risk assessment. All classes are FastAPI-compatible and type-safe.

### FairSense Class

The main entry point for programmatic bias detection and risk assessment.

::: fairsense_agentix.api.FairSense
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      members_order: source
      heading_level: 4

---

### Result Objects

Result objects are Pydantic models that provide type-safe access to analysis outputs.

#### BiasResult

Returned by `analyze_text()` and `analyze_image()` methods.

::: fairsense_agentix.api.BiasResult
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      members:
        - status
        - bias_detected
        - risk_level
        - bias_analysis
        - bias_instances
        - summary
        - highlighted_html
        - ocr_text
        - caption_text
        - merged_text
        - image_base64
        - metadata
        - errors
        - warnings
      heading_level: 5

#### RiskResult

Returned by `assess_risk()` method.

::: fairsense_agentix.api.RiskResult
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      members:
        - status
        - embedding
        - risks
        - rmf_recommendations
        - html_table
        - csv_path
        - metadata
        - errors
        - warnings
      heading_level: 5

#### ResultMetadata

Execution metadata included in all results.

::: fairsense_agentix.api.ResultMetadata
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      members:
        - run_id
        - workflow_id
        - execution_time_seconds
        - router_reasoning
        - router_confidence
        - refinement_count
        - preflight_score
        - posthoc_score
        - llm_provider
        - mock_mode
        - mock_components
      heading_level: 5

---

## REST API

The FastAPI backend exposes a production-ready REST API for remote analysis.

### Base URL

```
http://localhost:8000
```

All endpoints are versioned under `/v1/`.

---

### Endpoints

#### Health Check

Check if the server is ready to accept requests.

**Endpoint:** `GET /v1/health`

**Response:**
```json
{
  "status": "ok",
  "llm_provider": "openai",
  "mock_mode": false
}
```

`mock_mode` is `true` when the server runs with `FAIRSENSE_LLM_PROVIDER=fake`; every analysis result is then a synthetic placeholder and the UI shows a warning banner.

**cURL Example:**
```bash
curl http://localhost:8000/v1/health
```

---

#### Analyze Text/Content (JSON)

Analyze text or base64-encoded content with automatic input type detection.

**Endpoint:** `POST /v1/analyze`

**Request Body:**
```json
{
  "content": "Text to analyze for bias...",
  "input_type": "bias_text",  // Optional: "bias_text", "bias_image", "risk", null (auto-detect)
  "options": {                 // Optional per-request overrides
    "temperature": 0.3,
    "max_tokens": 2000
  }
}
```

**Response:** Returns `AnalyzeResponse` object
```json
{
  "workflow_id": "bias_text",
  "run_id": "a1b2c3d4-...",
  "bias_result": {
    "status": "success",
    "bias_detected": true,
    "risk_level": "medium",
    "bias_instances": [
      {
        "type": "age",
        "severity": "high",
        "text_span": "young, energetic",
        "explanation": "Age-related descriptors may discourage older applicants",
        "start_index": 14,
        "end_index": 30
      }
    ],
    "summary": "The text contains age-related bias...",
    "highlighted_html": "<span class='bias-age'>young, energetic</span>...",
    "metadata": {
      "run_id": "a1b2c3d4-...",
      "workflow_id": "bias_text",
      "execution_time_seconds": 2.34,
      "router_confidence": 0.95,
      "refinement_count": 1
    },
    "errors": [],
    "warnings": []
  },
  "risk_result": null,
  "metadata": { /* ... */ }
}
```

**cURL Example:**
```bash
curl -X POST http://localhost:8000/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "content": "We need young, energetic developers for our startup team.",
    "options": {"temperature": 0.2}
  }'
```

---

#### Analyze File Upload

Analyze uploaded files (images, text files, CSV).

**Endpoint:** `POST /v1/analyze/upload`

**Request:** `multipart/form-data`

- `file`: File to analyze (required)
- `input_type`: Optional workflow hint ("image", "text", "csv")

**Response:** Same structure as `/v1/analyze`

**cURL Example:**
```bash
# Analyze an image
curl -X POST http://localhost:8000/v1/analyze/upload \
  -F "file=@team_photo.jpg"

# Analyze a text file with explicit type
curl -X POST http://localhost:8000/v1/analyze/upload \
  -F "file=@job_posting.txt" \
  -F "input_type=text"
```

---

#### Start Analysis (for WebSocket streaming)

Start an analysis and return `run_id` immediately for WebSocket connection. Use this to receive real-time agent telemetry.

**Endpoint:** `POST /v1/analyze/start`

**Request Body:** Same as `/v1/analyze`

**Response:**
```json
{
  "run_id": "a1b2c3d4-...",
  "status": "started",
  "message": "Analysis started. Connect to WebSocket to receive events."
}
```

**Usage Pattern:**
```python
import requests
import websockets
import asyncio
import json

async def analyze_with_streaming():
    # 1. Start analysis
    response = requests.post(
        "http://localhost:8000/v1/analyze/start",
        json={"content": "Text to analyze..."}
    )
    run_id = response.json()["run_id"]

    # 2. Connect to WebSocket immediately
    uri = f"ws://localhost:8000/v1/stream/{run_id}"
    async with websockets.connect(uri) as ws:
        async for message in ws:
            event = json.loads(message)
            print(f"[{event['event']}] {event['context'].get('message', '')}")

            if event["event"] == "analysis_complete":
                result = event["context"]["result"]
                print(f"\n✅ Complete: {result['bias_result']['summary']}")
                break

asyncio.run(analyze_with_streaming())
```

---

#### Start File Upload Analysis (for WebSocket streaming)

Upload a file and return `run_id` for WebSocket streaming.

**Endpoint:** `POST /v1/analyze/upload/start`

**Request:** `multipart/form-data` (same as `/v1/analyze/upload`)

**Response:** Same as `/v1/analyze/start`

---

#### Batch Analysis

Submit multiple items for batch processing.

**Endpoint:** `POST /v1/batch`

**Request Body:**
```json
{
  "items": [
    {
      "content": "First text to analyze...",
      "input_type": "bias_text",
      "options": {"temperature": 0.3}
    },
    {
      "content": "Second text to analyze...",
      "input_type": null,  // Auto-detect
      "options": {}
    }
  ]
}
```

**Response:** Returns `BatchStatus` with `job_id`
```json
{
  "job_id": "batch-abc123",
  "status": "pending",  // "pending" | "running" | "completed" | "failed"
  "total": 2,
  "completed": 0,
  "errors": [],
  "results": []
}
```

**Status Code:** `202 Accepted`

---

#### Get Batch Status

Poll for batch job progress and results.

**Endpoint:** `GET /v1/batch/{job_id}`

**Response:**
```json
{
  "job_id": "batch-abc123",
  "status": "completed",
  "total": 2,
  "completed": 2,
  "errors": [],
  "results": [
    { /* AnalyzeResponse for item 1 */ },
    { /* AnalyzeResponse for item 2 */ }
  ]
}
```

**cURL Example:**
```bash
# Submit batch job
JOB_ID=$(curl -X POST http://localhost:8000/v1/batch \
  -H "Content-Type: application/json" \
  -d '{"items": [{"content": "Text 1"}, {"content": "Text 2"}]}' \
  | jq -r '.job_id')

# Poll for completion
while true; do
  STATUS=$(curl -s http://localhost:8000/v1/batch/$JOB_ID | jq -r '.status')
  echo "Status: $STATUS"
  [[ "$STATUS" == "completed" || "$STATUS" == "failed" ]] && break
  sleep 2
done

# Get final results
curl http://localhost:8000/v1/batch/$JOB_ID | jq '.results'
```

---

#### Shutdown Server

Gracefully shutdown the backend server (used by the UI shutdown button).

**Endpoint:** `POST /v1/shutdown`

The endpoint is **disabled by default** and returns `404` unless `FAIRSENSE_API_ENABLE_SHUTDOWN_ENDPOINT=true`. The server launcher (`fairsense_agentix.server`) sets this for the local backend it manages. When enabled:

- If `FAIRSENSE_API_SHUTDOWN_TOKEN` is set, the request must carry a matching `X-Shutdown-Token` header (otherwise `403`).
- If no token is set, only loopback clients (`127.0.0.1` / `::1`) may shut the server down; remote callers get `403`.

**Response:**
```json
{
  "status": "shutting_down",
  "message": "Server will shutdown in 1 second"
}
```

**cURL Example:**
```bash
curl -X POST http://localhost:8000/v1/shutdown \
  -H "X-Shutdown-Token: $FAIRSENSE_API_SHUTDOWN_TOKEN"
```

---

## WebSocket Protocol

The WebSocket API provides real-time streaming of agent telemetry events during analysis.

### Connection URL

```
ws://localhost:8000/v1/stream/{run_id}
```

Connect to this WebSocket **after** calling `/v1/analyze/start` to receive live events.

---

### Event Structure

Every message is the JSON telemetry payload emitted by the agent, forwarded to the client whose `run_id` it carries:

```json
{
  "run_id": "a1b2c3d4-...",
  "timestamp": 1234567890.123,
  "event": "bias_text_analyze_start",
  "level": "info",
  "context": {
    "text_length": 128
  }
}
```

`level` is `"info"`, `"warning"`, or `"error"`. `context` holds the structured fields the emitting node attached; there is no fixed schema beyond the event names below. There is no separate `message` field except on the two terminal events.

---

### Event Types

Node events are emitted by the orchestrator and the workflow subgraphs as each node begins. Only events that carry the run ID are streamed, so clients see one `*_start` event per node in execution order.

#### Orchestrator events (every workflow)

| Event | Context fields |
|-------|----------------|
| `orchestrator_plan_start` | `input_type`, `refinement_count` |
| `orchestrator_preflight_start` | `has_plan` |
| `orchestrator_execute_start` | `workflow_id` |
| `orchestrator_posthoc_start` | `has_result` |
| `orchestrator_decide_start` | `refinement_count`, `refinement_enabled` |
| `orchestrator_refine_start` | `current_refinement_count` (only when a refinement pass is triggered) |
| `orchestrator_finalize_start` | `decision`, `refinement_count` |

#### Workflow events

| Workflow | Events (in order) |
|----------|-------------------|
| `bias_text` | `bias_text_analyze_start` (`text_length`), `bias_text_summarize_start`*, `bias_text_highlight_start` |
| `bias_image_vlm` (default image mode) | `bias_image_vlm_analyze_start` (`image_size`, `model`, `provider`), `bias_image_vlm_summarize_start`, `bias_image_vlm_highlight_start` |
| `bias_image` (`FAIRSENSE_IMAGE_ANALYSIS_MODE=traditional`) | `bias_image_ocr_start`, `bias_image_caption_start`, `bias_image_merge_start`, `bias_image_analyze_start`, `bias_image_summarize_start`*, `bias_image_highlight_start` |
| `risk` | `risk_embed_start` (`text_length`), `risk_search_start`, `risk_rmf_search_start` (`risk_count`), `risk_join_start` (`risk_count`), `risk_format_start` (`table_rows`), `risk_export_start` (`table_rows`), then `risk_evaluator_start` (`workflow_id`) during post-hoc evaluation |

\* summarisation runs only when the input is long enough (router-controlled).

Warnings and errors raised inside nodes are streamed with the same envelope and `level` set accordingly (e.g. `posthoc_eval_failed`, `search_rmf_skipped`).

#### Terminal events (emitted by the service layer)

| Event | Level | Context fields |
|-------|-------|----------------|
| `analysis_complete` | `info` | `message`, `result` — the full `AnalyzeResponse` (`workflow_id`, `run_id`, `bias_result` or `risk_result`, `metadata`) |
| `analysis_error` | `error` | `message`, `error_type` |

Exactly one of these ends every run started via `/v1/analyze/start` or `/v1/analyze/upload/start`.

---

### Connection Lifecycle

1. **Start Analysis:**
   ```python
   response = requests.post(
       "http://localhost:8000/v1/analyze/start",
       json={"content": "..."}
   )
   run_id = response.json()["run_id"]
   ```

2. **Connect to WebSocket:**
   ```python
   uri = f"ws://localhost:8000/v1/stream/{run_id}"
   async with websockets.connect(uri) as ws:
       # Start receiving events
   ```

3. **Receive Events:**
   ```python
   async for message in ws:
       event = json.loads(message)

       if event["event"] == "orchestrator_execute_start":
           print(f"Running workflow {event['context']['workflow_id']}...")

       elif event["event"] == "analysis_complete":
           result = event["context"]["result"]
           break  # Analysis done

       elif event["event"] == "analysis_error":
           print(f"Error: {event['context']['message']}")
           break
   ```

4. **Disconnection:**
   - The server keeps the socket open; **the client should close it** after receiving `analysis_complete` or `analysis_error`.
   - Events are buffered per `run_id` (up to 200, oldest dropped), so connecting shortly after `/start` returns does not lose the early events.
   - Disconnecting early does not cancel the analysis; the final result is still stored and returned by `/v1/analyze/start`'s background task.

---

### Example: Full Event Stream

```python
import asyncio
import json
import requests
import websockets


async def stream_analysis():
    # Start analysis
    response = requests.post(
        "http://localhost:8000/v1/analyze/start",
        json={
            "content": "We need young, energetic developers",
            "options": {"temperature": 0.3}
        }
    )
    run_id = response.json()["run_id"]
    print(f"Started analysis: {run_id}")

    # Connect to WebSocket
    uri = f"ws://localhost:8000/v1/stream/{run_id}"
    async with websockets.connect(uri) as ws:
        print("Connected to event stream\n")

        async for message in ws:
            event = json.loads(message)

            # Format event for display
            event_type = event["event"]
            level = event["level"]
            ctx = event["context"]

            # Pretty print based on event type
            if event_type == "orchestrator_plan_start":
                print(f"🧭 [{level}] Planning ({ctx['input_type']})")

            elif event_type == "orchestrator_execute_start":
                print(f"🚀 [{level}] Executing workflow: {ctx['workflow_id']}")

            elif event_type == "orchestrator_refine_start":
                print(f"🔄 [{level}] Refinement pass {ctx['current_refinement_count'] + 1}")

            elif event_type == "analysis_complete":
                result = ctx["result"]
                print(f"\n✅ [{level}] Analysis complete!")
                if result["bias_result"]:
                    print(f"Bias detected: {result['bias_result']['bias_detected']}")
                    print(f"Risk level: {result['bias_result']['risk_level']}")
                else:
                    print(f"Risks found: {len(result['risk_result']['risks'])}")
                break

            elif event_type == "analysis_error":
                print(f"\n❌ [{level}] Analysis failed: {ctx['message']}")
                break

            else:
                # Node-level event (bias_text_analyze_start, risk_embed_start, ...)
                print(f"📋 [{level}] {event_type} {ctx}")


# Run the streaming example
asyncio.run(stream_analysis())
```

**Example Output:**
```
Started analysis: a1b2c3d4-5678-90ab-cdef-1234567890ab
Connected to event stream

🚀 [info] Workflow started: Starting bias_text workflow
📍 [info] Phase: planning
🔧 [info] Running tool: embedding
✅ [info] embedding completed (45ms)
📍 [info] Phase: tool_execution
🔧 [info] Running tool: knowledge_retrieval
✅ [info] knowledge_retrieval completed (120ms)
🤖 [info] LLM call: claude-3-5-sonnet-20241022
✅ [info] LLM response (523 tokens)
📍 [info] Phase: evaluation
🔄 [info] Refinement iteration 1
🤖 [info] LLM call: claude-3-5-sonnet-20241022
✅ [info] LLM response (612 tokens)
📍 [info] Phase: synthesis

✅ [info] Analysis complete!
Bias detected: True
Risk level: medium
```

---

### Error Handling

**WebSocket Connection Errors:**

```python
try:
    async with websockets.connect(uri) as ws:
        async for message in ws:
            # ... handle events
except websockets.exceptions.ConnectionClosed:
    print("WebSocket connection closed")
except Exception as e:
    print(f"WebSocket error: {e}")
```

**Analysis Errors (via Event Stream):**

When analysis fails, you'll receive an `analysis_error` event:

```json
{
  "run_id": "...",
  "timestamp": 1234567890.123,
  "event": "analysis_error",
  "level": "error",
  "context": {
    "message": "Analysis failed: OCR tool failed: Tesseract not found",
    "error_type": "ToolExecutionError"
  }
}
```

---

## API Usage Examples

### Python: Batch Processing

```python
from fairsense_agentix import FairSense

# Initialize once (expensive)
fs = FairSense()

# Process multiple texts efficiently
texts = [
    "Job posting 1...",
    "Job posting 2...",
    "Job posting 3...",
]

for text in texts:
    result = fs.analyze_text(text)
    print(f"{result.metadata.run_id}: {result.risk_level}")
```

### Python: Custom Configuration

```python
import os
from fairsense_agentix import FairSense

# Set environment variables
os.environ["FAIRSENSE_LLM_PROVIDER"] = "anthropic"
os.environ["FAIRSENSE_LLM_MODEL_NAME"] = "claude-3-5-sonnet-20241022"
os.environ["FAIRSENSE_LLM_API_KEY"] = "sk-ant-..."

# Initialize with custom settings
fs = FairSense()

# Per-request options
result = fs.analyze_text(
    "Text to analyze",
    temperature=0.2,  # Lower for consistency
    max_tokens=3000,  # More detailed analysis
)
```

### REST API: Image Analysis with Node.js

```javascript
const fs = require('fs');
const axios = require('axios');
const FormData = require('form-data');

async function analyzeImage(imagePath) {
  const form = new FormData();
  form.append('file', fs.createReadStream(imagePath));

  const response = await axios.post(
    'http://localhost:8000/v1/analyze/upload',
    form,
    { headers: form.getHeaders() }
  );

  const result = response.data.bias_result;
  console.log(`Bias detected: ${result.bias_detected}`);
  console.log(`Risk level: ${result.risk_level}`);
  console.log(`OCR text: ${result.ocr_text}`);
}

analyzeImage('team_photo.jpg');
```

### REST API: Batch Processing with Python

```python
import requests
import time

# Submit batch job
response = requests.post(
    "http://localhost:8000/v1/batch",
    json={
        "items": [
            {"content": "Job posting 1..."},
            {"content": "Job posting 2..."},
            {"content": "Job posting 3..."},
        ]
    }
)
job_id = response.json()["job_id"]
print(f"Batch job started: {job_id}")

# Poll for completion
while True:
    response = requests.get(f"http://localhost:8000/v1/batch/{job_id}")
    status = response.json()

    print(f"Progress: {status['completed']}/{status['total']} ({status['status']})")

    if status["status"] in ["completed", "failed"]:
        break

    time.sleep(2)

# Process results
for i, result in enumerate(status["results"]):
    bias_result = result["bias_result"]
    print(f"Item {i+1}: {bias_result['risk_level']}")
```

---

## Interactive API Documentation

The FastAPI backend provides interactive API documentation:

- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

These interfaces allow you to:

- Explore all available endpoints
- View detailed request/response schemas
- Test API calls directly in the browser
- Download OpenAPI specification (JSON/YAML)

---

## Rate Limits and Performance

**Python API:**

- No built-in rate limits
- Performance depends on LLM provider API limits
- Typical analysis time: 2-5 seconds (with refinement enabled)

**REST API:**

- No built-in rate limits (configure reverse proxy for production)
- Concurrent requests supported via FastAPI async
- WebSocket connections: Limited only by server resources

**Recommendations:**

- For high-throughput scenarios, use batch endpoints
- Reuse `FairSense` instances in Python for better performance
- Monitor LLM provider token usage and costs
- Consider disabling refinement (`FAIRSENSE_ENABLE_REFINEMENT=false`) for faster results

---

## Error Codes

| HTTP Code | Meaning | Common Causes |
|-----------|---------|---------------|
| 200 | Success | Request completed successfully |
| 202 | Accepted | Batch job queued |
| 400 | Bad Request | Invalid input format, malformed JSON |
| 404 | Not Found | Batch job ID doesn't exist |
| 500 | Internal Server Error | Tool execution failure, LLM API error |

**Error Response Format:**
```json
{
  "detail": "Error message describing what went wrong"
}
```

---

## Next Steps

- **[Getting Started](getting_started.md)** - Install and configure FairSense
- **[User Guide](user_guide.md)** - Detailed usage examples for each workflow
- **[Server Guide](server.md)** - Deploy and configure the FastAPI backend
