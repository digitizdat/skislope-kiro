"""Structured logging configuration for agent servers."""

import logging
import logging.config
import sys
from pathlib import Path
from typing import Any

import structlog
import yaml


def setup_logging(config_path: str = "logging.yaml") -> None:
    """
    Set up structured logging for agent servers.

    Args:
        config_path: Path to the logging configuration YAML file
    """
    # Ensure logs directory exists
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Load logging configuration
    config_file = Path(config_path)
    if config_file.exists():
        with open(config_file) as f:
            config = yaml.safe_load(f)
        logging.config.dictConfig(config)
    else:
        # Fallback configuration
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler("logs/agents.log"),
            ],
        )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer()
            if sys.stderr.isatty()
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.WriteLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


def log_request_response(
    logger: structlog.BoundLogger,
    method: str,
    params: dict[str, Any],
    response: dict[str, Any],
    duration_ms: float,
    correlation_id: str,
) -> None:
    """
    Log JSON-RPC request/response with structured data.

    Args:
        logger: Structured logger instance
        method: JSON-RPC method name
        params: Request parameters
        response: Response data
        duration_ms: Request duration in milliseconds
        correlation_id: Request correlation ID
    """
    logger.info(
        "JSON-RPC request completed",
        method=method,
        params=params,
        response_size=len(str(response)),
        duration_ms=duration_ms,
        correlation_id=correlation_id,
        success="error" not in response,
    )


def log_performance_metric(
    metric_name: str,
    value: float,
    unit: str,
    tags: dict[str, str] | None = None,
) -> None:
    """
    Log performance metrics in structured format.

    Args:
        metric_name: Name of the metric
        value: Metric value
        unit: Unit of measurement
        tags: Additional tags for the metric
    """
    perf_logger = structlog.get_logger("agents.performance")
    perf_logger.info(
        "Performance metric",
        metric=metric_name,
        value=value,
        unit=unit,
        tags=tags or {},
    )
