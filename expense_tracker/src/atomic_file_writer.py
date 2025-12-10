from app_controller import AppController
from atomic_file_writer import AtomicFileWriter
from config import Config
from expense_repository import ExpenseRepository
from expense_service import ExpenseService
from expense_validator import ExpenseValidator
from json_serializer import JsonSerializer
from models import Expense
from models import ExpenseStore
from models import ServiceState
from models import Settings

import os
import tempfile
from typing import Optional


class AtomicFileWriter:
    """Provide atomic write primitive using write-to-temp-then-rename semantics.

    Behavior:
    - Creates a temporary file adjacent to the target path.
    - Writes the provided content (UTF-8) to the temporary file.
    - Flushes and optionally fsyncs file data.
    - Optionally fsyncs the containing directory to ensure the rename is durable.
    - Atomically replaces the target path with the temporary file using os.replace.

    On failures during rename, an attempt is made to remove the temporary file. IO-related
    failures are propagated as IOError with the original exception chained.

    Note: This implementation chooses a deterministic approach using tempfile.mkstemp
    to allocate a unique temporary file in the same directory as the target. Directory
    fsync uses os.open on the directory; platforms that do not support directory
    fsync will have that step ignored silently.
    """

    def __init__(self, fsync_after_write: bool = True, temp_suffix: str = ".tmp") -> None:
        self.fsync_after_write = bool(fsync_after_write)
        self.temp_suffix = str(temp_suffix)

    def atomic_write(self, target_path: str, content: str) -> None:
        """Atomically write `content` (text) to `target_path`.

        Parameters:
        - target_path: destination file path to be atomically replaced.
        - content: full file content as text (will be encoded as UTF-8).

        Raises:
        - IOError on write/rename/fsync failures. Temporary files are cleaned up when
          possible on error.
        """
        target_path = str(target_path)
        # Ensure directory exists (do not create directories implicitly here; let IOErrors propagate)
        dirpath = os.path.dirname(os.path.abspath(target_path)) or "."

        fd = None
        tmp_path: Optional[str] = None
        try:
            # Create a uniquely named temporary file in same directory to ensure rename is atomic
            # Use a recognizable prefix based on the target file name
            prefix = os.path.basename(target_path) + "."
            fd, tmp_path = tempfile.mkstemp(suffix=self.temp_suffix, prefix=prefix, dir=dirpath)

            # Write content using the file descriptor returned by mkstemp
            # We open a text wrapper around the fd to write UTF-8 text
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                fd = None  # ownership transferred to fdopen context; avoid double-close
                f.write(content)
                f.flush()
                if self.fsync_after_write:
                    try:
                        os.fsync(f.fileno())
                    except Exception:
                        # fsync failure is considered an IO problem; raise as IOError below
                        raise

            # Optionally fsync the directory to ensure the directory entry for the new file is durable
            if self.fsync_after_write:
                dir_fd = None
                try:
                    # Some platforms provide O_DIRECTORY; fall back to read-only open if not present
                    flags = getattr(os, "O_DIRECTORY", None)
                    if flags is None:
                        dir_fd = os.open(dirpath, os.O_RDONLY)
                    else:
                        dir_fd = os.open(dirpath, flags)
                    os.fsync(dir_fd)
                except Exception:
                    # Directory fsync is best-effort; do not fail the whole write if unsupported.
                    pass
                finally:
                    if dir_fd is not None:
                        try:
                            os.close(dir_fd)
                        except Exception:
                            pass

            # Atomically replace target with temporary file
            try:
                os.replace(tmp_path, target_path)
                tmp_path = None  # moved successfully; avoid cleanup
            except Exception as exc:
                # Attempt to remove temporary file on failure
                try:
                    if tmp_path and os.path.exists(tmp_path):
                        os.remove(tmp_path)
                        tmp_path = None
                except Exception:
                    # If cleanup fails, there's not much we can do; continue to raise original error
                    pass
                raise IOError(f"Failed to atomically replace '{target_path}'") from exc

        except Exception as exc:
            # Ensure cleanup of temp file if it still exists
            try:
                if fd is not None:
                    try:
                        os.close(fd)
                    except Exception:
                        pass
                if tmp_path and os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass
            finally:
                # Normalize and propagate as IOError for the repository's expected error handling
                if isinstance(exc, IOError):
                    raise
                raise IOError("atomic_write failed") from exc
