import logging
import sys
from typing import Optional, Any, Dict


def _normalize_bool(value: Any) -> bool:
    """Normalize booleans coming from env/Secrets Manager."""
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _normalize_level(level: Any) -> int:
    """Convert log level inputs to a valid logging level int, default INFO."""
    if isinstance(level, int):
        return level
    s = str(level or "").strip().upper()
    return getattr(logging, s, logging.INFO)


class _SafeExtraFilter(logging.Filter):
    """
    Ensures expected extra fields exist so formatters (especially JSON) never crash.
    """
    DEFAULTS: Dict[str, Any] = {
        "request_id": "-",
        "user_id": "-",
        "step": "-",
    }

    def filter(self, record: logging.LogRecord) -> bool:
        for k, v in self.DEFAULTS.items():
            if not hasattr(record, k):
                setattr(record, k, v)
        return True


def setup_logger(log_level: Any, enable_cloudwatch_logs: Any) -> logging.Logger:
    """
    Setup structured logging for the application with optional JSON logs.

    - Always returns a valid logger (never NameError)
    - Safe against missing python-json-logger
    - Safe against missing extra fields in log records
    """
    level_int = _normalize_level(log_level)
    enable_json = _normalize_bool(enable_cloudwatch_logs)

    # Use a stable "app" logger name; callers can also get their own named loggers.
    logger = logging.getLogger("app")
    logger.setLevel(level_int)

    # Configure root once. force=True replaces existing root handlers (useful in containers).
    logging.basicConfig(
        level=level_int,
        format="%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        force=True,
    )

    # Add a filter to root so even third-party loggers won't crash JSON formatting
    root = logging.getLogger()
    root.addFilter(_SafeExtraFilter())

    # Ensure "your" loggers emit at chosen level (these names are from your codebase)
    for name in [
        "agentcore_mcp_server",
        "mcp_image_generator",
        "mcp_sharepoint_tools",   # ✅ add
        "sharepoint_auth",        # ✅ add
        "graph_client",           # ✅ add
        "clients",
        "mcp_tools",
        "app",
    ]:
        logging.getLogger(name).setLevel(level_int)

    # Reduce noisy ping logs
    for name in ["mcp.server.lowlevel.server", "mcp.server.streamable_http"]:
        logging.getLogger(name).setLevel(logging.INFO)

    # Uvicorn/FastAPI log levels (common in AgentCore containers)
    for name in ["uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"]:
        logging.getLogger(name).setLevel(level_int)

    # Optional JSON logging to stdout (CloudWatch friendly)
    # if enable_json:
    #     try:
    #         from pythonjsonlogger import jsonlogger  # type: ignore

    #         # Avoid adding duplicate JSON handlers on repeated setup_logger calls
    #         if not any(getattr(h, "name", "") == "json_stdout" for h in root.handlers):
    #             json_handler = logging.StreamHandler(sys.stdout)
    #             json_handler.name = "json_stdout"
    #             json_handler.setLevel(level_int)

    #             # Use a JSON formatter; SafeExtraFilter ensures missing fields won't crash.
    #             formatter = jsonlogger.JsonFormatter(
    #                 "%(asctime)s %(name)s %(levelname)s %(funcName)s %(lineno)d "
    #                 "%(message)s %(request_id)s %(user_id)s %(step)s"
    #             )
    #             json_handler.setFormatter(formatter)
    #             root.addHandler(json_handler)

    #         logger.info("CloudWatch structured JSON logging enabled")
    #     except Exception as e:
    #         # Never fail startup because of logging
    #         logger.warning("JSON logging not enabled (python-json-logger missing or error): %s", str(e))

    logger.info("CloudWatch logging enabled.")
    return logger


def log_step(
    logger: logging.Logger,
    step: str,
    request_id: str,
    user_id: str,
    message: str,
    level: str = "INFO",
    **kwargs,
):
    """
    Log a functional step with structured context for debugging.
    Guaranteed safe even if formatter expects extra fields.
    """
    extra = {
        "step": step or "-",
        "request_id": request_id or "-",
        "user_id": user_id or "-",
        **(kwargs or {}),
    }

    lvl = str(level or "INFO").strip().upper()
    if lvl == "DEBUG":
        logger.debug(message, extra=extra)
    elif lvl == "WARNING" or lvl == "WARN":
        logger.warning(message, extra=extra)
    elif lvl == "ERROR":
        logger.error(message, extra=extra)
    elif lvl == "CRITICAL":
        logger.critical(message, extra=extra)
    else:
        logger.info(message, extra=extra)