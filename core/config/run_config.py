# core/config/run_config.py
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


# ------------------------------------------------------
# New dataclass: LogIOSettings
# ------------------------------------------------------
@dataclass
class LogIOSettings:
    enabled: bool = False
    log_dir: str = "logs/io"
    request_file_pattern: str = "{run_name}__{attempt}__request.json"
    response_file_pattern: str = "{run_name}__{attempt}__response.json"

    @staticmethod
    def from_dict(data: Optional[Dict[str, Any]]) -> "LogIOSettings":
        if not data:
            return LogIOSettings()

        return LogIOSettings(
            enabled=bool(data.get("enabled", False)),
            log_dir=data.get("log_dir", "logs/io"),
            request_file_pattern=data.get(
                "request_file_pattern",
                "{run_name}__{attempt}__request.json",
            ),
            response_file_pattern=data.get(
                "response_file_pattern",
                "{run_name}__{attempt}__response.json",
            ),
        )


# ------------------------------------------------------
# RunItem (modified to include log_io override)
# ------------------------------------------------------
@dataclass
class RunItem:
    name: str
    profile_file: str
    task_description: Optional[str]
    context_file: List[str]
    target_file: Optional[str]
    allowed_actions: List[str]

    # Rerun-related fields
    rerun_index: Optional[int] = None
    target_run: Optional[str] = None
    rerun_strategy: Optional[str] = None

    # Legacy backward-compatibility
    strategy_index: Optional[int] = None
    strategy_file: Optional[str] = None

    # Optional per-run I/O logging overrides
    log_io_override: Optional[Dict[str, Any]] = None

    # Provider override (set during rerun)
    provider_override: Optional[str] = None

    retry: Optional[int] = None
    profile_name: Optional[str] = None

    def is_validator(self) -> bool:
        return (
            self.rerun_index is not None
            and self.target_run is not None
            and self.rerun_strategy is not None
        )


# ------------------------------------------------------
# RunConfig
# ------------------------------------------------------
@dataclass
class RunConfig:
    runs: List[RunItem] = field(default_factory=list)
    retry_policy: Optional[Dict[str, Any]] = None

    # NEW: global log-io settings
    log_io_settings: LogIOSettings = field(default_factory=LogIOSettings)

    @staticmethod
    def from_file(path: str | Path) -> "RunConfig":
        path = Path(path)
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        # Load top-level log_io block
        log_io_settings = LogIOSettings.from_dict(data.get("log_io"))

        retry_policy = data.get("retry_policy")

        runs_data = data.get("runs", [])
        runs: List[RunItem] = []

        for run_obj in runs_data:
            # backward compatibility for strategy names
            rerun_index = run_obj.get("rerun_index", run_obj.get("strategy_index"))
            rerun_strategy = run_obj.get("rerun_strategy", run_obj.get("strategy_file"))

            item = RunItem(
                name=run_obj.get("name"),
                profile_file=run_obj["profile_file"],
                task_description=run_obj.get("task_description"),
                context_file=run_obj.get("context_file", []),
                target_file=run_obj.get("target_file"),
                allowed_actions=run_obj.get("allowed_actions", []),

                rerun_index=rerun_index,
                target_run=run_obj.get("target_run"),
                rerun_strategy=rerun_strategy,

                strategy_index=run_obj.get("strategy_index"),
                strategy_file=run_obj.get("strategy_file"),

                log_io_override=run_obj.get("log_io"),
                retry=run_obj.get("retry"),
                profile_name=run_obj.get("profile_name"),
            )

            runs.append(item)

        return RunConfig(
            runs=runs,
            retry_policy=retry_policy,
            log_io_settings=log_io_settings,
        )
