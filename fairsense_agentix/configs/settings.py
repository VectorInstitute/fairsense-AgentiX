"""Module for loading and managing application settings.

This module provides a centralized configuration system using Pydantic Settings.
All configuration can be set via environment variables with the FAIRSENSE_ prefix.

Example:
    >>> from fairsense_agentix.configs.settings import Settings
    >>> settings = Settings()
    >>> print(settings.llm_model_name)
    'gpt-4'

    # Override via environment variable:
    $ export FAIRSENSE_LLM_MODEL_NAME="claude-3-5-sonnet-20241022"
"""

import json
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support.

    All settings can be overridden via environment variables with the
    FAIRSENSE_ prefix. For example, to set llm_model_name, use:
    FAIRSENSE_LLM_MODEL_NAME="gpt-4"

    Attributes
    ----------
    llm_provider : str
        LLM provider to use (openai, anthropic, local, fake)
    llm_model_name : str
        Specific model identifier
    llm_api_key : str | None
        API key for the LLM provider
    llm_base_url : str | None
        Endpoint override for OpenAI-compatible servers (Ollama, vLLM, ...)
    llm_temperature : float
        Sampling temperature for LLM calls (0.0-1.0)
    llm_max_tokens : int
        Maximum tokens to generate per LLM call
    llm_timeout_seconds : int
        Timeout for LLM API calls
    ocr_tool : str
        OCR tool to use (tesseract, paddleocr, fake)
    ocr_language : str
        Language code for OCR (e.g., 'eng', 'fra')
    ocr_confidence_threshold : float
        Minimum confidence for OCR results (0.0-1.0)
    caption_model : str
        Image captioning model (blip, blip2, llava, fake)
    caption_max_length : int
        Maximum length for generated captions
    image_analysis_mode : str
        Image bias analysis mode (vlm, traditional)
    embedding_model : str
        Sentence embedding model name
    embedding_dimension : int
        Expected dimension of embeddings
    faiss_risks_index_path : Path
        Path to FAISS index for risks database
    faiss_rmf_index_path : Path
        Path to FAISS index for AI-RMF database
    faiss_top_k : int
        Number of top results to retrieve from FAISS
    cache_enabled : bool
        Enable/disable caching globally
    cache_backend : str
        Cache backend (memory, redis, filesystem)
    cache_ttl_seconds : int
        Time-to-live for cache entries
    cache_dir : Path
        Directory for filesystem cache
    telemetry_enabled : bool
        Enable/disable telemetry globally
    log_level : str
        Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    otel_endpoint : str | None
        OpenTelemetry collector endpoint
    trace_all_llm_calls : bool
        Whether to trace all LLM calls
    api_host : str
        API server host
    api_port : int
        API server port
    api_reload : bool
        Enable auto-reload for development
    api_cors_origins : list[str]
        Allowed CORS origins for the API
    api_enable_shutdown_endpoint : bool
        Whether POST /v1/shutdown is exposed
    api_shutdown_token : str | None
        Shared secret required to call /v1/shutdown (loopback-only when unset)
    max_refinement_iterations : int
        Maximum refinement iterations for evaluators
    workflow_timeout_seconds : int
        Timeout for entire workflow execution
    router_confidence_threshold : float
        Minimum confidence for router decisions (0.0-1.0)
    bias_categories : list[str]
        Bias categories to detect and analyze
    bias_color_gender : str
        Highlight color for gender bias (hex code)
    bias_color_age : str
        Highlight color for age bias (hex code)
    bias_color_racial : str
        Highlight color for racial bias (hex code)
    bias_color_disability : str
        Highlight color for disability bias (hex code)
    bias_color_socioeconomic : str
        Highlight color for socioeconomic bias (hex code)
    output_dir : Path
        Directory for saved output files (CSV, JSON, HTML)
    summarizer_max_length : int
        Maximum length for generated summaries (characters)
    """

    model_config = SettingsConfigDict(
        env_prefix="FAIRSENSE_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ===========================
    # LLM Configuration
    # ===========================
    llm_provider: Literal["openai", "anthropic", "local", "fake"] = Field(
        default="fake",
        description="LLM provider to use for bias/risk analysis",
    )

    llm_model_name: str = Field(
        default="gpt-4",
        description="Specific model identifier (e.g., gpt-4, claude-3-5-sonnet)",
    )

    llm_api_key: str | None = Field(
        default=None,
        description="API key for the LLM provider",
    )

    llm_base_url: str | None = Field(
        default=None,
        description=(
            "Override the API endpoint for the openai provider. Lets any "
            "OpenAI-compatible server (Ollama, vLLM, LM Studio, ...) act as the "
            "LLM backend, e.g. http://localhost:11434/v1 for Ollama. Ignored by "
            "other providers."
        ),
    )

    llm_temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Sampling temperature for LLM calls",
    )

    llm_max_tokens: int = Field(
        default=2000,
        gt=0,
        description="Maximum tokens to generate per LLM call",
    )

    llm_timeout_seconds: int = Field(
        default=60,
        gt=0,
        description="Timeout for LLM API calls",
    )

    llm_cache_enabled: bool = Field(
        default=True,
        description="Enable LangChain SQLite caching for LLM responses",
    )

    llm_cache_path: Path = Field(
        default=Path(".cache/langchain.db"),
        description="Path to SQLite cache database for LLM responses",
    )

    # ===========================
    # OCR Configuration (Phase 5.3)
    # ===========================
    ocr_tool: Literal["auto", "paddleocr", "tesseract", "fake"] = Field(
        default="auto",
        description=(
            "OCR tool: auto (GPU-adaptive), paddleocr (GPU/best), "
            "tesseract (CPU/fast), fake (testing)"
        ),
    )

    ocr_force_cpu: bool = Field(
        default=False,
        description="Force CPU for OCR even if GPU available (for testing/debugging)",
    )

    ocr_language: str = Field(
        default="eng",
        description="Language code for OCR (e.g., 'eng', 'fra', 'spa', 'chi_sim')",
    )

    ocr_confidence_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold for OCR results (0.0-1.0)",
    )

    # ===========================
    # Image Captioning Configuration (Phase 5.3)
    # ===========================
    caption_model: Literal["auto", "blip2", "blip", "fake"] = Field(
        default="auto",
        description=(
            "Caption model: auto (GPU-adaptive), blip2 (GPU/best), "
            "blip (CPU/fast), fake (testing)"
        ),
    )

    caption_force_cpu: bool = Field(
        default=False,
        description=(
            "Force CPU for captioning even if GPU available (for testing/debugging)"
        ),
    )

    caption_preload: bool = Field(
        default=True,
        description=(
            "Preload model at startup (true: fast calls, slow startup; "
            "false: fast startup, slow first call)"
        ),
    )

    caption_max_length: int = Field(
        default=100,
        gt=0,
        description="Maximum caption length in tokens",
    )

    # ===========================
    # Image Analysis Configuration
    # ===========================
    image_analysis_mode: Literal["vlm", "traditional"] = Field(
        default="vlm",
        description=(
            "Image bias analysis method:\n"
            "- 'vlm': Vision-Language Model with Chain-of-Thought reasoning "
            "(fast, uses llm_provider for vision, requires OpenAI or Anthropic)\n"
            "- 'traditional': OCR + Caption + Text Analysis "
            "(slower, uses local models, works without API)"
        ),
    )

    # ===========================
    # Embedding & FAISS Configuration
    # ===========================
    embedding_model: str = Field(
        default="all-MiniLM-L6-v2",
        description="Sentence embedding model name (from sentence-transformers)",
    )

    embedding_dimension: int = Field(
        default=384,
        gt=0,
        description="Expected dimension of embeddings (must match embedding_model)",
    )

    faiss_risks_index_path: Path = Field(
        default=Path(__file__).parent.parent / "data" / "indexes" / "risks.faiss",
        description="Path to FAISS index for risks database (package-relative)",
    )

    faiss_rmf_index_path: Path = Field(
        default=Path(__file__).parent.parent / "data" / "indexes" / "rmf.faiss",
        description="Path to FAISS index for AI-RMF database (package-relative)",
    )

    faiss_top_k: int = Field(
        default=5,
        gt=0,
        description="Number of top results to retrieve from FAISS searches",
    )

    # ===========================
    # Cache Configuration
    # ===========================
    cache_enabled: bool = Field(
        default=True,
        description="Enable/disable caching globally",
    )

    cache_backend: Literal["memory", "redis", "filesystem"] = Field(
        default="memory",
        description="Cache backend to use",
    )

    cache_ttl_seconds: int = Field(
        default=3600,
        gt=0,
        description="Time-to-live for cache entries in seconds",
    )

    cache_dir: Path = Field(
        default=Path(".cache"),
        description="Directory for filesystem cache",
    )

    # ===========================
    # Telemetry & Observability Configuration
    # ===========================
    telemetry_enabled: bool = Field(
        default=False,
        description="Enable/disable telemetry and detailed logging",
    )

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level for the application",
    )

    otel_endpoint: str | None = Field(
        default=None,
        description="OpenTelemetry collector endpoint (optional)",
    )

    trace_all_llm_calls: bool = Field(
        default=True,
        description="Whether to trace all LLM calls for observability",
    )

    # ===========================
    # API Server Configuration
    # ===========================
    api_host: str = Field(
        default="127.0.0.1",
        description=(
            "API server bind address. Defaults to loopback so the service is not "
            "reachable from other hosts; set to 0.0.0.0 to expose it (e.g. in a "
            "container behind a reverse proxy)."
        ),
    )

    api_port: int = Field(
        default=8000,
        gt=0,
        le=65535,
        description="API server port",
    )

    api_reload: bool = Field(
        default=False,
        description="Enable auto-reload for development (uvicorn --reload)",
    )

    api_cors_origins: Annotated[list[str], NoDecode] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"],
        description=(
            "Allowed CORS origins for the API (JSON list or comma-separated). "
            "Defaults to the local Vite dev server; use ['*'] to allow any origin."
        ),
    )

    api_enable_shutdown_endpoint: bool = Field(
        default=False,
        description=(
            "Expose POST /v1/shutdown. Disabled by default; the server launcher "
            "enables it so the bundled UI can stop the local backend."
        ),
    )

    api_shutdown_token: str | None = Field(
        default=None,
        description=(
            "Shared secret required in the X-Shutdown-Token header for "
            "/v1/shutdown. When unset, shutdown requests are only accepted from "
            "loopback clients."
        ),
    )

    # ===========================
    # Workflow & Orchestration Configuration
    # ===========================
    enable_refinement: bool = Field(
        default=True,
        description="Enable refinement loop (Phase 7+: True by default)",
    )

    max_refinement_iterations: int = Field(
        default=1,
        ge=0,
        description="Maximum refinement iterations for evaluator feedback loops",
    )

    evaluator_enabled: bool = Field(
        default=True,
        description="Enable LLM-based evaluators for post-hoc quality checks",
    )

    bias_evaluator_min_score: int = Field(
        default=75,
        ge=0,
        le=100,
        description="Minimum score (0-100) required for bias evaluator to pass output",
    )

    # ===========================
    # Risk Evaluator Configuration (Phase 7.2)
    # ===========================
    risk_evaluator_min_rmf_functions: int = Field(
        default=3,
        ge=1,
        le=4,
        description=(
            "Minimum number of unique RMF functions for breadth check "
            "(1-4: Govern, Map, Measure, Manage)"
        ),
    )

    risk_evaluator_min_avg_score: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Minimum average FAISS similarity score for risk quality check",
    )

    risk_evaluator_min_risks: int = Field(
        default=3,
        ge=1,
        description="Minimum number of risks required for sufficient coverage",
    )

    risk_duplicate_threshold: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Similarity threshold for duplicate risk detection (0.0-1.0)",
    )

    workflow_timeout_seconds: int = Field(
        default=300,
        gt=0,
        description="Timeout for entire workflow execution",
    )

    router_confidence_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum confidence for router to select a workflow",
    )

    image_validation_enabled: bool = Field(
        default=True,
        description=(
            "Validate image bytes with Pillow before running OCR/caption nodes. "
            "Disable for synthetic tests that use non-image byte strings."
        ),
    )

    # ===========================
    # Bias Detection Configuration
    # ===========================
    bias_categories: list[str] = Field(
        default=["gender", "age", "racial", "disability", "socioeconomic"],
        description="Bias categories to detect and analyze",
    )

    bias_color_gender: str = Field(
        default="#FFB3BA",
        description="Highlight color for gender bias (pink)",
    )

    bias_color_age: str = Field(
        default="#FFDFBA",
        description="Highlight color for age bias (orange)",
    )

    bias_color_racial: str = Field(
        default="#FFFFBA",
        description="Highlight color for racial bias (yellow)",
    )

    bias_color_disability: str = Field(
        default="#BAE1FF",
        description="Highlight color for disability bias (blue)",
    )

    bias_color_socioeconomic: str = Field(
        default="#E0BBE4",
        description="Highlight color for socioeconomic bias (purple)",
    )

    # ===========================
    # Output & Persistence Configuration (Phase 5.4)
    # ===========================
    output_dir: Path = Field(
        default=Path("outputs"),
        description="Directory for saved output files (CSV, JSON, HTML)",
    )

    summarizer_max_length: int = Field(
        default=200,
        gt=0,
        description="Maximum length for generated summaries (characters)",
    )

    def get_bias_type_colors(self) -> dict[str, str]:
        """Get bias type to color mapping.

        Returns a dictionary mapping bias category names to their
        corresponding highlight colors for HTML rendering.

        Returns
        -------
        dict[str, str]
            Mapping of bias type to hex color code

        Examples
        --------
        >>> settings = Settings()
        >>> colors = settings.get_bias_type_colors()
        >>> colors["gender"]
        '#FFB3BA'
        """
        return {
            "gender": self.bias_color_gender,
            "age": self.bias_color_age,
            "racial": self.bias_color_racial,
            "disability": self.bias_color_disability,
            "socioeconomic": self.bias_color_socioeconomic,
        }

    @field_validator(
        "faiss_risks_index_path",
        "faiss_rmf_index_path",
        "cache_dir",
        "output_dir",
    )
    @classmethod
    def expand_path(cls, v: Path) -> Path:
        """Expand and resolve paths to absolute paths.

        Parameters
        ----------
        v : Path
            Path to expand

        Returns
        -------
        Path
            Absolute path
        """
        return v.expanduser().resolve()

    @property
    def mock_components(self) -> list[str]:
        """Names of tools configured with a ``fake`` (mock) implementation.

        Empty when every tool is real. Used to label results and API responses
        so that synthetic output is never mistaken for a real analysis.
        """
        candidates = {
            "llm": self.llm_provider,
            "ocr": self.ocr_tool,
            "caption": self.caption_model,
            "embedder": self.embedding_model,
        }
        return [name for name, value in candidates.items() if value == "fake"]

    @property
    def mock_mode(self) -> bool:
        """True when any tool is a fake — results are synthetic placeholders."""
        return bool(self.mock_components)

    @field_validator("api_cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: object) -> object:
        """Accept a JSON list or a comma-separated string for CORS origins."""
        if isinstance(v, str):
            stripped = v.strip()
            if stripped.startswith("["):
                return json.loads(stripped)
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return v

    @field_validator("llm_api_key")
    @classmethod
    def validate_api_key(cls, v: str | None, info: ValidationInfo) -> str | None:
        """Validate that API key is set for non-fake providers.

        Parameters
        ----------
        v : str | None
            API key value
        info : ValidationInfo
            Validation context with other field values

        Returns
        -------
        str | None
            Validated API key

        Raises
        ------
        ValueError
            If API key is missing for a provider that requires it
        """
        # Note: info.data contains other field values during validation
        provider = info.data.get("llm_provider", "fake")
        if provider in {"openai", "anthropic"} and not v:
            msg = f"llm_api_key is required when llm_provider={provider}"
            raise ValueError(msg)
        return v


# Singleton instance for convenient access
settings = Settings()
