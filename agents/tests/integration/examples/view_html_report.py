"""
HTML Report Viewer.

Generates and displays a sample HTML report to showcase the visual dashboard features.
"""

import tempfile
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path

from ..models import (
    TestResults, TestResult, TestCategory, TestStatus, TestSummary,
    CategoryResults, PerformanceMetrics, TestError, Severity,
    AgentHealthStatus, EnvironmentIssue
)
from ..report_generator import ReportGenerator


def create_comprehensive_test_results() -> TestResults:
    """Create comprehensive test results for HTML report demonstration."""
    results = TestResults()
    
    # Create detailed summary
    results.summary = TestSummary(
        total_tests=25,
        passed=20,
        failed=3,
        skipped=1,
        errors=1,
        duration=180.5,
        start_time=datetime.now() - timedelta(minutes=3),
        end_time=datetime.now()
    )
    
    # API Contracts Category - Mixed results
    api_category = CategoryResults(category=TestCategory.API_CONTRACTS)
    api_category.total_tests = 10
    api_category.passed = 8
    api_category.failed = 2
    api_category.duration = 65.0
    
    # Add detailed test results
    api_tests = [
        TestResult(
            name="Hill Metrics API - Elevation Service",
            category=TestCategory.API_CONTRACTS,
            status=TestStatus.PASSED,
            duration=8.2,
            message="All elevation endpoints validated successfully",
            start_time=datetime.now() - timedelta(minutes=3),
            end_time=datetime.now() - timedelta(minutes=2, seconds=52)
        ),
        TestResult(
            name="Hill Metrics API - Slope Analysis",
            category=TestCategory.API_CONTRACTS,
            status=TestStatus.PASSED,
            duration=12.1,
            message="Slope calculation methods working correctly",
            start_time=datetime.now() - timedelta(minutes=2, seconds=52),
            end_time=datetime.now() - timedelta(minutes=2, seconds=40)
        ),
        TestResult(
            name="Weather Service API - Current Conditions",
            category=TestCategory.API_CONTRACTS,
            status=TestStatus.FAILED,
            duration=15.3,
            start_time=datetime.now() - timedelta(minutes=2, seconds=40),
            end_time=datetime.now() - timedelta(minutes=2, seconds=25)
        ),
        TestResult(
            name="Weather Service API - Forecast Data",
            category=TestCategory.API_CONTRACTS,
            status=TestStatus.FAILED,
            duration=18.7,
            start_time=datetime.now() - timedelta(minutes=2, seconds=25),
            end_time=datetime.now() - timedelta(minutes=2, seconds=6)
        ),
        TestResult(
            name="Equipment API - Lift Status",
            category=TestCategory.API_CONTRACTS,
            status=TestStatus.PASSED,
            duration=6.8,
            message="Lift status endpoints responding correctly",
            start_time=datetime.now() - timedelta(minutes=2, seconds=6),
            end_time=datetime.now() - timedelta(minutes=2)
        )
    ]
    
    # Add error details to failed tests
    api_tests[2].error = TestError(
        category="api_contracts",
        severity=Severity.HIGH,
        message="Weather service timeout - current conditions endpoint not responding",
        suggested_fix="Check weather service connection and increase timeout to 45 seconds",
        context={
            "endpoint": "/api/weather/current",
            "timeout": "30s",
            "expected_response_time": "<5s",
            "actual_response_time": "timeout"
        },
        stack_trace="TimeoutError: Request timed out after 30 seconds\n  at WeatherClient.getCurrentConditions(weather_client.py:45)\n  at APIContractValidator.validate_weather_endpoints(api_validator.py:123)"
    )
    
    api_tests[3].error = TestError(
        category="api_contracts",
        severity=Severity.CRITICAL,
        message="Weather forecast endpoint returning 500 Internal Server Error",
        suggested_fix="Restart weather service and check database connectivity",
        context={
            "endpoint": "/api/weather/forecast",
            "status_code": 500,
            "error_message": "Database connection failed",
            "retry_attempts": 3
        },
        stack_trace="HTTPError: 500 Server Error\n  at WeatherClient.getForecast(weather_client.py:67)\n  at APIContractValidator.validate_forecast_endpoint(api_validator.py:145)"
    )
    
    api_category.tests = api_tests
    results.categories[TestCategory.API_CONTRACTS] = api_category
    
    # Communication Category - Mostly successful
    comm_category = CategoryResults(category=TestCategory.COMMUNICATION)
    comm_category.total_tests = 6
    comm_category.passed = 6
    comm_category.failed = 0
    comm_category.duration = 35.0
    results.categories[TestCategory.COMMUNICATION] = comm_category
    
    # Environment Category - One skipped test
    env_category = CategoryResults(category=TestCategory.ENVIRONMENT)
    env_category.total_tests = 5
    env_category.passed = 4
    env_category.skipped = 1
    env_category.duration = 25.0
    results.categories[TestCategory.ENVIRONMENT] = env_category
    
    # Workflows Category - One error
    workflow_category = CategoryResults(category=TestCategory.WORKFLOWS)
    workflow_category.total_tests = 4
    workflow_category.passed = 2
    workflow_category.failed = 1
    workflow_category.errors = 1
    workflow_category.duration = 55.5
    results.categories[TestCategory.WORKFLOWS] = workflow_category
    
    # Detailed agent health with realistic data
    results.agent_health = [
        AgentHealthStatus(
            name="hill_metrics",
            status="healthy",
            response_time=145.2,
            available_methods=["get_elevation", "get_slope", "get_aspect", "get_terrain_analysis"],
            missing_methods=[],
            endpoint="http://localhost:8001",
            version="1.2.3",
            uptime=86400.0,  # 24 hours
            memory_usage=256.7
        ),
        AgentHealthStatus(
            name="weather",
            status="degraded",
            response_time=2847.1,
            available_methods=["get_current"],
            missing_methods=["get_forecast", "get_historical", "get_alerts"],
            endpoint="http://localhost:8002",
            version="0.9.1",
            uptime=3600.0,  # 1 hour (recently restarted)
            memory_usage=512.3,
            last_error="Database connection timeout - forecast service unavailable"
        ),
        AgentHealthStatus(
            name="equipment",
            status="healthy",
            response_time=89.4,
            available_methods=["get_lifts", "get_trails", "get_facilities", "get_snow_conditions"],
            missing_methods=[],
            endpoint="http://localhost:8003",
            version="2.0.0",
            uptime=172800.0,  # 48 hours
            memory_usage=128.9
        ),
        AgentHealthStatus(
            name="cache_service",
            status="failed",
            response_time=None,
            available_methods=[],
            missing_methods=["get_cached_data", "set_cache", "clear_cache"],
            endpoint="http://localhost:8004",
            version="1.0.0",
            uptime=0.0,
            memory_usage=0.0,
            last_error="Service not responding - connection refused"
        )
    ]
    
    # Environment issues with different severity levels
    results.environment_issues = [
        EnvironmentIssue(
            component="ssl_certificates",
            issue_type="expiration_warning",
            description="SSL certificate for weather service expires in 15 days",
            severity=Severity.HIGH,
            suggested_fix="Renew SSL certificate before expiration date",
            detected_value="15 days remaining",
            expected_value=">30 days remaining"
        ),
        EnvironmentIssue(
            component="disk_space",
            issue_type="low_space",
            description="Log directory has less than 500MB free space",
            severity=Severity.CRITICAL,
            suggested_fix="Clean up old log files or increase disk allocation",
            detected_value="487MB free",
            expected_value=">2GB free"
        ),
        EnvironmentIssue(
            component="python_packages",
            issue_type="version_mismatch",
            description="Package 'rasterio' version 1.2.0 found, but 1.3.0+ required for terrain processing",
            severity=Severity.MEDIUM,
            suggested_fix="Run 'uv add rasterio>=1.3.0' to upgrade package",
            detected_value="1.2.0",
            expected_value=">=1.3.0"
        ),
        EnvironmentIssue(
            component="database_connection",
            issue_type="connection_pool",
            description="Database connection pool approaching maximum capacity",
            severity=Severity.MEDIUM,
            suggested_fix="Increase connection pool size or optimize query performance",
            detected_value="18/20 connections used",
            expected_value="<15/20 connections used"
        ),
        EnvironmentIssue(
            component="memory_usage",
            issue_type="high_usage",
            description="System memory usage above recommended threshold",
            severity=Severity.LOW,
            suggested_fix="Monitor memory usage and consider increasing available RAM",
            detected_value="78% used",
            expected_value="<70% used"
        )
    ]
    
    # Comprehensive performance metrics
    results.performance_metrics = PerformanceMetrics(
        total_duration=180.5,
        setup_duration=25.3,
        execution_duration=142.7,
        teardown_duration=12.5,
        memory_peak=1024.8,
        memory_average=756.2,
        cpu_peak=89.3,
        cpu_average=45.7,
        network_requests=156,
        network_bytes_sent=5242880,  # 5MB
        network_bytes_received=12582912  # 12MB
    )
    
    # Add diagnostic information
    results.diagnostics = {
        "test_environment": "integration",
        "python_version": "3.13.7",
        "platform": "macOS-14.0-arm64",
        "test_runner": "pytest-8.4.2",
        "parallel_workers": 4,
        "cache_enabled": True,
        "debug_mode": False,
        "test_data_size": "2.3MB",
        "external_dependencies": {
            "weather_api": "available",
            "terrain_database": "available", 
            "equipment_service": "available",
            "cache_service": "unavailable"
        }
    }
    
    return results


