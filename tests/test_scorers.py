from app.models.schemas import EvaluationCase
from app.services.scorers import score_output


def test_required_and_forbidden_phrase_checks_are_case_insensitive() -> None:
    case = EvaluationCase(id="a", input="x", expected_contains=["Refund"], expected_not_contains=["password"])
    results = score_output(case, "Refunds are available.", latency_ms=10, cost_usd=0.0)
    assert all(result.passed for result in results)


def test_missing_expected_phrase_fails() -> None:
    case = EvaluationCase(id="a", input="x", expected_contains=["approved"])
    results = score_output(case, "The request is pending.", latency_ms=10, cost_usd=0)
    assert not all(result.passed for result in results)
    assert any(item.name == "expected_contains_1" and not item.passed for item in results)


def test_latency_and_cost_budgets_are_checked() -> None:
    case = EvaluationCase(id="a", input="x", max_latency_ms=3, max_cost_usd=0.001)
    results = score_output(case, "ok", latency_ms=5, cost_usd=0.002)
    assert not next(item for item in results if item.name == "latency_budget").passed
    assert not next(item for item in results if item.name == "cost_budget").passed


def test_invalid_regex_is_a_failed_check_not_an_exception() -> None:
    case = EvaluationCase(id="a", input="x", regex_patterns=["["])
    results = score_output(case, "hello", latency_ms=1, cost_usd=0)
    assert not next(item for item in results if item.name == "regex_1").passed
