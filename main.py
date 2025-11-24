# main.py
from dotenv import load_dotenv
import argparse

from app.app import main as app_main
from core.config.run_config import RunConfig

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


if __name__ == "__main__":
    args = parse_args()

    config = RunConfig.from_file(args.config)

    for idx, run in enumerate(config.runs, start=1):
        print(
            f"[RUN {idx}] profile={run.profile_name}, "
            f"class_name={run.class_name}, "
            f"refactor_class={run.refactor_class}"
        )

        app_main(
            profile_name=run.profile_name,
            class_name=run.class_name,
            refactor_class=run.refactor_class,
            task_description=run.task_description,
            run_params=run.raw or {},
        )
