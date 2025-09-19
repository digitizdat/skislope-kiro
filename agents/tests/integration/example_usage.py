"""
WorkflowSimulator Usage Examples

This module provides comprehensive examples of how to use the WorkflowSimulator
for end-to-end testing in the Alpine Ski Slope Environment Viewer project.

The WorkflowSimulator enables testing of complete user workflows including:
- Terrain loading from ski area selection to cached data
- Cache integration with offline mode functionality  
- Error scenarios and graceful degradation testing
- Performance validation and monitoring

Examples are organized into several categories:
- basic_usage.py: Fundamental usage patterns
- advanced_usage.py: Advanced mocking and error injection
- real_world_scenarios.py: Realistic user interaction patterns
- integration_patterns.py: CI/CD and monitoring integration

Quick Start:
    from agents.tests.integration.workflow_simulator import WorkflowSimulator, WorkflowType
    from agents.tests.integration.config import get_test_config
    from unittest.mock import Mock
    
    config = get_test_config()
    agent_manager = Mock()
    agent_manager.is_agent_healthy.return_value = True
    
    async with WorkflowSimulator(config, agent_manager) as simulator:
        result = await simulator.simulate_workflow(WorkflowType.TERRAIN_LOADING)
        print(f"Status: {'✅' if result.success else '❌'}")
"""

import asyncio
from unittest.mock import Mock

from .workflow_simulator import WorkflowSimulator, WorkflowType, MockTerrainData
from .config import get_test_config
from .logging_utils import TestLogger


async def quick_start_example():
    """
    Quick start example showing basic WorkflowSimulator usage.
    
    This is the minimal example to get started with workflow simulation.
    """
    print("🚀 WorkflowSimulator Quick Start")
    print("=" * 40)
    
    # Basic setup
    config = get_test_config()
    agent_manager = Mock()
    agent_manager.is_agent_healthy.return_value = True
    
    # Run a single workflow
    async with WorkflowSimulator(config, agent_manager) as simulator:
        result = await simulator.simulate_workflow(WorkflowType.TERRAIN_LOADING)
        
        print(f"Workflow: {result.workflow_type.value}")
        print(f"Status: {'✅ Success' if result.success else '❌ Failed'}")
        print(f"Duration: {result.duration:.3f}s")
        print(f"Steps: {result.steps_completed}/{result.steps_total}")
        
        if result.error:
            print(f"Error: {result.error.message}")


async def all_workflows_example():
    """
    Example showing how to run all available workflows.
    
    This demonstrates batch execution and result analysis.
    """
    print("🔄 All Workflows Example")
    print("=" * 30)
    
    config = get_test_config()
    agent_manager = Mock()
    agent_manager.is_agent_healthy.return_value = True
    
    async with WorkflowSimulator(config, agent_manager) as simulator:
        print("Available workflows:")
        for workflow_type in WorkflowType:
            steps = simulator.workflows[workflow_type]
            print(f"  • {workflow_type.value.replace('_', ' ').title()}: {len(steps)} steps")
        
        print("\nExecuting all workflows...")
        results = await simulator.simulate_all_workflows()
        
        print("\nResults:")
        successful = 0
        for workflow_type, result in results.items():
            status = "✅" if result.success else "❌"
            print(f"  {status} {workflow_type.value}: {result.duration:.3f}s")
            if result.success:
                successful += 1
        
        print(f"\nSummary: {successful}/{len(results)} workflows successful")


async def mock_data_example():
    """
    Example showing MockTerrainData usage.
    
    This demonstrates how to generate realistic test data.
    """
    print("🏔️  Mock Data Generation Example")
    print("=" * 40)
    
    # Generate terrain data for different scenarios
    scenarios = [
        ("Small Area", "chamonix", (32, 32)),
        ("Medium Area", "whistler", (64, 64)),
        ("Large Area", "zermatt", (128, 128))
    ]
    
    for scenario_name, ski_area, grid_size in scenarios:
        mock_data = MockTerrainData.create_sample(ski_area, grid_size)
        
        print(f"\n{scenario_name}:")
        print(f"  Ski Area: {mock_data.ski_area}")
        print(f"  Grid Size: {mock_data.grid_size}")
        print(f"  Data Points: {len(mock_data.elevation_data) * len(mock_data.elevation_data[0]):,}")
        print(f"  Elevation Range: {mock_data.metadata['min_elevation']:.0f}m - {mock_data.metadata['max_elevation']:.0f}m")
        
        # Validate data structure
        all_elevations = [elev for row in mock_data.elevation_data for elev in row]
        is_valid = (
            len(mock_data.elevation_data) == grid_size[0] and
            len(mock_data.elevation_data[0]) == grid_size[1] and
            all(isinstance(elev, (int, float)) for elev in all_elevations)
        )
        print(f"  Data Valid: {'✅' if is_valid else '❌'}")


