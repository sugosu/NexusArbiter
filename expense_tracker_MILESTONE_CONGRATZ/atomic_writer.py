import os
import tempfile
import errno
import logging
from typing import Optional


logger = logging.getLogger(__name__)


class AtomicFileWriter:
    """
    Provide atomic write semantics by writing content to a temporary file in the
    same directory and atomically replacing the target file via os.replace.

    Behaviour:
      - Create a uniquely named temporary file adjacent to target_path.
      - Write the full content (UTF-8), flush and optionally fsync the file.
      - Close the temp file and atomically rename it to target_path.
      - Optionally fsync the containing directory to ensure the directory entry
        is persisted.
      - Attempt to remove the temporary file on failure.

    Notes:
      - If fsync_after_write is True, the implementation calls os.fsync on the
        file descriptor and attempts to fsync the directory. If the platform
        does not permit directory fsync, directory fsync errors are logged but
        not raised separately (the overall operation will raise if rename fails).
      - On any IO-related failure an IOError is raised.
    """

    def __init__(self, fsync_after_write: bool = True, temp_suffix: str = ".tmp") -> None:
        self.fsync_after_write = bool(fsync_after_write)
        self.temp_suffix = str(temp_suffix)

    def atomic_write(self, target_path: str, content: str) -> None:
        """
        Atomically write `content` to `target_path`.

        Parameters
        ----------
        target_path:
            Destination file path to be replaced atomically.
        content:
            Text content to write (will be encoded as UTF-8).

        Raises
        ------
        IOError:
            If writing, syncing or renaming fails. On failure the temporary
            file will be removed where possible.
        """
        if not isinstance(target_path, str) or not target_path:
            raise IOError("target_path must be a non-empty string")

        dirpath = os.path.dirname(os.path.abspath(target_path)) or os.getcwd()
        basename = os.path.basename(target_path) or "tmpfile"

        # Create temp file in same directory to ensure rename is atomic on the
        # same filesystem. Use delete=False so we can close and rename on all
        # platforms (Windows requires the file to be closed before rename).
        temp_file = None
        temp_name: Optional[str] = None
        try:
            fd = None
            # Use NamedTemporaryFile to get a unique filename; close file object
            # after writing so os.replace can operate on Windows as well.
            with tempfile.NamedTemporaryFile(
                mode="wb",
                suffix=self.temp_suffix,
                prefix=basename + "-",
                dir=dirpath,
                delete=False,
            ) as tf:
                temp_name = tf.name
                # Write bytes
                try:
                    data = content.encode("utf-8")
                except Exception as e:
                    raise IOError("Failed to encode content to UTF-8") from e

                tf.write(data)
                tf.flush()

                # Optionally fsync the file contents to disk
                if self.fsync_after_write:
                    try:
                        os.fsync(tf.fileno())
                    except OSError:
                        # If fsync fails here, we still attempt to clean up and
                        # propagate the error below after attempting rename.
                        logger.exception("fsync on temp file failed for %s", temp_name)

            # At this point the temporary file is closed.

            # Atomically replace the target with the temp file
            try:
                os.replace(temp_name, target_path)
            except Exception as e:
                # Attempt to remove the temp file on rename failure
                try:
                    if temp_name and os.path.exists(temp_name):
                        os.unlink(temp_name)
                except Exception:
                    logger.exception("Failed to remove temporary file after rename failure: %s", temp_name)
                raise IOError(f"Atomic rename failed for {target_path}") from e

            # Optionally fsync the containing directory to persist the directory entry
            if self.fsync_after_write:
                try:
                    dir_fd = os.open(dirpath, os.O_RDONLY)
                    try:
                        os.fsync(dir_fd)
                    finally:
                        os.close(dir_fd)
                except OSError as e:
                    # Directory fsync may not be supported on all platforms
                    # (or may fail due to permissions). Log but do not mask
                    # the successful rename; durability may be reduced.
                    logger.exception("Directory fsync failed for %s: %s", dirpath, e)

            logger.debug("Atomic write successful: %s", target_path)

        except Exception as exc:
            # Normalize to IOError for callers per manifest contract
            if isinstance(exc, IOError):
                raise
            raise IOError("Atomic write failed") from exc
