"""Integration tests for terrain processor with real DEM data processing."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

import numpy as np
import pytest
import rasterio
import structlog
from rasterio.crs import CRS
from rasterio.transform import from_bounds

from agents.hill_metrics.models import GeographicBounds
from agents.hill_metrics.models import GridSize
from agents.hill_metrics.terrain_processor import CoordinateTransformError
from agents.hill_metrics.terrain_processor import DataValidationError
from agents.hill_metrics.terrain_processor import DEMProcessor
from agents.hill_metrics.terrain_processor import TerrainDataError

logger = structlog.get_logger(__name__)


class TestDEMProcessorIntegration:
    """Integration tests for DEM processor with real data processing."""

    @pytest.fixture
    def processor(self):
        """Create DEM processor for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir) / "cache"
            yield DEMProcessor(cache_dir=cache_dir)

    @pytest.fixture
    def sample_bounds(self):
        """Sample geographic bounds for testing."""
        return GeographicBounds(north=46.0, south=45.9, east=7.8, west=7.7)

    @pytest.fixture
    def sample_dem_file(self):
        """Create a sample DEM file for testing."""
        with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmp_file:
            dem_path = Path(tmp_file.name)

        # Create sample elevation data
        width, height = 100, 100
        elevation_data = np.random.uniform(1000, 3000, (height, width)).astype(
            np.float32
        )

        # Add some realistic terrain features
        x, y = np.meshgrid(
            np.linspace(0, 2 * np.pi, width), np.linspace(0, 2 * np.pi, height)
        )
        elevation_data += 500 * np.sin(x) * np.cos(y)  # Add terrain variation

        # Create GeoTIFF
        bounds = GeographicBounds(north=46.0, south=45.9, east=7.8, west=7.7)
        transform = from_bounds(
            bounds.west, bounds.south, bounds.east, bounds.north, width, height
        )

        with rasterio.open(
            dem_path,
            "w",
            driver="GTiff",
            height=height,
            width=width,
            count=1,
            dtype=elevation_data.dtype,
            crs="EPSG:4326",
            transform=transform,
        ) as dst:
            dst.write(elevation_data, 1)

        yield dem_path

        # Cleanup
        if dem_path.exists():
            dem_path.unlink()

    @pytest.mark.asyncio
    async def test_process_terrain_with_real_data(
        self, processor, sample_bounds, sample_dem_file
    ):
        """Test complete terrain processing with real DEM data."""
        # Mock data source manager to return our sample file
        mock_data_source_info = MagicMock()
        mock_data_source_info.name = "test_source"
        mock_data_source_info.estimated_resolution = 30.0

        with patch.object(
            processor.data_source_manager, "fetch_dem_data"
        ) as mock_fetch:
            mock_fetch.return_value = mock_data_source_info

            # Mock cache key generation to return predictable key
            cache_key = "test_cache_key"
            with patch(
                "agents.hill_metrics.terrain_processor.generate_cache_key",
                return_value=cache_key,
            ):
                # Ensure cache file doesn't exist initially
                expected_path = processor.cache_dir / f"dem_{cache_key}.tif"
                if expected_path.exists():
                    expected_path.unlink()

                # Mock the fetch to copy our sample file
                def mock_fetch_side_effect(bounds, output_path):
                    import shutil

                    shutil.copy2(sample_dem_file, output_path)
                    return mock_data_source_info

                mock_fetch.side_effect = mock_fetch_side_effect

                result = await processor.process_terrain(
                    bounds=sample_bounds,
                    grid_size=GridSize.MEDIUM,
                    include_surface_classification=True,
                )

                # Verify result structure
                assert result is not None
                assert result.elevation is not None
                assert result.slope is not None
                assert result.aspect is not None
                assert result.surface_classification is not None

                # Verify elevation data
                assert len(result.elevation.grid) == 64  # MEDIUM grid size
                assert len(result.elevation.grid[0]) == 64
                assert result.elevation.resolution > 0
                assert result.elevation.bounds == sample_bounds

                # Verify slope data
                assert len(result.slope.grid) == 64
                assert len(result.slope.grid[0]) == 64
                assert all(
                    0 <= slope <= 90 for row in result.slope.grid for slope in row
                )

                # Verify aspect data
                assert len(result.aspect.grid) == 64
                assert len(result.aspect.grid[0]) == 64
                assert all(
                    0 <= aspect < 360 for row in result.aspect.grid for aspect in row
                )

                # Verify metadata
                assert "processing_time_ms" in result.metadata
                assert "data_source" in result.metadata
                assert result.metadata["data_source"] == "test_source"

    @pytest.mark.asyncio
    async def test_coordinate_system_transformation(self, processor, sample_bounds):
        """Test coordinate system transformation during DEM processing."""
        # Create DEM file in different CRS (UTM Zone 32N)
        with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmp_file:
            dem_path = Path(tmp_file.name)

        try:
            # Create sample data in UTM coordinates
            width, height = 50, 50
            elevation_data = np.random.uniform(1000, 2000, (height, width)).astype(
                np.float32
            )

            # UTM Zone 32N bounds (approximate for the sample_bounds area)
            utm_transform = from_bounds(400000, 5080000, 410000, 5090000, width, height)

            with rasterio.open(
                dem_path,
                "w",
                driver="GTiff",
                height=height,
                width=width,
                count=1,
                dtype=elevation_data.dtype,
                crs="EPSG:32632",  # UTM Zone 32N
                transform=utm_transform,
            ) as dst:
                dst.write(elevation_data, 1)

            # Test extraction with coordinate transformation
            result = await processor._extract_elevation_data(
                dem_path, sample_bounds, GridSize.SMALL
            )

            # Verify result
            assert result is not None
            assert len(result.grid) == 32  # SMALL grid size
            assert len(result.grid[0]) == 32
            assert result.bounds == sample_bounds
            assert result.resolution > 0

        finally:
            if dem_path.exists():
                dem_path.unlink()

    @pytest.mark.asyncio
    async def test_dem_file_validation(self, processor, sample_bounds):
        """Test DEM file validation functionality."""
        # Test valid file
        with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmp_file:
            valid_dem_path = Path(tmp_file.name)

        try:
            # Create valid DEM file
            width, height = 50, 50
            elevation_data = np.random.uniform(1000, 2000, (height, width)).astype(
                np.float32
            )
            transform = from_bounds(
                sample_bounds.west,
                sample_bounds.south,
                sample_bounds.east,
                sample_bounds.north,
                width,
                height,
            )

            with rasterio.open(
                valid_dem_path,
                "w",
                driver="GTiff",
                height=height,
                width=width,
                count=1,
                dtype=elevation_data.dtype,
                crs="EPSG:4326",
                transform=transform,
            ) as dst:
                dst.write(elevation_data, 1)

            # Test validation
            is_valid = await processor._validate_dem_file(valid_dem_path, sample_bounds)
            assert is_valid is True

        finally:
            if valid_dem_path.exists():
                valid_dem_path.unlink()

        # Test invalid file (no CRS)
        with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmp_file:
            invalid_dem_path = Path(tmp_file.name)

        try:
            # Create invalid DEM file (no CRS)
            elevation_data = np.random.uniform(1000, 2000, (50, 50)).astype(np.float32)
            transform = from_bounds(
                sample_bounds.west,
                sample_bounds.south,
                sample_bounds.east,
                sample_bounds.north,
                50,
                50,
            )

            with rasterio.open(
                invalid_dem_path,
                "w",
                driver="GTiff",
                height=50,
                width=50,
                count=1,
                dtype=elevation_data.dtype,
                crs=None,  # No CRS
                transform=transform,
            ) as dst:
                dst.write(elevation_data, 1)

            # Test validation
            is_valid = await processor._validate_dem_file(
                invalid_dem_path, sample_bounds
            )
            assert is_valid is False

        finally:
            if invalid_dem_path.exists():
                invalid_dem_path.unlink()

    @pytest.mark.asyncio
    async def test_data_validation_errors(self, processor, sample_bounds):
        """Test data validation error handling."""
        # Create DEM with invalid elevation values
        with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmp_file:
            dem_path = Path(tmp_file.name)

        try:
            # Create DEM with unrealistic elevation values
            width, height = 50, 50
            elevation_data = np.full(
                (height, width), 15000.0, dtype=np.float32
            )  # Too high
            transform = from_bounds(
                sample_bounds.west,
                sample_bounds.south,
                sample_bounds.east,
                sample_bounds.north,
                width,
                height,
            )

            with rasterio.open(
                dem_path,
                "w",
                driver="GTiff",
                height=height,
                width=width,
                count=1,
                dtype=elevation_data.dtype,
                crs="EPSG:4326",
                transform=transform,
            ) as dst:
                dst.write(elevation_data, 1)

            # Test that validation fails
            is_valid = await processor._validate_dem_file(dem_path, sample_bounds)
            assert is_valid is False

        finally:
            if dem_path.exists():
                dem_path.unlink()

    @pytest.mark.asyncio
    async def test_format_detection(self, processor):
        """Test DEM format detection."""
        # Test GeoTIFF detection
        with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmp_file:
            tif_path = Path(tmp_file.name)

        try:
            format_ext = processor._detect_dem_format(tif_path)
            assert format_ext == ".tif"
        finally:
            if tif_path.exists():
                tif_path.unlink()

        # Test IMG detection
        with tempfile.NamedTemporaryFile(suffix=".img", delete=False) as tmp_file:
            img_path = Path(tmp_file.name)

        try:
            format_ext = processor._detect_dem_format(img_path)
            assert format_ext == ".img"
        finally:
            if img_path.exists():
                img_path.unlink()

        # Test unsupported format
        with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as tmp_file:
            xyz_path = Path(tmp_file.name)

        try:
            with pytest.raises(TerrainDataError) as exc_info:
                processor._detect_dem_format(xyz_path)
            assert "Unsupported DEM format" in str(exc_info.value)
        finally:
            if xyz_path.exists():
                xyz_path.unlink()

    @pytest.mark.asyncio
    async def test_error_handling_no_data_sources(self, processor, sample_bounds):
        """Test error handling when no data sources are available."""
        # Mock data source manager to return None
        with patch.object(
            processor.data_source_manager, "fetch_dem_data", return_value=None
        ):
            with pytest.raises(TerrainDataError) as exc_info:
                await processor.process_terrain(sample_bounds, GridSize.MEDIUM)

            assert "No valid DEM data sources available" in str(exc_info.value)
            assert exc_info.value.bounds == sample_bounds
            assert exc_info.value.processing_step == "data_acquisition"

    @pytest.mark.asyncio
    async def test_error_handling_invalid_data(self, processor, sample_bounds):
        """Test error handling when data source returns invalid data."""
        # Mock data source manager to return info but create invalid file
        mock_data_source_info = MagicMock()
        mock_data_source_info.name = "test_source"
        mock_data_source_info.estimated_resolution = 30.0

        with patch.object(
            processor.data_source_manager, "fetch_dem_data"
        ) as mock_fetch:
            mock_fetch.return_value = mock_data_source_info

            # Mock validation to fail
            with patch.object(processor, "_validate_dem_file", return_value=False):
                with pytest.raises(TerrainDataError) as exc_info:
                    await processor.process_terrain(sample_bounds, GridSize.MEDIUM)

                assert "Invalid DEM data from test_source" in str(exc_info.value)
                assert exc_info.value.processing_step == "data_validation"

    @pytest.mark.asyncio
    async def test_coordinate_transform_error(self, processor, sample_bounds):
        """Test coordinate transformation error handling."""
        # Create a mock that raises an exception during reprojection
        with patch("agents.hill_metrics.terrain_processor.reproject") as mock_reproject:
            mock_reproject.side_effect = Exception("Reprojection failed")

            # Create a mock dataset with different CRS
            mock_src = MagicMock()
            mock_src.crs = CRS.from_epsg(32632)  # UTM
            mock_src.transform = from_bounds(400000, 5080000, 410000, 5090000, 50, 50)

            with pytest.raises(CoordinateTransformError) as exc_info:
                await processor._reproject_dem_data(
                    mock_src, sample_bounds, 32, 32, CRS.from_epsg(4326)
                )

            assert exc_info.value.source_crs == "EPSG:32632"
            assert exc_info.value.target_crs == "EPSG:4326"

    @pytest.mark.asyncio
    async def test_resolution_calculation(self, processor):
        """Test resolution calculation accuracy."""
        bounds = GeographicBounds(north=46.0, south=45.0, east=8.0, west=7.0)

        # Test different grid sizes
        resolution_32 = processor._calculate_resolution(bounds, 32, 32)
        resolution_64 = processor._calculate_resolution(bounds, 64, 64)

        # Higher grid size should result in finer resolution (smaller meters per cell)
        assert resolution_64 < resolution_32
        assert resolution_32 > 0
        assert resolution_64 > 0

    @pytest.mark.asyncio
    async def test_extracted_data_validation(self, processor, sample_bounds):
        """Test validation of extracted elevation data."""
        # Test valid data
        valid_data = np.random.uniform(1000, 2000, (32, 32)).astype(np.float32)
        await processor._validate_extracted_data(
            valid_data, sample_bounds
        )  # Should not raise

        # Test empty data
        empty_data = np.array([])
        with pytest.raises(DataValidationError) as exc_info:
            await processor._validate_extracted_data(empty_data, sample_bounds)
        assert "Empty elevation array" in exc_info.value.validation_failures

        # Test all no-data values
        nodata_array = np.full((32, 32), np.nan)
        with pytest.raises(DataValidationError) as exc_info:
            await processor._validate_extracted_data(nodata_array, sample_bounds)
        assert "No valid elevation values found" in exc_info.value.validation_failures

        # Test unrealistic elevation values
        high_elevation_data = np.full((32, 32), 15000.0)  # Too high
        with pytest.raises(DataValidationError) as exc_info:
            await processor._validate_extracted_data(high_elevation_data, sample_bounds)
        assert any(
            "too high" in failure for failure in exc_info.value.validation_failures
        )

        low_elevation_data = np.full((32, 32), -1000.0)  # Too low
        with pytest.raises(DataValidationError) as exc_info:
            await processor._validate_extracted_data(low_elevation_data, sample_bounds)
        assert any(
            "too low" in failure for failure in exc_info.value.validation_failures
        )

        # Test insufficient variation
        flat_data = np.full((32, 32), 1000.0)  # All same value
        with pytest.raises(DataValidationError) as exc_info:
            await processor._validate_extracted_data(flat_data, sample_bounds)
        assert any(
            "Insufficient elevation variation" in failure
            for failure in exc_info.value.validation_failures
        )