def generate_and_view_html_report():
    """Generate and display HTML report."""
    print("🎨 HTML Report Generation Demo")
    print("=" * 40)
    
    # Create comprehensive test results
    print("📊 Creating comprehensive test results...")
    results = create_comprehensive_test_results()
    
    print(f"   • {results.summary.total_tests} total tests")
    print(f"   • {results.summary.passed} passed, {results.summary.failed} failed")
    print(f"   • {len(results.categories)} test categories")
    print(f"   • {len(results.agent_health)} agents monitored")
    print(f"   • {len(results.environment_issues)} environment issues")
    
    # Generate HTML report
    print("\n🔧 Generating HTML report...")
    report_generator = ReportGenerator()
    
    # Create output directory
    output_dir = Path("/tmp/integration_test_reports")
    output_dir.mkdir(exist_ok=True)
    
    html_path = output_dir / "comprehensive_test_report.html"
    
    generated_path = report_generator.generate_report(
        results=results,
        format_type="html",
        output_path=html_path,
        include_diagnostics=True
    )
    
    print(f"✅ HTML report generated: {generated_path}")
    print(f"   File size: {generated_path.stat().st_size / 1024:.1f} KB")
    
    # Analyze HTML content
    html_content = generated_path.read_text()
    
    print(f"\n📊 HTML Report Analysis:")
    print(f"   • Summary cards: {html_content.count('summary-card')}")
    print(f"   • Category cards: {html_content.count('category-card')}")
    print(f"   • Agent health cards: {html_content.count('agent-card')}")
    print(f"   • Environment issues: {html_content.count('issue-item')}")
    print(f"   • Performance metrics: {html_content.count('metric-card')}")
    print(f"   • CSS styles: {'✅' if 'dashboard' in html_content else '❌'}")
    print(f"   • JavaScript: {'✅' if 'script' in html_content else '❌'}")
    
    # Show key features
    print(f"\n🎯 Key Visual Features:")
    print(f"   • Color-coded status indicators")
    print(f"   • Interactive summary cards")
    print(f"   • Detailed test breakdowns")
    print(f"   • Agent health monitoring")
    print(f"   • Environment issue alerts")
    print(f"   • Performance metrics dashboard")
    print(f"   • Responsive design")
    print(f"   • Professional styling")
    
    # Try to open in browser
    try:
        print(f"\n🌐 Opening report in browser...")
        webbrowser.open(f"file://{generated_path.absolute()}")
        print(f"✅ Report opened in default browser")
        print(f"   URL: file://{generated_path.absolute()}")
    except Exception as e:
        print(f"⚠️  Could not open browser automatically: {e}")
        print(f"   Manual URL: file://{generated_path.absolute()}")
    
    return generated_path


