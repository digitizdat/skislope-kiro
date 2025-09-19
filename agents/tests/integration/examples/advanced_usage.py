"""
Advanced WorkflowSimulator Usage Examples

This module demonstrates advanced usage patterns including custom mocking,
error injection, performance testing, and integration with real agents.
"""

import asyncio
import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from ..workflow_simulator import WorkflowSimulator, WorkflowType, MockTerrainData
from ..config import get_test_config
from ..agent_lifecycle import AgentLifecycleManager
from ..logging_utils import TestLogger
from ..models import TestError, Severity


class TestAdvancedWorkflowUsage:
    """Examples of advanced WorkflowSimulator usage patterns."""
    
    @pytest.mark.asyncio
    async def test_workflow_with_mock_http_responses(self):
        """Example: Mock HTTP responses for realistic agent simulation."""
        config = get_test_config()
        agent_manager = Mock()
        agent_manager.is_agent_healthy.return_value = True
        
        async with WorkflowSimulator(config, agent_manager) as simulator:
            # Create realistic mock terrain response
            mock_terrain_data = {
                "result": {
                    "ski_area": "chamonix",
                    "grid_size": (64, 64),
                    "elevation_data": [
                        [1000.0 + i * 5.0 + j * 2.0 for j in range(64)]
                        for i in range(64)
                    ],
                    "metadata": {
                        "min_elevation": 1000.0,
                        "max_elevation": 1500.0,
                        "resolution": 10.0,
                        "coordinate_system": "WGS84"
                    }
                }
            }
            
            # Mock HTTP client
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_terrain_data
            
            simulator.http_client = AsyncMock()
            simulator.http_client.post.return_value = mock_response
            
            # Execute workflow with mocked responses
            result = await simulator.simulate_workflow(WorkflowType.TERRAIN_LOADING)
            
            # Verify HTTP client was called
            simulator.http_client.post.assert_called()
            
            # Check if terrain data was processed
            if "terrain_data" in result.context:
                terrain_data = result.context["terrain_data"]
                assert terrain_data["ski_area"] == "chamonix"
                assert terrain_data["grid_size"] == (64, 64)
    
    @pytest.mark.asyncio
    async def test_error_injection_scenarios(self):
        """Example: Inject specific errors to test error handling."""
        config = get_test_config()
        
        # Test different error scenarios
        error_scenarios = [
            ("unhealthy_agents", False),
            ("network_timeout", True),
            ("invalid_response", True)
        ]
        
        for scenario_name, agents_healthy in error_scenarios:
            print(f"\nTesting scenario: {scenario_name}")
            
            agent_manager = Mock()
            agent_manager.is_agent_healthy.return_value = agents_healthy
            
            async with WorkflowSimulator(config, agent_manager) as simulator:
                if scenario_name == "network_timeout":
                    # Simulate network timeout
                    simulator.http_client = AsyncMock()
                    simulator.http_client.post.side_effect = asyncio.TimeoutError("Request timeout")
                
                elif scenario_name == "invalid_response":
                    # Simulate invalid response
                    mock_response = Mock()
                    mock_response.status_code = 500
                    simulator.http_client = AsyncMock()
                    simulator.http_client.post.return_value = mock_response
                
                result = await simulator.simulate_workflow(WorkflowType.TERRAIN_LOADING)
                
                # Verify error was handled appropriately
                if not result.success:
                    assert result.error is not None
                    print(f"  Error handled: {result.error.message}")
                else:
                    print(f"  Scenario passed unexpectedly")
    
    @pytest.mark.asyncio
    async def test_performance_benchmarking(self):
        """Example: Use WorkflowSimulator for performance benchmarking."""
        config = get_test_config()
        agent_manager = Mock()
        agent_manager.is_agent_healthy.return_value = True
        
        # Test different grid sizes for performance comparison
        grid_sizes = [(32, 32), (64, 64), (128, 128)]
        performance_results = {}
        
        async with WorkflowSimulator(config, agent_manager) as simulator:
            for grid_size in grid_sizes:
                context = {"grid_size": grid_size}
                
                # Run performance validation workflow
                result = await simulator.simulate_workflow(
                    WorkflowType.PERFORMANCE_VALIDATION,
                    context=context
                )
                
                performance_results[grid_size] = {
                    "duration": result.duration,
                    "success": result.success,
                    "steps_completed": result.steps_completed
                }
                
                print(f"Grid {grid_size}: {result.duration:.3f}s")
        
        # Analyze performance trends
        durations = [perf["duration"] for perf in performance_results.values()]
        print(f"Performance range: {min(durations):.3f}s - {max(durations):.3f}s")
    
    @pytest.mark.asyncio
    async def test_custom_workflow_step_execution(self):
        """Example: Execute individual workflow steps for detailed testing."""
        config = get_test_config()
        agent_manager = Mock()
        
        async with WorkflowSimulator(config, agent_manager) as simulator:
            # Test individual steps in isolation
            context = {}
            
            # Step 1: Select ski area
            context["ski_area"] = "zermatt"
            result1 = await simulator._step_select_ski_area(context)
            assert result1 is True
            assert "selected_ski_area" in context
            
            # Step 2: Configure grid size
            context["grid_size"] = (64, 64)
            result2 = await simulator._step_configure_grid_size(context)
            assert result2 is True
            assert "configured_grid_size" in context
            
            # Step 3: Test cache operations
            result3 = await simulator._step_initialize_cache(context)
            assert result3 is True
            assert "cache_initialized" in context
            
            print("All individual steps executed successfully")
    
    @pytest.mark.asyncio
    async def test_workflow_with_real_cache_files(self):
        """Example: Test workflows with actual file system operations."""
        config = get_test_config()
        agent_manager = Mock()
        
        async with WorkflowSimulator(config, agent_manager) as simulator:
            # Execute cache integration workflow
            result = await simulator.simulate_workflow(WorkflowType.CACHE_INTEGRATION)
            
            # Check if cache files were actually created
            if simulator.mock_cache_dir and simulator.mock_cache_dir.exists():
                cache_files = list(simulator.mock_cache_dir.glob("*.json"))
                print(f"Created {len(cache_files)} cache files")
                
                # Verify file contents
                for cache_file in cache_files:
                    if cache_file.name != "metadata.json":
                        with open(cache_file, 'r') as f:
                            data = json.load(f)
                            assert "ski_area" in data
                            assert "elevation_data" in data
                            print(f"Verified cache file: {cache_file.name}")


