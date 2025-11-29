# main.py
from dotenv import load_dotenv
import argparse

from app.app import main as app_main
from core.config.run_config import RunConfig
from pathlib import Path
import json

load_dotenv()  # load .env once at entry point


def parse_args():
    parser = argparse.ArgumentParser(description="AI Code Generation Framework")
    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Path to a JSON config file describing one or more runs.",
    )
    return parser.parse_args()

def load_context_params(project_root: Path, context_files: list[str]) -> dict:
    """
    Load one or more context/profile JSON files and merge them into a single
    OpenAI payload dict.

    For now:
    - Use the first file as the base.
    - Ignore the rest (you can extend to deep-merge later if needed).
    """
    if not context_files:
        raise ValueError("Run is missing 'context_file'. At least one path is required.")

    first = context_files[0]
    context_path = (project_root / first).resolve()

    if not context_path.exists():
        raise FileNotFoundError(f"context_file not found: {context_path}")

    with context_path.open("r", encoding="utf-8") as f:
        params = json.load(f)

    if not isinstance(params, dict):
        raise ValueError(f"context_file must contain a JSON object: {context_path}")

    return params


if __name__ == "__main__":
    args = parse_args()

    project_root = Path(__file__).resolve().parent
    config = RunConfig.from_file(args.config)

    for idx, run in enumerate(config.runs, start=1):
        print(
            f"[RUN {idx}] "
            f"profile={run.profile_name}, "
            f"class_name={run.class_name}, "
            f"refactor_class={run.refactor_class}, "
            f"context_file={run.context_file}, "
            f"target_file={run.target_file}"
        )

        agent_input = dict(run.agent_input or {})

# 🔒 target_file from RunItem is the single source of truth
        if run.target_file:
            agent_input["target_file"] = run.target_file


        # Build run_params from context_file (new style)
        if run.context_file:
            run_params = load_context_params(project_root, run.context_file)
        else:
            # If no context_file is provided, you can either:
            # - raise, or
            # - fall back to the old behaviour.
            raise ValueError(
                "Run is missing 'context_file'; new engine requires context_file-based runs."
            )

        app_main(
            profile_name=run.profile_name,
            class_name=run.class_name,
            task_description=run.task_description,
            refactor_class=run.refactor_class,
            agent_input=agent_input,
            run_item=run,
            run_params=run_params,
        )


