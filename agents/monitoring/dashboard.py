"""Monitoring dashboard server for agent health and performance."""

import asyncio
import json
from datetime import datetime
from typing import Any
from typing import Dict
from typing import List

import httpx
import structlog
import uvicorn
from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.responses import JSONResponse

from agents.shared.logging_config import setup_logging

# Set up logging
setup_logging()
logger = structlog.get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Agent Monitoring Dashboard",
    description="Monitoring dashboard for Alpine Ski Simulator agent servers",
    version="1.0.0",
)

# Agent server configurations
AGENT_SERVERS = {
    "hill_metrics": {
        "name": "Hill Metrics Agent",
        "url": "http://localhost:8001",
        "description": "Topographical data processing and terrain analysis",
    },
    "weather": {
        "name": "Weather Agent",
        "url": "http://localhost:8002",
        "description": "Real-time and historical weather data",
    },
    "equipment": {
        "name": "Equipment Agent",
        "url": "http://localhost:8003",
        "description": "Ski infrastructure and facility information",
    },
}


@app.get("/", response_class=HTMLResponse)
async def dashboard_home():
    """Main dashboard page."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Agent Monitoring Dashboard</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
            }
            .header {
                background: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                margin-bottom: 20px;
            }
            .agent-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
                gap: 20px;
                margin-bottom: 20px;
            }
            .agent-card {
                background: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .status-indicator {
                display: inline-block;
                width: 12px;
                height: 12px;
                border-radius: 50%;
                margin-right: 8px;
            }
            .status-healthy { background-color: #28a745; }
            .status-unhealthy { background-color: #dc3545; }
            .status-unknown { background-color: #6c757d; }
            .metrics {
                margin-top: 15px;
            }
            .metric {
                display: flex;
                justify-content: space-between;
                margin: 5px 0;
                padding: 5px 0;
                border-bottom: 1px solid #eee;
            }
            .refresh-btn {
                background: #007bff;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                cursor: pointer;
                margin-left: 10px;
            }
            .refresh-btn:hover {
                background: #0056b3;
            }
            .timestamp {
                color: #6c757d;
                font-size: 0.9em;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Alpine Ski Simulator - Agent Monitoring Dashboard</h1>
                <p>Real-time monitoring of agent server health and performance</p>
                <button class="refresh-btn" onclick="refreshData()">Refresh Data</button>
                <span class="timestamp" id="lastUpdate"></span>
            </div>
            
            <div class="agent-grid" id="agentGrid">
                <!-- Agent cards will be populated by JavaScript -->
            </div>
        </div>

        <script>
            async function fetchAgentStatus() {
                try {
                    const response = await fetch('/api/status');
                    const data = await response.json();
                    return data;
                } catch (error) {
                    console.error('Failed to fetch agent status:', error);
                    return null;
                }
            }

            function createAgentCard(agentId, agentData) {
                const statusClass = agentData.status === 'healthy' ? 'status-healthy' : 
                                  agentData.status === 'unhealthy' ? 'status-unhealthy' : 'status-unknown';
                
                const metricsHtml = agentData.metrics ? Object.entries(agentData.metrics)
                    .map(([key, value]) => `
                        <div class="metric">
                            <span>${key.replace(/_/g, ' ').replace(/\\b\\w/g, l => l.toUpperCase())}</span>
                            <span>${typeof value === 'number' ? value.toFixed(2) : value}</span>
                        </div>
                    `).join('') : '';

                return `
                    <div class="agent-card">
                        <h3>
                            <span class="status-indicator ${statusClass}"></span>
                            ${agentData.name}
                        </h3>
                        <p>${agentData.description}</p>
                        <div class="metrics">
                            <div class="metric">
                                <span>Status</span>
                                <span>${agentData.status}</span>
                            </div>
                            <div class="metric">
                                <span>URL</span>
                                <span>${agentData.url}</span>
                            </div>
                            <div class="metric">
                                <span>Response Time</span>
                                <span>${agentData.response_time_ms ? agentData.response_time_ms.toFixed(0) + 'ms' : 'N/A'}</span>
                            </div>
                            ${metricsHtml}
                        </div>
                    </div>
                `;
            }

            async function updateDashboard() {
                const statusData = await fetchAgentStatus();
                if (!statusData) return;

                const agentGrid = document.getElementById('agentGrid');
                agentGrid.innerHTML = Object.entries(statusData.agents)
                    .map(([agentId, agentData]) => createAgentCard(agentId, agentData))
                    .join('');

                document.getElementById('lastUpdate').textContent = 
                    `Last updated: ${new Date(statusData.timestamp).toLocaleString()}`;
            }

            function refreshData() {
                updateDashboard();
            }

            // Initial load and auto-refresh every 30 seconds
            updateDashboard();
            setInterval(updateDashboard, 30000);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/api/status")
async def get_agent_status():
    """Get status of all agent servers."""
    status_data = {
        "timestamp": datetime.now().isoformat(),
        "agents": {},
    }
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        for agent_id, config in AGENT_SERVERS.items():
            agent_status = {
                "name": config["name"],
                "url": config["url"],
                "description": config["description"],
                "status": "unknown",
                "response_time_ms": None,
                "metrics": {},
            }
            
            try:
                # Check basic health
                start_time = asyncio.get_event_loop().time()
                health_response = await client.get(f"{config['url']}/health")
                response_time = (asyncio.get_event_loop().time() - start_time) * 1000
                
                agent_status["response_time_ms"] = response_time
                
                if health_response.status_code == 200:
                    agent_status["status"] = "healthy"
                    
                    # Try to get detailed health info
                    try:
                        detailed_response = await client.get(f"{config['url']}/health/detailed")
                        if detailed_response.status_code == 200:
                            detailed_data = detailed_response.json()
                            agent_status["detailed_health"] = detailed_data
                    except Exception:
                        pass
                    
                    # Try to get metrics
                    try:
                        metrics_response = await client.get(f"{config['url']}/metrics")
                        if metrics_response.status_code == 200:
                            metrics_data = metrics_response.json()
                            agent_status["metrics"] = metrics_data
                    except Exception:
                        pass
                        
                else:
                    agent_status["status"] = "unhealthy"
                    
            except Exception as e:
                agent_status["status"] = "unhealthy"
                agent_status["error"] = str(e)
                logger.warning(
                    "Failed to check agent status",
                    agent_id=agent_id,
                    url=config["url"],
                    error=str(e),
                )
            
            status_data["agents"][agent_id] = agent_status
    
    return JSONResponse(content=status_data)


@app.get("/api/agents/{agent_id}/health")
async def get_agent_health(agent_id: str):
    """Get detailed health information for a specific agent."""
    if agent_id not in AGENT_SERVERS:
        return JSONResponse(
            content={"error": f"Agent '{agent_id}' not found"},
            status_code=404,
        )
    
    config = AGENT_SERVERS[agent_id]
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{config['url']}/health/detailed")
            
            if response.status_code == 200:
                return JSONResponse(content=response.json())
            else:
                return JSONResponse(
                    content={"error": f"Agent returned status {response.status_code}"},
                    status_code=response.status_code,
                )
                
    except Exception as e:
        logger.error(
            "Failed to get agent health",
            agent_id=agent_id,
            url=config["url"],
            error=str(e),
            exc_info=True,
        )
        return JSONResponse(
            content={"error": str(e)},
            status_code=500,
        )


@app.get("/api/agents/{agent_id}/metrics")
async def get_agent_metrics(agent_id: str):
    """Get metrics for a specific agent."""
    if agent_id not in AGENT_SERVERS:
        return JSONResponse(
            content={"error": f"Agent '{agent_id}' not found"},
            status_code=404,
        )
    
    config = AGENT_SERVERS[agent_id]
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{config['url']}/metrics")
            
            if response.status_code == 200:
                return JSONResponse(content=response.json())
            else:
                return JSONResponse(
                    content={"error": f"Agent returned status {response.status_code}"},
                    status_code=response.status_code,
                )
                
    except Exception as e:
        logger.error(
            "Failed to get agent metrics",
            agent_id=agent_id,
            url=config["url"],
            error=str(e),
            exc_info=True,
        )
        return JSONResponse(
            content={"error": str(e)},
            status_code=500,
        )


@app.post("/api/agents/{agent_id}/test")
async def test_agent(agent_id: str, request: Request):
    """Test an agent with a sample request."""
    if agent_id not in AGENT_SERVERS:
        return JSONResponse(
            content={"error": f"Agent '{agent_id}' not found"},
            status_code=404,
        )
    
    config = AGENT_SERVERS[agent_id]
    
    # Sample test requests for each agent
    test_requests = {
        "hill_metrics": {
            "jsonrpc": "2.0",
            "method": "get_hill_metrics",
            "params": {
                "bounds": {"north": 46.0, "south": 45.9, "east": 7.1, "west": 7.0},
                "grid_size": "32x32",
                "include_surface_classification": False,
            },
            "id": "test_request",
        },
        "weather": {
            "jsonrpc": "2.0",
            "method": "get_weather",
            "params": {
                "latitude": 46.0,
                "longitude": 7.0,
            },
            "id": "test_request",
        },
        "equipment": {
            "jsonrpc": "2.0",
            "method": "get_equipment_data",
            "params": {
                "north": 46.0,
                "south": 45.9,
                "east": 7.1,
                "west": 7.0,
                "include_lifts": True,
                "include_trails": False,
                "include_facilities": False,
                "include_safety_equipment": False,
            },
            "id": "test_request",
        },
    }
    
    if agent_id not in test_requests:
        return JSONResponse(
            content={"error": f"No test request defined for agent '{agent_id}'"},
            status_code=400,
        )
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            start_time = asyncio.get_event_loop().time()
            
            response = await client.post(
                f"{config['url']}/jsonrpc",
                json=test_requests[agent_id],
                headers={"Content-Type": "application/json"},
            )
            
            response_time = (asyncio.get_event_loop().time() - start_time) * 1000
            
            result = {
                "agent_id": agent_id,
                "status_code": response.status_code,
                "response_time_ms": response_time,
                "timestamp": datetime.now().isoformat(),
            }
            
            if response.status_code == 200:
                result["response"] = response.json()
                result["success"] = True
            else:
                result["error"] = f"HTTP {response.status_code}"
                result["success"] = False
            
            return JSONResponse(content=result)
            
    except Exception as e:
        logger.error(
            "Failed to test agent",
            agent_id=agent_id,
            url=config["url"],
            error=str(e),
            exc_info=True,
        )
        return JSONResponse(
            content={
                "agent_id": agent_id,
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            },
            status_code=500,
        )


if __name__ == "__main__":
    logger.info("Starting Agent Monitoring Dashboard")
    uvicorn.run(
        "agents.monitoring.dashboard:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_config=None,  # Use our custom logging
    )