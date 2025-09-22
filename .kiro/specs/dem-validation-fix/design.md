# DEM Validation Fix Design

## Overview

The current DEM validation logic uses a 10% unique values threshold that is too strict for real-world quantized elevation data. This design addresses the issue by implementing more nuanced validation that considers elevation range and data characteristics rather than just unique value percentage.

## Root Cause Analysis

### Current Problem
- SRTM data is quantized to integer meters
- Small geographic areas (7km x 7km) at 30m resolution create ~233x233 pixel grids
- Even with significant elevation variation (2,687m range in Chamonix), quantized data results in low unique value percentages
- Real Chamonix data: 2.93% unique values with 986m-3673m elevation range - clearly valid but rejected

### Why 10% Threshold Fails
1. **Quantization Effect**: Integer elevation values reduce unique count
2. **Resolution Effect**: 30m pixels over small areas limit variation
3. **Geographic Scale**: Mountain terrain over 7km may have repeated elevation values
4. **Data Source Characteristics**: Different DEM sources have different quantization patterns

## Design Solution

### New Validation Strategy

Replace the simple unique percentage threshold with a multi-factor validation approach:

```python
def _validate_elevation_variation(self, valid_data: np.ndarray) -> tuple[bool, str]:
    """
    Validate elevation data using multiple quality indicators.
    
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
        return True, f"Acceptable for small terrain: {elevation_range}m range, {unique_percentage:.2f}% unique"
    
    return False, f"Insufficient variation: {elevation_range}m range, {unique_percentage:.2f}% unique"
```

### Validation Criteria

#### Accept Data When:
1. **Significant Elevation Range**: ≥10m variation (regardless of unique percentage)
2. **Moderate Range + Diversity**: ≥5m variation AND ≥5% unique values
3. **High Diversity**: ≥1% unique values AND reasonable elevation range

#### Reject Data When:
1. **Extremely Low Diversity**: <1% unique values (likely corrupted)
2. **No Variation**: <1m elevation range (completely flat/corrupted)
3. **Unrealistic Values**: Outside -500m to 9000m range
4. **Technical Issues**: CRS problems, bounds mismatch, etc.

## Implementation Plan

### Modified Validation Function

```python
async def _validate_dem_file(self, dem_path: Path, bounds: GeographicBounds) -> bool:
    """Enhanced DEM validation with realistic thresholds."""
    try:
        with rasterio.open(dem_path) as src:
            # Existing technical validations (CRS, bounds, bands)
            if src.count != 1:
                logger.warning("DEM file has multiple bands", bands=src.count)
                return False

            if src.crs is None:
                logger.warning("DEM file has no coordinate reference system")
                return False

            file_bounds = src.bounds
            if not self._bounds_overlap(file_bounds, bounds):
                logger.warning("DEM file bounds do not overlap", 
                             file_bounds=file_bounds, requested_bounds=bounds.model_dump())
                return False

            # Read and process elevation data
            elevation_data = src.read(1)
            nodata = src.nodata
            
            if nodata is not None:
                valid_data = elevation_data[elevation_data != nodata]
            else:
                valid_data = elevation_data.flatten()

            if len(valid_data) == 0:
                logger.warning("DEM file contains no valid elevation data")
                return False

            # Enhanced elevation validation
            min_elevation = np.min(valid_data)
            max_elevation = np.max(valid_data)
            
            # Check realistic elevation ranges
            if min_elevation < -500 or max_elevation > 9000:
                logger.warning("Unrealistic elevation values",
                             min_elevation=min_elevation, max_elevation=max_elevation)
                return False

            # New multi-factor validation
            is_valid, reason = self._validate_elevation_variation(valid_data)
            
            if not is_valid:
                logger.warning("Elevation validation failed", reason=reason,
                             min_elevation=min_elevation, max_elevation=max_elevation)
                return False

            # Log successful validation with detailed metrics
            unique_values = len(np.unique(valid_data))
            total_values = len(valid_data)
            elevation_range = max_elevation - min_elevation
            
            logger.info("DEM file validation passed",
                       path=str(dem_path), crs=str(src.crs), bounds=file_bounds,
                       elevation_range=(min_elevation, max_elevation),
                       elevation_variation=elevation_range,
                       unique_values=unique_values, total_values=total_values,
                       unique_percentage=f"{unique_values/total_values*100:.2f}%",
                       validation_reason=reason)
            
            return True

    except Exception as e:
        logger.error("Error validating DEM file", path=str(dem_path), error=str(e))
        return False
```

### Enhanced Logging

The new validation provides detailed logging for debugging:

```
INFO: DEM file validation passed
  - elevation_range: (986, 3673)
  - elevation_variation: 2687m
  - unique_values: 2659 / 90720 (2.93%)
  - validation_reason: "Valid elevation range: 2687m"
```

## Testing Strategy

### Test Cases

1. **Chamonix SRTM Data**: Should pass with 2687m elevation range despite 2.93% unique values
2. **Flat Terrain**: Should fail with <1m elevation variation
3. **Corrupted Data**: Should fail with <1% unique values
4. **Moderate Terrain**: Should pass with 50m range and 3% unique values
5. **High-Resolution Data**: Should pass with higher unique percentages

### Validation Scenarios

```python
# Test data scenarios
test_scenarios = [
    {
        'name': 'Chamonix SRTM',
        'elevation_range': 2687,
        'unique_percentage': 2.93,
        'expected': True,
        'reason': 'Significant elevation range'
    },
    {
        'name': 'Flat corrupted',
        'elevation_range': 0.5,
        'unique_percentage': 0.1,
        'expected': False,
        'reason': 'No elevation variation'
    },
    {
        'name': 'Rolling hills',
        'elevation_range': 45,
        'unique_percentage': 8.2,
        'expected': True,
        'reason': 'Moderate range with diversity'
    }
]
```

## Backward Compatibility

- Maintains all existing technical validations (CRS, bounds, realistic elevation ranges)
- Only changes the unique values threshold logic
- Improves logging without breaking existing interfaces
- No changes to public API or return types

## Performance Impact

- Minimal performance impact (same data processing, different thresholds)
- Slightly more detailed logging
- No additional file I/O or computation

## Risk Mitigation

- Maintains strict validation for obviously corrupted data
- Preserves elevation range checks to prevent unrealistic data
- Enhanced logging helps identify edge cases
- Gradual rollout possible through configuration flags if needed