"""Tests for the enhanced DEM validation logic."""

import numpy as np
import pytest

from agents.hill_metrics.terrain_processor import DEMProcessor


class TestDEMValidationFix:
    """Test the enhanced DEM validation logic."""

    def setup_method(self):
        """Set up test fixtures."""
        self.processor = DEMProcessor()

    def test_chamonix_srtm_data_acceptance(self):
        """Test that Chamonix SRTM data with 2687m range and 2.93% unique values is accepted."""
        # Simulate Chamonix SRTM data characteristics
        # 90,720 total values with 2,659 unique values (2.93%)
        # Elevation range: 986m to 3673m (2687m variation)

        # Create test data with similar characteristics
        base_elevations = np.arange(986, 3674)  # 2688 unique values
        # Repeat values to simulate quantization effect
        total_pixels = 90720
        test_data = np.random.choice(base_elevations, size=total_pixels)

        # Ensure we have the right characteristics
        unique_count = len(np.unique(test_data))
        unique_percentage = unique_count / len(test_data) * 100
        elevation_range = np.max(test_data) - np.min(test_data)

        print(
            f"Test data: {unique_count} unique values, {unique_percentage:.2f}%, {elevation_range}m range"
        )

        # Test validation
        is_valid, reason = self.processor._validate_elevation_variation(test_data)

        assert is_valid, f"Chamonix-like data should be valid: {reason}"
        assert "Valid elevation range" in reason
        assert elevation_range >= 2000  # Should have significant elevation range

    def test_flat_terrain_rejection(self):
        """Test that completely flat terrain is rejected."""
        # Create flat data (all same elevation)
        test_data = np.full(10000, 1500.0)  # All 1500m elevation

        is_valid, reason = self.processor._validate_elevation_variation(test_data)

        assert not is_valid, "Flat terrain should be rejected"
        # Flat data fails on unique values check first (0.01% unique)
        assert "Too few unique values" in reason

    def test_no_elevation_variation_rejection(self):
        """Test rejection specifically for no elevation variation."""
        # Create data with adequate unique percentage but no elevation range
        # This tests the elevation range check specifically
        elevations = [
            1500,
            1500,
            1500,
        ]  # Same elevation but multiple "unique" values due to float precision
        test_data = np.array(elevations * 400)  # 1200 values, but all same elevation

        # Add tiny variations to get >1% unique but <1m range
        test_data = test_data + np.random.normal(0, 0.1, len(test_data))  # Add noise

        # Ensure we have >1% unique but <1m range
        unique_percentage = len(np.unique(test_data)) / len(test_data) * 100
        elevation_range = np.max(test_data) - np.min(test_data)

        if unique_percentage > 1.0 and elevation_range < 1.0:
            is_valid, reason = self.processor._validate_elevation_variation(test_data)
            assert not is_valid, "Data with no elevation variation should be rejected"
            assert "No elevation variation" in reason

    def test_corrupted_data_rejection(self):
        """Test that data with extremely few unique values is rejected."""
        # Create data with <1% unique values and small range
        test_data = np.array([100] * 9950 + [101] * 50)  # 0.5% unique values, 1m range

        is_valid, reason = self.processor._validate_elevation_variation(test_data)

        assert not is_valid, "Corrupted data should be rejected"
        assert "Too few unique values" in reason

    def test_moderate_terrain_acceptance(self):
        """Test that moderate terrain with adequate diversity is accepted."""
        # Create rolling hills data: 50m range with 8% unique values
        base_elevations = np.arange(200, 251)  # 51 unique values
        test_data = np.random.choice(base_elevations, size=600)  # ~8.5% unique

        unique_percentage = len(np.unique(test_data)) / len(test_data) * 100
        elevation_range = np.max(test_data) - np.min(test_data)

        print(
            f"Moderate terrain: {unique_percentage:.2f}% unique, {elevation_range}m range"
        )

        is_valid, reason = self.processor._validate_elevation_variation(test_data)

        assert is_valid, f"Moderate terrain should be valid: {reason}"

    def test_small_terrain_with_diversity(self):
        """Test small elevation range with adequate diversity."""
        # 8m range with 6% unique values - should pass
        elevations = [100, 101, 102, 103, 104, 105, 106, 107, 108]  # 9 unique values
        test_data = np.array(elevations * 17)  # 153 total values, ~5.9% unique

        unique_percentage = len(np.unique(test_data)) / len(test_data) * 100
        elevation_range = np.max(test_data) - np.min(test_data)

        print(
            f"Small diverse terrain: {unique_percentage:.2f}% unique, {elevation_range}m range"
        )

        is_valid, reason = self.processor._validate_elevation_variation(test_data)

        assert is_valid, f"Small diverse terrain should be valid: {reason}"
        assert "Acceptable for small terrain" in reason

    def test_insufficient_variation_rejection(self):
        """Test rejection of data with insufficient variation."""
        # 3m range with 2% unique values - should fail
        elevations = [100, 101, 102, 103]  # 4 unique values
        test_data = np.array(elevations * 50)  # 200 total values, 2% unique, 3m range

        unique_percentage = len(np.unique(test_data)) / len(test_data) * 100
        elevation_range = np.max(test_data) - np.min(test_data)

        print(
            f"Insufficient variation: {unique_percentage:.2f}% unique, {elevation_range}m range"
        )

        is_valid, reason = self.processor._validate_elevation_variation(test_data)

        assert not is_valid, "Insufficient variation should be rejected"
        assert "Insufficient variation" in reason

    def test_edge_case_10m_threshold(self):
        """Test the 10m elevation range threshold."""
        # Exactly 10m range with low unique percentage - should pass
        elevations = [1000, 1005, 1010]  # 3 unique values, 10m range
        test_data = np.array(elevations * 100)  # 300 total values, 1% unique

        unique_percentage = len(np.unique(test_data)) / len(test_data) * 100
        elevation_range = np.max(test_data) - np.min(test_data)

        print(
            f"10m threshold test: {unique_percentage:.2f}% unique, {elevation_range}m range"
        )

        is_valid, reason = self.processor._validate_elevation_variation(test_data)

        assert is_valid, (
            f"10m range should be valid regardless of unique percentage: {reason}"
        )
        assert "Valid elevation range" in reason

    def test_edge_case_5m_threshold(self):
        """Test the 5m elevation range with 5% unique threshold."""
        # Exactly 5m range with exactly 5% unique values - should pass
        elevations = [500, 501, 502, 503, 504, 505]  # 6 unique values, 5m range
        test_data = np.array(elevations * 20)  # 120 total values, 5% unique

        unique_percentage = len(np.unique(test_data)) / len(test_data) * 100
        elevation_range = np.max(test_data) - np.min(test_data)

        print(
            f"5m/5% threshold test: {unique_percentage:.2f}% unique, {elevation_range}m range"
        )

        is_valid, reason = self.processor._validate_elevation_variation(test_data)

        assert is_valid, f"5m range with 5% unique should be valid: {reason}"

    def test_realistic_mountain_data(self):
        """Test with realistic mountain elevation data."""
        # Simulate realistic mountain data with integer quantization
        # Base elevations from 800m to 3200m (2400m range)
        base_elevations = np.arange(800, 3201, 1)  # Integer elevations

        # Create realistic distribution (more values at lower elevations)
        weights = np.exp(-(np.arange(len(base_elevations)) / len(base_elevations)) * 2)
        test_data = np.random.choice(
            base_elevations, size=50000, p=weights / weights.sum()
        )

        unique_count = len(np.unique(test_data))
        unique_percentage = unique_count / len(test_data) * 100
        elevation_range = np.max(test_data) - np.min(test_data)

        print(
            f"Realistic mountain: {unique_count} unique, {unique_percentage:.2f}%, {elevation_range}m range"
        )

        is_valid, reason = self.processor._validate_elevation_variation(test_data)

        assert is_valid, f"Realistic mountain data should be valid: {reason}"
        assert elevation_range > 1000  # Should have significant range

    @pytest.mark.parametrize(
        "elevation_range,unique_pct,expected,expected_reason",
        [
            (2687, 2.93, True, "Valid elevation range"),  # Chamonix case
            (
                0.5,
                0.1,
                False,
                "Too few unique values",
            ),  # Flat (fails on unique % first)
            (50, 8.2, True, "Valid elevation range"),  # Rolling hills
            (8, 6.0, True, "Acceptable for small terrain"),  # Small diverse
            (3, 2.0, False, "Insufficient variation"),  # Insufficient
            (15, 0.8, False, "Too few unique values"),  # Low diversity
        ],
    )
    def test_validation_scenarios(
        self, elevation_range, unique_pct, expected, expected_reason
    ):
        """Test various validation scenarios with parameterized data."""
        # Create test data matching the scenario
        if elevation_range < 1:
            # Flat data
            test_data = np.full(1000, 1000.0)
        else:
            # Create data with specified characteristics
            num_unique = max(1, int(1000 * unique_pct / 100))
            elevations = np.linspace(1000, 1000 + elevation_range, num_unique)
            test_data = np.random.choice(elevations, size=1000)

        is_valid, reason = self.processor._validate_elevation_variation(test_data)

        assert is_valid == expected, (
            f"Expected {expected} for {elevation_range}m range, {unique_pct}% unique"
        )
        if expected_reason:
            assert expected_reason in reason, (
                f"Expected '{expected_reason}' in reason: {reason}"
            )
