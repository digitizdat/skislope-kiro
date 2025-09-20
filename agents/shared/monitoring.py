"""Performance monitoring and health checking for agent servers."""

import asyncio
import time
from typing import Any

import psutil
import structlog
from prometheus_client import Counter
from prometheus_client import Histogram
from prometheus_client import generate_latest

from agents.shared.logging_config import log_performance_metric

logger = structlog.get_logger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter(
    "agent_requests_total",
    "Total number of requests",
    ["agent", "method", "status"],
)

REQUEST_DURATION = Histogram(
    "agent_request_duration_seconds",
    "Request duration in seconds",
    ["agent", "method"],
)

ACTIVE_CONNECTIONS = Counter(
    "agent_active_connections",
    "Number of active connections",
    ["agent"],
)


class PerformanceMonitor:
    """Performance monitoring for agent servers."""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.start_time = time.time()
        self.request_count = 0
        self.error_count = 0
        self._monitoring_task: asyncio.Task | None = None

    def start_monitoring(self) -> None:
        """Start background monitoring task."""
        if self._monitoring_task is None:
            self._monitoring_task = asyncio.create_task(self._monitor_loop())
            logger.info("Started performance monitoring", agent=self.agent_name)

    def stop_monitoring(self) -> None:
        """Stop background monitoring task."""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            self._monitoring_task = None
            logger.info("Stopped performance monitoring", agent=self.agent_name)

    async def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        while True:
            try:
                await asyncio.sleep(30)  # Monitor every 30 seconds
                await self._collect_metrics()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    "Error in monitoring loop",
                    agent=self.agent_name,
                    error=str(e),
                    exc_info=True,
                )

    async def _collect_metrics(self) -> None:
        """Collect and log performance metrics."""
        try:
            # System metrics
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            # Log system metrics
            log_performance_metric(
                "cpu_usage_percent",
                cpu_percent,
                "percent",
                {"agent": self.agent_name},
            )

            log_performance_metric(
                "memory_usage_percent",
                memory.percent,
                "percent",
                {"agent": self.agent_name},
            )

            log_performance_metric(
                "disk_usage_percent",
                disk.percent,
                "percent",
                {"agent": self.agent_name},
            )

            # Application metrics
            uptime = time.time() - self.start_time
            log_performance_metric(
                "uptime_seconds",
                uptime,
                "seconds",
                {"agent": self.agent_name},
            )

            log_performance_metric(
                "total_requests",
                self.request_count,
                "count",
                {"agent": self.agent_name},
            )

            log_performance_metric(
                "error_rate",
                self.error_count / max(self.request_count, 1),
                "ratio",
                {"agent": self.agent_name},
            )

        except Exception as e:
            logger.error(
                "Failed to collect metrics",
                agent=self.agent_name,
                error=str(e),
                exc_info=True,
            )

    def record_request(self, method: str, duration: float, success: bool) -> None:
        """
        Record a request for monitoring.

        Args:
            method: Request method name
            duration: Request duration in seconds
            success: Whether the request was successful
        """
        self.request_count += 1
        if not success:
            self.error_count += 1

        # Update Prometheus metrics
        REQUEST_COUNT.labels(
            agent=self.agent_name,
            method=method,
            status="success" if success else "error",
        ).inc()

        REQUEST_DURATION.labels(
            agent=self.agent_name,
            method=method,
        ).observe(duration)


class HealthChecker:
    """Health checking for agent servers."""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.checks: dict[str, Any] = {}

    def add_check(self, name: str, check_func: Any) -> None:
        """
        Add a health check.

        Args:
            name: Check name
            check_func: Async function that returns True if healthy
        """
        self.checks[name] = check_func
        logger.info("Added health check", check=name, agent=self.agent_name)

    async def run_checks(self) -> dict[str, Any]:
        """
        Run all health checks.

        Returns:
            Health check results
        """
        results = {
            "agent": self.agent_name,
            "timestamp": time.time(),
            "checks": {},
            "overall_status": "healthy",
        }

        for name, check_func in self.checks.items():
            try:
                start_time = time.time()
                is_healthy = await check_func()
                duration = time.time() - start_time

                results["checks"][name] = {
                    "status": "healthy" if is_healthy else "unhealthy",
                    "duration_ms": duration * 1000,
                }

                if not is_healthy:
                    results["overall_status"] = "unhealthy"

            except Exception as e:
                results["checks"][name] = {
                    "status": "error",
                    "error": str(e),
                }
                results["overall_status"] = "unhealthy"

                logger.error(
                    "Health check failed",
                    check=name,
                    agent=self.agent_name,
                    error=str(e),
                    exc_info=True,
                )

        return results


def get_prometheus_metrics() -> str:
    """Get Prometheus metrics in text format."""
    return generate_latest().decode("utf-8")
