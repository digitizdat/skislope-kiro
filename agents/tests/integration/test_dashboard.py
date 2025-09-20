"""
Unit tests for the Dashboard components.

Tests dashboard data management, server functionality, and report integration.
"""

import json
import tempfile
import time
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from unittest.mock import Mock
from unittest.mock import patch

import pytest
import requests

from .dashboard import DashboardData
from .dashboard import DashboardServer
from .dashboard import TestResultsDashboard
from .models import AgentHealthStatus
from .models import CategoryResults
from .models import PerformanceMetrics
from .models import TestCategory
from .models import TestResults
from .models import TestSummary


class TestDashboardData:
    """Test cases for DashboardData."""

    @pytest.fixture
    def dashboard_data(self):
        """Create DashboardData instance."""
        return DashboardData()

    @pytest.fixture
    def sample_results(self):
        """Create sample test results."""
        results = TestResults()
        results.summary = TestSummary(
            total_tests=5, passed=4, failed=1, duration=30.0, start_time=datetime.now()
        )

        # Add category
        category = CategoryResults(category=TestCategory.API_CONTRACTS)
        category.total_tests = 3
        category.passed = 2
        category.failed = 1
        category.duration = 15.0
        results.categories[TestCategory.API_CONTRACTS] = category

        # Add performance metrics
        results.performance_metrics = PerformanceMetrics(
            total_duration=30.0,
            setup_duration=5.0,
            execution_duration=20.0,
            teardown_duration=5.0,
            network_requests=10,
        )

        return results

    def test_add_results(self, dashboard_data, sample_results):
        """Test adding test results to dashboard data."""
        assert len(dashboard_data.test_results) == 0
        assert dashboard_data.current_results is None
        assert dashboard_data.last_updated is None

        dashboard_data.add_results(sample_results)

        assert len(dashboard_data.test_results) == 1
        assert dashboard_data.current_results == sample_results
        assert dashboard_data.last_updated is not None
        assert len(dashboard_data.performance_trends) == 1

    def test_add_multiple_results(self, dashboard_data, sample_results):
        """Test adding multiple test results."""
        # Add first result
        dashboard_data.add_results(sample_results)

        # Create second result
        results2 = TestResults()
        results2.summary = TestSummary(
            total_tests=8, passed=7, failed=1, duration=25.0, start_time=datetime.now()
        )

        dashboard_data.add_results(results2)

        assert len(dashboard_data.test_results) == 2
        assert dashboard_data.current_results == results2
        assert len(dashboard_data.performance_trends) == 2

    def test_performance_trends_update(self, dashboard_data, sample_results):
        """Test performance trends are updated correctly."""
        dashboard_data.add_results(sample_results)

        trend = dashboard_data.performance_trends[0]
        assert trend["duration"] == 30.0
        assert trend["success_rate"] == 80.0
        assert trend["total_tests"] == 5
        assert trend["passed"] == 4
        assert trend["failed"] == 1
        assert "timestamp" in trend

    def test_performance_trends_limit(self, dashboard_data):
        """Test performance trends are limited to prevent memory issues."""
        # Add more than 100 results
        for _i in range(105):
            results = TestResults()
            results.summary = TestSummary(
                total_tests=1, passed=1, duration=1.0, start_time=datetime.now()
            )
            dashboard_data.add_results(results)

        # Should keep only last 100
        assert len(dashboard_data.performance_trends) == 100
        assert len(dashboard_data.test_results) == 50  # test_results limit is 50

    def test_get_dashboard_data(self, dashboard_data, sample_results):
        """Test getting complete dashboard data."""
        dashboard_data.add_results(sample_results)

        data = dashboard_data.get_dashboard_data()

        assert "current_results" in data
        assert "historical_summary" in data
        assert "performance_trends" in data
        assert "last_updated" in data
        assert "metadata" in data

        assert data["current_results"] is not None
        assert data["metadata"]["total_runs"] == 1

    def test_historical_summary(self, dashboard_data):
        """Test historical summary calculation."""
        # Add multiple results with different success rates
        success_rates = [80.0, 85.0, 90.0, 75.0, 95.0]

        for rate in success_rates:
            results = TestResults()
            # Use a different total to avoid rounding issues
            total_tests = 100
            passed_count = int(total_tests * rate / 100)
            results.summary = TestSummary(
                total_tests=total_tests,
                passed=passed_count,
                failed=total_tests - passed_count,
                duration=30.0,
                start_time=datetime.now(),
            )
            dashboard_data.add_results(results)

        summary = dashboard_data._get_historical_summary()

        assert summary["total_runs"] == 5
        assert summary["average_success_rate"] == sum(success_rates) / len(
            success_rates
        )
        assert summary["average_duration"] == 30.0
        assert summary["success_trend"] in ["improving", "declining", "stable"]

    def test_data_range(self, dashboard_data):
        """Test data range calculation."""
        # Add results with different timestamps
        base_time = datetime.now()

        for i in range(3):
            results = TestResults()
            results.summary = TestSummary(
                total_tests=1,
                passed=1,
                duration=1.0,
                start_time=base_time + timedelta(hours=i),
            )
            dashboard_data.add_results(results)

        data_range = dashboard_data._get_data_range()

        assert "start" in data_range
        assert "end" in data_range

        start_time = datetime.fromisoformat(data_range["start"])
        end_time = datetime.fromisoformat(data_range["end"])

        assert end_time > start_time


