"""
Dashboard Feature Showcase.

Demonstrates all dashboard features including data management, report generation,
and performance tracking without requiring a web server.
"""

import json
import tempfile
from datetime import datetime
from datetime import timedelta
from pathlib import Path

from ..dashboard import DashboardData
from ..dashboard import TestResultsDashboard
from ..models import AgentHealthStatus
from ..models import CategoryResults
from ..models import EnvironmentIssue
from ..models import PerformanceMetrics
from ..models import Severity
from ..models import TestCategory
from ..models import TestResults
from ..models import TestSummary


def create_sample_test_run(run_id: int, success_rate: float = 85.0) -> TestResults:
    """Create a sample test run with specified success rate."""
    results = TestResults()

    total_tests = 20
    passed = int(total_tests * success_rate / 100)
    failed = total_tests - passed

    results.summary = TestSummary(
        total_tests=total_tests,
        passed=passed,
        failed=failed,
        skipped=0,
        errors=0,
        duration=45.0 + run_id * 5,
        start_time=datetime.now() - timedelta(minutes=run_id * 10),
    )

    # Add categories
    api_category = CategoryResults(category=TestCategory.API_CONTRACTS)
    api_category.total_tests = 8
    api_category.passed = min(8, passed)
    api_category.failed = max(0, 8 - api_category.passed)
    api_category.duration = 20.0
    results.categories[TestCategory.API_CONTRACTS] = api_category

    comm_category = CategoryResults(category=TestCategory.COMMUNICATION)
    comm_category.total_tests = 6
    comm_category.passed = min(6, passed - api_category.passed)
    comm_category.failed = max(0, 6 - comm_category.passed)
    comm_category.duration = 15.0
    results.categories[TestCategory.COMMUNICATION] = comm_category

    env_category = CategoryResults(category=TestCategory.ENVIRONMENT)
    env_category.total_tests = 4
    env_category.passed = min(4, passed - api_category.passed - comm_category.passed)
    env_category.failed = max(0, 4 - env_category.passed)
    env_category.duration = 8.0
    results.categories[TestCategory.ENVIRONMENT] = env_category

    workflow_category = CategoryResults(category=TestCategory.WORKFLOWS)
    workflow_category.total_tests = 2
    workflow_category.passed = max(
        0, passed - api_category.passed - comm_category.passed - env_category.passed
    )
    workflow_category.failed = max(0, 2 - workflow_category.passed)
    workflow_category.duration = 12.0
    results.categories[TestCategory.WORKFLOWS] = workflow_category

    # Add agent health
    results.agent_health = [
        AgentHealthStatus(
            name="hill_metrics",
            status="healthy" if run_id % 3 != 0 else "degraded",
            response_time=120.0 + run_id * 10,
            available_methods=["get_elevation", "get_slope"],
            missing_methods=[],
            endpoint="http://localhost:8001",
        ),
        AgentHealthStatus(
            name="weather",
            status="healthy" if success_rate > 80 else "degraded",
            response_time=200.0 + run_id * 15,
            available_methods=["get_current"],
            missing_methods=["get_forecast"] if success_rate <= 80 else [],
            endpoint="http://localhost:8002",
        ),
        AgentHealthStatus(
            name="equipment",
            status="healthy",
            response_time=85.0,
            available_methods=["get_lifts", "get_trails"],
            missing_methods=[],
            endpoint="http://localhost:8003",
        ),
    ]

    # Add environment issues occasionally
    if run_id % 4 == 0:
        results.environment_issues = [
            EnvironmentIssue(
                component="disk_space",
                issue_type="low_space",
                description="Log directory approaching capacity",
                severity=Severity.MEDIUM,
                suggested_fix="Clean up old log files",
                detected_value="1.2GB",
                expected_value=">2GB",
            )
        ]

    # Add performance metrics
    results.performance_metrics = PerformanceMetrics(
        total_duration=results.summary.duration,
        setup_duration=8.0,
        execution_duration=results.summary.duration - 15.0,
        teardown_duration=7.0,
        memory_peak=256.0 + run_id * 20,
        memory_average=180.0,
        cpu_peak=75.0,
        cpu_average=35.0,
        network_requests=25 + run_id * 2,
        network_bytes_sent=1024000,
        network_bytes_received=2048000,
    )

    return results


