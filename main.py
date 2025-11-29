# main.py
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from core.config.run_config import RunConfig
from core.runtime.run_executor import RunExecutor

# Load .env once at entry point
load_dotenv()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="aiAgency – AI Code Generation Framework")
    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Path to a JSON config file describing one or more runs.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    project_root = Path(__file__).resolve().parent
    config = RunConfig.from_file(args.config)

    executor = RunExecutor(project_root=project_root)

    total_runs = len(config.runs)
    retry_from: Optional[int] = getattr(config, "retry_from", None)

    # Ensure retry_from is within [1, total_runs] if present
    if retry_from is not None:
        retry_from = max(1, min(retry_from, total_runs))

    # Pipeline control
    idx = 1                      # 1-based current run index
    pipeline_retried = False     # allow only a single pipeline-level restart
    restart_from_index: Optional[int] = None  # where to restart AND force retry_context

    while idx <= total_runs:
        run = config.runs[idx - 1]

        # If we just restarted the pipeline from a specific index,
        # then for that first run we want retry_context_files to override
        # the normal context_file from the very first attempt.
        use_retry_ctx_first = restart_from_index is not None and idx == restart_from_index

        # Consume the flag so it applies only to this first restarted run.
        if use_retry_ctx_first:
            restart_from_index = None

        result = executor.execute(
            run=run,
            run_index=idx,
            use_retry_context_on_first_attempt=use_retry_ctx_first,
        )

        status = "OK" if result.success else "FAILED"
        if result.retried:
            print(
                f"[RUN {idx}] finished with status {status} after {result.attempts} attempts. "
                f"Retry reason (last): {result.last_retry_reason or '<none>'}."
            )
        else:
            print(
                f"[RUN {idx}] finished with status {status} after {result.attempts} attempts."
            )

        # Pipeline-level retry_from logic:
        #
        # If:
        #   - this run did NOT succeed,
        #   - the RunExecutor reports that the agent requested retry at some point
        #     (result.retried == True), and
        #   - the config defines retry_from,
        #   - and we have not yet used the pipeline-level restart,
        # then:
        #   - restart the pipeline from retry_from,
        #   - and for that first restarted run, force use of retry_context_files.
        if (
            not result.success
            and result.retried
            and retry_from is not None
            and not pipeline_retried
        ):
            print(
                f"[RUN {idx}] pipeline-level retry_from triggered; "
                f"restarting from run index {retry_from} "
                f"using retry_context_files for that run (if configured)."
            )
            pipeline_retried = True
            restart_from_index = retry_from
            idx = retry_from
            continue

        idx += 1