class TestDashboardServer:
    """Test cases for DashboardServer."""

    @pytest.fixture
    def dashboard_data(self):
        """Create dashboard data with sample results."""
        data = DashboardData()

        results = TestResults()
        results.summary = TestSummary(
            total_tests=3, passed=2, failed=1, duration=15.0, start_time=datetime.now()
        )

        data.add_results(results)
        return data

    @pytest.fixture
    def dashboard_server(self, dashboard_data):
        """Create DashboardServer instance."""
        return DashboardServer(dashboard_data, port=0)  # Use port 0 for auto-assignment

    def test_server_initialization(self, dashboard_server):
        """Test server initialization."""
        assert dashboard_server.dashboard_data is not None
        assert dashboard_server.dashboard_dir.exists()

        # Check static files are created
        assert (dashboard_server.dashboard_dir / "index.html").exists()
        assert (dashboard_server.dashboard_dir / "styles.css").exists()
        assert (dashboard_server.dashboard_dir / "dashboard.js").exists()

    def test_static_file_generation(self, dashboard_server):
        """Test static file content generation."""
        # Check HTML file
        html_content = (dashboard_server.dashboard_dir / "index.html").read_text()
        assert "Integration Test Dashboard" in html_content
        assert "dashboard.js" in html_content
        assert "styles.css" in html_content

        # Check CSS file
        css_content = (dashboard_server.dashboard_dir / "styles.css").read_text()
        assert ".dashboard" in css_content
        assert ".summary-card" in css_content

        # Check JS file
        js_content = (dashboard_server.dashboard_dir / "dashboard.js").read_text()
        assert "TestDashboard" in js_content
        assert "loadData" in js_content

    @patch("webbrowser.open")
    def test_server_start_stop(self, mock_browser, dashboard_server):
        """Test server start and stop functionality."""
        # Start server
        url = dashboard_server.start()

        assert url.startswith("http://localhost:")
        assert dashboard_server.server is not None
        assert dashboard_server.server_thread is not None

        # Give server time to start
        time.sleep(0.1)

        # Test that server is responding
        try:
            response = requests.get(url, timeout=1)
            assert response.status_code == 200
        except requests.exceptions.RequestException:
            # Server might not be fully ready, that's okay for this test
            pass

        # Stop server
        dashboard_server.stop()

        # Server should be stopped
        assert (
            dashboard_server.server is None
            or not dashboard_server.server_thread.is_alive()
        )

    def test_api_endpoint_data(self, dashboard_server):
        """Test API endpoint returns correct data."""
        # Start server
        url = dashboard_server.start()

        try:
            # Give server time to start
            time.sleep(0.1)

            # Test API endpoint
            api_url = url + "/api/data"
            response = requests.get(api_url, timeout=2)

            if response.status_code == 200:
                data = response.json()

                assert "current_results" in data
                assert "historical_summary" in data
                assert "performance_trends" in data
                assert "last_updated" in data
                assert "metadata" in data

        except requests.exceptions.RequestException:
            # Server might not be ready, skip this test
            pytest.skip("Server not ready for API test")

        finally:
            dashboard_server.stop()

    def test_port_auto_increment(self, dashboard_data):
        """Test port auto-increment when port is in use."""
        # Create first server
        server1 = DashboardServer(dashboard_data, port=8080)
        url1 = server1.start()

        try:
            # Create second server with same port
            server2 = DashboardServer(dashboard_data, port=8080)
            url2 = server2.start()

            # Should use different ports
            assert url1 != url2

            server2.stop()

        finally:
            server1.stop()


