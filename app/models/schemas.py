from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EvaluationCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=100)
    input: str = Field(min_length=1, max_length=20_000)
    expected_contains: list[str] = Field(default_factory=list)
    expected_not_contains: list[str] = Field(default_factory=list)
    regex_patterns: list[str] = Field(default_factory=list)
    max_latency_ms: float | None = Field(default=None, gt=0)
    max_cost_usd: float | None = Field(default=None, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    # Used only by the deterministic mock provider. Live providers ignore it.
    mock_response: str | None = Field(default=None, max_length=20_000)


class EvaluationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cases: list[EvaluationCase] = Field(min_length=1, max_length=500)
    provider: Literal["mock", "openai"] = "mock"
    model: str = "gpt-4o-mini"
    prompt_template: str = "Answer the input below carefully and directly.\n\nInput: {input}"
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    baseline_run_id: UUID | None = None
    fail_on_regression: bool = False
    minimum_pass_rate: float = Field(default=0.8, ge=0.0, le=1.0)


class CheckResult(BaseModel):
    name: str
    passed: bool
    detail: str


class CaseResult(BaseModel):
    case_id: str
    passed: bool
    output: str | None = None
    checks: list[CheckResult] = Field(default_factory=list)
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RunEvent(BaseModel):
    timestamp: datetime
    event: str
    message: str
    case_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class BaselineComparison(BaseModel):
    baseline_run_id: UUID
    pass_rate_delta: float
    latency_delta_ms: float
    cost_delta_usd: float
    regressed: bool


class EvaluationRun(BaseModel):
    run_id: UUID
    created_at: datetime
    provider: str
    model: str
    prompt_template: str
    total_cases: int
    passed_cases: int
    failed_cases: int
    pass_rate: float
    avg_latency_ms: float
    p95_latency_ms: float
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    case_results: list[CaseResult]
    events: list[RunEvent] = Field(default_factory=list)
    baseline_comparison: BaselineComparison | None = None
    quality_gate_passed: bool | None = None


class EvaluationSummary(BaseModel):
    run_id: UUID
    created_at: datetime
    provider: str
    model: str
    total_cases: int
    passed_cases: int
    failed_cases: int
    pass_rate: float
    avg_latency_ms: float
    p95_latency_ms: float
    total_tokens: int
    estimated_cost_usd: float
