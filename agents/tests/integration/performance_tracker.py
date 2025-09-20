"""
Performance Metrics Tracker.

Tracks and analyzes performance metrics for integration tests,
including response times, resource usage, and trend analysis.
"""

import statistics
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from typing import Any

import psutil
import structlog

from .models import PerformanceMetrics

logger = structlog.get_logger(__name__)


@dataclass
class ResourceSnapshot:
    """Snapshot of system resources at a point in time."""

    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    network_bytes_sent: int
    network_bytes_recv: int
    disk_io_read: int
    disk_io_write: int


@dataclass
class PerformanceWindow:
    """Performance metrics for a time window."""

    start_time: datetime
    end_time: datetime
    duration: float
    cpu_avg: float
    cpu_peak: float
    memory_avg: float
    memory_peak: float
    network_bytes_sent: int
    network_bytes_recv: int
    disk_io_read: int
    disk_io_write: int
    snapshots: list[ResourceSnapshot] = field(default_factory=list)

    @property
    def requests_per_second(self) -> float:
        """Calculate requests per second (if network activity is proxy for requests)."""
        if self.duration > 0:
            # Rough estimate based on network activity
            total_requests = (
                self.network_bytes_sent + self.network_bytes_recv
            ) / 1024  # KB as proxy
            return total_requests / self.duration
        return 0.0


