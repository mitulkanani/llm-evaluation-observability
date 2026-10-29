# LLM Evaluation & Observability

A practical evaluation harness for LLM applications. Run a repeatable golden dataset against a provider, evaluate explicit assertions, track latency/tokens/estimated cost, compare runs to a baseline, and inspect outputs in a small dashboard.

> **Scope:** the mock provider is deterministic for local development and CI. An optional OpenAI adapter is included. The default checks are transparent assertion-based checks—not a semantic judge or a guarantee of factual correctness. Token/cost estimates are only as accurate as provider usage data and the editable pricing configuration.

## Features

- Versionable JSONL golden datasets.
- Assertion checks: required phrases, forbidden phrases, regex patterns, latency budget, cost budget, and non-empty output.
- Provider abstraction with a no-key mock provider and optional OpenAI Chat Completions adapter.
- Per-case traces, errors, outputs, prompt/completion token counts, estimated cost, average/p95 latency.
- SQLite-backed run history and CSV export.
- Baseline comparisons for pass-rate, latency, and cost deltas.
- CLI and REST API plus a minimal browser dashboard.
- Tests and GitHub Actions CI.

## Architecture

```text
Golden JSONL Dataset
        |
        v
Prompt Renderer ---> Provider Adapter (mock or OpenAI)
        |                        |
        +------------------------+
                     |
                     v
           Assertion Scorers
                     |
                     v
     Metrics + per-case trace events
                     |
          +----------+----------+
          |                     |
          v                     v
    SQLite run history     REST API / CLI
                                |
                                v
                           Dashboard / CSV
```

## Quick start

Python 3.11+ is recommended.

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
pytest
uvicorn app.main:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) for the dashboard and [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) for the API explorer.

## Run an evaluation from the CLI

```bash
python -m app.cli --provider mock --dataset examples/golden_dataset.jsonl
```

A nonzero exit code is returned if one or more cases fail. Runs are saved to `./data/evaluations.sqlite3` by default.

## Run with Docker

```bash
cp .env.example .env
docker compose up --build
```

The app listens on port `8000`; run history is persisted in the `eval-data` Docker volume.

## Run with OpenAI

Install the optional dependency and set `OPENAI_API_KEY` in your environment or `.env`:

```bash
python -m pip install -e ".[dev,openai]"
export OPENAI_API_KEY="your-key"
```

Then choose `provider: "openai"` in the API request or set `--provider openai` on the CLI. The sample JSONL's `mock_response` fields are ignored by the live provider. Real model outputs are not expected to pass all demo assertions consistently; use your own golden dataset and tune prompts deliberately.

## Dataset format

One JSON object per line:

```json
{"id":"refund-policy","input":"Can I get a refund?","expected_contains":["refund"],"expected_not_contains":["guaranteed"],"regex_patterns":["(?i)policy"],"max_latency_ms":800,"max_cost_usd":0.001,"metadata":{"category":"policy"},"mock_response":"A refund request follows the policy."}
```

Fields:
- `id`: unique case ID within one run.
- `input`: user/query input inserted into `{input}` in the prompt template.
- `expected_contains`: case-insensitive substrings that must appear.
- `expected_not_contains`: substrings that must not appear.
- `regex_patterns`: regex assertions; malformed regexes are recorded as failed checks.
- `max_latency_ms`, `max_cost_usd`: optional budgets.
- `metadata`: arbitrary tags for reporting.
- `mock_response`: deterministic fixture used only by the mock provider.

## REST API

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/evaluations` | Run cases, store results, optionally compare with a baseline run |
| `GET` | `/sample-dataset` | Load the included sample dataset for the dashboard |
| `GET` | `/evaluations?limit=20` | List recent run summaries |
| `GET` | `/evaluations/{run_id}` | Get full run details |
| `GET` | `/evaluations/{run_id}/export.csv` | Download per-case results as CSV |

Example request:

```bash
curl -X POST http://127.0.0.1:8000/evaluations \
  -H 'Content-Type: application/json' \
  -d @examples/api_request.json
```

You can optionally provide `baseline_run_id` to compare the new result to a stored run. Regression rules are intentionally simple and transparent: any pass-rate reduction, or more than a 10% relative increase in latency/cost when a baseline value is nonzero, marks a regression.

## Cost and token notes

- When provider usage counts are present, those are used. Missing counts use a rough characters/4 token approximation.
- Prices in `.env.example` and `app/core/pricing.py` are **editable example values**, not a statement of current provider pricing.
- Unknown models currently report `$0` estimated cost instead of guessing a rate; add a price entry for that model before using cost budgets.
- Evaluation harness latency includes provider call + local work around it, but does not include queue wait or external client latency.

## Reliability and security limitations

- The OpenAI adapter uses the Chat Completions endpoint; adapt the provider interface for other vendors/models.
- Assertion-based checks are useful smoke tests but do not measure semantics, truthfulness, harmlessness, or groundedness reliably. Add domain-specific graders, human review, and calibration before depending on automated scores.
- Treat evaluation inputs and outputs as potentially sensitive. The SQLite store keeps full outputs and prompt templates; set the DB path, access controls, retention, and redaction policy for your environment.
- The demo API has no authentication or rate limiting. Do not expose it publicly as-is.
- SQLite is suitable for a local/single-instance starter. Use managed storage, request isolation, and observability controls for multi-instance production deployment.
- Model responses can vary, and a successful assertion run is not proof of correctness.

## Project layout

```text
app/
  api/routes.py           # REST API
  core/config.py          # settings
  core/pricing.py         # editable cost estimates
  models/schemas.py       # evaluation/run schemas
  services/providers.py   # mock/OpenAI providers
  services/scorers.py     # explicit checks
  services/evaluator.py   # evaluation execution and metrics
  services/comparison.py  # baseline comparisons
  services/store.py       # SQLite persistence
  cli.py                  # command-line runner
  main.py                 # FastAPI + dashboard
examples/golden_dataset.jsonl
web/index.html
tests/
```

## Roadmap

- [ ] Add semantic/LLM-as-judge graders with calibration and human audit samples.
- [ ] Add prompt/model version registry and run lineage.
- [ ] Add OpenTelemetry spans and exportable metrics.
- [ ] Add token-aware concurrency limits and retry/backoff.
- [ ] Add role-based access, tenant isolation, redaction, and retention policies.
- [ ] Add CI threshold configuration by dataset and category.

## License

MIT. See [LICENSE](LICENSE).
