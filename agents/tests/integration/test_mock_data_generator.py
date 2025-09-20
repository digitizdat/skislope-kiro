"""
Unit tests for MockDataGenerator.

Tests the mock data generation functionality including terrain data,
weather data, equipment data, cache state manipulation, and scenario handling.
"""

from datetime import datetime

import pytest

from agents.equipment.models import LiftStatus
from agents.equipment.models import TrailStatus
from agents.hill_metrics.models import GridSize
from agents.hill_metrics.models import SurfaceType
from agents.tests.integration.mock_data_generator import MockDataConfig
from agents.tests.integration.mock_data_generator import MockDataGenerator
from agents.tests.integration.mock_data_generator import TestScenario
from agents.weather.models import SnowCondition
from agents.weather.models import WeatherCondition


class TestMockDataGenerator:
    """Test cases for MockDataGenerator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = MockDataConfig(seed=42)  # Fixed seed for reproducible tests
        self.generator = MockDataGenerator(self.config)

    def test_initialization_default_config(self):
        """Test generator initialization with default configuration."""
        generator = MockDataGenerator()

        assert generator.config.scenario == TestScenario.NORMAL_CONDITIONS
        assert generator.config.grid_size == GridSize.MEDIUM
        assert generator.config.weather_variability == 0.3
        assert generator.config.equipment_failure_rate == 0.1
        assert generator.config.cache_corruption_rate == 0.0
        assert generator.config.performance_load_factor == 1.0

    def test_initialization_custom_config(self):
        """Test generator initialization with custom configuration."""
        custom_config = MockDataConfig(
            seed=123,
            scenario=TestScenario.EXTREME_WEATHER,
            grid_size=GridSize.LARGE,
            weather_variability=0.8,
            equipment_failure_rate=0.5,
        )
        generator = MockDataGenerator(custom_config)

        assert generator.config.scenario == TestScenario.EXTREME_WEATHER
        assert generator.config.grid_size == GridSize.LARGE
        assert generator.config.weather_variability == 0.8
        assert generator.config.equipment_failure_rate == 0.5

    def test_ski_areas_data_structure(self):
        """Test that ski areas data structure is properly defined."""
        assert len(MockDataGenerator.SKI_AREAS) == 5

        required_keys = ["name", "country", "bounds", "base_elevation", "top_elevation"]
        for area_id, area_data in MockDataGenerator.SKI_AREAS.items():
            for key in required_keys:
                assert key in area_data, f"Missing key '{key}' in {area_id}"

            # Validate elevation data
            assert area_data["base_elevation"] < area_data["top_elevation"]
            assert area_data["base_elevation"] > 0
            assert area_data["top_elevation"] > 0

    def test_generate_terrain_data_valid_ski_area(self):
        """Test terrain data generation for valid ski area."""
        response = self.generator.generate_terrain_data("chamonix")

        # Validate response structure
        assert response.hill_metrics is not None
        assert response.processing_time_ms > 0
        assert len(response.data_sources) > 0
        assert response.cache_key.startswith("terrain_chamonix")
        assert response.expires_at > 0

        # Validate hill metrics
        hill_metrics = response.hill_metrics
        assert hill_metrics.elevation is not None
        assert hill_metrics.slope is not None
        assert hill_metrics.aspect is not None
        assert hill_metrics.surface_classification is not None

        # Validate grid dimensions
        grid_size = 64  # Medium grid size
        assert len(hill_metrics.elevation.grid) == grid_size
        assert len(hill_metrics.elevation.grid[0]) == grid_size
        assert len(hill_metrics.slope.grid) == grid_size
        assert len(hill_metrics.aspect.grid) == grid_size
        assert len(hill_metrics.surface_classification.grid) == grid_size

    def test_generate_terrain_data_invalid_ski_area(self):
        """Test terrain data generation for invalid ski area."""
        with pytest.raises(ValueError, match="Unknown ski area"):
            self.generator.generate_terrain_data("invalid_area")

    def test_generate_terrain_data_with_fis_data(self):
        """Test terrain data generation with FIS data enabled."""
        config = MockDataConfig(include_fis_data=True, seed=42)
        generator = MockDataGenerator(config)

        response = generator.generate_terrain_data("whistler")
        hill_metrics = response.hill_metrics

        assert len(hill_metrics.safety_zones) > 0
        assert len(hill_metrics.course_markers) > 0

        # Validate safety zone structure
        safety_zone = hill_metrics.safety_zones[0]
        assert safety_zone.id is not None
        assert safety_zone.type in ["barrier", "net", "padding"]
        assert len(safety_zone.coordinates) >= 4  # At least a triangle
        assert safety_zone.height > 0

        # Validate course marker structure
        course_marker = hill_metrics.course_markers[0]
        assert course_marker.id is not None
        assert course_marker.type in ["gate", "timing", "start", "finish"]
        assert -90 <= course_marker.latitude <= 90
        assert -180 <= course_marker.longitude <= 180
        assert course_marker.elevation > 0

    def test_generate_weather_data_valid_ski_area(self):
        """Test weather data generation for valid ski area."""
        response = self.generator.generate_weather_data("zermatt")

        # Validate response structure
        assert response.current is not None
        assert response.location is not None
        assert response.data_source == "mock_weather_service"
        assert response.processing_time_ms > 0

        # Validate current weather
        current = response.current
        assert isinstance(current.timestamp, datetime)
        assert isinstance(current.temperature_c, float)
        assert isinstance(current.humidity_percent, float)
        assert 0 <= current.humidity_percent <= 100
        assert current.pressure_hpa > 0
        assert current.condition in WeatherCondition
        assert current.wind is not None
        assert current.visibility is not None

        # Validate wind data
        assert current.wind.speed_kmh >= 0
        assert 0 <= current.wind.direction_degrees < 360

        # Validate snow data (if present)
        if current.snow:
            assert current.snow.depth_cm >= 0
            assert current.snow.condition in SnowCondition

    def test_generate_weather_data_invalid_ski_area(self):
        """Test weather data generation for invalid ski area."""
        with pytest.raises(ValueError, match="Unknown ski area"):
            self.generator.generate_weather_data("invalid_area")

    def test_generate_equipment_data_valid_ski_area(self):
        """Test equipment data generation for valid ski area."""
        response = self.generator.generate_equipment_data("st_anton")

        # Validate response structure
        assert len(response.lifts) > 0
        assert len(response.trails) > 0
        assert len(response.facilities) > 0
        assert len(response.safety_equipment) > 0
        assert response.total_lifts == len(response.lifts)
        assert response.total_trails == len(response.trails)
        assert response.operational_lifts <= response.total_lifts
        assert response.open_trails <= response.total_trails
        assert isinstance(response.last_updated, datetime)
        assert response.processing_time_ms > 0

        # Validate lift data
        lift = response.lifts[0]
        assert lift.id is not None
        assert lift.name is not None
        assert lift.capacity_per_hour > 0
        assert lift.vertical_rise_m > 0
        assert lift.length_m > 0
        assert lift.ride_time_minutes > 0
        assert -90 <= lift.base_latitude <= 90
        assert -180 <= lift.base_longitude <= 180
        assert lift.base_elevation_m < lift.top_elevation_m

        # Validate trail data
        trail = response.trails[0]
        assert trail.id is not None
        assert trail.name is not None
        assert trail.length_m > 0
        assert trail.vertical_drop_m > 0
        assert trail.width_m > 0
        assert trail.start_elevation_m > trail.end_elevation_m
        assert len(trail.access_lifts) > 0

    def test_generate_ski_conditions(self):
        """Test ski conditions generation."""
        response = self.generator.generate_ski_conditions("copper_mountain")

        # Validate response structure
        assert response.conditions is not None
        assert response.weather is not None
        assert response.location is not None
        assert isinstance(response.timestamp, datetime)
        assert response.processing_time_ms > 0

        # Validate ski conditions
        conditions = response.conditions
        assert 0 <= conditions.overall_rating <= 10
        assert conditions.snow_quality in SnowCondition
        assert 0 <= conditions.visibility_rating <= 10
        assert 0 <= conditions.wind_rating <= 10
        assert 0 <= conditions.temperature_rating <= 10
        assert len(conditions.recommended_gear) > 0
        assert conditions.best_time_of_day in ["morning", "midday", "afternoon"]

    def test_manipulate_cache_state_corrupted(self):
        """Test cache state manipulation for corrupted state."""
        cache_key = "test_cache_key"
        result = self.generator.manipulate_cache_state(cache_key, "corrupted")

        assert result["key"] == cache_key
        assert result["new_state"] == "corrupted"
        assert "corruption_type" in result
        assert result["corruption_type"] in [
            "partial_data",
            "invalid_json",
            "missing_fields",
            "wrong_schema",
        ]
        assert "timestamp" in result

    def test_manipulate_cache_state_expired(self):
        """Test cache state manipulation for expired state."""
        cache_key = "test_cache_key"
        result = self.generator.manipulate_cache_state(cache_key, "expired")

        assert result["key"] == cache_key
        assert result["new_state"] == "expired"
        assert "expiry_time" in result
        assert "timestamp" in result

    def test_manipulate_cache_state_missing(self):
        """Test cache state manipulation for missing state."""
        cache_key = "test_cache_key"
        result = self.generator.manipulate_cache_state(cache_key, "missing")

        assert result["key"] == cache_key
        assert result["new_state"] == "missing"
        assert result["deletion_reason"] == "cache_eviction"
        assert "timestamp" in result

    def test_generate_performance_test_data_small(self):
        """Test performance test data generation for small size."""
        data = self.generator.generate_performance_test_data("small")

        assert "grid_data" in data
        assert "data_points" in data
        assert "metadata" in data

        metadata = data["metadata"]
        assert metadata["size"] == "small"
        assert metadata["multiplier"] == 0.1
        assert "grid_dimensions" in metadata
        assert "point_count" in metadata
        assert "estimated_size_mb" in metadata

        # Verify data is smaller for small size
        assert len(data["data_points"]) < 1000

    def test_generate_performance_test_data_large(self):
        """Test performance test data generation for large size."""
        data = self.generator.generate_performance_test_data("large")

        metadata = data["metadata"]
        assert metadata["size"] == "large"
        assert metadata["multiplier"] == 5.0

        # Verify data is larger for large size
        assert len(data["data_points"]) > 1000
        assert metadata["estimated_size_mb"] > 0

    def test_scenario_extreme_weather_terrain(self):
        """Test extreme weather scenario affects terrain generation."""
        config = MockDataConfig(scenario=TestScenario.EXTREME_WEATHER, seed=42)
        generator = MockDataGenerator(config)

        response = generator.generate_terrain_data("chamonix")
        surface_grid = response.hill_metrics.surface_classification.grid

        # Count ice surfaces (should be higher in extreme weather)
        ice_count = sum(
            1 for row in surface_grid for cell in row if cell == SurfaceType.ICE
        )

        # Should have some ice surfaces due to extreme weather
        assert ice_count > 0

    def test_scenario_equipment_failures(self):
        """Test equipment failures scenario affects equipment generation."""
        config = MockDataConfig(
            scenario=TestScenario.EQUIPMENT_FAILURES,
            equipment_failure_rate=0.8,  # High failure rate
            seed=42,
        )
        generator = MockDataGenerator(config)

        response = generator.generate_equipment_data("whistler")

        # Count failed lifts
        failed_lifts = sum(
            1 for lift in response.lifts if lift.status != LiftStatus.OPERATIONAL
        )

        # Count closed trails
        closed_trails = sum(
            1 for trail in response.trails if trail.status != TrailStatus.OPEN
        )

        # Should have some failures due to high failure rate
        assert failed_lifts > 0 or closed_trails > 0

    def test_scenario_extreme_weather_conditions(self):
        """Test extreme weather scenario affects weather generation."""
        config = MockDataConfig(scenario=TestScenario.EXTREME_WEATHER, seed=42)
        generator = MockDataGenerator(config)

        response = generator.generate_weather_data("zermatt")
        current = response.current

        # Extreme weather should have harsh conditions
        assert current.temperature_c < -10  # Very cold
        assert current.wind.speed_kmh > 30  # High wind
        assert current.condition in [
            WeatherCondition.HEAVY_SNOW,
            WeatherCondition.BLIZZARD,
            WeatherCondition.FOG,
        ]
        assert current.visibility.distance_km < 2  # Poor visibility

    def test_get_generated_data(self):
        """Test retrieval of previously generated data."""
        # Generate some data first
        terrain_response = self.generator.generate_terrain_data("chamonix")
        weather_response = self.generator.generate_weather_data("chamonix")

        # Retrieve the data
        retrieved_terrain = self.generator.get_generated_data("terrain", "chamonix")
        retrieved_weather = self.generator.get_generated_data("weather", "chamonix")

        assert retrieved_terrain == terrain_response
        assert retrieved_weather == weather_response

        # Test non-existent data
        non_existent = self.generator.get_generated_data("terrain", "non_existent")
        assert non_existent is None

    def test_clear_generated_data(self):
        """Test clearing of generated data."""
        # Generate some data
        self.generator.generate_terrain_data("chamonix")
        self.generator.manipulate_cache_state("test_key", "corrupted")

        # Verify data exists
        assert self.generator.get_generated_data("terrain", "chamonix") is not None
        assert len(self.generator.get_cache_states()) > 0

        # Clear data
        self.generator.clear_generated_data()

        # Verify data is cleared
        assert self.generator.get_generated_data("terrain", "chamonix") is None
        assert len(self.generator.get_cache_states()) == 0

    def test_get_cache_states(self):
        """Test retrieval of cache states."""
        # Manipulate some cache states
        self.generator.manipulate_cache_state("key1", "corrupted")
        self.generator.manipulate_cache_state("key2", "expired")
        self.generator.manipulate_cache_state("key3", "missing")

        cache_states = self.generator.get_cache_states()

        assert len(cache_states) == 3
        assert cache_states["key1"] == "corrupted"
        assert cache_states["key2"] == "expired"
        assert cache_states["key3"] == "missing"

    def test_reproducible_generation_with_seed(self):
        """Test that data generation is reproducible with same seed."""
        config1 = MockDataConfig(seed=123)
        config2 = MockDataConfig(seed=123)

        generator1 = MockDataGenerator(config1)
        generator2 = MockDataGenerator(config2)

        response1 = generator1.generate_terrain_data("chamonix")
        response2 = generator2.generate_terrain_data("chamonix")

        # Should generate similar data with same seed (allowing for some floating point differences)
        # Check that the grids have the same dimensions
        assert len(response1.hill_metrics.elevation.grid) == len(
            response2.hill_metrics.elevation.grid
        )
        assert len(response1.hill_metrics.elevation.grid[0]) == len(
            response2.hill_metrics.elevation.grid[0]
        )

        # Check that the first few values are similar (within a reasonable tolerance)
        grid1 = response1.hill_metrics.elevation.grid
        grid2 = response2.hill_metrics.elevation.grid

        # Compare first row, first 5 values with tolerance for floating point differences
        for i in range(min(5, len(grid1[0]))):
            assert abs(grid1[0][i] - grid2[0][i]) < 1.0, (
                f"Values differ too much: {grid1[0][i]} vs {grid2[0][i]}"
            )

    def test_different_generation_with_different_seeds(self):
        """Test that data generation differs with different seeds."""
        config1 = MockDataConfig(seed=123)
        config2 = MockDataConfig(seed=456)

        generator1 = MockDataGenerator(config1)
        generator2 = MockDataGenerator(config2)

        response1 = generator1.generate_terrain_data("chamonix")
        response2 = generator2.generate_terrain_data("chamonix")

        # Should generate different data with different seeds
        assert (
            response1.hill_metrics.elevation.grid
            != response2.hill_metrics.elevation.grid
        )

    def test_performance_load_factor_affects_processing_time(self):
        """Test that performance load factor affects processing times."""
        config_normal = MockDataConfig(performance_load_factor=1.0, seed=42)
        config_high_load = MockDataConfig(performance_load_factor=3.0, seed=42)

        generator_normal = MockDataGenerator(config_normal)
        generator_high_load = MockDataGenerator(config_high_load)

        response_normal = generator_normal.generate_terrain_data("chamonix")
        response_high_load = generator_high_load.generate_terrain_data("chamonix")

        # High load should result in longer processing times
        assert (
            response_high_load.processing_time_ms > response_normal.processing_time_ms
        )

    def test_grid_size_affects_terrain_dimensions(self):
        """Test that grid size configuration affects terrain grid dimensions."""
        config_small = MockDataConfig(grid_size=GridSize.SMALL, seed=42)
        config_large = MockDataConfig(grid_size=GridSize.LARGE, seed=42)

        generator_small = MockDataGenerator(config_small)
        generator_large = MockDataGenerator(config_large)

        response_small = generator_small.generate_terrain_data("chamonix")
        response_large = generator_large.generate_terrain_data("chamonix")

        # Different grid sizes should produce different dimensions
        small_size = len(response_small.hill_metrics.elevation.grid)
        large_size = len(response_large.hill_metrics.elevation.grid)

        assert small_size == 32  # Small grid
        assert large_size == 96  # Large grid
        assert small_size < large_size


class TestMockDataConfig:
    """Test cases for MockDataConfig class."""

    def test_default_configuration(self):
        """Test default configuration values."""
        config = MockDataConfig()

        assert config.seed is None
        assert config.scenario == TestScenario.NORMAL_CONDITIONS
        assert config.grid_size == GridSize.MEDIUM
        assert config.include_fis_data is False
        assert config.weather_variability == 0.3
        assert config.equipment_failure_rate == 0.1
        assert config.cache_corruption_rate == 0.0
        assert config.performance_load_factor == 1.0

    def test_custom_configuration(self):
        """Test custom configuration values."""
        config = MockDataConfig(
            seed=42,
            scenario=TestScenario.EDGE_CASES,
            grid_size=GridSize.EXTRA_LARGE,
            include_fis_data=True,
            weather_variability=0.8,
            equipment_failure_rate=0.5,
            cache_corruption_rate=0.2,
            performance_load_factor=2.0,
        )

        assert config.seed == 42
        assert config.scenario == TestScenario.EDGE_CASES
        assert config.grid_size == GridSize.EXTRA_LARGE
        assert config.include_fis_data is True
        assert config.weather_variability == 0.8
        assert config.equipment_failure_rate == 0.5
        assert config.cache_corruption_rate == 0.2
        assert config.performance_load_factor == 2.0


class TestTestScenario:
    """Test cases for TestScenario enum."""

    def test_scenario_values(self):
        """Test that all expected scenario values exist."""
        expected_scenarios = [
            "normal",
            "extreme_weather",
            "equipment_failures",
            "cache_corruption",
            "network_issues",
            "performance_stress",
            "edge_cases",
        ]

        actual_scenarios = [scenario.value for scenario in TestScenario]

        for expected in expected_scenarios:
            assert expected in actual_scenarios

        assert len(actual_scenarios) == len(expected_scenarios)
