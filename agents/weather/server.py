"""Weather Agent server implementation."""

import time
from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

import structlog
import uvicorn

from agents.shared.jsonrpc import create_jsonrpc_app
from agents.shared.logging_config import setup_logging
from agents.shared.mcp import add_mcp_support
from agents.shared.monitoring import HealthChecker
from agents.shared.monitoring import PerformanceMonitor
from agents.weather.models import SkiConditionsRequest
from agents.weather.models import SkiConditionsResponse
from agents.weather.models import WeatherRequest
from agents.weather.models import WeatherResponse
from agents.weather.weather_service import WeatherService

# Set up logging
setup_logging()
logger = structlog.get_logger(__name__)

# Create FastAPI app with JSON-RPC support
app, jsonrpc_handler = create_jsonrpc_app(
    title="Weather Agent",
    description="Real-time and historical weather data agent for ski areas",
)

# Add MCP support
mcp_handler = add_mcp_support(app, "weather")

# Initialize components
weather_service = WeatherService()
performance_monitor = PerformanceMonitor("weather")
health_checker = HealthChecker("weather")


# JSON-RPC Methods
async def get_weather(
    latitude: float,
    longitude: float,
    timestamp: Optional[str] = None,
    include_forecast: bool = False,
    forecast_days: int = 7,
    include_historical: bool = False,
    historical_days: int = 30,
) -> Dict[str, Any]:
    """
    Get weather data for the specified coordinates.
    
    Args:
        latitude: Latitude
        longitude: Longitude
        timestamp: Specific timestamp (ISO format, for historical data)
        include_forecast: Include forecast data
        forecast_days: Number of forecast days
        include_historical: Include historical data
        historical_days: Number of historical days
        
    Returns:
        Weather data
    """
    start_time = time.time()
    
    try:
        # Parse timestamp if provided
        parsed_timestamp = None
        if timestamp:
            parsed_timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        # Create request
        weather_request = WeatherRequest(
            latitude=latitude,
            longitude=longitude,
            timestamp=parsed_timestamp,
            include_forecast=include_forecast,
            forecast_days=forecast_days,
            include_historical=include_historical,
            historical_days=historical_days,
        )
        
        # Get current weather
        current_weather = await weather_service.get_current_weather(
            latitude, longitude
        )
        
        # Get forecast if requested
        forecast = []
        if include_forecast:
            forecast = await weather_service.get_weather_forecast(
                latitude, longitude, forecast_days
            )
        
        # Get historical data if requested
        historical = []
        if include_historical:
            historical = await weather_service.get_historical_weather(
                latitude, longitude, historical_days
            )
        
        # Create response
        processing_time_ms = (time.time() - start_time) * 1000
        
        response = WeatherResponse(
            current=current_weather,
            forecast=forecast,
            historical=historical,
            location={
                "latitude": latitude,
                "longitude": longitude,
                "name": f"Location {latitude:.2f}, {longitude:.2f}",
            },
            data_source="Synthetic Weather Service",
            cache_expires_at=datetime.now().replace(microsecond=0),
            processing_time_ms=processing_time_ms,
        )
        
        # Record performance metrics
        performance_monitor.record_request(
            "get_weather",
            (time.time() - start_time),
            True,
        )
        
        logger.info(
            "Weather request completed",
            latitude=latitude,
            longitude=longitude,
            include_forecast=include_forecast,
            include_historical=include_historical,
            processing_time_ms=processing_time_ms,
        )
        
        return response.model_dump()
        
    except Exception as e:
        # Record error
        performance_monitor.record_request(
            "get_weather",
            (time.time() - start_time),
            False,
        )
        
        logger.error(
            "Weather request failed",
            latitude=latitude,
            longitude=longitude,
            error=str(e),
            exc_info=True,
        )
        raise


