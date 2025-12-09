import os
import tempfile
import logging
from typing import Optional


logger = logging.getLogger(__name__)


class AtomicFileWriter:
    """Provide an atomic write primitive: write to a temp file in the same
    directory, optionally fsync the file, then atomically rename into place.

    Notes / reasonable defaults chosen when manifest details are missing:
    - temp files are created using tempfile.NamedTemporaryFile(delete=False)
      in the same directory as the target file to ensure rename stays on the
      same filesystem.
    - If directory fsync is not supported on the platform, errors from that
      step are logged and ignored (best-effort durability).
    """

    def __init__(self, temp_suffix: str = ".tmp", fsync_after_write: bool = True) -> None:
        self.temp_suffix = temp_suffix
        self.fsync_after_write = bool(fsync_after_write)

    def atomic_write(self, target_path: str, content: str) -> None:
        """Atomically write `content` to `target_path`.

        Behaviour:
        1. Create a temporary file adjacent to target_path.
        2. Write the full content and flush; optionally fsync the file.
        3. Atomically replace target_path with the temporary file using os.replace().
        4. Attempt to fsync the containing directory to persist the rename (best-effort).

        Raises:
            IOError: on write/rename failures. Temporary file is removed when
            possible on error.
        """
        target_dir = os.path.dirname(target_path) or "."

        # Ensure the directory exists; let underlying IO raise if it doesn't.
        if not os.path.isdir(target_dir):
            # Let the operation fail naturally when attempting to create the temp file.
            logger.debug("Target directory does not exist: %s", target_dir)

        tmp_file = None
        try:
            # Use a predictable prefix based on target filename to keep temp files
            # adjacent and easier to correlate when debugging.
            base_name = os.path.basename(target_path) or "tmpfile"
            # NamedTemporaryFile with delete=False: close it before rename on all platforms.
            tmp_file = tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=target_dir,
                prefix=f".{base_name}.",
                suffix=self.temp_suffix,
                delete=False,
            )
            tmp_path = tmp_file.name

            # Write content
            tmp_file.write(content)
            tmp_file.flush()

            if self.fsync_after_write:
                try:
                    os.fsync(tmp_file.fileno())
                except OSError as e:
                    # fsync failure on the data file is serious; raise as IOError
                    # to let the caller handle fatal durability errors.
                    raise IOError(f"fsync failed on temporary file '{tmp_path}': {e}") from e

            # Close before rename to ensure compatibility across platforms.
            tmp_file.close()
            tmp_file = None

            # Atomically replace the target
            try:
                os.replace(tmp_path, target_path)
            except Exception as e:
                # Attempt to remove the temp file on failure, then raise IOError.
                try:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
                except Exception:
                    logger.exception("Failed to remove temporary file after rename failure: %s", tmp_path)
                raise IOError(f"atomic rename failed for '{tmp_path}' -> '{target_path}': {e}") from e

            # Best-effort: fsync the containing directory so the directory entry is durable.
            try:
                self._fsync_dir(target_dir)
            except Exception:
                # Do not treat directory fsync failures as fatal; log and continue.
                logger.warning("Directory fsync failed (best-effort): %s", target_dir)

            logger.info("Atomic write successful: %s", target_path)

        except Exception:
            logger.exception("Atomic write failed for target: %s", target_path)
            # Normalize exceptions to IOError for callers expecting IO-related errors.
            raise
        finally:
            # Ensure temporary file (if still present and not moved) is cleaned up.
            if tmp_file is not None:
                try:
                    tmp_file.close()
                except Exception:
                    pass
            # If a tmp_path variable exists and the file still exists, remove it.
            try:
                # tmp_path may not be defined if NamedTemporaryFile creation failed.
                tmp_path  # type: ignore
            except NameError:
                tmp_path = None

            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except Exception:
                    logger.exception("Failed to cleanup temporary file: %s", tmp_path)

    def _fsync_dir(self, dirpath: str) -> None:
        """Attempt to fsync the directory containing the target file.

        This makes the rename durable on POSIX systems. Implemented as best-effort
        because not all platforms allow opening directories or fsyncing them.
        """
        try:
            # Open the directory for reading and fsync its descriptor.
            # Use os.O_RDONLY which is portable; some platforms may refuse to open
            # directories and raise OSError — allow that to bubble up to caller.
            fd = os.open(dirpath, os.O_RDONLY)
        except Exception as e:
            # Re-raise as OSError to be consistent with fsync expectations.
            raise
        else:
            try:
                os.fsync(fd)
            finally:
                try:
                    os.close(fd)
                except Exception:
                    pass
