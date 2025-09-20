"""
Test Result Report Generator.

Generates comprehensive test reports in multiple formats (JSON, HTML, JUnit)
with visual indicators, performance metrics tracking, and detailed diagnostics.
"""

import gzip
import json
import xml.etree.ElementTree as ET
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

from .config import TestConfig
from .models import AgentHealthStatus
from .models import Severity
from .models import TestResults
from .models import TestStatus

logger = structlog.get_logger(__name__)


class ReportFormat:
    """Supported report formats."""

    JSON = "json"
    HTML = "html"
    JUNIT = "junit"
    MARKDOWN = "markdown"


class ReportGenerator:
    """
    Generates comprehensive test reports in multiple formats.

    Supports JSON, HTML, JUnit XML, and Markdown formats with visual indicators,
    performance metrics, and detailed diagnostic information.
    """

    def __init__(self, config: TestConfig | None = None):
        """
        Initialize the report generator.

        Args:
            config: Optional test configuration
        """
        self.config = config
        self.logger = structlog.get_logger(__name__)

    def generate_report(
        self,
        results: TestResults,
        format_type: str,
        output_path: Path | None = None,
        include_diagnostics: bool = True,
        compress: bool = False,
    ) -> Path:
        """
        Generate a test report in the specified format.

        Args:
            results: Test results to report on
            format_type: Report format (json, html, junit, markdown)
            output_path: Optional output file path
            include_diagnostics: Whether to include detailed diagnostics
            compress: Whether to compress the output

        Returns:
            Path to the generated report file
        """
        self.logger.info(
            f"Generating {format_type} report",
            total_tests=results.summary.total_tests,
            passed=results.summary.passed,
            failed=results.summary.failed,
            include_diagnostics=include_diagnostics,
        )

        # Generate report content based on format
        if format_type == ReportFormat.JSON:
            content = self._generate_json_report(results, include_diagnostics)
            extension = ".json"
        elif format_type == ReportFormat.HTML:
            content = self._generate_html_report(results, include_diagnostics)
            extension = ".html"
        elif format_type == ReportFormat.JUNIT:
            content = self._generate_junit_report(results)
            extension = ".xml"
        elif format_type == ReportFormat.MARKDOWN:
            content = self._generate_markdown_report(results, include_diagnostics)
            extension = ".md"
        else:
            raise ValueError(f"Unsupported report format: {format_type}")

        # Determine output path
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_report_{timestamp}{extension}"
            output_path = Path.cwd() / "test_results" / filename

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write content
        if compress and format_type in [
            ReportFormat.JSON,
            ReportFormat.HTML,
            ReportFormat.MARKDOWN,
        ]:
            # Compress text-based formats
            compressed_content = gzip.compress(content.encode("utf-8"))
            output_path = output_path.with_suffix(output_path.suffix + ".gz")
            output_path.write_bytes(compressed_content)
        else:
            if isinstance(content, str):
                output_path.write_text(content, encoding="utf-8")
            else:
                output_path.write_bytes(content)

        self.logger.info(
            "Report generated successfully",
            format=format_type,
            output_path=str(output_path),
            size_bytes=output_path.stat().st_size,
            compressed=compress,
        )

        return output_path

    def generate_multiple_formats(
        self,
        results: TestResults,
        formats: list[str],
        output_dir: Path | None = None,
        include_diagnostics: bool = True,
    ) -> dict[str, Path]:
        """
        Generate reports in multiple formats.

        Args:
            results: Test results to report on
            formats: List of report formats to generate
            output_dir: Output directory for all reports
            include_diagnostics: Whether to include detailed diagnostics

        Returns:
            Dictionary mapping format to output path
        """
        if output_dir is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = Path.cwd() / "test_results" / f"report_{timestamp}"

        output_dir.mkdir(parents=True, exist_ok=True)

        report_paths = {}

        for format_type in formats:
            try:
                output_path = output_dir / f"test_report.{format_type}"
                if format_type == ReportFormat.JUNIT:
                    output_path = output_dir / "test_report.xml"

                report_path = self.generate_report(
                    results=results,
                    format_type=format_type,
                    output_path=output_path,
                    include_diagnostics=include_diagnostics,
                )

                report_paths[format_type] = report_path

            except Exception as e:
                self.logger.error(
                    f"Failed to generate {format_type} report",
                    error=str(e),
                    exc_info=True,
                )

        return report_paths

    def _generate_json_report(
        self, results: TestResults, include_diagnostics: bool
    ) -> str:
        """Generate JSON format report."""
        report_data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "generator": "IntegrationTestReportGenerator",
                "version": "1.0.0",
                "include_diagnostics": include_diagnostics,
            },
            "summary": results.summary.to_dict(),
            "categories": {
                category.value: category_results.to_dict()
                for category, category_results in results.categories.items()
            },
            "agent_health": [
                agent.to_dict()
                if hasattr(agent, "to_dict")
                else self._agent_to_dict(agent)
                for agent in results.agent_health
            ],
            "environment_issues": [
                issue.to_dict() for issue in results.environment_issues
            ],
        }

        # Add performance metrics if available
        if results.performance_metrics:
            report_data["performance_metrics"] = asdict(results.performance_metrics)

        # Add diagnostics if requested
        if include_diagnostics:
            report_data["diagnostics"] = results.diagnostics

            # Add detailed test information
            report_data["detailed_tests"] = {}
            for category, category_results in results.categories.items():
                report_data["detailed_tests"][category.value] = [
                    test.to_dict() for test in category_results.tests
                ]

        return json.dumps(report_data, indent=2, default=str)

    def _generate_html_report(
        self, results: TestResults, include_diagnostics: bool
    ) -> str:
        """Generate HTML format report with visual indicators."""
        # Calculate summary statistics
        success_rate = results.summary.success_rate
        status_color = self._get_status_color(success_rate)

        # Generate HTML content
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Integration Test Report</title>
    <style>
        {self._get_html_styles()}
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>Integration Test Report</h1>
            <div class="metadata">
                <p>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                <p>Duration: {results.summary.duration:.2f}s</p>
            </div>
        </header>

        <section class="summary">
            <h2>Test Summary</h2>
            <div class="summary-grid">
                <div class="summary-card">
                    <div class="summary-number">{results.summary.total_tests}</div>
                    <div class="summary-label">Total Tests</div>
                </div>
                <div class="summary-card success">
                    <div class="summary-number">{results.summary.passed}</div>
                    <div class="summary-label">Passed</div>
                </div>
                <div class="summary-card failure">
                    <div class="summary-number">{results.summary.failed}</div>
                    <div class="summary-label">Failed</div>
                </div>
                <div class="summary-card skipped">
                    <div class="summary-number">{results.summary.skipped}</div>
                    <div class="summary-label">Skipped</div>
                </div>
                <div class="summary-card rate" style="background-color: {status_color}">
                    <div class="summary-number">{success_rate:.1f}%</div>
                    <div class="summary-label">Success Rate</div>
                </div>
            </div>
        </section>

        {self._generate_category_section_html(results)}

        {self._generate_agent_health_section_html(results)}

        {self._generate_environment_section_html(results)}

        {self._generate_performance_section_html(results) if results.performance_metrics else ""}

        {self._generate_diagnostics_section_html(results) if include_diagnostics else ""}

        <footer class="footer">
            <p>Generated by Integration Test Report Generator v1.0.0</p>
        </footer>
    </div>

    <script>
        {self._get_html_scripts()}
    </script>
