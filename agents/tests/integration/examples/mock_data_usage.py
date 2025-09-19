"""
Example usage of MockDataGenerator for integration testing.

This example demonstrates how to use the MockDataGenerator to create
realistic test data for various testing scenarios.
"""

from agents.tests.integration.mock_data_generator import (
    MockDataGenerator, MockDataConfig, TestScenario
)
from agents.hill_metrics.models import GridSize


def basic_mock_data_example():
    """Basic example of generating mock data."""
    print("=== Basic Mock Data Generation ===")
    
    # Create generator with default configuration
    generator = MockDataGenerator()
    
    # Generate terrain data for Chamonix
    terrain_response = generator.generate_terrain_data("chamonix")
    print(f"Generated terrain data with {len(terrain_response.hill_metrics.elevation.grid)}x{len(terrain_response.hill_metrics.elevation.grid[0])} grid")
    print(f"Processing time: {terrain_response.processing_time_ms:.2f}ms")
    
    # Generate weather data
    weather_response = generator.generate_weather_data("chamonix")
    print(f"Current temperature: {weather_response.current.temperature_c:.1f}°C")
    print(f"Wind speed: {weather_response.current.wind.speed_kmh:.1f} km/h")
    print(f"Snow depth: {weather_response.current.snow.depth_cm:.1f} cm")
    
    # Generate equipment data
    equipment_response = generator.generate_equipment_data("chamonix")
    print(f"Generated {len(equipment_response.lifts)} lifts and {len(equipment_response.trails)} trails")
    print(f"Operational lifts: {equipment_response.operational_lifts}/{equipment_response.total_lifts}")


def scenario_based_testing_example():
    """Example of using different test scenarios."""
    print("\n=== Scenario-Based Testing ===")
    
    # Test extreme weather scenario
    extreme_config = MockDataConfig(
        scenario=TestScenario.EXTREME_WEATHER,
        seed=42  # For reproducible results
    )
    extreme_generator = MockDataGenerator(extreme_config)
    
    weather_response = extreme_generator.generate_weather_data("whistler")
    print(f"Extreme weather - Temperature: {weather_response.current.temperature_c:.1f}°C")
    print(f"Extreme weather - Wind: {weather_response.current.wind.speed_kmh:.1f} km/h")
    print(f"Extreme weather - Visibility: {weather_response.current.visibility.distance_km:.1f} km")
    
    # Test equipment failures scenario
    failure_config = MockDataConfig(
        scenario=TestScenario.EQUIPMENT_FAILURES,
        equipment_failure_rate=0.3,  # 30% failure rate
        seed=42
    )
    failure_generator = MockDataGenerator(failure_config)
    
    equipment_response = failure_generator.generate_equipment_data("whistler")
    failed_lifts = len(equipment_response.lifts) - equipment_response.operational_lifts
    print(f"Equipment failures - Failed lifts: {failed_lifts}/{len(equipment_response.lifts)}")


def cache_manipulation_example():
    """Example of cache state manipulation for testing."""
    print("\n=== Cache State Manipulation ===")
    
    generator = MockDataGenerator()
    
    # Simulate different cache states
    cache_states = [
        ("terrain_cache_key", "corrupted"),
        ("weather_cache_key", "expired"),
        ("equipment_cache_key", "missing")
    ]
    
    for cache_key, state in cache_states:
        result = generator.manipulate_cache_state(cache_key, state)
        print(f"Cache key '{cache_key}' set to '{state}'")
        if state == "corrupted":
            print(f"  Corruption type: {result.get('corruption_type')}")
        elif state == "expired":
            print(f"  Expiry time: {result.get('expiry_time')}")
    
    # Show all cache states
    all_states = generator.get_cache_states()
    print(f"Total cache manipulations: {len(all_states)}")


def performance_testing_example():
    """Example of generating data for performance testing."""
    print("\n=== Performance Testing Data ===")
    
    # Generate different sizes of test data
    generator = MockDataGenerator()
    
    for size in ["small", "medium", "large"]:
        perf_data = generator.generate_performance_test_data(size)
        metadata = perf_data["metadata"]
        
        print(f"{size.title()} dataset:")
        print(f"  Grid dimensions: {metadata['grid_dimensions']}")
        print(f"  Data points: {metadata['point_count']}")
        print(f"  Estimated size: {metadata['estimated_size_mb']:.2f} MB")


def reproducible_testing_example():
    """Example of reproducible test data generation."""
    print("\n=== Reproducible Testing ===")
    
    # Create two generators with the same seed
    config1 = MockDataConfig(seed=123, grid_size=GridSize.SMALL)
    config2 = MockDataConfig(seed=123, grid_size=GridSize.SMALL)
    
    generator1 = MockDataGenerator(config1)
    generator2 = MockDataGenerator(config2)
    
    # Generate terrain data with both generators
    terrain1 = generator1.generate_terrain_data("zermatt")
    terrain2 = generator2.generate_terrain_data("zermatt")
    
    # Compare first elevation values
    elev1 = terrain1.hill_metrics.elevation.grid[0][0]
    elev2 = terrain2.hill_metrics.elevation.grid[0][0]
    
    print(f"Generator 1 first elevation: {elev1:.2f}m")
    print(f"Generator 2 first elevation: {elev2:.2f}m")
    print(f"Values match: {abs(elev1 - elev2) < 0.1}")


def comprehensive_testing_workflow():
    """Example of a comprehensive testing workflow."""
    print("\n=== Comprehensive Testing Workflow ===")
    
    # Step 1: Generate baseline data
    config = MockDataConfig(
        seed=42,
        grid_size=GridSize.MEDIUM,
        include_fis_data=True
    )
    generator = MockDataGenerator(config)
    
    # Step 2: Generate all types of data for a ski area
    ski_area = "st_anton"
    
    terrain = generator.generate_terrain_data(ski_area)
    weather = generator.generate_weather_data(ski_area)
    equipment = generator.generate_equipment_data(ski_area)
    ski_conditions = generator.generate_ski_conditions(ski_area)
    
    print(f"Generated complete dataset for {ski_area}:")
    print(f"  Terrain: {len(terrain.hill_metrics.elevation.grid)}x{len(terrain.hill_metrics.elevation.grid[0])} grid")
    print(f"  Weather: {weather.current.condition.value} conditions")
    print(f"  Equipment: {len(equipment.lifts)} lifts, {len(equipment.trails)} trails")
    print(f"  Ski conditions rating: {ski_conditions.conditions.overall_rating:.1f}/10")
    
    # Step 3: Manipulate cache states for testing
    cache_keys = [
        f"terrain_{ski_area}",
        f"weather_{ski_area}",
        f"equipment_{ski_area}"
    ]
    
    for i, key in enumerate(cache_keys):
        state = ["corrupted", "expired", "missing"][i]
        generator.manipulate_cache_state(key, state)
    
    print(f"  Cache manipulations: {len(generator.get_cache_states())}")
    
    # Step 4: Retrieve generated data for validation
    retrieved_terrain = generator.get_generated_data("terrain", ski_area)
    print(f"  Data retrieval successful: {retrieved_terrain is not None}")
    
    # Step 5: Clean up for next test
    generator.clear_generated_data()
    print(f"  Data cleared: {len(generator.get_cache_states()) == 0}")


if __name__ == "__main__":
    """Run all examples."""
    basic_mock_data_example()
    scenario_based_testing_example()
    cache_manipulation_example()
    performance_testing_example()
    reproducible_testing_example()
    comprehensive_testing_workflow()
    
    print("\n=== Mock Data Generation Examples Complete ===")