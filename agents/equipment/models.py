"""Data models for Equipment Agent."""

from datetime import datetime
from enum import Enum
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class LiftType(str, Enum):
    """Ski lift types."""
    
    CHAIRLIFT = "chairlift"
    GONDOLA = "gondola"
    CABLE_CAR = "cable-car"
    T_BAR = "t-bar"
    PLATTER_LIFT = "platter-lift"
    MAGIC_CARPET = "magic-carpet"
    FUNICULAR = "funicular"


class LiftStatus(str, Enum):
    """Lift operational status."""
    
    OPERATIONAL = "operational"
    CLOSED = "closed"
    MAINTENANCE = "maintenance"
    WEATHER_HOLD = "weather-hold"
    MECHANICAL_ISSUE = "mechanical-issue"


class TrailDifficulty(str, Enum):
    """Trail difficulty levels."""
    
    BEGINNER = "beginner"      # Green circle
    INTERMEDIATE = "intermediate"  # Blue square
    ADVANCED = "advanced"      # Black diamond
    EXPERT = "expert"          # Double black diamond
    TERRAIN_PARK = "terrain-park"
    CROSS_COUNTRY = "cross-country"


class TrailStatus(str, Enum):
    """Trail operational status."""
    
    OPEN = "open"
    CLOSED = "closed"
    GROOMED = "groomed"
    UNGROOMED = "ungroomed"
    POWDER = "powder"
    PACKED_POWDER = "packed-powder"
    MACHINE_GROOMED = "machine-groomed"


class FacilityType(str, Enum):
    """Facility types."""
    
    LODGE = "lodge"
    RESTAURANT = "restaurant"
    CAFETERIA = "cafeteria"
    BAR = "bar"
    SHOP = "shop"
    RENTAL = "rental"
    SKI_SCHOOL = "ski-school"
    FIRST_AID = "first-aid"
    PARKING = "parking"
    RESTROOM = "restroom"
    CHILDCARE = "childcare"


class SafetyEquipmentType(str, Enum):
    """Safety equipment types."""
    
    AVALANCHE_BEACON = "avalanche-beacon"
    EMERGENCY_PHONE = "emergency-phone"
    FIRST_AID_STATION = "first-aid-station"
    PATROL_HUT = "patrol-hut"
    BOUNDARY_MARKER = "boundary-marker"
    WARNING_SIGN = "warning-sign"
    CLOSURE_ROPE = "closure-rope"
    SAFETY_NET = "safety-net"
    PADDING = "padding"


class LiftInfo(BaseModel):
    """Ski lift information."""
    
    id: str = Field(..., description="Unique lift identifier")
    name: str = Field(..., description="Lift name")
    type: LiftType = Field(..., description="Lift type")
    status: LiftStatus = Field(..., description="Current operational status")
    capacity_per_hour: int = Field(..., gt=0, description="Hourly capacity (people)")
    vertical_rise_m: float = Field(..., gt=0, description="Vertical rise in meters")
    length_m: float = Field(..., gt=0, description="Lift length in meters")
    ride_time_minutes: float = Field(..., gt=0, description="Ride time in minutes")
    
    # Geographic data
    base_latitude: float = Field(..., ge=-90, le=90, description="Base station latitude")
    base_longitude: float = Field(..., ge=-180, le=180, description="Base station longitude")
    base_elevation_m: float = Field(..., description="Base station elevation in meters")
    top_latitude: float = Field(..., ge=-90, le=90, description="Top station latitude")
    top_longitude: float = Field(..., ge=-180, le=180, description="Top station longitude")
    top_elevation_m: float = Field(..., description="Top station elevation in meters")
    
    # Operational data
    operating_hours: dict = Field(default_factory=dict, description="Operating hours by day")
    last_inspection: Optional[datetime] = Field(None, description="Last safety inspection")
    next_maintenance: Optional[datetime] = Field(None, description="Next scheduled maintenance")
    
    # Additional info
    heated_seats: bool = Field(default=False, description="Has heated seats")
    weather_shield: bool = Field(default=False, description="Has weather protection")
    beginner_friendly: bool = Field(default=True, description="Suitable for beginners")


class TrailInfo(BaseModel):
    """Ski trail information."""
    
    id: str = Field(..., description="Unique trail identifier")
    name: str = Field(..., description="Trail name")
    difficulty: TrailDifficulty = Field(..., description="Trail difficulty level")
    status: TrailStatus = Field(..., description="Current trail status")
    length_m: float = Field(..., gt=0, description="Trail length in meters")
    vertical_drop_m: float = Field(..., gt=0, description="Vertical drop in meters")
    average_grade_percent: float = Field(..., description="Average grade percentage")
    max_grade_percent: float = Field(..., description="Maximum grade percentage")
    
    # Geographic data
    start_latitude: float = Field(..., ge=-90, le=90, description="Trail start latitude")
    start_longitude: float = Field(..., ge=-180, le=180, description="Trail start longitude")
    start_elevation_m: float = Field(..., description="Trail start elevation in meters")
    end_latitude: float = Field(..., ge=-90, le=90, description="Trail end latitude")
    end_longitude: float = Field(..., ge=-180, le=180, description="Trail end longitude")
    end_elevation_m: float = Field(..., description="Trail end elevation in meters")
    
    # Trail characteristics
    width_m: float = Field(..., gt=0, description="Average trail width in meters")
    groomed: bool = Field(default=True, description="Is trail groomed")
    snowmaking: bool = Field(default=False, description="Has snowmaking capability")
    night_skiing: bool = Field(default=False, description="Open for night skiing")
    
    # Conditions
    last_groomed: Optional[datetime] = Field(None, description="Last grooming time")
    snow_depth_cm: Optional[float] = Field(None, ge=0, description="Current snow depth in cm")
    surface_condition: Optional[str] = Field(None, description="Current surface condition")
    
    # Connected lifts and trails
    access_lifts: List[str] = Field(default_factory=list, description="Lift IDs providing access")
    connected_trails: List[str] = Field(default_factory=list, description="Connected trail IDs")


