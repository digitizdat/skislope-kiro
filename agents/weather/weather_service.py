"""Weather data processing and API integration."""

import random
from datetime import datetime
from datetime import timedelta

import structlog

from agents.shared.utils import CacheManager
from agents.shared.utils import RetryConfig
from agents.shared.utils import generate_cache_key
from agents.weather.models import HistoricalWeatherData
from agents.weather.models import SkiConditions
from agents.weather.models import SnowCondition
from agents.weather.models import SnowData
from agents.weather.models import VisibilityData
from agents.weather.models import WeatherCondition
from agents.weather.models import WeatherData
from agents.weather.models import WeatherForecast
from agents.weather.models import WindData

logger = structlog.get_logger(__name__)


class WeatherService:
    """Weather data service with API integration."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key
        self.cache_manager = CacheManager(default_ttl=900)  # 15 minutes cache
        self.retry_config = RetryConfig(max_attempts=3, base_delay=1.0)

        # API endpoints (using OpenWeatherMap as example)
        self.current_weather_url = "https://api.openweathermap.org/data/2.5/weather"
        self.forecast_url = "https://api.openweathermap.org/data/2.5/forecast"
        self.historical_url = (
            "https://api.openweathermap.org/data/3.0/onecall/timemachine"
        )

    async def get_current_weather(
        self,
        latitude: float,
        longitude: float,
    ) -> WeatherData:
        """
        Get current weather data for coordinates.

        Args:
            latitude: Latitude
            longitude: Longitude

        Returns:
            Current weather data
        """
        cache_key = generate_cache_key("current", latitude, longitude)

        # Check cache first
        cached_data = self.cache_manager.get(cache_key)
        if cached_data:
            logger.info("Returning cached weather data", cache_key=cache_key)
            return cached_data

        try:
            # For demonstration, generate synthetic weather data
            # In production, replace with actual API calls
            weather_data = await self._generate_synthetic_weather(latitude, longitude)

            # Cache the result
            self.cache_manager.set(cache_key, weather_data)

            logger.info(
                "Retrieved current weather",
                latitude=latitude,
                longitude=longitude,
            )

            return weather_data

        except Exception as e:
            logger.error(
                "Failed to get current weather",
                latitude=latitude,
                longitude=longitude,
                error=str(e),
                exc_info=True,
            )
            raise

    async def get_weather_forecast(
        self,
        latitude: float,
        longitude: float,
        days: int = 7,
    ) -> list[WeatherForecast]:
        """
        Get weather forecast for coordinates.

        Args:
            latitude: Latitude
            longitude: Longitude
            days: Number of forecast days

        Returns:
            Weather forecast data
        """
        cache_key = generate_cache_key("forecast", latitude, longitude, days)

        # Check cache first
        cached_data = self.cache_manager.get(cache_key)
        if cached_data:
            logger.info("Returning cached forecast data", cache_key=cache_key)
            return cached_data

        try:
            # Generate synthetic forecast data
            forecast_data = await self._generate_synthetic_forecast(
                latitude, longitude, days
            )

            # Cache the result
            self.cache_manager.set(cache_key, forecast_data, ttl=3600)  # 1 hour cache

            logger.info(
                "Retrieved weather forecast",
                latitude=latitude,
                longitude=longitude,
                days=days,
            )

            return forecast_data

        except Exception as e:
            logger.error(
                "Failed to get weather forecast",
                latitude=latitude,
                longitude=longitude,
                days=days,
                error=str(e),
                exc_info=True,
            )
            raise

    async def get_historical_weather(
        self,
        latitude: float,
        longitude: float,
        days: int = 30,
    ) -> list[HistoricalWeatherData]:
        """
        Get historical weather data for coordinates.

        Args:
            latitude: Latitude
            longitude: Longitude
            days: Number of historical days

        Returns:
            Historical weather data
        """
        cache_key = generate_cache_key("historical", latitude, longitude, days)

        # Check cache first
        cached_data = self.cache_manager.get(cache_key)
        if cached_data:
            logger.info("Returning cached historical data", cache_key=cache_key)
            return cached_data

        try:
            # Generate synthetic historical data
            historical_data = await self._generate_synthetic_historical(
                latitude, longitude, days
            )

            # Cache the result for longer (historical data doesn't change)
            self.cache_manager.set(cache_key, historical_data, ttl=86400)  # 24 hours

            logger.info(
                "Retrieved historical weather",
                latitude=latitude,
                longitude=longitude,
                days=days,
            )

            return historical_data

        except Exception as e:
            logger.error(
                "Failed to get historical weather",
                latitude=latitude,
                longitude=longitude,
                days=days,
                error=str(e),
                exc_info=True,
            )
            raise

    async def get_ski_conditions(
        self,
        latitude: float,
        longitude: float,
        elevation_m: float | None = None,
    ) -> SkiConditions:
        """
        Get ski-specific conditions analysis.

        Args:
            latitude: Latitude
            longitude: Longitude
            elevation_m: Elevation in meters

        Returns:
            Ski conditions analysis
        """
        # Get current weather
        weather = await self.get_current_weather(latitude, longitude)

        # Analyze ski conditions
        conditions = self._analyze_ski_conditions(weather, elevation_m)

        logger.info(
            "Analyzed ski conditions",
            latitude=latitude,
            longitude=longitude,
            elevation_m=elevation_m,
            overall_rating=conditions.overall_rating,
        )

        return conditions

    async def _generate_synthetic_weather(
        self,
        latitude: float,
        longitude: float,
    ) -> WeatherData:
        """Generate synthetic weather data for demonstration."""

        # Simulate seasonal and elevation-based weather
        now = datetime.now()

        # Base temperature varies by season and latitude
        base_temp = self._calculate_base_temperature(latitude, now)

        # Add some randomness
        temperature = base_temp + random.uniform(-5, 5)
        feels_like = temperature + random.uniform(-3, 3)

        # Generate other weather parameters
        humidity = random.uniform(30, 90)
        pressure = random.uniform(950, 1050)

        # Wind data
        wind = WindData(
            speed_kmh=random.uniform(0, 30),
            direction_degrees=random.uniform(0, 360),
            gust_speed_kmh=random.uniform(0, 50),
        )

        # Snow data (more likely in winter and at higher latitudes)
        snow_data = None
        if temperature < 5 and (now.month in [11, 12, 1, 2, 3] or abs(latitude) > 45):
            snow_data = SnowData(
                depth_cm=random.uniform(10, 200),
                condition=random.choice(list(SnowCondition)),
                temperature_c=min(temperature, 0),
                density_kg_m3=random.uniform(100, 500),
                last_snowfall_hours=random.randint(0, 72),
            )

        # Visibility
        visibility = VisibilityData(
            distance_km=random.uniform(1, 50),
            condition="Good" if random.random() > 0.3 else "Limited",
        )

        # Weather condition
        if snow_data and temperature < 0:
            condition = random.choice(
                [
                    WeatherCondition.LIGHT_SNOW,
                    WeatherCondition.MODERATE_SNOW,
                    WeatherCondition.CLEAR,
                ]
            )
        else:
            condition = random.choice(
                [
                    WeatherCondition.CLEAR,
                    WeatherCondition.PARTLY_CLOUDY,
                    WeatherCondition.CLOUDY,
                ]
            )

        return WeatherData(
            timestamp=now,
            temperature_c=temperature,
            feels_like_c=feels_like,
            humidity_percent=humidity,
            pressure_hpa=pressure,
            condition=condition,
            wind=wind,
            snow=snow_data,
            visibility=visibility,
            uv_index=random.uniform(0, 10) if now.hour > 6 and now.hour < 18 else 0,
            precipitation_mm=random.uniform(0, 10) if random.random() > 0.7 else 0,
        )

    async def _generate_synthetic_forecast(
        self,
        latitude: float,
        longitude: float,
        days: int,
    ) -> list[WeatherForecast]:
        """Generate synthetic forecast data."""

        forecast = []
        base_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        for i in range(days):
            date = base_date + timedelta(days=i + 1)
            base_temp = self._calculate_base_temperature(latitude, date)

            # Add daily variation
            temp_high = base_temp + random.uniform(2, 8)
            temp_low = base_temp - random.uniform(2, 8)

            forecast.append(
                WeatherForecast(
                    timestamp=date,
                    temperature_high_c=temp_high,
                    temperature_low_c=temp_low,
                    condition=random.choice(list(WeatherCondition)),
                    precipitation_probability=random.uniform(0, 1),
                    precipitation_mm=random.uniform(0, 15)
                    if random.random() > 0.6
                    else 0,
                    wind_speed_kmh=random.uniform(5, 25),
                    snow_depth_cm=random.uniform(0, 50) if temp_low < 2 else None,
                )
            )

        return forecast

    async def _generate_synthetic_historical(
        self,
        latitude: float,
        longitude: float,
        days: int,
    ) -> list[HistoricalWeatherData]:
        """Generate synthetic historical data."""

        historical = []
        base_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        for i in range(days):
            date = base_date - timedelta(days=i + 1)
            base_temp = self._calculate_base_temperature(latitude, date)

            # Add daily variation
            temp_high = base_temp + random.uniform(2, 8)
            temp_low = base_temp - random.uniform(2, 8)
            temp_avg = (temp_high + temp_low) / 2

            historical.append(
                HistoricalWeatherData(
                    date=date,
                    temperature_high_c=temp_high,
                    temperature_low_c=temp_low,
                    temperature_avg_c=temp_avg,
                    precipitation_mm=random.uniform(0, 20)
                    if random.random() > 0.7
                    else 0,
                    snow_depth_cm=random.uniform(0, 100) if temp_avg < 2 else None,
                    wind_speed_avg_kmh=random.uniform(5, 20),
                    condition=random.choice(list(WeatherCondition)),
                )
            )

        return historical

    def _calculate_base_temperature(self, latitude: float, date: datetime) -> float:
        """Calculate base temperature based on latitude and season."""

        # Seasonal variation
        day_of_year = date.timetuple().tm_yday
        seasonal_factor = -10 * math.cos(2 * math.pi * day_of_year / 365)

        # Latitude factor (colder at higher latitudes)
        latitude_factor = -0.5 * abs(latitude)

        # Base temperature
        base_temp = 15 + seasonal_factor + latitude_factor

        return base_temp

    def _analyze_ski_conditions(
        self,
        weather: WeatherData,
        elevation_m: float | None = None,
    ) -> SkiConditions:
        """Analyze ski conditions based on weather data."""

        # Temperature rating (ideal range: -10 to -2°C)
        temp_rating = 10
        if weather.temperature_c > 5:
            temp_rating = 2
        elif weather.temperature_c > 0:
            temp_rating = 5
        elif weather.temperature_c < -15:
            temp_rating = 6

        # Wind rating (lower is better for skiing)
        wind_rating = max(0, 10 - (weather.wind.speed_kmh / 5))

        # Visibility rating
        visibility_rating = min(10, weather.visibility.distance_km / 2)

        # Snow quality assessment
        snow_quality = SnowCondition.NO_SNOW
        if weather.snow:
            snow_quality = weather.snow.condition

        # Overall rating
        overall_rating = (temp_rating + wind_rating + visibility_rating) / 3

        # Recommended gear
        recommended_gear = ["Ski goggles", "Ski helmet"]
        if weather.temperature_c < -10:
            recommended_gear.extend(["Thermal layers", "Face mask"])
        if weather.wind.speed_kmh > 20:
            recommended_gear.append("Windproof jacket")
        if weather.condition in [
            WeatherCondition.LIGHT_SNOW,
            WeatherCondition.MODERATE_SNOW,
        ]:
            recommended_gear.append("Snow goggles")

        # Safety warnings
        safety_warnings = []
        if weather.wind.speed_kmh > 30:
            safety_warnings.append(
                "High wind conditions - exercise caution on exposed slopes"
            )
        if weather.visibility.distance_km < 5:
            safety_warnings.append("Limited visibility - stay on marked trails")
        if weather.temperature_c < -20:
            safety_warnings.append("Extreme cold - risk of frostbite")

        # Best time of day
        best_time = "Morning"
        if weather.condition == WeatherCondition.CLEAR:
            best_time = "All day"
        elif weather.wind.speed_kmh > 20:
            best_time = "Early morning (calmer winds)"

        return SkiConditions(
            overall_rating=overall_rating,
            snow_quality=snow_quality,
            visibility_rating=visibility_rating,
            wind_rating=wind_rating,
            temperature_rating=temp_rating,
            recommended_gear=recommended_gear,
            safety_warnings=safety_warnings,
            best_time_of_day=best_time,
        )


# Import math for temperature calculations
import math
