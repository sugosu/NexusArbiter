from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping


@dataclass(frozen=True)
class StrategyDefinition:
    method: str
    mode: str
    system_instructions: List[str]


def load_strategy_registry(strategies_dir: Path) -> Mapping[str, StrategyDefinition]:
    """
    Loads all strategies/*/strategy.json and returns a registry:
      method -> StrategyDefinition

    Deterministic rules:
    - Each strategy.json MUST contain "method".
    - Methods MUST be unique.
    - Directory order must not matter (we sort paths).
    """
    strategies_dir = Path(strategies_dir)
    if not strategies_dir.exists():
        return {}

    registry: Dict[str, StrategyDefinition] = {}

    for p in sorted(strategies_dir.glob("*/strategy.json")):
        data = json.loads(p.read_text(encoding="utf-8"))

        method = data.get("method")
        mode = data.get("mode", "append_messages")
        system_instructions = data.get("system_instructions", [])

        if not isinstance(method, str) or not method.strip():
            raise ValueError(f"Invalid strategy.json (missing/invalid method): {p}")
        if method in registry:
            raise ValueError(f"Duplicate strategy method '{method}' found in: {p}")
        if not isinstance(mode, str) or not mode.strip():
            raise ValueError(f"Invalid strategy.json (missing/invalid mode): {p}")
        if not isinstance(system_instructions, list) or any(not isinstance(x, str) for x in system_instructions):
            raise ValueError(f"Invalid strategy.json (system_instructions must be list[str]): {p}")

        registry[method] = StrategyDefinition(
            method=method,
            mode=mode,
            system_instructions=system_instructions,
        )

    return registry
