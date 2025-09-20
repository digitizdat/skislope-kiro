"""
Unit tests for the ReportGenerator class.

Tests report generation in multiple formats (JSON, HTML, JUnit, Markdown)
with various test result scenarios and configurations.
"""

import json
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

from .report_generator import ReportGenerator, ReportFormat
from .models import (
    TestResults, TestResult, TestCategory, TestStatus, TestSummary,
    CategoryResults, PerformanceMetrics, TestError, Severity,
    AgentHealthStatus, EnvironmentIssue
)
from .config import TestConfig


class TestReportGenerator:
    """Test cases for ReportGenerator."""
    
    @pytest.fixture
    def sample_test_results(self):
        """Create sample test results for testing."""
        results = TestResults()
        
        # Create summary
        results.summary = TestSummary(
            total_tests=10,
            passed=7,
            failed=2,
            skipped=1,
            errors=0,
            duration=45.5,
            start_time=datetime.now() - timedelta(minutes=1),
            end_time=datetime.now()
        )
        
        # Create category results
        api_category = CategoryResults(category=TestCategory.API_CONTRACTS)
        api_category.total_tests = 5
        api_category.passed = 4
        api_category.failed = 1
        api_category.duration = 20.0
        
        # Add some test results to category
        passed_test = TestResult(
            name="API Contract - Hill Metrics",
            category=TestCategory.API_CONTRACTS,
            status=TestStatus.PASSED,
            duration=5.0,
            message="All API methods validated successfully"
        )
        
        failed_test = TestResult(
            name="API Contract - Weather Service",
            category=TestCategory.API_CONTRACTS,
            status=TestStatus.FAILED,
            duration=3.0
        )
        failed_test.error = TestError(
            category="api_contracts",
            severity=Severity.HIGH,
            message="Missing method: get_forecast",
            suggested_fix="Implement get_forecast method in weather agent"
        )
        
        api_category.tests = [passed_test, failed_test]
        results.categories[TestCategory.API_CONTRACTS] = api_category
        
        # Add environment category
        env_category = CategoryResults(category=TestCategory.ENVIRONMENT)
        env_category.total_tests = 3
        env_category.passed = 2
        env_category.skipped = 1
        env_category.duration = 10.0
        
        skipped_test = TestResult(
            name="SSL Certificate Validation",
            category=TestCategory.ENVIRONMENT,
            status=TestStatus.SKIPPED,
            duration=0.0,
            message="SSL validation skipped in test environment"
        )
        env_category.tests = [skipped_test]
        results.categories[TestCategory.ENVIRONMENT] = env_category
        
        # Add agent health
        results.agent_health = [
            AgentHealthStatus(
                name="hill_metrics",
                status="healthy",
                response_time=150.0,
                available_methods=["get_elevation", "get_slope"],
                missing_methods=[]
            ),
            AgentHealthStatus(
                name="weather",
                status="degraded",
                response_time=500.0,
                available_methods=["get_current"],
                missing_methods=["get_forecast"]
            )
        ]
        
        # Add environment issues
        results.environment_issues = [
            EnvironmentIssue(
                component="python_packages",
                issue_type="missing_dependency",
                description="Package 'shapely' not found",
                severity=Severity.HIGH,
                suggested_fix="Run 'uv add shapely' to install missing package"
            )
        ]
        
        # Add performance metrics
        results.performance_metrics = PerformanceMetrics(
            total_duration=45.5,
            setup_duration=5.0,
            execution_duration=35.0,
            teardown_duration=5.5,
            memory_peak=512.0,
            memory_average=256.0,
            cpu_peak=75.0,
            cpu_average=45.0,
            network_requests=25,
            network_bytes_sent=1024000,
            network_bytes_received=2048000
        )
        
        return results
    
    @pytest.fixture
    def report_generator(self):
        """Create ReportGenerator instance."""
        return ReportGenerator()
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test outputs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    def test_generate_json_report(self, report_generator, sample_test_results, temp_dir):
        """Test JSON report generation."""
        output_path = temp_dir / "test_report.json"
        
        result_path = report_generator.generate_report(
            results=sample_test_results,
            format_type=ReportFormat.JSON,
            output_path=output_path,
            include_diagnostics=True
        )
        
        assert result_path == output_path
        assert output_path.exists()
        
        # Verify JSON content
        with open(output_path) as f:
            data = json.load(f)
        
        assert "metadata" in data
        assert "summary" in data
        assert "categories" in data
        assert "agent_health" in data
        assert "environment_issues" in data
        assert "performance_metrics" in data
        
        # Verify summary data
        assert data["summary"]["total_tests"] == 10
        assert data["summary"]["passed"] == 7
        assert data["summary"]["failed"] == 2
        assert data["summary"]["success_rate"] == 70.0
        
        # Verify categories
        assert "api_contracts" in data["categories"]
        assert data["categories"]["api_contracts"]["total_tests"] == 5
        
        # Verify agent health
        assert len(data["agent_health"]) == 2
        assert data["agent_health"][0]["name"] == "hill_metrics"
        assert data["agent_health"][0]["status"] == "healthy"
    
    def test_generate_html_report(self, report_generator, sample_test_results, temp_dir):
        """Test HTML report generation."""
        output_path = temp_dir / "test_report.html"
        
        result_path = report_generator.generate_report(
            results=sample_test_results,
            format_type=ReportFormat.HTML,
            output_path=output_path,
            include_diagnostics=True
        )
        
        assert result_path == output_path
        assert output_path.exists()
        
        # Verify HTML content
        html_content = output_path.read_text()
        
        assert "<!DOCTYPE html>" in html_content
        assert "Integration Test Report" in html_content
        assert "Test Summary" in html_content
        assert "Test Categories" in html_content
        assert "Agent Health" in html_content
        assert "Environment Issues" in html_content
        assert "Performance Metrics" in html_content
        
        # Check for specific data
        assert "10" in html_content  # total tests
        assert "70.0%" in html_content  # success rate
        assert "hill_metrics" in html_content
        assert "weather" in html_content
        assert "shapely" in html_content  # environment issue
    
    def test_generate_junit_report(self, report_generator, sample_test_results, temp_dir):
        """Test JUnit XML report generation."""
        output_path = temp_dir / "test_report.xml"
        
        result_path = report_generator.generate_report(
            results=sample_test_results,
            format_type=ReportFormat.JUNIT,
            output_path=output_path
        )
        
        assert result_path == output_path
        assert output_path.exists()
        
        # Parse and verify XML content
        tree = ET.parse(output_path)
        root = tree.getroot()
        
        assert root.tag == "testsuites"
        assert root.get("tests") == "10"
        assert root.get("failures") == "2"
        assert root.get("skipped") == "1"
        
        # Check testsuites
        testsuites = root.findall("testsuite")
        assert len(testsuites) >= 1
        
        # Find API contracts testsuite
        api_suite = None
        for suite in testsuites:
            if suite.get("name") == "api_contracts":
                api_suite = suite
                break
        
        assert api_suite is not None
        assert api_suite.get("tests") == "5"
        assert api_suite.get("failures") == "1"
        
        # Check testcases
        testcases = api_suite.findall("testcase")
        assert len(testcases) >= 1
        
        # Find failed testcase
        failed_case = None
        for case in testcases:
            if case.find("failure") is not None:
                failed_case = case
                break
        
        assert failed_case is not None
        failure = failed_case.find("failure")
        assert "Missing method: get_forecast" in failure.get("message")
    
    def test_generate_markdown_report(self, report_generator, sample_test_results, temp_dir):
        """Test Markdown report generation."""
        output_path = temp_dir / "test_report.md"
        
        result_path = report_generator.generate_report(
            results=sample_test_results,
            format_type=ReportFormat.MARKDOWN,
            output_path=output_path,
            include_diagnostics=True
        )
        
        assert result_path == output_path
        assert output_path.exists()
        
        # Verify Markdown content
        md_content = output_path.read_text()
        
        assert "# Integration Test Report" in md_content
        assert "## Summary" in md_content
        assert "## Test Categories" in md_content
        assert "## Agent Health" in md_content
        assert "## Environment Issues" in md_content
        assert "## Performance Metrics" in md_content
        
        # Check for specific data
        assert "| Total Tests | 10 |" in md_content
        assert "| ✅ Passed | 7 |" in md_content
        assert "| ❌ Failed | 2 |" in md_content
        assert "Success Rate:** 70.0%" in md_content
        
        # Check emojis and formatting
        assert "✅" in md_content or "⚠️" in md_content or "❌" in md_content
        assert "hill_metrics" in md_content
        assert "weather" in md_content
    
    def test_generate_multiple_formats(self, report_generator, sample_test_results, temp_dir):
        """Test generating multiple report formats."""
        formats = [ReportFormat.JSON, ReportFormat.HTML, ReportFormat.MARKDOWN]
        
        report_paths = report_generator.generate_multiple_formats(
            results=sample_test_results,
            formats=formats,
            output_dir=temp_dir,
            include_diagnostics=True
        )
        
        assert len(report_paths) == 3
        assert ReportFormat.JSON in report_paths
        assert ReportFormat.HTML in report_paths
        assert ReportFormat.MARKDOWN in report_paths
        
        # Verify all files exist
        for format_type, path in report_paths.items():
            assert path.exists()
            assert path.parent == temp_dir
    
    def test_generate_report_with_compression(self, report_generator, sample_test_results, temp_dir):
        """Test report generation with compression."""
        output_path = temp_dir / "test_report.json"
        
        result_path = report_generator.generate_report(
            results=sample_test_results,
            format_type=ReportFormat.JSON,
            output_path=output_path,
            compress=True
        )
        
        # Should have .gz extension
        assert result_path.suffix == ".gz"
        assert result_path.exists()
        
        # Verify compressed content can be read
        import gzip
        with gzip.open(result_path, 'rt') as f:
            data = json.load(f)
        
        assert "summary" in data
        assert data["summary"]["total_tests"] == 10
    
    def test_generate_report_without_diagnostics(self, report_generator, sample_test_results, temp_dir):
        """Test report generation without diagnostics."""
        output_path = temp_dir / "test_report.json"
        
        report_generator.generate_report(
            results=sample_test_results,
            format_type=ReportFormat.JSON,
            output_path=output_path,
            include_diagnostics=False
        )
        
        with open(output_path) as f:
            data = json.load(f)
        
        # Should not include detailed diagnostics
        assert "diagnostics" not in data or not data["diagnostics"]
        assert "detailed_tests" not in data
    
    def test_generate_report_empty_results(self, report_generator, temp_dir):
        """Test report generation with empty results."""
        empty_results = TestResults()
        empty_results.summary = TestSummary()
        
        output_path = temp_dir / "empty_report.json"
        
        result_path = report_generator.generate_report(
            results=empty_results,
            format_type=ReportFormat.JSON,
            output_path=output_path
        )
        
        assert result_path.exists()
        
        with open(output_path) as f:
            data = json.load(f)
        
        assert data["summary"]["total_tests"] == 0
        assert data["summary"]["success_rate"] == 0.0
        assert len(data["categories"]) == 0
    
    def test_generate_report_invalid_format(self, report_generator, sample_test_results, temp_dir):
        """Test report generation with invalid format."""
        output_path = temp_dir / "test_report.txt"
        
        with pytest.raises(ValueError, match="Unsupported report format"):
            report_generator.generate_report(
                results=sample_test_results,
                format_type="invalid_format",
                output_path=output_path
            )
    
    def test_generate_report_auto_path(self, report_generator, sample_test_results):
        """Test report generation with automatic path generation."""
        result_path = report_generator.generate_report(
            results=sample_test_results,
            format_type=ReportFormat.JSON
        )
        
        assert result_path.exists()
        assert result_path.suffix == ".json"
        assert "test_report_" in result_path.name
        
        # Cleanup
        result_path.unlink()
        if result_path.parent.name == "test_results":
            result_path.parent.rmdir()
    
    def test_html_status_colors(self, report_generator):
        """Test HTML status color generation."""
        # Test success color (green)
        color = report_generator._get_status_color(95.0)
        assert color == "#27ae60"
        
        # Test warning color (orange)
        color = report_generator._get_status_color(75.0)
        assert color == "#f39c12"
        
        # Test failure color (red)
        color = report_generator._get_status_color(50.0)
        assert color == "#e74c3c"
    
    def test_html_status_classes(self, report_generator):
        """Test HTML status class generation."""
        # Test success class
        cls = report_generator._get_status_class(95.0)
        assert cls == "success"
        
        # Test warning class
        cls = report_generator._get_status_class(75.0)
        assert cls == "warning"
        
        # Test failure class
        cls = report_generator._get_status_class(50.0)
        assert cls == "failure"
    
    def test_agent_to_dict_conversion(self, report_generator):
        """Test agent health status to dictionary conversion."""
        agent = AgentHealthStatus(
            name="test_agent",
            status="healthy",
            response_time=100.0,
            available_methods=["method1", "method2"],
            missing_methods=[]
        )
        
        agent_dict = report_generator._agent_to_dict(agent)
        
        assert agent_dict["name"] == "test_agent"
        assert agent_dict["status"] == "healthy"
        assert agent_dict["response_time"] == 100.0
        assert agent_dict["available_methods"] == ["method1", "method2"]
        assert agent_dict["missing_methods"] == []
    
    def test_html_sections_generation(self, report_generator, sample_test_results):
        """Test individual HTML section generation."""
        # Test category section
        category_html = report_generator._generate_category_section_html(sample_test_results)
        assert "Test Categories" in category_html
        assert "api_contracts" in category_html.lower()
        assert "category-card" in category_html
        
        # Test agent health section
        agent_html = report_generator._generate_agent_health_section_html(sample_test_results)
        assert "Agent Health" in agent_html
        assert "hill_metrics" in agent_html
        assert "weather" in agent_html
        
        # Test environment section
        env_html = report_generator._generate_environment_section_html(sample_test_results)
        assert "Environment Issues" in env_html
        assert "shapely" in env_html
        
        # Test performance section
        perf_html = report_generator._generate_performance_section_html(sample_test_results)
        assert "Performance Metrics" in perf_html
        assert "45.5" in perf_html  # total duration
    
    def test_markdown_emoji_usage(self, report_generator, sample_test_results, temp_dir):
        """Test proper emoji usage in Markdown reports."""
        output_path = temp_dir / "test_report.md"
        
        report_generator.generate_report(
            results=sample_test_results,
            format_type=ReportFormat.MARKDOWN,
            output_path=output_path
        )
        
        md_content = output_path.read_text()
        
        # Should have status emoji in title
        assert "✅" in md_content or "⚠️" in md_content or "❌" in md_content
        
        # Should have emojis in summary table
        assert "✅ Passed" in md_content
        assert "❌ Failed" in md_content
        assert "⏭️ Skipped" in md_content
        
        # Should have emojis for agent health
        assert "hill_metrics" in md_content
        assert "weather" in md_content
    
    def test_junit_xml_structure(self, report_generator, sample_test_results, temp_dir):
        """Test JUnit XML structure compliance."""
        output_path = temp_dir / "junit_report.xml"
        
        report_generator.generate_report(
            results=sample_test_results,
            format_type=ReportFormat.JUNIT,
            output_path=output_path
        )
        
        # Parse XML and validate structure
        tree = ET.parse(output_path)
        root = tree.getroot()
        
        # Validate root element
        assert root.tag == "testsuites"
        required_attrs = ["name", "tests", "failures", "errors", "skipped", "time", "timestamp"]
        for attr in required_attrs:
            assert root.get(attr) is not None
        
        # Validate testsuite elements
        for testsuite in root.findall("testsuite"):
            suite_attrs = ["name", "tests", "failures", "errors", "skipped", "time"]
            for attr in suite_attrs:
                assert testsuite.get(attr) is not None
            
            # Validate testcase elements
            for testcase in testsuite.findall("testcase"):
                case_attrs = ["name", "classname", "time"]
                for attr in case_attrs:
                    assert testcase.get(attr) is not None
    
    @patch('webbrowser.open')
    def test_report_generation_with_config(self, mock_browser, temp_dir):
        """Test report generation with custom configuration."""
        config = TestConfig()
        report_generator = ReportGenerator(config)
        
        # Create minimal test results
        results = TestResults()
        results.summary = TestSummary(total_tests=1, passed=1)
        
        output_path = temp_dir / "config_test.html"
        
        result_path = report_generator.generate_report(
            results=results,
            format_type=ReportFormat.HTML,
            output_path=output_path
        )
        
        assert result_path.exists()
        html_content = result_path.read_text()
        assert "Integration Test Report" in html_content


if __name__ == "__main__":
    pytest.main([__file__])