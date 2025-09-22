#!/usr/bin/env python3
"""Debug script to understand DEM validation issues."""

import asyncio
import logging

from agents.hill_metrics.models import GeographicBounds
from agents.hill_metrics.terrain_processor import DEMProcessor

# Set up logging
logging.basicConfig(level=logging.DEBUG)


async def debug_validation():
    """Debug the validation process."""
    processor = DEMProcessor()

    # Use the same bounds from the error log
    bounds = GeographicBounds(north=45.95, south=45.88, east=6.92, west=6.82)

    print(f"Testing bounds: {bounds}")

    try:
        # Try to get DEM data
        dem_path = await processor._get_dem_data(bounds)
        print(f"Successfully got DEM data: {dem_path}")

        # Try validation manually
        is_valid = await processor._validate_dem_file(dem_path, bounds)
        print(f"Validation result: {is_valid}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_validation())