def demonstrate_dashboard_data_management():
    """Demonstrate dashboard data management features."""
    print("📊 Dashboard Data Management Demo")
    print("=" * 40)

    # Initialize dashboard data
    dashboard_data = DashboardData()

    print("🔧 Adding test results with varying success rates...")

    # Add test results with different success rates to show trends
    success_rates = [85.0, 90.0, 75.0, 95.0, 80.0, 88.0, 92.0, 78.0]

    for i, rate in enumerate(success_rates):
        results = create_sample_test_run(i, rate)
        dashboard_data.add_results(results)
        print(
            f"   📈 Run {i + 1}: {rate}% success rate, {results.summary.duration:.1f}s duration"
        )

    print(f"\n✅ Added {len(success_rates)} test runs")

    # Get dashboard data
    data = dashboard_data.get_dashboard_data()

    print("\n📊 Dashboard Summary:")
    print(f"   • Total runs: {data['metadata']['total_runs']}")
    print(f"   • Performance trends: {len(data['performance_trends'])} data points")
    print(f"   • Last updated: {data['last_updated']}")

    # Show historical summary
    if data["historical_summary"]:
        summary = data["historical_summary"]
        print("\n📈 Historical Analysis:")
        print(f"   • Average success rate: {summary['average_success_rate']:.1f}%")
        print(f"   • Average duration: {summary['average_duration']:.1f}s")
        print(f"   • Success trend: {summary['success_trend']}")

    # Show current results
    if data["current_results"]:
        current = data["current_results"]
        print("\n🔍 Latest Test Run:")
        print(f"   • Tests: {current['summary']['total_tests']} total")
        print(f"   • Success rate: {current['summary']['success_rate']:.1f}%")
        print(f"   • Duration: {current['summary']['duration']:.1f}s")
        print(f"   • Categories: {len(current['categories'])}")
        print(f"   • Agents: {len(current['agent_health'])}")
        print(f"   • Environment issues: {len(current['environment_issues'])}")

    return dashboard_data


def demonstrate_dashboard_integration():
    """Demonstrate full dashboard integration."""
    print("\n🔗 Dashboard Integration Demo")
    print("=" * 40)

    # Initialize dashboard
    dashboard = TestResultsDashboard()

    print("📊 Adding realistic test scenarios...")

    # Scenario 1: Successful test run
    print("   ✅ Scenario 1: Successful test run (95% success)")
    results1 = create_sample_test_run(1, 95.0)
    dashboard.add_test_results(results1)

    # Scenario 2: Degraded performance
    print("   ⚠️  Scenario 2: Degraded performance (75% success)")
    results2 = create_sample_test_run(2, 75.0)
    dashboard.add_test_results(results2)

    # Scenario 3: Recovery
    print("   🔄 Scenario 3: Performance recovery (90% success)")
    results3 = create_sample_test_run(3, 90.0)
    dashboard.add_test_results(results3)

    # Get performance summary
    summary = dashboard.get_performance_summary()

    print("\n📊 Performance Summary:")
    print(f"   • Total runs: {summary['total_runs']}")
    print(f"   • Average success rate: {summary['average_success_rate']:.1f}%")
    print(f"   • Average duration: {summary['average_duration']:.1f}s")
    print(f"   • Trend: {summary['success_trend']}")

    return dashboard


