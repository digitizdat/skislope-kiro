"""
Test Results Dashboard.

Provides a web-based dashboard for viewing test results with visual indicators,
real-time updates, and interactive features for exploring test data.
"""

import json
import threading
import webbrowser
from datetime import datetime
from http.server import HTTPServer
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any

import structlog

from .config import TestConfig
from .models import TestResults
from .report_generator import ReportGenerator

logger = structlog.get_logger(__name__)


class DashboardData:
    """Manages dashboard data and state."""

    def __init__(self):
        self.test_results: list[TestResults] = []
        self.current_results: TestResults | None = None
        self.historical_data: dict[str, Any] = {}
        self.performance_trends: list[dict[str, Any]] = []
        self.last_updated: datetime | None = None

    def add_results(self, results: TestResults) -> None:
        """Add new test results."""
        self.test_results.append(results)
        self.current_results = results
        self.last_updated = datetime.now()

        # Update performance trends
        self._update_performance_trends(results)

        # Maintain only last 50 results for performance
        if len(self.test_results) > 50:
            self.test_results = self.test_results[-50:]

    def _update_performance_trends(self, results: TestResults) -> None:
        """Update performance trend data."""
        trend_point = {
            "timestamp": results.summary.start_time.isoformat(),
            "duration": results.summary.duration,
            "success_rate": results.summary.success_rate,
            "total_tests": results.summary.total_tests,
            "passed": results.summary.passed,
            "failed": results.summary.failed,
        }

        # Add category-specific metrics
        for category, category_results in results.categories.items():
            trend_point[f"{category.value}_duration"] = category_results.duration
            trend_point[f"{category.value}_success_rate"] = (
                category_results.success_rate
            )

        self.performance_trends.append(trend_point)

        # Keep only last 100 trend points
        if len(self.performance_trends) > 100:
            self.performance_trends = self.performance_trends[-100:]

    def get_dashboard_data(self) -> dict[str, Any]:
        """Get complete dashboard data."""
        return {
            "current_results": self.current_results.to_dict()
            if self.current_results
            else None,
            "historical_summary": self._get_historical_summary(),
            "performance_trends": self.performance_trends,
            "last_updated": self.last_updated.isoformat()
            if self.last_updated
            else None,
            "metadata": {
                "total_runs": len(self.test_results),
                "data_range": self._get_data_range(),
            },
        }

    def _get_historical_summary(self) -> dict[str, Any]:
        """Get summary of historical test data."""
        if not self.test_results:
            return {}

        # Calculate averages and trends
        recent_results = self.test_results[-10:]  # Last 10 runs

        avg_success_rate = sum(r.summary.success_rate for r in recent_results) / len(
            recent_results
        )
        avg_duration = sum(r.summary.duration for r in recent_results) / len(
            recent_results
        )

        # Calculate trend direction
        if len(recent_results) >= 2:
            recent_success = (
                recent_results[-3:] if len(recent_results) >= 3 else recent_results[-2:]
            )
            success_trend = (
                "improving"
                if recent_success[-1].summary.success_rate
                > recent_success[0].summary.success_rate
                else "declining"
            )
        else:
            success_trend = "stable"

        return {
            "average_success_rate": avg_success_rate,
            "average_duration": avg_duration,
            "success_trend": success_trend,
            "total_runs": len(self.test_results),
            "last_run": self.test_results[-1].summary.start_time.isoformat()
            if self.test_results
            else None,
        }

    def _get_data_range(self) -> dict[str, str]:
        """Get the date range of available data."""
        if not self.test_results:
            return {}

        start_date = min(r.summary.start_time for r in self.test_results)
        end_date = max(r.summary.start_time for r in self.test_results)

        return {"start": start_date.isoformat(), "end": end_date.isoformat()}


