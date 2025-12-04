# core/config/run_config.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Any
import json


# ---------------------------------------------------------------------------
# Core Run Item representation
# ---------------------------------------------------------------------------

@dataclass
class RunItem:
    """
    Represents a single entry in runs.json.
    """

    name: str
    profile_file: str
    task_description: Optional[str]
    context_file: List[str]
    target_file: Optional[str]
    allowed_actions: List[str]

    # These fields apply ONLY to validator runs.
    # Code-generation runs must leave them as None.
    strategy_index: Optional[int] = None        # which strategy block to use
    target_run: Optional[str] = None            # which codegen run to retry
    strategy_file: Optional[str] = None         # path to strategy .json file

    # Reserved for future or profile metadata:
    retry: Optional[int] = None
    profile_name: Optional[str] = None

    def is_validator(self) -> bool:
        return (
            self.strategy_index is not None
            and self.target_run is not None
            and self.strategy_file is not None
        )


# ---------------------------------------------------------------------------
# Full Run Configuration (the root of runs.json)
# ---------------------------------------------------------------------------

@dataclass
class RunConfig:
    """
    Represents the parsed content of the run configuration JSON.

    NOTE: Provider is intentionally NOT stored here anymore.
          Provider is now taken from profile files only (or strategy overrides).
    """

    runs: List[RunItem]
    retry_policy: Optional[Dict[str, Any]] = None

    @staticmethod
    def from_file(path: Path | str) -> "RunConfig":
        """
        Load and parse runs.json.
        """
        if isinstance(path, str):
            path = Path(path)

        with path.open("r", encoding="utf-8") as f:
            raw = json.load(f)

        # Top-level `provider` is ignored now (backwards-compatible).
        retry_policy = raw.get("retry_policy")

        runs_section = raw.get("runs", [])
        runs: List[RunItem] = []

        for r in runs_section:
            run_item = RunItem(
                name=r["name"],
                profile_file=r["profile_file"],
                task_description=r.get("task_description"),
                context_file=r.get("context_file", []),
                target_file=r.get("target_file"),
                allowed_actions=r.get("allowed_actions", []),

                # Validator-only fields:
                strategy_index=r.get("strategy_index"),
                target_run=r.get("target_run"),
                strategy_file=r.get("strategy_file"),

                # Misc metadata:
                retry=r.get("retry"),
                profile_name=r.get("profile_name"),
            )
            runs.append(run_item)

        return RunConfig(
            runs=runs,
            retry_policy=retry_policy,
        )
    