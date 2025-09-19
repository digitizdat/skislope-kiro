"""
Mock Data Generator for integration testing.

Provides realistic test data generation for terrain, weather, equipment,
and cache state manipulation to support comprehensive integration testing.
"""

import json
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import math

from agents.hill_metrics.models import (
    HillMetrics, ElevationData, SlopeData, AspectData, SurfaceClassification,
    GeographicBounds, SurfaceType, GridSize, SafetyZone, CourseMarker,
    TerrainResponse
)
from agents.weather.models import (
    WeatherData, WeatherForecast, HistoricalWeatherData, WindData, SnowData,
    VisibilityData, WeatherCondition, SnowCondition, WeatherResponse,
    SkiConditions, SkiConditionsResponse
)
from agents.equipment.models import (
    LiftInfo, TrailInfo, FacilityInfo, SafetyEquipment, EquipmentResponse,
    LiftType, LiftStatus, TrailDifficulty, TrailStatus, FacilityType,
    SafetyEquipmentType
)


class TestScenario(Enum):
    """Predefined test scenarios."""
    NORMAL_CONDITIONS = "normal"
    EXTREME_WEATHER = "extreme_weather"
    EQUIPMENT_FAILURES = "equipment_failures"
    CACHE_CORRUPTION = "cache_corruption"
    NETWORK_ISSUES = "network_issues"
    PERFORMANCE_STRESS = "performance_stress"
    EDGE_CASES = "edge_cases"


@dataclass
class MockDataConfig:
    """Configuration for mock data generation."""
    seed: Optional[int] = None
    scenario: TestScenario = TestScenario.NORMAL_CONDITIONS
    grid_size: GridSize = GridSize.MEDIUM
    include_fis_data: bool = False
    weather_variability: float = 0.3  # 0.0 = stable, 1.0 = highly variable
    equipment_failure_rate: float = 0.1  # 0.0 = no failures, 1.0 = all failed
    cache_corruption_rate: float = 0.0  # 0.0 = no corruption, 1.0 = all corrupted
    performance_load_factor: float = 1.0  # 1.0 = normal, >1.0 = increased load