class DashboardServer:
    """HTTP server for the test results dashboard."""

    def __init__(self, dashboard_data: DashboardData, port: int = 8080):
        self.dashboard_data = dashboard_data
        self.port = port
        self.server: HTTPServer | None = None
        self.server_thread: threading.Thread | None = None
        self.dashboard_dir = Path(__file__).parent / "dashboard_static"
        self._setup_dashboard_files()

    def _setup_dashboard_files(self) -> None:
        """Set up static dashboard files."""
        self.dashboard_dir.mkdir(exist_ok=True)

        # Create HTML dashboard
        html_content = self._generate_dashboard_html()
        (self.dashboard_dir / "index.html").write_text(html_content)

        # Create CSS styles
        css_content = self._generate_dashboard_css()
        (self.dashboard_dir / "styles.css").write_text(css_content)

        # Create JavaScript
        js_content = self._generate_dashboard_js()
        (self.dashboard_dir / "dashboard.js").write_text(js_content)

    def start(self) -> str:
        """Start the dashboard server."""

        class DashboardHandler(SimpleHTTPRequestHandler):
            def __init__(
                self, *args, dashboard_data=None, dashboard_dir=None, **kwargs
            ):
                self.dashboard_data = dashboard_data
                super().__init__(*args, directory=str(dashboard_dir), **kwargs)

            def do_GET(self):
                if self.path == "/api/data":
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()

                    data = self.dashboard_data.get_dashboard_data()
                    self.wfile.write(json.dumps(data, default=str).encode())
                else:
                    super().do_GET()

        # Create server with custom handler
        def handler(*args, **kwargs):
            return DashboardHandler(
                *args,
                dashboard_data=self.dashboard_data,
                dashboard_dir=self.dashboard_dir,
                **kwargs,
            )

        try:
            self.server = HTTPServer(("localhost", self.port), handler)
            self.server_thread = threading.Thread(
                target=self.server.serve_forever, daemon=True
            )
            self.server_thread.start()

            url = f"http://localhost:{self.port}"
            logger.info(f"Dashboard server started at {url}")
            return url

        except OSError as e:
            if e.errno in (48, 98):  # Address already in use (macOS: 48, Linux: 98)
                self.port += 1
                return self.start()  # Try next port
            raise

    def stop(self) -> None:
        """Stop the dashboard server."""
        if self.server:
            try:
                self.server.shutdown()
                self.server.server_close()
                logger.info("Dashboard server stopped")
            except Exception as e:
                logger.warning(f"Error stopping dashboard server: {e}")
            finally:
                self.server = None
                self.server_thread = None

    def _generate_dashboard_html(self) -> str:
        """Generate the main dashboard HTML."""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Integration Test Dashboard</title>
    <link rel="stylesheet" href="styles.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <div class="dashboard">
        <header class="dashboard-header">
            <h1>Integration Test Dashboard</h1>
            <div class="header-controls">
                <button id="refresh-btn" class="btn btn-primary">Refresh</button>
                <button id="auto-refresh-btn" class="btn btn-secondary">Auto Refresh: OFF</button>
                <span id="last-updated" class="last-updated"></span>
            </div>
        </header>

        <div class="dashboard-content">
            <!-- Summary Cards -->
            <section class="summary-section">
                <div class="summary-cards">
                    <div class="summary-card" id="total-tests-card">
                        <div class="card-icon">📊</div>
                        <div class="card-content">
                            <div class="card-number" id="total-tests">-</div>
                            <div class="card-label">Total Tests</div>
                        </div>
                    </div>

                    <div class="summary-card" id="success-rate-card">
                        <div class="card-icon">✅</div>
                        <div class="card-content">
                            <div class="card-number" id="success-rate">-</div>
                            <div class="card-label">Success Rate</div>
                        </div>
                    </div>

                    <div class="summary-card" id="duration-card">
                        <div class="card-icon">⏱️</div>
                        <div class="card-content">
                            <div class="card-number" id="duration">-</div>
                            <div class="card-label">Duration</div>
                        </div>
                    </div>

                    <div class="summary-card" id="trend-card">
                        <div class="card-icon">📈</div>
                        <div class="card-content">
                            <div class="card-number" id="trend">-</div>
                            <div class="card-label">Trend</div>
                        </div>
                    </div>
                </div>
            </section>

            <!-- Charts Section -->
            <section class="charts-section">
                <div class="chart-container">
                    <h3>Success Rate Trend</h3>
                    <canvas id="success-trend-chart"></canvas>
                </div>

                <div class="chart-container">
                    <h3>Test Duration Trend</h3>
                    <canvas id="duration-trend-chart"></canvas>
                </div>
            </section>

            <!-- Categories Section -->
            <section class="categories-section">
                <h3>Test Categories</h3>
                <div class="categories-grid" id="categories-grid">
                    <!-- Categories will be populated by JavaScript -->
                </div>
            </section>

            <!-- Agent Health Section -->
            <section class="agent-health-section">
                <h3>Agent Health</h3>
                <div class="agent-grid" id="agent-grid">
                    <!-- Agent health will be populated by JavaScript -->
                </div>
            </section>

            <!-- Environment Issues Section -->
            <section class="environment-section" id="environment-section" style="display: none;">
                <h3>Environment Issues</h3>
                <div class="issues-list" id="issues-list">
                    <!-- Issues will be populated by JavaScript -->
                </div>
            </section>

            <!-- Recent Tests Section -->
            <section class="recent-tests-section">
                <h3>Recent Test Results</h3>
                <div class="test-history" id="test-history">
                    <!-- Test history will be populated by JavaScript -->
                </div>
            </section>
        </div>
    </div>

    <script src="dashboard.js"></script>
