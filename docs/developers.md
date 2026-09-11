# Developer Guide

This guide is for developers who want to contribute to FairSense-AgentiX or extend it with custom functionality.

---

## Project Structure

```
fairsense-agentix/
├── fairsense_agentix/          # Core Python package
│   ├── __init__.py             # Package exports and eager loading
│   ├── api.py                  # High-level Python API (FairSense class)
│   ├── graphs/                 # LangGraph workflow definitions
│   │   ├── orchestrator_graph.py   # Public entry: create_orchestrator_graph re-export
│   │   ├── orchestrator/           # Orchestrator implementation (split modules)
│   │   │   ├── build.py                # Graph construction and compile
│   │   │   ├── planning.py             # request_plan, preflight_eval
│   │   │   ├── execution.py            # execute_workflow (subgraph dispatch)
│   │   │   ├── evaluation.py           # posthoc_eval, bias source text helper
│   │   │   ├── decision_finalize.py    # decide_action, apply_refinement, finalize
│   │   │   └── routing.py              # Conditional edge routing helpers
│   │   ├── bias_text_graph.py      # Public entry: create_bias_text_graph re-export
│   │   ├── bias_text/              # Text bias workflow implementation
│   │   │   ├── build.py                # StateGraph wiring + compile
│   │   │   ├── nodes.py                # analyze_bias, summarize, highlight
│   │   │   ├── routing.py              # should_summarize
│   │   │   └── spans.py                # Span extraction for highlighting
│   │   ├── bias_image_graph.py     # Public entry: create_bias_image_graph re-export
│   │   ├── bias_image/             # Traditional image workflow implementation
│   │   │   ├── build.py                # StateGraph wiring + compile
│   │   │   ├── nodes_extraction.py     # extract_ocr, generate_caption, merge_text
│   │   │   ├── nodes_analysis.py       # analyze_bias, summarize, highlight
│   │   │   ├── validation.py           # Pillow decode checks before OCR/caption
│   │   │   └── spans.py                # Bias spans mapped to merged OCR+caption text
│   │   ├── bias_image_vlm_graph.py # Public entry: create_bias_image_vlm_graph re-export
│   │   ├── bias_image_vlm/         # VLM image workflow implementation
│   │   │   ├── build.py                # StateGraph wiring + compile
│   │   │   └── nodes.py                # visual_analyze, summarize, highlight
│   │   ├── risk_graph.py           # Public entry: create_risk_graph re-export
│   │   ├── risk/                   # Risk assessment workflow implementation
│   │   │   ├── build.py                # StateGraph wiring + compile
│   │   │   ├── nodes_retrieval.py      # embed, FAISS risks, RMF per risk
│   │   │   └── nodes_output.py         # join, HTML table, CSV export
│   │   └── state/                  # State definitions (split modules)
│   │       ├── orchestrator.py         # SelectionPlan, EvaluationResult, OrchestratorState
│   │       ├── bias_text.py            # BiasTextState
│   │       ├── bias_image.py           # BiasImageState
│   │       ├── bias_image_vlm.py       # BiasImageVLMState
│   │       └── risk.py                 # RiskState
│   ├── tools/                  # Tool implementations
│   │   ├── registry.py             # Tool factory and DI container
│   │   ├── resolvers/               # Per-tool resolver modules (ocr, llm, etc.)
│   │   ├── interfaces/             # Tool protocol interfaces (split modules)
│   │   │   ├── image.py                # OCRTool, CaptionTool
│   │   │   ├── text.py                 # LLMTool, SummarizerTool, VLMTool
│   │   │   ├── search.py               # EmbedderTool, FAISSIndexTool
│   │   │   └── output.py               # FormatterTool, PersistenceTool
│   │   ├── ocr/                    # OCR implementations
│   │   ├── caption/                # Image captioning
│   │   ├── vlm/                    # Vision-Language Models
│   │   ├── llm/                    # LLM integrations
│   │   ├── embeddings/             # Text embeddings
│   │   ├── faiss_index/            # Vector search
│   │   ├── formatter/              # Output formatting (HTML)
│   │   │   ├── html_formatter.py       # HTMLFormatter facade
│   │   │   ├── highlight.py            # Bias span fragments + full documents
│   │   │   └── tables.py               # Data table HTML
│   │   ├── persistence/            # File I/O
│   │   └── fake/                   # Fake tools for testing (split modules)
│   │       ├── image.py                # FakeOCRTool, FakeCaptionTool
│   │       ├── text.py                 # FakeLLMTool, FakeSummarizerTool
│   │       ├── search.py               # FakeEmbedderTool, FakeFAISSIndexTool
│   │       └── output.py               # FakeFormatterTool, FakePersistenceTool
│   ├── services/               # Support services
│   │   ├── router.py               # Workflow routing logic
│   │   ├── evaluator/              # Quality evaluation (split modules)
│   │   │   ├── common.py               # EvaluationContext (shared)
│   │   │   ├── bias.py                 # LLM-based bias evaluator
│   │   │   └── risk.py                 # Rule-based risk evaluator
│   │   ├── telemetry.py            # Event streaming
│   │   └── event_bus.py            # WebSocket event bus
│   ├── service_api/            # FastAPI backend
│   │   ├── __main__.py             # `python -m fairsense_agentix.service_api` (uvicorn + settings)
│   │   ├── server.py               # App factory: lifespan, middleware, router includes
│   │   ├── app_state.py            # Shared runtime state (engine, event_bus, locks)
│   │   ├── helpers.py              # run_analysis, run_analysis_background
│   │   └── routes/                 # APIRouter modules
│   │       ├── health.py               # GET /v1/health, POST /v1/shutdown
│   │       ├── analyze.py              # POST /v1/analyze* (4 endpoints)
│   │       ├── batch.py                # POST/GET /v1/batch
│   │       └── stream.py               # WS /v1/stream/{run_id}
│   │   ├── schemas.py              # Request/response models
│   │   └── utils.py                # Helper functions
│   ├── server/                 # Server launcher utilities
│   │   ├── launcher/               # ServerLauncher orchestration (split modules)
│   │   │   ├── messages.py             # Banners, ready message, troubleshooting output
│   │   │   ├── health.py               # HTTP health-check polling
│   │   │   ├── processes.py            # start_backend, start_frontend, kill_port
│   │   │   └── core.py                 # ServerLauncher orchestrator + start()
│   │   └── README.md               # Launcher usage notes
│   ├── prompts/                # LLM prompt templates
│   │   ├── prompt_loader.py        # Template loading
│   │   └── templates/              # .txt files with Jinja2 templates
│   ├── configs/                # Configuration management
│   │   ├── settings.py             # Pydantic Settings class
│   │   └── logging_config.py       # Logging setup
│   └── data/                   # Package data (index metadata, etc.)
│       └── indexes/                # FAISS index metadata (risks_meta.json, rmf_meta.json)
├── ui/                         # React frontend
│   ├── src/
│   │   ├── App.tsx                 # Main app component
│   │   ├── api.ts                  # API client
│   │   └── components/             # React components
│   ├── package.json
│   └── vite.config.ts
├── tests/                      # Test suite
│   ├── test_ocr_tools.py           # OCR tool tests
│   ├── test_caption_tools.py       # Caption tool tests
│   ├── test_server_launcher.py     # Server launcher tests
│   ├── test_*.py                   # Other tool/API tests
│   ├── fairsense-agentix/          # Graph and integration tests
│   └── benchmarks/                 # Performance benchmarks
├── docs/                       # Documentation (MkDocs)
├── examples/                   # Usage examples
├── .env                        # Environment variables (create from template)
├── pyproject.toml              # Python dependencies (uv)
├── mkdocs.yml                  # Documentation config
└── README.md                   # Project README
```

