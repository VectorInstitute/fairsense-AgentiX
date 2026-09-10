"""High-level API for FairSense-AgentiX.

This module provides a clean, user-friendly interface for bias detection and
risk assessment. It wraps the internal graph orchestration with Pydantic models
that are easy to use in scripts, FastAPI servers, and Streamlit apps.

Examples
--------
    >>> from fairsense_agentix import FairSense
    >>> fs = FairSense()  # Initialize once, reuse for many calls
    >>> result = fs.analyze_text("Text 1", temperature=0.3)
    >>> result2 = fs.analyze_text("Text 2", temperature=0.3)

FastAPI integration:

    >>> from fastapi import FastAPI
    >>> from fairsense_agentix import FairSense, BiasResult
    >>> app = FastAPI()
    >>> fs = FairSense()
    >>> @app.post("/analyze", response_model=BiasResult)
    >>> def analyze(text: str):
    ...     return fs.analyze_text(text)

Configuration is controlled via environment variables (see Settings docs):
    - FAIRSENSE_LLM_PROVIDER: "openai", "anthropic", "local", "fake"
    - FAIRSENSE_LLM_API_KEY: Your API key
    - FAIRSENSE_LLM_MODEL_NAME: Model to use (e.g., "gpt-4")
    - FAIRSENSE_OCR_TOOL: "tesseract", "paddleocr", "fake"
    - FAIRSENSE_CAPTION_MODEL: "blip", "blip2", "fake"

Per-request options can be passed to analysis methods (see options parameter docs).
"""

import logging
import time
import warnings
from pathlib import Path
from typing import Any, Union

# Import logging config for side effects (suppress verbose HTTP logs)
from fairsense_agentix import logging_config  # noqa: F401
from fairsense_agentix.configs import settings
from fairsense_agentix.graphs.orchestrator_graph import create_orchestrator_graph
from fairsense_agentix.schemas import BiasResult, ResultMetadata, RiskResult
from fairsense_agentix.tools.llm.output_schemas import BiasAnalysisOutput


__all__ = [
    "FairSense",
    "BiasResult",
    "MockProviderWarning",
    "ResultMetadata",
    "RiskResult",
]

logger = logging.getLogger(__name__)

MOCK_MODE_WARNING = (
    "MOCK MODE: one or more tools are configured as 'fake' ({components}). "
    "This result is a synthetic placeholder for testing, not a real analysis. "
    "Set FAIRSENSE_LLM_PROVIDER (openai/anthropic) and FAIRSENSE_LLM_API_KEY "
    "for real analysis."
)


class MockProviderWarning(RuntimeWarning):
    """Emitted when FairSense is initialised with fake (mock) tools."""


def _with_mock_warning(existing: list[str]) -> list[str]:
    """Prepend a mock-mode notice to a result's warnings when fakes are active."""
    if not settings.mock_mode:
        return existing
    notice = MOCK_MODE_WARNING.format(components=", ".join(settings.mock_components))
    return [notice, *existing]


# ============================================================================
# Main API Class
# ============================================================================


