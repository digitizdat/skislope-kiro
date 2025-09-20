"""
Basic WorkflowSimulator Usage Examples

This module demonstrates the fundamental ways to use the WorkflowSimulator
for testing terrain loading and other core workflows.
"""

import asyncio
from unittest.mock import Mock

import pytest

from ..agent_lifecycle import AgentLifecycleManager
from ..config import get_test_config
from ..logging_utils import TestLogger
from ..models import TestCategory
from ..models import TestStatus
from ..workflow_simulator import SimulationState
from ..workflow_simulator import WorkflowSimulator
from ..workflow_simulator import WorkflowType


class TestBasicWorkflowUsage:
    """Examples of basic WorkflowSimulator usage patterns."""

    @pytest.mark.asyncio
    async def test_single_workflow_execution(self):
        """Example: Execute a single workflow and check results."""
        # Set up configuration and dependencies
        config = get_test_config()
        logger = TestLogger("basic_example", config)

        # Create mock agent manager
        agent_manager = Mock(spec=AgentLifecycleManager)
        agent_manager.is_agent_healthy.return_value = True

        # Execute workflow
        async with WorkflowSimulator(config, agent_manager, logger) as simulator:
            result = await simulator.simulate_workflow(WorkflowType.TERRAIN_LOADING)

            # Verify workflow execution
            assert result.workflow_type == WorkflowType.TERRAIN_LOADING
            assert result.duration > 0
            assert result.steps_total > 0

            # Check if workflow succeeded or failed gracefully
            if result.success:
                assert result.state == SimulationState.COMPLETED
                assert result.steps_completed == result.steps_total
            else:
                assert result.state == SimulationState.FAILED
                assert result.error is not None
                print(f"Workflow failed as expected: {result.error.message}")

    @pytest.mark.asyncio
    async def test_workflow_with_custom_context(self):
        """Example: Execute workflow with custom context data."""
        config = get_test_config()
        agent_manager = Mock()
        agent_manager.is_agent_healthy.return_value = True

        # Define custom context
        custom_context = {
            "ski_area": "whistler",
            "grid_size": (128, 128),
            "user_preferences": {"detail_level": "ultra_high", "cache_enabled": True},
        }

        async with WorkflowSimulator(config, agent_manager) as simulator:
            result = await simulator.simulate_workflow(
                WorkflowType.TERRAIN_LOADING, context=custom_context
            )

            # Verify context was preserved
            assert "ski_area" in result.context
            assert "user_preferences" in result.context
            assert result.context["user_preferences"]["detail_level"] == "ultra_high"

    @pytest.mark.asyncio
    async def test_multiple_workflows_batch(self):
        """Example: Execute multiple workflows in batch."""
        config = get_test_config()
        agent_manager = Mock()
        agent_manager.is_agent_healthy.return_value = True

        async with WorkflowSimulator(config, agent_manager) as simulator:
            # Execute all workflows
            results = await simulator.simulate_all_workflows()

            # Verify all workflow types were executed
            assert len(results) == len(WorkflowType)

            for workflow_type in WorkflowType:
                assert workflow_type in results
                result = results[workflow_type]
                assert result.workflow_type == workflow_type
                assert result.duration > 0

                print(
                    f"{workflow_type.value}: {result.state.value} "
                    f"({result.steps_completed}/{result.steps_total} steps)"
                )

    @pytest.mark.asyncio
    async def test_convert_to_test_results(self):
        """Example: Convert workflow results to standard test results."""
        config = get_test_config()
        agent_manager = Mock()

        async with WorkflowSimulator(config, agent_manager) as simulator:
            # Execute a workflow
            workflow_result = await simulator.simulate_workflow(
                WorkflowType.CACHE_INTEGRATION
            )

            # Convert to test results
            test_results = simulator.create_test_results(
                {WorkflowType.CACHE_INTEGRATION: workflow_result}
            )

            # Verify test result format
            assert len(test_results) == 1
            test_result = test_results[0]

            assert test_result.name == "workflow_cache_integration"
            assert test_result.category == TestCategory.WORKFLOWS
            assert test_result.duration > 0

            if workflow_result.success:
                assert test_result.status == TestStatus.PASSED
            else:
                assert test_result.status == TestStatus.FAILED
                assert test_result.error is not None


async def simple_terrain_loading_example():
    """
    Simple standalone example of terrain loading workflow.

    This function demonstrates the minimal setup needed to run
    a terrain loading workflow simulation.
    """
    print("🎿 Simple Terrain Loading Example")
    print("=" * 40)

    # Basic setup
    config = get_test_config()
    agent_manager = Mock()
    agent_manager.is_agent_healthy.return_value = True

    # Run the workflow
    async with WorkflowSimulator(config, agent_manager) as simulator:
        result = await simulator.simulate_workflow(WorkflowType.TERRAIN_LOADING)

        print(f"Status: {'✅ Success' if result.success else '❌ Failed'}")
        print(f"Duration: {result.duration:.3f}s")
        print(f"Steps: {result.steps_completed}/{result.steps_total}")

        if result.error:
            print(f"Error: {result.error.message}")


async def workflow_comparison_example():
    """
    Example comparing different workflow types.

    This demonstrates how to run multiple workflows and compare their results.
    """
    print("🔄 Workflow Comparison Example")
    print("=" * 40)

    config = get_test_config()
    agent_manager = Mock()
    agent_manager.is_agent_healthy.return_value = True

    workflows_to_test = [
        WorkflowType.TERRAIN_LOADING,
        WorkflowType.CACHE_INTEGRATION,
        WorkflowType.OFFLINE_MODE,
    ]

    results = {}

    async with WorkflowSimulator(config, agent_manager) as simulator:
        for workflow_type in workflows_to_test:
            print(f"Testing {workflow_type.value}...")
            result = await simulator.simulate_workflow(workflow_type)
            results[workflow_type] = result

            status = "✅" if result.success else "❌"
            print(
                f"  {status} {result.duration:.3f}s ({result.steps_completed}/{result.steps_total})"
            )

    # Summary
    print("\nSummary:")
    successful = sum(1 for r in results.values() if r.success)
    print(f"Success rate: {successful}/{len(results)} workflows")


if __name__ == "__main__":
    # Run standalone examples
    asyncio.run(simple_terrain_loading_example())
    print()
    asyncio.run(workflow_comparison_example())
