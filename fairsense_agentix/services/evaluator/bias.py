"""LLM-based evaluator for post-hoc quality checks on bias workflow output."""

from __future__ import annotations

import json
import logging
from typing import Any, cast

from langchain_anthropic import ChatAnthropic
from langchain_community.cache import SQLiteCache
from langchain_core.globals import set_llm_cache
from langchain_core.language_models import BaseLanguageModel
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, SecretStr

from fairsense_agentix.configs import settings
from fairsense_agentix.graphs.state import EvaluationResult
from fairsense_agentix.prompts.prompt_loader import PromptLoader
from fairsense_agentix.services.telemetry import telemetry
from fairsense_agentix.tools.llm.callbacks import TelemetryCallback
from fairsense_agentix.tools.llm.output_schemas import BiasAnalysisOutput

from .common import EvaluationContext


logger = logging.getLogger(__name__)


class BiasEvaluatorOutput(BaseModel):
    """Structured response from the bias evaluator critique."""

    score: int = Field(..., ge=0, le=100)
    justification: str = Field(..., description="Why this score was assigned")
    suggested_changes: list[str] = Field(
        default_factory=list,
        description="Concrete actions the next run should apply",
    )


def evaluate_bias_output(
    workflow_result: dict[str, Any],
    *,
    original_text: str | None,
    options: dict[str, Any],
    context: EvaluationContext,
) -> EvaluationResult:
    """Evaluate bias workflow output with a single-shot critique.

    Parameters
    ----------
    workflow_result : dict[str, Any]
        Output payload from bias_text or bias_image workflow.
    original_text : str | None
        Source text (for text workflow) or merged OCR+caption text for image workflow.
    options : dict[str, Any]
        Orchestrator options (used for debug hooks / refinement hints).
    context : EvaluationContext
        Metadata describing the workflow under evaluation.
    """
    if not settings.evaluator_enabled:
        logger.debug("Evaluator disabled; returning pass-through result")
        return EvaluationResult(
            passed=True,
            score=1.0,
            issues=[],
            explanation="Evaluators disabled",
        )

    # Allow tests and debug runs to force a score before calling the LLM.
    forced_score = _extract_forced_score(options)
    feedback_applied = bool(options.get("bias_prompt_feedback"))

    if forced_score is not None and not feedback_applied:
        critique = BiasEvaluatorOutput(
            score=forced_score,
            justification="Forced score for testing",
            suggested_changes=[
                "Address evaluator feedback by covering missing categories",
                "Ground bias spans explicitly in the source text",
            ],
        )
    elif settings.llm_provider == "fake":
        critique = _simulate_bias_evaluator(feedback_applied)
    else:
        critique = _invoke_bias_evaluator_llm(
            workflow_result=workflow_result,
            original_text=original_text,
            existing_feedback=options.get("bias_prompt_feedback") or [],
        )

    passed = critique.score >= settings.bias_evaluator_min_score
    metadata = {
        "bias": {
            "score": critique.score,
            "threshold": settings.bias_evaluator_min_score,
            "justification": critique.justification,
            "suggested_changes": critique.suggested_changes,
            "workflow_id": context.workflow_id,
            "run_id": context.run_id,
        },
    }

    refinement_hints: dict[str, Any] = {}
    issues: list[str] = []

    if not passed:
        issues.append(critique.justification)
        feedback = critique.suggested_changes or [
            "Re-check every bias category and cite exact spans.",
        ]
        refinement_hints = {
            "options": {
                "bias_prompt_feedback": feedback,
            },
        }

    return EvaluationResult(
        passed=passed,
        score=critique.score / 100,
        issues=issues,
        refinement_hints=refinement_hints,
        explanation=critique.justification,
        metadata=metadata,
    )


def _simulate_bias_evaluator(feedback_applied: bool) -> BiasEvaluatorOutput:
    """Deterministic evaluator used when llm_provider=fake."""
    if feedback_applied:
        return BiasEvaluatorOutput(
            score=95,
            justification="Feedback applied; auto-accepting bias analysis.",
            suggested_changes=[],
        )

    return BiasEvaluatorOutput(
        score=85,
        justification=(
            "Simulation mode (fake provider): analysis considered sufficient."
        ),
        suggested_changes=[],
    )


