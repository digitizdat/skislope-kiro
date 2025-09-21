"""Equipment Agent server implementation."""

import time
from datetime import datetime
from typing import Any

import structlog
import uvicorn

from agents.equipment.equipment_service import EquipmentService
from agents.equipment.models import EquipmentRequest
from agents.shared.jsonrpc import create_jsonrpc_app
from agents.shared.logging_config import setup_logging
from agents.shared.mcp import add_mcp_support
from agents.shared.monitoring import HealthChecker
from agents.shared.monitoring import PerformanceMonitor

# Set up logging
setup_logging()
logger = structlog.get_logger(__name__)

# Create FastAPI app with JSON-RPC support
app, jsonrpc_handler = create_jsonrpc_app(
    title="Equipment Agent",
    description="Ski infrastructure and facility information agent",
)

# Add MCP support
mcp_handler = add_mcp_support(app, "equipment")

# Initialize components
equipment_service = EquipmentService()
performance_monitor = PerformanceMonitor("equipment")
health_checker = HealthChecker("equipment")


# JSON-RPC Methods
async def get_equipment_data(
    area: dict[str, Any],
    include_status: bool = True,
    equipment_types: list[str] | None = None,
    include_lifts: bool = True,
    include_trails: bool = True,
    include_facilities: bool = True,
    include_safety_equipment: bool = True,
    operational_only: bool = False,
    open_trails_only: bool = False,
) -> dict[str, Any]:
    """
    Get equipment data for the specified ski area.

    Args:
        area: Ski area object with bounds and location info
        include_status: Include operational status
        equipment_types: List of equipment types to include
        include_lifts: Include lift data
        include_trails: Include trail data
        include_facilities: Include facility data
        include_safety_equipment: Include safety equipment
        operational_only: Only include operational equipment
        open_trails_only: Only include open trails

    Returns:
        Equipment data
    """
    start_time = time.time()

    try:
        # Create request
        # Extract bounds from area
        bounds = area.get("bounds", {})
        north_east = bounds.get("northEast", {})
        south_west = bounds.get("southWest", {})

        north = north_east.get("lat", 46.0)
        south = south_west.get("lat", 45.0)
        east = north_east.get("lng", 7.0)
        west = south_west.get("lng", 6.0)

        equipment_request = EquipmentRequest(
            north=north,
            south=south,
            east=east,
            west=west,
            include_lifts=include_lifts,
            include_trails=include_trails,
            include_facilities=include_facilities,
            include_safety_equipment=include_safety_equipment,
            operational_only=operational_only,
            open_trails_only=open_trails_only,
        )

        # Get equipment data
        equipment_data = await equipment_service.get_equipment_data(equipment_request)

        # Record performance metrics
        performance_monitor.record_request(
            "get_equipment_data",
            (time.time() - start_time),
            True,
        )

        logger.info(
            "Equipment data request completed",
            bounds={"north": north, "south": south, "east": east, "west": west},
            lifts=len(equipment_data["lifts"]),
            trails=len(equipment_data["trails"]),
            facilities=len(equipment_data["facilities"]),
            safety_equipment=len(equipment_data["safety_equipment"]),
            processing_time_ms=equipment_data["processing_time_ms"],
        )

        return equipment_data

    except Exception as e:
        # Record error
        performance_monitor.record_request(
            "get_equipment_data",
            (time.time() - start_time),
            False,
        )

        logger.error(
            "Equipment data request failed",
            bounds={"north": north, "south": south, "east": east, "west": west},
            error=str(e),
            exc_info=True,
        )
        raise


async def get_lift_status(
    lift_ids: list[str] | None = None,
    bounds: dict[str, float] | None = None,
) -> dict[str, Any]:
    """
    Get lift status information.

    Args:
        lift_ids: Specific lift IDs to query
        bounds: Geographic bounds (north, south, east, west)

    Returns:
        Lift status data
    """
    start_time = time.time()

    try:
        # If bounds provided, get all lifts in area
        if bounds:
            equipment_request = EquipmentRequest(
                north=bounds["north"],
                south=bounds["south"],
                east=bounds["east"],
                west=bounds["west"],
                include_lifts=True,
                include_trails=False,
                include_facilities=False,
                include_safety_equipment=False,
            )

            equipment_data = await equipment_service.get_equipment_data(
                equipment_request
            )
            lifts = equipment_data["lifts"]

            # Filter by lift IDs if provided
            if lift_ids:
                lifts = [lift for lift in lifts if lift["id"] in lift_ids]

        else:
            # For demonstration, return sample data
            lifts = []

        # Extract status information
        lift_status = []
        for lift in lifts:
            lift_status.append(
                {
                    "id": lift["id"],
                    "name": lift["name"],
                    "type": lift["type"],
                    "status": lift["status"],
                    "capacity_per_hour": lift["capacity_per_hour"],
                    "vertical_rise_m": lift["vertical_rise_m"],
                    "operating_hours": lift["operating_hours"],
                    "last_inspection": lift["last_inspection"],
                    "next_maintenance": lift["next_maintenance"],
                }
            )

        # Record performance metrics
        performance_monitor.record_request(
            "get_lift_status",
            (time.time() - start_time),
            True,
        )

        processing_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "Lift status request completed",
            lift_count=len(lift_status),
            processing_time_ms=processing_time_ms,
        )

        return {
            "lifts": lift_status,
            "timestamp": datetime.now().isoformat(),
            "processing_time_ms": processing_time_ms,
        }

    except Exception as e:
        # Record error
        performance_monitor.record_request(
            "get_lift_status",
            (time.time() - start_time),
            False,
        )

        logger.error(
            "Lift status request failed",
            lift_ids=lift_ids,
            bounds=bounds,
            error=str(e),
            exc_info=True,
        )
        raise


