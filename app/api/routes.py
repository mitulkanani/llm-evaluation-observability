import csv
import io
import json
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.models.schemas import EvaluationCase, EvaluationRequest, EvaluationRun, EvaluationSummary
from app.services.comparison import compare_runs
from app.services.evaluator import evaluate_cases
from app.services.providers import ProviderError, build_provider
from app.services.store import EvaluationStore

router = APIRouter()
store: EvaluationStore | None = None


def configure_store(instance: EvaluationStore) -> None:
    global store
    store = instance


def _store() -> EvaluationStore:
    if store is None:
        raise RuntimeError("Evaluation store has not been configured.")
    return store


@router.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/evaluations", response_model=EvaluationRun, status_code=status.HTTP_201_CREATED, tags=["evaluations"])
def create_evaluation(payload: EvaluationRequest) -> EvaluationRun:
    try:
        provider = build_provider(payload.provider)
        run = evaluate_cases(
            payload.cases, provider=provider, model=payload.model,
            prompt_template=payload.prompt_template, temperature=payload.temperature,
        )
    except ProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if payload.baseline_run_id:
        baseline = _store().get(payload.baseline_run_id)
        if baseline is None:
            raise HTTPException(status_code=404, detail="Baseline evaluation run not found.")
        run.baseline_comparison = compare_runs(run, baseline)
    run.quality_gate_passed = run.pass_rate >= payload.minimum_pass_rate
    if payload.fail_on_regression and run.baseline_comparison and run.baseline_comparison.regressed:
        run.quality_gate_passed = False
    _store().save(run)
    return run


@router.get("/sample-dataset", response_model=list[EvaluationCase], tags=["examples"])
def sample_dataset() -> list[EvaluationCase]:
    """Return the included deterministic dataset for the demo dashboard."""
    path = Path(__file__).resolve().parents[2] / "examples" / "golden_dataset.jsonl"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Sample dataset is not installed.")
    cases: list[EvaluationCase] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.lstrip().startswith("#"):
                cases.append(EvaluationCase.model_validate(json.loads(line)))
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=500, detail="Sample dataset could not be loaded.") from exc
    return cases


@router.get("/evaluations", response_model=list[EvaluationSummary], tags=["evaluations"])
def list_evaluations(limit: int = Query(default=20, ge=1, le=100)) -> list[EvaluationSummary]:
    return _store().list_summaries(limit)


@router.get("/evaluations/{run_id}", response_model=EvaluationRun, tags=["evaluations"])
def get_evaluation(run_id: UUID) -> EvaluationRun:
    run = _store().get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Evaluation run not found.")
    return run


@router.get("/evaluations/{run_id}/export.csv", tags=["evaluations"])
def export_evaluation_csv(run_id: UUID) -> Response:
    run = _store().get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Evaluation run not found.")
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        "case_id", "passed", "latency_ms", "prompt_tokens", "completion_tokens",
        "total_tokens", "estimated_cost_usd", "error", "output",
    ])
    writer.writeheader()
    for item in run.case_results:
        writer.writerow({
            "case_id": item.case_id, "passed": item.passed, "latency_ms": item.latency_ms,
            "prompt_tokens": item.prompt_tokens, "completion_tokens": item.completion_tokens,
            "total_tokens": item.total_tokens, "estimated_cost_usd": item.estimated_cost_usd,
            "error": item.error or "", "output": item.output or "",
        })
    return Response(content=output.getvalue(), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="evaluation-{run_id}.csv"'})