</body>
</html>
"""

    def _generate_dashboard_css(self) -> str:
        """Generate CSS styles for the dashboard."""
        return """
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background-color: #f5f7fa;
    color: #2d3748;
    line-height: 1.6;
}

.dashboard {
    min-height: 100vh;
}

.dashboard-header {
    background: white;
    padding: 1.5rem 2rem;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.dashboard-header h1 {
    color: #2d3748;
    font-size: 1.8rem;
    font-weight: 600;
}

.header-controls {
    display: flex;
    align-items: center;
    gap: 1rem;
}

.btn {
    padding: 0.5rem 1rem;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.9rem;
    font-weight: 500;
    transition: all 0.2s;
}

.btn-primary {
    background: #4299e1;
    color: white;
}

.btn-primary:hover {
    background: #3182ce;
}

.btn-secondary {
    background: #e2e8f0;
    color: #4a5568;
}

.btn-secondary:hover {
    background: #cbd5e0;
}

.btn-secondary.active {
    background: #48bb78;
    color: white;
}

.last-updated {
    font-size: 0.8rem;
    color: #718096;
}

.dashboard-content {
    padding: 2rem;
    max-width: 1400px;
    margin: 0 auto;
}

.summary-section {
    margin-bottom: 2rem;
}

.summary-cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 1.5rem;
}

.summary-card {
    background: white;
    padding: 1.5rem;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    display: flex;
    align-items: center;
    gap: 1rem;
    transition: transform 0.2s;
}

.summary-card:hover {
    transform: translateY(-2px);
}

.card-icon {
    font-size: 2rem;
    opacity: 0.8;
}

.card-content {
    flex: 1;
}

.card-number {
    font-size: 2rem;
    font-weight: 700;
    margin-bottom: 0.25rem;
}

.card-label {
    font-size: 0.9rem;
    color: #718096;
    font-weight: 500;
}

