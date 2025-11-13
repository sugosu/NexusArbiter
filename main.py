# main.py
from dotenv import load_dotenv
import argparse

load_dotenv()  # load .env once at entry point

from app.app import main


def parse_args():
    parser = argparse.ArgumentParser(description="AI Code Generation Framework")
    parser.add_argument(
        "--profile",
        type=str,
        required=True,
        help="Name of the AI profile to use (e.g. code_generation, fast_chat)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    main(profile_name=args.profile)