</body>
</html>
"""

        return html_content

    def _generate_junit_report(self, results: TestResults) -> str:
        """Generate JUnit XML format report."""
        # Create root testsuites element
        testsuites = ET.Element("testsuites")
        testsuites.set("name", "Integration Tests")
        testsuites.set("tests", str(results.summary.total_tests))
        testsuites.set("failures", str(results.summary.failed))
        testsuites.set("errors", str(results.summary.errors))
        testsuites.set("skipped", str(results.summary.skipped))
        testsuites.set("time", str(results.summary.duration))
        testsuites.set("timestamp", results.summary.start_time.isoformat())

        # Create testsuite for each category
        for category, category_results in results.categories.items():
            testsuite = ET.SubElement(testsuites, "testsuite")
            testsuite.set("name", category.value)
            testsuite.set("tests", str(category_results.total_tests))
            testsuite.set("failures", str(category_results.failed))
            testsuite.set("errors", str(category_results.errors))
            testsuite.set("skipped", str(category_results.skipped))
            testsuite.set("time", str(category_results.duration))

            # Add individual test cases
            for test in category_results.tests:
                testcase = ET.SubElement(testsuite, "testcase")
                testcase.set("name", test.name)
                testcase.set("classname", f"integration.{category.value}")
                testcase.set("time", str(test.duration))

                if test.status == TestStatus.FAILED:
                    failure = ET.SubElement(testcase, "failure")
                    failure.set(
                        "message", test.error.message if test.error else "Test failed"
                    )
                    if test.error and test.error.stack_trace:
                        failure.text = test.error.stack_trace
                elif test.status == TestStatus.ERROR:
                    error = ET.SubElement(testcase, "error")
                    error.set(
                        "message", test.error.message if test.error else "Test error"
                    )
                    if test.error and test.error.stack_trace:
                        error.text = test.error.stack_trace
                elif test.status == TestStatus.SKIPPED:
                    skipped = ET.SubElement(testcase, "skipped")
                    skipped.set("message", test.message or "Test skipped")

        # Convert to string
        return ET.tostring(testsuites, encoding="unicode", xml_declaration=True)

    def _generate_markdown_report(
        self, results: TestResults, include_diagnostics: bool
    ) -> str:
        """Generate Markdown format report."""
        success_rate = results.summary.success_rate
        status_emoji = (
            "✅" if success_rate >= 90 else "⚠️" if success_rate >= 70 else "❌"
        )

        md_content = f"""# Integration Test Report {status_emoji}

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Duration:** {results.summary.duration:.2f}s
**Success Rate:** {success_rate:.1f}%