class FairSense:
    """High-level API for bias detection and AI risk assessment.

    This class provides a clean interface for analyzing text, images, and
    AI deployment scenarios. It manages graph initialization internally and
    can be reused for multiple analyses (recommended for performance).

    Configuration
    -------------
    Configuration is controlled via environment variables or .env file.
    Set these before initializing FairSense:

        - FAIRSENSE_LLM_PROVIDER: "openai", "anthropic", "local", "fake"
        - FAIRSENSE_LLM_API_KEY: Your API key (required for real analysis)
        - FAIRSENSE_LLM_MODEL_NAME: Model to use (default per provider)
        - FAIRSENSE_OCR_TOOL: "tesseract", "paddleocr", "fake" (default "tesseract")
        - FAIRSENSE_CAPTION_MODEL: "blip", "blip2", "fake" (default "blip")
        - FAIRSENSE_TELEMETRY_ENABLED: "true" or "false" (default "true")

    See Settings documentation for all available configuration options.

    Per-Request Options
    -------------------
    All analysis methods accept optional **options kwargs:

    Text/Image Bias Detection:
        - temperature: LLM temperature (0.0-1.0, default 0.3)
        - max_tokens: Maximum LLM response tokens (default 2000)
        - ocr_language: OCR language code (default "eng")
        - caption_max_length: Max caption length (default 100)

    Risk Assessment:
        - top_k: Number of risks to retrieve (default 5, max 100)
        - rmf_per_risk: RMF recommendations per risk (default 3, max 20)

    Examples
    --------
    Basic usage:

        >>> fs = FairSense()
        >>> result = fs.analyze_text("Job posting text")
        >>> print(result.bias_detected, result.risk_level)

    With configuration:

        >>> result = fs.analyze_text(
        ...     "Job posting",
        ...     temperature=0.2,  # Lower for consistency
        ...     max_tokens=3000,  # More detailed analysis
        ... )

    Batch processing:

        >>> fs = FairSense()  # Initialize once
        >>> for text in texts:
        ...     result = fs.analyze_text(text)
        ...     print(f"{result.metadata.run_id}: {result.status}")

    FastAPI integration:

        >>> from fastapi import FastAPI
        >>> app = FastAPI()
        >>> fs = FairSense()
        >>> @app.post("/analyze", response_model=BiasResult)
        >>> def analyze(text: str):
        ...     return fs.analyze_text(text)
    """

    def __init__(self) -> None:
        """Initialize FairSense API.

        This creates and compiles the orchestrator graph. Graph compilation is
        expensive (~1-2s), so reuse this instance for multiple analyses.

        **Performance Note**: Models are preloaded at module import time, so
        FairSense initialization is fast and all analysis calls are instant.
        """
        # Tool registry already loaded at module import (see __init__.py)
        # Just create the orchestrator graph
        self._graph = create_orchestrator_graph()

        # The default provider is "fake" so the package imports without an API
        # key, but that also means FairSense() "works" out of the box while
        # returning synthetic output. Say so loudly.
        if settings.mock_mode:
            notice = MOCK_MODE_WARNING.format(
                components=", ".join(settings.mock_components),
            )
            logger.warning(notice)
            warnings.warn(notice, MockProviderWarning, stacklevel=2)

    def analyze_text(
        self,
        text: str,
        run_id: str | None = None,
        **options: Any,
    ) -> BiasResult:
        """Detect bias in text.

        Analyzes text for various forms of bias including gender, age, racial,
        disability, and socioeconomic bias. Uses LLM to identify bias instances,
        generate explanations, and produce color-coded HTML output.

        Parameters
        ----------
        text : str
            Text to analyze for bias
        run_id : str | None, optional
            Pre-generated run ID for tracing (if None, auto-generated)
        **options
            Optional configuration overrides:
            - temperature: LLM temperature (0.0-1.0, default 0.3)
            - max_tokens: Maximum response tokens (default 2000)

        Returns
        -------
        BiasResult
            Complete analysis result with bias detection, instances, HTML output,
            execution metadata, and any errors/warnings

        Examples
        --------
        >>> fs = FairSense()
        >>> result = fs.analyze_text("We need young rockstar developers")
        >>> if result.bias_detected:
        ...     print(f"Risk: {result.risk_level}")
        ...     for inst in result.bias_instances or []:
        ...         print(f"  {inst['type']}: {inst['text_span']}")
        """
        start_time = time.time()

        # Prepare input dict with optional run_id
        input_dict: dict[str, Any] = {
            "input_type": "text",
            "content": text,
            "options": options,
        }
        if run_id is not None:
            input_dict["run_id"] = run_id

        result = self._graph.invoke(input_dict)

        execution_time = time.time() - start_time

        return self._build_bias_result(result, execution_time)

    def analyze_image(
        self,
        image: Union[bytes, Path],
        run_id: str | None = None,
        **options: Any,
    ) -> BiasResult:
        """Detect bias in images.

        Analyzes images by extracting text (OCR), generating captions, and
        performing bias analysis on the combined text. Uses parallel execution
        for OCR and captioning for optimal performance.

        Parameters
        ----------
        image : bytes | Path
            Image data as bytes or path to image file
        run_id : str | None, optional
            Pre-generated run ID for tracing (if None, auto-generated)
        **options
            Optional configuration overrides:
            - ocr_language: OCR language code (default "eng")
            - caption_max_length: Max caption length (default 100)
            - temperature: LLM temperature (0.0-1.0, default 0.3)

        Returns
        -------
        BiasResult
            Complete analysis result including OCR text, caption, bias detection,
            HTML output, execution metadata, and any errors/warnings

        Examples
        --------
        >>> fs = FairSense()
        >>> result = fs.analyze_image(Path("hiring_ad.png"))
        >>> print(f"OCR: {result.ocr_text}")
        >>> print(f"Caption: {result.caption_text}")
        >>> if result.bias_detected:
        ...     print(f"Bias found: {result.risk_level}")
        """
        start_time = time.time()

        # Load image if path provided
        if isinstance(image, Path):
            image = image.read_bytes()

        # Prepare input dict with optional run_id
        input_dict: dict[str, Any] = {
            "input_type": "image",
            "content": image,
            "options": options,
        }
        if run_id is not None:
            input_dict["run_id"] = run_id

        result = self._graph.invoke(input_dict)

        execution_time = time.time() - start_time

        return self._build_bias_result(result, execution_time)

    def assess_risk(
        self,
        scenario: str,
        run_id: str | None = None,
        **options: Any,
    ) -> RiskResult:
        """Assess AI risks in deployment scenario.

        Performs semantic search against 280+ AI risks from the NIST AI Risk
        Management Framework. Retrieves relevant risks and corresponding
        mitigation recommendations.

        Parameters
        ----------
        scenario : str
            AI deployment scenario description
        run_id : str | None, optional
            Pre-generated run ID for tracing (if None, auto-generated)
        **options
            Optional configuration overrides:
            - top_k: Number of risks to retrieve (default 5, max 100)
            - rmf_per_risk: Recommendations per risk (default 3, max 20)

        Returns
        -------
        RiskResult
            Complete risk assessment including identified risks, RMF recommendations,
            HTML table, CSV export path, execution metadata, and any errors/warnings

        Examples
        --------
        >>> fs = FairSense()
        >>> result = fs.assess_risk(
        ...     "Facial recognition for employee monitoring", top_k=10
        ... )
        >>> print(f"Found {len(result.risks)} risks")
        >>> for risk in result.risks:
        ...     print(f"  {risk['name']}: {risk['score']:.3f}")
        >>> print(f"CSV exported to: {result.csv_path}")
        """
        start_time = time.time()

        # Prepare input dict with optional run_id
        input_dict: dict[str, Any] = {
            "input_type": "csv",  # CSV triggers risk workflow
            "content": scenario,
            "options": options,
        }
        if run_id is not None:
            input_dict["run_id"] = run_id

        result = self._graph.invoke(input_dict)

        execution_time = time.time() - start_time

        return self._build_risk_result(result, execution_time)

    def _build_bias_result(
        self,
        raw_result: dict[str, Any],
        execution_time: float,
    ) -> BiasResult:
        """Build BiasResult from orchestrator output."""
        final = raw_result["final_result"]
        output = final.get("output") or {}

        # Extract bias analysis (always BiasAnalysisOutput now)
        bias_analysis = output.get("bias_analysis")

        # Determine if structured or string
        bias_detected = None
        risk_level = None
        bias_instances = None

        if isinstance(bias_analysis, BiasAnalysisOutput):
            # Structured output (always the case now with new design)
            bias_detected = bias_analysis.bias_detected
            risk_level = bias_analysis.risk_level
            # Convert Pydantic models to dicts for JSON serialization
            bias_instances = [
                inst.model_dump() for inst in bias_analysis.bias_instances
            ]
        elif bias_analysis is None:
            # No analysis (shouldn't happen in normal flow)
            bias_detected = None
            risk_level = None
        else:
            # Unexpected type (shouldn't happen with new design)
            raise TypeError(
                f"Unexpected bias_analysis type: {type(bias_analysis)}. "
                "Expected BiasAnalysisOutput.",
            )

        # Build metadata
        metadata = ResultMetadata(
            run_id=final["run_id"],
            workflow_id=final["workflow_id"],
            execution_time_seconds=execution_time,
            router_reasoning=final["metadata"]["plan_reasoning"] or "",
            router_confidence=final["metadata"]["plan_confidence"] or 0.0,
            refinement_count=final["refinement_count"],
            preflight_score=final["metadata"].get("preflight_score"),
            posthoc_score=final["metadata"].get("posthoc_score"),
            llm_provider=settings.llm_provider,
            mock_mode=settings.mock_mode,
            mock_components=settings.mock_components,
        )

        return BiasResult(
            status=final["status"],
            bias_detected=bias_detected,
            risk_level=risk_level,
            bias_analysis=bias_analysis,
            bias_instances=bias_instances,
            summary=output.get("summary"),
            highlighted_html=output.get("highlighted_html"),
            ocr_text=output.get("ocr_text"),
            caption_text=output.get("caption_text"),
            merged_text=output.get("merged_text"),
            image_base64=output.get("image_base64"),
            metadata=metadata,
            errors=final["errors"],
            warnings=_with_mock_warning(final["warnings"]),
        )

    def _build_risk_result(
        self,
        raw_result: dict[str, Any],
        execution_time: float,
    ) -> RiskResult:
        """Build RiskResult from orchestrator output."""
        final = raw_result["final_result"]
        output = final.get("output") or {}

        # Build metadata
        metadata = ResultMetadata(
            run_id=final["run_id"],
            workflow_id=final["workflow_id"],
            execution_time_seconds=execution_time,
            router_reasoning=final["metadata"]["plan_reasoning"] or "",
            router_confidence=final["metadata"]["plan_confidence"] or 0.0,
            refinement_count=final["refinement_count"],
            preflight_score=final["metadata"].get("preflight_score"),
            posthoc_score=final["metadata"].get("posthoc_score"),
            llm_provider=settings.llm_provider,
            mock_mode=settings.mock_mode,
            mock_components=settings.mock_components,
        )

        return RiskResult(
            status=final["status"],
            embedding=output.get("embedding"),
            risks=output.get("risks", []),
            rmf_recommendations=output.get("rmf_recommendations", {}),
            html_table=output.get("html_table"),
            csv_path=output.get("csv_path"),
            metadata=metadata,
            errors=final["errors"],
            warnings=_with_mock_warning(final["warnings"]),
        )
