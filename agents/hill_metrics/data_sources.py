"""Data source management and API integrations for terrain data."""

import asyncio
import os
from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import aiohttp
import structlog

from agents.hill_metrics.models import GeographicBounds

logger = structlog.get_logger(__name__)


class DataSourcePriority(int, Enum):
    """Data source priority levels."""

    NATIONAL = 1  # National government sources (highest priority)
    REGIONAL = 2  # Regional sources (EU-DEM, etc.)
    GLOBAL = 3  # Global sources (SRTM, ASTER)


class DataSourceStatus(str, Enum):
    """Data source status."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"


@dataclass
class DataSourceConfig:
    """Configuration for a data source."""

    name: str
    api_endpoint: str
    api_key_env_var: str | None
    rate_limit_per_hour: int
    max_area_km2: float
    supported_formats: list[str]
    coordinate_systems: list[str]
    resolution_meters: float
    coverage_regions: list[str]
    priority: DataSourcePriority


@dataclass
class DataSourceInfo:
    """Information about a selected data source."""

    name: str
    config: DataSourceConfig
    status: DataSourceStatus
    estimated_resolution: float
    coverage_quality: float  # 0-1 score


class DEMDataSource(ABC):
    """Abstract base class for DEM data sources."""

    def __init__(self, config: DataSourceConfig):
        self.config = config
        self.status = DataSourceStatus.AVAILABLE
        self.last_request_time = 0
        self.request_count = 0

    @abstractmethod
    async def fetch_data(self, bounds: GeographicBounds, output_path: Path) -> bool:
        """
        Fetch DEM data for the given bounds.

        Args:
            bounds: Geographic bounds
            output_path: Path to save the data

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def check_coverage(self, bounds: GeographicBounds) -> float:
        """
        Check coverage quality for the given bounds.

        Args:
            bounds: Geographic bounds

        Returns:
            Coverage quality score (0-1)
        """
        pass

    def get_api_key(self) -> str | None:
        """Get API key from environment variable."""
        if self.config.api_key_env_var:
            return os.getenv(self.config.api_key_env_var)
        return None

    def is_rate_limited(self) -> bool:
        """Check if source is currently rate limited."""
        return self.status == DataSourceStatus.RATE_LIMITED


