"""Topographical data processing using DEM sources."""

import math
import time
from pathlib import Path

import numpy as np
import rasterio
import structlog
from rasterio.crs import CRS
from rasterio.mask import mask
from rasterio.warp import Resampling as WarpResampling
from rasterio.warp import calculate_default_transform
from rasterio.warp import reproject
from shapely.geometry import box

from agents.hill_metrics.data_sources import DataSourceManager
from agents.hill_metrics.models import AspectData
from agents.hill_metrics.models import ElevationData
from agents.hill_metrics.models import GeographicBounds
from agents.hill_metrics.models import GridSize
from agents.hill_metrics.models import HillMetrics
from agents.hill_metrics.models import SlopeData
from agents.hill_metrics.models import SurfaceClassification
from agents.hill_metrics.models import SurfaceType
from agents.shared.utils import CacheManager
from agents.shared.utils import generate_cache_key

logger = structlog.get_logger(__name__)


class TerrainDataError(Exception):
    """Base exception for terrain data errors."""

    def __init__(
        self,
        message: str,
        bounds: GeographicBounds | None = None,
        processing_step: str | None = None,
    ):
        self.bounds = bounds
        self.processing_step = processing_step
        super().__init__(message)


class DataValidationError(TerrainDataError):
    """Raised when terrain data validation fails."""

    def __init__(
        self, validation_failures: list[str], bounds: GeographicBounds | None = None
    ):
        self.validation_failures = validation_failures
        super().__init__(
            f"Data validation failed: {validation_failures}",
            bounds=bounds,
            processing_step="validation",
        )


class CoordinateTransformError(TerrainDataError):
    """Raised when coordinate system transformation fails."""

    def __init__(
        self, source_crs: str, target_crs: str, bounds: GeographicBounds | None = None
    ):
        self.source_crs = source_crs
        self.target_crs = target_crs
        super().__init__(
            f"Failed to transform from {source_crs} to {target_crs}",
            bounds=bounds,
            processing_step="coordinate_transform",
        )


