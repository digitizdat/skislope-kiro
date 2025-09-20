"""Tests for Equipment Agent."""

import pytest

from agents.equipment.equipment_service import EquipmentService
from agents.equipment.models import EquipmentRequest
from agents.equipment.models import FacilityType
from agents.equipment.models import LiftType
from agents.equipment.models import TrailDifficulty


class TestEquipmentService:
    """Test cases for equipment service."""

    @pytest.fixture
    def equipment_service(self):
        """Create an equipment service instance."""
        return EquipmentService()

    @pytest.fixture
    def sample_request(self):
        """Sample equipment request."""
        return EquipmentRequest(
            north=46.0,
            south=45.9,
            east=7.1,
            west=7.0,
            include_lifts=True,
            include_trails=True,
            include_facilities=True,
            include_safety_equipment=True,
        )

    @pytest.mark.asyncio
    async def test_get_equipment_data_basic(self, equipment_service, sample_request):
        """Test basic equipment data retrieval."""
        result = await equipment_service.get_equipment_data(sample_request)

        assert result is not None
        assert "lifts" in result
        assert "trails" in result
        assert "facilities" in result
        assert "safety_equipment" in result
        assert "bounds" in result
        assert "processing_time_ms" in result

        # Check that we got some data
        assert len(result["lifts"]) > 0
        assert len(result["trails"]) > 0
        assert len(result["facilities"]) > 0
        assert len(result["safety_equipment"]) > 0

    @pytest.mark.asyncio
    async def test_get_equipment_data_filtered(self, equipment_service):
        """Test equipment data with filters."""
        request = EquipmentRequest(
            north=46.0,
            south=45.9,
            east=7.1,
            west=7.0,
            include_lifts=True,
            include_trails=False,
            include_facilities=False,
            include_safety_equipment=False,
            operational_only=True,
        )

        result = await equipment_service.get_equipment_data(request)

        assert len(result["lifts"]) > 0
        assert len(result["trails"]) == 0
        assert len(result["facilities"]) == 0
        assert len(result["safety_equipment"]) == 0

        # All lifts should be operational
        for lift in result["lifts"]:
            assert lift["status"] == "operational"

    @pytest.mark.asyncio
    async def test_cache_functionality(self, equipment_service, sample_request):
        """Test that caching works correctly."""
        # First call
        result1 = await equipment_service.get_equipment_data(sample_request)

        # Second call should use cache
        result2 = await equipment_service.get_equipment_data(sample_request)

        # Results should be identical
        assert len(result1["lifts"]) == len(result2["lifts"])
        assert len(result1["trails"]) == len(result2["trails"])
        assert len(result1["facilities"]) == len(result2["facilities"])

    def test_identify_ski_area(self, equipment_service):
        """Test ski area identification."""
        # Test Chamonix bounds
        chamonix_request = EquipmentRequest(
            north=45.95,
            south=45.85,
            east=6.95,
            west=6.85,
        )

        ski_area = equipment_service._identify_ski_area(chamonix_request)
        assert ski_area is not None
        assert ski_area["name"] == "Chamonix"

        # Test unknown area
        unknown_request = EquipmentRequest(
            north=0.1,
            south=0.0,
            east=0.1,
            west=0.0,
        )

        ski_area = equipment_service._identify_ski_area(unknown_request)
        assert ski_area is None

    @pytest.mark.asyncio
    async def test_generate_lifts(self, equipment_service, sample_request):
        """Test lift generation."""
        ski_area = equipment_service.ski_areas["chamonix"]
        lifts = await equipment_service._generate_lifts(sample_request, ski_area)

        assert len(lifts) > 0

        for lift in lifts:
            assert lift.id is not None
            assert lift.name is not None
            assert isinstance(lift.type, LiftType)
            assert lift.capacity_per_hour > 0
            assert lift.vertical_rise_m > 0
            assert lift.length_m > 0
            assert lift.ride_time_minutes > 0

            # Check coordinates are within bounds
            assert sample_request.south <= lift.base_latitude <= sample_request.north
            assert sample_request.west <= lift.base_longitude <= sample_request.east
            assert sample_request.south <= lift.top_latitude <= sample_request.north
            assert sample_request.west <= lift.top_longitude <= sample_request.east

    @pytest.mark.asyncio
    async def test_generate_trails(self, equipment_service, sample_request):
        """Test trail generation."""
        ski_area = equipment_service.ski_areas["chamonix"]
        trails = await equipment_service._generate_trails(sample_request, ski_area)

        assert len(trails) > 0

        for trail in trails:
            assert trail.id is not None
            assert trail.name is not None
            assert isinstance(trail.difficulty, TrailDifficulty)
            assert trail.length_m > 0
            assert trail.vertical_drop_m > 0
            assert trail.width_m > 0

            # Check coordinates are within bounds
            assert sample_request.south <= trail.start_latitude <= sample_request.north
            assert sample_request.west <= trail.start_longitude <= sample_request.east
            assert sample_request.south <= trail.end_latitude <= sample_request.north
            assert sample_request.west <= trail.end_longitude <= sample_request.east

            # Start elevation should be higher than end elevation
            assert trail.start_elevation_m > trail.end_elevation_m

    @pytest.mark.asyncio
    async def test_generate_facilities(self, equipment_service, sample_request):
        """Test facility generation."""
        ski_area = equipment_service.ski_areas["chamonix"]
        facilities = await equipment_service._generate_facilities(
            sample_request, ski_area
        )

        assert len(facilities) > 0

        for facility in facilities:
            assert facility.id is not None
            assert facility.name is not None
            assert isinstance(facility.type, FacilityType)

            # Check coordinates are within bounds
            assert sample_request.south <= facility.latitude <= sample_request.north
            assert sample_request.west <= facility.longitude <= sample_request.east

            # Check operating hours
            assert isinstance(facility.operating_hours, dict)

    @pytest.mark.asyncio
    async def test_generate_safety_equipment(self, equipment_service, sample_request):
        """Test safety equipment generation."""
        ski_area = equipment_service.ski_areas["chamonix"]
        safety_equipment = await equipment_service._generate_safety_equipment(
            sample_request, ski_area
        )

        assert len(safety_equipment) > 0

        for equipment in safety_equipment:
            assert equipment.id is not None
            assert equipment.type is not None

            # Check coordinates are within bounds
            assert sample_request.south <= equipment.latitude <= sample_request.north
            assert sample_request.west <= equipment.longitude <= sample_request.east

            # Check operational status
            assert isinstance(equipment.is_operational, bool)


