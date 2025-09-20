"""
Live Dashboard Demonstration.

This script starts a live dashboard server with sample test data and demonstrates
all the dashboard features including real-time updates, performance trends, and
interactive visualizations.
"""

import asyncio
import time
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path

from ..models import (
    TestResults, TestResult, TestCategory, TestStatus, TestSummary,
    CategoryResults, PerformanceMetrics, TestError, Severity,
    AgentHealthStatus, EnvironmentIssue
)
from ..dashboard import TestResultsDashboard
from ..performance_tracker import PerformanceTracker


def create_realistic_test_results(run_number: int = 1, base_time: datetime = None) -> TestResults:
    """Create realistic test results with varying outcomes."""
    if base_time is None:
        base_time = datetime.now()
    
    results = TestResults()
    
    # Vary results based on run number to show trends
    success_variation = [85, 90, 75, 95, 80, 88, 92, 78, 96, 85][run_number % 10]
    total_tests = 20
    passed = int(total_tests * success_variation / 100)
    failed = total_tests - passed
    
    results.summary = TestSummary(
        total_tests=total_tests,
        passed=passed,
        failed=failed,
        skipped=0,
        errors=0,
        duration=45.0 + (run_number * 5) + (run_number % 3) * 10,
        start_time=base_time - timedelta(minutes=run_number * 15)
    )
    
    # API Contracts Category
    api_category = CategoryResults(category=TestCategory.API_CONTRACTS)
    api_category.total_tests = 8
    api_category.passed = min(8, passed)
    api_category.failed = max(0, 8 - api_category.passed)
    api_category.duration = 20.0 + run_number * 2
    
    # Add some test results
    api_tests = [
        TestResult(
            name="Hill Metrics API Validation",
            category=TestCategory.API_CONTRACTS,
            status=TestStatus.PASSED,
            duration=5.2,
            message="All elevation and slope methods validated"
        ),
        TestResult(
            name="Weather Service API Validation", 
            category=TestCategory.API_CONTRACTS,
            status=TestStatus.PASSED if run_number % 3 != 0 else TestStatus.FAILED,
            duration=7.8
        ),
        TestResult(
            name="Equipment API Validation",
            category=TestCategory.API_CONTRACTS,
            status=TestStatus.PASSED,
            duration=4.1,
            message="Lift and trail data endpoints working"
        )
    ]
    
    # Add failure details for failed test
    if api_tests[1].status == TestStatus.FAILED:
        api_tests[1].error = TestError(
            category="api_contracts",
            severity=Severity.HIGH,
            message=f"Forecast endpoint timeout (run {run_number})",
            suggested_fix="Check weather service connection and increase timeout",
            context={"endpoint": "/api/weather/forecast", "timeout": "30s"}
        )
    
    api_category.tests = api_tests
    results.categories[TestCategory.API_CONTRACTS] = api_category
    
    # Communication Category
    comm_category = CategoryResults(category=TestCategory.COMMUNICATION)
    comm_category.total_tests = 5
    comm_category.passed = min(5, passed - api_category.passed)
    comm_category.failed = max(0, 5 - comm_category.passed)
    comm_category.duration = 15.0 + run_number
    results.categories[TestCategory.COMMUNICATION] = comm_category
    
    # Environment Category
    env_category = CategoryResults(category=TestCategory.ENVIRONMENT)
    env_category.total_tests = 4
    env_category.passed = min(4, passed - api_category.passed - comm_category.passed)
    env_category.failed = max(0, 4 - env_category.passed)
    env_category.duration = 8.0
    results.categories[TestCategory.ENVIRONMENT] = env_category
    
    # Workflows Category
    workflow_category = CategoryResults(category=TestCategory.WORKFLOWS)
    workflow_category.total_tests = 3
    workflow_category.passed = max(0, passed - api_category.passed - comm_category.passed - env_category.passed)
    workflow_category.failed = max(0, 3 - workflow_category.passed)
    workflow_category.duration = 12.0 + run_number * 1.5
    results.categories[TestCategory.WORKFLOWS] = workflow_category
    
    # Agent Health (varies by run)
    agents_health = [
        AgentHealthStatus(
            name="hill_metrics",
            status="healthy" if run_number % 4 != 0 else "degraded",
            response_time=120.0 + run_number * 10,
            available_methods=["get_elevation", "get_slope", "get_aspect"],
            missing_methods=[],
            endpoint="http://localhost:8001",
            version="1.0.0"
        ),
        AgentHealthStatus(
            name="weather",
            status="healthy" if run_number % 3 != 0 else "degraded",
            response_time=200.0 + run_number * 15,
            available_methods=["get_current", "get_forecast"] if run_number % 3 != 0 else ["get_current"],
            missing_methods=[] if run_number % 3 != 0 else ["get_forecast"],
            endpoint="http://localhost:8002",
            version="1.1.0",
            last_error="Forecast service timeout" if run_number % 3 == 0 else None
        ),
        AgentHealthStatus(
            name="equipment",
            status="healthy",
            response_time=85.0 + run_number * 5,
            available_methods=["get_lifts", "get_trails", "get_facilities"],
            missing_methods=[],
            endpoint="http://localhost:8003",
            version="1.2.0"
        )
    ]
    
    results.agent_health = agents_health
    
    # Environment Issues (occasional)
    if run_number % 5 == 0:
        results.environment_issues = [
            EnvironmentIssue(
                component="ssl_certificates",
                issue_type="expiration_warning",
                description="SSL certificate expires in 30 days",
                severity=Severity.MEDIUM,
                suggested_fix="Renew SSL certificates before expiration",
                detected_value="30 days",
                expected_value=">90 days"
            )
        ]
    elif run_number % 7 == 0:
        results.environment_issues = [
            EnvironmentIssue(
                component="disk_space",
                issue_type="low_space",
                description="Log directory has less than 1GB free space",
                severity=Severity.HIGH,
                suggested_fix="Clean up old log files or increase disk space",
                detected_value="0.8GB",
                expected_value=">2GB"
            )
        ]
    
    # Performance Metrics
    results.performance_metrics = PerformanceMetrics(
        total_duration=results.summary.duration,
        setup_duration=8.0 + run_number * 0.5,
        execution_duration=results.summary.duration - 15.0,
        teardown_duration=7.0 + run_number * 0.3,
        memory_peak=256.0 + run_number * 20,
        memory_average=180.0 + run_number * 15,
        cpu_peak=75.0 + run_number * 2,
        cpu_average=35.0 + run_number * 1.5,
        network_requests=25 + run_number * 3,
        network_bytes_sent=1024000 + run_number * 100000,
        network_bytes_received=2048000 + run_number * 150000
    )
    
    return results