async def get_trail_conditions(
    trail_ids: list[str] | None = None,
    bounds: dict[str, float] | None = None,
    difficulty_filter: str | None = None,
) -> dict[str, Any]:
    """
    Get trail conditions information.

    Args:
        trail_ids: Specific trail IDs to query
        bounds: Geographic bounds (north, south, east, west)
        difficulty_filter: Filter by difficulty level

    Returns:
        Trail conditions data
    """
    start_time = time.time()

    try:
        # If bounds provided, get all trails in area
        if bounds:
            equipment_request = EquipmentRequest(
                north=bounds["north"],
                south=bounds["south"],
                east=bounds["east"],
                west=bounds["west"],
                include_lifts=False,
                include_trails=True,
                include_facilities=False,
                include_safety_equipment=False,
            )

            equipment_data = await equipment_service.get_equipment_data(
                equipment_request
            )
            trails = equipment_data["trails"]

            # Filter by trail IDs if provided
            if trail_ids:
                trails = [trail for trail in trails if trail["id"] in trail_ids]

            # Filter by difficulty if provided
            if difficulty_filter:
                trails = [
                    trail
                    for trail in trails
                    if trail["difficulty"] == difficulty_filter
                ]

        else:
            # For demonstration, return sample data
            trails = []

        # Extract conditions information
        trail_conditions = []
        for trail in trails:
            trail_conditions.append(
                {
                    "id": trail["id"],
                    "name": trail["name"],
                    "difficulty": trail["difficulty"],
                    "status": trail["status"],
                    "length_m": trail["length_m"],
                    "vertical_drop_m": trail["vertical_drop_m"],
                    "average_grade_percent": trail["average_grade_percent"],
                    "groomed": trail["groomed"],
                    "snowmaking": trail["snowmaking"],
                    "last_groomed": trail["last_groomed"],
                    "snow_depth_cm": trail["snow_depth_cm"],
                    "surface_condition": trail["surface_condition"],
                }
            )

        # Record performance metrics
        performance_monitor.record_request(
            "get_trail_conditions",
            (time.time() - start_time),
            True,
        )

        processing_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "Trail conditions request completed",
            trail_count=len(trail_conditions),
            difficulty_filter=difficulty_filter,
            processing_time_ms=processing_time_ms,
        )

        return {
            "trails": trail_conditions,
            "timestamp": datetime.now().isoformat(),
            "processing_time_ms": processing_time_ms,
        }

    except Exception as e:
        # Record error
        performance_monitor.record_request(
            "get_trail_conditions",
            (time.time() - start_time),
            False,
        )

        logger.error(
            "Trail conditions request failed",
            trail_ids=trail_ids,
            bounds=bounds,
            difficulty_filter=difficulty_filter,
            error=str(e),
            exc_info=True,
        )
        raise


async def get_facilities(
    bounds: dict[str, float],
    facility_types: list[str] | None = None,
    open_only: bool = False,
) -> dict[str, Any]:
    """
    Get facility information.

    Args:
        bounds: Geographic bounds (north, south, east, west)
        facility_types: Filter by facility types
        open_only: Only include open facilities

    Returns:
        Facility data
    """
    start_time = time.time()

    try:
        # Get facilities in area
        equipment_request = EquipmentRequest(
            north=bounds["north"],
            south=bounds["south"],
            east=bounds["east"],
            west=bounds["west"],
            include_lifts=False,
            include_trails=False,
            include_facilities=True,
            include_safety_equipment=False,
        )

        equipment_data = await equipment_service.get_equipment_data(equipment_request)
        facilities = equipment_data["facilities"]

        # Apply filters
        if facility_types:
            facilities = [f for f in facilities if f["type"] in facility_types]

        if open_only:
            facilities = [f for f in facilities if f["is_open"]]

        # Record performance metrics
        performance_monitor.record_request(
            "get_facilities",
            (time.time() - start_time),
            True,
        )

        processing_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "Facilities request completed",
            facility_count=len(facilities),
            facility_types=facility_types,
            open_only=open_only,
            processing_time_ms=processing_time_ms,
        )

        return {
            "facilities": facilities,
            "timestamp": datetime.now().isoformat(),
            "processing_time_ms": processing_time_ms,
        }

    except Exception as e:
        # Record error
        performance_monitor.record_request(
            "get_facilities",
            (time.time() - start_time),
            False,
        )

        logger.error(
            "Facilities request failed",
            bounds=bounds,
            facility_types=facility_types,
            open_only=open_only,
            error=str(e),
            exc_info=True,
        )
        raise