def _extract_forced_score(options: dict[str, Any]) -> int | None:
    """Read the debug hook for forcing evaluator score (testing only)."""
    raw_value = options.get("force_bias_eval_score")
    if raw_value is None:
        return None
    try:
        numeric = float(raw_value)
    except (TypeError, ValueError):
        logger.warning("force_bias_eval_score must be numeric; ignoring %r", raw_value)
        return None

    # Support 0-1 or 0-100 ranges.
    if 0 <= numeric <= 1:
        numeric *= 100

    numeric = max(0, min(100, int(numeric)))
    logger.debug("Forcing bias evaluator score to %s", numeric)
    return numeric


def _invoke_bias_evaluator_llm(
    *,
    workflow_result: dict[str, Any],
    original_text: str | None,
    existing_feedback: list[str],
) -> BiasEvaluatorOutput:
    """Call LangChain LLM with structured output for the critique."""
    prompt_loader = PromptLoader()
    prompt_template = prompt_loader.load("bias_evaluator_v1.txt")
    analysis_section = _serialize_bias_analysis(workflow_result.get("bias_analysis"))
    summary_section = workflow_result.get("summary") or ""
    merged_text = original_text or workflow_result.get("merged_text") or ""
    existing_feedback_text = (
        "\n".join(f"- {item}" for item in existing_feedback)
        if existing_feedback
        else "None"
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                (
                    "You critique fairness analyses and return structured "
                    "JSON as instructed."
                ),
            ),
            (
                "user",
                prompt_template,
            ),
        ],
    ).partial(
        bias_analysis_json=analysis_section,
        analysis_summary=summary_section or "None",
        source_text=merged_text or "Not available",
        existing_feedback=existing_feedback_text,
    )

    parser = PydanticOutputParser(pydantic_object=BiasEvaluatorOutput)
    langchain_model = _build_plain_langchain_model()
    chain = prompt | langchain_model | parser
    logger.debug("Invoking bias evaluator LLM")
    return chain.invoke({})


def _serialize_bias_analysis(analysis: Any) -> str:
    """Convert bias analysis payload to readable JSON for evaluator prompt."""
    if isinstance(analysis, BiasAnalysisOutput):
        return json.dumps(
            analysis.model_dump(),
            indent=2,
            ensure_ascii=False,
            default=str,
        )
    if isinstance(analysis, str):
        # Already serialized (fake provider)
        return analysis
    if analysis is None:
        return "null"
    return json.dumps(analysis, indent=2, default=str, ensure_ascii=False)


def _build_plain_langchain_model() -> BaseLanguageModel:
    """Create a plain LangChain chat model with telemetry + caching."""
    provider = settings.llm_provider
    callback = TelemetryCallback(
        telemetry=telemetry,
        provider=provider,
        model=settings.llm_model_name,
    )

    if settings.llm_cache_enabled:
        settings.llm_cache_path.parent.mkdir(parents=True, exist_ok=True)
        set_llm_cache(SQLiteCache(database_path=str(settings.llm_cache_path)))

    if provider == "openai":
        base_model = ChatOpenAI(
            model=settings.llm_model_name,
            api_key=SecretStr(settings.llm_api_key) if settings.llm_api_key else None,
            base_url=settings.llm_base_url,
            callbacks=[callback],
        )
        return cast(BaseLanguageModel, base_model.with_retry(stop_after_attempt=3))

    if provider == "anthropic":
        if not settings.llm_api_key:
            raise ValueError("Anthropic provider requires API key for evaluator.")

        anthropic_model = ChatAnthropic(  # type: ignore[call-arg]
            model_name=settings.llm_model_name,
            api_key=SecretStr(settings.llm_api_key),
            callbacks=[callback],
        )
        return cast(BaseLanguageModel, anthropic_model.with_retry(stop_after_attempt=3))

    raise ValueError(f"Unsupported LLM provider for evaluator: {provider}")
