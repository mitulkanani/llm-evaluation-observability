from uuid import UUID
from app.models.schemas import EvaluationCase
from app.services.comparison import compare_runs
from app.services.evaluator import evaluate_cases
from app.services.providers import MockProvider
from app.services.store import EvaluationStore


def make_run(response: str, expected: str = "yes"):
    return evaluate_cases(
        [EvaluationCase(id="case", input="say yes", expected_contains=[expected], mock_response=response)],
        provider=MockProvider(), model="test-model", prompt_template="{input}",
    )


def test_sqlite_store_saves_gets_and_lists_runs(tmp_path) -> None:
    store = EvaluationStore(str(tmp_path / "runs.db"))
    run = make_run("yes")
    store.save(run)
    loaded = store.get(run.run_id)
    summaries = store.list_summaries()
    assert loaded is not None and loaded.run_id == run.run_id
    assert len(summaries) == 1
    assert summaries[0].run_id == run.run_id


def test_comparison_detects_quality_regression() -> None:
    baseline = make_run("yes")
    current = make_run("no")
    result = compare_runs(current, baseline)
    assert result.baseline_run_id == baseline.run_id
    assert result.pass_rate_delta < 0
    assert result.regressed


def test_unknown_run_is_none(tmp_path) -> None:
    store = EvaluationStore(str(tmp_path / "runs.db"))
    assert store.get(UUID("00000000-0000-0000-0000-000000000000")) is None