class OpenTopographySRTMSource(DEMDataSource):
    """OpenTopography SRTM data source (30m global coverage)."""

    async def fetch_data(self, bounds: GeographicBounds, output_path: Path) -> bool:
        """Fetch SRTM data from OpenTopography API."""
        try:
            api_key = self.get_api_key()
            if not api_key:
                logger.warning(
                    "No API key found for OpenTopography",
                    env_var=self.config.api_key_env_var,
                )
                return False
            else:
                logger.info("Loaded API key for OpenTopography")

            # Construct API URL for SRTM GL1 (30m) using correct OpenTopography API
            url = "https://portal.opentopography.org/API/globaldem"
            params = {
                "demtype": "SRTMGL1",  # Correct parameter name from API docs
                "south": bounds.south,
                "north": bounds.north,
                "west": bounds.west,
                "east": bounds.east,
                "outputFormat": "GTiff",
                "API_Key": api_key,
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        with open(output_path, "wb") as f:
                            async for chunk in response.content.iter_chunked(8192):
                                f.write(chunk)

                        logger.info(
                            "Successfully fetched SRTM data",
                            bounds=bounds.model_dump(),
                            output_path=str(output_path),
                        )
                        return True
                    elif response.status == 429:
                        self.status = DataSourceStatus.RATE_LIMITED
                        logger.warning("Rate limited by OpenTopography API")
                        return False
                    else:
                        logger.error(
                            "Failed to fetch SRTM data",
                            status=response.status,
                            response_text=await response.text(),
                        )
                        return False

        except Exception as e:
            logger.error("Error fetching SRTM data", error=str(e), exc_info=True)
            self.status = DataSourceStatus.ERROR
            return False

    def check_coverage(self, bounds: GeographicBounds) -> float:
        """SRTM has global coverage between 60°N and 56°S."""
        if bounds.north <= 60 and bounds.south >= -56:
            return 1.0  # Full coverage
        elif bounds.south >= 60 or bounds.north <= -56:
            return 0.0  # No coverage
        else:
            # Partial coverage - calculate overlap
            coverage_south = max(bounds.south, -56)
            coverage_north = min(bounds.north, 60)

            if coverage_north <= coverage_south:
                return 0.0

            covered_lat_range = coverage_north - coverage_south
            total_lat_range = bounds.north - bounds.south
            return covered_lat_range / total_lat_range


class USGS3DEPSource(DEMDataSource):
    """USGS 3DEP data source (10m US coverage)."""

    async def fetch_data(self, bounds: GeographicBounds, output_path: Path) -> bool:
        """Fetch USGS 3DEP data."""
        try:
            # USGS 3DEP API endpoint
            url = f"{self.config.api_endpoint}/3DEP"
            params = {
                "demtype": "3DEP",
                "south": bounds.south,
                "north": bounds.north,
                "west": bounds.west,
                "east": bounds.east,
                "outputFormat": "GTiff",
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        with open(output_path, "wb") as f:
                            async for chunk in response.content.iter_chunked(8192):
                                f.write(chunk)

                        logger.info(
                            "Successfully fetched USGS 3DEP data",
                            bounds=bounds.model_dump(),
                            output_path=str(output_path),
                        )
                        return True
                    elif response.status == 429:
                        self.status = DataSourceStatus.RATE_LIMITED
                        logger.warning("Rate limited by USGS API")
                        return False
                    else:
                        logger.error(
                            "Failed to fetch USGS 3DEP data",
                            status=response.status,
                            response_text=await response.text(),
                        )
                        return False

        except Exception as e:
            logger.error("Error fetching USGS 3DEP data", error=str(e), exc_info=True)
            self.status = DataSourceStatus.ERROR
            return False

    def check_coverage(self, bounds: GeographicBounds) -> float:
        """USGS 3DEP covers continental US, Alaska, Hawaii, and territories."""
        # Simplified coverage check for continental US
        if (
            bounds.west >= -125
            and bounds.east <= -66
            and bounds.south >= 20
            and bounds.north <= 50
        ):
            return 1.0  # Full coverage for continental US
        elif (
            bounds.west >= -180
            and bounds.east <= -129
            and bounds.south >= 51
            and bounds.north <= 72
        ):
            return 1.0  # Alaska coverage
        else:
            return 0.0  # No coverage outside US


class EUDEMSource(DEMDataSource):
    """EU-DEM data source (25m European coverage)."""

    async def fetch_data(self, bounds: GeographicBounds, output_path: Path) -> bool:
        """Fetch EU-DEM data from Copernicus Land Monitoring Service."""
        try:
            # EU-DEM is typically accessed through WCS services
            # This is a simplified implementation
            url = f"{self.config.api_endpoint}/wcs"
            params = {
                "service": "WCS",
                "version": "2.0.1",
                "request": "GetCoverage",
                "coverageId": "EU_DEM_V11",
                "format": "image/tiff",
            }
            # Add subset parameters separately to handle multiple values
            params["subset"] = [
                f"Lat({bounds.south},{bounds.north})",
                f"Long({bounds.west},{bounds.east})",
            ]

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        with open(output_path, "wb") as f:
                            async for chunk in response.content.iter_chunked(8192):
                                f.write(chunk)

                        logger.info(
                            "Successfully fetched EU-DEM data",
                            bounds=bounds.model_dump(),
                            output_path=str(output_path),
                        )
                        return True
                    else:
                        logger.error(
                            "Failed to fetch EU-DEM data",
                            status=response.status,
                            response_text=await response.text(),
                        )
                        return False

        except Exception as e:
            logger.error("Error fetching EU-DEM data", error=str(e), exc_info=True)
            self.status = DataSourceStatus.ERROR
            return False

    def check_coverage(self, bounds: GeographicBounds) -> float:
        """EU-DEM covers Europe and surrounding areas."""
        # Temporarily disable EU-DEM due to API issues
        # TODO: Fix EU-DEM API implementation
        return 0.0  # Disabled until API is fixed


class CredentialManager:
    """Secure credential management for API keys."""

    def __init__(self):
        self.credentials: dict[str, str] = {}
        self._load_credentials()

    def _load_credentials(self):
        """Load credentials from environment variables."""
        credential_mappings = {
            "OPENTOPOGRAPHY_API_KEY": "opentopography",
            "USGS_API_KEY": "usgs",
            "COPERNICUS_API_KEY": "copernicus",
            "SWISSTOPO_API_KEY": "swisstopo",
            "IGN_FRANCE_API_KEY": "ign_france",
        }

        for env_var, service in credential_mappings.items():
            credential = os.getenv(env_var)
            if credential:
                self.credentials[service] = credential
                logger.info(f"Loaded credentials for {service}")
            else:
                logger.debug(f"No credentials found for {service}")

    def get_credential(self, service: str) -> str | None:
        """Get API credential for service."""
        return self.credentials.get(service)

    def has_credential(self, service: str) -> bool:
        """Check if credential exists for service."""
        return service in self.credentials


class DataSourceManager:
    """Manages multiple DEM data sources with intelligent selection."""

    def __init__(self):
        self.credential_manager = CredentialManager()
        self.data_sources: dict[str, DEMDataSource] = {}
        self._initialize_data_sources()

    def _initialize_data_sources(self):
        """Initialize all available data sources."""

        # OpenTopography SRTM (Global)
        srtm_config = DataSourceConfig(
            name="OpenTopography SRTM",
            api_endpoint="https://portal.opentopography.org/API",
            api_key_env_var="OPENTOPOGRAPHY_API_KEY",
            rate_limit_per_hour=100,
            max_area_km2=1000,
            supported_formats=["GTiff"],
            coordinate_systems=["EPSG:4326"],
            resolution_meters=30.0,
            coverage_regions=["global"],
            priority=DataSourcePriority.GLOBAL,
        )
        self.data_sources["srtm"] = OpenTopographySRTMSource(srtm_config)

        # USGS 3DEP (US)
        usgs_config = DataSourceConfig(
            name="USGS 3DEP",
            api_endpoint="https://elevation.nationalmap.gov/arcgis/rest/services",
            api_key_env_var=None,  # Public API
            rate_limit_per_hour=1000,
            max_area_km2=100,
            supported_formats=["GTiff", "IMG"],
            coordinate_systems=["EPSG:4326", "EPSG:3857"],
            resolution_meters=10.0,
            coverage_regions=["usa"],
            priority=DataSourcePriority.NATIONAL,
        )
        self.data_sources["usgs_3dep"] = USGS3DEPSource(usgs_config)

        # EU-DEM (Europe)
        eudem_config = DataSourceConfig(
            name="EU-DEM",
            api_endpoint="https://land.copernicus.eu/imagery-in-situ/eu-dem",
            api_key_env_var="COPERNICUS_API_KEY",
            rate_limit_per_hour=200,
            max_area_km2=500,
            supported_formats=["GTiff"],
            coordinate_systems=["EPSG:4326", "EPSG:3035"],
            resolution_meters=25.0,
            coverage_regions=["europe"],
            priority=DataSourcePriority.REGIONAL,
        )
        self.data_sources["eu_dem"] = EUDEMSource(eudem_config)

    async def get_best_data_source(
        self, bounds: GeographicBounds
    ) -> DataSourceInfo | None:
        """
        Select the best available data source for the given bounds.

        Args:
            bounds: Geographic bounds

        Returns:
            Information about the best data source, or None if none available
        """
        candidates = []

        # Evaluate all data sources
        for name, source in self.data_sources.items():
            if source.is_rate_limited():
                continue

            coverage = source.check_coverage(bounds)
            if coverage > 0:
                candidates.append(
                    DataSourceInfo(
                        name=name,
                        config=source.config,
                        status=source.status,
                        estimated_resolution=source.config.resolution_meters,
                        coverage_quality=coverage,
                    )
                )

        if not candidates:
            logger.warning(
                "No data sources available for bounds", bounds=bounds.model_dump()
            )
            return None

        # Sort by priority (lower number = higher priority), then by coverage
        candidates.sort(key=lambda x: (x.config.priority.value, -x.coverage_quality))

        best_source = candidates[0]
        logger.info(
            "Selected best data source",
            source=best_source.name,
            priority=best_source.config.priority.value,
            coverage=best_source.coverage_quality,
            resolution=best_source.estimated_resolution,
        )

        return best_source

    async def fetch_dem_data(
        self,
        bounds: GeographicBounds,
        output_path: Path,
        fallback_sources: list[str] | None = None,
    ) -> DataSourceInfo | None:
        """
        Fetch DEM data with automatic fallback.

        Args:
            bounds: Geographic bounds
            output_path: Path to save the data
            fallback_sources: Optional list of source names to try in order

        Returns:
            Information about the successful data source, or None if all failed
        """
        if fallback_sources:
            # Use specified fallback order
            sources_to_try = fallback_sources
        else:
            # Use intelligent source selection
            best_source = await self.get_best_data_source(bounds)
            if not best_source:
                return None
            sources_to_try = [best_source.name]

        errors = []

        for source_name in sources_to_try:
            if source_name not in self.data_sources:
                logger.warning(f"Unknown data source: {source_name}")
                continue

            source = self.data_sources[source_name]

            try:
                logger.info(f"Attempting to fetch data from {source_name}")

                success = await source.fetch_data(bounds, output_path)

                if success:
                    logger.info(f"Successfully fetched data from {source_name}")
                    return DataSourceInfo(
                        name=source_name,
                        config=source.config,
                        status=source.status,
                        estimated_resolution=source.config.resolution_meters,
                        coverage_quality=source.check_coverage(bounds),
                    )
                else:
                    errors.append((source_name, "Fetch failed"))

            except Exception as e:
                logger.warning(f"Failed to fetch from {source_name}: {e}")
                errors.append((source_name, str(e)))

                # Implement exponential backoff for retryable errors
                if source.status == DataSourceStatus.RATE_LIMITED:
                    await asyncio.sleep(min(60, 2 ** len(errors)))

        logger.error(
            "All data sources failed", bounds=bounds.model_dump(), errors=errors
        )
        return None

    def get_source_status(self) -> dict[str, dict[str, Any]]:
        """Get status of all data sources."""
        status = {}

        for name, source in self.data_sources.items():
            status[name] = {
                "name": source.config.name,
                "status": source.status.value,
                "priority": source.config.priority.value,
                "resolution_meters": source.config.resolution_meters,
                "coverage_regions": source.config.coverage_regions,
                "has_api_key": source.get_api_key() is not None,
                "rate_limit_per_hour": source.config.rate_limit_per_hour,
            }

        return status
