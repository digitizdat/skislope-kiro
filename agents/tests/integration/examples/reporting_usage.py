"""
Example usage of the reporting and dashboard functionality.

Demonstrates how to use the ReportGenerator, TestResultsDashboard, and PerformanceTracker
components for comprehensive test result reporting and monitoring.
"""

import asyncio
import tempfile
from datetime import datetime
from pathlib import Path

from ..models import (
    TestResults, TestResult, TestCategory, TestStatus, TestSummary,
    CategoryResults, PerformanceMetrics, TestError, Severity,
    AgentHealthStatus, EnvironmentIssue
)
from ..report_generator import ReportGenerator
from ..dashboard import TestResultsDashboard
from ..performance_tracker import PerformanceTracker


def create_sample_test_results() -> TestResults:
    """Create sample test results for demonstration."""
    results = TestResults()
    
    # Create summary
    results.summary = TestSummary(
        total_tests=15,
        passed=12,
        failed=2,
        skipped=1,
        errors=0,
        duration=120.5,
        start_time=datetime.now()
    )
    
    # Create API contracts category
    api_category = CategoryResults(category=TestCategory.API_CONTRACTS)
    api_category.total_tests = 6
    api_category.passed = 5
    api_category.failed = 1
    api_category.duration = 45.0
    
    # Add test results
    passed_test = TestResult(
        name="Hill Metrics API Contract",
        category=TestCategory.API_CONTRACTS,
        status=TestStatus.PASSED,
        duration=8.5,
        message="All API methods validated successfully"
    )
    
    failed_test = TestResult(
        name="Weather Service API Contract",
        category=TestCategory.API_CONTRACTS,
        status=TestStatus.FAILED,
        duration=12.0
    )
    failed_test.error = TestError(
        category="api_contracts",
        severity=Severity.HIGH,
        message="Method signature mismatch: get_forecast",
        suggested_fix="Update frontend client to match backend method signature",
        context={"expected_params": ["location", "days"], "actual_params": ["location"]}
    )
    
    api_category.tests = [passed_test, failed_test]
    results.categories[TestCategory.API_CONTRACTS] = api_category
    
    # Create communication category
    comm_category = CategoryResults(category=TestCategory.COMMUNICATION)
    comm_category.total_tests = 4
    comm_category.passed = 4
    comm_category.failed = 0
    comm_category.duration = 25.0
    results.categories[TestCategory.COMMUNICATION] = comm_category
    
    # Create environment category
    env_category = CategoryResults(category=TestCategory.ENVIRONMENT)
    env_category.total_tests = 3
    env_category.passed = 2
    env_category.skipped = 1
    env_category.duration = 15.0
    results.categories[TestCategory.ENVIRONMENT] = env_category
    
    # Create workflow category
    workflow_category = CategoryResults(category=TestCategory.WORKFLOWS)
    workflow_category.total_tests = 2
    workflow_category.passed = 1
    workflow_category.failed = 1
    workflow_category.duration = 35.5
    results.categories[TestCategory.WORKFLOWS] = workflow_category
    
    # Add agent health status
    results.agent_health = [
        AgentHealthStatus(
            name="hill_metrics",
            status="healthy",
            response_time=125.0,
            available_methods=["get_elevation", "get_slope", "get_aspect"],
            missing_methods=[],
            endpoint="http://localhost:8001",
            version="1.0.0"
        ),
        AgentHealthStatus(
            name="weather",
            status="degraded",
            response_time=450.0,
            available_methods=["get_current"],
            missing_methods=["get_forecast", "get_historical"],
            endpoint="http://localhost:8002",
            version="0.9.0",
            last_error="Connection timeout on forecast endpoint"
        ),
        AgentHealthStatus(
            name="equipment",
            status="healthy",
            response_time=95.0,
            available_methods=["get_lifts", "get_trails", "get_facilities"],
            missing_methods=[],
            endpoint="http://localhost:8003",
            version="1.1.0"
        )
    ]
    
    # Add environment issues
    results.environment_issues = [
        EnvironmentIssue(
            component="python_packages",
            issue_type="version_mismatch",
            description="Package 'rasterio' version 1.2.0 found, but 1.3.0+ required",
            severity=Severity.MEDIUM,
            suggested_fix="Run 'uv add rasterio>=1.3.0' to upgrade package",
            detected_value="1.2.0",
            expected_value=">=1.3.0"
        ),
        EnvironmentIssue(
            component="ssl_configuration",
            issue_type="certificate_warning",
            description="SSL certificate verification disabled in test environment",
            severity=Severity.LOW,
            suggested_fix="Enable SSL verification for production deployment",
            detected_value="disabled",
            expected_value="enabled"
        )
    ]
    
    # Add performance metrics
    results.performance_metrics = PerformanceMetrics(
        total_duration=120.5,
        setup_duration=15.0,
        execution_duration=95.0,
        teardown_duration=10.5,
        memory_peak=512.0,
        memory_average=256.0,
        cpu_peak=85.0,
        cpu_average=45.0,
        network_requests=42,
        network_bytes_sent=2048000,
        network_bytes_received=4096000
    )
    
    return results


