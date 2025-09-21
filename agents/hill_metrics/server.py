"""Hill Metrics Agent server implementation."""

import time
from contextlib import asynccontextmanager
from typing import Any

import structlog
import uvicorn
from fastapi import FastAPI

from agents.hill_metrics.models import GeographicBounds
from agents.hill_metrics.models import GridSize
from agents.hill_metrics.models import TerrainRequest
from agents.hill_metrics.models import TerrainResponse
from agents.hill_metrics.terrain_processor import DEMProcessor
from agents.shared.jsonrpc import create_jsonrpc_app
from agents.shared.logging_config import setup_logging
from agents.shared.mcp import add_mcp_support
from agents.shared.monitoring import HealthChecker
from agents.shared.monitoring import PerformanceMonitor

# Set up logging
setup_logging()
logger = structlog.get_logger(__name__)

# Initialize components
dem_processor = DEMProcessor()
performance_monitor = PerformanceMonitor("hill_metrics")
health_checker = HealthChecker("hill_metrics")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    # Startup
    logger.info("Starting Hill Metrics Agent")
    performance_monitor.start_monitoring()

    yield

    # Shutdown
    logger.info("Shutting down Hill Metrics Agent")
    performance_monitor.stop_monitoring()


# Create FastAPI app with JSON-RPC support
app, jsonrpc_handler = create_jsonrpc_app(
    title="Hill Metrics Agent",
    description="Topographical data processing and terrain analysis agent",
    lifespan=lifespan,
)

# Add MCP support
mcp_handler = add_mcp_support(app, "hill_metrics")


# JSON-RPC Methods
async def get_hill_metrics(
    bounds: dict[str, float],
    grid_size: str = "64x64",
    include_surface_classification: bool = True,
    include_safety_zones: bool = False,
    include_course_markers: bool = False,
) -> dict[str, Any]:
    """
    Get hill metrics for the specified geographic bounds.

    Args:
        bounds: Geographic bounds (north, south, east, west)
        grid_size: Grid resolution (32x32, 64x64, 96x96, 128x128)
        include_surface_classification: Include surface type analysis
        include_safety_zones: Include FIS safety zones
        include_course_markers: Include FIS course markers

    Returns:
        Hill metrics data
    """
    start_time = time.time()

    try:
        # Validate and create request
        logger.info(
            f"Creating TerrainRequest with bounds={bounds}, grid_size={grid_size}"
        )
        try:
            geographic_bounds = GeographicBounds(**bounds)
            logger.info(f"GeographicBounds created successfully: {geographic_bounds}")
        except Exception as e:
            logger.error(f"Failed to create GeographicBounds: {e}")
            raise

        try:
            grid_size_enum = GridSize(grid_size)
            logger.info(f"GridSize enum created successfully: {grid_size_enum}")
        except Exception as e:
            logger.error(f"Failed to create GridSize enum: {e}")
            raise

        terrain_request = TerrainRequest(
            bounds=geographic_bounds,
            grid_size=grid_size_enum,
            include_surface_classification=include_surface_classification,
            include_safety_zones=include_safety_zones,
            include_course_markers=include_course_markers,
        )
        logger.info("TerrainRequest created successfully")

        # Process terrain data
        hill_metrics = await dem_processor.process_terrain(
            terrain_request.bounds,
            terrain_request.grid_size,
            terrain_request.include_surface_classification,
        )

        # Create response
        processing_time_ms = (time.time() - start_time) * 1000

        response = TerrainResponse(
            hill_metrics=hill_metrics,
            processing_time_ms=processing_time_ms,
            data_sources=["SRTM", "USGS"],
            cache_key=f"terrain_{hash(str(terrain_request.model_dump()))}",
            expires_at=time.time() + 3600,  # 1 hour
        )

        # Record performance metrics
        performance_monitor.record_request(
            "get_hill_metrics",
            (time.time() - start_time),
            True,
        )

        logger.info(
            "Hill metrics request completed",
            bounds=bounds,
            grid_size=grid_size,
            processing_time_ms=processing_time_ms,
        )

        return response.model_dump()

    except Exception as e:
        # Record error
        performance_monitor.record_request(
            "get_hill_metrics",
            (time.time() - start_time),
            False,
        )

        logger.error(
            "Hill metrics request failed",
            bounds=bounds,
            grid_size=grid_size,
            error=str(e),
            exc_info=True,
        )
        raise