@pytest.mark.integration
class TestRealDataSourceIntegration:
    """Integration tests with real data sources (when available)."""

    @pytest.fixture
    def processor(self):
        """Create DEM processor for integration testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir) / "cache"
            yield DEMProcessor(cache_dir=cache_dir)

    @pytest.mark.asyncio
    async def test_ski_area_processing(self, processor):
        """Test processing of actual ski area bounds."""
        # Test with small area to avoid large downloads
        ski_areas = {
            "small_chamonix": GeographicBounds(
                north=45.925, south=45.920, east=6.875, west=6.870
            ),
            "small_zermatt": GeographicBounds(
                north=46.005, south=46.000, east=7.755, west=7.750
            ),
        }

        for area_name, bounds in ski_areas.items():
            try:
                # This will attempt to use real data sources if available
                result = await processor.process_terrain(
                    bounds=bounds,
                    grid_size=GridSize.SMALL,  # Use small grid to minimize processing time
                    include_surface_classification=True,
                )

                # Verify basic result structure
                assert result is not None
                assert result.elevation is not None
                assert len(result.elevation.grid) == 32
                assert len(result.elevation.grid[0]) == 32

                # Verify realistic elevation values for ski areas
                elevation_array = np.array(result.elevation.grid)
                min_elevation = np.min(elevation_array)
                max_elevation = np.max(elevation_array)

                # Ski areas should have reasonable elevation ranges
                assert 500 <= min_elevation <= 4000
                assert 1000 <= max_elevation <= 5000
                assert max_elevation > min_elevation

                logger.info(
                    f"Successfully processed {area_name}",
                    elevation_range=(min_elevation, max_elevation),
                    data_source=result.metadata.get("data_source", "unknown"),
                )

            except TerrainDataError as e:
                # Log but don't fail test if data sources are unavailable
                logger.warning(f"Could not process {area_name}: {e}")
                pytest.skip(f"Data sources unavailable for {area_name}")

    @pytest.mark.asyncio
    async def test_data_source_validation(self, processor):
        """Test validation of real data sources."""
        validation_results = await processor.validate_data_sources()

        # Should return status for all configured sources
        assert isinstance(validation_results, dict)
        assert len(validation_results) > 0

        # Each source should have validation info
        for source_name, validation_info in validation_results.items():
            assert "configured" in validation_info
            assert "has_credentials" in validation_info
            assert "status" in validation_info
            assert "accessible" in validation_info

            logger.info(f"Data source validation: {source_name}", **validation_info)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