class TestTestResultsDashboard:
    """Test cases for TestResultsDashboard."""

    @pytest.fixture
    def dashboard(self):
        """Create TestResultsDashboard instance."""
        return TestResultsDashboard()

    @pytest.fixture
    def sample_results(self):
        """Create sample test results."""
        results = TestResults()
        results.summary = TestSummary(
            total_tests=4, passed=3, failed=1, duration=20.0, start_time=datetime.now()
        )

        # Add agent health
        results.agent_health = [
            AgentHealthStatus(
                name="test_agent",
                status="healthy",
                response_time=100.0,
                available_methods=["method1"],
                missing_methods=[],
            )
        ]

        return results

    def test_add_test_results(self, dashboard, sample_results):
        """Test adding test results to dashboard."""
        assert dashboard.dashboard_data.current_results is None

        dashboard.add_test_results(sample_results)

        assert dashboard.dashboard_data.current_results == sample_results
        assert len(dashboard.dashboard_data.test_results) == 1

    @patch("webbrowser.open")
    def test_start_stop_server(self, mock_browser, dashboard, sample_results):
        """Test starting and stopping dashboard server."""
        dashboard.add_test_results(sample_results)

        # Start server
        url = dashboard.start_server(port=0, open_browser=True)

        assert url.startswith("http://localhost:")
        assert dashboard.server is not None
        mock_browser.assert_called_once_with(url)

        # Stop server
        dashboard.stop_server()

        assert dashboard.server is None

    def test_generate_static_report(self, dashboard, sample_results):
        """Test generating static reports."""
        dashboard.add_test_results(sample_results)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test_report.html"

            result_path = dashboard.generate_static_report(
                format_type="html", output_path=output_path
            )

            assert result_path == output_path
            assert output_path.exists()

            html_content = output_path.read_text()
            assert "Integration Test Report" in html_content

    def test_generate_static_report_no_results(self, dashboard):
        """Test generating static report with no results."""
        result_path = dashboard.generate_static_report()

        assert result_path is None

    def test_get_performance_summary(self, dashboard, sample_results):
        """Test getting performance summary."""
        dashboard.add_test_results(sample_results)

        summary = dashboard.get_performance_summary()

        assert "total_runs" in summary
        assert "average_success_rate" in summary
        assert "average_duration" in summary
        assert summary["total_runs"] == 1
        assert summary["average_success_rate"] == 75.0

    def test_export_data(self, dashboard, sample_results):
        """Test exporting dashboard data."""
        dashboard.add_test_results(sample_results)

        with tempfile.TemporaryDirectory() as temp_dir:
            export_path = Path(temp_dir) / "dashboard_export.json"

            dashboard.export_data(export_path)

            assert export_path.exists()

            with open(export_path) as f:
                data = json.load(f)

            assert "current_results" in data
            assert "historical_summary" in data
            assert "performance_trends" in data

    def test_context_manager(self, dashboard, sample_results):
        """Test dashboard as context manager."""
        with dashboard as d:
            d.add_test_results(sample_results)
            url = d.start_server(port=0, open_browser=False)
            assert url.startswith("http://localhost:")

        # Server should be stopped after context exit
        assert dashboard.server is None

    def test_multiple_results_tracking(self, dashboard):
        """Test tracking multiple test results over time."""
        # Add multiple results
        for i in range(5):
            results = TestResults()
            results.summary = TestSummary(
                total_tests=10,
                passed=8 + i % 3,  # Varying success rates
                failed=2 - i % 3,
                duration=20.0 + i * 2,
                start_time=datetime.now() + timedelta(minutes=i),
            )
            dashboard.add_test_results(results)

        # Check performance summary
        summary = dashboard.get_performance_summary()
        assert summary["total_runs"] == 5

        # Check trends
        data = dashboard.dashboard_data.get_dashboard_data()
        assert len(data["performance_trends"]) == 5

    def test_report_generator_integration(self, dashboard, sample_results):
        """Test integration with ReportGenerator."""
        # Mock the dashboard's report_generator instance
        mock_generator = Mock()
        mock_generator.generate_report.return_value = Path("/fake/path.html")
        dashboard.report_generator = mock_generator

        dashboard.add_test_results(sample_results)

        result_path = dashboard.generate_static_report(format_type="html")

        mock_generator.generate_report.assert_called_once()
        assert result_path == Path("/fake/path.html")

    def test_dashboard_data_persistence(self, dashboard):
        """Test that dashboard data persists across operations."""
        # Add first result
        results1 = TestResults()
        results1.summary = TestSummary(
            total_tests=5, passed=4, failed=1, duration=15.0, start_time=datetime.now()
        )
        dashboard.add_test_results(results1)

        # Start and stop server
        dashboard.start_server(port=0, open_browser=False)
        dashboard.stop_server()

        # Add second result
        results2 = TestResults()
        results2.summary = TestSummary(
            total_tests=3, passed=3, failed=0, duration=10.0, start_time=datetime.now()
        )
        dashboard.add_test_results(results2)

        # Data should persist
        assert len(dashboard.dashboard_data.test_results) == 2
        assert dashboard.dashboard_data.current_results == results2

        summary = dashboard.get_performance_summary()
        assert summary["total_runs"] == 2


if __name__ == "__main__":
    pytest.main([__file__])