### Orchestrator package (`graphs/orchestrator/`)

The orchestrator supergraph used to live entirely in `orchestrator_graph.py`. It is now split into focused modules under `fairsense_agentix/graphs/orchestrator/` so each file stays easier to read and review. **Imports for callers are unchanged:** use `from fairsense_agentix.graphs.orchestrator_graph import create_orchestrator_graph` (or `from fairsense_agentix import create_orchestrator_graph`).

| Module | Contents |
|--------|----------|
| `build.py` | `create_orchestrator_graph()` — registers nodes, edges, and conditional routes, then compiles the graph. |
| `planning.py` | `request_plan` (router integration), `preflight_eval` (plan validation stub / future checks). |
| `execution.py` | `execute_workflow` — dispatches to `bias_text`, `bias_image` / VLM, `bias_image_vlm`, or `risk` subgraphs based on `plan.workflow_id`. |
| `evaluation.py` | `posthoc_eval` (quality evaluation), `_extract_bias_source_text` (evaluator context for bias workflows). |
| `decision_finalize.py` | `decide_action` (accept / refine / fail), `apply_refinement` (plan/options updates), `finalize` (client-facing `final_result`). |
| `routing.py` | `should_execute_workflow`, `route_after_decision` — LangGraph conditional edge callables. |