def show_report_structure(html_path: Path):
    """Show the structure of the generated HTML report."""
    print(f"\n📋 HTML Report Structure:")
    print(f"=" * 40)
    
    html_content = html_path.read_text()
    
    # Extract key sections
    sections = [
        ("Header", "dashboard-header"),
        ("Summary Section", "summary-section"),
        ("Categories Section", "categories-section"),
        ("Agent Health Section", "agent-health-section"),
        ("Environment Section", "environment-section"),
        ("Performance Section", "performance"),
        ("Diagnostics Section", "diagnostics"),
        ("Footer", "footer")
    ]
    
    for section_name, section_class in sections:
        if section_class in html_content:
            print(f"   ✅ {section_name}")
        else:
            print(f"   ❌ {section_name}")
    
    # Show CSS classes used
    css_classes = [
        "summary-card", "category-card", "agent-card", "issue-item",
        "metric-card", "success", "warning", "failure", "error"
    ]
    
    print(f"\n🎨 CSS Classes:")
    for css_class in css_classes:
        count = html_content.count(css_class)
        if count > 0:
            print(f"   • {css_class}: {count} occurrences")


def main():
    """Main demonstration function."""
    print("🎨 HTML Report Viewer Demo")
    print("=" * 50)
    
    try:
        # Generate and view HTML report
        html_path = generate_and_view_html_report()
        
        # Show report structure
        show_report_structure(html_path)
        
        print(f"\n✨ HTML Report Demo Complete!")
        print(f"\n📁 Report Location: {html_path}")
        print(f"🌐 Open in browser: file://{html_path.absolute()}")
        
        print(f"\n💡 HTML Report Features:")
        print(f"   • Professional dashboard-style layout")
        print(f"   • Color-coded status indicators")
        print(f"   • Interactive elements and hover effects")
        print(f"   • Responsive design for mobile devices")
        print(f"   • Comprehensive test result visualization")
        print(f"   • Agent health monitoring display")
        print(f"   • Environment issue alerts")
        print(f"   • Performance metrics charts")
        print(f"   • Detailed diagnostic information")
        print(f"   • Print-friendly styling")
        
    except Exception as e:
        print(f"\n❌ HTML report demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()