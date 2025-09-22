#!/usr/bin/env python3
"""Test the full terrain processing pipeline with the validation fix."""

import asyncio
import logging

from agents.hill_metrics.models import GeographicBounds
from agents.hill_metrics.models import GridSize
from agents.hill_metrics.terrain_processor import DEMProcessor

# Set up logging
logging.basicConfig(level=logging.INFO)


async def test_full_pipeline():
    """Test the complete terrain processing pipeline."""
    processor = DEMProcessor()

    # Use Chamonix coordinates
    bounds = GeographicBounds(north=45.95, south=45.88, east=6.92, west=6.82)

    print(f"Testing full terrain processing for Chamonix: {bounds}")

    try:
        # Process terrain with the fix
        hill_metrics = await processor.process_terrain(
            bounds=bounds,
            grid_size=GridSize.SMALL,  # 32x32
            include_surface_classification=True,
        )

        print("✅ SUCCESS: Terrain processing completed!")
        print(
            f"Elevation grid shape: {len(hill_metrics.elevation.grid)} x {len(hill_metrics.elevation.grid[0])}"
        )
        print(f"Resolution: {hill_metrics.elevation.resolution:.2f}m per cell")
        print(f"Elevation range: {hill_metrics.metadata['elevation_range']}")
        print(f"Data source: {hill_metrics.metadata['data_source']}")
        print(f"Processing time: {hill_metrics.metadata['processing_time_ms']:.1f}ms")

        # Verify we have valid data
        assert len(hill_metrics.elevation.grid) == 32, "Should have 32 rows"
        assert len(hill_metrics.elevation.grid[0]) == 32, "Should have 32 columns"
        assert hill_metrics.slope is not None, "Should have slope data"
        assert hill_metrics.aspect is not None, "Should have aspect data"
        assert hill_metrics.surface_classification is not None, (
            "Should have surface classification"
        )

        print("✅ All assertions passed - terrain data is valid!")

    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    success = asyncio.run(test_full_pipeline())
    if success:
        print("\n🎉 Full terrain processing pipeline test PASSED!")
    else:
        print("\n💥 Full terrain processing pipeline test FAILED!")
        exit(1)