class PerformanceTracker:
    """
    Tracks performance metrics during test execution.

    Monitors CPU, memory, network, and disk I/O usage with configurable
    sampling intervals and provides trend analysis capabilities.
    """

    def __init__(self, sampling_interval: float = 1.0, max_samples: int = 1000):
        """
        Initialize the performance tracker.

        Args:
            sampling_interval: Interval between samples in seconds
            max_samples: Maximum number of samples to keep in memory
        """
        self.sampling_interval = sampling_interval
        self.max_samples = max_samples
        self.logger = structlog.get_logger(__name__)

        # Tracking state
        self.is_tracking = False
        self.tracking_thread: threading.Thread | None = None
        self.samples: deque = deque(maxlen=max_samples)
        self.start_time: datetime | None = None
        self.end_time: datetime | None = None

        # Baseline measurements
        self.baseline_snapshot: ResourceSnapshot | None = None

        # Performance windows for different phases
        self.windows: dict[str, PerformanceWindow] = {}
        self.current_window: str | None = None

        # Network counters (for tracking test-related network activity)
        self.initial_network_stats: dict[str, int] | None = None

        # Callbacks for performance events
        self.threshold_callbacks: list[Callable[[str, float, float], None]] = []

    def start_tracking(self, window_name: str = "default") -> None:
        """
        Start performance tracking.

        Args:
            window_name: Name for the performance window
        """
        if self.is_tracking:
            self.logger.warning("Performance tracking already active")
            return

        self.logger.info(f"Starting performance tracking for window: {window_name}")

        self.is_tracking = True
        self.start_time = datetime.now()
        self.current_window = window_name
        self.samples.clear()

        # Take baseline snapshot
        self.baseline_snapshot = self._take_snapshot()
        self.initial_network_stats = self._get_network_stats()

        # Start tracking thread
        self.tracking_thread = threading.Thread(target=self._tracking_loop, daemon=True)
        self.tracking_thread.start()

    def stop_tracking(self) -> PerformanceWindow:
        """
        Stop performance tracking and return metrics.

        Returns:
            Performance metrics for the tracking period
        """
        if not self.is_tracking:
            self.logger.warning("Performance tracking not active")
            return self._create_empty_window()

        self.logger.info(
            f"Stopping performance tracking for window: {self.current_window}"
        )

        self.is_tracking = False
        self.end_time = datetime.now()

        # Wait for tracking thread to finish
        if self.tracking_thread and self.tracking_thread.is_alive():
            self.tracking_thread.join(timeout=2.0)

        # Create performance window
        window = self._create_performance_window()

        if self.current_window:
            self.windows[self.current_window] = window

        return window

    def start_phase(self, phase_name: str) -> None:
        """
        Start tracking a specific test phase.

        Args:
            phase_name: Name of the test phase
        """
        if not self.is_tracking:
            self.start_tracking(phase_name)
        else:
            # End current phase and start new one
            if self.current_window:
                self.stop_tracking()
            self.start_tracking(phase_name)

    def end_phase(self) -> PerformanceWindow | None:
        """
        End the current test phase.

        Returns:
            Performance metrics for the phase
        """
        if self.is_tracking:
            return self.stop_tracking()
        return None

    def add_threshold_callback(
        self, callback: Callable[[str, float, float], None]
    ) -> None:
        """
        Add a callback for performance threshold violations.

        Args:
            callback: Function called with (metric_name, current_value, threshold)
        """
        self.threshold_callbacks.append(callback)

    def get_current_metrics(self) -> ResourceSnapshot | None:
        """
        Get current resource usage snapshot.

        Returns:
            Current resource snapshot or None if not tracking
        """
        if not self.is_tracking:
            return None

        return self._take_snapshot()

    def get_performance_summary(self) -> dict[str, Any]:
        """
        Get summary of all performance windows.

        Returns:
            Performance summary across all windows
        """
        if not self.windows:
            return {"message": "No performance data available"}

        summary = {
            "total_windows": len(self.windows),
            "total_duration": sum(w.duration for w in self.windows.values()),
            "windows": {},
        }

        for name, window in self.windows.items():
            summary["windows"][name] = {
                "duration": window.duration,
                "cpu_avg": window.cpu_avg,
                "cpu_peak": window.cpu_peak,
                "memory_avg": window.memory_avg,
                "memory_peak": window.memory_peak,
                "network_sent_mb": window.network_bytes_sent / (1024 * 1024),
                "network_recv_mb": window.network_bytes_recv / (1024 * 1024),
                "requests_per_second": window.requests_per_second,
            }

        # Calculate overall statistics
        if len(self.windows) > 1:
            all_cpu_avg = [w.cpu_avg for w in self.windows.values()]
            all_memory_avg = [w.memory_avg for w in self.windows.values()]

            summary["overall"] = {
                "cpu_avg": statistics.mean(all_cpu_avg),
                "cpu_peak": max(w.cpu_peak for w in self.windows.values()),
                "memory_avg": statistics.mean(all_memory_avg),
                "memory_peak": max(w.memory_peak for w in self.windows.values()),
                "total_network_mb": sum(
                    (w.network_bytes_sent + w.network_bytes_recv) / (1024 * 1024)
                    for w in self.windows.values()
                ),
            }

        return summary

    def create_performance_metrics(self) -> PerformanceMetrics:
        """
        Create PerformanceMetrics object from tracked data.

        Returns:
            PerformanceMetrics object for test results
        """
        if not self.windows:
            return PerformanceMetrics(
                total_duration=0.0,
                setup_duration=0.0,
                execution_duration=0.0,
                teardown_duration=0.0,
            )

        # Map common window names to metrics fields
        setup_duration = self.windows.get(
            "setup", self.windows.get("environment", None)
        )
        execution_duration = self.windows.get(
            "execution", self.windows.get("tests", None)
        )
        teardown_duration = self.windows.get(
            "teardown", self.windows.get("cleanup", None)
        )

        total_duration = sum(w.duration for w in self.windows.values())

        # Calculate overall resource usage
        all_windows = list(self.windows.values())
        if all_windows:
            memory_peak = max(w.memory_peak for w in all_windows)
            memory_avg = statistics.mean([w.memory_avg for w in all_windows])
            cpu_peak = max(w.cpu_peak for w in all_windows)
            cpu_avg = statistics.mean([w.cpu_avg for w in all_windows])

            total_network_sent = sum(w.network_bytes_sent for w in all_windows)
            total_network_recv = sum(w.network_bytes_recv for w in all_windows)
        else:
            memory_peak = memory_avg = cpu_peak = cpu_avg = 0.0
            total_network_sent = total_network_recv = 0

        return PerformanceMetrics(
            total_duration=total_duration,
            setup_duration=setup_duration.duration if setup_duration else 0.0,
            execution_duration=execution_duration.duration
            if execution_duration
            else total_duration,
            teardown_duration=teardown_duration.duration if teardown_duration else 0.0,
            memory_peak=memory_peak,
            memory_average=memory_avg,
            cpu_peak=cpu_peak,
            cpu_average=cpu_avg,
            network_requests=0,  # Would need to be tracked separately
            network_bytes_sent=total_network_sent,
            network_bytes_received=total_network_recv,
        )

    def analyze_trends(self, window_name: str) -> dict[str, Any]:
        """
        Analyze performance trends for a specific window.

        Args:
            window_name: Name of the window to analyze

        Returns:
            Trend analysis results
        """
        if window_name not in self.windows:
            return {"error": f"Window '{window_name}' not found"}

        window = self.windows[window_name]

        if len(window.snapshots) < 2:
            return {"error": "Insufficient data for trend analysis"}

        # Analyze CPU trend
        cpu_values = [s.cpu_percent for s in window.snapshots]
        cpu_trend = self._calculate_trend(cpu_values)

        # Analyze memory trend
        memory_values = [s.memory_percent for s in window.snapshots]
        memory_trend = self._calculate_trend(memory_values)

        # Analyze network activity
        [s.network_bytes_sent for s in window.snapshots]
        [s.network_bytes_recv for s in window.snapshots]

        return {
            "window": window_name,
            "duration": window.duration,
            "sample_count": len(window.snapshots),
            "cpu_trend": {
                "direction": cpu_trend,
                "avg": window.cpu_avg,
                "peak": window.cpu_peak,
                "variance": statistics.variance(cpu_values)
                if len(cpu_values) > 1
                else 0,
            },
            "memory_trend": {
                "direction": memory_trend,
                "avg": window.memory_avg,
                "peak": window.memory_peak,
                "variance": statistics.variance(memory_values)
                if len(memory_values) > 1
                else 0,
            },
            "network_activity": {
                "total_sent_mb": window.network_bytes_sent / (1024 * 1024),
                "total_recv_mb": window.network_bytes_recv / (1024 * 1024),
                "avg_throughput_mbps": (
                    (window.network_bytes_sent + window.network_bytes_recv)
                    / (1024 * 1024 * window.duration)
                )
                if window.duration > 0
                else 0,
            },
        }

    def _tracking_loop(self) -> None:
        """Main tracking loop running in separate thread."""
        while self.is_tracking:
            try:
                snapshot = self._take_snapshot()
                self.samples.append(snapshot)

                # Check thresholds
                self._check_thresholds(snapshot)

                time.sleep(self.sampling_interval)

            except Exception as e:
                self.logger.error(f"Error in performance tracking loop: {e}")
                time.sleep(self.sampling_interval)

    def _take_snapshot(self) -> ResourceSnapshot:
        """Take a snapshot of current system resources."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=None)

            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_mb = memory.used / (1024 * 1024)

            # Network I/O
            network = psutil.net_io_counters()
            network_sent = network.bytes_sent
            network_recv = network.bytes_recv

            # Disk I/O
            disk = psutil.disk_io_counters()
            disk_read = disk.read_bytes if disk else 0
            disk_write = disk.write_bytes if disk else 0

            return ResourceSnapshot(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_used_mb=memory_used_mb,
                network_bytes_sent=network_sent,
                network_bytes_recv=network_recv,
                disk_io_read=disk_read,
                disk_io_write=disk_write,
            )

        except Exception as e:
            self.logger.error(f"Failed to take resource snapshot: {e}")
            # Return empty snapshot
            return ResourceSnapshot(
                timestamp=datetime.now(),
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_used_mb=0.0,
                network_bytes_sent=0,
                network_bytes_recv=0,
                disk_io_read=0,
                disk_io_write=0,
            )

    def _get_network_stats(self) -> dict[str, int]:
        """Get current network statistics."""
        try:
            network = psutil.net_io_counters()
            return {"bytes_sent": network.bytes_sent, "bytes_recv": network.bytes_recv}
        except Exception:
            return {"bytes_sent": 0, "bytes_recv": 0}

    def _create_performance_window(self) -> PerformanceWindow:
        """Create a performance window from collected samples."""
        if not self.samples or not self.start_time or not self.end_time:
            return self._create_empty_window()

        duration = (self.end_time - self.start_time).total_seconds()

        # Calculate statistics
        cpu_values = [s.cpu_percent for s in self.samples]
        memory_values = [s.memory_percent for s in self.samples]

        cpu_avg = statistics.mean(cpu_values) if cpu_values else 0.0
        cpu_peak = max(cpu_values) if cpu_values else 0.0
        memory_avg = statistics.mean(memory_values) if memory_values else 0.0
        memory_peak = max(memory_values) if memory_values else 0.0

        # Calculate network delta
        if self.samples and self.initial_network_stats:
            final_snapshot = self.samples[-1]
            network_sent = (
                final_snapshot.network_bytes_sent
                - self.initial_network_stats["bytes_sent"]
            )
            network_recv = (
                final_snapshot.network_bytes_recv
                - self.initial_network_stats["bytes_recv"]
            )
        else:
            network_sent = network_recv = 0

        # Calculate disk I/O delta
        if self.samples and self.baseline_snapshot:
            final_snapshot = self.samples[-1]
            disk_read = (
                final_snapshot.disk_io_read - self.baseline_snapshot.disk_io_read
            )
            disk_write = (
                final_snapshot.disk_io_write - self.baseline_snapshot.disk_io_write
            )
        else:
            disk_read = disk_write = 0

        return PerformanceWindow(
            start_time=self.start_time,
            end_time=self.end_time,
            duration=duration,
            cpu_avg=cpu_avg,
            cpu_peak=cpu_peak,
            memory_avg=memory_avg,
            memory_peak=memory_peak,
            network_bytes_sent=max(0, network_sent),
            network_bytes_recv=max(0, network_recv),
            disk_io_read=max(0, disk_read),
            disk_io_write=max(0, disk_write),
            snapshots=list(self.samples),
        )

    def _create_empty_window(self) -> PerformanceWindow:
        """Create an empty performance window."""
        now = datetime.now()
        return PerformanceWindow(
            start_time=now,
            end_time=now,
            duration=0.0,
            cpu_avg=0.0,
            cpu_peak=0.0,
            memory_avg=0.0,
            memory_peak=0.0,
            network_bytes_sent=0,
            network_bytes_recv=0,
            disk_io_read=0,
            disk_io_write=0,
        )

    def _check_thresholds(self, snapshot: ResourceSnapshot) -> None:
        """Check if any performance thresholds are exceeded."""
        thresholds = {"cpu_percent": 80.0, "memory_percent": 85.0}

        for metric, threshold in thresholds.items():
            value = getattr(snapshot, metric, 0.0)
            if value > threshold:
                for callback in self.threshold_callbacks:
                    try:
                        callback(metric, value, threshold)
                    except Exception as e:
                        self.logger.error(f"Error in threshold callback: {e}")

    def _calculate_trend(self, values: list[float]) -> str:
        """
        Calculate trend direction from a series of values.

        Args:
            values: List of numeric values

        Returns:
            Trend direction: 'increasing', 'decreasing', or 'stable'
        """
        if len(values) < 2:
            return "stable"

        # Simple linear regression to determine trend
        n = len(values)
        x = list(range(n))

        # Calculate slope
        x_mean = statistics.mean(x)
        y_mean = statistics.mean(values)

        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return "stable"

        slope = numerator / denominator

        # Determine trend based on slope
        if slope > 0.1:
            return "increasing"
        elif slope < -0.1:
            return "decreasing"
        else:
            return "stable"

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.is_tracking:
            self.stop_tracking()
