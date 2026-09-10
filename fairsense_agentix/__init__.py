"""FairSense-AgentiX: Agentic Multimodal Bias & AI-Risk Platform.

Quick Start
-----------
Configure a real LLM provider first (otherwise the default ``fake`` provider
returns synthetic placeholder results and emits a ``MockProviderWarning``)::

    export FAIRSENSE_LLM_PROVIDER=openai
    export FAIRSENSE_LLM_API_KEY=sk-...

    >>> from fairsense_agentix import FairSense
    >>> fs = FairSense()
    >>> result = fs.analyze_text("Job posting text")
    >>> print(result.bias_detected, result.risk_level)
    >>> result.metadata.mock_mode  # False when using a real provider

Advanced (full control):

    >>> from fairsense_agentix import create_orchestrator_graph
    >>> graph = create_orchestrator_graph()
    >>> result = graph.invoke({"input_type": "text", "content": "...", "options": {}})
"""

# High-level API (recommended)
# Server launcher (for programmatic usage)
from importlib.metadata import version

from fairsense_agentix import server
from fairsense_agentix.api import (
    BiasResult,
    FairSense,
    MockProviderWarning,
    ResultMetadata,
    RiskResult,
)

# Configuration
from fairsense_agentix.configs.settings import Settings

# Advanced API (for power users)
from fairsense_agentix.graphs.orchestrator_graph import create_orchestrator_graph


def _get_version() -> str:
    try:
        return version("fairsense-agentix")
    except Exception:
        return "0.1.0"


__version__ = _get_version()

__all__ = [
    # Main API
    "FairSense",
    # Result models
    "BiasResult",
    "RiskResult",
    "ResultMetadata",
    "MockProviderWarning",
    # Configuration
    "Settings",
    # Advanced
    "create_orchestrator_graph",
    # Server launcher
    "server",
]

# ==============================================================================
# Eager Loading: Preload models at import time for fast first use
# ==============================================================================
# This loads all models (LLM, OCR, embeddings, FAISS) when the module is
# imported, making all subsequent function calls instant (~0.03s instead of ~30s).
#
# Trade-off: Import takes 30-60s, but every FairSense().analyze_*() call is instant.
# Perfect for: Production servers, demos, notebooks (import once, use many times)
#
# To disable: Set FAIRSENSE_DISABLE_EAGER_LOADING=true in environment
import os as _os


if _os.getenv("FAIRSENSE_DISABLE_EAGER_LOADING", "").lower() not in (
    "true",
    "1",
    "yes",
):
    from fairsense_agentix.tools.registry import get_tool_registry as _get_registry

    # Force singleton creation (preloads all models)
    _ = _get_registry()
    del _get_registry  # Clean up namespace