# Register JSON-RPC methods
jsonrpc_handler.register_method("getEquipmentData", get_equipment_data)
jsonrpc_handler.register_method("getLiftStatus", get_lift_status)
jsonrpc_handler.register_method("getTrailConditions", get_trail_conditions)
jsonrpc_handler.register_method("getFacilities", get_facilities)

# Register MCP tools
mcp_handler.register_tool(
    "get_equipment_data",
    "Get comprehensive equipment data for a ski area including lifts, trails, facilities, and safety equipment",
    {
        "type": "object",
        "properties": {
            "north": {"type": "number", "minimum": -90, "maximum": 90},
            "south": {"type": "number", "minimum": -90, "maximum": 90},
            "east": {"type": "number", "minimum": -180, "maximum": 180},
            "west": {"type": "number", "minimum": -180, "maximum": 180},
            "include_lifts": {"type": "boolean", "default": True},
            "include_trails": {"type": "boolean", "default": True},
            "include_facilities": {"type": "boolean", "default": True},
            "include_safety_equipment": {"type": "boolean", "default": True},
            "operational_only": {"type": "boolean", "default": False},
            "open_trails_only": {"type": "boolean", "default": False},
        },
        "required": ["north", "south", "east", "west"],
    },
    get_equipment_data,
)

mcp_handler.register_tool(
    "get_lift_status",
    "Get current status of ski lifts",
    {
        "type": "object",
        "properties": {
            "lift_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Specific lift IDs to query",
            },
            "bounds": {
                "type": "object",
                "properties": {
                    "north": {"type": "number"},
                    "south": {"type": "number"},
                    "east": {"type": "number"},
                    "west": {"type": "number"},
                },
                "description": "Geographic bounds to search within",
            },
        },
    },
    get_lift_status,
)

mcp_handler.register_tool(
    "get_trail_conditions",
    "Get current trail conditions and status",
    {
        "type": "object",
        "properties": {
            "trail_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Specific trail IDs to query",
            },
            "bounds": {
                "type": "object",
                "properties": {
                    "north": {"type": "number"},
                    "south": {"type": "number"},
                    "east": {"type": "number"},
                    "west": {"type": "number"},
                },
                "description": "Geographic bounds to search within",
            },
            "difficulty_filter": {
                "type": "string",
                "enum": [
                    "beginner",
                    "intermediate",
                    "advanced",
                    "expert",
                    "terrain-park",
                    "cross-country",
                ],
                "description": "Filter by difficulty level",
            },
        },
    },
    get_trail_conditions,
)

mcp_handler.register_tool(
    "get_facilities",
    "Get information about ski area facilities",
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
            "facility_types": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": [
                        "lodge",
                        "restaurant",
                        "cafeteria",
                        "bar",
                        "shop",
                        "rental",
                        "ski-school",
                        "first-aid",
                        "parking",
                        "restroom",
                        "childcare",
                    ],
                },
                "description": "Filter by facility types",
            },
            "open_only": {"type": "boolean", "default": False},
        },
        "required": ["bounds"],
    },
    get_facilities,
)


# Health checks
async def check_equipment_service() -> bool:
    """Check if equipment service is working."""
    try:
        # Test with a simple request
        test_request = EquipmentRequest(
            north=46.0,
            south=45.9,
            east=7.1,
            west=7.0,
            include_lifts=True,
            include_trails=False,
            include_facilities=False,
            include_safety_equipment=False,
        )

        await equipment_service.get_equipment_data(test_request)
        return True
    except Exception:
        return False


health_checker.add_check("equipment_service", check_equipment_service)


# Lifespan handlers are now managed by the shared jsonrpc module
# The startup and shutdown logic is handled in the create_jsonrpc_app function


# Add health check endpoint
@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check endpoint."""
    return await health_checker.run_checks()


if __name__ == "__main__":
    uvicorn.run(
        "agents.equipment.server:app",
        host="0.0.0.0",
        port=8003,
        reload=False,
        log_config=None,  # Use our custom logging
    )
