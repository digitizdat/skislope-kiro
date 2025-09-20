"""
Logging and diagnostic collection utilities for integration testing.

Provides structured logging, diagnostic data collection, and test artifact
management for comprehensive test result analysis and debugging.
"""

import json
import logging
import os
import platform
import subprocess
import sys
import time
import traceback
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

import psutil

from .config import TestConfig
from .models import DiagnosticData
from .models import Severity
from .models import TestError


class TestLogger:
    """Enhanced logger for integration testing with structured output."""

    def __init__(self, name: str, config: TestConfig):
        self.name = name
        self.config = config
        self.logger = logging.getLogger(f"integration_test.{name}")
        self.logger.setLevel(getattr(logging, config.log_level.value))

        # Clear existing handlers
        self.logger.handlers.clear()

        # Set up handlers
        self._setup_handlers()

        # Test context for structured logging
        self.context: dict[str, Any] = {}

    def _setup_handlers(self) -> None:
        """Set up logging handlers based on configuration."""
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # File handler if log directory is configured and exists
        if self.config.env_config.log_dir and self.config.env_config.log_dir.exists():
            log_file = self.config.env_config.log_dir / f"{self.name}.log"
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def set_context(self, **kwargs) -> None:
        """Set logging context for structured logging."""
        self.context.update(kwargs)

    def clear_context(self) -> None:
        """Clear logging context."""
        self.context.clear()

    def _log_with_context(self, level: int, message: str, **kwargs) -> None:
        """Log message with context."""
        context_str = ""
        if self.context or kwargs:
            combined_context = {**self.context, **kwargs}
            context_str = f" | Context: {json.dumps(combined_context, default=str)}"

        self.logger.log(level, f"{message}{context_str}")

    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        self._log_with_context(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        self._log_with_context(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        self._log_with_context(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        """Log error message."""
        self._log_with_context(logging.ERROR, message, **kwargs)

    def exception(self, message: str, **kwargs) -> None:
        """Log exception with traceback."""
        self._log_with_context(
            logging.ERROR, f"{message}\n{traceback.format_exc()}", **kwargs
        )


class DiagnosticCollector:
    """Collects diagnostic information for test analysis."""

    def __init__(self, config: TestConfig):
        self.config = config
        self.logger = TestLogger("diagnostics", config)
        self.start_time = time.time()
        self.diagnostics: DiagnosticData = {}

    def collect_system_info(self) -> dict[str, Any]:
        """Collect system information."""
        try:
            system_info = {
                "platform": platform.platform(),
                "python_version": sys.version,
                "python_executable": sys.executable,
                "architecture": platform.architecture(),
                "processor": platform.processor(),
                "hostname": platform.node(),
                "timestamp": datetime.now().isoformat(),
            }

            # Memory information
            memory = psutil.virtual_memory()
            system_info["memory"] = {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent,
                "used": memory.used,
                "free": memory.free,
            }

            # CPU information
            system_info["cpu"] = {
                "count": psutil.cpu_count(),
                "count_logical": psutil.cpu_count(logical=True),
                "percent": psutil.cpu_percent(interval=1),
            }

            # Disk information
            disk = psutil.disk_usage("/")
            system_info["disk"] = {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": (disk.used / disk.total) * 100,
            }

            self.logger.debug("Collected system information", **system_info)
            return system_info

        except Exception as e:
            self.logger.error(f"Failed to collect system info: {e}")
            return {"error": str(e)}

    def collect_environment_info(self) -> dict[str, Any]:
        """Collect environment information."""
        try:
            env_info = {
                "environment_variables": dict(os.environ),
                "working_directory": os.getcwd(),
                "path": os.environ.get("PATH", "").split(os.pathsep),
                "python_path": sys.path,
            }

            # Node.js information if available
            try:
                node_version = subprocess.run(
                    ["node", "--version"], capture_output=True, text=True, timeout=5
                )
                if node_version.returncode == 0:
                    env_info["node_version"] = node_version.stdout.strip()

                npm_version = subprocess.run(
                    ["npm", "--version"], capture_output=True, text=True, timeout=5
                )
                if npm_version.returncode == 0:
                    env_info["npm_version"] = npm_version.stdout.strip()

            except (subprocess.TimeoutExpired, FileNotFoundError):
                env_info["node_available"] = False

            # UV information if available
            try:
                uv_version = subprocess.run(
                    ["uv", "--version"], capture_output=True, text=True, timeout=5
                )
                if uv_version.returncode == 0:
                    env_info["uv_version"] = uv_version.stdout.strip()
            except (subprocess.TimeoutExpired, FileNotFoundError):
                env_info["uv_available"] = False

            self.logger.debug("Collected environment information")
            return env_info

        except Exception as e:
            self.logger.error(f"Failed to collect environment info: {e}")
            return {"error": str(e)}

    def collect_network_info(self) -> dict[str, Any]:
        """Collect network configuration information."""
        try:
            network_info = {"interfaces": [], "connections": []}

            # Network interfaces
            for interface, addrs in psutil.net_if_addrs().items():
                interface_info = {"name": interface, "addresses": []}
                for addr in addrs:
                    interface_info["addresses"].append(
                        {
                            "family": str(addr.family),
                            "address": addr.address,
                            "netmask": addr.netmask,
                            "broadcast": addr.broadcast,
                        }
                    )
                network_info["interfaces"].append(interface_info)

            # Network connections (limited to avoid security issues)
            try:
                connections = psutil.net_connections(kind="inet")
                for conn in connections[:10]:  # Limit to first 10
                    if conn.status == "LISTEN":
                        network_info["connections"].append(
                            {
                                "local_address": f"{conn.laddr.ip}:{conn.laddr.port}",
                                "status": conn.status,
                                "pid": conn.pid,
                            }
                        )
            except psutil.AccessDenied:
                network_info["connections_error"] = "Access denied"

            self.logger.debug("Collected network information")
            return network_info

        except Exception as e:
            self.logger.error(f"Failed to collect network info: {e}")
            return {"error": str(e)}

    def collect_process_info(self) -> dict[str, Any]:
        """Collect information about running processes."""
        try:
            current_process = psutil.Process()
            process_info = {
                "current_process": {
                    "pid": current_process.pid,
                    "name": current_process.name(),
                    "memory_info": current_process.memory_info()._asdict(),
                    "cpu_percent": current_process.cpu_percent(),
                    "create_time": current_process.create_time(),
                    "cmdline": current_process.cmdline(),
                },
                "python_processes": [],
            }

            # Find other Python processes
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    if "python" in proc.info["name"].lower():
                        process_info["python_processes"].append(
                            {
                                "pid": proc.info["pid"],
                                "name": proc.info["name"],
                                "cmdline": proc.info["cmdline"][:3]
                                if proc.info["cmdline"]
                                else [],
                            }
                        )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            self.logger.debug("Collected process information")
            return process_info

        except Exception as e:
            self.logger.error(f"Failed to collect process info: {e}")
            return {"error": str(e)}

    def collect_all_diagnostics(self) -> DiagnosticData:
        """Collect all diagnostic information."""
        self.logger.info("Starting diagnostic collection")

        self.diagnostics = {
            "collection_time": datetime.now().isoformat(),
            "test_config": {
                "environment": self.config.environment.value,
                "log_level": self.config.log_level.value,
                "parallel_execution": self.config.parallel_execution,
                "max_workers": self.config.max_workers,
            },
            "system": self.collect_system_info(),
            "environment": self.collect_environment_info(),
            "network": self.collect_network_info(),
            "processes": self.collect_process_info(),
        }

        self.logger.info("Diagnostic collection completed")
        return self.diagnostics

    def save_diagnostics(self, filepath: Path | None = None) -> Path:
        """Save diagnostics to file."""
        if not filepath:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"diagnostics_{timestamp}.json"
            filepath = self.config.env_config.log_dir / filename

        try:
            with open(filepath, "w") as f:
                json.dump(self.diagnostics, f, indent=2, default=str)

            self.logger.info(f"Diagnostics saved to {filepath}")
            return filepath

        except Exception as e:
            self.logger.error(f"Failed to save diagnostics: {e}")
            raise


class TestArtifactManager:
    """Manages test artifacts and cleanup."""

    def __init__(self, config: TestConfig):
        self.config = config
        self.logger = TestLogger("artifacts", config)
        self.artifacts: list[Path] = []

    def register_artifact(self, filepath: Path) -> None:
        """Register an artifact for cleanup."""
        self.artifacts.append(filepath)
        self.logger.debug(f"Registered artifact: {filepath}")

    def save_test_output(self, content: str, filename: str) -> Path:
        """Save test output to file."""
        filepath = self.config.env_config.temp_dir / filename

        try:
            with open(filepath, "w") as f:
                f.write(content)

            self.register_artifact(filepath)
            self.logger.debug(f"Saved test output to {filepath}")
            return filepath

        except Exception as e:
            self.logger.error(f"Failed to save test output: {e}")
            raise

    def save_json_artifact(self, data: Any, filename: str) -> Path:
        """Save JSON data as artifact."""
        filepath = self.config.env_config.temp_dir / filename

        try:
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2, default=str)

            self.register_artifact(filepath)
            self.logger.debug(f"Saved JSON artifact to {filepath}")
            return filepath

        except Exception as e:
            self.logger.error(f"Failed to save JSON artifact: {e}")
            raise

    def cleanup_artifacts(self, max_age_days: int | None = None) -> None:
        """Clean up old artifacts."""
        if max_age_days is None:
            max_age_days = self.config.reporting.artifact_retention_days

        cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)
        cleaned_count = 0

        for artifact in self.artifacts[:]:
            try:
                if artifact.exists() and artifact.stat().st_mtime < cutoff_time:
                    artifact.unlink()
                    self.artifacts.remove(artifact)
                    cleaned_count += 1
            except Exception as e:
                self.logger.warning(f"Failed to clean up artifact {artifact}: {e}")

        self.logger.info(f"Cleaned up {cleaned_count} old artifacts")


@contextmanager
def integration_test_context(name: str, config: TestConfig, **context_kwargs):
    """Context manager for test execution with logging and diagnostics."""
    logger = TestLogger(name, config)
    logger.set_context(**context_kwargs)

    start_time = time.time()
    logger.info(f"Starting test context: {name}")

    try:
        yield logger
    except Exception:
        logger.exception(f"Test context {name} failed")
        raise
    finally:
        duration = time.time() - start_time
        logger.info(f"Test context {name} completed in {duration:.2f}s")
        logger.clear_context()


def create_test_error(
    message: str,
    category: str,
    severity: Severity = Severity.HIGH,
    context: dict[str, Any] | None = None,
    suggested_fix: str | None = None,
) -> TestError:
    """Create a structured test error."""
    return TestError(
        category=category,
        severity=severity,
        message=message,
        context=context or {},
        suggested_fix=suggested_fix,
        timestamp=datetime.now(),
    )