async def custom_terrain_data_example():
    """
    Example: Create and use custom terrain data in workflows.
    
    This demonstrates how to generate custom terrain data for specific
    testing scenarios.
    """
    print("🏔️  Custom Terrain Data Example")
    print("=" * 40)
    
    # Create custom terrain data for different scenarios
    test_scenarios = [
        ("flat_terrain", "whistler", (16, 16)),
        ("steep_mountain", "chamonix", (32, 32)),
        ("large_area", "zermatt", (64, 64))
    ]
    
    for scenario_name, ski_area, grid_size in test_scenarios:
        print(f"\nTesting {scenario_name}:")
        
        # Generate custom terrain data
        mock_data = MockTerrainData.create_sample(ski_area, grid_size)
        
        # Modify elevation data for specific scenarios
        if scenario_name == "flat_terrain":
            # Create flat terrain
            mock_data.elevation_data = [
                [1000.0 for _ in range(grid_size[1])]
                for _ in range(grid_size[0])
            ]
        elif scenario_name == "steep_mountain":
            # Create steep mountain
            center_row, center_col = grid_size[0] // 2, grid_size[1] // 2
            mock_data.elevation_data = [
                [max(0, 2000 - abs(i - center_row) * 100 - abs(j - center_col) * 100)
                 for j in range(grid_size[1])]
                for i in range(grid_size[0])
            ]
        
        # Calculate statistics
        all_elevations = [elev for row in mock_data.elevation_data for elev in row]
        min_elev, max_elev = min(all_elevations), max(all_elevations)
        
        print(f"  Ski Area: {mock_data.ski_area}")
        print(f"  Grid Size: {mock_data.grid_size}")
        print(f"  Elevation Range: {min_elev:.0f}m - {max_elev:.0f}m")
        print(f"  Data Points: {len(all_elevations)}")


async def workflow_monitoring_example():
    """
    Example: Monitor workflow execution with detailed logging.
    
    This demonstrates how to set up comprehensive monitoring and logging
    for workflow execution.
    """
    print("📊 Workflow Monitoring Example")
    print("=" * 40)
    
    config = get_test_config()
    
    # Create logger with detailed configuration
    logger = TestLogger("monitoring_example", config)
    agent_manager = Mock()
    agent_manager.is_agent_healthy.return_value = True
    
    async with WorkflowSimulator(config, agent_manager, logger) as simulator:
        # Monitor multiple workflows
        workflows_to_monitor = [
            WorkflowType.TERRAIN_LOADING,
            WorkflowType.CACHE_INTEGRATION,
            WorkflowType.ERROR_SCENARIOS
        ]
        
        monitoring_data = {}
        
        for workflow_type in workflows_to_monitor:
            print(f"\n🔍 Monitoring {workflow_type.value}...")
            
            start_time = asyncio.get_event_loop().time()
            result = await simulator.simulate_workflow(workflow_type)
            end_time = asyncio.get_event_loop().time()
            
            # Collect monitoring data
            monitoring_data[workflow_type] = {
                "duration": result.duration,
                "wall_clock_time": end_time - start_time,
                "steps_completed": result.steps_completed,
                "steps_total": result.steps_total,
                "success": result.success,
                "error_category": result.error.category if result.error else None
            }
            
            # Log detailed information
            print(f"  Duration: {result.duration:.3f}s")
            print(f"  Wall Clock: {end_time - start_time:.3f}s")
            print(f"  Progress: {result.steps_completed}/{result.steps_total}")
            print(f"  Status: {'✅' if result.success else '❌'}")
        
        # Summary report
        print(f"\n📈 Monitoring Summary:")
        total_duration = sum(data["duration"] for data in monitoring_data.values())
        successful_workflows = sum(1 for data in monitoring_data.values() if data["success"])
        
        print(f"  Total Duration: {total_duration:.3f}s")
        print(f"  Success Rate: {successful_workflows}/{len(monitoring_data)}")
        print(f"  Average Duration: {total_duration/len(monitoring_data):.3f}s")


if __name__ == "__main__":
    # Run advanced examples
    asyncio.run(custom_terrain_data_example())
    print()
    asyncio.run(workflow_monitoring_example())