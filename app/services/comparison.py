from app.models.schemas import BaselineComparison, EvaluationRun


def compare_runs(current: EvaluationRun, baseline: EvaluationRun) -> BaselineComparison:
    pass_delta = current.pass_rate - baseline.pass_rate
    latency_delta = current.avg_latency_ms - baseline.avg_latency_ms
    cost_delta = current.estimated_cost_usd - baseline.estimated_cost_usd
    # A run is regressed if quality drops, or cost/latency rises by >10% when
    # the baseline metric is nonzero. This rule is intentionally transparent.
    quality_regression = pass_delta < 0
    latency_regression = baseline.avg_latency_ms > 0 and latency_delta > baseline.avg_latency_ms * 0.10
    cost_regression = baseline.estimated_cost_usd > 0 and cost_delta > baseline.estimated_cost_usd * 0.10
    return BaselineComparison(
        baseline_run_id=baseline.run_id,
        pass_rate_delta=pass_delta,
        latency_delta_ms=latency_delta,
        cost_delta_usd=cost_delta,
        regressed=quality_regression or latency_regression or cost_regression,
    )
