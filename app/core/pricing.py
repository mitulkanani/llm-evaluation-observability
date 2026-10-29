"""Editable cost estimates. Values are example USD rates per 1M tokens.

They are not a guarantee of current provider pricing. Update these values to
match the prices in use for your account, region, and model variant.
"""
import os

from dotenv import load_dotenv

load_dotenv()


def _env_float(name: str, default: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
        return max(value, 0.0)
    except (TypeError, ValueError):
        return default


PRICING_USD_PER_1M: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (
        _env_float("PRICE_GPT_4O_MINI_INPUT_PER_1M", 0.15),
        _env_float("PRICE_GPT_4O_MINI_OUTPUT_PER_1M", 0.60),
    ),
    "gpt-4o": (
        _env_float("PRICE_GPT_4O_INPUT_PER_1M", 2.50),
        _env_float("PRICE_GPT_4O_OUTPUT_PER_1M", 10.00),
    ),
}


def estimate_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    rates = PRICING_USD_PER_1M.get(model)
    if rates is None:
        return 0.0
    input_rate, output_rate = rates
    return (max(prompt_tokens, 0) * input_rate + max(completion_tokens, 0) * output_rate) / 1_000_000
