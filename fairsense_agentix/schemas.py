"""Pydantic result models for FairSense-AgentiX API.

ResultMetadata, BiasResult, and RiskResult are used as return types and
FastAPI response models for the high-level API (analyze_text, analyze_image,
assess_risk).
"""

from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from fairsense_agentix.tools.llm.output_schemas import BiasAnalysisOutput


# ============================================================================
# Result Models (Pydantic for FastAPI compatibility)
# ============================================================================


class ResultMetadata(BaseModel):
    """Metadata about analysis execution.

    Attributes
    ----------
    run_id : str
        Unique identifier for tracing this execution
    workflow_id : str
        Which workflow was executed ("bias_text", "bias_image", "risk")
    execution_time_seconds : float
        Total execution time in seconds
    router_reasoning : str
        Human-readable explanation of why this workflow was selected
    router_confidence : float
        Router's confidence in workflow selection (0.0-1.0)
    refinement_count : int
        Number of refinement iterations performed (0 if none)
    preflight_score : float | None
        Pre-execution quality score (None if not evaluated, Phase 7+)
    posthoc_score : float | None
        Post-execution quality score (None if not evaluated, Phase 7+)
    llm_provider : str
        LLM provider that produced this result ("openai", "anthropic", "fake", ...)
    mock_mode : bool
        True when any tool was a ``fake`` implementation. Such results are
        synthetic placeholders for testing and must not be interpreted as a
        real analysis.
    mock_components : list[str]
        Which tools were fakes (e.g. ``["llm", "ocr"]``); empty when none
    """

    run_id: str = Field(description="Unique execution identifier for tracing")
    workflow_id: str = Field(description="Workflow executed")
    execution_time_seconds: float = Field(description="Total execution time")
    router_reasoning: str = Field(description="Why this workflow was selected")
    router_confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Router confidence (0.0-1.0)",
    )
    refinement_count: int = Field(ge=0, description="Number of refinement iterations")
    preflight_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Pre-execution quality score (Phase 7+)",
    )
    posthoc_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Post-execution quality score (Phase 7+)",
    )
    llm_provider: str = Field(
        "unknown",
        description="LLM provider that produced this result",
    )
    mock_mode: bool = Field(
        False,
        description=(
            "True when any tool was a fake implementation; the result is a "
            "synthetic placeholder, not a real analysis"
        ),
    )
    mock_components: list[str] = Field(
        default_factory=list,
        description="Tools that were fakes (e.g. ['llm']); empty when none",
    )