class FacilityInfo(BaseModel):
    """Facility information."""
    
    id: str = Field(..., description="Unique facility identifier")
    name: str = Field(..., description="Facility name")
    type: FacilityType = Field(..., description="Facility type")
    latitude: float = Field(..., ge=-90, le=90, description="Facility latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Facility longitude")
    elevation_m: float = Field(..., description="Facility elevation in meters")
    
    # Operational data
    is_open: bool = Field(default=True, description="Currently open")
    operating_hours: dict = Field(default_factory=dict, description="Operating hours by day")
    capacity: Optional[int] = Field(None, gt=0, description="Maximum capacity")
    
    # Contact and details
    phone: Optional[str] = Field(None, description="Contact phone number")
    website: Optional[str] = Field(None, description="Website URL")
    description: Optional[str] = Field(None, description="Facility description")
    amenities: List[str] = Field(default_factory=list, description="Available amenities")
    
    # Accessibility
    wheelchair_accessible: bool = Field(default=False, description="Wheelchair accessible")
    parking_available: bool = Field(default=False, description="Parking available")


class SafetyEquipment(BaseModel):
    """Safety equipment information."""
    
    id: str = Field(..., description="Unique equipment identifier")
    type: SafetyEquipmentType = Field(..., description="Equipment type")
    latitude: float = Field(..., ge=-90, le=90, description="Equipment latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Equipment longitude")
    elevation_m: float = Field(..., description="Equipment elevation in meters")
    
    # Status and maintenance
    is_operational: bool = Field(default=True, description="Currently operational")
    last_inspection: Optional[datetime] = Field(None, description="Last inspection date")
    next_maintenance: Optional[datetime] = Field(None, description="Next maintenance date")
    
    # Equipment details
    model: Optional[str] = Field(None, description="Equipment model")
    installation_date: Optional[datetime] = Field(None, description="Installation date")
    coverage_radius_m: Optional[float] = Field(None, gt=0, description="Coverage radius in meters")
    
    # Associated trail/lift
    associated_trail: Optional[str] = Field(None, description="Associated trail ID")
    associated_lift: Optional[str] = Field(None, description="Associated lift ID")


class EquipmentRequest(BaseModel):
    """Request for equipment data."""
    
    # Geographic bounds
    north: float = Field(..., ge=-90, le=90, description="Northern latitude bound")
    south: float = Field(..., ge=-90, le=90, description="Southern latitude bound")
    east: float = Field(..., ge=-180, le=180, description="Eastern longitude bound")
    west: float = Field(..., ge=-180, le=180, description="Western longitude bound")
    
    # Filters
    include_lifts: bool = Field(default=True, description="Include lift data")
    include_trails: bool = Field(default=True, description="Include trail data")
    include_facilities: bool = Field(default=True, description="Include facility data")
    include_safety_equipment: bool = Field(default=True, description="Include safety equipment")
    
    # Status filters
    operational_only: bool = Field(default=False, description="Only include operational equipment")
    open_trails_only: bool = Field(default=False, description="Only include open trails")


class EquipmentResponse(BaseModel):
    """Response containing equipment data."""
    
    lifts: List[LiftInfo] = Field(default_factory=list, description="Ski lifts")
    trails: List[TrailInfo] = Field(default_factory=list, description="Ski trails")
    facilities: List[FacilityInfo] = Field(default_factory=list, description="Facilities")
    safety_equipment: List[SafetyEquipment] = Field(default_factory=list, description="Safety equipment")
    
    # Metadata
    bounds: dict = Field(..., description="Geographic bounds of the data")
    total_lifts: int = Field(..., description="Total number of lifts")
    operational_lifts: int = Field(..., description="Number of operational lifts")
    total_trails: int = Field(..., description="Total number of trails")
    open_trails: int = Field(..., description="Number of open trails")
    last_updated: datetime = Field(..., description="Last data update time")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")


class LiftStatusUpdate(BaseModel):
    """Lift status update."""
    
    lift_id: str = Field(..., description="Lift identifier")
    status: LiftStatus = Field(..., description="New status")
    reason: Optional[str] = Field(None, description="Reason for status change")
    estimated_reopening: Optional[datetime] = Field(None, description="Estimated reopening time")


class TrailStatusUpdate(BaseModel):
    """Trail status update."""
    
    trail_id: str = Field(..., description="Trail identifier")
    status: TrailStatus = Field(..., description="New status")
    snow_depth_cm: Optional[float] = Field(None, ge=0, description="Current snow depth")
    surface_condition: Optional[str] = Field(None, description="Surface condition")
    last_groomed: Optional[datetime] = Field(None, description="Last grooming time")