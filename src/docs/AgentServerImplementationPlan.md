# Backend Agent Server Implementation Plan

## Task 8.5: Implement Backend Agent Servers (Python)

### Overview
Create three independent Python agent servers that provide specialized data via JSON-RPC over HTTP and MCP protocols. These servers will process real topographical data, weather information, and ski infrastructure data for the frontend client.

### Sub-Tasks

#### 8.5.1 Hill Metrics Agent Server
**Purpose**: Process real topographical data and provide elevation grids, slope analysis, and terrain classification for user-defined ski run boundaries.

**Implementation Details**:
- **JSON-RPC Server**: HTTP server using Python `jsonrpc-server` or custom implementation
- **DEM Data Processing**: Integration with elevation data sources:
  - SRTM (Shuttle Radar Topography Mission) data
  - USGS National Elevation Dataset (NED)
  - NASA ASTER Global DEM
  - Local high-resolution LiDAR data for ski areas
- **Terrain Analysis**: 
  - Elevation grid generation for specific geographic boundaries
  - Slope angle calculations using gradient analysis
  - Aspect angle determination (compass direction of slope)
  - Surface type classification (powder, packed, ice, moguls)
- **Geographic Processing**: 
  - Coordinate system transformations (WGS84 to local projections)
  - Boundary clipping for user-defined run areas
  - Grid resampling for different detail levels (32x32 to 128x128)

**Key Methods**:
```python
def get_hill_metrics(area: SkiArea, grid_size: GridSize, boundary: List[Coordinate]) -> HillMetricsResponse:
    """Process topographical data for specific run boundary"""
    
def get_elevation_grid(boundary: List[Coordinate], resolution: int) -> List[List[float]]:
    """Generate elevation grid within boundary at specified resolution"""
    
def calculate_slope_angles(elevation_data: List[List[float]]) -> List[List[float]]:
    """Calculate slope angles from elevation data"""
    
def classify_terrain_surface(elevation_data, slope_data, weather_data) -> List[List[str]]:
    """Classify surface types based on terrain and weather conditions"""
```

#### 8.5.2 Weather Agent Server
**Purpose**: Provide real-time and historical weather data for ski areas, including temperature, wind, precipitation, and snow conditions.

**Implementation Details**:
- **Weather API Integration**:
  - OpenWeatherMap API for current conditions
  - NOAA/National Weather Service for historical data
  - Local weather station data where available
  - Avalanche center data for snow conditions
- **Data Processing**:
  - Weather interpolation for specific coordinates
  - Historical weather pattern analysis
  - Snow condition modeling based on temperature and precipitation
  - Wind effect calculations for terrain features
- **Caching System**:
  - Redis or in-memory caching for frequently requested data
  - Configurable cache expiration (5-15 minutes for current, longer for historical)

**Key Methods**:
```python
def get_weather_data(area: SkiArea, timestamp: Optional[datetime] = None) -> WeatherResponse:
    """Get current or historical weather for ski area"""
    
def get_weather_forecast(area: SkiArea, hours: int = 24) -> List[WeatherData]:
    """Get weather forecast for specified time period"""
    
def get_snow_conditions(area: SkiArea, elevation: float) -> SnowCondition:
    """Determine snow conditions based on weather and elevation"""
```

#### 8.5.3 Equipment Agent Server
**Purpose**: Manage information about ski lifts, trails, facilities, and safety equipment within ski areas.

**Implementation Details**:
- **Infrastructure Database**:
  - Ski lift locations, types, and operational status
  - Trail maps and difficulty ratings
  - Facility locations (lodges, restaurants, first aid)
  - Safety equipment (patrol stations, emergency phones)
- **Data Sources**:
  - Ski resort APIs where available
  - OpenStreetMap data for ski infrastructure
  - Manual data entry for detailed facility information
  - Real-time operational status feeds
- **Spatial Queries**:
  - Equipment within user-defined run boundaries
  - Nearest facilities to specific coordinates
  - Safety equipment accessibility analysis

**Key Methods**:
```python
def get_equipment_data(area: SkiArea, boundary: Optional[List[Coordinate]] = None) -> EquipmentResponse:
    """Get ski infrastructure data for area or specific boundary"""
    
def get_nearby_facilities(coordinate: Coordinate, radius: float) -> List[Facility]:
    """Find facilities within specified radius of coordinate"""
    
def get_lift_status(area: SkiArea) -> List[LiftStatus]:
    """Get real-time operational status of ski lifts"""
```

### Technical Implementation