async def get_ski_conditions(
    latitude: float,
    longitude: float,
    elevation_m: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Get ski-specific weather conditions analysis.
    
    Args:
        latitude: Latitude
        longitude: Longitude
        elevation_m: Elevation in meters
        
    Returns:
        Ski conditions analysis
    """
    start_time = time.time()
    
    try:
        # Create request
        ski_request = SkiConditionsRequest(
            latitude=latitude,
            longitude=longitude,
            elevation_m=elevation_m,
        )
        
        # Get ski conditions
        conditions = await weather_service.get_ski_conditions(
            latitude, longitude, elevation_m
        )
        
        # Get current weather for context
        weather = await weather_service.get_current_weather(latitude, longitude)
        
        # Create response
        processing_time_ms = (time.time() - start_time) * 1000
        
        response = SkiConditionsResponse(
            conditions=conditions,
            weather=weather,
            location={
                "latitude": latitude,
                "longitude": longitude,
                "elevation_m": elevation_m,
                "name": f"Ski Area {latitude:.2f}, {longitude:.2f}",
            },
            timestamp=datetime.now(),
            processing_time_ms=processing_time_ms,
        )
        
        # Record performance metrics
        performance_monitor.record_request(
            "get_ski_conditions",
            (time.time() - start_time),
            True,
        )
        
        logger.info(
            "Ski conditions request completed",
            latitude=latitude,
            longitude=longitude,
            elevation_m=elevation_m,
            overall_rating=conditions.overall_rating,
            processing_time_ms=processing_time_ms,
        )
        
        return response.model_dump()
        
    except Exception as e:
        # Record error
        performance_monitor.record_request(
            "get_ski_conditions",
            (time.time() - start_time),
            False,
        )
        
        logger.error(
            "Ski conditions request failed",
            latitude=latitude,
            longitude=longitude,
            elevation_m=elevation_m,
            error=str(e),
            exc_info=True,
        )
        raise


async def get_weather_alerts(
    latitude: float,
    longitude: float,
) -> Dict[str, Any]:
    """
    Get weather alerts for the specified coordinates.
    
    Args:
        latitude: Latitude
        longitude: Longitude
        
    Returns:
        Weather alerts
    """
    start_time = time.time()
    
    try:
        # Get current weather to check for alert conditions
        weather = await weather_service.get_current_weather(latitude, longitude)
        
        alerts = []
        
        # Check for various alert conditions
        if weather.wind.speed_kmh > 50:
            alerts.append({
                "type": "wind",
                "severity": "high",
                "title": "High Wind Warning",
                "description": f"Wind speeds of {weather.wind.speed_kmh:.1f} km/h. Avoid exposed areas.",
                "expires_at": (datetime.now().timestamp() + 3600),  # 1 hour
            })
        
        if weather.temperature_c < -25:
            alerts.append({
                "type": "temperature",
                "severity": "extreme",
                "title": "Extreme Cold Warning",
                "description": f"Temperature of {weather.temperature_c:.1f}°C. Risk of frostbite.",
                "expires_at": (datetime.now().timestamp() + 7200),  # 2 hours
            })
        
        if weather.visibility.distance_km < 1:
            alerts.append({
                "type": "visibility",
                "severity": "high",
                "title": "Low Visibility Warning",
                "description": f"Visibility reduced to {weather.visibility.distance_km:.1f} km.",
                "expires_at": (datetime.now().timestamp() + 1800),  # 30 minutes
            })
        
        # Record performance metrics
        performance_monitor.record_request(
            "get_weather_alerts",
            (time.time() - start_time),
            True,
        )
        
        processing_time_ms = (time.time() - start_time) * 1000
        
        logger.info(
            "Weather alerts request completed",
            latitude=latitude,
            longitude=longitude,
            alert_count=len(alerts),
            processing_time_ms=processing_time_ms,
        )
        
        return {
            "alerts": alerts,
            "location": {
                "latitude": latitude,
                "longitude": longitude,
            },
            "timestamp": datetime.now().isoformat(),
            "processing_time_ms": processing_time_ms,
        }
        
    except Exception as e:
        # Record error
        performance_monitor.record_request(
            "get_weather_alerts",
            (time.time() - start_time),
            False,
        )
        
        logger.error(
            "Weather alerts request failed",
            latitude=latitude,
            longitude=longitude,
            error=str(e),
            exc_info=True,
        )
        raise


# Register JSON-RPC methods
jsonrpc_handler.register_method("get_weather", get_weather)
jsonrpc_handler.register_method("get_ski_conditions", get_ski_conditions)
jsonrpc_handler.register_method("get_weather_alerts", get_weather_alerts)

# Register MCP tools
mcp_handler.register_tool(
    "get_weather",
    "Get current weather, forecast, and historical data for a location",
    {
        "type": "object",
        "properties": {
            "latitude": {"type": "number", "minimum": -90, "maximum": 90},
            "longitude": {"type": "number", "minimum": -180, "maximum": 180},
            "include_forecast": {"type": "boolean", "default": False},
            "forecast_days": {"type": "integer", "minimum": 1, "maximum": 14, "default": 7},
            "include_historical": {"type": "boolean", "default": False},
            "historical_days": {"type": "integer", "minimum": 1, "maximum": 365, "default": 30},
        },
        "required": ["latitude", "longitude"],
    },
    get_weather,
)

mcp_handler.register_tool(
    "get_ski_conditions",
    "Get ski-specific weather conditions and recommendations",
    {
        "type": "object",
        "properties": {
            "latitude": {"type": "number", "minimum": -90, "maximum": 90},
            "longitude": {"type": "number", "minimum": -180, "maximum": 180},
            "elevation_m": {"type": "number", "minimum": 0},
        },
        "required": ["latitude", "longitude"],
    },
    get_ski_conditions,
)

mcp_handler.register_tool(
    "get_weather_alerts",
    "Get weather alerts and warnings for a location",
    {
        "type": "object",
        "properties": {
            "latitude": {"type": "number", "minimum": -90, "maximum": 90},
            "longitude": {"type": "number", "minimum": -180, "maximum": 180},
        },
        "required": ["latitude", "longitude"],
    },
    get_weather_alerts,
)


# Health checks
async def check_weather_service() -> bool:
    """Check if weather service is working."""
    try:
        # Test with a simple request
        await weather_service.get_current_weather(46.0, 7.0)
        return True
    except Exception:
        return False


health_checker.add_check("weather_service", check_weather_service)


@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info("Starting Weather Agent")
    performance_monitor.start_monitoring()


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("Shutting down Weather Agent")
    performance_monitor.stop_monitoring()


# Add health check endpoint
@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check endpoint."""
    return await health_checker.run_checks()


if __name__ == "__main__":
    uvicorn.run(
        "agents.weather.server:app",
        host="0.0.0.0",
        port=8002,
        reload=False,
        log_config=None,  # Use our custom logging
    )