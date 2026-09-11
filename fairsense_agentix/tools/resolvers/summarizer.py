"""Resolver for summarizer tool."""

from fairsense_agentix.configs.settings import Settings
from fairsense_agentix.tools.exceptions import ToolConfigurationError
from fairsense_agentix.tools.interfaces import SummarizerTool


def _resolve_summarizer_tool(settings: Settings) -> SummarizerTool:
    """Resolve summarizer tool from settings.

    In most cases, the summarizer uses the same LLM backend as the main
    LLM tool, just with a different prompt. This ensures cache sharing and
    consistent telemetry tracking.

    Design Choice: Reuse LLM Model
    -------------------------------
    The summarizer reuses the SAME LangChain model instance as the main LLM
    tool. This is critical for:
    - **Cache sharing**: Avoid duplicate API calls (cost savings)
    - **Telemetry consistency**: Track all LLM usage in one place
    - **Connection pooling**: Single HTTP client for all requests

    Parameters
    ----------
    settings : Settings
        Application configuration

    Returns
    -------
    SummarizerTool
        Configured summarizer tool instance

    Raises
    ------
    ToolConfigurationError
        If summarizer cannot be constructed
    """
    import logging  # noqa: PLC0415

    logger = logging.getLogger(__name__)

    if settings.llm_provider == "fake":
        from fairsense_agentix.tools.fake import FakeSummarizerTool  # noqa: PLC0415

        return FakeSummarizerTool()

    # Phase 5.4: Use LLM-based summarizer
    # NOTE: Creates separate model instance without structured output
    # (cannot reuse bias analysis model which has structured output configured)
    try:
        from fairsense_agentix.prompts import PromptLoader  # noqa: PLC0415
        from fairsense_agentix.services import telemetry  # noqa: PLC0415
        from fairsense_agentix.tools.summarizer import LLMSummarizer  # noqa: PLC0415

        # Create a plain text model for summarization (no structured output)
        if settings.llm_provider == "openai":
            from langchain_openai import ChatOpenAI  # noqa: PLC0415
            from pydantic import SecretStr  # noqa: PLC0415

            base_model = ChatOpenAI(
                model=settings.llm_model_name,
                api_key=SecretStr(settings.llm_api_key)
                if settings.llm_api_key
                else None,
                base_url=settings.llm_base_url,
            )
            # Add retry (no structured output for summarizer)
            langchain_model = base_model.with_retry(stop_after_attempt=3)

        elif settings.llm_provider == "anthropic":
            from langchain_anthropic import ChatAnthropic  # noqa: PLC0415
            from pydantic import SecretStr  # noqa: PLC0415

            # Ensure API key is present (should be validated by Settings)
            if not settings.llm_api_key:
                raise ToolConfigurationError(
                    "API key required for Anthropic provider",
                    context={"llm_provider": settings.llm_provider},
                )

            base_model = ChatAnthropic(  # type: ignore[call-arg,assignment]
                model_name=settings.llm_model_name,
                api_key=SecretStr(settings.llm_api_key),
            )
            # Add retry (no structured output for summarizer)
            langchain_model = base_model.with_retry(stop_after_attempt=3)

        else:
            raise ToolConfigurationError(
                f"Unsupported LLM provider for summarizer: {settings.llm_provider}",
                context={"llm_provider": settings.llm_provider},
            )

        logger.info(
            f"Creating LLMSummarizer (plain text model from {settings.llm_provider})",
        )

        return LLMSummarizer(
            langchain_model=langchain_model,  # type: ignore[arg-type]
            telemetry=telemetry,
            settings=settings,
            prompt_loader=PromptLoader(),
        )

    except Exception as e:
        raise ToolConfigurationError(
            f"Failed to create LLMSummarizer: {e}",
            context={
                "llm_provider": settings.llm_provider,
                "error_type": type(e).__name__,
            },
        ) from e
