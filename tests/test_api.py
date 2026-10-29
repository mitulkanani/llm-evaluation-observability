from fastapi.testclient import TestClient

from app.api.routes import configure_store
from app.main import app
from app.services.store import EvaluationStore


def make_client(tmp_path):
    configure_store(EvaluationStore(str(tmp_path / "api.db")))
    return TestClient(app)


def test_health_endpoint(tmp_path):
    client = make_client(tmp_path)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_get_list_and_csv_export(tmp_path):
    client = make_client(tmp_path)
    response = client.post("/evaluations", json={
        "provider": "mock", "model": "gpt-4o-mini", "prompt_template": "Input: {input}",
        "cases": [{"id": "hello", "input": "greet", "expected_contains": ["hello"], "mock_response": "Hello!"}],
    })
    assert response.status_code == 201
    run_id = response.json()["run_id"]
    assert response.json()["pass_rate"] == 1.0
    assert response.json()["quality_gate_passed"] is True
    assert client.get(f"/evaluations/{run_id}").status_code == 200
    assert len(client.get("/evaluations").json()) == 1
    csv_response = client.get(f"/evaluations/{run_id}/export.csv")
    assert csv_response.status_code == 200
    assert "case_id,passed" in csv_response.text


def test_not_found_evaluation_returns_404(tmp_path):
    client = make_client(tmp_path)
    response = client.get("/evaluations/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_invalid_case_request_returns_422(tmp_path):
    client = make_client(tmp_path)
    response = client.post("/evaluations", json={"cases": []})
    assert response.status_code == 422


def test_sample_dataset_is_served_to_dashboard(tmp_path):
    client = make_client(tmp_path)
    response = client.get("/sample-dataset")
    assert response.status_code == 200
    assert len(response.json()) >= 4


def test_quality_gate_marks_low_pass_rate(tmp_path):
    client = make_client(tmp_path)
    response = client.post("/evaluations", json={
        "provider": "mock", "model": "gpt-4o-mini", "prompt_template": "{input}",
        "minimum_pass_rate": 1.0,
        "cases": [{"id": "fails", "input": "question", "expected_contains": ["missing"], "mock_response": "different answer"}],
    })
    assert response.status_code == 201
    assert response.json()["quality_gate_passed"] is False


def test_baseline_comparison_can_fail_quality_gate(tmp_path):
    client = make_client(tmp_path)
    baseline = client.post("/evaluations", json={
        "provider": "mock", "model": "gpt-4o-mini", "prompt_template": "{input}",
        "cases": [{"id": "case", "input": "say yes", "expected_contains": ["yes"], "mock_response": "yes"}],
    })
    assert baseline.status_code == 201
    baseline_id = baseline.json()["run_id"]
    current = client.post("/evaluations", json={
        "provider": "mock", "model": "gpt-4o-mini", "prompt_template": "{input}",
        "baseline_run_id": baseline_id, "fail_on_regression": True,
        "cases": [{"id": "case", "input": "say yes", "expected_contains": ["yes"], "mock_response": "no"}],
    })
    assert current.status_code == 201
    body = current.json()
    assert body["baseline_comparison"]["regressed"] is True
    assert body["quality_gate_passed"] is False


def test_root_serves_dashboard(tmp_path):
    client = make_client(tmp_path)
    response = client.get("/")
    assert response.status_code == 200
    assert "LLM Evaluation" in response.text