class MockDataGenerator:
    """Generates realistic mock data for integration testing."""
    
    # Predefined ski areas with realistic coordinates
    SKI_AREAS = {
        "chamonix": {
            "name": "Chamonix",
            "country": "France",
            "bounds": GeographicBounds(
                north=45.9500, south=45.9000,
                east=6.9000, west=6.8500
            ),
            "base_elevation": 1035,
            "top_elevation": 3842
        },
        "whistler": {
            "name": "Whistler",
            "country": "Canada", 
            "bounds": GeographicBounds(
                north=50.1200, south=50.1000,
                east=-122.9000, west=-122.9500
            ),
            "base_elevation": 652,
            "top_elevation": 2284
        },
        "st_anton": {
            "name": "St. Anton am Arlberg",
            "country": "Austria",
            "bounds": GeographicBounds(
                north=47.1400, south=47.1200,
                east=10.2700, west=10.2500
            ),
            "base_elevation": 1304,
            "top_elevation": 2811
        },
        "zermatt": {
            "name": "Zermatt",
            "country": "Switzerland",
            "bounds": GeographicBounds(
                north=45.9900, south=45.9700,
                east=7.7600, west=7.7400
            ),
            "base_elevation": 1620,
            "top_elevation": 3883
        },
        "copper_mountain": {
            "name": "Copper Mountain",
            "country": "United States",
            "bounds": GeographicBounds(
                north=39.5100, south=39.4900,
                east=-106.1400, west=-106.1600
            ),
            "base_elevation": 2926,
            "top_elevation": 3962
        }
    }
    
    def __init__(self, config: Optional[MockDataConfig] = None):
        """Initialize mock data generator with configuration."""
        self.config = config or MockDataConfig()
        self._random = random.Random()
        if self.config.seed is not None:
            self._random.seed(self.config.seed)
        
        self._cache_states: Dict[str, Any] = {}
        self._generated_data: Dict[str, Any] = {}
    
    def generate_terrain_data(self, ski_area_id: str) -> TerrainResponse:
        """Generate realistic terrain data for a ski area."""
        if ski_area_id not in self.SKI_AREAS:
            raise ValueError(f"Unknown ski area: {ski_area_id}")
        
        area_info = self.SKI_AREAS[ski_area_id]
        bounds = area_info["bounds"]
        
        # Generate elevation grid
        elevation_data = self._generate_elevation_data(bounds, area_info)
        
        # Generate slope and aspect data based on elevation
        slope_data = self._generate_slope_data(elevation_data)
        aspect_data = self._generate_aspect_data(elevation_data)
        
        # Generate surface classification
        surface_classification = self._generate_surface_classification(
            elevation_data, slope_data
        )
        
        # Generate safety zones and course markers if FIS data requested
        safety_zones = []
        course_markers = []
        if self.config.include_fis_data:
            safety_zones = self._generate_safety_zones(bounds)
            course_markers = self._generate_course_markers(bounds, elevation_data)
        
        hill_metrics = HillMetrics(
            elevation=elevation_data,
            slope=slope_data,
            aspect=aspect_data,
            surface_classification=surface_classification,
            safety_zones=safety_zones,
            course_markers=course_markers,
            metadata={
                "generated_at": datetime.now().isoformat(),
                "scenario": self.config.scenario.value,
                "ski_area": area_info["name"]
            }
        )
        
        # Apply scenario-specific modifications
        if self.config.scenario == TestScenario.EXTREME_WEATHER:
            hill_metrics = self._apply_extreme_weather_terrain(hill_metrics)
        elif self.config.scenario == TestScenario.EDGE_CASES:
            hill_metrics = self._apply_edge_case_terrain(hill_metrics)
        
        processing_time = self._random.uniform(50, 500) * self.config.performance_load_factor
        
        response = TerrainResponse(
            hill_metrics=hill_metrics,
            processing_time_ms=processing_time,
            data_sources=["mock_dem_data", "mock_surface_analysis"],
            cache_key=f"terrain_{ski_area_id}_{self.config.grid_size.value}",
            expires_at=time.time() + 3600  # 1 hour
        )
        
        self._generated_data[f"terrain_{ski_area_id}"] = response
        return response
    
    def generate_weather_data(self, ski_area_id: str) -> WeatherResponse:
        """Generate realistic weather data for a ski area."""
        if ski_area_id not in self.SKI_AREAS:
            raise ValueError(f"Unknown ski area: {ski_area_id}")
        
        area_info = self.SKI_AREAS[ski_area_id]
        
        # Generate current weather
        current_weather = self._generate_current_weather(area_info)
        
        # Generate forecast data
        forecast = []
        if self._random.random() > 0.3:  # 70% chance of including forecast
            forecast = self._generate_weather_forecast(area_info, days=7)
        
        # Generate historical data
        historical = []
        if self._random.random() > 0.5:  # 50% chance of including historical
            historical = self._generate_historical_weather(area_info, days=30)
        
        # Apply scenario-specific modifications
        if self.config.scenario == TestScenario.EXTREME_WEATHER:
            current_weather = self._apply_extreme_weather_conditions(current_weather)
            forecast = [self._apply_extreme_weather_forecast(f) for f in forecast]
        
        processing_time = self._random.uniform(20, 200) * self.config.performance_load_factor
        
        response = WeatherResponse(
            current=current_weather,
            forecast=forecast,
            historical=historical,
            location={
                "name": area_info["name"],
                "country": area_info["country"],
                "latitude": (area_info["bounds"].north + area_info["bounds"].south) / 2,
                "longitude": (area_info["bounds"].east + area_info["bounds"].west) / 2,
                "elevation": area_info["base_elevation"]
            },
            data_source="mock_weather_service",
            cache_expires_at=datetime.now() + timedelta(minutes=30),
            processing_time_ms=processing_time
        )
        
        self._generated_data[f"weather_{ski_area_id}"] = response
        return response
    
    def generate_equipment_data(self, ski_area_id: str) -> EquipmentResponse:
        """Generate realistic equipment data for a ski area."""
        if ski_area_id not in self.SKI_AREAS:
            raise ValueError(f"Unknown ski area: {ski_area_id}")
        
        area_info = self.SKI_AREAS[ski_area_id]
        bounds = area_info["bounds"]
        
        # Generate lifts
        lifts = self._generate_lifts(bounds, area_info)
        
        # Generate trails
        trails = self._generate_trails(bounds, area_info, lifts)
        
        # Generate facilities
        facilities = self._generate_facilities(bounds, area_info)
        
        # Generate safety equipment
        safety_equipment = self._generate_safety_equipment(bounds, trails)
        
        # Apply scenario-specific modifications
        if self.config.scenario == TestScenario.EQUIPMENT_FAILURES:
            lifts = self._apply_equipment_failures_lifts(lifts)
            trails = self._apply_equipment_failures_trails(trails)
        
        # Calculate statistics
        operational_lifts = sum(1 for lift in lifts if lift.status == LiftStatus.OPERATIONAL)
        open_trails = sum(1 for trail in trails if trail.status == TrailStatus.OPEN)
        
        processing_time = self._random.uniform(30, 300) * self.config.performance_load_factor
        
        response = EquipmentResponse(
            lifts=lifts,
            trails=trails,
            facilities=facilities,
            safety_equipment=safety_equipment,
            bounds={
                "north": bounds.north,
                "south": bounds.south,
                "east": bounds.east,
                "west": bounds.west
            },
            total_lifts=len(lifts),
            operational_lifts=operational_lifts,
            total_trails=len(trails),
            open_trails=open_trails,
            last_updated=datetime.now(),
            processing_time_ms=processing_time
        )
        
        self._generated_data[f"equipment_{ski_area_id}"] = response
        return response
    
    def generate_ski_conditions(self, ski_area_id: str) -> SkiConditionsResponse:
        """Generate ski-specific conditions data."""
        if ski_area_id not in self.SKI_AREAS:
            raise ValueError(f"Unknown ski area: {ski_area_id}")
        
        area_info = self.SKI_AREAS[ski_area_id]
        weather_data = self._generate_current_weather(area_info)
        
        # Generate ski conditions based on weather
        conditions = self._generate_ski_conditions_from_weather(weather_data)
        
        processing_time = self._random.uniform(10, 100) * self.config.performance_load_factor
        
        response = SkiConditionsResponse(
            conditions=conditions,
            weather=weather_data,
            location={
                "name": area_info["name"],
                "country": area_info["country"],
                "latitude": (area_info["bounds"].north + area_info["bounds"].south) / 2,
                "longitude": (area_info["bounds"].east + area_info["bounds"].west) / 2,
                "elevation": area_info["base_elevation"]
            },
            timestamp=datetime.now(),
            processing_time_ms=processing_time
        )
        
        return response
    
    def manipulate_cache_state(self, cache_key: str, state: str) -> Dict[str, Any]:
        """Manipulate cache state for testing scenarios."""
        cache_manipulation = {
            "key": cache_key,
            "original_state": self._cache_states.get(cache_key, "clean"),
            "new_state": state,
            "timestamp": datetime.now().isoformat()
        }
        
        if state == "corrupted":
            cache_manipulation["corruption_type"] = self._random.choice([
                "partial_data", "invalid_json", "missing_fields", "wrong_schema"
            ])
        elif state == "expired":
            cache_manipulation["expiry_time"] = (datetime.now() - timedelta(hours=1)).isoformat()
        elif state == "missing":
            cache_manipulation["deletion_reason"] = "cache_eviction"
        
        self._cache_states[cache_key] = state
        return cache_manipulation
    
    def generate_performance_test_data(self, data_size: str = "large") -> Dict[str, Any]:
        """Generate data for performance testing scenarios."""
        size_multipliers = {
            "small": 0.1,
            "medium": 1.0,
            "large": 5.0,
            "xlarge": 20.0
        }
        
        multiplier = size_multipliers.get(data_size, 1.0)
        
        # Generate large terrain grid
        grid_size = int(64 * math.sqrt(multiplier))
        large_grid = [
            [self._random.uniform(1000, 4000) for _ in range(grid_size)]
            for _ in range(grid_size)
        ]
        
        # Generate many data points
        num_points = int(1000 * multiplier)
        data_points = [
            {
                "id": f"point_{i}",
                "value": self._random.uniform(0, 100),
                "timestamp": (datetime.now() - timedelta(seconds=i)).isoformat()
            }
            for i in range(num_points)
        ]
        
        return {
            "grid_data": large_grid,
            "data_points": data_points,
            "metadata": {
                "size": data_size,
                "multiplier": multiplier,
                "grid_dimensions": f"{grid_size}x{grid_size}",
                "point_count": num_points,
                "estimated_size_mb": len(json.dumps(large_grid)) / (1024 * 1024)
            }
        }
    
    def get_generated_data(self, data_type: str, ski_area_id: str) -> Optional[Any]:
        """Retrieve previously generated data."""
        key = f"{data_type}_{ski_area_id}"
        return self._generated_data.get(key)
    
    def clear_generated_data(self) -> None:
        """Clear all generated data."""
        self._generated_data.clear()
        self._cache_states.clear()
    
    def get_cache_states(self) -> Dict[str, Any]:
        """Get current cache state manipulations."""
        return self._cache_states.copy() 
   
    # Private helper methods for terrain data generation
    
    def _generate_elevation_data(self, bounds: GeographicBounds, area_info: Dict[str, Any]) -> ElevationData:
        """Generate realistic elevation data."""
        grid_sizes = {
            GridSize.SMALL: 32,
            GridSize.MEDIUM: 64,
            GridSize.LARGE: 96,
            GridSize.EXTRA_LARGE: 128
        }
        
        size = grid_sizes[self.config.grid_size]
        base_elevation = area_info["base_elevation"]
        top_elevation = area_info["top_elevation"]
        
        # Generate realistic elevation profile
        grid = []
        for i in range(size):
            row = []
            for j in range(size):
                # Create slope from top to bottom with some randomness
                height_factor = 1.0 - (i / size)  # Higher at top (i=0)
                base_height = base_elevation + (top_elevation - base_elevation) * height_factor
                
                # Add terrain variation
                noise = self._random.uniform(-200, 200) * self.config.weather_variability
                elevation = max(base_elevation, base_height + noise)
                
                row.append(elevation)
            grid.append(row)
        
        # Calculate resolution (meters per cell)
        lat_diff = bounds.north - bounds.south
        lon_diff = bounds.east - bounds.west
        avg_diff = (lat_diff + lon_diff) / 2
        resolution = (avg_diff * 111000) / size  # Rough conversion to meters
        
        return ElevationData(
            grid=grid,
            resolution=resolution,
            bounds=bounds,
            no_data_value=-9999
        )
    
    def _generate_slope_data(self, elevation_data: ElevationData) -> SlopeData:
        """Generate slope data from elevation data."""
        grid = elevation_data.grid
        size = len(grid)
        slope_grid = []
        
        for i in range(size):
            row = []
            for j in range(size):
                # Calculate slope using neighboring cells
                if i > 0 and i < size - 1 and j > 0 and j < size - 1:
                    # Use simple gradient calculation
                    dx = grid[i][j+1] - grid[i][j-1]
                    dy = grid[i+1][j] - grid[i-1][j]
                    slope = math.degrees(math.atan(math.sqrt(dx*dx + dy*dy) / (2 * elevation_data.resolution)))
                else:
                    # Edge cells get average slope
                    slope = self._random.uniform(5, 25)
                
                # Clamp slope to realistic values
                slope = max(0, min(60, slope))
                row.append(slope)
            slope_grid.append(row)
        
        return SlopeData(
            grid=slope_grid,
            resolution=elevation_data.resolution,
            bounds=elevation_data.bounds
        )
    
    def _generate_aspect_data(self, elevation_data: ElevationData) -> AspectData:
        """Generate aspect (slope direction) data from elevation data."""
        grid = elevation_data.grid
        size = len(grid)
        aspect_grid = []
        
        for i in range(size):
            row = []
            for j in range(size):
                # Calculate aspect using neighboring cells
                if i > 0 and i < size - 1 and j > 0 and j < size - 1:
                    dx = grid[i][j+1] - grid[i][j-1]
                    dy = grid[i+1][j] - grid[i-1][j]
                    aspect = math.degrees(math.atan2(dy, dx))
                    # Convert to 0-360 degrees
                    if aspect < 0:
                        aspect += 360
                else:
                    # Edge cells get random aspect
                    aspect = self._random.uniform(0, 360)
                
                row.append(aspect)
            aspect_grid.append(row)
        
        return AspectData(
            grid=aspect_grid,
            resolution=elevation_data.resolution,
            bounds=elevation_data.bounds
        )
    
    def _generate_surface_classification(self, elevation_data: ElevationData, slope_data: SlopeData) -> SurfaceClassification:
        """Generate surface type classification based on elevation and slope."""
        size = len(elevation_data.grid)
        surface_grid = []
        confidence_grid = []
        
        for i in range(size):
            surface_row = []
            confidence_row = []
            for j in range(size):
                elevation = elevation_data.grid[i][j]
                slope = slope_data.grid[i][j]
                
                # Determine surface type based on elevation and slope
                if slope > 45:
                    surface_type = SurfaceType.ROCKS
                    confidence = 0.9
                elif slope > 30:
                    surface_type = self._random.choice([SurfaceType.MOGULS, SurfaceType.ICE])
                    confidence = 0.7
                elif slope > 15:
                    surface_type = self._random.choice([SurfaceType.PACKED, SurfaceType.POWDER])
                    confidence = 0.8
                else:
                    surface_type = SurfaceType.POWDER
                    confidence = 0.6
                
                # Add some randomness based on scenario
                if self.config.scenario == TestScenario.EXTREME_WEATHER:
                    if self._random.random() < 0.3:
                        surface_type = SurfaceType.ICE
                        confidence = 0.9
                
                surface_row.append(surface_type)
                confidence_row.append(confidence)
            
            surface_grid.append(surface_row)
            confidence_grid.append(confidence_row)
        
        return SurfaceClassification(
            grid=surface_grid,
            resolution=elevation_data.resolution,
            bounds=elevation_data.bounds,
            confidence=confidence_grid
        )
    
    def _generate_safety_zones(self, bounds: GeographicBounds) -> List[SafetyZone]:
        """Generate FIS safety zones."""
        zones = []
        num_zones = self._random.randint(3, 8)
        
        for i in range(num_zones):
            zone_id = f"safety_zone_{i+1}"
            zone_type = self._random.choice(["barrier", "net", "padding"])
            
            # Generate zone boundary (simple rectangle)
            lat_center = self._random.uniform(bounds.south, bounds.north)
            lon_center = self._random.uniform(bounds.west, bounds.east)
            size = self._random.uniform(0.001, 0.005)  # Small area
            
            coordinates = [
                [lat_center - size, lon_center - size],
                [lat_center + size, lon_center - size],
                [lat_center + size, lon_center + size],
                [lat_center - size, lon_center + size],
                [lat_center - size, lon_center - size]  # Close the polygon
            ]
            
            zones.append(SafetyZone(
                id=zone_id,
                type=zone_type,
                coordinates=coordinates,
                height=self._random.uniform(1.0, 3.0),
                material=self._random.choice(["foam", "net", "barrier"])
            ))
        
        return zones
    
    def _generate_course_markers(self, bounds: GeographicBounds, elevation_data: ElevationData) -> List[CourseMarker]:
        """Generate FIS course markers."""
        markers = []
        num_markers = self._random.randint(10, 20)
        
        for i in range(num_markers):
            marker_id = f"marker_{i+1}"
            marker_type = self._random.choice(["gate", "timing", "start", "finish"])
            
            lat = self._random.uniform(bounds.south, bounds.north)
            lon = self._random.uniform(bounds.west, bounds.east)
            
            # Get elevation from grid (approximate)
            grid_size = len(elevation_data.grid)
            lat_idx = int((lat - bounds.south) / (bounds.north - bounds.south) * (grid_size - 1))
            lon_idx = int((lon - bounds.west) / (bounds.east - bounds.west) * (grid_size - 1))
            elevation = elevation_data.grid[lat_idx][lon_idx]
            
            markers.append(CourseMarker(
                id=marker_id,
                type=marker_type,
                latitude=lat,
                longitude=lon,
                elevation=elevation,
                orientation=self._random.uniform(0, 360)
            ))
        
        return markers
    
    # Private helper methods for weather data generation
    
    def _generate_current_weather(self, area_info: Dict[str, Any]) -> WeatherData:
        """Generate current weather data."""
        # Base temperature varies by elevation and season
        base_temp = self._random.uniform(-15, 10)  # Winter skiing temperatures
        elevation_factor = (area_info["base_elevation"] - 1000) / 1000 * -6.5  # Lapse rate
        temperature = base_temp + elevation_factor
        
        # Generate wind data
        wind = WindData(
            speed_kmh=self._random.uniform(0, 40),
            direction_degrees=self._random.uniform(0, 360),
            gust_speed_kmh=self._random.uniform(0, 60) if self._random.random() > 0.5 else None
        )
        
        # Generate snow data
        snow_depth = self._random.uniform(20, 200)  # cm
        snow_condition = self._random.choice(list(SnowCondition))
        snow = SnowData(
            depth_cm=snow_depth,
            condition=snow_condition,
            temperature_c=temperature - self._random.uniform(0, 5),
            density_kg_m3=self._random.uniform(200, 600),
            last_snowfall_hours=self._random.randint(0, 72) if self._random.random() > 0.3 else None
        )
        
        # Generate visibility
        visibility = VisibilityData(
            distance_km=self._random.uniform(0.1, 50),
            condition=self._random.choice(["clear", "light_fog", "heavy_fog", "snow"])
        )
        
        # Select weather condition
        weather_condition = self._random.choice(list(WeatherCondition))
        
        return WeatherData(
            timestamp=datetime.now(),
            temperature_c=temperature,
            feels_like_c=temperature - wind.speed_kmh * 0.1,  # Wind chill approximation
            humidity_percent=self._random.uniform(30, 90),
            pressure_hpa=self._random.uniform(950, 1050),
            condition=weather_condition,
            wind=wind,
            snow=snow,
            visibility=visibility,
            uv_index=self._random.uniform(0, 8) if self._random.random() > 0.5 else None,
            precipitation_mm=self._random.uniform(0, 20) if self._random.random() > 0.6 else 0
        )
    
    def _generate_weather_forecast(self, area_info: Dict[str, Any], days: int) -> List[WeatherForecast]:
        """Generate weather forecast data."""
        forecast = []
        base_date = datetime.now()
        
        for day in range(1, days + 1):
            forecast_date = base_date + timedelta(days=day)
            
            # Temperature trend with some randomness
            base_temp = self._random.uniform(-20, 5)
            temp_variation = self._random.uniform(5, 15)
            
            forecast.append(WeatherForecast(
                timestamp=forecast_date,
                temperature_high_c=base_temp + temp_variation,
                temperature_low_c=base_temp - temp_variation,
                condition=self._random.choice(list(WeatherCondition)),
                precipitation_probability=self._random.uniform(0, 1),
                precipitation_mm=self._random.uniform(0, 30) if self._random.random() > 0.5 else 0,
                wind_speed_kmh=self._random.uniform(0, 50),
                snow_depth_cm=self._random.uniform(10, 300) if self._random.random() > 0.3 else None
            ))
        
        return forecast
    
    def _generate_historical_weather(self, area_info: Dict[str, Any], days: int) -> List[HistoricalWeatherData]:
        """Generate historical weather data."""
        historical = []
        base_date = datetime.now()
        
        for day in range(1, days + 1):
            hist_date = base_date - timedelta(days=day)
            
            temp_avg = self._random.uniform(-15, 5)
            temp_range = self._random.uniform(5, 20)
            
            historical.append(HistoricalWeatherData(
                date=hist_date,
                temperature_high_c=temp_avg + temp_range / 2,
                temperature_low_c=temp_avg - temp_range / 2,
                temperature_avg_c=temp_avg,
                precipitation_mm=self._random.uniform(0, 25) if self._random.random() > 0.6 else 0,
                snow_depth_cm=self._random.uniform(0, 250) if self._random.random() > 0.4 else None,
                wind_speed_avg_kmh=self._random.uniform(0, 30),
                condition=self._random.choice(list(WeatherCondition))
            ))
        
        return historical
    
    def _generate_ski_conditions_from_weather(self, weather: WeatherData) -> SkiConditions:
        """Generate ski conditions based on weather data."""
        # Calculate ratings based on weather conditions
        temp_rating = self._rate_temperature(weather.temperature_c)
        wind_rating = self._rate_wind(weather.wind.speed_kmh)
        visibility_rating = self._rate_visibility(weather.visibility.distance_km)
        
        # Overall rating is average of individual ratings
        overall_rating = (temp_rating + wind_rating + visibility_rating) / 3
        
        # Generate gear recommendations
        gear = ["helmet", "goggles"]
        if weather.temperature_c < -10:
            gear.extend(["thermal_underwear", "face_mask"])
        if weather.wind.speed_kmh > 20:
            gear.append("windproof_jacket")
        if weather.visibility.distance_km < 1:
            gear.append("high_visibility_clothing")
        
        # Generate safety warnings
        warnings = []
        if weather.wind.speed_kmh > 30:
            warnings.append("High wind conditions - exercise caution on exposed slopes")
        if weather.visibility.distance_km < 0.5:
            warnings.append("Poor visibility - stay on marked trails")
        if weather.temperature_c < -20:
            warnings.append("Extreme cold - risk of frostbite")
        
        return SkiConditions(
            overall_rating=overall_rating,
            snow_quality=weather.snow.condition if weather.snow else SnowCondition.PACKED_POWDER,
            visibility_rating=visibility_rating,
            wind_rating=wind_rating,
            temperature_rating=temp_rating,
            recommended_gear=gear,
            safety_warnings=warnings,
            best_time_of_day=self._determine_best_time(weather)
        )
    
    def _rate_temperature(self, temp: float) -> float:
        """Rate temperature for skiing (0-10 scale)."""
        if -10 <= temp <= -2:
            return 10.0  # Perfect skiing temperature
        elif -15 <= temp < -10 or -2 < temp <= 2:
            return 8.0   # Good
        elif -20 <= temp < -15 or 2 < temp <= 5:
            return 6.0   # Acceptable
        elif temp < -20 or temp > 5:
            return 3.0   # Poor
        else:
            return 5.0   # Average
    
    def _rate_wind(self, wind_speed: float) -> float:
        """Rate wind conditions for skiing (0-10 scale)."""
        if wind_speed <= 10:
            return 10.0  # Calm
        elif wind_speed <= 20:
            return 8.0   # Light breeze
        elif wind_speed <= 30:
            return 6.0   # Moderate wind
        elif wind_speed <= 40:
            return 4.0   # Strong wind
        else:
            return 2.0   # Very strong wind
    
    def _rate_visibility(self, visibility_km: float) -> float:
        """Rate visibility for skiing (0-10 scale)."""
        if visibility_km >= 10:
            return 10.0  # Excellent
        elif visibility_km >= 5:
            return 8.0   # Good
        elif visibility_km >= 2:
            return 6.0   # Fair
        elif visibility_km >= 0.5:
            return 4.0   # Poor
        else:
            return 2.0   # Very poor
    
    def _determine_best_time(self, weather: WeatherData) -> str:
        """Determine best time of day for skiing based on conditions."""
        if weather.condition in [WeatherCondition.CLEAR, WeatherCondition.PARTLY_CLOUDY]:
            return "morning"  # Best visibility and snow conditions
        elif weather.wind.speed_kmh > 25:
            return "midday"   # Wind often calms down midday
        elif weather.condition in [WeatherCondition.LIGHT_SNOW, WeatherCondition.MODERATE_SNOW]:
            return "afternoon"  # Fresh snow settles
        else:
            return "morning"    # Default    

    # Private helper methods for equipment data generation
    
    def _generate_lifts(self, bounds: GeographicBounds, area_info: Dict[str, Any]) -> List[LiftInfo]:
        """Generate realistic lift data."""
        lifts = []
        num_lifts = self._random.randint(8, 15)
        
        for i in range(num_lifts):
            lift_id = f"lift_{i+1}"
            lift_name = f"{area_info['name']} Lift {i+1}"
            lift_type = self._random.choice(list(LiftType))
            
            # Generate base and top positions
            base_lat = self._random.uniform(bounds.south, bounds.north)
            base_lon = self._random.uniform(bounds.west, bounds.east)
            base_elevation = area_info["base_elevation"] + self._random.uniform(0, 500)
            
            # Top is higher and slightly offset
            top_lat = base_lat + self._random.uniform(-0.01, 0.01)
            top_lon = base_lon + self._random.uniform(-0.01, 0.01)
            top_elevation = base_elevation + self._random.uniform(200, 1000)
            
            # Calculate lift characteristics
            vertical_rise = top_elevation - base_elevation
            length = math.sqrt((top_lat - base_lat)**2 + (top_lon - base_lon)**2) * 111000  # Rough conversion to meters
            
            # Capacity varies by lift type
            capacity_map = {
                LiftType.CHAIRLIFT: self._random.randint(1200, 2400),
                LiftType.GONDOLA: self._random.randint(2000, 4000),
                LiftType.CABLE_CAR: self._random.randint(800, 1600),
                LiftType.T_BAR: self._random.randint(600, 1200),
                LiftType.PLATTER_LIFT: self._random.randint(400, 800),
                LiftType.MAGIC_CARPET: self._random.randint(800, 1200),
                LiftType.FUNICULAR: self._random.randint(400, 800)
            }
            
            capacity = capacity_map[lift_type]
            ride_time = length / 300  # Rough estimate: 5 m/s average speed
            
            # Determine status
            status = LiftStatus.OPERATIONAL
            if self.config.equipment_failure_rate > 0:
                if self._random.random() < self.config.equipment_failure_rate:
                    status = self._random.choice([
                        LiftStatus.CLOSED, LiftStatus.MAINTENANCE, 
                        LiftStatus.WEATHER_HOLD, LiftStatus.MECHANICAL_ISSUE
                    ])
            
            lifts.append(LiftInfo(
                id=lift_id,
                name=lift_name,
                type=lift_type,
                status=status,
                capacity_per_hour=capacity,
                vertical_rise_m=vertical_rise,
                length_m=length,
                ride_time_minutes=ride_time,
                base_latitude=base_lat,
                base_longitude=base_lon,
                base_elevation_m=base_elevation,
                top_latitude=top_lat,
                top_longitude=top_lon,
                top_elevation_m=top_elevation,
                operating_hours={
                    "monday": "8:30-16:00",
                    "tuesday": "8:30-16:00",
                    "wednesday": "8:30-16:00",
                    "thursday": "8:30-16:00",
                    "friday": "8:30-16:00",
                    "saturday": "8:00-16:30",
                    "sunday": "8:00-16:30"
                },
                last_inspection=datetime.now() - timedelta(days=self._random.randint(1, 30)),
                next_maintenance=datetime.now() + timedelta(days=self._random.randint(30, 90)),
                heated_seats=self._random.random() > 0.6,
                weather_shield=self._random.random() > 0.7,
                beginner_friendly=lift_type in [LiftType.MAGIC_CARPET, LiftType.CHAIRLIFT]
            ))
        
        return lifts
    
    def _generate_trails(self, bounds: GeographicBounds, area_info: Dict[str, Any], lifts: List[LiftInfo]) -> List[TrailInfo]:
        """Generate realistic trail data."""
        trails = []
        num_trails = self._random.randint(15, 30)
        
        for i in range(num_trails):
            trail_id = f"trail_{i+1}"
            trail_name = f"{area_info['name']} Trail {i+1}"
            difficulty = self._random.choice(list(TrailDifficulty))
            
            # Generate trail path
            start_lat = self._random.uniform(bounds.south, bounds.north)
            start_lon = self._random.uniform(bounds.west, bounds.east)
            start_elevation = area_info["base_elevation"] + self._random.uniform(200, 1200)
            
            end_lat = start_lat + self._random.uniform(-0.02, 0.02)
            end_lon = start_lon + self._random.uniform(-0.02, 0.02)
            end_elevation = start_elevation - self._random.uniform(100, 800)  # Trails go downhill
            
            # Calculate trail characteristics
            vertical_drop = start_elevation - end_elevation
            length = math.sqrt((start_lat - end_lat)**2 + (start_lon - end_lon)**2) * 111000
            
            # Grade varies by difficulty
            average_grade = (vertical_drop / length) * 100 if length > 0 else 10
            max_grade = average_grade * self._random.uniform(1.2, 2.0)
            
            # Width varies by difficulty
            width_map = {
                TrailDifficulty.BEGINNER: self._random.uniform(30, 50),
                TrailDifficulty.INTERMEDIATE: self._random.uniform(20, 40),
                TrailDifficulty.ADVANCED: self._random.uniform(15, 30),
                TrailDifficulty.EXPERT: self._random.uniform(10, 25),
                TrailDifficulty.TERRAIN_PARK: self._random.uniform(25, 40),
                TrailDifficulty.CROSS_COUNTRY: self._random.uniform(3, 8)
            }
            
            width = width_map[difficulty]
            
            # Determine status
            status = TrailStatus.OPEN
            if self.config.equipment_failure_rate > 0:
                if self._random.random() < self.config.equipment_failure_rate * 0.5:  # Trails fail less than lifts
                    status = self._random.choice([TrailStatus.CLOSED, TrailStatus.UNGROOMED])
            
            # Connect to random lifts
            access_lifts = self._random.sample([lift.id for lift in lifts], k=self._random.randint(1, 3))
            
            trails.append(TrailInfo(
                id=trail_id,
                name=trail_name,
                difficulty=difficulty,
                status=status,
                length_m=length,
                vertical_drop_m=vertical_drop,
                average_grade_percent=average_grade,
                max_grade_percent=max_grade,
                start_latitude=start_lat,
                start_longitude=start_lon,
                start_elevation_m=start_elevation,
                end_latitude=end_lat,
                end_longitude=end_lon,
                end_elevation_m=end_elevation,
                width_m=width,
                groomed=self._random.random() > 0.2,
                snowmaking=self._random.random() > 0.4,
                night_skiing=self._random.random() > 0.8,
                last_groomed=datetime.now() - timedelta(hours=self._random.randint(1, 48)),
                snow_depth_cm=self._random.uniform(20, 150),
                surface_condition=self._random.choice(["powder", "packed", "icy", "moguls"]),
                access_lifts=access_lifts,
                connected_trails=[]  # Would be populated in a real system
            ))
        
        return trails
    
    def _generate_facilities(self, bounds: GeographicBounds, area_info: Dict[str, Any]) -> List[FacilityInfo]:
        """Generate realistic facility data."""
        facilities = []
        facility_types = [
            (FacilityType.LODGE, 2),
            (FacilityType.RESTAURANT, 3),
            (FacilityType.CAFETERIA, 2),
            (FacilityType.BAR, 2),
            (FacilityType.SHOP, 3),
            (FacilityType.RENTAL, 2),
            (FacilityType.SKI_SCHOOL, 1),
            (FacilityType.FIRST_AID, 2),
            (FacilityType.PARKING, 4),
            (FacilityType.RESTROOM, 6),
            (FacilityType.CHILDCARE, 1)
        ]
        
        facility_id = 1
        for facility_type, count in facility_types:
            for i in range(count):
                fac_id = f"facility_{facility_id}"
                fac_name = f"{area_info['name']} {facility_type.value.title()} {i+1}"
                
                lat = self._random.uniform(bounds.south, bounds.north)
                lon = self._random.uniform(bounds.west, bounds.east)
                elevation = area_info["base_elevation"] + self._random.uniform(0, 300)
                
                # Capacity varies by type
                capacity_map = {
                    FacilityType.LODGE: self._random.randint(200, 500),
                    FacilityType.RESTAURANT: self._random.randint(50, 150),
                    FacilityType.CAFETERIA: self._random.randint(100, 300),
                    FacilityType.BAR: self._random.randint(30, 80),
                    FacilityType.SHOP: self._random.randint(20, 50),
                    FacilityType.RENTAL: self._random.randint(50, 100),
                    FacilityType.SKI_SCHOOL: self._random.randint(100, 200),
                    FacilityType.FIRST_AID: self._random.randint(10, 20),
                    FacilityType.PARKING: self._random.randint(100, 1000),
                    FacilityType.RESTROOM: self._random.randint(10, 30),
                    FacilityType.CHILDCARE: self._random.randint(20, 50)
                }
                
                capacity = capacity_map.get(facility_type, 50)
                
                # Generate amenities based on facility type
                amenities = []
                if facility_type == FacilityType.LODGE:
                    amenities = ["wifi", "heating", "lockers", "seating"]
                elif facility_type == FacilityType.RESTAURANT:
                    amenities = ["hot_food", "beverages", "seating", "heating"]
                elif facility_type == FacilityType.RENTAL:
                    amenities = ["ski_rental", "boot_rental", "helmet_rental", "fitting_service"]
                
                facilities.append(FacilityInfo(
                    id=fac_id,
                    name=fac_name,
                    type=facility_type,
                    latitude=lat,
                    longitude=lon,
                    elevation_m=elevation,
                    is_open=self._random.random() > 0.1,  # 90% open
                    operating_hours={
                        "monday": "8:00-17:00",
                        "tuesday": "8:00-17:00",
                        "wednesday": "8:00-17:00",
                        "thursday": "8:00-17:00",
                        "friday": "8:00-18:00",
                        "saturday": "7:30-18:00",
                        "sunday": "7:30-18:00"
                    },
                    capacity=capacity,
                    phone=f"+{self._random.randint(1, 99)}-{self._random.randint(100, 999)}-{self._random.randint(1000, 9999)}",
                    website=f"https://{area_info['name'].lower().replace(' ', '')}.com/{facility_type.value}",
                    description=f"{facility_type.value.title()} facility at {area_info['name']}",
                    amenities=amenities,
                    wheelchair_accessible=self._random.random() > 0.3,
                    parking_available=facility_type in [FacilityType.LODGE, FacilityType.RESTAURANT, FacilityType.PARKING]
                ))
                
                facility_id += 1
        
        return facilities
    
    def _generate_safety_equipment(self, bounds: GeographicBounds, trails: List[TrailInfo]) -> List[SafetyEquipment]:
        """Generate safety equipment data."""
        equipment = []
        equipment_types = [
            (SafetyEquipmentType.EMERGENCY_PHONE, 8),
            (SafetyEquipmentType.FIRST_AID_STATION, 4),
            (SafetyEquipmentType.PATROL_HUT, 3),
            (SafetyEquipmentType.BOUNDARY_MARKER, 20),
            (SafetyEquipmentType.WARNING_SIGN, 15),
            (SafetyEquipmentType.CLOSURE_ROPE, 10),
            (SafetyEquipmentType.SAFETY_NET, 5),
            (SafetyEquipmentType.PADDING, 8),
            (SafetyEquipmentType.AVALANCHE_BEACON, 6)
        ]
        
        equipment_id = 1
        for eq_type, count in equipment_types:
            for i in range(count):
                eq_id = f"safety_{equipment_id}"
                
                lat = self._random.uniform(bounds.south, bounds.north)
                lon = self._random.uniform(bounds.west, bounds.east)
                elevation = self._random.uniform(1000, 3000)
                
                # Some equipment is associated with trails
                associated_trail = None
                if self._random.random() > 0.5 and trails:
                    associated_trail = self._random.choice(trails).id
                
                equipment.append(SafetyEquipment(
                    id=eq_id,
                    type=eq_type,
                    latitude=lat,
                    longitude=lon,
                    elevation_m=elevation,
                    is_operational=self._random.random() > 0.05,  # 95% operational
                    last_inspection=datetime.now() - timedelta(days=self._random.randint(1, 60)),
                    next_maintenance=datetime.now() + timedelta(days=self._random.randint(30, 180)),
                    model=f"Model-{self._random.randint(100, 999)}",
                    installation_date=datetime.now() - timedelta(days=self._random.randint(365, 3650)),
                    coverage_radius_m=self._random.uniform(50, 500) if eq_type in [
                        SafetyEquipmentType.EMERGENCY_PHONE, 
                        SafetyEquipmentType.FIRST_AID_STATION
                    ] else None,
                    associated_trail=associated_trail
                ))
                
                equipment_id += 1
        
        return equipment
    
    # Scenario-specific modification methods
    
    def _apply_extreme_weather_terrain(self, hill_metrics: HillMetrics) -> HillMetrics:
        """Apply extreme weather modifications to terrain data."""
        # Increase ice surface classification
        size = len(hill_metrics.surface_classification.grid)
        for i in range(size):
            for j in range(size):
                if self._random.random() < 0.4:  # 40% chance to become icy
                    hill_metrics.surface_classification.grid[i][j] = SurfaceType.ICE
                    hill_metrics.surface_classification.confidence[i][j] = 0.95
        
        return hill_metrics
    
    def _apply_edge_case_terrain(self, hill_metrics: HillMetrics) -> HillMetrics:
        """Apply edge case modifications to terrain data."""
        # Add some extreme slopes and unusual surface types
        size = len(hill_metrics.slope.grid)
        for i in range(size):
            for j in range(size):
                if self._random.random() < 0.1:  # 10% chance for edge cases
                    hill_metrics.slope.grid[i][j] = self._random.uniform(50, 70)  # Very steep
                    hill_metrics.surface_classification.grid[i][j] = SurfaceType.ROCKS
        
        return hill_metrics
    
    def _apply_extreme_weather_conditions(self, weather: WeatherData) -> WeatherData:
        """Apply extreme weather conditions."""
        weather.temperature_c = self._random.uniform(-30, -15)
        weather.wind.speed_kmh = self._random.uniform(40, 80)
        weather.condition = self._random.choice([
            WeatherCondition.HEAVY_SNOW, WeatherCondition.BLIZZARD, WeatherCondition.FOG
        ])
        weather.visibility.distance_km = self._random.uniform(0.1, 1.0)
        weather.precipitation_mm = self._random.uniform(20, 50)
        
        return weather
    
    def _apply_extreme_weather_forecast(self, forecast: WeatherForecast) -> WeatherForecast:
        """Apply extreme weather to forecast."""
        forecast.temperature_high_c = self._random.uniform(-25, -10)
        forecast.temperature_low_c = self._random.uniform(-40, -20)
        forecast.condition = self._random.choice([
            WeatherCondition.HEAVY_SNOW, WeatherCondition.BLIZZARD
        ])
        forecast.precipitation_probability = self._random.uniform(0.8, 1.0)
        forecast.wind_speed_kmh = self._random.uniform(30, 70)
        
        return forecast
    
    def _apply_equipment_failures_lifts(self, lifts: List[LiftInfo]) -> List[LiftInfo]:
        """Apply equipment failures to lifts."""
        for lift in lifts:
            if self._random.random() < self.config.equipment_failure_rate:
                lift.status = self._random.choice([
                    LiftStatus.CLOSED, LiftStatus.MAINTENANCE, 
                    LiftStatus.MECHANICAL_ISSUE, LiftStatus.WEATHER_HOLD
                ])
        
        return lifts
    
    def _apply_equipment_failures_trails(self, trails: List[TrailInfo]) -> List[TrailInfo]:
        """Apply equipment failures to trails."""
        for trail in trails:
            if self._random.random() < self.config.equipment_failure_rate * 0.3:  # Lower failure rate for trails
                trail.status = self._random.choice([TrailStatus.CLOSED, TrailStatus.UNGROOMED])
        
        return trails