"""Data models for Weather Agent."""

from datetime import datetime
from enum import Enum
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class SnowCondition(str, Enum):
    """Snow condition types."""
    
    POWDER = "powder"
    PACKED_POWDER = "packed-powder"
    HARD_PACK = "hard-pack"
    ICE = "ice"
    SLUSH = "slush"
    ARTIFICIAL = "artificial"
    NO_SNOW = "no-snow"


class WeatherCondition(str, Enum):
    """Weather condition types."""
    
    CLEAR = "clear"
    PARTLY_CLOUDY = "partly-cloudy"
    CLOUDY = "cloudy"
    OVERCAST = "overcast"
    LIGHT_SNOW = "light-snow"
    MODERATE_SNOW = "moderate-snow"
    HEAVY_SNOW = "heavy-snow"
    LIGHT_RAIN = "light-rain"
    MODERATE_RAIN = "moderate-rain"
    HEAVY_RAIN = "heavy-rain"
    FOG = "fog"
    BLIZZARD = "blizzard"


class WindData(BaseModel):
    """Wind information."""
    
    speed_kmh: float = Field(..., ge=0, description="Wind speed in km/h")
    direction_degrees: float = Field(..., ge=0, lt=360, description="Wind direction in degrees")
    gust_speed_kmh: Optional[float] = Field(None, ge=0, description="Wind gust speed in km/h")


class SnowData(BaseModel):
    """Snow information."""
    
    depth_cm: float = Field(..., ge=0, description="Snow depth in centimeters")
    condition: SnowCondition = Field(..., description="Snow condition type")
    temperature_c: float = Field(..., description="Snow temperature in Celsius")
    density_kg_m3: Optional[float] = Field(None, ge=0, description="Snow density in kg/m³")
    last_snowfall_hours: Optional[int] = Field(None, ge=0, description="Hours since last snowfall")


class VisibilityData(BaseModel):
    """Visibility information."""
    
    distance_km: float = Field(..., ge=0, description="Visibility distance in kilometers")
    condition: str = Field(..., description="Visibility condition description")


class WeatherData(BaseModel):
    """Current weather data."""
    
    timestamp: datetime = Field(..., description="Data timestamp")
    temperature_c: float = Field(..., description="Air temperature in Celsius")
    feels_like_c: float = Field(..., description="Feels like temperature in Celsius")
    humidity_percent: float = Field(..., ge=0, le=100, description="Relative humidity percentage")
    pressure_hpa: float = Field(..., gt=0, description="Atmospheric pressure in hPa")
    condition: WeatherCondition = Field(..., description="Weather condition")
    wind: WindData = Field(..., description="Wind information")
    snow: Optional[SnowData] = Field(None, description="Snow information")
    visibility: VisibilityData = Field(..., description="Visibility information")
    uv_index: Optional[float] = Field(None, ge=0, description="UV index")
    precipitation_mm: float = Field(default=0, ge=0, description="Precipitation in mm")


class WeatherForecast(BaseModel):
    """Weather forecast data."""
    
    timestamp: datetime = Field(..., description="Forecast timestamp")
    temperature_high_c: float = Field(..., description="High temperature in Celsius")
    temperature_low_c: float = Field(..., description="Low temperature in Celsius")
    condition: WeatherCondition = Field(..., description="Weather condition")
    precipitation_probability: float = Field(..., ge=0, le=1, description="Precipitation probability (0-1)")
    precipitation_mm: float = Field(default=0, ge=0, description="Expected precipitation in mm")
    wind_speed_kmh: float = Field(..., ge=0, description="Wind speed in km/h")
    snow_depth_cm: Optional[float] = Field(None, ge=0, description="Expected snow depth in cm")


class HistoricalWeatherData(BaseModel):
    """Historical weather data."""
    
    date: datetime = Field(..., description="Date of the data")
    temperature_high_c: float = Field(..., description="High temperature in Celsius")
    temperature_low_c: float = Field(..., description="Low temperature in Celsius")
    temperature_avg_c: float = Field(..., description="Average temperature in Celsius")
    precipitation_mm: float = Field(default=0, ge=0, description="Total precipitation in mm")
    snow_depth_cm: Optional[float] = Field(None, ge=0, description="Snow depth in cm")
    wind_speed_avg_kmh: float = Field(..., ge=0, description="Average wind speed in km/h")
    condition: WeatherCondition = Field(..., description="Dominant weather condition")


class WeatherRequest(BaseModel):
    """Request for weather data."""
    
    latitude: float = Field(..., ge=-90, le=90, description="Latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude")
    timestamp: Optional[datetime] = Field(None, description="Specific timestamp (for historical data)")
    include_forecast: bool = Field(default=False, description="Include forecast data")
    forecast_days: int = Field(default=7, ge=1, le=14, description="Number of forecast days")
    include_historical: bool = Field(default=False, description="Include historical data")
    historical_days: int = Field(default=30, ge=1, le=365, description="Number of historical days")


class WeatherResponse(BaseModel):
    """Response containing weather data."""
    
    current: WeatherData = Field(..., description="Current weather data")
    forecast: List[WeatherForecast] = Field(default_factory=list, description="Weather forecast")
    historical: List[HistoricalWeatherData] = Field(default_factory=list, description="Historical weather data")
    location: dict = Field(..., description="Location information")
    data_source: str = Field(..., description="Weather data source")
    cache_expires_at: datetime = Field(..., description="Cache expiration time")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")


class SkiConditionsRequest(BaseModel):
    """Request for ski-specific conditions."""
    
    latitude: float = Field(..., ge=-90, le=90, description="Latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude")
    elevation_m: Optional[float] = Field(None, description="Elevation in meters")


class SkiConditions(BaseModel):
    """Ski-specific weather conditions."""
    
    overall_rating: float = Field(..., ge=0, le=10, description="Overall ski conditions rating (0-10)")
    snow_quality: SnowCondition = Field(..., description="Snow quality")
    visibility_rating: float = Field(..., ge=0, le=10, description="Visibility rating (0-10)")
    wind_rating: float = Field(..., ge=0, le=10, description="Wind conditions rating (0-10)")
    temperature_rating: float = Field(..., ge=0, le=10, description="Temperature rating (0-10)")
    recommended_gear: List[str] = Field(..., description="Recommended gear/clothing")
    safety_warnings: List[str] = Field(default_factory=list, description="Safety warnings")
    best_time_of_day: str = Field(..., description="Best time of day for skiing")


class SkiConditionsResponse(BaseModel):
    """Response containing ski conditions."""
    
    conditions: SkiConditions = Field(..., description="Ski conditions")
    weather: WeatherData = Field(..., description="Current weather data")
    location: dict = Field(..., description="Location information")
    timestamp: datetime = Field(..., description="Data timestamp")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")