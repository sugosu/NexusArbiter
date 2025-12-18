from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from core.strategy.strategy_loader import StrategyDefinition


@dataclass(frozen=True)
class StrategyContext:
    run_name: str
    attempt: int
    reason: str
    diagnostics: Dict[str, Any]
    previous_output: Dict[str, Any] | None


def apply_strategy_to_messages(
    base_messages: List[Dict[str, Any]],
    strategy: StrategyDefinition,
    ctx: StrategyContext,
) -> List[Dict[str, Any]]:
    """
    Applies a strategy definition to the model messages deterministically.
    """
    if strategy.mode != "append_messages":
        raise ValueError(f"Unsupported strategy mode '{strategy.mode}' for method '{strategy.method}'")

    system_payload = "\n".join(strategy.system_instructions).strip()

    extra = {
        "role": "system",
        "content": (
            f"{system_payload}\n\n"
            f"Reason: {ctx.reason}\n"
            f"Diagnostics: {ctx.diagnostics}\n"
        ).strip(),
    }

    return [*base_messages, extra]