#### 8.5.4 Server Infrastructure
**Framework**: FastAPI or Flask for HTTP server with JSON-RPC support
**Dependencies**:
```python
# Core server
fastapi>=0.104.0
uvicorn>=0.24.0
jsonrpc-server>=1.2.0

# Geospatial processing
rasterio>=1.3.0          # Raster data processing
geopandas>=0.14.0        # Geographic data manipulation
pyproj>=3.6.0            # Coordinate transformations
shapely>=2.0.0           # Geometric operations

# Data sources
requests>=2.31.0         # HTTP requests for APIs
numpy>=1.24.0            # Numerical computations
scipy>=1.11.0            # Scientific computing

# Caching and storage
redis>=5.0.0             # Caching layer
sqlalchemy>=2.0.0        # Database ORM (for equipment data)

# Monitoring and logging
structlog>=23.2.0        # Structured logging
prometheus-client>=0.19.0 # Metrics collection
```

#### 8.5.5 Configuration and Deployment
**Environment Configuration**:
```python
# config.py
class AgentConfig:
    # Server settings
    HOST: str = "localhost"
    PORT: int = 8001  # Hill Metrics: 8001, Weather: 8002, Equipment: 8003
    
    # Data source APIs
    OPENWEATHER_API_KEY: str
    USGS_API_ENDPOINT: str
    SRTM_DATA_PATH: str
    
    # Caching
    REDIS_URL: str = "redis://localhost:6379"
    CACHE_TTL: int = 300  # 5 minutes
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
```

**Docker Configuration**:
```dockerfile
# Dockerfile.hill-metrics
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY agents/hill_metrics/ ./
EXPOSE 8001

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
```

#### 8.5.6 Health Checks and Monitoring
**Health Check Endpoints**:
```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "version": "1.0.0",
        "uptime": get_uptime(),
        "dependencies": check_dependencies()
    }

@app.get("/metrics")
async def metrics():
    return {
        "requests_total": request_counter.get(),
        "response_time_avg": response_time.get_average(),
        "error_rate": error_rate.get(),
        "cache_hit_rate": cache_hit_rate.get()
    }
```

#### 8.5.7 MCP Protocol Support
**MCP Integration**:
```python
# mcp_server.py
class MCPAgentServer:
    def __init__(self, jsonrpc_server):
        self.jsonrpc_server = jsonrpc_server
    
    async def handle_mcp_request(self, request: MCPRequest) -> MCPResponse:
        """Handle MCP protocol requests and translate to JSON-RPC"""
        
    async def get_capabilities(self) -> AgentCapabilities:
        """Return agent capabilities for MCP discovery"""
```

### Testing Strategy

#### 8.5.8 Agent Server Testing
**Unit Tests**:
- Data processing functions (elevation grid generation, slope calculations)
- API integration modules (weather API, DEM data loading)
- Coordinate transformations and geometric operations
- Caching mechanisms and data validation

**Integration Tests**:
- End-to-end JSON-RPC request/response cycles
- Real API integration with external data sources
- Database operations for equipment data
- MCP protocol compatibility

**Performance Tests**:
- Large elevation grid processing (128x128 grids)
- Concurrent request handling
- Memory usage with large datasets
- Response time benchmarks

### Deployment and Operations

#### 8.5.9 Production Deployment
**Server Startup Scripts**:
```bash
#!/bin/bash
# start_agents.sh

# Start Hill Metrics Agent
uv run python -m agents.hill_metrics &
HILL_PID=$!

# Start Weather Agent  
uv run python -m agents.weather &
WEATHER_PID=$!

# Start Equipment Agent
uv run python -m agents.equipment &
EQUIPMENT_PID=$!

echo "Started agents: Hill($HILL_PID) Weather($WEATHER_PID) Equipment($EQUIPMENT_PID)"
```

**Monitoring and Logging**:
- Structured JSON logging with correlation IDs
- Prometheus metrics for request rates, response times, error rates
- Health check monitoring with alerting
- Log aggregation for debugging and analysis

### Success Criteria
- [ ] All three agent servers start successfully and respond to health checks
- [ ] Hill Metrics Agent can process real DEM data and return elevation grids
- [ ] Weather Agent integrates with external APIs and provides current/historical data
- [ ] Equipment Agent serves ski infrastructure data for all five ski areas
- [ ] JSON-RPC protocol works correctly with the frontend AgentClient
- [ ] MCP protocol support enables external tool integration
- [ ] Performance meets requirements (sub-second response for typical requests)
- [ ] Comprehensive test coverage (>80%) for all agent functionality
- [ ] Production deployment scripts and monitoring are functional

### Dependencies
- **Requires**: Task 8 (Agent communication system) - completed
- **Enables**: Task 9 (Terrain data processing) - needs Hill Metrics Agent
- **Enables**: Task 11 (Weather effects) - needs Weather Agent  
- **Enables**: Task 15 (Equipment visualization) - needs Equipment Agent

This implementation will provide the missing backend infrastructure needed for the frontend terrain processing and visualization systems.