def demonstrate_report_generation(dashboard: TestResultsDashboard):
    """Demonstrate report generation from dashboard data."""
    print("\n📄 Report Generation Demo")
    print("=" * 40)

    if not dashboard.dashboard_data.current_results:
        print("❌ No test results available for report generation")
        return

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        print("🔧 Generating reports in multiple formats...")

        # Generate HTML report
        html_report = dashboard.generate_static_report(
            format_type="html",
            output_path=temp_path / "dashboard_report.html",
            include_diagnostics=True,
        )

        if html_report:
            size_kb = html_report.stat().st_size / 1024
            print(f"   📊 HTML Report: {html_report.name} ({size_kb:.1f} KB)")

            # Show HTML content preview
            html_content = html_report.read_text()
            print(
                f"      • Contains {html_content.count('summary-card')} summary cards"
            )
            print(
                f"      • Contains {html_content.count('category-card')} category cards"
            )
            print(
                f"      • Contains {html_content.count('agent-card')} agent health cards"
            )

        # Generate JSON report
        json_report = dashboard.generate_static_report(
            format_type="json",
            output_path=temp_path / "dashboard_report.json",
            include_diagnostics=True,
        )

        if json_report:
            size_kb = json_report.stat().st_size / 1024
            print(f"   📋 JSON Report: {json_report.name} ({size_kb:.1f} KB)")

            # Show JSON structure
            with open(json_report) as f:
                data = json.load(f)
            print(f"      • Metadata: {len(data.get('metadata', {}))} fields")
            print(f"      • Summary: {len(data.get('summary', {}))} metrics")
            print(f"      • Categories: {len(data.get('categories', {}))}")

        # Export dashboard data
        export_path = temp_path / "dashboard_data.json"
        dashboard.export_data(export_path)

        size_kb = export_path.stat().st_size / 1024
        print(f"   💾 Dashboard Data: {export_path.name} ({size_kb:.1f} KB)")

        # Show export structure
        with open(export_path) as f:
            export_data = json.load(f)

        print(
            f"      • Current results: {'Available' if export_data.get('current_results') else 'None'}"
        )
        print(
            f"      • Performance trends: {len(export_data.get('performance_trends', []))} points"
        )
        print(
            f"      • Historical summary: {'Available' if export_data.get('historical_summary') else 'None'}"
        )


def demonstrate_performance_analysis(dashboard_data: DashboardData):
    """Demonstrate performance analysis features."""
    print("\n📈 Performance Analysis Demo")
    print("=" * 40)

    if not dashboard_data.performance_trends:
        print("❌ No performance trends available")
        return

    trends = dashboard_data.performance_trends

    print(f"📊 Analyzing {len(trends)} performance data points...")

    # Calculate statistics
    success_rates = [t["success_rate"] for t in trends]
    durations = [t["duration"] for t in trends]

    avg_success = sum(success_rates) / len(success_rates)
    min_success = min(success_rates)
    max_success = max(success_rates)

    avg_duration = sum(durations) / len(durations)
    min_duration = min(durations)
    max_duration = max(durations)

    print("\n📊 Success Rate Analysis:")
    print(f"   • Average: {avg_success:.1f}%")
    print(f"   • Range: {min_success:.1f}% - {max_success:.1f}%")
    print(f"   • Variation: {max_success - min_success:.1f} percentage points")

    print("\n⏱️  Duration Analysis:")
    print(f"   • Average: {avg_duration:.1f}s")
    print(f"   • Range: {min_duration:.1f}s - {max_duration:.1f}s")
    print(f"   • Variation: {max_duration - min_duration:.1f}s")

    # Show trend over time
    print("\n📈 Trend Analysis:")
    recent_trends = trends[-3:] if len(trends) >= 3 else trends

    for _i, trend in enumerate(recent_trends):
        timestamp = datetime.fromisoformat(trend["timestamp"])
        print(
            f"   • {timestamp.strftime('%H:%M:%S')}: {trend['success_rate']:.1f}% success, {trend['duration']:.1f}s"
        )

    # Calculate trend direction
    if len(success_rates) >= 2:
        recent_avg = sum(success_rates[-3:]) / min(3, len(success_rates))
        early_avg = sum(success_rates[:3]) / min(3, len(success_rates))

        if recent_avg > early_avg + 2:
            trend_direction = "📈 Improving"
        elif recent_avg < early_avg - 2:
            trend_direction = "📉 Declining"
        else:
            trend_direction = "➡️  Stable"

        print(f"\n🎯 Overall Trend: {trend_direction}")
        print(f"   • Early average: {early_avg:.1f}%")
        print(f"   • Recent average: {recent_avg:.1f}%")