## Summary

| Metric | Count |
|--------|-------|
| Total Tests | {results.summary.total_tests} |
| ✅ Passed | {results.summary.passed} |
| ❌ Failed | {results.summary.failed} |
| ⏭️ Skipped | {results.summary.skipped} |
| 🔥 Errors | {results.summary.errors} |

## Test Categories

"""

        # Add category results
        for category, category_results in results.categories.items():
            category_emoji = (
                "✅"
                if category_results.success_rate >= 90
                else "⚠️"
                if category_results.success_rate >= 70
                else "❌"
            )

            md_content += f"""### {category.value.replace("_", " ").title()} {category_emoji}

- **Tests:** {category_results.total_tests}
- **Success Rate:** {category_results.success_rate:.1f}%
- **Duration:** {category_results.duration:.2f}s

"""

            if category_results.has_failures and include_diagnostics:
                md_content += "**Failed Tests:**\n"
                for test in category_results.tests:
                    if test.status in [TestStatus.FAILED, TestStatus.ERROR]:
                        md_content += f"- ❌ {test.name}: {test.error.message if test.error else 'Unknown error'}\n"
                md_content += "\n"

        # Add agent health
        if results.agent_health:
            md_content += "## Agent Health\n\n"
            for agent in results.agent_health:
                status_emoji = (
                    "✅"
                    if agent.status == "healthy"
                    else "⚠️"
                    if agent.status == "degraded"
                    else "❌"
                )
                md_content += f"- {status_emoji} **{agent.name}**: {agent.status}"
                if agent.response_time:
                    md_content += f" ({agent.response_time:.2f}ms)"
                md_content += "\n"
            md_content += "\n"

        # Add environment issues
        if results.environment_issues:
            md_content += "## Environment Issues\n\n"
            for issue in results.environment_issues:
                severity_emoji = (
                    "🔥"
                    if issue.severity == Severity.CRITICAL
                    else "⚠️"
                    if issue.severity == Severity.HIGH
                    else "ℹ️"
                )
                md_content += (
                    f"- {severity_emoji} **{issue.component}**: {issue.description}\n"
                )
            md_content += "\n"

        # Add performance metrics
        if results.performance_metrics:
            md_content += f"""## Performance Metrics

- **Total Duration:** {results.performance_metrics.total_duration:.2f}s
- **Setup Duration:** {results.performance_metrics.setup_duration:.2f}s
- **Execution Duration:** {results.performance_metrics.execution_duration:.2f}s
- **Network Requests:** {results.performance_metrics.network_requests}
- **Requests/Second:** {results.performance_metrics.requests_per_second:.2f}