async def get_elevation_profile(
    start_lat: float,
    start_lng: float,
    end_lat: float,
    end_lng: float,
    num_points: int = 100,
) -> dict[str, Any]:
    """
    Get elevation profile along a line.

    Args:
        start_lat: Starting latitude
        start_lng: Starting longitude
        end_lat: Ending latitude
        end_lng: Ending longitude
        num_points: Number of points in the profile

    Returns:
        Elevation profile data
    """
    start_time = time.time()

    try:
        # Create bounds that encompass the line
        bounds = {
            "north": max(start_lat, end_lat) + 0.001,
            "south": min(start_lat, end_lat) - 0.001,
            "east": max(start_lng, end_lng) + 0.001,
            "west": min(start_lng, end_lng) - 0.001,
        }

        # Get terrain data
        hill_metrics_response = await get_hill_metrics(bounds, "64x64", False)
        hill_metrics_response["hill_metrics"]

        # Extract elevation profile
        profile = []
        for i in range(num_points):
            t = i / (num_points - 1)
            lat = start_lat + t * (end_lat - start_lat)
            lng = start_lng + t * (end_lng - start_lng)

            # Simple interpolation to get elevation at this point
            # In production, use proper bilinear interpolation
            elevation = 1500 + 500 * (i / num_points)  # Simplified

            profile.append(
                {
                    "latitude": lat,
                    "longitude": lng,
                    "elevation": elevation,
                    "distance_km": t * 10,  # Simplified distance
                }
            )

        performance_monitor.record_request(
            "get_elevation_profile",
            (time.time() - start_time),
            True,
        )

        return {
            "profile": profile,
            "total_distance_km": 10,  # Simplified
            "elevation_gain_m": max(p["elevation"] for p in profile)
            - min(p["elevation"] for p in profile),
            "processing_time_ms": (time.time() - start_time) * 1000,
        }

    except Exception as e:
        performance_monitor.record_request(
            "get_elevation_profile",
            (time.time() - start_time),
            False,
        )

        logger.error(
            "Elevation profile request failed",
            start_lat=start_lat,
            start_lng=start_lng,
            end_lat=end_lat,
            end_lng=end_lng,
            error=str(e),
            exc_info=True,
        )
        raise


# Register JSON-RPC methods
jsonrpc_handler.register_method("getHillMetrics", get_hill_metrics)
jsonrpc_handler.register_method("getElevationProfile", get_elevation_profile)

# Register MCP tools
mcp_handler.register_tool(
    "get_hill_metrics",
    "Get topographical data and terrain analysis for a geographic area",
    {
        "type": "object",
        "properties": {
            "bounds": {
                "type": "object",
                "properties": {
                    "north": {"type": "number"},
                    "south": {"type": "number"},
                    "east": {"type": "number"},
                    "west": {"type": "number"},
                },
                "required": ["north", "south", "east", "west"],
            },
            "grid_size": {
                "type": "string",
                "enum": ["32x32", "64x64", "96x96", "128x128"],
                "default": "64x64",
            },
            "include_surface_classification": {"type": "boolean", "default": True},
        },
        "required": ["bounds"],
    },
    get_hill_metrics,
)

mcp_handler.register_tool(
    "get_elevation_profile",
    "Get elevation profile along a line between two points",
    {
        "type": "object",
        "properties": {
            "start_lat": {"type": "number"},
            "start_lng": {"type": "number"},
            "end_lat": {"type": "number"},
            "end_lng": {"type": "number"},
            "num_points": {"type": "integer", "default": 100},
        },
        "required": ["start_lat", "start_lng", "end_lat", "end_lng"],
    },
    get_elevation_profile,
)


# Health checks
async def check_dem_processor() -> bool:
    """Check if DEM processor is working."""
    try:
        # Simple test bounds
        from agents.hill_metrics.models import GeographicBounds
        from agents.hill_metrics.models import GridSize

        test_bounds = GeographicBounds(
            north=46.0,
            south=45.9,
            east=7.1,
            west=7.0,
        )

        # Try to process a small area
        await dem_processor.process_terrain(test_bounds, GridSize.SMALL, False)
        return True
    except Exception:
        return False


health_checker.add_check("dem_processor", check_dem_processor)


# Add health check endpoint
@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check endpoint."""
    return await health_checker.run_checks()


if __name__ == "__main__":
    uvicorn.run(
        "agents.hill_metrics.server:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
        log_config=None,  # Use our custom logging
    )
