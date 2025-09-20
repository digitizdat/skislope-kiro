"""Data models for Hill Metrics Agent."""

from enum import Enum

from pydantic import BaseModel
from pydantic import Field


class SurfaceType(str, Enum):
    """Surface type classification."""

    POWDER = "powder"
    PACKED = "packed"
    ICE = "ice"
    MOGULS = "moguls"
    TREES = "trees"
    ROCKS = "rocks"


class GridSize(str, Enum):
    """Terrain grid size options."""

    SMALL = "32x32"
    MEDIUM = "64x64"
    LARGE = "96x96"
    EXTRA_LARGE = "128x128"


class GeographicBounds(BaseModel):
    """Geographic bounding box."""

    north: float = Field(..., ge=-90, le=90, description="Northern latitude")
    south: float = Field(..., ge=-90, le=90, description="Southern latitude")
    east: float = Field(..., ge=-180, le=180, description="Eastern longitude")
    west: float = Field(..., ge=-180, le=180, description="Western longitude")


class ElevationData(BaseModel):
    """Elevation data for a terrain grid."""

    grid: list[list[float]] = Field(..., description="2D elevation grid in meters")
    resolution: float = Field(
        ..., gt=0, description="Grid resolution in meters per cell"
    )
    bounds: GeographicBounds = Field(..., description="Geographic bounds of the data")
    no_data_value: float = Field(
        default=-9999, description="Value representing no data"
    )


class SlopeData(BaseModel):
    """Slope angle data for terrain analysis."""

    grid: list[list[float]] = Field(..., description="2D slope angle grid in degrees")
    resolution: float = Field(
        ..., gt=0, description="Grid resolution in meters per cell"
    )
    bounds: GeographicBounds = Field(..., description="Geographic bounds of the data")


class AspectData(BaseModel):
    """Aspect (slope direction) data for terrain analysis."""

    grid: list[list[float]] = Field(
        ..., description="2D aspect grid in degrees (0-360)"
    )
    resolution: float = Field(
        ..., gt=0, description="Grid resolution in meters per cell"
    )
    bounds: GeographicBounds = Field(..., description="Geographic bounds of the data")


class SurfaceClassification(BaseModel):
    """Surface type classification for terrain."""

    grid: list[list[SurfaceType]] = Field(..., description="2D surface type grid")
    resolution: float = Field(
        ..., gt=0, description="Grid resolution in meters per cell"
    )
    bounds: GeographicBounds = Field(..., description="Geographic bounds of the data")
    confidence: list[list[float]] = Field(
        default_factory=list,
        description="Classification confidence (0-1)",
    )


class SafetyZone(BaseModel):
    """Safety zone definition for FIS compatibility."""

    id: str = Field(..., description="Unique zone identifier")
    type: str = Field(..., description="Zone type (barrier, net, padding)")
    coordinates: list[list[float]] = Field(..., description="Zone boundary coordinates")
    height: float = Field(..., gt=0, description="Zone height in meters")
    material: str | None = Field(None, description="Zone material type")


class CourseMarker(BaseModel):
    """Course marker for FIS compatibility."""

    id: str = Field(..., description="Unique marker identifier")
    type: str = Field(..., description="Marker type (gate, start, finish, timing)")
    latitude: float = Field(..., ge=-90, le=90, description="Marker latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Marker longitude")
    elevation: float = Field(..., description="Marker elevation in meters")
    orientation: float = Field(
        default=0, ge=0, lt=360, description="Marker orientation in degrees"
    )


class HillMetrics(BaseModel):
    """Complete hill metrics data."""

    elevation: ElevationData = Field(..., description="Elevation data")
    slope: SlopeData = Field(..., description="Slope angle data")
    aspect: AspectData = Field(..., description="Aspect data")
    surface_classification: SurfaceClassification = Field(
        ..., description="Surface type classification"
    )
    safety_zones: list[SafetyZone] = Field(
        default_factory=list, description="Safety zones for FIS compatibility"
    )
    course_markers: list[CourseMarker] = Field(
        default_factory=list, description="Course markers for FIS compatibility"
    )
    metadata: dict = Field(default_factory=dict, description="Additional metadata")


class TerrainRequest(BaseModel):
    """Request for terrain data processing."""

    bounds: GeographicBounds = Field(
        ..., description="Geographic bounds for data extraction"
    )
    grid_size: GridSize = Field(
        default=GridSize.MEDIUM, description="Desired grid resolution"
    )
    include_surface_classification: bool = Field(
        default=True, description="Include surface type analysis"
    )
    include_safety_zones: bool = Field(
        default=False, description="Include FIS safety zones"
    )
    include_course_markers: bool = Field(
        default=False, description="Include FIS course markers"
    )


class TerrainResponse(BaseModel):
    """Response containing processed terrain data."""

    hill_metrics: HillMetrics = Field(..., description="Processed hill metrics")
    processing_time_ms: float = Field(
        ..., description="Processing time in milliseconds"
    )
    data_sources: list[str] = Field(..., description="Data sources used")
    cache_key: str = Field(..., description="Cache key for this data")
    expires_at: float = Field(..., description="Cache expiration timestamp")