def demonstrate_report_generation():
    """Demonstrate report generation in multiple formats."""
    print("🔧 Generating Test Reports...")
    
    # Create sample results
    results = create_sample_test_results()
    
    # Initialize report generator
    report_generator = ReportGenerator()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Generate reports in all formats
        formats = ["json", "html", "junit", "markdown"]
        report_paths = report_generator.generate_multiple_formats(
            results=results,
            formats=formats,
            output_dir=temp_path,
            include_diagnostics=True
        )
        
        print(f"✅ Generated {len(report_paths)} report formats:")
        for format_type, path in report_paths.items():
            size_kb = path.stat().st_size / 1024
            print(f"   📄 {format_type.upper()}: {path.name} ({size_kb:.1f} KB)")
        
        # Display HTML report content preview
        if "html" in report_paths:
            html_content = report_paths["html"].read_text()
            print(f"\n📊 HTML Report Preview:")
            print(f"   - Contains {html_content.count('summary-card')} summary cards")
            print(f"   - Contains {html_content.count('category-card')} category cards")
            print(f"   - Contains {html_content.count('agent-card')} agent health cards")
            print(f"   - Includes CSS styling and JavaScript interactivity")
        
        # Display JUnit XML structure
        if "junit" in report_paths:
            import xml.etree.ElementTree as ET
            tree = ET.parse(report_paths["junit"])
            root = tree.getroot()
            testsuites = root.findall("testsuite")
            total_testcases = sum(len(suite.findall("testcase")) for suite in testsuites)
            print(f"\n🧪 JUnit XML Report:")
            print(f"   - {len(testsuites)} test suites")
            print(f"   - {total_testcases} test cases")
            print(f"   - Compatible with CI/CD systems")


def demonstrate_dashboard_usage():
    """Demonstrate dashboard functionality."""
    print("\n🖥️  Starting Test Results Dashboard...")
    
    # Create sample results
    results = create_sample_test_results()
    
    # Initialize dashboard
    dashboard = TestResultsDashboard()
    dashboard.add_test_results(results)
    
    # Add historical data for trends
    print("📈 Adding historical test data...")
    for i in range(5):
        historical_results = create_sample_test_results()
        # Vary the results slightly for trend demonstration
        historical_results.summary.passed = 12 - i % 3
        historical_results.summary.failed = 2 + i % 3
        historical_results.summary.duration = 120.5 + i * 10
        dashboard.add_test_results(historical_results)
    
    # Get performance summary
    summary = dashboard.get_performance_summary()
    print(f"📊 Performance Summary:")
    print(f"   - Total test runs: {summary['total_runs']}")
    print(f"   - Average success rate: {summary['average_success_rate']:.1f}%")
    print(f"   - Average duration: {summary['average_duration']:.1f}s")
    print(f"   - Trend: {summary['success_trend']}")
    
    # Export dashboard data
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        export_path = Path(f.name)
    
    dashboard.export_data(export_path)
    export_size = export_path.stat().st_size / 1024
    print(f"💾 Dashboard data exported: {export_path.name} ({export_size:.1f} KB)")
    
    # Clean up
    export_path.unlink()
    
    print("ℹ️  Dashboard server can be started with dashboard.start_server()")
    print("   This would open a web interface at http://localhost:8080")


