import time
from datetime import UTC, datetime
from statistics import mean
from uuid import uuid4

from app.core.pricing import estimate_cost_usd
from app.models.schemas import CaseResult, EvaluationCase, EvaluationRun, RunEvent
from app.services.providers import LLMProvider, ProviderError, approximate_tokens
from app.services.scorers import score_output


def _percentile_95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1)))))
    return float(ordered[index])


def render_prompt(template: str, case: EvaluationCase) -> str:
    try:
        return template.format(input=case.input, case_id=case.id, metadata=case.metadata)
    except (KeyError, ValueError) as exc:
        raise ValueError(f"Invalid prompt template: {exc}") from exc


def evaluate_cases(
    cases: list[EvaluationCase],
    *,
    provider: LLMProvider,
    model: str,
    prompt_template: str,
    temperature: float = 0.0,
) -> EvaluationRun:
    if not cases:
        raise ValueError("At least one evaluation case is required.")
    ids = [case.id for case in cases]
    if len(set(ids)) != len(ids):
        raise ValueError("Case IDs must be unique within an evaluation run.")

    created_at = datetime.now(UTC)
    run_id = uuid4()
    events = [RunEvent(timestamp=created_at, event="run_started", message=f"Started evaluation with {len(cases)} case(s).")]
    case_results: list[CaseResult] = []

    for case in cases:
        events.append(RunEvent(timestamp=datetime.now(UTC), event="case_started", message="Evaluation case started.", case_id=case.id))
        started = time.perf_counter()
        try:
            prompt = render_prompt(prompt_template, case)
            generated = provider.generate(
                prompt,
                model,
                temperature=temperature,
                mock_response=case.mock_response,
            )
            latency_ms = (time.perf_counter() - started) * 1000
            prompt_tokens = generated.prompt_tokens or approximate_tokens(prompt)
            completion_tokens = generated.completion_tokens or approximate_tokens(generated.output)
            cost = estimate_cost_usd(model, prompt_tokens, completion_tokens)
            checks = score_output(case, generated.output, latency_ms, cost)
            passed = all(check.passed for check in checks)
            case_results.append(CaseResult(
                case_id=case.id,
                passed=passed,
                output=generated.output,
                checks=checks,
                latency_ms=round(latency_ms, 3),
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                estimated_cost_usd=cost,
                metadata=case.metadata,
            ))
            events.append(RunEvent(timestamp=datetime.now(UTC), event="case_completed", message="Evaluation case completed.", case_id=case.id, details={"passed": passed, "latency_ms": round(latency_ms, 3)}))
        except (ValueError, ProviderError) as exc:
            latency_ms = (time.perf_counter() - started) * 1000
            detail = f"{type(exc).__name__}: {exc}"
            case_results.append(CaseResult(
                case_id=case.id,
                passed=False,
                checks=[],
                latency_ms=round(latency_ms, 3),
                error=detail,
                metadata=case.metadata,
            ))
            events.append(RunEvent(timestamp=datetime.now(UTC), event="case_failed", message=detail, case_id=case.id))
        except Exception as exc:  # Keep one failed case from discarding the full run.
            latency_ms = (time.perf_counter() - started) * 1000
            detail = f"Unexpected {type(exc).__name__}: {exc}"
            case_results.append(CaseResult(
                case_id=case.id, passed=False, latency_ms=round(latency_ms, 3),
                error=detail, metadata=case.metadata,
            ))
            events.append(RunEvent(timestamp=datetime.now(UTC), event="case_failed", message=detail, case_id=case.id))

    latencies = [result.latency_ms for result in case_results]
    passed_cases = sum(result.passed for result in case_results)
    prompt_tokens = sum(result.prompt_tokens for result in case_results)
    completion_tokens = sum(result.completion_tokens for result in case_results)
    cost = sum(result.estimated_cost_usd for result in case_results)
    events.append(RunEvent(timestamp=datetime.now(UTC), event="run_completed", message="Evaluation run completed.", details={"passed_cases": passed_cases, "failed_cases": len(case_results) - passed_cases}))
    return EvaluationRun(
        run_id=run_id,
        created_at=created_at,
        provider=provider.name,
        model=model,
        prompt_template=prompt_template,
        total_cases=len(case_results),
        passed_cases=passed_cases,
        failed_cases=len(case_results) - passed_cases,
        pass_rate=passed_cases / len(case_results),
        avg_latency_ms=mean(latencies) if latencies else 0.0,
        p95_latency_ms=_percentile_95(latencies),
        total_prompt_tokens=prompt_tokens,
        total_completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        estimated_cost_usd=cost,
        case_results=case_results,
        events=events,
    )