async def simulate_continuous_testing(dashboard: TestResultsDashboard, num_runs: int = 10):
    """Simulate continuous test runs to show dashboard updates."""
    print(f"🔄 Simulating {num_runs} test runs...")
    
    base_time = datetime.now()
    
    for i in range(num_runs):
        print(f"   📊 Adding test run {i + 1}/{num_runs}")
        
        # Create test results for this run
        results = create_realistic_test_results(i, base_time)
        
        # Add to dashboard
        dashboard.add_test_results(results)
        
        # Small delay to simulate real test execution
        await asyncio.sleep(0.5)
    
    print(f"✅ Added {num_runs} test runs to dashboard")


def print_dashboard_info(dashboard: TestResultsDashboard):
    """Print information about the dashboard state."""
    summary = dashboard.get_performance_summary()
    
    print("\n📊 Dashboard Summary:")
    print(f"   • Total test runs: {summary.get('total_runs', 0)}")
    print(f"   • Average success rate: {summary.get('average_success_rate', 0):.1f}%")
    print(f"   • Average duration: {summary.get('average_duration', 0):.1f}s")
    print(f"   • Success trend: {summary.get('success_trend', 'unknown')}")
    
    # Get current results
    current = dashboard.dashboard_data.current_results
    if current:
        print(f"\n🔍 Latest Test Run:")
        print(f"   • Tests: {current.summary.total_tests} total, {current.summary.passed} passed, {current.summary.failed} failed")
        print(f"   • Duration: {current.summary.duration:.1f}s")
        print(f"   • Success rate: {current.summary.success_rate:.1f}%")
        print(f"   • Categories: {len(current.categories)}")
        print(f"   • Agents monitored: {len(current.agent_health)}")
        print(f"   • Environment issues: {len(current.environment_issues)}")


