"""Topographical data processing using DEM sources."""

import asyncio
import math
import tempfile
import time
from pathlib import Path
from typing import List
from typing import Optional
from typing import Tuple

import numpy as np
import rasterio
import structlog
from rasterio.enums import Resampling
from rasterio.mask import mask
from rasterio.warp import calculate_default_transform
from rasterio.warp import reproject
from rasterio.warp import Resampling as WarpResampling
from shapely.geometry import box

from agents.hill_metrics.models import AspectData
from agents.hill_metrics.models import ElevationData
from agents.hill_metrics.models import GeographicBounds
from agents.hill_metrics.models import GridSize
from agents.hill_metrics.models import HillMetrics
from agents.hill_metrics.models import SlopeData
from agents.hill_metrics.models import SurfaceClassification
from agents.hill_metrics.models import SurfaceType
from agents.shared.utils import CacheManager
from agents.shared.utils import download_file
from agents.shared.utils import generate_cache_key

logger = structlog.get_logger(__name__)


class DEMProcessor:
    """Digital Elevation Model processor for terrain analysis."""
    
    def __init__(self, cache_dir: Path = Path("cache/dem")):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_manager = CacheManager(default_ttl=3600)  # 1 hour cache
        
        # SRTM data sources (30m resolution)
        self.srtm_base_url = "https://cloud.sdsc.edu/v1/AUTH_opentopography/Raster/SRTM_GL1"
        
        # USGS 3DEP data sources (10m resolution for US)
        self.usgs_base_url = "https://cloud.sdsc.edu/v1/AUTH_opentopography/Raster/USGS3DEP"
    
    async def process_terrain(
        self,
        bounds: GeographicBounds,
        grid_size: GridSize,
        include_surface_classification: bool = True,
    ) -> HillMetrics:
        """
        Process terrain data for the given bounds.
        
        Args:
            bounds: Geographic bounds for processing
            grid_size: Desired grid resolution
            include_surface_classification: Whether to classify surface types
            
        Returns:
            Processed hill metrics data
        """
        start_time = time.time()
        
        # Generate cache key
        cache_key = generate_cache_key(
            bounds.model_dump(),
            grid_size.value,
            include_surface_classification,
        )
        
        # Check cache first
        cached_result = self.cache_manager.get(cache_key)
        if cached_result:
            logger.info("Returning cached terrain data", cache_key=cache_key)
            return cached_result
        
        try:
            # Download and process DEM data
            dem_path = await self._get_dem_data(bounds)
            
            # Extract elevation data for the specific bounds
            elevation_data = await self._extract_elevation_data(
                dem_path, bounds, grid_size
            )
            
            # Calculate slope and aspect
            slope_data = self._calculate_slope(elevation_data)
            aspect_data = self._calculate_aspect(elevation_data)
            
            # Classify surface types if requested
            surface_classification = None
            if include_surface_classification:
                surface_classification = self._classify_surfaces(
                    elevation_data, slope_data, aspect_data
                )
            
            # Create hill metrics
            hill_metrics = HillMetrics(
                elevation=elevation_data,
                slope=slope_data,
                aspect=aspect_data,
                surface_classification=surface_classification or SurfaceClassification(
                    grid=[[SurfaceType.PACKED for _ in range(len(elevation_data.grid[0]))]
                          for _ in range(len(elevation_data.grid))],
                    resolution=elevation_data.resolution,
                    bounds=elevation_data.bounds,
                ),
                metadata={
                    "processing_time_ms": (time.time() - start_time) * 1000,
                    "data_source": "SRTM/USGS",
                    "grid_size": grid_size.value,
                },
            )
            
            # Cache the result
            self.cache_manager.set(cache_key, hill_metrics)
            
            logger.info(
                "Processed terrain data",
                bounds=bounds.model_dump(),
                grid_size=grid_size.value,
                processing_time_ms=(time.time() - start_time) * 1000,
            )
            
            return hill_metrics
            
        except Exception as e:
            logger.error(
                "Failed to process terrain data",
                bounds=bounds.model_dump(),
                grid_size=grid_size.value,
                error=str(e),
                exc_info=True,
            )
            raise
    
    async def _get_dem_data(self, bounds: GeographicBounds) -> Path:
        """
        Download or retrieve cached DEM data for the bounds.
        
        Args:
            bounds: Geographic bounds
            
        Returns:
            Path to the DEM file
        """
        # For this implementation, we'll use a simplified approach
        # In production, you would implement proper SRTM/USGS data fetching
        
        cache_key = generate_cache_key(bounds.model_dump())
        dem_path = self.cache_dir / f"dem_{cache_key}.tif"
        
        if dem_path.exists():
            logger.info("Using cached DEM data", path=str(dem_path))
            return dem_path
        
        # Generate synthetic DEM data for demonstration
        # In production, replace this with actual SRTM/USGS data download
        await self._generate_synthetic_dem(bounds, dem_path)
        
        return dem_path
    
    async def _generate_synthetic_dem(
        self,
        bounds: GeographicBounds,
        output_path: Path,
    ) -> None:
        """
        Generate synthetic DEM data for demonstration purposes.
        
        Args:
            bounds: Geographic bounds
            output_path: Output file path
        """
        logger.info("Generating synthetic DEM data", bounds=bounds.model_dump())
        
        # Create synthetic elevation data with realistic ski slope characteristics
        width, height = 512, 512
        
        # Generate base terrain with multiple peaks and valleys
        x = np.linspace(0, 4 * np.pi, width)
        y = np.linspace(0, 4 * np.pi, height)
        X, Y = np.meshgrid(x, y)
        
        # Create mountainous terrain
        elevation = (
            1000 +  # Base elevation
            800 * np.sin(X * 0.5) * np.cos(Y * 0.5) +  # Main mountain
            400 * np.sin(X * 1.2) * np.sin(Y * 0.8) +  # Secondary peaks
            200 * np.sin(X * 2.0) * np.cos(Y * 1.5) +  # Ridges
            100 * np.random.random((height, width))     # Noise
        )
        
        # Ensure realistic elevation range for ski areas (500-3000m)
        elevation = np.clip(elevation, 500, 3000)
        
        # Create GeoTIFF
        transform = rasterio.transform.from_bounds(
            bounds.west, bounds.south, bounds.east, bounds.north,
            width, height
        )
        
        with rasterio.open(
            output_path,
            'w',
            driver='GTiff',
            height=height,
            width=width,
            count=1,
            dtype=elevation.dtype,
            crs='EPSG:4326',
            transform=transform,
        ) as dst:
            dst.write(elevation, 1)
        
        logger.info("Generated synthetic DEM", output_path=str(output_path))
    
    async def _extract_elevation_data(
        self,
        dem_path: Path,
        bounds: GeographicBounds,
        grid_size: GridSize,
    ) -> ElevationData:
        """
        Extract elevation data from DEM file.
        
        Args:
            dem_path: Path to DEM file
            bounds: Geographic bounds
            grid_size: Desired grid size
            
        Returns:
            Elevation data
        """
        # Parse grid size
        grid_width, grid_height = map(int, grid_size.value.split('x'))
        
        with rasterio.open(dem_path) as src:
            # Create bounding box geometry
            bbox = box(bounds.west, bounds.south, bounds.east, bounds.north)
            
            # Mask the raster to the bounding box
            out_image, out_transform = mask(src, [bbox], crop=True)
            elevation_array = out_image[0]
            
            # Resample to desired grid size
            if elevation_array.shape != (grid_height, grid_width):
                # Calculate new transform for resampling
                new_transform = rasterio.transform.from_bounds(
                    bounds.west, bounds.south, bounds.east, bounds.north,
                    grid_width, grid_height
                )
                
                # Create output array
                resampled = np.empty((grid_height, grid_width), dtype=np.float32)
                
                # Reproject to new grid
                reproject(
                    elevation_array,
                    resampled,
                    src_transform=out_transform,
                    src_crs=src.crs,
                    dst_transform=new_transform,
                    dst_crs=src.crs,
                    resampling=WarpResampling.bilinear,
                )
                
                elevation_array = resampled
                out_transform = new_transform
        
        # Convert to list format and calculate resolution
        elevation_grid = elevation_array.tolist()
        
        # Calculate resolution in meters per cell
        lat_range = bounds.north - bounds.south
        lng_range = bounds.east - bounds.west
        
        # Approximate resolution (this is simplified)
        lat_resolution = (lat_range * 111000) / grid_height  # ~111km per degree
        lng_resolution = (lng_range * 111000 * math.cos(math.radians((bounds.north + bounds.south) / 2))) / grid_width
        resolution = (lat_resolution + lng_resolution) / 2
        
        return ElevationData(
            grid=elevation_grid,
            resolution=resolution,
            bounds=bounds,
            no_data_value=-9999,
        )
    
    def _calculate_slope(self, elevation_data: ElevationData) -> SlopeData:
        """
        Calculate slope angles from elevation data.
        
        Args:
            elevation_data: Elevation data
            
        Returns:
            Slope data in degrees
        """
        elevation_array = np.array(elevation_data.grid)
        
        # Calculate gradients
        dy, dx = np.gradient(elevation_array)
        
        # Calculate slope in radians, then convert to degrees
        slope_rad = np.arctan(np.sqrt(dx**2 + dy**2) / elevation_data.resolution)
        slope_deg = np.degrees(slope_rad)
        
        return SlopeData(
            grid=slope_deg.tolist(),
            resolution=elevation_data.resolution,
            bounds=elevation_data.bounds,
        )
    
    def _calculate_aspect(self, elevation_data: ElevationData) -> AspectData:
        """
        Calculate aspect (slope direction) from elevation data.
        
        Args:
            elevation_data: Elevation data
            
        Returns:
            Aspect data in degrees (0-360)
        """
        elevation_array = np.array(elevation_data.grid)
        
        # Calculate gradients
        dy, dx = np.gradient(elevation_array)
        
        # Calculate aspect in radians, then convert to degrees
        aspect_rad = np.arctan2(-dy, dx)
        aspect_deg = np.degrees(aspect_rad)
        
        # Convert to 0-360 range
        aspect_deg = (aspect_deg + 360) % 360
        
        return AspectData(
            grid=aspect_deg.tolist(),
            resolution=elevation_data.resolution,
            bounds=elevation_data.bounds,
        )
    
    def _classify_surfaces(
        self,
        elevation_data: ElevationData,
        slope_data: SlopeData,
        aspect_data: AspectData,
    ) -> SurfaceClassification:
        """
        Classify surface types based on terrain characteristics.
        
        Args:
            elevation_data: Elevation data
            slope_data: Slope data
            aspect_data: Aspect data
            
        Returns:
            Surface classification
        """
        elevation_array = np.array(elevation_data.grid)
        slope_array = np.array(slope_data.grid)
        aspect_array = np.array(aspect_data.grid)
        
        height, width = elevation_array.shape
        surface_grid = []
        confidence_grid = []
        
        for i in range(height):
            surface_row = []
            confidence_row = []
            
            for j in range(width):
                elevation = elevation_array[i, j]
                slope = slope_array[i, j]
                aspect = aspect_array[i, j]
                
                # Simple classification logic
                surface_type, confidence = self._classify_single_cell(
                    elevation, slope, aspect
                )
                
                surface_row.append(surface_type)
                confidence_row.append(confidence)
            
            surface_grid.append(surface_row)
            confidence_grid.append(confidence_row)
        
        return SurfaceClassification(
            grid=surface_grid,
            resolution=elevation_data.resolution,
            bounds=elevation_data.bounds,
            confidence=confidence_grid,
        )
    
    def _classify_single_cell(
        self,
        elevation: float,
        slope: float,
        aspect: float,
    ) -> Tuple[SurfaceType, float]:
        """
        Classify a single terrain cell.
        
        Args:
            elevation: Cell elevation in meters
            slope: Cell slope in degrees
            aspect: Cell aspect in degrees
            
        Returns:
            Tuple of (surface_type, confidence)
        """
        # Simple classification rules
        if slope > 45:
            return SurfaceType.ROCKS, 0.8
        elif slope > 35:
            return SurfaceType.ICE, 0.7
        elif slope > 25:
            return SurfaceType.PACKED, 0.9
        elif slope > 15:
            # Check for moguls based on elevation variation
            return SurfaceType.MOGULS, 0.6
        elif elevation > 2500:
            return SurfaceType.POWDER, 0.8
        elif slope < 5:
            return SurfaceType.TREES, 0.5
        else:
            return SurfaceType.PACKED, 0.7