import re
from app.models.schemas import CheckResult, EvaluationCase


def score_output(case: EvaluationCase, output: str, latency_ms: float, cost_usd: float) -> list[CheckResult]:
    """Evaluate explicit, explainable assertions; no LLM judge is implied."""
    checks: list[CheckResult] = []
    normalized = output.casefold()
    checks.append(CheckResult(
        name="non_empty_output",
        passed=bool(output.strip()),
        detail="Output contains text." if output.strip() else "Output is empty.",
    ))
    for index, needle in enumerate(case.expected_contains, start=1):
        ok = needle.casefold() in normalized
        checks.append(CheckResult(
            name=f"expected_contains_{index}",
            passed=ok,
            detail=(f"Found required phrase: {needle!r}." if ok else f"Missing required phrase: {needle!r}."),
        ))
    for index, needle in enumerate(case.expected_not_contains, start=1):
        ok = needle.casefold() not in normalized
        checks.append(CheckResult(
            name=f"expected_not_contains_{index}",
            passed=ok,
            detail=(f"Forbidden phrase absent: {needle!r}." if ok else f"Forbidden phrase present: {needle!r}."),
        ))
    for index, pattern in enumerate(case.regex_patterns, start=1):
        try:
            ok = re.search(pattern, output, flags=re.IGNORECASE) is not None
            detail = f"Regex matched: {pattern!r}." if ok else f"Regex did not match: {pattern!r}."
        except re.error as exc:
            ok = False
            detail = f"Invalid regex {pattern!r}: {exc}."
        checks.append(CheckResult(name=f"regex_{index}", passed=ok, detail=detail))
    if case.max_latency_ms is not None:
        ok = latency_ms <= case.max_latency_ms
        checks.append(CheckResult(
            name="latency_budget",
            passed=ok,
            detail=f"Latency {latency_ms:.2f} ms {'within' if ok else 'exceeds'} {case.max_latency_ms:.2f} ms budget.",
        ))
    if case.max_cost_usd is not None:
        ok = cost_usd <= case.max_cost_usd
        checks.append(CheckResult(
            name="cost_budget",
            passed=ok,
            detail=f"Estimated cost ${cost_usd:.8f} {'within' if ok else 'exceeds'} ${case.max_cost_usd:.8f} budget.",
        ))
    return checks