class BiasResult(BaseModel):
    """Result from text or image bias analysis.

    This model is compatible with FastAPI (Pydantic-based) and provides
    attribute-style access to all results and metadata.

    Attributes
    ----------
    status : str
        Execution status: "success", "failed", or "partial"
    bias_detected : bool
        Whether bias was detected (None if using fake LLM)
    risk_level : str
        Risk level: "low", "medium", "high" (None if using fake LLM)
    bias_analysis : BiasAnalysisOutput | str | None
        Structured bias analysis (BiasAnalysisOutput) from real LLM,
        or string summary from fake LLM, or None if failed
    bias_instances : list[dict] | None
        List of bias instances with type, severity, text_span, explanation.
        None if using fake LLM or if no structured output
    summary : str | None
        Optional condensed summary of findings
    highlighted_html : str | None
        HTML with bias spans color-coded by type
    ocr_text : str | None
        Text extracted via OCR (image workflow only)
    caption_text : str | None
        Generated image caption (image workflow only)
    merged_text : str | None
        Combined OCR + caption text (image workflow only)
    metadata : ResultMetadata
        Execution metadata (timing, routing, quality scores)
    errors : list[str]
        Error messages (empty if successful)
    warnings : list[str]
        Warning messages (empty if none)

    Examples
    --------
    >>> result = analyze_text("Job posting")
    >>> if result.status == "success":
    ...     print(f"Bias detected: {result.bias_detected}")
    ...     print(f"Risk level: {result.risk_level}")
    ...     if result.bias_instances:
    ...         for inst in result.bias_instances:
    ...             print(f"  - {inst['type']}: {inst['text_span']}")
    >>> print(f"Execution time: {result.metadata.execution_time_seconds:.2f}s")
    >>> print(f"Router confidence: {result.metadata.router_confidence:.2%}")
    """

    status: Literal["success", "failed", "partial"] = Field(
        description="Execution status",
    )
    bias_detected: Optional[bool] = Field(None, description="Whether bias was detected")
    risk_level: Optional[Literal["low", "medium", "high"]] = Field(
        None,
        description="Overall risk level",
    )
    bias_analysis: Optional[Union[BiasAnalysisOutput, str]] = Field(
        None,
        description="Structured or string bias analysis",
    )
    bias_instances: Optional[list[dict[str, Any]]] = Field(
        None,
        description="Individual bias instances with details",
    )
    summary: Optional[str] = Field(None, description="Optional condensed summary")
    highlighted_html: Optional[str] = Field(
        None,
        description="HTML with color-coded bias highlighting",
    )

    # Image-specific fields (None for text workflow)
    ocr_text: Optional[str] = Field(None, description="OCR extracted text (image only)")
    caption_text: Optional[str] = Field(
        None,
        description="Generated caption (image only)",
    )
    merged_text: Optional[str] = Field(
        None,
        description="Combined OCR + caption text (image only)",
    )
    image_base64: Optional[str] = Field(
        None,
        description=(
            "Base64-encoded image with data URL for UI display (VLM workflow only)"
        ),
    )

    # Metadata and diagnostics
    metadata: ResultMetadata = Field(description="Execution metadata")
    errors: list[str] = Field(default_factory=list, description="Error messages")
    warnings: list[str] = Field(default_factory=list, description="Warning messages")

    model_config = ConfigDict(
        arbitrary_types_allowed=True,  # BiasAnalysisOutput in bias_analysis union
    )


class RiskResult(BaseModel):
    """Result from AI risk assessment.

    This model is compatible with FastAPI (Pydantic-based) and provides
    attribute-style access to all results and metadata.

    Attributes
    ----------
    status : str
        Execution status: "success", "failed", or "partial"
    embedding : list[float] | None
        Vector embedding of scenario (384 dimensions for default model)
    risks : list[dict[str, Any]]
        Top-k AI risks found via semantic search, each with:
        - name: str (risk name)
        - description: str (risk description)
        - score: float (similarity score 0.0-1.0)
        - category: str (risk category)
    rmf_recommendations : dict[str, list[dict[str, Any]]]
        AI-RMF recommendations per risk, keyed by risk ID
    html_table : str | None
        Formatted HTML table of risks + recommendations
    csv_path : str | None
        Path to exported CSV file
    metadata : ResultMetadata
        Execution metadata (timing, routing, quality scores)
    errors : list[str]
        Error messages (empty if successful)
    warnings : list[str]
        Warning messages (empty if none)

    Examples
    --------
    >>> result = assess_risk("AI deployment scenario")
    >>> if result.status == "success":
    ...     print(f"Found {len(result.risks)} risks")
    ...     for risk in result.risks[:3]:
    ...         print(f"  - {risk['name']}: {risk['score']:.3f}")
    >>> print(f"Execution time: {result.metadata.execution_time_seconds:.2f}s")
    """

    status: Literal["success", "failed", "partial"] = Field(
        description="Execution status",
    )
    embedding: Optional[list[float]] = Field(
        None,
        description="Vector embedding of scenario",
    )
    risks: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Top-k AI risks from semantic search",
    )
    rmf_recommendations: dict[str, list[dict[str, Any]]] = Field(
        default_factory=dict,
        description="AI-RMF recommendations per risk",
    )
    html_table: Optional[str] = Field(
        None,
        description="Formatted HTML table of risks + recommendations",
    )
    csv_path: Optional[str] = Field(None, description="Path to exported CSV file")

    # Metadata and diagnostics
    metadata: ResultMetadata = Field(description="Execution metadata")
    errors: list[str] = Field(default_factory=list, description="Error messages")
    warnings: list[str] = Field(default_factory=list, description="Warning messages")
