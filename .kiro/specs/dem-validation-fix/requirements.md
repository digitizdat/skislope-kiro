# DEM Validation Fix Requirements

## Introduction

The current DEM validation logic is too strict and rejects valid real-world terrain data. The "unique values" threshold of 10% is causing valid SRTM data from Chamonix (elevation range 986m-3673m) to be rejected because it only has 2.93% unique values. This is normal for quantized integer elevation data at 30m resolution over small areas.

## Requirements

### Requirement 1: Adjust Unique Values Validation

**User Story:** As a terrain processing system, I want to accept valid DEM data with realistic variation patterns, so that real-world terrain can be processed successfully.

#### Acceptance Criteria

1. WHEN DEM data has elevation variation consistent with real terrain THEN the system SHALL accept the data
2. WHEN DEM data has less than 1% unique values THEN the system SHALL reject it as potentially corrupted
3. WHEN DEM data has 1% or more unique values AND reasonable elevation range THEN the system SHALL accept it
4. WHEN DEM data has unrealistic elevation ranges (outside -500m to 9000m) THEN the system SHALL still reject it

### Requirement 2: Enhanced Validation Logging

**User Story:** As a developer debugging terrain issues, I want detailed validation information, so that I can understand why data is accepted or rejected.

#### Acceptance Criteria

1. WHEN validation runs THEN the system SHALL log elevation statistics (min, max, range, unique percentage)
2. WHEN validation fails THEN the system SHALL log the specific reason for failure
3. WHEN validation passes THEN the system SHALL log confirmation with key metrics
4. WHEN validation encounters edge cases THEN the system SHALL log warnings but continue processing

### Requirement 3: Maintain Data Quality Standards

**User Story:** As a terrain processing system, I want to maintain high data quality standards, so that obviously corrupted data is still rejected.

#### Acceptance Criteria

1. WHEN DEM data has no elevation variation (all same value) THEN the system SHALL reject it
2. WHEN DEM data has extreme elevation values outside realistic ranges THEN the system SHALL reject it
3. WHEN DEM data has coordinate system issues THEN the system SHALL reject it
4. WHEN DEM data has bounds that don't overlap requested area THEN the system SHALL reject it