"""

        if include_diagnostics and results.diagnostics:
            md_content += "## Diagnostics\n\n"
            md_content += "```json\n"
            md_content += json.dumps(results.diagnostics, indent=2, default=str)
            md_content += "\n```\n"

        return md_content

    def _generate_category_section_html(self, results: TestResults) -> str:
        """Generate HTML for test categories section."""
        html = '<section class="categories"><h2>Test Categories</h2><div class="category-grid">'

        for category, category_results in results.categories.items():
            success_rate = category_results.success_rate
            status_class = self._get_status_class(success_rate)

            html += f"""
            <div class="category-card {status_class}">
                <h3>{category.value.replace("_", " ").title()}</h3>
                <div class="category-stats">
                    <div class="stat">
                        <span class="stat-number">{category_results.total_tests}</span>
                        <span class="stat-label">Tests</span>
                    </div>
                    <div class="stat">
                        <span class="stat-number">{success_rate:.1f}%</span>
                        <span class="stat-label">Success</span>
                    </div>
                    <div class="stat">
                        <span class="stat-number">{category_results.duration:.2f}s</span>
                        <span class="stat-label">Duration</span>
                    </div>
                </div>
                <div class="test-breakdown">
                    <span class="passed">{category_results.passed} passed</span>
                    <span class="failed">{category_results.failed} failed</span>
                    <span class="skipped">{category_results.skipped} skipped</span>
                </div>
            </div>
            """

        html += "</div></section>"
        return html

    def _generate_agent_health_section_html(self, results: TestResults) -> str:
        """Generate HTML for agent health section."""
        if not results.agent_health:
            return ""

        html = '<section class="agent-health"><h2>Agent Health</h2><div class="agent-grid">'

        for agent in results.agent_health:
            status_class = (
                "healthy"
                if agent.status == "healthy"
                else "degraded"
                if agent.status == "degraded"
                else "failed"
            )

            html += f"""
            <div class="agent-card {status_class}">
                <h3>{agent.name}</h3>
                <div class="agent-status">{agent.status.title()}</div>
                <div class="agent-details">
                    {f"<div>Response Time: {agent.response_time:.2f}ms</div>" if agent.response_time else ""}
                    <div>Methods: {len(agent.available_methods)}</div>
                    {f"<div>Missing: {len(agent.missing_methods)}</div>" if agent.missing_methods else ""}
                </div>
            </div>
            """

        html += "</div></section>"
        return html

    def _generate_environment_section_html(self, results: TestResults) -> str:
        """Generate HTML for environment issues section."""
        if not results.environment_issues:
            return ""

        html = '<section class="environment"><h2>Environment Issues</h2><div class="issue-list">'

        for issue in results.environment_issues:
            severity_class = issue.severity.value.lower()

            html += f"""
            <div class="issue-item {severity_class}">
                <div class="issue-header">
                    <span class="issue-component">{issue.component}</span>
                    <span class="issue-severity">{issue.severity.value}</span>
                </div>
                <div class="issue-description">{issue.description}</div>
                {f'<div class="issue-fix">{issue.suggested_fix}</div>' if issue.suggested_fix else ""}
            </div>
            """

        html += "</div></section>"
        return html

    def _generate_performance_section_html(self, results: TestResults) -> str:
        """Generate HTML for performance metrics section."""
        if not results.performance_metrics:
            return ""

        metrics = results.performance_metrics

        html = f"""
        <section class="performance">
            <h2>Performance Metrics</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">{metrics.total_duration:.2f}s</div>
                    <div class="metric-label">Total Duration</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{metrics.execution_duration:.2f}s</div>
                    <div class="metric-label">Execution Time</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{metrics.network_requests}</div>
                    <div class="metric-label">Network Requests</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{metrics.requests_per_second:.2f}</div>
                    <div class="metric-label">Requests/Second</div>
                </div>
            </div>
        </section>
        """

        return html

    def _generate_diagnostics_section_html(self, results: TestResults) -> str:
        """Generate HTML for diagnostics section."""
        if not results.diagnostics:
            return ""

        diagnostics_json = json.dumps(results.diagnostics, indent=2, default=str)

        html = f"""
        <section class="diagnostics">
            <h2>Diagnostics</h2>
            <details>
                <summary>View Diagnostic Data</summary>
                <pre class="diagnostics-data">{diagnostics_json}</pre>
            </details>
        </section>
        """

        return html

    def _get_html_styles(self) -> str:
        """Get CSS styles for HTML report."""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }

        .header {
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }

        .header h1 {
            color: #2c3e50;
            margin-bottom: 10px;
        }

        .metadata p {
            color: #7f8c8d;
            margin: 5px 0;
        }

        .summary {
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }

        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }

        .summary-card {
            text-align: center;
            padding: 20px;
            border-radius: 8px;
            background: #ecf0f1;
        }

        .summary-card.success { background: #d5f4e6; }
        .summary-card.failure { background: #ffeaa7; }
        .summary-card.skipped { background: #ddd6fe; }
        .summary-card.rate { color: white; }

        .summary-number {
            font-size: 2em;
            font-weight: bold;
            margin-bottom: 5px;
        }

        .summary-label {
            font-size: 0.9em;
            opacity: 0.8;
        }

        .categories, .agent-health, .environment, .performance {
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }

        .category-grid, .agent-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }

        .category-card, .agent-card {
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #3498db;
        }

        .category-card.success, .agent-card.healthy { border-left-color: #27ae60; background: #d5f4e6; }
        .category-card.warning, .agent-card.degraded { border-left-color: #f39c12; background: #ffeaa7; }
        .category-card.failure, .agent-card.failed { border-left-color: #e74c3c; background: #ffebee; }

        .category-stats {
            display: flex;
            justify-content: space-between;
            margin: 15px 0;
        }

        .stat {
            text-align: center;
        }

        .stat-number {
            display: block;
            font-size: 1.5em;
            font-weight: bold;
        }

        .stat-label {
            font-size: 0.8em;
            opacity: 0.7;
        }

        .test-breakdown {
            font-size: 0.9em;
            opacity: 0.8;
        }

        .test-breakdown span {
            margin-right: 15px;
        }

        .passed { color: #27ae60; }
        .failed { color: #e74c3c; }
        .skipped { color: #8e44ad; }

        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }

        .metric-card {
            text-align: center;
            padding: 20px;
            background: #ecf0f1;
            border-radius: 8px;
        }

        .metric-value {
            font-size: 1.8em;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 5px;
        }

        .metric-label {
            font-size: 0.9em;
            opacity: 0.7;
        }

        .issue-list {
            margin-top: 20px;
        }

        .issue-item {
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 8px;
            border-left: 4px solid #3498db;
        }

        .issue-item.critical { border-left-color: #e74c3c; background: #ffebee; }
        .issue-item.high { border-left-color: #f39c12; background: #ffeaa7; }
        .issue-item.medium { border-left-color: #3498db; background: #e3f2fd; }
        .issue-item.low { border-left-color: #27ae60; background: #d5f4e6; }

        .issue-header {
            display: flex;
            justify-content: space-between;
            font-weight: bold;
            margin-bottom: 5px;
        }

        .issue-severity {
            text-transform: uppercase;
            font-size: 0.8em;
            padding: 2px 8px;
            border-radius: 4px;
            background: rgba(0,0,0,0.1);
        }

        .diagnostics {
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }

        .diagnostics-data {
            background: #2c3e50;
            color: #ecf0f1;
            padding: 20px;
            border-radius: 4px;
            overflow-x: auto;
            font-size: 0.9em;
        }

        .footer {
            text-align: center;
            padding: 20px;
            color: #7f8c8d;
            font-size: 0.9em;
        }

        details {
            margin-top: 15px;
        }

        summary {
            cursor: pointer;
            padding: 10px;
            background: #ecf0f1;
            border-radius: 4px;
            font-weight: bold;
        }

        summary:hover {
            background: #d5dbdb;
        }
        """

    def _get_html_scripts(self) -> str:
        """Get JavaScript for HTML report."""
        return """
        // Add interactive features
        document.addEventListener('DOMContentLoaded', function() {
            // Add click handlers for expandable sections
            const cards = document.querySelectorAll('.category-card, .agent-card');
            cards.forEach(card => {
                card.style.cursor = 'pointer';
                card.addEventListener('click', function() {
                    this.style.transform = this.style.transform ? '' : 'scale(1.02)';
                });
            });

            // Add tooltips for metrics
            const metrics = document.querySelectorAll('.metric-card');
            metrics.forEach(metric => {
                metric.title = 'Click for more details';
            });
        });
        """

    def _get_status_color(self, success_rate: float) -> str:
        """Get color based on success rate."""
        if success_rate >= 90:
            return "#27ae60"  # Green
        elif success_rate >= 70:
            return "#f39c12"  # Orange
        else:
            return "#e74c3c"  # Red

    def _get_status_class(self, success_rate: float) -> str:
        """Get CSS class based on success rate."""
        if success_rate >= 90:
            return "success"
        elif success_rate >= 70:
            return "warning"
        else:
            return "failure"

    def _agent_to_dict(self, agent: AgentHealthStatus) -> dict[str, Any]:
        """Convert agent to dictionary if it doesn't have to_dict method."""
        return {
            "name": agent.name,
            "status": agent.status,
            "response_time": agent.response_time,
            "last_error": agent.last_error,
            "available_methods": agent.available_methods,
            "missing_methods": agent.missing_methods,
            "endpoint": getattr(agent, "endpoint", None),
            "version": getattr(agent, "version", None),
            "uptime": getattr(agent, "uptime", None),
            "memory_usage": getattr(agent, "memory_usage", None),
        }
