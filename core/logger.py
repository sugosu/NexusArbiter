import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


class JsonFormatter(logging.Formatter):
    """Format log records as single-line JSON objects."""

    # keys from LogRecord we DON'T want to dump
    _skip_keys = {
        "name", "msg", "args", "levelname", "levelno",
        "pathname", "filename", "module", "exc_info",
        "exc_text", "stack_info", "lineno", "funcName",
        "created", "msecs", "relativeCreated", "thread",
        "threadName", "processName", "process", "asctime"
    }

    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # include any extra fields passed via logger.*(..., extra={...})
        for key, value in record.__dict__.items():
            if key not in self._skip_keys:
                log_record[key] = value

        return json.dumps(log_record, ensure_ascii=False)


class BasicLogger:
    def __init__(
        self,
        name: str,
        level: int = logging.INFO,
        log_to_file: bool = True,
        log_dir: str = "logs",
        log_file: str = "app.jsonl",
        max_bytes: int = 5_000_000,  # 5 MB
        backup_count: int = 5,
    ):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # Prevent adding handlers multiple times
        if self.logger.handlers:
            return

        # --- Console handler (human-readable) ---
        console_handler = logging.StreamHandler()
        console_fmt = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(console_fmt)
        self.logger.addHandler(console_handler)

        # --- File handler (JSON) ---
        if log_to_file:
            Path(log_dir).mkdir(parents=True, exist_ok=True)
            file_path = Path(log_dir) / log_file

            file_handler = RotatingFileHandler(
                file_path,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8",
            )

            json_formatter = JsonFormatter()
            file_handler.setFormatter(json_formatter)

            self.logger.addHandler(file_handler)

    def get_logger(self) -> logging.Logger:
        return self.logger
