"""
Integration test for WorkflowSimulator with the existing test infrastructure.

This test demonstrates the WorkflowSimulator working with real agent lifecycle
management and integration test components.
"""

from unittest.mock import Mock

import pytest

from .agent_lifecycle import AgentLifecycleManager
from .config import get_test_config
from .logging_utils import TestLogger
from .models import TestCategory
from .models import TestStatus
from .workflow_simulator import SimulationState
from .workflow_simulator import WorkflowSimulator
from .workflow_simulator import WorkflowType


class TestWorkflowIntegration:
    """Integration tests for WorkflowSimulator."""

    @pytest.mark.asyncio
    async def test_workflow_simulator_with_mock_agents(self):
        """Test WorkflowSimulator with mocked agent infrastructure."""
        # Get test configuration
        config = get_test_config()

        # Create logger
        logger = TestLogger("workflow_integration", config)

        # Create mock agent manager
        agent_manager = Mock(spec=AgentLifecycleManager)
        agent_manager.is_agent_healthy.return_value = True

        # Create workflow simulator
        async with WorkflowSimulator(config, agent_manager, logger) as simulator:
            # Test terrain loading workflow
            result = await simulator.simulate_workflow(WorkflowType.TERRAIN_LOADING)

            assert result.workflow_type == WorkflowType.TERRAIN_LOADING
            assert result.state in [SimulationState.COMPLETED, SimulationState.FAILED]
            assert result.duration > 0
            assert result.steps_total > 0

            # If successful, should have completed all steps
            if result.success:
                assert result.steps_completed == result.steps_total
                assert result.state == SimulationState.COMPLETED
            else:
                # If failed, should have error information
                assert result.error is not None
                assert result.state == SimulationState.FAILED

    @pytest.mark.asyncio
    async def test_cache_integration_workflow(self):
        """Test cache integration workflow specifically."""
        config = get_test_config()
        logger = TestLogger("cache_integration", config)
        agent_manager = Mock(spec=AgentLifecycleManager)

        async with WorkflowSimulator(config, agent_manager, logger) as simulator:
            result = await simulator.simulate_workflow(WorkflowType.CACHE_INTEGRATION)

            assert result.workflow_type == WorkflowType.CACHE_INTEGRATION
            assert result.duration > 0

            # Cache integration should work without external dependencies
            assert result.success is True
            assert result.state == SimulationState.COMPLETED
            assert result.steps_completed == result.steps_total

    @pytest.mark.asyncio
    async def test_offline_mode_workflow(self):
        """Test offline mode workflow."""
        config = get_test_config()
        logger = TestLogger("offline_mode", config)
        agent_manager = Mock(spec=AgentLifecycleManager)

        async with WorkflowSimulator(config, agent_manager, logger) as simulator:
            result = await simulator.simulate_workflow(WorkflowType.OFFLINE_MODE)

            assert result.workflow_type == WorkflowType.OFFLINE_MODE
            assert result.duration > 0

            # Offline mode should work with mock data
            assert result.success is True
            assert result.state == SimulationState.COMPLETED

    @pytest.mark.asyncio
    async def test_error_scenarios_workflow(self):
        """Test error scenarios workflow."""
        config = get_test_config()
        logger = TestLogger("error_scenarios", config)
        agent_manager = Mock(spec=AgentLifecycleManager)

        async with WorkflowSimulator(config, agent_manager, logger) as simulator:
            result = await simulator.simulate_workflow(WorkflowType.ERROR_SCENARIOS)

            assert result.workflow_type == WorkflowType.ERROR_SCENARIOS
            assert result.duration > 0

            # Error scenarios should complete successfully (testing error handling)
            assert result.success is True
            assert result.state == SimulationState.COMPLETED

    @pytest.mark.asyncio
    async def test_performance_validation_workflow(self):
        """Test performance validation workflow."""
        config = get_test_config()
        logger = TestLogger("performance_validation", config)
        agent_manager = Mock(spec=AgentLifecycleManager)

        async with WorkflowSimulator(config, agent_manager, logger) as simulator:
            result = await simulator.simulate_workflow(
                WorkflowType.PERFORMANCE_VALIDATION
            )

            assert result.workflow_type == WorkflowType.PERFORMANCE_VALIDATION
            assert result.duration > 0

            # Performance validation should complete
            assert result.success is True
            assert result.state == SimulationState.COMPLETED

    @pytest.mark.asyncio
    async def test_simulate_all_workflows(self):
        """Test simulating all workflows."""
        config = get_test_config()
        logger = TestLogger("all_workflows", config)
        agent_manager = Mock(spec=AgentLifecycleManager)
        agent_manager.is_agent_healthy.return_value = True

        async with WorkflowSimulator(config, agent_manager, logger) as simulator:
            results = await simulator.simulate_all_workflows()

            # Should have results for all workflow types
            assert len(results) == len(WorkflowType)

            for workflow_type in WorkflowType:
                assert workflow_type in results
                result = results[workflow_type]
                assert result.workflow_type == workflow_type
                assert result.duration > 0
                assert result.steps_total > 0

    @pytest.mark.asyncio
    async def test_create_test_results_from_workflows(self):
        """Test converting workflow results to test results."""
        config = get_test_config()
        logger = TestLogger("test_results", config)
        agent_manager = Mock(spec=AgentLifecycleManager)
        agent_manager.is_agent_healthy.return_value = True

        async with WorkflowSimulator(config, agent_manager, logger) as simulator:
            # Run a single workflow
            workflow_result = await simulator.simulate_workflow(
                WorkflowType.CACHE_INTEGRATION
            )

            # Convert to test results
            test_results = simulator.create_test_results(
                {WorkflowType.CACHE_INTEGRATION: workflow_result}
            )

            assert len(test_results) == 1
            test_result = test_results[0]

            assert test_result.name == "workflow_cache_integration"
            assert test_result.category == TestCategory.WORKFLOWS
            assert test_result.duration > 0

            if workflow_result.success:
                assert test_result.status == TestStatus.PASSED
                assert test_result.error is None
            else:
                assert test_result.status == TestStatus.FAILED
                assert test_result.error is not None

    @pytest.mark.asyncio
    async def test_workflow_with_agent_failure(self):
        """Test workflow behavior when agents are unavailable."""
        config = get_test_config()
        logger = TestLogger("agent_failure", config)

        # Create agent manager that reports unhealthy agents
        agent_manager = Mock(spec=AgentLifecycleManager)
        agent_manager.is_agent_healthy.return_value = False

        async with WorkflowSimulator(config, agent_manager, logger) as simulator:
            result = await simulator.simulate_workflow(WorkflowType.TERRAIN_LOADING)

            assert result.workflow_type == WorkflowType.TERRAIN_LOADING

            # Should handle agent failure gracefully
            # Either succeed with fallback or fail with proper error
            if not result.success:
                assert result.error is not None
                assert result.state == SimulationState.FAILED

    @pytest.mark.asyncio
    async def test_workflow_context_passing(self):
        """Test that context is properly passed through workflow steps."""
        config = get_test_config()
        logger = TestLogger("context_passing", config)
        agent_manager = Mock(spec=AgentLifecycleManager)

        async with WorkflowSimulator(config, agent_manager, logger) as simulator:
            # Test with custom context
            custom_context = {"test_key": "test_value", "grid_size": (128, 128)}

            result = await simulator.simulate_workflow(
                WorkflowType.PERFORMANCE_VALIDATION, context=custom_context
            )

            assert result.workflow_type == WorkflowType.PERFORMANCE_VALIDATION
            assert "test_key" in result.context
            assert result.context["test_key"] == "test_value"

    def test_mock_terrain_data_generation(self):
        """Test mock terrain data generation."""
        from .workflow_simulator import MockTerrainData

        # Test default generation
        data = MockTerrainData.create_sample()
        assert data.ski_area == "test_area"
        assert data.grid_size == (32, 32)
        assert len(data.elevation_data) == 32
        assert len(data.elevation_data[0]) == 32

        # Test custom generation
        data = MockTerrainData.create_sample("chamonix", (64, 64))
        assert data.ski_area == "chamonix"
        assert data.grid_size == (64, 64)
        assert len(data.elevation_data) == 64
        assert len(data.elevation_data[0]) == 64

        # Verify elevation data is reasonable
        all_elevations = [elev for row in data.elevation_data for elev in row]
        assert all(isinstance(elev, (int, float)) for elev in all_elevations)
        assert all(elev >= 0 for elev in all_elevations)
        assert max(all_elevations) > min(all_elevations)  # Should have variation


if __name__ == "__main__":
    pytest.main([__file__])