async def error_handling_example():
    """
    Example showing error handling capabilities.
    
    This demonstrates how the simulator handles various error conditions.
    """
    print("⚠️  Error Handling Example")
    print("=" * 30)
    
    config = get_test_config()
    
    # Test with unhealthy agents
    print("Testing with unhealthy agents...")
    agent_manager = Mock()
    agent_manager.is_agent_healthy.return_value = False
    
    async with WorkflowSimulator(config, agent_manager) as simulator:
        result = await simulator.simulate_workflow(WorkflowType.TERRAIN_LOADING)
        
        print(f"  Result: {'✅ Handled gracefully' if not result.success else '❌ Unexpected success'}")
        if result.error:
            print(f"  Error: {result.error.message}")
        print(f"  Steps completed: {result.steps_completed}/{result.steps_total}")


async def context_passing_example():
    """
    Example showing context passing between workflow steps.
    
    This demonstrates how data flows through workflow execution.
    """
    print("📦 Context Passing Example")
    print("=" * 30)
    
    config = get_test_config()
    agent_manager = Mock()
    agent_manager.is_agent_healthy.return_value = True
    
    # Custom context with user preferences
    custom_context = {
        "ski_area": "saint_anton",
        "grid_size": (128, 128),
        "user_preferences": {
            "detail_level": "ultra_high",
            "cache_enabled": True,
            "offline_mode": True
        },
        "session_id": "demo_session_123"
    }
    
    async with WorkflowSimulator(config, agent_manager) as simulator:
        result = await simulator.simulate_workflow(
            WorkflowType.TERRAIN_LOADING,
            context=custom_context
        )
        
        print("Input context:")
        for key, value in custom_context.items():
            print(f"  {key}: {value}")
        
        print(f"\nWorkflow result:")
        print(f"  Success: {'✅' if result.success else '❌'}")
        print(f"  Duration: {result.duration:.3f}s")
        
        print(f"\nOutput context keys:")
        for key in sorted(result.context.keys()):
            print(f"  • {key}")


async def test_integration_example():
    """
    Example showing integration with test infrastructure.
    
    This demonstrates converting workflow results to standard test results.
    """
    print("🧪 Test Integration Example")
    print("=" * 30)
    
    config = get_test_config()
    agent_manager = Mock()
    agent_manager.is_agent_healthy.return_value = True
    
    async with WorkflowSimulator(config, agent_manager) as simulator:
        # Run a few workflows
        workflow_results = {}
        
        for workflow_type in [WorkflowType.CACHE_INTEGRATION, WorkflowType.ERROR_SCENARIOS]:
            result = await simulator.simulate_workflow(workflow_type)
            workflow_results[workflow_type] = result
        
        # Convert to test results
        test_results = simulator.create_test_results(workflow_results)
        
        print("Generated test results:")
        for test_result in test_results:
            print(f"  • {test_result.name}")
            print(f"    Category: {test_result.category.value}")
            print(f"    Status: {test_result.status.value}")
            print(f"    Duration: {test_result.duration:.3f}s")
            if test_result.message:
                print(f"    Message: {test_result.message}")
            print()


async def main():
    """Run all usage examples."""
    print("🎿 Alpine Ski Slope Environment Viewer")
    print("🧪 WorkflowSimulator Usage Examples")
    print("=" * 60)
    print()
    
    examples = [
        ("Quick Start", quick_start_example),
        ("All Workflows", all_workflows_example),
        ("Mock Data Generation", mock_data_example),
        ("Error Handling", error_handling_example),
        ("Context Passing", context_passing_example),
        ("Test Integration", test_integration_example)
    ]
    
    for example_name, example_func in examples:
        try:
            await example_func()
            print()
            print("─" * 60)
            print()
        except Exception as e:
            print(f"❌ {example_name} failed: {e}")
            print()
    
    print("✅ All examples completed!")
    print()
    print("📚 For more examples, see:")
    print("  • examples/basic_usage.py - Fundamental patterns")
    print("  • examples/advanced_usage.py - Advanced techniques")
    print("  • examples/real_world_scenarios.py - Realistic scenarios")
    print("  • examples/integration_patterns.py - CI/CD integration")


if __name__ == "__main__":
    asyncio.run(main())