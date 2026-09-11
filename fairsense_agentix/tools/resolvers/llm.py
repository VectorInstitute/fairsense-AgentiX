"""Resolver for LLM tool."""

from fairsense_agentix.configs.settings import Settings
from fairsense_agentix.tools.exceptions import ToolConfigurationError
from fairsense_agentix.tools.interfaces import LLMTool


def _setup_llm_cache(settings: Settings) -> None:
    """Enable LangChain SQLite caching if configured in settings.

    This sets up a global SQLite cache for all LLM calls.
    Content-addressed: cache key = SHA256(model, prompt, params).
    """
    if not settings.llm_cache_enabled:
        return
    from langchain_community.cache import SQLiteCache  # noqa: PLC0415
    from langchain_core.globals import set_llm_cache  # noqa: PLC0415

    # Ensure cache directory exists
    settings.llm_cache_path.parent.mkdir(parents=True, exist_ok=True)
    set_llm_cache(SQLiteCache(database_path=str(settings.llm_cache_path)))


def _build_openai_tool(settings: Settings) -> LLMTool:
    """Build and return a LangChain-backed OpenAI LLMTool.

    Phase 5.2: Real OpenAI LLM via LangChain.
    """
    try:
        from langchain_openai import ChatOpenAI  # noqa: PLC0415
        from pydantic import SecretStr  # noqa: PLC0415

        from fairsense_agentix.services import telemetry  # noqa: PLC0415
        from fairsense_agentix.tools.llm.callbacks import (  # noqa: PLC0415
            TelemetryCallback,
        )
        from fairsense_agentix.tools.llm.langchain_adapter import (  # noqa: PLC0415
            LangChainLLMAdapter,
        )
        from fairsense_agentix.tools.llm.output_schemas import (  # noqa: PLC0415
            BiasAnalysisOutput,
        )

        # Create telemetry callback
        callback = TelemetryCallback(
            telemetry=telemetry,
            provider="openai",
            model=settings.llm_model_name,
        )

        _setup_llm_cache(settings)

        # Create LangChain ChatOpenAI model with retry
        # Note: temperature, max_tokens, timeout set per-call in adapter
        base_model = ChatOpenAI(
            model=settings.llm_model_name,
            api_key=SecretStr(settings.llm_api_key) if settings.llm_api_key else None,
            base_url=settings.llm_base_url,  # None -> api.openai.com
            callbacks=[callback],
        )

        # Apply structured output BEFORE retry wrapper.
        # ChatOpenAI defaults to method="json_schema" (OpenAI structured outputs API).
        # Many chat models (e.g. gpt-4-turbo) do not support that API; LangChain
        # then falls back to function_calling and emits a UserWarning. Using
        # method="function_calling" explicitly matches that fallback; same runtime
        # path those models already used without the warning.
        structured_model = base_model.with_structured_output(
            BiasAnalysisOutput,
            method="function_calling",
        )

        # Add retry after structured output configuration
        langchain_model = structured_model.with_retry(
            stop_after_attempt=3,  # Retry up to 3 times
        )

        # No output parser needed - structured_output handles parsing
        # Wrap in adapter to satisfy LLMTool protocol
        # LangChain types after .with_retry() are complex, requiring type ignores
        return LangChainLLMAdapter(  # type: ignore[return-value]
            langchain_model=langchain_model,  # type: ignore[arg-type]
            telemetry=telemetry,
            settings=settings,
            output_parser=None,  # Not needed with structured_output
            provider_name="openai",
        )

    except Exception as e:
        msg = f"Failed to initialize OpenAI LLM: {e}"
        raise ToolConfigurationError(
            msg,
            context={"llm_provider": settings.llm_provider},
        ) from e


def _build_anthropic_tool(settings: Settings) -> LLMTool:
    """Build and return a LangChain-backed Anthropic LLMTool.

    Phase 5.2: Real Anthropic LLM via LangChain.
    """
    try:
        from langchain_anthropic import ChatAnthropic  # noqa: PLC0415
        from pydantic import SecretStr  # noqa: PLC0415

        from fairsense_agentix.services import telemetry  # noqa: PLC0415
        from fairsense_agentix.tools.llm.callbacks import (  # noqa: PLC0415
            TelemetryCallback,
        )
        from fairsense_agentix.tools.llm.langchain_adapter import (  # noqa: PLC0415
            LangChainLLMAdapter,
        )
        from fairsense_agentix.tools.llm.output_schemas import (  # noqa: PLC0415
            BiasAnalysisOutput,
        )

        # Create telemetry callback
        callback = TelemetryCallback(
            telemetry=telemetry,
            provider="anthropic",
            model=settings.llm_model_name,
        )

        _setup_llm_cache(settings)

        # Create LangChain ChatAnthropic model with retry
        # Note: temperature, max_tokens, timeout set per-call in adapter

        # Ensure API key is present (should be guaranteed by Settings validator)
        if not settings.llm_api_key:
            msg = "API key required for Anthropic provider"
            raise ToolConfigurationError(
                msg,
                context={"llm_provider": settings.llm_provider},
            )

        # ChatAnthropic uses model_name not model
        anthropic_model = ChatAnthropic(  # type: ignore[call-arg]
            model_name=settings.llm_model_name,
            api_key=SecretStr(settings.llm_api_key),
            callbacks=[callback],
        )

        # Apply structured output mode BEFORE retry wrapper
        # Anthropic's native JSON mode is more reliable than prompt-based parsing
        structured_model = anthropic_model.with_structured_output(
            BiasAnalysisOutput,
        )

        # Add retry after structured output configuration
        langchain_model = structured_model.with_retry(
            stop_after_attempt=3,  # Retry up to 3 times
        )

        # No output parser needed - structured_output handles parsing
        # Wrap in adapter to satisfy LLMTool protocol
        # LangChain types after .with_retry() are complex, requiring type ignores
        return LangChainLLMAdapter(  # type: ignore[return-value]
            langchain_model=langchain_model,  # type: ignore[arg-type]
            telemetry=telemetry,
            settings=settings,
            output_parser=None,  # Not needed with structured_output
            provider_name="anthropic",
        )

    except Exception as e:
        msg = f"Failed to initialize Anthropic LLM: {e}"
        raise ToolConfigurationError(
            msg,
            context={"llm_provider": settings.llm_provider},
        ) from e


def _resolve_llm_tool(settings: Settings) -> LLMTool:
    """Resolve LLM tool from settings.

    Parameters
    ----------
    settings : Settings
        Application configuration

    Returns
    -------
    LLMTool
        Configured LLM tool instance

    Raises
    ------
    ToolConfigurationError
        If llm_provider setting is invalid or implementation not available
    """
    if settings.llm_provider == "fake":
        from fairsense_agentix.tools.fake import FakeLLMTool  # noqa: PLC0415

        return FakeLLMTool()

    if settings.llm_provider == "openai":
        return _build_openai_tool(settings)

    if settings.llm_provider == "anthropic":
        return _build_anthropic_tool(settings)

    if settings.llm_provider == "local":
        # Phase 5+: Real local LLM (vLLM, llama.cpp, etc.) - not yet implemented
        raise ToolConfigurationError(
            "Local LLM not yet implemented (future phase)",
            context={"llm_provider": settings.llm_provider},
        )

    raise ToolConfigurationError(
        f"Unknown llm_provider: {settings.llm_provider}",
        context={
            "llm_provider": settings.llm_provider,
            "valid_options": ["fake", "openai", "anthropic", "local"],
        },
    )
