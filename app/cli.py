import argparse
import json
from pathlib import Path

from app.core.config import settings
from app.models.schemas import EvaluationCase
from app.services.evaluator import evaluate_cases
from app.services.providers import ProviderError, build_provider
from app.services.store import EvaluationStore


def load_jsonl(path: str) -> list[EvaluationCase]:
    cases: list[EvaluationCase] = []
    with Path(path).open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            try:
                cases.append(EvaluationCase.model_validate(json.loads(line)))
            except Exception as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_number}: {exc}") from exc
    if not cases:
        raise ValueError("Dataset contains no evaluation cases.")
    return cases


def main() -> None:
    parser = argparse.ArgumentParser(description="Run an LLM evaluation dataset.")
    parser.add_argument("--dataset", default="examples/golden_dataset.jsonl")
    parser.add_argument("--provider", choices=["mock", "openai"], default="mock")
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--prompt-template", default="Answer the input below carefully and directly.\n\nInput: {input}")
    args = parser.parse_args()
    try:
        cases = load_jsonl(args.dataset)
        run = evaluate_cases(cases, provider=build_provider(args.provider), model=args.model, prompt_template=args.prompt_template)
        store = EvaluationStore(settings.db_path)
        store.save(run)
        print(run.model_dump_json(indent=2))
        if run.failed_cases:
            raise SystemExit(1)
    except (ValueError, ProviderError) as exc:
        parser.exit(status=2, message=f"Error: {exc}\n")


if __name__ == "__main__":
    main()
