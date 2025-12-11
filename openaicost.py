#!/usr/bin/env python3
import argparse
import json
import os
from datetime import datetime, timezone
from typing import Optional, Tuple

PRICE_PER_1K_TOKENS = 0.0


def looks_like_response_file(filename: str) -> bool:
    """Return True if filename should be treated as an API response JSON file."""
    lower = filename.lower()
    return lower.endswith("_response.json") or lower.endswith("_response")


def load_json_safe(path: str) -> Optional[dict]:
    """Load JSON file, return dict or None on error."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:  # noqa: BLE001
        print(f"[WARN] Failed to load JSON from {path}: {exc}")
        return None


def extract_usage(entry: dict) -> Tuple[int, int, int]:
    """
    Extract (total_tokens, prompt_tokens, completion_tokens) from a response dict.
    Missing fields are treated as 0.
    """
    usage = entry.get("usage", {}) or {}
    total_tokens = int(usage.get("total_tokens", 0) or 0)
    prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
    completion_tokens = int(usage.get("completion_tokens", 0) or 0)
    return total_tokens, prompt_tokens, completion_tokens


def extract_created(entry: dict) -> Optional[int]:
    """
    Extract 'created' field as int UNIX timestamp, if present and valid.
    """
    created = entry.get("created")
    if created is None:
        return None
    try:
        return int(created)
    except (TypeError, ValueError):
        return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Aggregate token usage and time span from *_response JSON files "
            "in a given directory."
        )
    )
    parser.add_argument(
        "directory",
        help="Directory containing *_response JSON files.",
    )
    parser.add_argument(
        "--price-per-1k",
        type=float,
        default=PRICE_PER_1K_TOKENS,
        help=(
            "Price per 1000 tokens (same currency as you want in the report). "
            "Overrides the constant in the script."
        ),
    )
    args = parser.parse_args()

    base_dir = args.directory
    price_per_1k = args.price_per_1k

    if not os.path.isdir(base_dir):
        print(f"[ERROR] Not a directory: {base_dir}")
        raise SystemExit(1)

    total_tokens_sum = 0
    prompt_tokens_sum = 0
    completion_tokens_sum = 0
    file_count = 0

    earliest_created: Optional[int] = None
    latest_created: Optional[int] = None

    for name in os.listdir(base_dir):
        if not looks_like_response_file(name):
            continue

        full_path = os.path.join(base_dir, name)
        if not os.path.isfile(full_path):
            continue

        entry = load_json_safe(full_path)
        if entry is None:
            continue

        total_tokens, prompt_tokens, completion_tokens = extract_usage(entry)
        created_ts = extract_created(entry)

        total_tokens_sum += total_tokens
        prompt_tokens_sum += prompt_tokens
        completion_tokens_sum += completion_tokens
        file_count += 1

        if created_ts is not None:
            if earliest_created is None or created_ts < earliest_created:
                earliest_created = created_ts
            if latest_created is None or created_ts > latest_created:
                latest_created = created_ts

    print("=== NexusArbiter Token Usage Summary ===")
    print(f"Directory:           {os.path.abspath(base_dir)}")
    print(f"Response files used: {file_count}")
    print()

    print(f"Total tokens:        {total_tokens_sum}")
    print(f"  Prompt tokens:     {prompt_tokens_sum}")
    print(f"  Completion tokens: {completion_tokens_sum}")
    print()

    if price_per_1k > 0 and total_tokens_sum > 0:
        cost = (total_tokens_sum / 1000.0) * price_per_1k
        print(f"Price per 1K tokens: {price_per_1k}")
        print(f"Estimated cost:      {cost}")
        print()
    else:
        print(
            "Estimated cost:      (set --price-per-1k or PRICE_PER_1K_TOKENS "
            "to compute cost)"
        )
        print()

    if earliest_created is not None and latest_created is not None:
        earliest_dt = datetime.fromtimestamp(earliest_created, tz=timezone.utc)
        latest_dt = datetime.fromtimestamp(latest_created, tz=timezone.utc)
        span_seconds = latest_created - earliest_created

        print("Time span (from 'created' fields):")
        print(f"  Earliest:          {earliest_dt.isoformat()}")
        print(f"  Latest:            {latest_dt.isoformat()}")
        print(f"  Span (seconds):    {span_seconds}")
    else:
        print("Time span:           No valid 'created' timestamps found.")


if __name__ == "__main__":
    main()
