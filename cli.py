from __future__ import annotations

import argparse
import signal
import sys
from pathlib import Path

from dotenv import load_dotenv

from core.config.run_config import RunConfig
from core.runtime.pipeline_runner import PipelineRunner


def _handle_sigint(signum, frame) -> None:
    print("\n[INTERRUPTED] NexusArbiter terminated by user (Ctrl+C).")
    raise SystemExit(130)  # 130 is the conventional exit code for SIGINT


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nexusarbiter",
        description="NexusArbiter – AI orchestration framework",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # --------------------
    # run command
    # --------------------
    run_p = sub.add_parser("run", help="Execute a run config JSON")
    run_p.add_argument(
        "config",
        type=str,
        help="Path to run config JSON (e.g. library_manager/runs/main.json)",
    )
    run_p.add_argument(
        "--project-root",
        type=str,
        default=None,
        help="Project root for resolving relative paths. Default: current working directory.",
    )
    run_p.add_argument(
        "--start-from",
        type=int,
        default=None,
        help="Zero-based index of the run item to start from.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    # Register Ctrl+C handler as early as possible
    signal.signal(signal.SIGINT, _handle_sigint)

    load_dotenv()

    args = _build_parser().parse_args(argv)

    if args.command == "run":
        project_root = Path(args.project_root).resolve() if args.project_root else Path.cwd().resolve()
        config_path = Path(args.config).resolve()

        config = RunConfig.from_file(config_path)
        runner = PipelineRunner(
            project_root=project_root,
            config=config,
            start_from=args.start_from,
        )

        runner.run()
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
