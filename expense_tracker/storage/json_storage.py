from typing import Any, Optional

from app_logging import AppLogger
import json
import tempfile
import os
import io


class JsonStorage:
    """Storage adapter that reads and writes JSON-serializable structures

    Responsibilities (per manifest):
    - read(file_path) -> Optional[Any]: return parsed JSON or None if missing
    - write(file_path, data): atomic write using a temporary file in same directory

    Uses injected AppLogger for logging.
    """

    def __init__(self, logger: AppLogger) -> None:
        # Store injected logger. Do not perform I/O here.
        self._logger = logger

    def read(self, file_path: str) -> Optional[Any]:
        """Read and parse JSON from file_path.

        Returns the parsed JSON-serializable structure, or None if file is missing.
        On I/O or parse errors, logs and re-raises the exception.
        """
        try:
            # Use io.open to be explicit about encoding
            with io.open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data
        except FileNotFoundError:
            # Missing file is treated as bootstrap-safe empty result
            try:
                self._logger.debug("json_storage.read: file not found, returning None", {"file_path": file_path})
            except Exception:
                # Logging should not break read semantics; swallow logger errors
                pass
            return None
        except Exception as exc:
            # Log parse or I/O errors and propagate
            try:
                self._logger.error("json_storage.read: error reading or parsing file", {"file_path": file_path, "error": str(exc)})
            except Exception:
                pass
            raise

    def write(self, file_path: str, data: Any) -> None:
        """Atomically write JSON-serializable `data` to `file_path`.

        Steps:
        1) Serialize to JSON text using json.dumps(..., ensure_ascii=False, separators=(',', ':'))
        2) Create a temporary file in the same directory using tempfile.NamedTemporaryFile(delete=False)
        3) Write bytes, flush, and fsync
        4) Atomically replace target with os.replace
        On error, attempts to clean up temporary file and propagates the exception.
        """
        dir_name = os.path.dirname(file_path) or "."
        tmp_file_path = None
        try:
            # Ensure directory exists to avoid needless failures when writing
            os.makedirs(dir_name, exist_ok=True)

            # Serialize to JSON text and encode to bytes
            json_text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
            json_bytes = json_text.encode("utf-8")

            # Create a temporary file in the same directory
            with tempfile.NamedTemporaryFile(mode="wb", delete=False, dir=dir_name) as tmpf:
                tmp_file_path = tmpf.name
                tmpf.write(json_bytes)
                tmpf.flush()
                try:
                    os.fsync(tmpf.fileno())
                except Exception:
                    # If fsync is not available or fails, log and continue to attempt atomic replace
                    try:
                        self._logger.debug("json_storage.write: fsync failed or not supported", {"tmp_path": tmp_file_path})
                    except Exception:
                        pass

            # Atomically replace the target file with the temporary file
            os.replace(tmp_file_path, file_path)
            tmp_file_path = None  # ownership transferred; avoid removing in finally

            try:
                self._logger.debug("json_storage.write: successfully wrote file", {"file_path": file_path})
            except Exception:
                pass

        except Exception as exc:
            # Attempt cleanup of temp file if it still exists
            if tmp_file_path and os.path.exists(tmp_file_path):
                try:
                    os.remove(tmp_file_path)
                except Exception:
                    try:
                        self._logger.error("json_storage.write: failed to remove temporary file", {"tmp_path": tmp_file_path, "error": str(exc)})
                    except Exception:
                        pass
            try:
                self._logger.error("json_storage.write: error during write", {"file_path": file_path, "error": str(exc)})
            except Exception:
                pass
            raise
