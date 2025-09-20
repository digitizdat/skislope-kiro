
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
        return name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
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