def demonstrate_agent_health_monitoring(dashboard: TestResultsDashboard):
    """Demonstrate agent health monitoring features."""
    print("\n🏥 Agent Health Monitoring Demo")
    print("=" * 40)

    current_results = dashboard.dashboard_data.current_results
    if not current_results or not current_results.agent_health:
        print("❌ No agent health data available")
        return

    print(f"🔍 Monitoring {len(current_results.agent_health)} agents...")

    for agent in current_results.agent_health:
        status_emoji = {"healthy": "✅", "degraded": "⚠️", "failed": "❌"}.get(
            agent.status, "❓"
        )

        print(f"\n{status_emoji} {agent.name.upper()}")
        print(f"   • Status: {agent.status}")
        print(f"   • Response time: {agent.response_time:.1f}ms")
        print(f"   • Endpoint: {agent.endpoint}")
        print(f"   • Available methods: {len(agent.available_methods)}")

        if agent.available_methods:
            print(f"     - {', '.join(agent.available_methods)}")

        if agent.missing_methods:
            print(f"   • Missing methods: {len(agent.missing_methods)}")
            print(f"     - {', '.join(agent.missing_methods)}")

        if agent.last_error:
            print(f"   • Last error: {agent.last_error}")

    # Health summary
    healthy_count = sum(
        1 for agent in current_results.agent_health if agent.status == "healthy"
    )
    degraded_count = sum(
        1 for agent in current_results.agent_health if agent.status == "degraded"
    )
    failed_count = sum(
        1 for agent in current_results.agent_health if agent.status == "failed"
    )

    print("\n📊 Health Summary:")
    print(f"   • Healthy: {healthy_count}")
    print(f"   • Degraded: {degraded_count}")
    print(f"   • Failed: {failed_count}")

    overall_health = (
        "Excellent"
        if failed_count == 0 and degraded_count == 0
        else "Good"
        if failed_count == 0
        else "Poor"
    )

    print(f"   • Overall health: {overall_health}")


def main():
    """Main demonstration function."""
    print("🎯 Integration Test Dashboard Showcase")
    print("=" * 50)

    try:
        # Demonstrate data management
        dashboard_data = demonstrate_dashboard_data_management()

        # Demonstrate dashboard integration
        dashboard = demonstrate_dashboard_integration()

        # Demonstrate report generation
        demonstrate_report_generation(dashboard)

        # Demonstrate performance analysis
        demonstrate_performance_analysis(dashboard_data)

        # Demonstrate agent health monitoring
        demonstrate_agent_health_monitoring(dashboard)

        print("\n✨ Dashboard Showcase Complete!")
        print("\n🎯 Key Features Demonstrated:")
        print("   ✅ Multi-run test result tracking")
        print("   ✅ Performance trend analysis")
        print("   ✅ Historical data management")
        print("   ✅ Agent health monitoring")
        print("   ✅ Environment issue tracking")
        print("   ✅ Multi-format report generation")
        print("   ✅ Data export capabilities")
        print("   ✅ Statistical analysis")
        print("   ✅ Trend detection")

        print("\n💡 Dashboard Benefits:")
        print("   • Real-time visibility into test health")
        print("   • Historical performance tracking")
        print("   • Early detection of performance degradation")
        print("   • Comprehensive diagnostic information")
        print("   • Multiple output formats for different audiences")
        print("   • Integration with existing test infrastructure")

    except Exception as e:
        print(f"\n❌ Showcase failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
