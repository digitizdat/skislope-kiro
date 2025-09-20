"""Equipment data processing and management service."""
# Note: Uses random for simulation data generation, not cryptographic purposes

import random
import time
from datetime import datetime
from datetime import timedelta

import structlog

from agents.equipment.models import EquipmentRequest
from agents.equipment.models import FacilityInfo
from agents.equipment.models import FacilityType
from agents.equipment.models import LiftInfo
from agents.equipment.models import LiftStatus
from agents.equipment.models import LiftType
from agents.equipment.models import SafetyEquipment
from agents.equipment.models import SafetyEquipmentType
from agents.equipment.models import TrailDifficulty
from agents.equipment.models import TrailInfo
from agents.equipment.models import TrailStatus
from agents.shared.utils import CacheManager
from agents.shared.utils import generate_cache_key
from agents.shared.utils import validate_coordinates

logger = structlog.get_logger(__name__)


class EquipmentService:
    """Equipment data service for ski infrastructure management."""

    def __init__(self):
        self.cache_manager = CacheManager(default_ttl=1800)  # 30 minutes cache

        # Predefined ski areas with their bounds
        self.ski_areas = {
            "chamonix": {
                "name": "Chamonix",
                "bounds": {"north": 45.95, "south": 45.85, "east": 6.95, "west": 6.85},
                "base_elevation": 1035,
                "top_elevation": 3842,
            },
            "whistler": {
                "name": "Whistler",
                "bounds": {
                    "north": 50.15,
                    "south": 50.05,
                    "east": -122.85,
                    "west": -122.95,
                },
                "base_elevation": 675,
                "top_elevation": 2284,
            },
            "st_anton": {
                "name": "Saint Anton am Arlberg",
                "bounds": {
                    "north": 47.15,
                    "south": 47.05,
                    "east": 10.30,
                    "west": 10.20,
                },
                "base_elevation": 1304,
                "top_elevation": 2811,
            },
            "zermatt": {
                "name": "Zermatt",
                "bounds": {"north": 46.05, "south": 45.95, "east": 7.80, "west": 7.70},
                "base_elevation": 1620,
                "top_elevation": 3883,
            },
            "copper_mountain": {
                "name": "Copper Mountain",
                "bounds": {
                    "north": 39.55,
                    "south": 39.45,
                    "east": -106.10,
                    "west": -106.20,
                },
                "base_elevation": 2926,
                "top_elevation": 3962,
            },
        }

    async def get_equipment_data(self, request: EquipmentRequest) -> dict:
        """
        Get equipment data for the specified geographic bounds.

        Args:
            request: Equipment data request

        Returns:
            Equipment data dictionary
        """
        start_time = time.time()

        # Generate cache key
        cache_key = generate_cache_key(request.model_dump())

        # Check cache first
        cached_data = self.cache_manager.get(cache_key)
        if cached_data:
            logger.info("Returning cached equipment data", cache_key=cache_key)
            return cached_data

        try:
            # Validate coordinates
            if not (
                validate_coordinates(request.north, request.east)
                and validate_coordinates(request.south, request.west)
            ):
                raise ValueError("Invalid coordinates in request")

            # Determine which ski area this request covers
            ski_area = self._identify_ski_area(request)

            # Generate equipment data
            lifts = []
            trails = []
            facilities = []
            safety_equipment = []

            if request.include_lifts:
                lifts = await self._generate_lifts(request, ski_area)

            if request.include_trails:
                trails = await self._generate_trails(request, ski_area)

            if request.include_facilities:
                facilities = await self._generate_facilities(request, ski_area)

            if request.include_safety_equipment:
                safety_equipment = await self._generate_safety_equipment(
                    request, ski_area
                )

            # Apply filters
            if request.operational_only:
                lifts = [
                    lift for lift in lifts if lift.status == LiftStatus.OPERATIONAL
                ]

            if request.open_trails_only:
                trails = [trail for trail in trails if trail.status == TrailStatus.OPEN]

            # Create response data
            response_data = {
                "lifts": [lift.model_dump() for lift in lifts],
                "trails": [trail.model_dump() for trail in trails],
                "facilities": [facility.model_dump() for facility in facilities],
                "safety_equipment": [
                    equipment.model_dump() for equipment in safety_equipment
                ],
                "bounds": {
                    "north": request.north,
                    "south": request.south,
                    "east": request.east,
                    "west": request.west,
                },
                "total_lifts": len(lifts),
                "operational_lifts": len(
                    [lift for lift in lifts if lift.status == LiftStatus.OPERATIONAL]
                ),
                "total_trails": len(trails),
                "open_trails": len([t for t in trails if t.status == TrailStatus.OPEN]),
                "last_updated": datetime.now(),
                "processing_time_ms": (time.time() - start_time) * 1000,
            }

            # Cache the result
            self.cache_manager.set(cache_key, response_data)

            logger.info(
                "Generated equipment data",
                ski_area=ski_area["name"] if ski_area else "Unknown",
                lifts=len(lifts),
                trails=len(trails),
                facilities=len(facilities),
                safety_equipment=len(safety_equipment),
                processing_time_ms=(time.time() - start_time) * 1000,
            )

            return response_data

        except Exception as e:
            logger.error(
                "Failed to get equipment data",
                request=request.model_dump(),
                error=str(e),
                exc_info=True,
            )
            raise

    def _identify_ski_area(self, request: EquipmentRequest) -> dict | None:
        """
        Identify which ski area the request covers.

        Args:
            request: Equipment request

        Returns:
            Ski area information or None
        """
        for _area_id, area_info in self.ski_areas.items():
            bounds = area_info["bounds"]

            # Check if request bounds overlap with ski area bounds
            if (
                request.south <= bounds["north"]
                and request.north >= bounds["south"]
                and request.west <= bounds["east"]
                and request.east >= bounds["west"]
            ):
                return area_info

        return None

    async def _generate_lifts(
        self,
        request: EquipmentRequest,
        ski_area: dict | None,
    ) -> list[LiftInfo]:
        """Generate lift data for the area."""

        lifts = []

        # Number of lifts based on area size
        area_size = abs(request.north - request.south) * abs(
            request.east - request.west
        )
        num_lifts = max(3, min(15, int(area_size * 1000)))

        base_elevation = ski_area["base_elevation"] if ski_area else 1500
        ski_area["top_elevation"] if ski_area else 3000

        for i in range(num_lifts):
            # Generate lift positions within bounds
            base_lat = random.uniform(request.south, request.north)
            base_lng = random.uniform(request.west, request.east)

            # Top station is typically higher up the mountain, but stay within bounds
            max_lat_offset = min(
                0.01, request.north - base_lat, base_lat - request.south
            )
            max_lng_offset = min(0.01, request.east - base_lng, base_lng - request.west)

            top_lat = base_lat + random.uniform(-max_lat_offset, max_lat_offset)
            top_lng = base_lng + random.uniform(-max_lng_offset, max_lng_offset)

            # Ensure top coordinates are still within bounds
            top_lat = max(request.south, min(request.north, top_lat))
            top_lng = max(request.west, min(request.east, top_lng))

            # Elevation difference
            base_elev = base_elevation + random.uniform(0, 500)
            top_elev = base_elev + random.uniform(200, 1000)

            # Lift characteristics
            lift_type = random.choice(list(LiftType))
            vertical_rise = top_elev - base_elev
            length = vertical_rise / random.uniform(0.3, 0.7)  # Slope factor

            # Capacity based on lift type
            capacity_map = {
                LiftType.CHAIRLIFT: random.randint(1200, 2400),
                LiftType.GONDOLA: random.randint(2000, 4000),
                LiftType.CABLE_CAR: random.randint(800, 1600),
                LiftType.T_BAR: random.randint(600, 1200),
                LiftType.PLATTER_LIFT: random.randint(400, 800),
                LiftType.MAGIC_CARPET: random.randint(800, 1200),
                LiftType.FUNICULAR: random.randint(1000, 2000),
            }

            # Status (most lifts operational)
            status = random.choices(
                list(LiftStatus),
                weights=[0.8, 0.1, 0.05, 0.03, 0.02],
            )[0]

            lift = LiftInfo(
                id=f"lift_{i + 1:03d}",
                name=f"{lift_type.value.replace('-', ' ').title()} {i + 1}",
                type=lift_type,
                status=status,
                capacity_per_hour=capacity_map[lift_type],
                vertical_rise_m=vertical_rise,
                length_m=length,
                ride_time_minutes=length / 200,  # Approximate ride time
                base_latitude=base_lat,
                base_longitude=base_lng,
                base_elevation_m=base_elev,
                top_latitude=top_lat,
                top_longitude=top_lng,
                top_elevation_m=top_elev,
                operating_hours={
                    "monday": "8:30-16:00",
                    "tuesday": "8:30-16:00",
                    "wednesday": "8:30-16:00",
                    "thursday": "8:30-16:00",
                    "friday": "8:30-16:00",
                    "saturday": "8:00-16:30",
                    "sunday": "8:00-16:30",
                },
                last_inspection=datetime.now() - timedelta(days=random.randint(1, 30)),
                next_maintenance=datetime.now()
                + timedelta(days=random.randint(30, 90)),
                heated_seats=lift_type in [LiftType.CHAIRLIFT, LiftType.GONDOLA]
                and random.random() > 0.5,
                weather_shield=lift_type in [LiftType.GONDOLA, LiftType.CABLE_CAR],
                beginner_friendly=lift_type
                in [LiftType.MAGIC_CARPET, LiftType.CHAIRLIFT],
            )

            lifts.append(lift)

        return lifts

    async def _generate_trails(
        self,
        request: EquipmentRequest,
        ski_area: dict | None,
    ) -> list[TrailInfo]:
        """Generate trail data for the area."""

        trails = []

        # Number of trails based on area size
        area_size = abs(request.north - request.south) * abs(
            request.east - request.west
        )
        num_trails = max(5, min(25, int(area_size * 2000)))

        base_elevation = ski_area["base_elevation"] if ski_area else 1500
        top_elevation = ski_area["top_elevation"] if ski_area else 3000

        for i in range(num_trails):
            # Generate trail path within bounds
            start_lat = random.uniform(request.south, request.north)
            start_lng = random.uniform(request.west, request.east)

            # End point is typically lower, but stay within bounds
            max_lat_offset = min(
                0.02, request.north - start_lat, start_lat - request.south
            )
            max_lng_offset = min(
                0.02, request.east - start_lng, start_lng - request.west
            )

            end_lat = start_lat + random.uniform(-max_lat_offset, max_lat_offset)
            end_lng = start_lng + random.uniform(-max_lng_offset, max_lng_offset)

            # Ensure end coordinates are still within bounds
            end_lat = max(request.south, min(request.north, end_lat))
            end_lng = max(request.west, min(request.east, end_lng))

            # Elevation (start higher than end)
            start_elev = random.uniform(base_elevation + 200, top_elevation)
            end_elev = random.uniform(base_elevation, start_elev - 100)

            vertical_drop = start_elev - end_elev

            # Trail characteristics
            difficulty = random.choice(list(TrailDifficulty))
            length = random.uniform(500, 3000)  # Trail length in meters

            # Grade based on difficulty
            grade_ranges = {
                TrailDifficulty.BEGINNER: (5, 15),
                TrailDifficulty.INTERMEDIATE: (15, 25),
                TrailDifficulty.ADVANCED: (25, 35),
                TrailDifficulty.EXPERT: (35, 50),
                TrailDifficulty.TERRAIN_PARK: (10, 30),
                TrailDifficulty.CROSS_COUNTRY: (2, 8),
            }

            min_grade, max_grade = grade_ranges[difficulty]
            average_grade = random.uniform(min_grade, max_grade)
            max_grade_val = average_grade + random.uniform(5, 15)

            # Status (most trails open)
            status = random.choices(
                list(TrailStatus),
                weights=[0.7, 0.1, 0.1, 0.05, 0.02, 0.02, 0.01],
            )[0]

            trail = TrailInfo(
                id=f"trail_{i + 1:03d}",
                name=f"Trail {i + 1}",
                difficulty=difficulty,
                status=status,
                length_m=length,
                vertical_drop_m=vertical_drop,
                average_grade_percent=average_grade,
                max_grade_percent=max_grade_val,
                start_latitude=start_lat,
                start_longitude=start_lng,
                start_elevation_m=start_elev,
                end_latitude=end_lat,
                end_longitude=end_lng,
                end_elevation_m=end_elev,
                width_m=random.uniform(15, 50),
                groomed=random.random() > 0.2,
                snowmaking=random.random() > 0.4,
                night_skiing=random.random() > 0.8,
                last_groomed=datetime.now() - timedelta(hours=random.randint(1, 48)),
                snow_depth_cm=random.uniform(20, 150)
                if random.random() > 0.1
                else None,
                surface_condition=random.choice(
                    [
                        "Packed powder",
                        "Machine groomed",
                        "Powder",
                        "Hard pack",
                        "Icy patches",
                    ]
                ),
                access_lifts=[
                    f"lift_{random.randint(1, 10):03d}"
                    for _ in range(random.randint(1, 3))
                ],
                connected_trails=[
                    f"trail_{random.randint(1, num_trails):03d}"
                    for _ in range(random.randint(0, 2))
                ],
            )

            trails.append(trail)

        return trails

    async def _generate_facilities(
        self,
        request: EquipmentRequest,
        ski_area: dict | None,
    ) -> list[FacilityInfo]:
        """Generate facility data for the area."""

        facilities = []

        # Number of facilities based on area size
        area_size = abs(request.north - request.south) * abs(
            request.east - request.west
        )
        num_facilities = max(3, min(12, int(area_size * 500)))

        base_elevation = ski_area["base_elevation"] if ski_area else 1500

        facility_types = [
            FacilityType.LODGE,
            FacilityType.RESTAURANT,
            FacilityType.CAFETERIA,
            FacilityType.BAR,
            FacilityType.SHOP,
            FacilityType.RENTAL,
            FacilityType.SKI_SCHOOL,
            FacilityType.FIRST_AID,
            FacilityType.PARKING,
            FacilityType.RESTROOM,
        ]

        for i in range(num_facilities):
            facility_type = random.choice(facility_types)

            # Position within bounds (facilities often near base)
            lat = random.uniform(request.south, request.north)
            lng = random.uniform(request.west, request.east)
            elevation = base_elevation + random.uniform(0, 300)

            # Capacity based on facility type
            capacity_map = {
                FacilityType.LODGE: random.randint(200, 800),
                FacilityType.RESTAURANT: random.randint(50, 200),
                FacilityType.CAFETERIA: random.randint(100, 300),
                FacilityType.BAR: random.randint(30, 100),
                FacilityType.SHOP: random.randint(20, 50),
                FacilityType.RENTAL: random.randint(50, 150),
                FacilityType.SKI_SCHOOL: random.randint(100, 300),
                FacilityType.FIRST_AID: random.randint(5, 20),
                FacilityType.PARKING: random.randint(100, 1000),
                FacilityType.RESTROOM: random.randint(10, 30),
            }

            amenities_map = {
                FacilityType.LODGE: ["WiFi", "Heating", "Lockers", "Seating area"],
                FacilityType.RESTAURANT: [
                    "Full menu",
                    "Alcohol service",
                    "Reservations",
                ],
                FacilityType.CAFETERIA: ["Quick service", "Hot drinks", "Snacks"],
                FacilityType.BAR: ["Alcohol service", "Après-ski", "Live music"],
                FacilityType.SHOP: ["Ski gear", "Souvenirs", "Clothing"],
                FacilityType.RENTAL: ["Ski rental", "Boot rental", "Helmet rental"],
                FacilityType.SKI_SCHOOL: [
                    "Group lessons",
                    "Private lessons",
                    "Kids programs",
                ],
                FacilityType.FIRST_AID: [
                    "Emergency care",
                    "Ski patrol",
                    "Medical supplies",
                ],
                FacilityType.PARKING: [
                    "Day parking",
                    "Season passes",
                    "Shuttle service",
                ],
                FacilityType.RESTROOM: ["Heated", "Baby changing", "Accessible"],
            }

            facility = FacilityInfo(
                id=f"facility_{i + 1:03d}",
                name=f"{facility_type.value.replace('-', ' ').title()} {i + 1}",
                type=facility_type,
                latitude=lat,
                longitude=lng,
                elevation_m=elevation,
                is_open=random.random() > 0.1,
                operating_hours={
                    "monday": "8:00-17:00",
                    "tuesday": "8:00-17:00",
                    "wednesday": "8:00-17:00",
                    "thursday": "8:00-17:00",
                    "friday": "8:00-18:00",
                    "saturday": "7:30-18:00",
                    "sunday": "7:30-18:00",
                },
                capacity=capacity_map.get(facility_type),
                amenities=amenities_map.get(facility_type, []),
                wheelchair_accessible=random.random() > 0.3,
                parking_available=facility_type
                in [FacilityType.LODGE, FacilityType.RESTAURANT, FacilityType.PARKING],
            )

            facilities.append(facility)

        return facilities

    async def _generate_safety_equipment(
        self,
        request: EquipmentRequest,
        ski_area: dict | None,
    ) -> list[SafetyEquipment]:
        """Generate safety equipment data for the area."""

        safety_equipment = []

        # Number of safety equipment based on area size
        area_size = abs(request.north - request.south) * abs(
            request.east - request.west
        )
        num_equipment = max(5, min(20, int(area_size * 1000)))

        equipment_types = list(SafetyEquipmentType)

        for i in range(num_equipment):
            equipment_type = random.choice(equipment_types)

            # Position within bounds
            lat = random.uniform(request.south, request.north)
            lng = random.uniform(request.west, request.east)
            elevation = random.uniform(1500, 3000)

            # Coverage radius based on equipment type
            coverage_map = {
                SafetyEquipmentType.AVALANCHE_BEACON: 100,
                SafetyEquipmentType.EMERGENCY_PHONE: 500,
                SafetyEquipmentType.FIRST_AID_STATION: 1000,
                SafetyEquipmentType.PATROL_HUT: 2000,
                SafetyEquipmentType.BOUNDARY_MARKER: 50,
                SafetyEquipmentType.WARNING_SIGN: 100,
                SafetyEquipmentType.CLOSURE_ROPE: 200,
                SafetyEquipmentType.SAFETY_NET: 50,
                SafetyEquipmentType.PADDING: 20,
            }

            equipment = SafetyEquipment(
                id=f"safety_{i + 1:03d}",
                type=equipment_type,
                latitude=lat,
                longitude=lng,
                elevation_m=elevation,
                is_operational=random.random() > 0.05,
                last_inspection=datetime.now() - timedelta(days=random.randint(1, 30)),
                next_maintenance=datetime.now()
                + timedelta(days=random.randint(30, 180)),
                coverage_radius_m=coverage_map.get(equipment_type),
                installation_date=datetime.now()
                - timedelta(days=random.randint(30, 3650)),
                associated_trail=f"trail_{random.randint(1, 20):03d}"
                if random.random() > 0.5
                else None,
                associated_lift=f"lift_{random.randint(1, 10):03d}"
                if random.random() > 0.7
                else None,
            )

            safety_equipment.append(equipment)

        return safety_equipment
