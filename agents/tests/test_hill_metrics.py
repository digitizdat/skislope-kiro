"""Tests for Hill Metrics Agent."""

import pytest

from agents.hill_metrics.models import GeographicBounds
from agents.hill_metrics.models import GridSize
from agents.hill_metrics.models import TerrainRequest
from agents.hill_metrics.terrain_processor import DEMProcessor


class TestDEMProcessor:
    """Test cases for DEM processor."""

    @pytest.fixture
    def dem_processor(self):
        """Create a DEM processor instance."""
        return DEMProcessor()

    @pytest.fixture
    def sample_bounds(self):
        """Sample geographic bounds."""
        return GeographicBounds(
            north=46.0,
            south=45.9,
            east=7.1,
            west=7.0,
        )

    @pytest.mark.asyncio
    async def test_process_terrain_basic(self, dem_processor, sample_bounds):
        """Test basic terrain processing."""
        result = await dem_processor.process_terrain(
            sample_bounds,
            GridSize.SMALL,
            include_surface_classification=False,
        )

        assert result is not None
        assert result.elevation is not None
        assert result.slope is not None
        assert result.aspect is not None
        assert len(result.elevation.grid) == 32  # 32x32 grid
        assert len(result.elevation.grid[0]) == 32

    @pytest.mark.asyncio
    async def test_process_terrain_with_surface_classification(
        self, dem_processor, sample_bounds
    ):
        """Test terrain processing with surface classification."""
        result = await dem_processor.process_terrain(
            sample_bounds,
            GridSize.MEDIUM,
            include_surface_classification=True,
        )

        assert result is not None
        assert result.surface_classification is not None
        assert len(result.surface_classification.grid) == 64  # 64x64 grid
        assert len(result.surface_classification.grid[0]) == 64

    @pytest.mark.asyncio
    async def test_cache_functionality(self, dem_processor, sample_bounds):
        """Test that caching works correctly."""
        # First call
        result1 = await dem_processor.process_terrain(
            sample_bounds,
            GridSize.SMALL,
            include_surface_classification=False,
        )

        # Second call should use cache
        result2 = await dem_processor.process_terrain(
            sample_bounds,
            GridSize.SMALL,
            include_surface_classification=False,
        )

        # Results should be identical
        assert result1.elevation.grid == result2.elevation.grid
        assert result1.slope.grid == result2.slope.grid
        assert result1.aspect.grid == result2.aspect.grid

    def test_classify_single_cell(self, dem_processor):
        """Test surface classification for a single cell."""
        # Test steep slope (should be rocks)
        surface_type, confidence = dem_processor._classify_single_cell(2000, 50, 180)
        assert surface_type.value == "rocks"
        assert confidence > 0.5

        # Test gentle slope (should be packed)
        surface_type, confidence = dem_processor._classify_single_cell(1500, 20, 90)
        assert surface_type.value == "packed"
        assert confidence > 0.5

        # Test high elevation (should be powder)
        surface_type, confidence = dem_processor._classify_single_cell(2800, 10, 45)
        assert surface_type.value == "powder"
        assert confidence > 0.5


class TestTerrainModels:
    """Test cases for terrain data models."""

    def test_geographic_bounds_validation(self):
        """Test geographic bounds validation."""
        # Valid bounds
        bounds = GeographicBounds(north=46.0, south=45.0, east=7.0, west=6.0)
        assert bounds.north == 46.0
        assert bounds.south == 45.0

        # Invalid bounds (should raise validation error)
        with pytest.raises(ValueError):
            GeographicBounds(
                north=100.0, south=45.0, east=7.0, west=6.0
            )  # Invalid latitude

    def test_terrain_request_defaults(self):
        """Test terrain request default values."""
        bounds = GeographicBounds(north=46.0, south=45.0, east=7.0, west=6.0)
        request = TerrainRequest(bounds=bounds)

        assert request.grid_size == GridSize.MEDIUM
        assert request.include_surface_classification is True
        assert request.include_safety_zones is False
        assert request.include_course_markers is False