`orchestrator_graph.py` keeps the high-level module docstring and re-exports `create_orchestrator_graph` from `orchestrator.build`. When you add a new workflow, you still update `services/router.py` for routing; extend **`execution.py`** with a new `workflow_id` branch (and any packaging of subgraph results), following the existing patterns.

### Bias text package (`graphs/bias_text/`)

The text bias workflow lives under `fairsense_agentix/graphs/bias_text/`. **Callers still import** `create_bias_text_graph` **from** `fairsense_agentix.graphs.bias_text_graph`.

| Module | Contents |
|--------|----------|
| `build.py` | `create_bias_text_graph()` — analyze → conditional summarize → highlight. |
| `nodes.py` | `analyze_bias`, `summarize`, `highlight` (prompt template from package root). |
| `routing.py` | `should_summarize` — long text or `enable_summary` option. |
| `spans.py` | `_extract_spans_from_analysis` — character spans in original text. |

### Risk package (`graphs/risk/`)

The CSV / FAISS risk workflow lives under `fairsense_agentix/graphs/risk/`. **Callers still import** `create_risk_graph` **from** `fairsense_agentix.graphs.risk_graph`.

| Module | Contents |
|--------|----------|
| `build.py` | `create_risk_graph()` — sequential embed → search → RMF → join → HTML → CSV. |
| `nodes_retrieval.py` | `embed_scenario`, `search_risks`, `search_rmf_per_risk`. |
| `nodes_output.py` | `join_data`, `format_html`, `export_csv`. |

### Evaluator package (`services/evaluator/`)

The quality evaluators live under `fairsense_agentix/services/evaluator/`. All names are re-exported from `__init__.py` so existing imports of `from fairsense_agentix.services.evaluator import ...` are unchanged.

| Module | Contents |
|--------|----------|
| `common.py` | `EvaluationContext` — shared dataclass used by both evaluators. |
| `bias.py` | `BiasEvaluatorOutput`, `evaluate_bias_output` — LLM-based critique via OpenAI/Anthropic. Includes prompt rendering, `_build_plain_langchain_model`, serialization, and fake/forced-score helpers. |
| `risk.py` | `RiskEvaluatorOutput`, `evaluate_risk_output` — rule-based checks: RMF breadth, duplicate detection, FAISS score sanity, risk coverage. |

---

### Bias image VLM package (`graphs/bias_image_vlm/`)

The VLM image bias workflow lives under `fairsense_agentix/graphs/bias_image_vlm/`. **Callers still import** `create_bias_image_vlm_graph` **from** `fairsense_agentix.graphs.bias_image_vlm_graph`.

| Module | Contents |
|--------|----------|
| `build.py` | `create_bias_image_vlm_graph()` — sequential visual_analyze → summarize → highlight. |
| `nodes.py` | `visual_analyze` (VLM CoT prompt), `summarize`, `highlight` (HTML with bias instances). |

No routing module — the workflow is a simple linear chain. Prompt template resolved from the package root (`prompts/templates/bias_visual_analysis_v1.txt`).

### Bias image package (`graphs/bias_image/`)

The traditional OCR + caption image workflow is implemented under `fairsense_agentix/graphs/bias_image/`. **Callers still import** `create_bias_image_graph` **from** `fairsense_agentix.graphs.bias_image_graph`.

| Module | Contents |
|--------|----------|
| `build.py` | `create_bias_image_graph()` — parallel OCR/caption fan-out, merge, analyze, summarize, highlight. |
| `nodes_extraction.py` | `extract_ocr`, `generate_caption`, `merge_text`. |
| `nodes_analysis.py` | `analyze_bias` (loads `prompts/templates/bias_analysis_v1.txt` from package root), `summarize`, `highlight`. |
| `validation.py` | `_ensure_valid_image_bytes` — optional Pillow verification. |
| `spans.py` | `_extract_spans_from_analysis` — maps bias instances to spans in merged text. |

---

## Development Setup

### 1. Clone and Install

```bash
git clone https://github.com/VectorInstitute/fairsense-agentix.git
cd fairsense-agentix

# Install all dependencies (including dev tools)
uv sync

# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
# OR
.venv\Scripts\activate  # Windows
```

### 2. Configure Environment

```bash
# Create .env file
touch .env

# Edit .env with your settings
# At minimum, set:
FAIRSENSE_LLM_PROVIDER=fake  # Use 'fake' for development/testing
FAIRSENSE_LLM_API_KEY=dummy   # Not needed for fake provider
```

