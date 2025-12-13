from __future__ import annotations

import sys
from cli import main as cli_main


def main() -> None:
    # Backward-compatible shim:
    # python main.py --config X  ->  nexusarbiter run X
    argv = sys.argv[1:]

    if "--config" in argv:
        i = argv.index("--config")
        cfg = argv[i + 1] if i + 1 < len(argv) else None
        if not cfg:
            raise SystemExit(2)

        # map legacy --startfrom to --start-from
        start_from = None
        if "--startfrom" in argv:
            j = argv.index("--startfrom")
            start_from = argv[j + 1] if j + 1 < len(argv) else None

        new_argv = ["run", cfg]
        if start_from is not None:
            new_argv += ["--start-from", str(int(start_from))]

        raise SystemExit(cli_main(new_argv))

    # If someone calls main.py with no legacy args, just show CLI help
    raise SystemExit(cli_main(["run", "--help"]))


if __name__ == "__main__":
    main()