class DEMProcessor:
    """Digital Elevation Model processor for terrain analysis."""

    def __init__(self, cache_dir: Path = Path("cache/dem")):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_manager = CacheManager(default_ttl=3600)  # 1 hour cache
        self.data_source_manager = DataSourceManager()
        self._last_data_source_info = None  # Store last used data source info

        # Supported DEM formats
        self.supported_formats = {
            ".tif": self._read_geotiff,
            ".tiff": self._read_geotiff,
            ".img": self._read_erdas_imagine,
            ".hgt": self._read_srtm_hgt,
            ".asc": self._read_ascii_grid,
            ".bil": self._read_bil,
            ".flt": self._read_float_grid,
        }

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

            # Create default surface classification if not requested
            if surface_classification is None:
                surface_classification = SurfaceClassification(
                    grid=[
                        [SurfaceType.PACKED for _ in range(len(elevation_data.grid[0]))]
                        for _ in range(len(elevation_data.grid))
                    ],
                    resolution=elevation_data.resolution,
                    bounds=elevation_data.bounds,
                )

            # Determine data source from metadata
            data_source = "Unknown"
            if hasattr(self, "_last_data_source_info") and self._last_data_source_info:
                data_source = self._last_data_source_info.name

            # Create hill metrics
            hill_metrics = HillMetrics(
                elevation=elevation_data,
                slope=slope_data,
                aspect=aspect_data,
                surface_classification=surface_classification,
                metadata={
                    "processing_time_ms": (time.time() - start_time) * 1000,
                    "data_source": data_source,
                    "grid_size": grid_size.value,
                    "bounds": bounds.model_dump(),
                    "resolution_meters": elevation_data.resolution,
                    "elevation_range": [
                        float(np.min(np.array(elevation_data.grid))),
                        float(np.max(np.array(elevation_data.grid))),
                    ],
                },
            )

            # Cache the result
            self.cache_manager.set(cache_key, hill_metrics)

            logger.info(
                "Successfully processed terrain data",
                bounds=bounds.model_dump(),
                grid_size=grid_size.value,
                data_source=data_source,
                processing_time_ms=(time.time() - start_time) * 1000,
                elevation_range=hill_metrics.metadata["elevation_range"],
                resolution_meters=elevation_data.resolution,
            )

            return hill_metrics

        except TerrainDataError:
            # Re-raise terrain-specific errors without wrapping
            raise
        except Exception as e:
            logger.error(
                "Unexpected error processing terrain data",
                bounds=bounds.model_dump(),
                grid_size=grid_size.value,
                error=str(e),
                exc_info=True,
            )
            raise TerrainDataError(
                f"Unexpected error during terrain processing: {e!s}",
                bounds=bounds,
                processing_step="terrain_processing",
            ) from e

    async def _get_dem_data(self, bounds: GeographicBounds) -> Path:
        """
        Download or retrieve cached DEM data for the bounds.

        Args:
            bounds: Geographic bounds

        Returns:
            Path to the DEM file

        Raises:
            TerrainDataError: When no valid DEM data can be obtained
        """
        cache_key = generate_cache_key(bounds.model_dump())
        dem_path = self.cache_dir / f"dem_{cache_key}.tif"

        if dem_path.exists():
            logger.info("Using cached DEM data", path=str(dem_path))
            # Validate cached file before using
            if await self._validate_dem_file(dem_path, bounds):
                return dem_path
            else:
                logger.warning(
                    "Cached DEM file is invalid, removing", path=str(dem_path)
                )
                dem_path.unlink()

        # Try to fetch real DEM data using data source manager
        data_source_info = await self.data_source_manager.fetch_dem_data(
            bounds, dem_path
        )

        if data_source_info:
            # Store data source info for metadata
            self._last_data_source_info = data_source_info

            logger.info(
                "Successfully fetched real DEM data",
                source=data_source_info.name,
                resolution=data_source_info.estimated_resolution,
                path=str(dem_path),
            )

            # Validate the downloaded file
            if await self._validate_dem_file(dem_path, bounds):
                return dem_path
            else:
                logger.error(
                    "Downloaded DEM file is invalid",
                    path=str(dem_path),
                    source=data_source_info.name,
                )
                # Remove invalid file
                if dem_path.exists():
                    dem_path.unlink()
                raise TerrainDataError(
                    f"Invalid DEM data from {data_source_info.name}",
                    bounds=bounds,
                    processing_step="data_validation",
                )

        # No fallback to synthetic data - raise error instead
        raise TerrainDataError(
            "No valid DEM data sources available",
            bounds=bounds,
            processing_step="data_acquisition",
        )

    async def _validate_dem_file(
        self, dem_path: Path, bounds: GeographicBounds
    ) -> bool:
        """
        Validate a DEM file for correctness and quality.

        Args:
            dem_path: Path to the DEM file
            bounds: Expected geographic bounds

        Returns:
            True if file is valid, False otherwise
        """
        try:
            with rasterio.open(dem_path) as src:
                # Check basic file properties
                if src.count != 1:
                    logger.warning("DEM file has multiple bands", bands=src.count)
                    return False

                if src.crs is None:
                    logger.warning("DEM file has no coordinate reference system")
                    return False

                # Check bounds overlap
                file_bounds = src.bounds
                if not self._bounds_overlap(file_bounds, bounds):
                    logger.warning(
                        "DEM file bounds do not overlap with requested bounds",
                        file_bounds=file_bounds,
                        requested_bounds=bounds.model_dump(),
                    )
                    return False

                # Check for reasonable elevation values
                elevation_data = src.read(1)

                # Remove no-data values for validation
                nodata = src.nodata
                if nodata is not None:
                    valid_data = elevation_data[elevation_data != nodata]
                else:
                    valid_data = elevation_data

                if len(valid_data) == 0:
                    logger.warning("DEM file contains no valid elevation data")
                    return False

                min_elevation = np.min(valid_data)
                max_elevation = np.max(valid_data)

                # Check for reasonable elevation ranges (-500m to 9000m)
                if min_elevation < -500 or max_elevation > 9000:
                    logger.warning(
                        "DEM file contains unrealistic elevation values",
                        min_elevation=min_elevation,
                        max_elevation=max_elevation,
                    )
                    return False

                # Enhanced elevation variation validation
                is_valid, reason = self._validate_elevation_variation(valid_data)

                if not is_valid:
                    logger.warning(
                        "Elevation validation failed",
                        reason=reason,
                        min_elevation=min_elevation,
                        max_elevation=max_elevation,
                    )
                    return False

                # Log successful validation with detailed metrics
                unique_values = len(np.unique(valid_data))
                total_values = len(valid_data)
                elevation_range = max_elevation - min_elevation

                logger.info(
                    "DEM file validation passed",
                    path=str(dem_path),
                    crs=str(src.crs),
                    bounds=file_bounds,
                    elevation_range=(min_elevation, max_elevation),
                    elevation_variation=elevation_range,
                    unique_values=unique_values,
                    total_values=total_values,
                    unique_percentage=f"{unique_values / total_values * 100:.2f}%",
                    validation_reason=reason,
                )
                return True

        except Exception as e:
            logger.error("Error validating DEM file", path=str(dem_path), error=str(e))
            return False

    def _validate_elevation_variation(self, valid_data: np.ndarray) -> tuple[bool, str]:
        """
        Validate elevation data using multiple quality indicators.

        Args:
            valid_data: Array of valid elevation values (no-data removed)

        Returns:
            Tuple of (is_valid, reason)
        """
        unique_values = len(np.unique(valid_data))
        total_values = len(valid_data)
        unique_percentage = unique_values / total_values * 100

        min_elevation = np.min(valid_data)
        max_elevation = np.max(valid_data)
        elevation_range = max_elevation - min_elevation

        # Reject obviously corrupted data (less than 1% unique)
        if unique_percentage < 1.0:
            return False, f"Too few unique values: {unique_percentage:.2f}%"

        # Reject completely flat data (no elevation variation)
        if elevation_range < 1.0:
            return False, f"No elevation variation: {elevation_range}m range"

        # Accept data with reasonable elevation range, even if low unique percentage
        if elevation_range >= 10.0:  # At least 10m variation
            return True, f"Valid elevation range: {elevation_range}m"

        # For small elevation ranges, require higher unique percentage
        if elevation_range >= 5.0 and unique_percentage >= 5.0:
            return (
                True,
                f"Acceptable for small terrain: {elevation_range}m range, {unique_percentage:.2f}% unique",
            )

        return (
            False,
            f"Insufficient variation: {elevation_range}m range, {unique_percentage:.2f}% unique",
        )

    def _bounds_overlap(self, file_bounds, requested_bounds: GeographicBounds) -> bool:
        """
        Check if file bounds overlap with requested bounds.

        Args:
            file_bounds: Rasterio bounds object
            requested_bounds: Requested geographic bounds

        Returns:
            True if bounds overlap, False otherwise
        """
        # Convert file bounds to comparable format
        file_west, file_south, file_east, file_north = file_bounds

        # Check for overlap
        return not (
            requested_bounds.east < file_west
            or requested_bounds.west > file_east
            or requested_bounds.north < file_south
            or requested_bounds.south > file_north
        )

    async def _extract_elevation_data(
        self,
        dem_path: Path,
        bounds: GeographicBounds,
        grid_size: GridSize,
    ) -> ElevationData:
        """
        Extract elevation data from DEM file with coordinate system transformation support.

        Args:
            dem_path: Path to DEM file
            bounds: Geographic bounds (in WGS84)
            grid_size: Desired grid size

        Returns:
            Elevation data

        Raises:
            CoordinateTransformError: When coordinate transformation fails
            DataValidationError: When extracted data is invalid
        """
        # Parse grid size
        grid_width, grid_height = map(int, grid_size.value.split("x"))

        try:
            # Detect and open DEM file with appropriate format handler
            format_ext = self._detect_dem_format(dem_path)
            format_reader = self.supported_formats[format_ext]

            with format_reader(dem_path) as src:
                logger.info(
                    "Processing DEM file",
                    path=str(dem_path),
                    format=format_ext,
                    source_crs=str(src.crs),
                    source_bounds=src.bounds,
                    source_shape=src.shape,
                )

                # Handle coordinate system transformation if needed
                target_crs = CRS.from_epsg(4326)  # WGS84

                if src.crs != target_crs:
                    logger.info(
                        "Reprojecting DEM data",
                        source_crs=str(src.crs),
                        target_crs=str(target_crs),
                    )
                    elevation_array, _ = await self._reproject_dem_data(
                        src, bounds, grid_width, grid_height, target_crs
                    )
                else:
                    # Same CRS - extract and resample directly
                    elevation_array, _ = await self._extract_and_resample(
                        src, bounds, grid_width, grid_height
                    )

                # Validate extracted data
                await self._validate_extracted_data(elevation_array, bounds)

                # Convert to list format and calculate resolution
                elevation_grid = elevation_array.tolist()

                # Calculate resolution in meters per cell
                resolution = self._calculate_resolution(bounds, grid_width, grid_height)

                # Determine no-data value
                no_data_value = src.nodata if src.nodata is not None else -9999

                logger.info(
                    "Successfully extracted elevation data",
                    grid_shape=(grid_height, grid_width),
                    resolution_meters=resolution,
                    elevation_range=(np.min(elevation_array), np.max(elevation_array)),
                    no_data_value=no_data_value,
                )

                return ElevationData(
                    grid=elevation_grid,
                    resolution=resolution,
                    bounds=bounds,
                    no_data_value=no_data_value,
                )

        except Exception as e:
            logger.error(
                "Failed to extract elevation data",
                path=str(dem_path),
                bounds=bounds.model_dump(),
                error=str(e),
                exc_info=True,
            )
            raise TerrainDataError(
                f"Failed to extract elevation data: {e!s}",
                bounds=bounds,
                processing_step="data_extraction",
            ) from e

    async def _reproject_dem_data(
        self,
        src: rasterio.DatasetReader,
        bounds: GeographicBounds,
        grid_width: int,
        grid_height: int,
        target_crs: CRS,
    ) -> tuple[np.ndarray, rasterio.Affine]:
        """
        Reproject DEM data to target coordinate system and bounds.

        Args:
            src: Source rasterio dataset
            bounds: Target bounds in target CRS
            grid_width: Target grid width
            grid_height: Target grid height
            target_crs: Target coordinate reference system

        Returns:
            Tuple of (reprojected_array, transform)

        Raises:
            CoordinateTransformError: When reprojection fails
        """
        try:
            # Calculate transform for target bounds and grid size
            dst_transform, _, _ = calculate_default_transform(
                src.crs,
                target_crs,
                src.width,
                src.height,
                left=bounds.west,
                bottom=bounds.south,
                right=bounds.east,
                top=bounds.north,
            )

            # Override dimensions to match requested grid size
            dst_transform = rasterio.transform.from_bounds(
                bounds.west,
                bounds.south,
                bounds.east,
                bounds.north,
                grid_width,
                grid_height,
            )

            # Create output array
            destination = np.empty((grid_height, grid_width), dtype=np.float32)

            # Perform reprojection
            reproject(
                source=rasterio.band(src, 1),
                destination=destination,
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=dst_transform,
                dst_crs=target_crs,
                resampling=WarpResampling.bilinear,
                src_nodata=src.nodata,
                dst_nodata=src.nodata,
            )

            logger.info(
                "Successfully reprojected DEM data",
                source_crs=str(src.crs),
                target_crs=str(target_crs),
                output_shape=destination.shape,
            )

            return destination, dst_transform

        except Exception as e:
            logger.error(
                "Failed to reproject DEM data",
                source_crs=str(src.crs),
                target_crs=str(target_crs),
                error=str(e),
            )
            raise CoordinateTransformError(str(src.crs), str(target_crs), bounds) from e

    async def _extract_and_resample(
        self,
        src: rasterio.DatasetReader,
        bounds: GeographicBounds,
        grid_width: int,
        grid_height: int,
    ) -> tuple[np.ndarray, rasterio.Affine]:
        """
        Extract and resample DEM data without coordinate transformation.

        Args:
            src: Source rasterio dataset
            bounds: Geographic bounds
            grid_width: Target grid width
            grid_height: Target grid height

        Returns:
            Tuple of (resampled_array, transform)
        """
        # Create bounding box geometry
        bbox = box(bounds.west, bounds.south, bounds.east, bounds.north)

        # Mask the raster to the bounding box
        out_image, out_transform = mask(src, [bbox], crop=True)
        elevation_array = out_image[0]

        # Resample to desired grid size if needed
        if elevation_array.shape != (grid_height, grid_width):
            # Calculate new transform for resampling
            new_transform = rasterio.transform.from_bounds(
                bounds.west,
                bounds.south,
                bounds.east,
                bounds.north,
                grid_width,
                grid_height,
            )

            # Create output array
            resampled = np.empty((grid_height, grid_width), dtype=np.float32)

            # Reproject to new grid (same CRS, different resolution)
            reproject(
                elevation_array,
                resampled,
                src_transform=out_transform,
                src_crs=src.crs,
                dst_transform=new_transform,
                dst_crs=src.crs,
                resampling=WarpResampling.bilinear,
                src_nodata=src.nodata,
                dst_nodata=src.nodata,
            )

            elevation_array = resampled
            out_transform = new_transform

        return elevation_array, out_transform

    async def _validate_extracted_data(
        self, elevation_array: np.ndarray, bounds: GeographicBounds
    ) -> None:
        """
        Validate extracted elevation data.

        Args:
            elevation_array: Extracted elevation data
            bounds: Geographic bounds

        Raises:
            DataValidationError: When validation fails
        """
        validation_failures = []

        # Check for empty data
        if elevation_array.size == 0:
            validation_failures.append("Empty elevation array")

        # Check for all no-data values
        finite_values = elevation_array[np.isfinite(elevation_array)]
        if len(finite_values) == 0:
            validation_failures.append("No valid elevation values found")

        # Check elevation range
        if len(finite_values) > 0:
            min_elevation = np.min(finite_values)
            max_elevation = np.max(finite_values)

            if min_elevation < -500:
                validation_failures.append(
                    f"Minimum elevation too low: {min_elevation}m"
                )

            if max_elevation > 9000:
                validation_failures.append(
                    f"Maximum elevation too high: {max_elevation}m"
                )

            # Check for reasonable elevation variation
            elevation_range = max_elevation - min_elevation
            if elevation_range < 1:
                validation_failures.append(
                    f"Insufficient elevation variation: {elevation_range}m"
                )

        if validation_failures:
            raise DataValidationError(validation_failures, bounds)

    def _calculate_resolution(
        self, bounds: GeographicBounds, grid_width: int, grid_height: int
    ) -> float:
        """
        Calculate grid resolution in meters per cell.

        Args:
            bounds: Geographic bounds
            grid_width: Grid width in cells
            grid_height: Grid height in cells

        Returns:
            Resolution in meters per cell
        """
        # Calculate resolution in meters per cell
        lat_range = bounds.north - bounds.south
        lng_range = bounds.east - bounds.west

        # Convert degrees to meters (approximate)
        lat_resolution = (
            lat_range * 111000
        ) / grid_height  # ~111km per degree latitude
        lng_resolution = (
            lng_range
            * 111000
            * math.cos(math.radians((bounds.north + bounds.south) / 2))
        ) / grid_width  # Longitude varies with latitude

        # Return average resolution
        return (lat_resolution + lng_resolution) / 2

    def _detect_dem_format(self, dem_path: Path) -> str:
        """
        Detect DEM file format based on file extension and content.

        Args:
            dem_path: Path to DEM file

        Returns:
            Format identifier string

        Raises:
            TerrainDataError: When format cannot be determined
        """
        file_extension = dem_path.suffix.lower()

        if file_extension in self.supported_formats:
            logger.info(f"Detected DEM format: {file_extension}", path=str(dem_path))
            return file_extension

        # Try to detect format by content if extension is unknown
        try:
            with rasterio.open(dem_path):
                # If rasterio can open it, treat as GeoTIFF-compatible
                logger.info("Detected rasterio-compatible format", path=str(dem_path))
                return ".tif"
        except Exception:
            pass

        raise TerrainDataError(
            f"Unsupported DEM format: {file_extension}",
            processing_step="format_detection",
        )

    def _read_geotiff(self, dem_path: Path) -> rasterio.DatasetReader:
        """
        Read GeoTIFF format DEM file.

        Args:
            dem_path: Path to GeoTIFF file

        Returns:
            Rasterio dataset reader
        """
        return rasterio.open(dem_path)

    def _read_erdas_imagine(self, dem_path: Path) -> rasterio.DatasetReader:
        """
        Read ERDAS Imagine format DEM file.

        Args:
            dem_path: Path to IMG file

        Returns:
            Rasterio dataset reader
        """
        return rasterio.open(dem_path)

    def _read_srtm_hgt(self, dem_path: Path) -> rasterio.DatasetReader:
        """
        Read SRTM HGT format DEM file.

        Args:
            dem_path: Path to HGT file

        Returns:
            Rasterio dataset reader
        """
        return rasterio.open(dem_path)

    def _read_ascii_grid(self, dem_path: Path) -> rasterio.DatasetReader:
        """
        Read ASCII Grid format DEM file.

        Args:
            dem_path: Path to ASC file

        Returns:
            Rasterio dataset reader
        """
        return rasterio.open(dem_path)

    def _read_bil(self, dem_path: Path) -> rasterio.DatasetReader:
        """
        Read BIL (Band Interleaved by Line) format DEM file.

        Args:
            dem_path: Path to BIL file

        Returns:
            Rasterio dataset reader
        """
        return rasterio.open(dem_path)

    def _read_float_grid(self, dem_path: Path) -> rasterio.DatasetReader:
        """
        Read Float Grid format DEM file.

        Args:
            dem_path: Path to FLT file

        Returns:
            Rasterio dataset reader
        """
        return rasterio.open(dem_path)

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
    ) -> tuple[SurfaceType, float]:
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
        elif slope > 20:
            # Check for moguls based on elevation variation
            return SurfaceType.MOGULS, 0.6
        elif slope > 15:
            return SurfaceType.PACKED, 0.7
        elif elevation > 2500:
            return SurfaceType.POWDER, 0.8
        elif slope < 5:
            return SurfaceType.TREES, 0.5
        else:
            return SurfaceType.PACKED, 0.7

    def get_data_source_status(self) -> dict:
        """Get status of all available data sources."""
        return self.data_source_manager.get_source_status()

    async def validate_data_sources(self) -> dict:
        """Validate that data sources are accessible."""
        status = self.get_data_source_status()
        validation_results = {}

        for source_name, source_info in status.items():
            validation_results[source_name] = {
                "configured": True,
                "has_credentials": source_info["has_api_key"],
                "status": source_info["status"],
                "accessible": source_info["status"] == "available",
            }

        return validation_results
