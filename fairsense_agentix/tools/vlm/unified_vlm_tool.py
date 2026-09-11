"""Unified Vision-Language Model tool supporting multiple providers.

This module provides a single VLM implementation that routes to OpenAI or
Anthropic based on the llm_provider setting. This eliminates the need for
separate API keys and configuration - the same provider handles both text
and vision operations.

Key Features:
    - Single API key for text + vision (uses llm_provider setting)
    - Supports OpenAI GPT-4o Vision and Anthropic Claude Sonnet Vision
    - Structured output via Pydantic models (both providers supported)
    - Automatic retry on transient failures
    - Comprehensive error handling and logging
"""

import base64
import logging
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from fairsense_agentix.configs import Settings
from fairsense_agentix.tools.exceptions import VLMError


logger = logging.getLogger(__name__)


def _detect_image_format(image_bytes: bytes) -> str:
    """Detect image format from magic bytes (file signature).

    Inspects the first few bytes of image data to determine the format.
    This ensures correct MIME type in data URLs for API compatibility.

    Parameters
    ----------
    image_bytes : bytes
        Raw image data

    Returns
    -------
    str
        MIME type string (e.g., "image/png", "image/jpeg")

    Notes
    -----
    Supported formats:
    - PNG: Starts with b'\\x89PNG\\r\\n\\x1a\\n'
    - JPEG: Starts with b'\\xff\\xd8\\xff'
    - GIF: Starts with b'GIF87a' or b'GIF89a'
    - WebP: Contains b'RIFF....WEBP'

    Defaults to "image/jpeg" if format cannot be determined.
    """
    if len(image_bytes) < 12:
        # Too small to reliably detect, assume JPEG
        return "image/jpeg"

    # Check PNG signature (first 8 bytes)
    if image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"

    # Check JPEG signature (first 3 bytes)
    if image_bytes[:3] == b"\xff\xd8\xff":
        return "image/jpeg"

    # Check GIF signature (first 6 bytes)
    if image_bytes[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"

    # Check WebP signature (bytes 0-4 are RIFF, bytes 8-12 are WEBP)
    if image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        return "image/webp"

    # Default to JPEG if unknown
    logger.warning(
        f"Could not detect image format from magic bytes, "
        f"defaulting to image/jpeg. First 12 bytes: {image_bytes[:12]!r}",
    )
    return "image/jpeg"


class UnifiedVLMTool:
    """Vision-Language Model tool that routes to OpenAI or Anthropic.

    Uses the same provider and API key as the configured LLM tool,
    eliminating the need for separate VLM configuration. Automatically
    detects the provider from settings and initializes the appropriate
    vision-capable model.

    Supported Providers:
        - OpenAI: gpt-4o, gpt-4-turbo (GPT-4o Vision)
        - Anthropic: claude-sonnet-4-5, claude-sonnet-3-5 (Claude Vision)

    Attributes
    ----------
    settings : Settings
        Application configuration
    provider : str
        Active provider name (openai or anthropic)
    _model : BaseChatModel
        LangChain model instance for the active provider

    Examples
    --------
    >>> from fairsense_agentix.configs import Settings
    >>> settings = Settings(
    ...     llm_provider="openai", llm_model_name="gpt-4o", llm_api_key="sk-proj-..."
    ... )
    >>> vlm = UnifiedVLMTool(settings)
    >>> result = vlm.analyze_image(
    ...     image_bytes=image_data,
    ...     prompt="Analyze this image for bias",
    ...     response_model=BiasVisualAnalysisOutput,
    ... )
    >>> print(result.bias_analysis.overall_assessment)
    """

    def __init__(self, settings: Settings):
        """Initialize VLM tool with provider detection.

        Parameters
        ----------
        settings : Settings
            Application configuration with llm_provider, llm_model_name,
            and llm_api_key

        Raises
        ------
        VLMError
            If provider is not supported or initialization fails
        """
        self.settings = settings
        self.provider = settings.llm_provider
        self._model: BaseChatModel | None = None
        self._initialize_model()

    def _initialize_model(self) -> None:
        """Initialize LangChain model based on configured provider.

        Raises
        ------
        VLMError
            If provider is unsupported or model initialization fails
        """
        if self.provider == "openai":
            self._initialize_openai()
        elif self.provider == "anthropic":
            self._initialize_anthropic()
        else:
            raise VLMError(
                f"VLM requires llm_provider to be 'openai' or 'anthropic', "
                f"got '{self.provider}'",
                context={
                    "provider": self.provider,
                    "supported": ["openai", "anthropic"],
                },
            )

    def _initialize_openai(self) -> None:
        """Initialize OpenAI GPT-4o Vision model.

        Uses same API key as LLM tool (llm_api_key setting).

        Raises
        ------
        VLMError
            If OpenAI initialization fails
        """
        try:
            from langchain_openai import ChatOpenAI
            from pydantic import SecretStr

            self._model = ChatOpenAI(
                model=self.settings.llm_model_name,  # gpt-4o, gpt-4-turbo, etc.
                api_key=(
                    SecretStr(self.settings.llm_api_key)
                    if self.settings.llm_api_key
                    else None
                ),
                timeout=self.settings.llm_timeout_seconds,
                base_url=self.settings.llm_base_url,
            )

            logger.info(
                f"Initialized OpenAI VLM: {self.settings.llm_model_name} "
                f"(using llm_api_key)",
            )

        except ImportError as e:
            raise VLMError(
                "Failed to import OpenAI dependencies. Install with: "
                "pip install langchain-openai",
                context={"error": str(e)},
            ) from e
        except Exception as e:
            raise VLMError(
                f"Failed to initialize OpenAI VLM: {e}",
                context={
                    "provider": "openai",
                    "model": self.settings.llm_model_name,
                },
            ) from e

    def _initialize_anthropic(self) -> None:
        """Initialize Anthropic Claude Sonnet Vision model.

        Uses same API key as LLM tool (llm_api_key setting).

        Raises
        ------
        VLMError
            If Anthropic initialization fails or API key is missing
        """
        try:
            from langchain_anthropic import ChatAnthropic
            from pydantic import SecretStr

            if not self.settings.llm_api_key:
                raise VLMError(
                    "API key required for Anthropic VLM. Set FAIRSENSE_LLM_API_KEY.",
                    context={"provider": "anthropic"},
                )

            model_kwargs: dict[str, Any] = {
                "model_name": self.settings.llm_model_name,  # claude-sonnet-4-5, etc.
                "api_key": SecretStr(self.settings.llm_api_key),
                "timeout": self.settings.llm_timeout_seconds,
            }
            self._model = ChatAnthropic(**model_kwargs)

            logger.info(
                f"Initialized Anthropic VLM: {self.settings.llm_model_name} "
                f"(using llm_api_key)",
            )

        except ImportError as e:
            raise VLMError(
                "Failed to import Anthropic dependencies. Install with: "
                "pip install langchain-anthropic",
                context={"error": str(e)},
            ) from e
        except Exception as e:
            raise VLMError(
                f"Failed to initialize Anthropic VLM: {e}",
                context={
                    "provider": "anthropic",
                    "model": self.settings.llm_model_name,
                },
            ) from e

    def analyze_image(
        self,
        image_bytes: bytes,
        prompt: str,
        response_model: type[BaseModel],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> BaseModel:
        """Analyze image with structured Pydantic output.

        Sends image + prompt to vision-language model (OpenAI or Anthropic)
        and returns structured output matching the provided Pydantic schema.
        Both providers support the same message format and structured output.

        Parameters
        ----------
        image_bytes : bytes
            Raw image data (PNG, JPEG, etc.)
        prompt : str
            Analysis instructions (e.g., bias detection prompt)
        response_model : type[BaseModel]
            Pydantic model class for structured output validation
        temperature : float | None, optional
            Sampling temperature (0.0-1.0). If None, uses llm_temperature from settings.
        max_tokens : int | None, optional
            Maximum tokens to generate. If None, uses llm_max_tokens from settings.

        Returns
        -------
        BaseModel
            Instance of response_model with populated fields

        Raises
        ------
        VLMError
            If analysis fails (invalid image, API error, timeout, etc.)

        Notes
        -----
        - Image is automatically base64-encoded for API transmission
        - Both OpenAI and Anthropic use the same message format
        - Structured output enforced via .with_structured_output()
        - Automatic retry (3 attempts) on transient failures
        - Character positions (start_char, end_char) should be 0 for images
        - evidence_source should be "visual" for image analysis

        Examples
        --------
        >>> result = vlm.analyze_image(
        ...     image_bytes=image_data,
        ...     prompt="Analyze for gender and age bias",
        ...     response_model=BiasVisualAnalysisOutput,
        ... )
        >>> assert isinstance(result, BiasVisualAnalysisOutput)
        >>> if result.bias_analysis.bias_detected:
        ...     for instance in result.bias_analysis.bias_instances:
        ...         print(f"{instance.type}: {instance.explanation}")
        """
        # Use defaults from settings if not provided
        temperature = (
            temperature if temperature is not None else self.settings.llm_temperature
        )
        max_tokens = (
            max_tokens if max_tokens is not None else self.settings.llm_max_tokens
        )

        try:
            # Detect image format from magic bytes to use correct MIME type
            mime_type = _detect_image_format(image_bytes)

            # Encode image to base64 for API transmission
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")

            logger.info(
                f"VLM analyzing image: {len(image_bytes)} bytes "
                f"(format: {mime_type}) via {self.provider}",
            )

            # Create multimodal message (same format for both providers)
            # IMPORTANT: Use detected MIME type, not hardcoded jpeg
            message = HumanMessage(
                content=[
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{image_b64}"},
                    },
                ],
            )

            # Ensure model is initialized
            if self._model is None:
                raise VLMError(
                    "Model not initialized",
                    context={"provider": self.provider},
                )

            # OpenAI: use function_calling to skip json_schema and UserWarning for
            # models without native structured-output support (see llm resolver).
            # Anthropic already defaults to function_calling.
            if self.provider == "openai":
                structured_model = self._model.with_structured_output(
                    response_model,
                    method="function_calling",
                )
            else:
                structured_model = self._model.with_structured_output(response_model)

            # Add retry for transient failures
            structured_model_with_retry = structured_model.with_retry(
                stop_after_attempt=3,
            )

            # Invoke API (OpenAI or Anthropic depending on provider)
            # Note: config dict is converted internally by LangChain
            result = structured_model_with_retry.invoke(
                [message],
                config={"temperature": temperature, "max_tokens": max_tokens},  # type: ignore[arg-type]
            )

            logger.info(
                f"VLM analysis complete via {self.provider}: "
                f"{response_model.__name__} returned",
            )

            # Type narrowing: structured_output returns the response_model type
            return result  # type: ignore[return-value]

        except Exception as e:
            logger.error(
                f"VLM analysis failed: {e}",
                extra={
                    "provider": self.provider,
                    "model": self.settings.llm_model_name,
                    "image_size": len(image_bytes),
                },
            )
            raise VLMError(
                f"Image analysis failed: {e}",
                context={
                    "provider": self.provider,
                    "model": self.settings.llm_model_name,
                    "image_size_bytes": len(image_bytes),
                },
            ) from e
