# core/config/run_config.py
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


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
            log_dir=str(data.get("log_dir", "logs/io")),
            request_file_pattern=str(
                data.get("request_file_pattern", "{run_name}__{attempt}__request.json")
            ),
            response_file_pattern=str(
                data.get("response_file_pattern", "{run_name}__{attempt}__response.json")
            ),
        )


@dataclass
class RunItem:
    name: str
    profile_file: str
    task_description: Optional[str]
    context_file: List[str]
    target_file: Optional[str]
    allowed_actions: List[str]

    # Rerun-related fields (validator step)
    rerun_index: Optional[int] = None
    target_run: Optional[str] = None
    rerun_strategy: Optional[str] = None


    # Optional per-run I/O logging overrides
    log_io_override: Optional[Dict[str, Any]] = None

    # Provider override (set during rerun)
    provider_override: Optional[str] = None

    def is_validator(self) -> bool:
        return (
            self.rerun_index is not None
            and self.target_run is not None
            and self.rerun_strategy is not None
        )


@dataclass(frozen=True)
class IncludeRun:
    include_run: str


RunStep = Union[RunItem, IncludeRun]


@dataclass
class RunConfig:
    runs: List[RunStep] = field(default_factory=list)
    retry_policy: Optional[Dict[str, Any]] = None
    log_io_settings: LogIOSettings = field(default_factory=LogIOSettings)

    @staticmethod
    def from_file(path: str | Path) -> "RunConfig":
        path = Path(path)
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            raise ValueError("Run config root must be a JSON object.")

        log_io_settings = LogIOSettings.from_dict(data.get("log_io"))
        retry_policy = data.get("retry_policy")

        runs_raw = data.get("runs", [])
        if runs_raw is None:
            runs_raw = []
        if not isinstance(runs_raw, list):
            raise ValueError("'runs' must be a list.")

        runs: List[RunStep] = []
        for idx, obj in enumerate(runs_raw):
            if not isinstance(obj, dict):
                raise ValueError(f"runs[{idx}] must be an object.")

            # include_run step
            if "include_run" in obj:
                include_val = obj.get("include_run")
                if not isinstance(include_val, str) or not include_val.strip():
                    raise ValueError(f"runs[{idx}].include_run must be a non-empty string.")

                # enforce mutual exclusivity (schema stays the same; error earlier)
                forbidden = [k for k in ("profile_file", "context_file", "target_file", "allowed_actions") if k in obj]
                if forbidden:
                    raise ValueError(
                        f"runs[{idx}] include_run step must not include agent fields: {forbidden}."
                    )

                runs.append(IncludeRun(include_run=include_val))
                continue

            # agent step
            if "profile_file" not in obj:
                raise ValueError(f"runs[{idx}] missing required field 'profile_file'.")

            rerun_index = obj.get("rerun_index")
            rerun_strategy = obj.get("rerun_strategy")


            context_file = obj.get("context_file", [])
            if context_file is None:
                context_file = []
            if not isinstance(context_file, list):
                raise ValueError(f"runs[{idx}].context_file must be a list.")
            context_file = [str(x) for x in context_file]

            allowed_actions = obj.get("allowed_actions", [])
            if allowed_actions is None:
                allowed_actions = []
            if not isinstance(allowed_actions, list):
                raise ValueError(f"runs[{idx}].allowed_actions must be a list.")
            allowed_actions = [str(x) for x in allowed_actions]

            runs.append(
                RunItem(
                    name=str(obj.get("name") or ""),
                    profile_file=str(obj["profile_file"]),
                    task_description=obj.get("task_description"),
                    context_file=context_file,
                    target_file=obj.get("target_file"),
                    allowed_actions=allowed_actions,
                    rerun_index=rerun_index,
                    target_run=obj.get("target_run"),
                    rerun_strategy=rerun_strategy,
                    log_io_override=obj.get("log_io")
                )
            )

        return RunConfig(runs=runs, retry_policy=retry_policy, log_io_settings=log_io_settings)