class TestEquipmentModels:
    """Test cases for equipment data models."""

    def test_equipment_request_validation(self):
        """Test equipment request validation."""
        # Valid request
        request = EquipmentRequest(
            north=46.0,
            south=45.0,
            east=7.0,
            west=6.0,
        )
        assert request.north == 46.0
        assert request.south == 45.0

        # Invalid coordinates (should raise validation error)
        with pytest.raises(ValueError):
            EquipmentRequest(
                north=100.0,  # Invalid latitude
                south=45.0,
                east=7.0,
                west=6.0,
            )

    def test_equipment_request_defaults(self):
        """Test equipment request default values."""
        request = EquipmentRequest(
            north=46.0,
            south=45.0,
            east=7.0,
            west=6.0,
        )

        assert request.include_lifts is True
        assert request.include_trails is True
        assert request.include_facilities is True
        assert request.include_safety_equipment is True
        assert request.operational_only is False
        assert request.open_trails_only is False

    def test_lift_info_validation(self):
        """Test lift info validation."""
        from agents.equipment.models import LiftInfo
        from agents.equipment.models import LiftStatus

        # Valid lift info
        lift = LiftInfo(
            id="lift_001",
            name="Test Chairlift",
            type=LiftType.CHAIRLIFT,
            status=LiftStatus.OPERATIONAL,
            capacity_per_hour=2000,
            vertical_rise_m=500,
            length_m=1200,
            ride_time_minutes=8.5,
            base_latitude=46.0,
            base_longitude=7.0,
            base_elevation_m=1500,
            top_latitude=46.01,
            top_longitude=7.01,
            top_elevation_m=2000,
        )

        assert lift.id == "lift_001"
        assert lift.type == LiftType.CHAIRLIFT
        assert lift.capacity_per_hour == 2000

        # Invalid lift info (should raise validation error)
        with pytest.raises(ValueError):
            LiftInfo(
                id="lift_001",
                name="Test Chairlift",
                type=LiftType.CHAIRLIFT,
                status=LiftStatus.OPERATIONAL,
                capacity_per_hour=0,  # Invalid capacity
                vertical_rise_m=500,
                length_m=1200,
                ride_time_minutes=8.5,
                base_latitude=46.0,
                base_longitude=7.0,
                base_elevation_m=1500,
                top_latitude=46.01,
                top_longitude=7.01,
                top_elevation_m=2000,
            )