async def demonstrate_live_dashboard():
    """Main demonstration function."""
    print("🚀 Integration Test Dashboard Live Demo")
    print("=" * 50)
    
    # Initialize dashboard
    print("🔧 Initializing dashboard...")
    dashboard = TestResultsDashboard()
    
    # Add initial test data
    print("📊 Adding initial test data...")
    initial_results = create_realistic_test_results(0)
    dashboard.add_test_results(initial_results)
    
    # Start dashboard server
    print("🌐 Starting dashboard server...")
    try:
        url = dashboard.start_server(port=8080, open_browser=False)
        print(f"✅ Dashboard server started at: {url}")
        print(f"🌍 Open this URL in your browser to view the dashboard")
        
        # Print initial dashboard info
        print_dashboard_info(dashboard)
        
        # Simulate continuous testing
        await simulate_continuous_testing(dashboard, 8)
        
        # Print updated dashboard info
        print_dashboard_info(dashboard)
        
        # Generate static reports
        print("\n📄 Generating static reports...")
        temp_dir = Path("/tmp/dashboard_demo_reports")
        temp_dir.mkdir(exist_ok=True)
        
        html_report = dashboard.generate_static_report(
            format_type="html",
            output_path=temp_dir / "dashboard_report.html",
            include_diagnostics=True
        )
        
        if html_report:
            print(f"📊 HTML report generated: {html_report}")
            print(f"   File size: {html_report.stat().st_size / 1024:.1f} KB")
        
        # Export dashboard data
        export_path = temp_dir / "dashboard_data.json"
        dashboard.export_data(export_path)
        print(f"💾 Dashboard data exported: {export_path}")
        print(f"   File size: {export_path.stat().st_size / 1024:.1f} KB")
        
        print(f"\n🎯 Dashboard Features Demonstrated:")
        print(f"   ✅ Real-time test result display")
        print(f"   ✅ Performance trend tracking")
        print(f"   ✅ Agent health monitoring")
        print(f"   ✅ Environment issue reporting")
        print(f"   ✅ Interactive web interface")
        print(f"   ✅ Historical data analysis")
        print(f"   ✅ Static report generation")
        print(f"   ✅ Data export functionality")
        
        print(f"\n🌐 Dashboard is running at: {url}")
        print(f"📱 Features available in the web interface:")
        print(f"   • Summary cards with key metrics")
        print(f"   • Success rate and duration trend charts")
        print(f"   • Test category breakdown with visual indicators")
        print(f"   • Agent health status with response times")
        print(f"   • Environment issues with severity levels")
        print(f"   • Auto-refresh toggle for live updates")
        print(f"   • Responsive design for mobile devices")
        
        # Keep server running
        print(f"\n⏳ Dashboard server will run for 60 seconds...")
        print(f"   Open {url} in your browser to explore the interface")
        print(f"   Press Ctrl+C to stop the server early")
        
        try:
            # Wait for user interaction
            await asyncio.sleep(60)
        except KeyboardInterrupt:
            print(f"\n⏹️  Server stopped by user")
        
    except Exception as e:
        print(f"❌ Failed to start dashboard: {e}")
        return
    
    finally:
        # Clean up
        print(f"🧹 Cleaning up...")
        dashboard.stop_server()
        print(f"✅ Dashboard server stopped")


def demonstrate_dashboard_api():
    """Demonstrate dashboard API functionality."""
    print("\n🔌 Dashboard API Demo")
    print("-" * 30)
    
    # Initialize dashboard with data
    dashboard = TestResultsDashboard()
    
    # Add multiple test runs
    for i in range(3):
        results = create_realistic_test_results(i)
        dashboard.add_test_results(results)
    
    # Get dashboard data via API
    data = dashboard.dashboard_data.get_dashboard_data()
    
    print(f"📊 Dashboard API Response:")
    print(f"   • Current results: {'Available' if data['current_results'] else 'None'}")
    print(f"   • Historical summary: {'Available' if data['historical_summary'] else 'None'}")
    print(f"   • Performance trends: {len(data['performance_trends'])} data points")
    print(f"   • Last updated: {data['last_updated']}")
    print(f"   • Total runs: {data['metadata']['total_runs']}")
    
    if data['current_results']:
        current = data['current_results']
        print(f"\n🔍 Current Test Results:")
        print(f"   • Summary: {current['summary']['total_tests']} tests, {current['summary']['success_rate']:.1f}% success")
        print(f"   • Categories: {len(current['categories'])}")
        print(f"   • Agent health: {len(current['agent_health'])} agents")
        print(f"   • Environment issues: {len(current['environment_issues'])}")
    
    if data['performance_trends']:
        latest_trend = data['performance_trends'][-1]
        print(f"\n📈 Latest Performance Trend:")
        print(f"   • Timestamp: {latest_trend['timestamp']}")
        print(f"   • Duration: {latest_trend['duration']:.1f}s")
        print(f"   • Success rate: {latest_trend['success_rate']:.1f}%")
        print(f"   • Total tests: {latest_trend['total_tests']}")


if __name__ == "__main__":
    print("🎮 Choose demonstration mode:")
    print("1. Live Dashboard Server (recommended)")
    print("2. API Functionality Demo")
    
    try:
        choice = input("\nEnter choice (1 or 2): ").strip()
        
        if choice == "1":
            asyncio.run(demonstrate_live_dashboard())
        elif choice == "2":
            demonstrate_dashboard_api()
        else:
            print("Invalid choice. Running live dashboard demo...")
            asyncio.run(demonstrate_live_dashboard())
            
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()