def demonstrate_performance_tracking():
    """Demonstrate performance tracking functionality."""
    print("\n⚡ Performance Tracking Demo...")
    
    # Initialize performance tracker
    tracker = PerformanceTracker(sampling_interval=0.1, max_samples=50)
    
    # Simulate test phases
    print("🔄 Simulating test execution phases...")
    
    # Setup phase
    tracker.start_phase("setup")
    import time
    time.sleep(0.5)  # Simulate setup work
    setup_window = tracker.end_phase()
    
    # Execution phase
    tracker.start_phase("execution")
    time.sleep(1.0)  # Simulate test execution
    execution_window = tracker.end_phase()
    
    # Teardown phase
    tracker.start_phase("teardown")
    time.sleep(0.3)  # Simulate cleanup
    teardown_window = tracker.end_phase()
    
    # Get performance summary
    summary = tracker.get_performance_summary()
    print(f"📊 Performance Summary:")
    print(f"   - Total phases: {summary['total_windows']}")
    print(f"   - Total duration: {summary['total_duration']:.2f}s")
    
    for phase_name, phase_data in summary['windows'].items():
        print(f"   - {phase_name.title()}: {phase_data['duration']:.2f}s")
        print(f"     CPU avg: {phase_data['cpu_avg']:.1f}%, peak: {phase_data['cpu_peak']:.1f}%")
        print(f"     Memory avg: {phase_data['memory_avg']:.1f}%, peak: {phase_data['memory_peak']:.1f}%")
    
    # Analyze trends
    if "execution" in tracker.windows:
        trend_analysis = tracker.analyze_trends("execution")
        print(f"📈 Execution Phase Trend Analysis:")
        print(f"   - CPU trend: {trend_analysis['cpu_trend']['direction']}")
        print(f"   - Memory trend: {trend_analysis['memory_trend']['direction']}")
        print(f"   - Sample count: {trend_analysis['sample_count']}")
    
    # Create PerformanceMetrics object
    metrics = tracker.create_performance_metrics()
    print(f"📋 Performance Metrics Object:")
    print(f"   - Total duration: {metrics.total_duration:.2f}s")
    print(f"   - Setup duration: {metrics.setup_duration:.2f}s")
    print(f"   - Execution duration: {metrics.execution_duration:.2f}s")
    print(f"   - Teardown duration: {metrics.teardown_duration:.2f}s")


async def demonstrate_integrated_workflow():
    """Demonstrate integrated reporting workflow."""
    print("\n🔗 Integrated Reporting Workflow Demo...")
    
    # Initialize all components
    report_generator = ReportGenerator()
    dashboard = TestResultsDashboard()
    performance_tracker = PerformanceTracker()
    
    print("🚀 Starting integrated test simulation...")
    
    # Start performance tracking
    performance_tracker.start_phase("full_test_suite")
    
    # Simulate test execution
    import time
    time.sleep(0.5)
    
    # Create test results
    results = create_sample_test_results()
    
    # Add performance metrics from tracker
    performance_tracker.end_phase()
    results.performance_metrics = performance_tracker.create_performance_metrics()
    
    # Add to dashboard
    dashboard.add_test_results(results)
    
    # Generate reports
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        report_paths = report_generator.generate_multiple_formats(
            results=results,
            formats=["html", "json"],
            output_dir=temp_path,
            include_diagnostics=True
        )
        
        print(f"✅ Generated integrated reports:")
        for format_type, path in report_paths.items():
            print(f"   📄 {format_type.upper()}: {path.name}")
    
    # Get dashboard summary
    summary = dashboard.get_performance_summary()
    print(f"📊 Dashboard shows {summary['total_runs']} test run(s)")
    
    print("🎉 Integrated workflow completed successfully!")


def main():
    """Main demonstration function."""
    print("🧪 Integration Test Reporting & Dashboard Demo")
    print("=" * 50)
    
    try:
        # Demonstrate individual components
        demonstrate_report_generation()
        demonstrate_dashboard_usage()
        demonstrate_performance_tracking()
        
        # Demonstrate integrated workflow
        asyncio.run(demonstrate_integrated_workflow())
        
        print("\n✨ All demonstrations completed successfully!")
        print("\nKey Features Demonstrated:")
        print("• Multi-format report generation (JSON, HTML, JUnit, Markdown)")
        print("• Interactive web dashboard with trends")
        print("• Real-time performance monitoring")
        print("• Comprehensive test result tracking")
        print("• Integration with existing test infrastructure")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()