.summary-card.success .card-number { color: #38a169; }
.summary-card.warning .card-number { color: #d69e2e; }
.summary-card.error .card-number { color: #e53e3e; }

.charts-section {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 2rem;
    margin-bottom: 2rem;
}

.chart-container {
    background: white;
    padding: 1.5rem;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.chart-container h3 {
    margin-bottom: 1rem;
    color: #2d3748;
    font-size: 1.1rem;
}

.categories-section, .agent-health-section, .environment-section, .recent-tests-section {
    background: white;
    padding: 1.5rem;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    margin-bottom: 2rem;
}

.categories-section h3, .agent-health-section h3, .environment-section h3, .recent-tests-section h3 {
    margin-bottom: 1rem;
    color: #2d3748;
    font-size: 1.2rem;
}

.categories-grid, .agent-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 1rem;
}

.category-card, .agent-card {
    padding: 1rem;
    border-radius: 8px;
    border-left: 4px solid #4299e1;
    background: #f7fafc;
}

.category-card.success, .agent-card.healthy {
    border-left-color: #38a169;
    background: #f0fff4;
}

.category-card.warning, .agent-card.degraded {
    border-left-color: #d69e2e;
    background: #fffbeb;
}

.category-card.error, .agent-card.failed {
    border-left-color: #e53e3e;
    background: #fed7d7;
}

.category-header, .agent-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
}

.category-name, .agent-name {
    font-weight: 600;
    font-size: 1rem;
}

.category-status, .agent-status {
    font-size: 0.8rem;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-weight: 500;
}

.category-status.success, .agent-status.healthy {
    background: #c6f6d5;
    color: #22543d;
}

.category-status.warning, .agent-status.degraded {
    background: #faf089;
    color: #744210;
}

.category-status.error, .agent-status.failed {
    background: #fed7d7;
    color: #742a2a;
}

.category-stats, .agent-stats {
    display: flex;
    justify-content: space-between;
    font-size: 0.9rem;
    color: #4a5568;
}

.issues-list {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}

.issue-item {
    padding: 1rem;
    border-radius: 8px;
    border-left: 4px solid #4299e1;
    background: #f7fafc;
}

.issue-item.critical { border-left-color: #e53e3e; background: #fed7d7; }
.issue-item.high { border-left-color: #d69e2e; background: #fffbeb; }
.issue-item.medium { border-left-color: #4299e1; background: #ebf8ff; }
.issue-item.low { border-left-color: #38a169; background: #f0fff4; }

.issue-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
}

.issue-component {
    font-weight: 600;
}

.issue-severity {
    font-size: 0.8rem;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-weight: 500;
    text-transform: uppercase;
    background: rgba(0,0,0,0.1);
}

.issue-description {
    color: #4a5568;
    margin-bottom: 0.5rem;
}

.issue-fix {
    font-size: 0.9rem;
    color: #2d3748;
    font-style: italic;
}

.test-history {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    max-height: 400px;
    overflow-y: auto;
}

.history-item {
    padding: 1rem;
    border-radius: 8px;
    background: #f7fafc;
    border-left: 4px solid #4299e1;
}

.history-item.success { border-left-color: #38a169; }
.history-item.warning { border-left-color: #d69e2e; }
.history-item.error { border-left-color: #e53e3e; }

.history-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
}

.history-timestamp {
    font-weight: 600;
}

.history-stats {
    font-size: 0.9rem;
    color: #4a5568;
}

.loading {
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 2rem;
    color: #718096;
}

.error-message {
    background: #fed7d7;
    color: #742a2a;
    padding: 1rem;
    border-radius: 8px;
    margin: 1rem 0;
}

@media (max-width: 768px) {
    .dashboard-header {
        flex-direction: column;
        gap: 1rem;
        text-align: center;
    }

    .charts-section {
        grid-template-columns: 1fr;
    }

    .categories-grid, .agent-grid {
        grid-template-columns: 1fr;
    }
}
"""

    def _generate_dashboard_js(self) -> str:
        """Generate JavaScript for the dashboard."""
        return """
class TestDashboard {
    constructor() {
        this.autoRefresh = false;
        this.refreshInterval = null;
        this.charts = {};
        this.lastUpdateTime = null;

        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadData();
    }

    setupEventListeners() {
        document.getElementById('refresh-btn').addEventListener('click', () => {
            this.loadData();
        });

        document.getElementById('auto-refresh-btn').addEventListener('click', () => {
            this.toggleAutoRefresh();
        });
    }

    toggleAutoRefresh() {
        this.autoRefresh = !this.autoRefresh;
        const btn = document.getElementById('auto-refresh-btn');

        if (this.autoRefresh) {
            btn.textContent = 'Auto Refresh: ON';
            btn.classList.add('active');
            this.refreshInterval = setInterval(() => this.loadData(), 30000); // 30 seconds
        } else {
            btn.textContent = 'Auto Refresh: OFF';
            btn.classList.remove('active');
            if (this.refreshInterval) {
                clearInterval(this.refreshInterval);
                this.refreshInterval = null;
            }
        }
    }

    async loadData() {
        try {
            const response = await fetch('/api/data');
            const data = await response.json();

            this.updateDashboard(data);
            this.updateLastUpdated(data.last_updated);

        } catch (error) {
            console.error('Failed to load dashboard data:', error);
            this.showError('Failed to load dashboard data');
        }
    }

    updateDashboard(data) {
        if (!data.current_results) {
            this.showNoData();
            return;
        }

        this.updateSummaryCards(data.current_results.summary);
        this.updateCategories(data.current_results.categories);
        this.updateAgentHealth(data.current_results.agent_health);
        this.updateEnvironmentIssues(data.current_results.environment_issues);
        this.updateCharts(data.performance_trends);
        this.updateTestHistory(data);
    }

    updateSummaryCards(summary) {
        document.getElementById('total-tests').textContent = summary.total_tests;
        document.getElementById('success-rate').textContent = `${summary.success_rate.toFixed(1)}%`;
        document.getElementById('duration').textContent = `${summary.duration.toFixed(1)}s`;

        // Update card colors based on success rate
        const successCard = document.getElementById('success-rate-card');
        successCard.className = 'summary-card ' + this.getStatusClass(summary.success_rate);

        // Update trend (placeholder for now)
        document.getElementById('trend').textContent = summary.is_successful ? '📈' : '📉';
    }

    updateCategories(categories) {
        const grid = document.getElementById('categories-grid');
        grid.innerHTML = '';

        Object.entries(categories).forEach(([categoryName, categoryData]) => {
            const card = document.createElement('div');
            card.className = `category-card ${this.getStatusClass(categoryData.success_rate)}`;

            card.innerHTML = `
                <div class="category-header">
                    <div class="category-name">${this.formatCategoryName(categoryName)}</div>
                    <div class="category-status ${this.getStatusClass(categoryData.success_rate)}">
                        ${categoryData.success_rate.toFixed(1)}%
                    </div>
                </div>
                <div class="category-stats">
                    <span>${categoryData.total_tests} tests</span>
                    <span>${categoryData.duration.toFixed(1)}s</span>
                    <span>${categoryData.passed}✅ ${categoryData.failed}❌</span>
                </div>
            `;

            grid.appendChild(card);
        });
    }

    updateAgentHealth(agentHealth) {
        const grid = document.getElementById('agent-grid');
        grid.innerHTML = '';

        if (!agentHealth || agentHealth.length === 0) {
            grid.innerHTML = '<p>No agent health data available</p>';
            return;
        }

        agentHealth.forEach(agent => {
            const card = document.createElement('div');
            card.className = `agent-card ${agent.status}`;

            card.innerHTML = `
                <div class="agent-header">
                    <div class="agent-name">${agent.name}</div>
                    <div class="agent-status ${agent.status}">${agent.status}</div>
                </div>
                <div class="agent-stats">
                    <span>Response: ${agent.response_time ? agent.response_time.toFixed(1) + 'ms' : 'N/A'}</span>
                    <span>Methods: ${agent.available_methods ? agent.available_methods.length : 0}</span>
                    ${agent.missing_methods && agent.missing_methods.length > 0 ?
                        `<span>Missing: ${agent.missing_methods.length}</span>` : ''}
                </div>
            `;

            grid.appendChild(card);
        });
    }

    updateEnvironmentIssues(issues) {
        const section = document.getElementById('environment-section');
        const list = document.getElementById('issues-list');

        if (!issues || issues.length === 0) {
            section.style.display = 'none';
            return;
        }

        section.style.display = 'block';
        list.innerHTML = '';

        issues.forEach(issue => {
            const item = document.createElement('div');
            item.className = `issue-item ${issue.severity}`;

            item.innerHTML = `
                <div class="issue-header">
                    <div class="issue-component">${issue.component}</div>
                    <div class="issue-severity">${issue.severity}</div>
                </div>
                <div class="issue-description">${issue.description}</div>
                ${issue.suggested_fix ? `<div class="issue-fix">💡 ${issue.suggested_fix}</div>` : ''}
            `;

            list.appendChild(item);
        });
    }

    updateCharts(trends) {
        if (!trends || trends.length === 0) return;

        this.updateSuccessTrendChart(trends);
        this.updateDurationTrendChart(trends);
    }

    updateSuccessTrendChart(trends) {
        const ctx = document.getElementById('success-trend-chart').getContext('2d');

        if (this.charts.successTrend) {
            this.charts.successTrend.destroy();
        }

        const labels = trends.map(t => new Date(t.timestamp).toLocaleTimeString());
        const data = trends.map(t => t.success_rate);

        this.charts.successTrend = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Success Rate (%)',
                    data: data,
                    borderColor: '#38a169',
                    backgroundColor: 'rgba(56, 161, 105, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }

    updateDurationTrendChart(trends) {
        const ctx = document.getElementById('duration-trend-chart').getContext('2d');

        if (this.charts.durationTrend) {
            this.charts.durationTrend.destroy();
        }

        const labels = trends.map(t => new Date(t.timestamp).toLocaleTimeString());
        const data = trends.map(t => t.duration);

        this.charts.durationTrend = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Duration (s)',
                    data: data,
                    borderColor: '#4299e1',
                    backgroundColor: 'rgba(66, 153, 225, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }

    updateTestHistory(data) {
        const history = document.getElementById('test-history');
        history.innerHTML = '';

        if (!data.historical_summary) {
            history.innerHTML = '<p>No historical data available</p>';
            return;
        }

        // Show recent trends
        const item = document.createElement('div');
        item.className = `history-item ${this.getStatusClass(data.historical_summary.average_success_rate)}`;

        item.innerHTML = `
            <div class="history-header">
                <div class="history-timestamp">Recent Average (${data.historical_summary.total_runs} runs)</div>
                <div class="history-stats">Trend: ${data.historical_summary.success_trend}</div>
            </div>
            <div class="history-stats">
                Success Rate: ${data.historical_summary.average_success_rate.toFixed(1)}% |
                Avg Duration: ${data.historical_summary.average_duration.toFixed(1)}s
            </div>
        `;

        history.appendChild(item);
    }

    updateLastUpdated(timestamp) {
        const element = document.getElementById('last-updated');
        if (timestamp) {
            const date = new Date(timestamp);
            element.textContent = `Last updated: ${date.toLocaleTimeString()}`;
        } else {
            element.textContent = 'Never updated';
        }
    }

    getStatusClass(successRate) {
        if (successRate >= 90) return 'success';
        if (successRate >= 70) return 'warning';
        return 'error';
    }

    formatCategoryName(name) {
        return name.replace(/_/g, ' ').replace(/\\b\\w/g, l => l.toUpperCase());
    }

    showError(message) {
        const content = document.querySelector('.dashboard-content');
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = message;
        content.insertBefore(errorDiv, content.firstChild);

        setTimeout(() => errorDiv.remove(), 5000);
    }

    showNoData() {
        const content = document.querySelector('.dashboard-content');
        content.innerHTML = '<div class="loading">No test data available</div>';
    }
}

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', () => {
    new TestDashboard();
});
"""


class TestResultsDashboard:
    """
    Main dashboard class for displaying test results.

    Provides a web-based interface for viewing test results with real-time updates,
    visual indicators, and interactive features.
    """

    def __init__(self, config: TestConfig | None = None):
        """
        Initialize the dashboard.

        Args:
            config: Optional test configuration
        """
        self.config = config
        self.logger = structlog.get_logger(__name__)
        self.dashboard_data = DashboardData()
        self.server: DashboardServer | None = None
        self.report_generator = ReportGenerator(config)

    def add_test_results(self, results: TestResults) -> None:
        """
        Add new test results to the dashboard.

        Args:
            results: Test results to add
        """
        self.dashboard_data.add_results(results)
        self.logger.info(
            "Added test results to dashboard",
            total_tests=results.summary.total_tests,
            success_rate=results.summary.success_rate,
            duration=results.summary.duration,
        )

    def start_server(self, port: int = 8080, open_browser: bool = True) -> str:
        """
        Start the dashboard web server.

        Args:
            port: Port to run the server on
            open_browser: Whether to automatically open the browser

        Returns:
            URL of the dashboard
        """
        self.server = DashboardServer(self.dashboard_data, port)
        url = self.server.start()

        if open_browser:
            try:
                webbrowser.open(url)
                self.logger.info(f"Opened dashboard in browser: {url}")
            except Exception as e:
                self.logger.warning(f"Failed to open browser: {e}")

        return url

    def stop_server(self) -> None:
        """Stop the dashboard web server."""
        if self.server:
            self.server.stop()
            self.server = None

    def generate_static_report(
        self,
        format_type: str = "html",
        output_path: Path | None = None,
        include_diagnostics: bool = True,
    ) -> Path | None:
        """
        Generate a static report from current results.

        Args:
            format_type: Report format (html, json, junit, markdown)
            output_path: Optional output file path
            include_diagnostics: Whether to include detailed diagnostics

        Returns:
            Path to generated report or None if no results
        """
        if not self.dashboard_data.current_results:
            self.logger.warning("No test results available for report generation")
            return None

        return self.report_generator.generate_report(
            results=self.dashboard_data.current_results,
            format_type=format_type,
            output_path=output_path,
            include_diagnostics=include_diagnostics,
        )

    def get_performance_summary(self) -> dict[str, Any]:
        """
        Get performance summary from historical data.

        Returns:
            Performance summary statistics
        """
        return self.dashboard_data._get_historical_summary()

    def export_data(self, output_path: Path) -> None:
        """
        Export all dashboard data to a file.

        Args:
            output_path: Path to export data to
        """
        data = self.dashboard_data.get_dashboard_data()

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

        self.logger.info(f"Exported dashboard data to {output_path}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop_server()
