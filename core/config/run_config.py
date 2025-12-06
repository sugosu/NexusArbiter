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

    # These fields apply ONLY to validator / rerun controller runs.
    # Code-generation runs must leave them as None.
    rerun_index: Optional[int] = None          # which rerun strategy block to use
    target_run: Optional[str] = None           # which codegen run to rerun
    rerun_strategy: Optional[str] = None       # path to rerun strategy .json file

    # Reserved for future or profile metadata:
    retry: Optional[int] = None
    profile_name: Optional[str] = None

    def is_validator(self) -> bool:
        """
        A run is considered a validator/rerun controller if all rerun-related
        fields are present.
        """
        return (
            self.rerun_index is not None
            and self.target_run is not None
            and self.rerun_strategy is not None
        )


# ---------------------------------------------------------------------------
# Full Run Configuration (the root of runs.json)
# ---------------------------------------------------------------------------

@dataclass
class RunConfig:
    """
    Represents the parsed content of the run configuration JSON.

    NOTE: Provider is intentionally NOT stored here anymore.
          Provider is now taken from profile files only (or rerun strategy overrides).
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
            # New preferred keys
            rerun_index = r.get("rerun_index")
            rerun_strategy = r.get("rerun_strategy")

            # Backwards compatibility: accept old names if present
            if rerun_index is None and "strategy_index" in r:
                rerun_index = r.get("strategy_index")

            if rerun_strategy is None and "strategy_file" in r:
                rerun_strategy = r.get("strategy_file")

            run_item = RunItem(
                name=r["name"],
                profile_file=r["profile_file"],
                task_description=r.get("task_description"),
                context_file=r.get("context_file", []),
                target_file=r.get("target_file"),
                allowed_actions=r.get("allowed_actions", []),

                # Validator-only fields (new names)
                rerun_index=rerun_index,
                target_run=r.get("target_run"),
                rerun_strategy=rerun_strategy,

                # Misc metadata:
                retry=r.get("retry"),
                profile_name=r.get("profile_name"),
            )
            runs.append(run_item)

        return RunConfig(
            runs=runs,
            retry_policy=retry_policy,
        )
