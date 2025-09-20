# Alpine Ski Simulator - Agent Servers

This directory contains the backend agent servers for the Alpine Ski Simulator project. The agents provide specialized data services for topographical analysis, weather information, and ski equipment data.

## Architecture

The system consists of three independent agent servers:

- **Hill Metrics Agent** (Port 8001): Topographical data processing and terrain analysis
- **Weather Agent** (Port 8002): Real-time and historical weather data
- **Equipment Agent** (Port 8003): Ski infrastructure and facility information
- **Monitoring Dashboard** (Port 8000): Health monitoring and performance metrics

## Features

- **JSON-RPC over HTTP**: Primary communication protocol
- **MCP Protocol Support**: Integration with external tools and AI assistants
- **Comprehensive Logging**: Structured logging with performance metrics
- **Health Monitoring**: Real-time health checks and performance monitoring
- **Caching**: Intelligent caching for improved performance
- **Error Handling**: Robust error handling with graceful degradation

## Quick Start

### Prerequisites

- Python 3.12
- uv (Python package manager)

### Installation

1. Install uv (if not already installed):
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or using pip
pip install uv
```

2. Install dependencies:
```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -r pyproject.toml
```

### Running the Agents

#### Option 1: Start All Agents (Recommended)
```bash
python scripts/start_agents.py
```

This will start all agents and the monitoring dashboard. The script will:
- Start all three agent servers
- Start the monitoring dashboard
- Wait for all agents to become healthy
- Display status information
- Handle graceful shutdown on Ctrl+C

#### Option 2: Start Individual Agents
```bash
# Hill Metrics Agent
uv run python -m agents.hill_metrics.server

# Weather Agent
uv run python -m agents.weather.server

# Equipment Agent
uv run python -m agents.equipment.server

# Monitoring Dashboard
uv run python -m agents.monitoring.dashboard
```

### Testing the Agents

Run the comprehensive test suite:
```bash
python scripts/test_agents.py
```

This will test all agents with sample requests and display results.

### Health Checks

Check agent health manually:
```bash
python -m agents.monitoring.health_checker
```

Or visit the monitoring dashboard at: http://localhost:8000

## API Documentation

### Hill Metrics Agent (Port 8001)

**Endpoints:**
- `GET /health` - Basic health check
- `GET /health/detailed` - Detailed health information
- `GET /metrics` - Performance metrics
- `POST /jsonrpc` - JSON-RPC requests
- `GET /mcp/tools` - List MCP tools
- `POST /mcp/call` - Call MCP tools

**JSON-RPC Methods:**
- `get_hill_metrics(bounds, grid_size, include_surface_classification)` - Get topographical data
- `get_elevation_profile(start_lat, start_lng, end_lat, end_lng, num_points)` - Get elevation profile

**Example Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "get_hill_metrics",
  "params": {
    "bounds": {"north": 46.0, "south": 45.9, "east": 7.1, "west": 7.0},
    "grid_size": "64x64",
    "include_surface_classification": true
  },
  "id": "1"
}
```

### Weather Agent (Port 8002)

**JSON-RPC Methods:**
- `get_weather(latitude, longitude, include_forecast, include_historical)` - Get weather data
- `get_ski_conditions(latitude, longitude, elevation_m)` - Get ski-specific conditions
- `get_weather_alerts(latitude, longitude)` - Get weather alerts

**Example Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "get_weather",
  "params": {
    "latitude": 46.0,
    "longitude": 7.0,
    "include_forecast": true,
    "forecast_days": 7
  },
  "id": "1"
}
```

### Equipment Agent (Port 8003)

**JSON-RPC Methods:**
- `get_equipment_data(north, south, east, west, filters...)` - Get comprehensive equipment data
- `get_lift_status(lift_ids, bounds)` - Get lift status information
- `get_trail_conditions(trail_ids, bounds, difficulty_filter)` - Get trail conditions
- `get_facilities(bounds, facility_types, open_only)` - Get facility information

**Example Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "get_equipment_data",
  "params": {
    "north": 46.0,
    "south": 45.9,
    "east": 7.1,
    "west": 7.0,
    "include_lifts": true,
    "include_trails": true,
    "operational_only": false
  },
  "id": "1"
}
```

## Development

### Code Quality

```bash
# Linting and formatting
ruff check
ruff check --fix
ruff format

# Static analysis
semgrep --config=auto

# Type checking
mypy agents/
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=agents

# Run specific test file
uv run pytest agents/tests/test_hill_metrics.py

# Run integration tests
uv run pytest -m integration
```

### Logging

Logs are written to:
- `logs/agents.log` - General application logs
- `logs/performance.log` - Performance metrics
- Console output for development

Log configuration is in `logging.yaml`.

### Monitoring

The monitoring dashboard provides:
- Real-time agent health status
- Performance metrics
- Request/response times
- Error rates
- System resource usage

Access at: http://localhost:8000

## Configuration

### Environment Variables

- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARN, ERROR)
- `CACHE_TTL` - Default cache TTL in seconds
- `REQUEST_TIMEOUT` - HTTP request timeout in seconds

### Ski Areas

The system includes data for five predefined ski areas:
- Chamonix, France
- Whistler, Canada
- Saint Anton am Arlberg, Austria
- Zermatt, Switzerland
- Copper Mountain, United States

## Deployment

### Production Deployment

1. Install dependencies:
```bash
uv pip install -r pyproject.toml
```

2. Configure logging and monitoring
3. Start agents with process manager (systemd, supervisor, etc.)
4. Set up reverse proxy (nginx, traefik, etc.)
5. Configure monitoring and alerting

### Docker Deployment

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY . .

RUN pip install uv
RUN uv pip install -r pyproject.toml

EXPOSE 8001 8002 8003 8000

CMD ["python", "scripts/start_agents.py"]
```

## Troubleshooting

### Common Issues

1. **Port already in use**: Check if agents are already running
2. **Import errors**: Ensure Python path includes project root
3. **Permission errors**: Check file permissions for logs directory
4. **Network timeouts**: Adjust timeout settings in configuration

### Debug Mode

Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
python scripts/start_agents.py
```

### Health Check Failures

Check individual agent health:
```bash
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
```

## Contributing

1. Follow the existing code style (ruff formatting)
2. Add tests for new functionality
3. Update documentation
4. Ensure all health checks pass
5. Test with the monitoring dashboard

## License

This project is part of the Alpine Ski Simulator and follows the same license terms.