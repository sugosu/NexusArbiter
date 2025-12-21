import os
import sys

OUTPUT_NAME = "merged_all_library.txt"
LICENSE_NAME = "LICENSE"

INCLUDED_DIRS = [
##    r"C:\projects\aiAgency\core",
 ##   r"C:\projects\aiAgency\context_files",
##    r"C:\projects\aiAgency\example"
r"C:\projects\aiAgency\expense_tracker"
]

INCLUDED_FILES = [
##    r"C:\projects\aiAgency\cli.py",
 ##   r"C:\projects\aiAgency\main.py",
  ##  r"C:\projects\aiAgency\README.md",  # will be skipped unless allowed below
   ## r"C:\projects\aiAgency\LICENSE",
]

ALLOWED_EXTENSIONS = {".py"}  # extend if needed, e.g. {".py", ".json"}


def _safe_abspath(path: str) -> str:
    return os.path.normpath(os.path.abspath(os.path.expanduser(path)))


def _is_allowed_file(path: str, output_name: str) -> bool:
    if os.path.basename(path) == output_name:
        return False

    if os.path.basename(path) == LICENSE_NAME:
        return True

    _, ext = os.path.splitext(path)
    return ext in ALLOWED_EXTENSIONS


def collect_all_files(
    included_dirs: list[str],
    included_files: list[str],
    output_name: str,
) -> list[str]:

    files: list[str] = []
    seen: set[str] = set()

    for fpath in included_files:
        fpath = _safe_abspath(fpath)
        if not os.path.isfile(fpath):
            continue

        if not _is_allowed_file(fpath, output_name):
            continue

        if fpath not in seen:
            files.append(fpath)
            seen.add(fpath)

    for base_dir in included_dirs:
        base_dir = _safe_abspath(base_dir)
        if not os.path.isdir(base_dir):
            continue

        for dirpath, _, filenames in os.walk(base_dir):
            for fname in filenames:
                full_path = _safe_abspath(os.path.join(dirpath, fname))

                if full_path in seen:
                    continue

                if not _is_allowed_file(full_path, output_name):
                    continue

                files.append(full_path)
                seen.add(full_path)

    return sorted(files)


def merge_all(files: list[str], output_path: str) -> None:
    out_dir = os.path.dirname(_safe_abspath(output_path))

    with open(output_path, "w", encoding="utf-8") as out:
        for fpath in files:
            rel_path = os.path.relpath(fpath, start=out_dir)

            out.write("\n")
            out.write("#" * 90 + "\n")
            out.write(f"# FILE: {rel_path}\n")
            out.write("#" * 90 + "\n\n")

            try:
                with open(fpath, "r", encoding="utf-8") as src:
                    out.write(src.read())
            except Exception as e:
                out.write(f"!! ERROR READING FILE: {e} !!")

            out.write("\n\n")

    print(f"Merged {len(files)} files into: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        output_root = _safe_abspath(sys.argv[1])
    else:
        output_root = os.path.dirname(_safe_abspath(INCLUDED_FILES[0])) \
            if INCLUDED_FILES else os.getcwd()

    output_file = os.path.join(output_root, OUTPUT_NAME)

    files = collect_all_files(
        included_dirs=INCLUDED_DIRS,
        included_files=INCLUDED_FILES,
        output_name=OUTPUT_NAME,
    )

    merge_all(files, output_file)
