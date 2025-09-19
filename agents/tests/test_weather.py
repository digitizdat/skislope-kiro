"""Tests for Weather Agent."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch

from agents.weather.models import SnowCondition, WeatherCondition
from agents.weather.weather_service import WeatherService


class TestWeatherService:
    """Test cases for weather service."""
    
    @pytest.fixture
    def weather_service(self):
        """Create a weather service instance."""
        return WeatherService()
    
    @pytest.mark.asyncio
    async def test_get_current_weather(self, weather_service):
        """Test getting current weather data."""
        result = await weather_service.get_current_weather(46.0, 7.0)
        
        assert result is not None
        assert isinstance(result.timestamp, datetime)
        assert -50 <= result.temperature_c <= 50  # Reasonable temperature range
        assert 0 <= result.humidity_percent <= 100
        assert result.pressure_hpa > 0
        assert result.wind is not None
        assert result.visibility is not None
    
    @pytest.mark.asyncio
    async def test_get_weather_forecast(self, weather_service):
        """Test getting weather forecast."""
        result = await weather_service.get_weather_forecast(46.0, 7.0, days=5)
        
        assert result is not None
        assert len(result) == 5
        
        for forecast in result:
            assert isinstance(forecast.timestamp, datetime)
            assert forecast.temperature_high_c >= forecast.temperature_low_c
            assert 0 <= forecast.precipitation_probability <= 1
    
    @pytest.mark.asyncio
    async def test_get_historical_weather(self, weather_service):
        """Test getting historical weather data."""
        result = await weather_service.get_historical_weather(46.0, 7.0, days=10)
        
        assert result is not None
        assert len(result) == 10
        
        for historical in result:
            assert isinstance(historical.date, datetime)
            assert historical.temperature_high_c >= historical.temperature_low_c
            assert historical.precipitation_mm >= 0
    
    @pytest.mark.asyncio
    async def test_get_ski_conditions(self, weather_service):
        """Test getting ski conditions analysis."""
        result = await weather_service.get_ski_conditions(46.0, 7.0, elevation_m=2000)
        
        assert result is not None
        assert 0 <= result.overall_rating <= 10
        assert 0 <= result.visibility_rating <= 10
        assert 0 <= result.wind_rating <= 10
        assert 0 <= result.temperature_rating <= 10
        assert isinstance(result.snow_quality, SnowCondition)
        assert isinstance(result.recommended_gear, list)
        assert isinstance(result.safety_warnings, list)
        assert result.best_time_of_day is not None
    
    @pytest.mark.asyncio
    async def test_cache_functionality(self, weather_service):
        """Test that caching works correctly."""
        # First call
        result1 = await weather_service.get_current_weather(46.0, 7.0)
        
        # Second call should use cache (same coordinates)
        result2 = await weather_service.get_current_weather(46.0, 7.0)
        
        # Results should be identical (from cache)
        assert result1.timestamp == result2.timestamp
        assert result1.temperature_c == result2.temperature_c
    
    def test_calculate_base_temperature(self, weather_service):
        """Test base temperature calculation."""
        # Test winter date
        winter_date = datetime(2024, 1, 15)
        temp_winter = weather_service._calculate_base_temperature(46.0, winter_date)
        
        # Test summer date
        summer_date = datetime(2024, 7, 15)
        temp_summer = weather_service._calculate_base_temperature(46.0, summer_date)
        
        # Summer should be warmer than winter
        assert temp_summer > temp_winter
        
        # Test latitude effect (higher latitude should be colder)
        temp_low_lat = weather_service._calculate_base_temperature(30.0, winter_date)
        temp_high_lat = weather_service._calculate_base_temperature(60.0, winter_date)
        
        assert temp_low_lat > temp_high_lat
    
    def test_analyze_ski_conditions(self, weather_service):
        """Test ski conditions analysis."""
        # Create mock weather data
        from agents.weather.models import WeatherData, WindData, VisibilityData
        
        weather = WeatherData(
            timestamp=datetime.now(),
            temperature_c=-5.0,  # Good skiing temperature
            feels_like_c=-7.0,
            humidity_percent=70.0,
            pressure_hpa=1013.0,
            condition=WeatherCondition.CLEAR,
            wind=WindData(speed_kmh=10.0, direction_degrees=180.0),
            visibility=VisibilityData(distance_km=20.0, condition="Good"),
            precipitation_mm=0.0,
        )
        
        conditions = weather_service._analyze_ski_conditions(weather, elevation_m=2000)
        
        assert conditions.overall_rating > 5  # Should be good conditions
        assert conditions.temperature_rating > 5  # Good temperature
        assert conditions.wind_rating > 5  # Low wind
        assert conditions.visibility_rating > 5  # Good visibility
        assert len(conditions.recommended_gear) > 0
        assert conditions.best_time_of_day is not None


class TestWeatherModels:
    """Test cases for weather data models."""
    
    def test_wind_data_validation(self):
        """Test wind data validation."""
        from agents.weather.models import WindData
        
        # Valid wind data
        wind = WindData(speed_kmh=25.0, direction_degrees=180.0)
        assert wind.speed_kmh == 25.0
        assert wind.direction_degrees == 180.0
        
        # Invalid wind data (should raise validation error)
        with pytest.raises(ValueError):
            WindData(speed_kmh=-5.0, direction_degrees=180.0)  # Negative speed
        
        with pytest.raises(ValueError):
            WindData(speed_kmh=25.0, direction_degrees=400.0)  # Invalid direction
    
    def test_weather_request_defaults(self):
        """Test weather request default values."""
        from agents.weather.models import WeatherRequest
        
        request = WeatherRequest(latitude=46.0, longitude=7.0)
        
        assert request.latitude == 46.0
        assert request.longitude == 7.0
        assert request.timestamp is None
        assert request.include_forecast is False
        assert request.forecast_days == 7
        assert request.include_historical is False
        assert request.historical_days == 30