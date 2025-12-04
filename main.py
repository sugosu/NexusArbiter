# main.py
from __future__ import annotations

import argparse
from pathlib import Path

from dotenv import load_dotenv

from core.config.run_config import RunConfig
from core.runtime.pipeline_runner import PipelineRunner


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="aiAgency – AI Code Generation Framework")
    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Path to a JSON config file describing one or more runs.",
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv()

    args = parse_args()
    project_root = Path(__file__).resolve().parent

    config = RunConfig.from_file(args.config)
    runner = PipelineRunner(project_root=project_root, config=config)

    # Run the pipeline; summary is logged inside PipelineRunner.run()
    runner.run()



if __name__ == "__main__":
    main()
