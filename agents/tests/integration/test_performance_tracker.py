"""
Unit tests for the PerformanceTracker class.

Tests performance monitoring, resource tracking, and trend analysis functionality.
"""

import time
import threading
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import pytest

from .performance_tracker import (
    PerformanceTracker, ResourceSnapshot, PerformanceWindow
)
from .models import PerformanceMetrics


class TestResourceSnapshot:
    """Test cases for ResourceSnapshot."""
    
    def test_resource_snapshot_creation(self):
        """Test creating a resource snapshot."""
        timestamp = datetime.now()
        snapshot = ResourceSnapshot(
            timestamp=timestamp,
            cpu_percent=50.0,
            memory_percent=60.0,
            memory_used_mb=1024.0,
            network_bytes_sent=1000,
            network_bytes_recv=2000,
            disk_io_read=500,
            disk_io_write=300
        )
        
        assert snapshot.timestamp == timestamp
        assert snapshot.cpu_percent == 50.0
        assert snapshot.memory_percent == 60.0
        assert snapshot.memory_used_mb == 1024.0
        assert snapshot.network_bytes_sent == 1000
        assert snapshot.network_bytes_recv == 2000
        assert snapshot.disk_io_read == 500
        assert snapshot.disk_io_write == 300


class TestPerformanceWindow:
    """Test cases for PerformanceWindow."""
    
    def test_performance_window_creation(self):
        """Test creating a performance window."""
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=30)
        
        window = PerformanceWindow(
            start_time=start_time,
            end_time=end_time,
            duration=30.0,
            cpu_avg=45.0,
            cpu_peak=80.0,
            memory_avg=55.0,
            memory_peak=75.0,
            network_bytes_sent=1024,
            network_bytes_recv=2048,
            disk_io_read=512,
            disk_io_write=256
        )
        
        assert window.start_time == start_time
        assert window.end_time == end_time
        assert window.duration == 30.0
        assert window.cpu_avg == 45.0
        assert window.cpu_peak == 80.0
        assert window.memory_avg == 55.0
        assert window.memory_peak == 75.0
        assert window.network_bytes_sent == 1024
        assert window.network_bytes_recv == 2048
        assert window.disk_io_read == 512
        assert window.disk_io_write == 256
    
    def test_requests_per_second_calculation(self):
        """Test requests per second calculation."""
        window = PerformanceWindow(
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(seconds=10),
            duration=10.0,
            cpu_avg=50.0,
            cpu_peak=70.0,
            memory_avg=60.0,
            memory_peak=80.0,
            network_bytes_sent=5120,  # 5KB
            network_bytes_recv=10240,  # 10KB
            disk_io_read=0,
            disk_io_write=0
        )
        
        # Total network activity: 15KB = 15 "requests" over 10 seconds = 1.5 RPS
        expected_rps = 15.0 / 10.0
        assert window.requests_per_second == expected_rps
    
    def test_requests_per_second_zero_duration(self):
        """Test requests per second with zero duration."""
        window = PerformanceWindow(
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=0.0,
            cpu_avg=50.0,
            cpu_peak=70.0,
            memory_avg=60.0,
            memory_peak=80.0,
            network_bytes_sent=1024,
            network_bytes_recv=2048,
            disk_io_read=0,
            disk_io_write=0
        )
        
        assert window.requests_per_second == 0.0


