import pytest
from app.models.schemas import EvaluationCase
from app.services.evaluator import evaluate_cases, render_prompt
from app.services.providers import MockProvider


def test_run_records_pass_rate_tokens_cost_and_events() -> None:
    cases = [
        EvaluationCase(id="pass", input="greet", expected_contains=["hello"], mock_response="Hello there."),
        EvaluationCase(id="fail", input="bye", expected_contains=["goodbye"], mock_response="See you."),
    ]
    run = evaluate_cases(cases, provider=MockProvider(), model="gpt-4o-mini", prompt_template="Input: {input}")
    assert run.total_cases == 2
    assert run.passed_cases == 1
    assert run.failed_cases == 1
    assert run.pass_rate == 0.5
    assert run.total_tokens > 0
    assert run.estimated_cost_usd >= 0
    assert any(event.event == "run_completed" for event in run.events)


def test_duplicate_case_ids_are_rejected() -> None:
    cases = [EvaluationCase(id="same", input="x"), EvaluationCase(id="same", input="y")]
    with pytest.raises(ValueError, match="unique"):
        evaluate_cases(cases, provider=MockProvider(), model="local", prompt_template="{input}")


def test_prompt_template_rejects_unknown_placeholders() -> None:
    case = EvaluationCase(id="a", input="hello")
    with pytest.raises(ValueError, match="Invalid prompt template"):
        render_prompt("{unknown}", case)


def test_case_level_latency_budget_can_fail_an_otherwise_good_answer() -> None:
    case = EvaluationCase(id="slow", input="x", expected_contains=["ok"], max_latency_ms=0.0001, mock_response="ok")
    run = evaluate_cases([case], provider=MockProvider(), model="gpt-4o-mini", prompt_template="{input}")
    assert not run.case_results[0].passed
    assert not next(check for check in run.case_results[0].checks if check.name == "latency_budget").passed
