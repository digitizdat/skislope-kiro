#!/usr/bin/env python3
"""Debug script to examine DEM validation in detail."""

import asyncio
import logging
from pathlib import Path

import numpy as np
import rasterio

from agents.hill_metrics.models import GeographicBounds
from agents.hill_metrics.terrain_processor import DEMProcessor

# Set up detailed logging
logging.basicConfig(level=logging.DEBUG)


async def debug_dem_validation():
    """Debug the DEM validation process in detail."""
    processor = DEMProcessor()

    # Use the same bounds from the error log
    bounds = GeographicBounds(north=45.95, south=45.88, east=6.92, west=6.82)

    print(f"Testing bounds: {bounds}")

    try:
        # First, let's fetch the data manually to analyze it before validation
        cache_key = "7424eaf44300dbb57f34aab8ced908f4d444ec270cf4a6eb98fb6d66e8d51eef"  # From logs
        dem_path = Path(f"cache/dem/dem_{cache_key}.tif")

        # Fetch data using data source manager directly
        data_source_info = await processor.data_source_manager.fetch_dem_data(
            bounds, dem_path
        )
        print(f"Fetched DEM data: {dem_path}")
        print(f"Data source info: {data_source_info}")

        # Manually analyze the file
        print("\n=== Manual DEM Analysis ===")
        with rasterio.open(dem_path) as src:
            print(f"CRS: {src.crs}")
            print(f"Bounds: {src.bounds}")
            print(f"Shape: {src.shape}")
            print(f"Count: {src.count}")
            print(f"NoData: {src.nodata}")

            # Read elevation data
            elevation_data = src.read(1)
            print(f"Elevation data shape: {elevation_data.shape}")
            print(f"Elevation data dtype: {elevation_data.dtype}")

            # Remove no-data values
            nodata = src.nodata
            if nodata is not None:
                valid_data = elevation_data[elevation_data != nodata]
                print(f"NoData value: {nodata}")
                print(f"Total pixels: {elevation_data.size}")
                print(f"NoData pixels: {np.sum(elevation_data == nodata)}")
                print(f"Valid pixels: {len(valid_data)}")
            else:
                valid_data = elevation_data.flatten()
                print("No NoData value specified")
                print(f"Total pixels: {len(valid_data)}")

            if len(valid_data) > 0:
                min_elevation = np.min(valid_data)
                max_elevation = np.max(valid_data)
                unique_values = len(np.unique(valid_data))
                total_values = len(valid_data)

                print(f"Min elevation: {min_elevation}")
                print(f"Max elevation: {max_elevation}")
                print(f"Unique values: {unique_values}")
                print(f"Total values: {total_values}")
                print(f"Unique percentage: {unique_values / total_values * 100:.2f}%")
                print(f"Threshold (10%): {total_values * 0.1}")
                print(f"Passes unique test: {unique_values >= total_values * 0.1}")

                # Show some sample values
                print(f"Sample values: {valid_data[:10]}")

                # Check elevation range
                elevation_ok = min_elevation >= -500 and max_elevation <= 9000
                print(f"Elevation range OK: {elevation_ok}")

        # Now try the actual validation
        print("\n=== Actual Validation ===")
        is_valid = await processor._validate_dem_file(dem_path, bounds)
        print(f"Validation result: {is_valid}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_dem_validation())
