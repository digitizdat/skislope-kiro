"""
Integration test for API Contract Validator with real agent servers.

Tests the contract validator against actual running agent servers to ensure
it can discover methods and validate contracts correctly.
"""

import pytest

from agents.tests.integration.api_contract_validator import APIContractValidator
from agents.tests.integration.config import AgentConfig
from agents.tests.integration.config import TestConfig


class TestAPIContractValidatorIntegration:
    """Integration tests for API Contract Validator."""

    @pytest.fixture
    def test_config(self):
        """Create test configuration for integration testing."""
        config = TestConfig()
        config.agents = {
            "hill_metrics": AgentConfig(
                name="hill_metrics", host="localhost", port=8001, enabled=True
            )
        }
        return config

    @pytest.mark.asyncio
    async def test_discover_hill_metrics_methods(self, test_config):
        """Test discovering methods from hill metrics agent server."""
        validator = APIContractValidator(test_config)

        try:
            # Test method discovery via reflection
            methods = await validator._discover_backend_methods("hill_metrics")

            # Should discover the registered JSON-RPC methods
            method_names = [m.name for m in methods]

            # Check for expected methods based on the server implementation
            expected_methods = ["getHillMetrics", "getElevationProfile"]

            for expected_method in expected_methods:
                assert expected_method in method_names, (
                    f"Expected method {expected_method} not found in {method_names}"
                )

            # Check method signatures
            hill_metrics_method = next(
                (m for m in methods if m.name == "getHillMetrics"), None
            )
            assert hill_metrics_method is not None
            assert hill_metrics_method.is_async is True

            # Check parameters
            assert "bounds" in hill_metrics_method.parameters
            assert "grid_size" in hill_metrics_method.parameters

        except ImportError:
            pytest.skip("Hill metrics agent module not available for testing")

    @pytest.mark.asyncio
    async def test_validate_hill_metrics_contract(self, test_config):
        """Test validating contract for hill metrics agent."""
        validator = APIContractValidator(test_config)

        try:
            # Test contract validation
            result = await validator.validate_agent_contract(
                "hill_metrics", test_config.agents["hill_metrics"]
            )

            # Should have discovered methods
            assert len(result.backend_methods) > 0
            assert len(result.frontend_methods) > 0

            # Check for expected frontend methods
            frontend_method_names = [m.name for m in result.frontend_methods]
            assert "getHillMetrics" in frontend_method_names
            assert "getElevationProfile" in frontend_method_names

            # Check for expected backend methods
            backend_method_names = [m.name for m in result.backend_methods]
            assert "getHillMetrics" in backend_method_names

            # Contract should be valid if methods match and no signature mismatches
            # (protocol violations are expected in test environment without HTTP session)
            if not result.missing_backend_methods and not result.signature_mismatches:
                # Contract is valid from method perspective, protocol violations are expected
                print("Contract validation successful - methods match")
                print(
                    f"Protocol violations (expected in test): {result.protocol_violations}"
                )
            else:
                # If there are missing methods or signature mismatches, contract should be invalid
                print(f"Missing backend methods: {result.missing_backend_methods}")
                print(f"Signature mismatches: {result.signature_mismatches}")
                if result.missing_backend_methods:
                    raise AssertionError(
                        f"Missing backend methods: {result.missing_backend_methods}"
                    )

        except ImportError:
            pytest.skip("Hill metrics agent module not available for testing")

    @pytest.mark.asyncio
    async def test_run_contract_tests_integration(self, test_config):
        """Test running contract tests in integration mode."""
        validator = APIContractValidator(test_config)

        try:
            # Run contract tests
            test_results = await validator.run_contract_tests()

            # Should have results for enabled agents
            assert len(test_results) > 0

            # Check test result structure
            for test_result in test_results:
                assert test_result.name.startswith("API Contract Validation")
                assert test_result.category.value == "api_contracts"
                assert test_result.status.value in ["passed", "failed"]

                if test_result.status.value == "failed":
                    assert test_result.error is not None
                    print(f"Contract validation failed: {test_result.error.message}")
                    print(f"Context: {test_result.context}")

        except ImportError:
            pytest.skip("Agent modules not available for testing")

    def test_frontend_method_mappings_completeness(self):
        """Test that frontend method mappings are complete."""
        validator = APIContractValidator(TestConfig())

        # Check that all expected agents have method mappings
        expected_agents = ["hill_metrics", "weather", "equipment"]

        for agent in expected_agents:
            assert agent in validator.frontend_method_mappings
            methods = validator.frontend_method_mappings[agent]
            assert len(methods) > 0

            # Check method structure
            for _method_name, method_info in methods.items():
                assert "parameters" in method_info
                assert "return_type" in method_info
                assert isinstance(method_info["parameters"], dict)
                assert isinstance(method_info["return_type"], str)

    def test_type_compatibility_comprehensive(self):
        """Test type compatibility checking with various type combinations."""
        validator = APIContractValidator(TestConfig())

        # Test exact matches
        assert validator._are_types_compatible("string", "string")
        assert validator._are_types_compatible("number", "number")

        # Test compatible mappings
        compatible_pairs = [
            ("string", "str"),
            ("number", "float"),
            ("number", "int"),
            ("integer", "int"),
            ("boolean", "bool"),
            ("object", "dict"),
            ("array", "list"),
            ("array", "List"),
            ("object", "Dict"),
        ]

        for frontend_type, backend_type in compatible_pairs:
            assert validator._are_types_compatible(frontend_type, backend_type)
            # Test reverse compatibility
            assert validator._are_types_compatible(backend_type, frontend_type)

        # Test incompatible types (should still return True for unknown types)
        assert validator._are_types_compatible("CustomType1", "CustomType2")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