### 3. Install Pre-commit Hooks

```bash
# Setup pre-commit hooks (runs on every commit)
pre-commit install

# Run manually on all files
pre-commit run --all-files
```

**Pre-commit Checks:**
- **ruff** - Code formatting and linting
- **mypy** - Static type checking
- **pytest** - Run test suite

---

## Code Style Guidelines

### General Principles
- Follow [PEP 8](https://peps.python.org/pep-0008/) style guide
- Use [numpy-style docstrings](https://numpydoc.readthedocs.io/en/latest/format.html)
- Add type hints to all functions (checked by mypy)
- Keep functions short and focused (< 50 lines)
- Prefer composition over inheritance

### Example Function

```python
def analyze_text_bias(
    text: str,
    *,
    temperature: float = 0.3,
    max_tokens: int = 2000,
) -> BiasAnalysisOutput:
    """Analyze text for bias using LLM.

    Parameters
    ----------
    text : str
        Text content to analyze for bias
    temperature : float, optional
        LLM temperature (0.0-1.0), by default 0.3
    max_tokens : int, optional
        Maximum response tokens, by default 2000

    Returns
    -------
    BiasAnalysisOutput
        Structured bias analysis with instances and explanations

    Raises
    ------
    ValueError
        If text is empty or temperature is out of range

    Examples
    --------
    >>> result = analyze_text_bias("Job posting text", temperature=0.2)
    >>> result.bias_detected
    True
    """
    if not text.strip():
        raise ValueError("Text cannot be empty")

    if not 0.0 <= temperature <= 1.0:
        raise ValueError(f"Temperature must be 0.0-1.0, got {temperature}")

    # Implementation...
```

### Import Organization

```python
# Standard library
import os
import time
from pathlib import Path
from typing import Any, Literal

# Third-party packages
import anthropic
from langgraph.graph import StateGraph
from pydantic import BaseModel, Field

# Local imports
from fairsense_agentix.configs import settings
from fairsense_agentix.tools import get_tool_registry
from fairsense_agentix.services.telemetry import telemetry
```

---

## interfaces/ — Tool Protocol Interfaces

`fairsense_agentix/tools/interfaces/` defines all `@runtime_checkable` Protocol classes that tool implementations must satisfy. Split across four focused modules:

| Module | Protocols |
|---|---|
| `image.py` | `OCRTool`, `CaptionTool` |
| `text.py` | `LLMTool`, `SummarizerTool`, `VLMTool` |
| `search.py` | `EmbedderTool`, `FAISSIndexTool` |
| `output.py` | `FormatterTool`, `PersistenceTool` |

All names are re-exported from `interfaces/__init__.py` so existing imports like `from fairsense_agentix.tools.interfaces import OCRTool` continue to work unchanged.

---

## How to Add a Custom Tool

Tools in FairSense follow the **Tool Abstraction Pattern** - they implement an interface and are registered via the ToolRegistry.

### Step 1: Define Tool Interface

**File:** `fairsense_agentix/tools/interfaces/` (add to the appropriate submodule: `image.py`, `text.py`, `search.py`, or `output.py`)

```python
from typing import Protocol

class SentimentTool(Protocol):
    """Protocol for sentiment analysis tools."""

    def analyze_sentiment(self, text: str) -> dict[str, float]:
        """Analyze sentiment of text.

        Parameters
        ----------
        text : str
            Text to analyze

        Returns
        -------
        dict[str, float]
            Sentiment scores (e.g., {"positive": 0.8, "negative": 0.2})
        """
        ...
```

### Step 2: Implement Tool

**File:** `fairsense_agentix/tools/sentiment/my_sentiment_tool.py`

```python
class MySentimentTool:
    """Custom sentiment analysis tool."""

    def __init__(self, model_name: str = "default"):
        """Initialize sentiment tool.

        Parameters
        ----------
        model_name : str, optional
            Sentiment model to use, by default "default"
        """
        self.model_name = model_name
        # Load model, setup resources, etc.

    def analyze_sentiment(self, text: str) -> dict[str, float]:
        """Analyze sentiment of text."""
        # Your implementation
        return {"positive": 0.7, "negative": 0.3}
```

### Step 3: Register Tool in Registry

**File:** `fairsense_agentix/tools/registry.py`

```python
def _resolve_sentiment_tool(settings: Settings) -> SentimentTool:
    """Resolve sentiment tool based on settings."""
    if settings.sentiment_tool == "my_sentiment":
        from fairsense_agentix.tools.sentiment import MySentimentTool
        return MySentimentTool(model_name=settings.sentiment_model)
    elif settings.sentiment_tool == "fake":
        return FakeSentimentTool()
    else:
        raise ToolConfigurationError(
            f"Unknown sentiment_tool: {settings.sentiment_tool}"
        )

@dataclass
class ToolRegistry:
    """Container for all tool instances."""
    ocr: OCRTool
    caption: CaptionTool
    llm: LLMTool
    sentiment: SentimentTool  # Add new tool

def create_tool_registry(settings: Settings) -> ToolRegistry:
    """Create tool registry from settings."""
    return ToolRegistry(
        ocr=_resolve_ocr_tool(settings),
        caption=_resolve_caption_tool(settings),
        llm=_resolve_llm_tool(settings),
        sentiment=_resolve_sentiment_tool(settings),  # Register
    )
```

### Step 4: Add Configuration Settings

**File:** `fairsense_agentix/configs/settings.py`

```python
class Settings(BaseSettings):
    """Application settings."""
    # ... existing settings ...

    # Sentiment Tool Settings
    sentiment_tool: Literal["my_sentiment", "fake"] = Field(
        default="my_sentiment",
        description="Sentiment analysis tool",
    )
    sentiment_model: str = Field(
        default="default",
        description="Sentiment model name",
    )

    class Config:
        env_prefix = "FAIRSENSE_"
```

### Step 5: Use Tool in Workflow

**File:** `fairsense_agentix/graphs/my_workflow_graph.py`

```python
from fairsense_agentix.tools import get_tool_registry

def sentiment_analysis_node(state: MyState) -> dict:
    """Analyze sentiment of text."""
    registry = get_tool_registry()

    # Use the tool
    sentiment = registry.sentiment.analyze_sentiment(state.text)

    return {"sentiment_scores": sentiment}
```

---

## How to Modify Prompts

Prompts are stored as Jinja2 templates in `fairsense_agentix/prompts/templates/`.

### Prompt File Structure

**File:** `fairsense_agentix/prompts/templates/bias_text_v1.txt`

```jinja2
You are an expert fairness auditor analyzing text for bias.

## Task
Analyze the following text for various forms of bias including:
- Gender bias
- Age bias
- Racial/ethnic bias
- Disability bias
- Socioeconomic bias

## Text to Analyze
{{ text }}

## Instructions
1. Identify ALL instances of bias in the text
2. For each bias instance, provide:
   - **type**: The category of bias (gender, age, race, disability, socioeconomic)
   - **severity**: How severe the bias is (low, medium, high)
   - **text_span**: The exact phrase showing bias
   - **explanation**: Why this is biased and how it could exclude/harm people
   - **start_char**: Character position where bias starts (0-indexed)
   - **end_char**: Character position where bias ends
3. Assess the overall risk level (low, medium, high)

{% if feedback %}
## Previous Feedback
The previous analysis had these issues:
{% for item in feedback %}
- {{ item }}
{% endfor %}

Please address these issues in your analysis.
{% endif %}

## Output Format
Return your analysis as JSON matching this schema:
{{ output_schema }}
```

### Template Variables

Prompts can use these variables:

| Variable | Type | Description |
|----------|------|-------------|
| `text` | str | Input text to analyze |
| `image_description` | str | Visual description (image workflows) |
| `ocr_text` | str | Extracted text (image workflows) |
| `caption_text` | str | Generated caption (image workflows) |
| `feedback` | list[str] | Refinement hints from evaluator |
| `output_schema` | str | JSON schema for structured output |
| `options` | dict | User-provided options |

### Prompt Versioning

Prompts are versioned (`_v1`, `_v2`, etc.) to enable A/B testing:

```python
# Load specific version
prompt = prompt_loader.load("bias_text_v1")

# Or use latest
prompt = prompt_loader.load("bias_text")  # Defaults to latest version
```

### Testing Prompt Changes

```bash
# Run tests to verify prompts work
pytest tests/test_prompts.py

# Test with fake LLM (fast, deterministic)
FAIRSENSE_LLM_PROVIDER=fake pytest tests/test_graphs.py

# Test with real LLM (slow, requires API key)
FAIRSENSE_LLM_PROVIDER=anthropic pytest tests/test_graphs.py::test_bias_text_real
```

---

## How to Customize Evaluation

Evaluators assess output quality and provide refinement guidance.

### Bias Evaluator Example

**File:** `fairsense_agentix/services/evaluator.py`

```python
def _invoke_bias_evaluator_llm(
    workflow_result: dict[str, Any],
    original_text: str | None,
    existing_feedback: list[str],
) -> BiasEvaluatorOutput:
    """Call LLM to critique bias analysis output.

    Parameters
    ----------
    workflow_result : dict[str, Any]
        Output from bias workflow (bias_analysis, summary, etc.)
    original_text : str | None
        Source text for grounding check
    existing_feedback : list[str]
        Previous critiques (for refinement iterations)

    Returns
    -------
    BiasEvaluatorOutput
        Critique with score (0-100), justification, suggested changes
    """
    # Load evaluator prompt
    prompt_template = prompt_loader.load("bias_evaluator_v1")

    # Prepare context
    context = {
        "workflow_result": workflow_result,
        "original_text": original_text,
        "existing_feedback": existing_feedback,
        "output_schema": BiasEvaluatorOutput.model_json_schema(),
    }

    # Render prompt
    prompt = prompt_template.render(**context)

    # Call LLM
    llm = _get_evaluator_llm()
    parser = PydanticOutputParser(pydantic_object=BiasEvaluatorOutput)

    chain = (
        ChatPromptTemplate.from_template(prompt)
        | llm
        | parser
    )

    critique = chain.invoke({})

    return critique
```

### Custom Evaluator

```python
def evaluate_custom_criteria(
    workflow_result: dict[str, Any],
    options: dict[str, Any],
    context: EvaluationContext,
) -> EvaluationResult:
    """Custom evaluator for domain-specific criteria.

    Parameters
    ----------
    workflow_result : dict[str, Any]
        Workflow output
    options : dict[str, Any]
        User options
    context : EvaluationContext
        Evaluation metadata

    Returns
    -------
    EvaluationResult
        Evaluation result with pass/fail, score, issues, refinement hints
    """
    # Extract relevant fields
    bias_analysis = workflow_result.get("bias_analysis")

    # Apply custom logic
    issues = []
    score = 100

    # Example: Check for specific bias types
    required_types = {"gender", "age", "race"}
    found_types = {inst.type for inst in bias_analysis.bias_instances}

    if not required_types.issubset(found_types):
        missing = required_types - found_types
        issues.append(f"Missing bias types: {missing}")
        score -= 30

    # Determine pass/fail
    passed = score >= settings.custom_evaluator_min_score

    # Refinement hints
    refinement_hints = {}
    if not passed:
        refinement_hints = {
            "options": {
                "custom_feedback": issues,
            }
        }

    return EvaluationResult(
        passed=passed,
        score=score / 100,
        issues=issues,
        explanation=f"Custom evaluation: score={score}",
        refinement_hints=refinement_hints,
    )
```

---

## How to Add a Custom Workflow

Workflows are LangGraph state machines that define analysis pipelines.

### Step 1: Define Workflow State

**File:** `fairsense_agentix/graphs/state/` (add to the appropriate submodule)

```python
from typing import TypedDict

class MyWorkflowState(TypedDict, total=False):
    """State for my custom workflow."""
    # Inputs (required)
    text: str
    options: dict[str, Any]
    run_id: str | None

    # Intermediate results
    preprocessed_text: str
    analysis_result: dict[str, Any]

    # Outputs
    final_result: dict[str, Any]
    errors: list[str]
```

### Step 2: Define Workflow Nodes

**File:** `fairsense_agentix/graphs/my_workflow_graph.py`

```python
from langgraph.graph import END, START, StateGraph

def preprocess_node(state: MyWorkflowState) -> dict:
    """Preprocess text before analysis."""
    text = state["text"]

    # Your preprocessing logic
    preprocessed = text.lower().strip()

    return {"preprocessed_text": preprocessed}

def analyze_node(state: MyWorkflowState) -> dict:
    """Run analysis on preprocessed text."""
    registry = get_tool_registry()

    # Use tools
    result = registry.llm.generate(
        prompt=f"Analyze: {state['preprocessed_text']}",
        temperature=0.3,
    )

    return {"analysis_result": result}

def finalize_node(state: MyWorkflowState) -> dict:
    """Package final output."""
    return {
        "final_result": {
            "analysis": state["analysis_result"],
            "metadata": {"run_id": state.get("run_id")},
        }
    }
```

### Step 3: Build Workflow Graph

```python
def create_my_workflow_graph() -> CompiledStateGraph:
    """Create and compile my custom workflow graph."""
    # Create graph with state
    workflow = StateGraph(MyWorkflowState)

    # Add nodes
    workflow.add_node("preprocess", preprocess_node)
    workflow.add_node("analyze", analyze_node)
    workflow.add_node("finalize", finalize_node)

    # Add edges
    workflow.add_edge(START, "preprocess")
    workflow.add_edge("preprocess", "analyze")
    workflow.add_edge("analyze", "finalize")
    workflow.add_edge("finalize", END)

    # Compile
    return workflow.compile()
```

### Step 4: Integrate with Orchestrator

**File:** `fairsense_agentix/services/router.py`

```python
def create_selection_plan(
    input_type: Literal["text", "image", "csv"],
    content: str | bytes,
    options: dict[str, Any] | None = None,
) -> SelectionPlan:
    """Route to appropriate workflow."""
    options = options or {}

    if input_type == "text":
        return _create_text_bias_plan(content, options)
    elif input_type == "image":
        return _create_image_bias_plan(content, options)
    elif input_type == "csv":
        return _create_risk_plan(content, options)
    elif input_type == "custom":  # ADD NEW WORKFLOW
        return _create_my_workflow_plan(content, options)
    # ...
```

**File:** `fairsense_agentix/graphs/orchestrator/execution.py`

```python
def execute_workflow(state: OrchestratorState) -> dict:
    """Execute workflow based on plan."""
    workflow_id = state.plan.workflow_id

    if workflow_id == "bias_text":
        # ...
    elif workflow_id == "my_workflow":  # ADD NEW WORKFLOW
        from fairsense_agentix.graphs.my_workflow_graph import (
            create_my_workflow_graph,
        )
        graph = create_my_workflow_graph()
        subgraph_result = graph.invoke({
            "text": state.content,
            "options": state.options,
            "run_id": state.run_id,
        })
        result = {
            "workflow_id": "my_workflow",
            "analysis": subgraph_result["final_result"],
        }
    # ...
```

---

## Testing Guidelines

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_graphs.py

# Run specific test
pytest tests/test_api.py::test_analyze_text

# Run with coverage
pytest --cov=fairsense_agentix --cov-report=html

# Run with verbose output
pytest -v

# Run tests matching pattern
pytest -k "bias"
```

### Writing Tests

#### Unit Test Example

```python
def test_bias_text_workflow():
    """Test bias text workflow with fake LLM."""
    # Setup
    graph = create_bias_text_graph()

    # Execute
    result = graph.invoke({
        "text": "Job posting for young rockstar developers",
        "options": {},
        "run_id": "test-123",
    })

    # Assert
    assert "bias_analysis" in result
    assert result["bias_analysis"].bias_detected is True
    assert "highlighted_html" in result
```

#### Integration Test Example

```python
@pytest.mark.integration
def test_full_analysis_flow():
    """Test complete analysis from API to result."""
    from fairsense_agentix import FairSense

    # Setup
    fs = FairSense()

    # Execute
    result = fs.analyze_text("Sample biased text")

    # Assert
    assert result.status == "success"
    assert result.metadata.execution_time_seconds > 0
    assert len(result.errors) == 0
```

### Mocking LLM Calls

```python
import pytest
from unittest.mock import patch, MagicMock

@pytest.fixture
def mock_llm():
    """Mock LLM tool for fast testing."""
    with patch("fairsense_agentix.tools.llm.openai_llm.OpenAILLM") as mock:
        llm_instance = MagicMock()
        llm_instance.generate.return_value = BiasAnalysisOutput(
            bias_detected=True,
            risk_level="medium",
            bias_instances=[
                BiasInstance(
                    type="gender",
                    severity="high",
                    text_span="rockstar",
                    explanation="Gendered term",
                    start_char=0,
                    end_char=8,
                )
            ],
            overall_assessment="Bias detected",
        )
        mock.return_value = llm_instance
        yield llm_instance

def test_with_mock_llm(mock_llm):
    """Test using mocked LLM."""
    graph = create_bias_text_graph()

    result = graph.invoke({"text": "test", "options": {}})

    assert mock_llm.generate.called
    assert result["bias_analysis"].bias_detected
```

### Test Coverage Requirements

- **Minimum Coverage:** 80% overall
- **Critical Paths:** 95%+ (API, orchestrator, workflows)
- **Tools:** 70%+ (harder to test ML models)
- **Exclude:** Fake implementations, example scripts

---

## Contributing Guidelines

### Pull Request Process

1. **Fork the Repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/fairsense-agentix.git
   cd fairsense-agentix
   git checkout -b feature/my-new-feature
   ```

2. **Make Changes**
   - Write code following style guidelines
   - Add tests for new functionality
   - Update documentation

3. **Run Pre-commit Checks**
   ```bash
   pre-commit run --all-files
   ```

4. **Run Tests**
   ```bash
   pytest
   ```

5. **Commit with Descriptive Message**
   ```bash
   git add .
   git commit -m "feat: Add custom sentiment analysis tool"
   ```

6. **Push and Create PR**
   ```bash
   git push origin feature/my-new-feature
   # Then create PR on GitHub
   ```

### PR Review Checklist

- [ ] Code follows PEP 8 style guide
- [ ] All functions have numpy-style docstrings
- [ ] Type hints added to all functions
- [ ] Tests added for new functionality
- [ ] Tests pass (`pytest`)
- [ ] Pre-commit hooks pass
- [ ] Documentation updated (if applicable)
- [ ] No breaking changes (or documented)

### Commit Message Format

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic changes)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(tools): Add custom sentiment analysis tool

- Implement MySentimentTool class
- Add sentiment tool interface
- Register in tool registry

Closes #123
```

```
fix(graph): Fix bias span extraction for overlapping instances

Previously, overlapping bias spans would cause incorrect highlighting.
This commit adds deduplication logic to merge overlapping spans.

Fixes #456
```

---

## Debugging Tips

### Enable Debug Logging

```bash
# Set environment variable
export FAIRSENSE_LOG_LEVEL=DEBUG

# Or in Python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Visualize LangGraph Workflow

```python
from fairsense_agentix.graphs.bias_text_graph import create_bias_text_graph

graph = create_bias_text_graph()

# Generate Mermaid diagram
print(graph.get_graph().draw_mermaid())

# Save as PNG (requires graphviz)
graph.get_graph().draw_png("workflow.png")
```

### Inspect Telemetry Events

```python
from fairsense_agentix import FairSense
from fairsense_agentix.services.telemetry import telemetry

# Enable telemetry capture
telemetry.enable_capture()

# Run analysis
fs = FairSense()
result = fs.analyze_text("Test text")

# Inspect events
events = telemetry.get_captured_events()
for event in events:
    print(f"[{event['event']}] {event['context']}")
```

### Step Through Workflow

```python
# Run workflow with breakpoint
import pdb

def my_node(state):
    pdb.set_trace()  # Set breakpoint
    # Step through execution
    result = process(state)
    return {"result": result}
```

### Input Type Detection and Routing

The server auto-detects whether a string payload is plain text or a CSV (risk workflow) using `looks_like_csv` in `fairsense_agentix/service_api/utils.py`. The rules are:

| Condition | Detected as |
|---|---|
| `bytes` / `bytearray` | `image` |
| `Path` with image extension | `image` |
| `Path` with `.csv` extension | `csv` |
| String with **≥ 2 lines**, all containing commas, consistent comma count per line | `csv` → risk workflow |
| Everything else (including single-line strings with commas) | `text` → bias text workflow |

**Examples that route to bias text:**
```
We need a skilled, motivated, and experienced engineer.   ← single line, ignored
```
```
This role is rewarding, flexible, and well-paid.
It also offers great benefits, career growth.             ← inconsistent comma counts (3 vs 2)
```

**Examples that route to risk (CSV):**
```
name,age,role
Alice,30,engineer
Bob,25,designer
```

If your text input is unexpectedly routing to the risk workflow, check whether it spans multiple lines and has the same number of commas on each line.

---

## Resources

- **LangGraph Docs:** https://langchain-ai.github.io/langgraph/
- **LangChain Docs:** https://python.langchain.com/
- **FastAPI Docs:** https://fastapi.tiangolo.com/
- **Pydantic Docs:** https://docs.pydantic.dev/
- **FAISS Docs:** https://github.com/facebookresearch/faiss/wiki

---

## Getting Help

- **GitHub Issues:** [Report bugs or request features](https://github.com/VectorInstitute/fairsense-agentix/issues)
- **GitHub Discussions:** [Ask questions](https://github.com/VectorInstitute/fairsense-agentix/discussions)
- **Code Review:** Tag `@VectorInstitute/fairsense-maintainers` in PRs

---

## Next Steps

- **[Architecture](architecture.md)** - Understand the system design
- **[API Reference](api.md)** - Explore the API documentation
- **[User Guide](user_guide.md)** - Learn how to use FairSense
