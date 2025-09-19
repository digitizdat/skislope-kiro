"""Common utilities for agent servers."""

import asyncio
import hashlib
import json
import time
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

import httpx
import structlog

logger = structlog.get_logger(__name__)


class RetryConfig:
    """Configuration for retry logic."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base


async def retry_with_backoff(
    func: Any,
    config: RetryConfig,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """
    Retry a function with exponential backoff.
    
    Args:
        func: Async function to retry
        config: Retry configuration
        *args: Function arguments
        **kwargs: Function keyword arguments
        
    Returns:
        Function result
        
    Raises:
        Last exception if all retries fail
    """
    last_exception = None
    
    for attempt in range(config.max_attempts):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            
            if attempt == config.max_attempts - 1:
                break
            
            delay = min(
                config.base_delay * (config.exponential_base ** attempt),
                config.max_delay,
            )
            
            logger.warning(
                "Function call failed, retrying",
                attempt=attempt + 1,
                max_attempts=config.max_attempts,
                delay=delay,
                error=str(e),
            )
            
            await asyncio.sleep(delay)
    
    raise last_exception


class CacheManager:
    """Simple in-memory cache with TTL support."""
    
    def __init__(self, default_ttl: float = 300.0):
        self.default_ttl = default_ttl
        self._cache: Dict[str, Tuple[Any, float]] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        if key not in self._cache:
            return None
        
        value, expires_at = self._cache[key]
        
        if time.time() > expires_at:
            del self._cache[key]
            return None
        
        return value
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """
        Set a value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (uses default if None)
        """
        ttl = ttl or self.default_ttl
        expires_at = time.time() + ttl
        self._cache[key] = (value, expires_at)
    
    def delete(self, key: str) -> None:
        """Delete a key from cache."""
        self._cache.pop(key, None)
    
    def clear(self) -> None:
        """Clear all cached values."""
        self._cache.clear()
    
    def cleanup_expired(self) -> None:
        """Remove expired entries from cache."""
        current_time = time.time()
        expired_keys = [
            key for key, (_, expires_at) in self._cache.items()
            if current_time > expires_at
        ]
        
        for key in expired_keys:
            del self._cache[key]


def generate_cache_key(*args: Any) -> str:
    """
    Generate a cache key from arguments.
    
    Args:
        *args: Arguments to include in key
        
    Returns:
        SHA256 hash of the arguments
    """
    key_data = json.dumps(args, sort_keys=True, default=str)
    return hashlib.sha256(key_data.encode()).hexdigest()


async def download_file(
    url: str,
    output_path: Path,
    chunk_size: int = 8192,
    timeout: float = 30.0,
) -> None:
    """
    Download a file from URL.
    
    Args:
        url: URL to download from
        output_path: Path to save the file
        chunk_size: Download chunk size in bytes
        timeout: Request timeout in seconds
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream("GET", url) as response:
            response.raise_for_status()
            
            with open(output_path, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size):
                    f.write(chunk)
    
    logger.info(
        "Downloaded file",
        url=url,
        output_path=str(output_path),
        size_bytes=output_path.stat().st_size,
    )


def validate_coordinates(lat: float, lng: float) -> bool:
    """
    Validate geographic coordinates.
    
    Args:
        lat: Latitude
        lng: Longitude
        
    Returns:
        True if coordinates are valid
    """
    return -90 <= lat <= 90 and -180 <= lng <= 180


def calculate_distance(
    lat1: float,
    lng1: float,
    lat2: float,
    lng2: float,
) -> float:
    """
    Calculate distance between two points using Haversine formula.
    
    Args:
        lat1: First point latitude
        lng1: First point longitude
        lat2: Second point latitude
        lng2: Second point longitude
        
    Returns:
        Distance in kilometers
    """
    import math
    
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lng1_rad = math.radians(lng1)
    lat2_rad = math.radians(lat2)
    lng2_rad = math.radians(lng2)
    
    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlng = lng2_rad - lng1_rad
    
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))
    
    # Earth radius in kilometers
    earth_radius = 6371.0
    
    return earth_radius * c


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"