class TestPerformanceTracker:
    """Test cases for PerformanceTracker."""
    
    @pytest.fixture
    def tracker(self):
        """Create PerformanceTracker instance."""
        return PerformanceTracker(sampling_interval=0.1, max_samples=10)
    
    @pytest.fixture
    def mock_psutil(self):
        """Mock psutil functions."""
        with patch('agents.tests.integration.performance_tracker.psutil') as mock:
            # Mock CPU usage
            mock.cpu_percent.return_value = 50.0
            
            # Mock memory usage
            mock_memory = Mock()
            mock_memory.percent = 60.0
            mock_memory.used = 1024 * 1024 * 1024  # 1GB
            mock.virtual_memory.return_value = mock_memory
            
            # Mock network I/O
            mock_network = Mock()
            mock_network.bytes_sent = 1000
            mock_network.bytes_recv = 2000
            mock.net_io_counters.return_value = mock_network
            
            # Mock disk I/O
            mock_disk = Mock()
            mock_disk.read_bytes = 500
            mock_disk.write_bytes = 300
            mock.disk_io_counters.return_value = mock_disk
            
            yield mock
    
    def test_tracker_initialization(self, tracker):
        """Test tracker initialization."""
        assert tracker.sampling_interval == 0.1
        assert tracker.max_samples == 10
        assert not tracker.is_tracking
        assert tracker.tracking_thread is None
        assert len(tracker.samples) == 0
        assert tracker.start_time is None
        assert tracker.end_time is None
    
    def test_start_tracking(self, tracker, mock_psutil):
        """Test starting performance tracking."""
        assert not tracker.is_tracking
        
        tracker.start_tracking("test_window")
        
        assert tracker.is_tracking
        assert tracker.current_window == "test_window"
        assert tracker.start_time is not None
        assert tracker.tracking_thread is not None
        assert tracker.tracking_thread.is_alive()
        assert tracker.baseline_snapshot is not None
        
        # Clean up
        tracker.stop_tracking()
    
    def test_stop_tracking(self, tracker, mock_psutil):
        """Test stopping performance tracking."""
        tracker.start_tracking("test_window")
        assert tracker.is_tracking
        
        # Let it collect some samples
        time.sleep(0.3)
        
        window = tracker.stop_tracking()
        
        assert not tracker.is_tracking
        assert tracker.end_time is not None
        assert isinstance(window, PerformanceWindow)
        assert window.duration > 0
        assert "test_window" in tracker.windows
    
    def test_tracking_collects_samples(self, tracker, mock_psutil):
        """Test that tracking collects performance samples."""
        tracker.start_tracking("sample_test")
        
        # Let it collect samples
        time.sleep(0.3)
        
        tracker.stop_tracking()
        
        # Should have collected some samples
        assert len(tracker.samples) > 0
        
        # Check sample content
        sample = tracker.samples[0]
        assert isinstance(sample, ResourceSnapshot)
        assert sample.cpu_percent == 50.0
        assert sample.memory_percent == 60.0
    
    def test_start_phase(self, tracker, mock_psutil):
        """Test starting a specific test phase."""
        tracker.start_phase("setup")
        
        assert tracker.is_tracking
        assert tracker.current_window == "setup"
        
        # Start another phase
        tracker.start_phase("execution")
        
        assert tracker.current_window == "execution"
        assert "setup" in tracker.windows
        
        tracker.stop_tracking()
    
    def test_end_phase(self, tracker, mock_psutil):
        """Test ending a test phase."""
        tracker.start_phase("test_phase")
        
        time.sleep(0.2)
        
        window = tracker.end_phase()
        
        assert not tracker.is_tracking
        assert isinstance(window, PerformanceWindow)
        assert window.duration > 0
    
    def test_get_current_metrics(self, tracker, mock_psutil):
        """Test getting current metrics."""
        # Should return None when not tracking
        assert tracker.get_current_metrics() is None
        
        tracker.start_tracking("current_test")
        
        metrics = tracker.get_current_metrics()
        assert isinstance(metrics, ResourceSnapshot)
        assert metrics.cpu_percent == 50.0
        
        tracker.stop_tracking()
    
    def test_threshold_callbacks(self, tracker, mock_psutil):
        """Test performance threshold callbacks."""
        callback_calls = []
        
        def threshold_callback(metric_name, current_value, threshold):
            callback_calls.append((metric_name, current_value, threshold))
        
        tracker.add_threshold_callback(threshold_callback)
        
        # Mock high CPU usage to trigger threshold
        mock_psutil.cpu_percent.return_value = 85.0
        
        tracker.start_tracking("threshold_test")
        time.sleep(0.2)
        tracker.stop_tracking()
        
        # Should have triggered callback
        assert len(callback_calls) > 0
        assert callback_calls[0][0] == "cpu_percent"
        assert callback_calls[0][1] == 85.0
        assert callback_calls[0][2] == 80.0
    
    def test_get_performance_summary(self, tracker, mock_psutil):
        """Test getting performance summary."""
        # No data initially
        summary = tracker.get_performance_summary()
        assert "message" in summary
        assert "No performance data available" in summary["message"]
        
        # Add some windows
        tracker.start_phase("setup")
        time.sleep(0.1)
        tracker.end_phase()
        
        tracker.start_phase("execution")
        time.sleep(0.1)
        tracker.end_phase()
        
        summary = tracker.get_performance_summary()
        
        assert "total_windows" in summary
        assert "total_duration" in summary
        assert "windows" in summary
        assert summary["total_windows"] == 2
        assert "setup" in summary["windows"]
        assert "execution" in summary["windows"]
    
    def test_create_performance_metrics(self, tracker, mock_psutil):
        """Test creating PerformanceMetrics object."""
        # No data initially
        metrics = tracker.create_performance_metrics()
        assert isinstance(metrics, PerformanceMetrics)
        assert metrics.total_duration == 0.0
        
        # Add some phases
        tracker.start_phase("setup")
        time.sleep(0.1)
        tracker.end_phase()
        
        tracker.start_phase("execution")
        time.sleep(0.1)
        tracker.end_phase()
        
        metrics = tracker.create_performance_metrics()
        
        assert isinstance(metrics, PerformanceMetrics)
        assert metrics.total_duration > 0
        assert metrics.setup_duration > 0
        assert metrics.execution_duration > 0
        assert metrics.memory_peak > 0
        assert metrics.cpu_peak > 0
    
    def test_analyze_trends(self, tracker, mock_psutil):
        """Test trend analysis."""
        # Create window with varying CPU usage
        tracker.start_tracking("trend_test")
        
        # Simulate increasing CPU usage
        for i in range(5):
            mock_psutil.cpu_percent.return_value = 30.0 + i * 10
            time.sleep(0.05)
        
        tracker.stop_tracking()
        
        analysis = tracker.analyze_trends("trend_test")
        
        assert "window" in analysis
        assert "duration" in analysis
        assert "sample_count" in analysis
        assert "cpu_trend" in analysis
        assert "memory_trend" in analysis
        assert "network_activity" in analysis
        
        assert analysis["window"] == "trend_test"
        assert analysis["sample_count"] > 0
    
    def test_analyze_trends_nonexistent_window(self, tracker):
        """Test trend analysis for nonexistent window."""
        analysis = tracker.analyze_trends("nonexistent")
        
        assert "error" in analysis
        assert "not found" in analysis["error"]
    
    def test_analyze_trends_insufficient_data(self, tracker, mock_psutil):
        """Test trend analysis with insufficient data."""
        # Create window with minimal data
        tracker.start_tracking("minimal_test")
        time.sleep(0.05)  # Very short duration
        tracker.stop_tracking()
        
        # Clear most samples to simulate insufficient data
        if len(tracker.windows["minimal_test"].snapshots) > 1:
            tracker.windows["minimal_test"].snapshots = tracker.windows["minimal_test"].snapshots[:1]
        
        analysis = tracker.analyze_trends("minimal_test")
        
        if "error" in analysis:
            assert "Insufficient data" in analysis["error"]
    
    def test_max_samples_limit(self, tracker, mock_psutil):
        """Test that samples are limited to max_samples."""
        tracker.start_tracking("limit_test")
        
        # Let it collect more samples than the limit
        time.sleep(1.5)  # Should collect ~15 samples with 0.1s interval
        
        tracker.stop_tracking()
        
        # Should not exceed max_samples
        assert len(tracker.samples) <= tracker.max_samples
    
    def test_context_manager(self, tracker, mock_psutil):
        """Test tracker as context manager."""
        with tracker as t:
            t.start_tracking("context_test")
            time.sleep(0.1)
        
        # Should stop tracking when exiting context
        assert not tracker.is_tracking
    
    def test_tracking_thread_error_handling(self, tracker):
        """Test error handling in tracking thread."""
        # Mock psutil to raise exception
        with patch('agents.tests.integration.performance_tracker.psutil.cpu_percent', side_effect=Exception("Test error")):
            tracker.start_tracking("error_test")
            time.sleep(0.2)
            tracker.stop_tracking()
        
        # Should handle errors gracefully and continue
        assert not tracker.is_tracking
    
    def test_take_snapshot_error_handling(self, tracker):
        """Test error handling in _take_snapshot."""
        # Mock psutil to raise exception
        with patch('agents.tests.integration.performance_tracker.psutil.cpu_percent', side_effect=Exception("Test error")):
            snapshot = tracker._take_snapshot()
        
        # Should return empty snapshot on error
        assert isinstance(snapshot, ResourceSnapshot)
        assert snapshot.cpu_percent == 0.0
        assert snapshot.memory_percent == 0.0
    
    def test_calculate_trend_directions(self, tracker):
        """Test trend direction calculations."""
        # Test increasing trend
        increasing_values = [10.0, 20.0, 30.0, 40.0, 50.0]
        trend = tracker._calculate_trend(increasing_values)
        assert trend == "increasing"
        
        # Test decreasing trend
        decreasing_values = [50.0, 40.0, 30.0, 20.0, 10.0]
        trend = tracker._calculate_trend(decreasing_values)
        assert trend == "decreasing"
        
        # Test stable trend
        stable_values = [30.0, 31.0, 29.0, 30.5, 30.2]
        trend = tracker._calculate_trend(stable_values)
        assert trend == "stable"
        
        # Test insufficient data
        single_value = [30.0]
        trend = tracker._calculate_trend(single_value)
        assert trend == "stable"
    
    def test_network_delta_calculation(self, tracker, mock_psutil):
        """Test network usage delta calculation."""
        # Set initial network stats
        mock_psutil.net_io_counters.return_value.bytes_sent = 1000
        mock_psutil.net_io_counters.return_value.bytes_recv = 2000
        
        tracker.start_tracking("network_test")
        
        # Change network stats
        mock_psutil.net_io_counters.return_value.bytes_sent = 2000
        mock_psutil.net_io_counters.return_value.bytes_recv = 3000
        
        time.sleep(0.1)
        window = tracker.stop_tracking()
        
        # Should calculate delta correctly
        assert window.network_bytes_sent == 1000  # 2000 - 1000
        assert window.network_bytes_recv == 1000  # 3000 - 2000
    
    @patch('agents.tests.integration.performance_tracker.psutil.disk_io_counters', return_value=None)
    def test_disk_io_unavailable(self, mock_disk, tracker, mock_psutil):
        """Test handling when disk I/O counters are unavailable."""
        snapshot = tracker._take_snapshot()
        
        assert snapshot.disk_io_read == 0
        assert snapshot.disk_io_write == 0


if __name__ == "__main__":
    pytest.main([__file__])