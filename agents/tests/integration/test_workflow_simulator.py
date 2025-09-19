"""
Unit tests for WorkflowSimulator.

Tests the workflow simulation functionality including terrain loading,
cache integration, offline mode, error scenarios, and performance validation.
"""

import asyncio
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import pytest
import pytest_asyncio

from .workflow_simulator import (
    WorkflowSimulator, WorkflowType, SimulationState, WorkflowResult,
    MockTerrainData, WorkflowStep
)
from .config import TestConfig, AgentConfig
from .models import TestCategory, TestStatus, Severity
from .agent_lifecycle import AgentLifecycleManager
from .logging_utils import TestLogger


class TestMockTerrainData:
    """Test MockTerrainData functionality."""
    
    def test_create_sample_default(self):
        """Test creating sample terrain data with defaults."""
        data = MockTerrainData.create_sample()
        
        assert data.ski_area == "test_area"
        assert data.grid_size == (32, 32)
        assert len(data.elevation_data) == 32
        assert len(data.elevation_data[0]) == 32
        assert "min_elevation" in data.metadata
        assert "max_elevation" in data.metadata
    
    def test_create_sample_custom(self):
        """Test creating sample terrain data with custom parameters."""
        data = MockTerrainData.create_sample("chamonix", (64, 64))
        
        assert data.ski_area == "chamonix"
        assert data.grid_size == (64, 64)
        assert len(data.elevation_data) == 64
        assert len(data.elevation_data[0]) == 64
    
    def test_elevation_data_structure(self):
        """Test that elevation data has proper structure."""
        data = MockTerrainData.create_sample("test", (16, 16))
        
        # Check all rows have same length
        for row in data.elevation_data:
            assert len(row) == 16
        
        # Check elevation values are reasonable
        all_elevations = [elev for row in data.elevation_data for elev in row]
        assert all(isinstance(elev, (int, float)) for elev in all_elevations)
        assert all(elev >= 0 for elev in all_elevations)


class TestWorkflowSimulator:
    """Test WorkflowSimulator functionality."""
    
    @pytest_asyncio.fixture
    async def config(self):
        """Create test configuration."""
        config = TestConfig()
        config.agents = {
            "hill_metrics": AgentConfig(
                name="hill_metrics",
                port=8001,
                required_methods=["get_terrain_data"]
            ),
            "weather": AgentConfig(
                name="weather",
                port=8002,
                required_methods=["get_weather_data"]
            )
        }
        return config
    
    @pytest_asyncio.fixture
    async def agent_manager(self, config):
        """Create mock agent manager."""
        manager = Mock(spec=AgentLifecycleManager)
        manager.is_agent_healthy.return_value = True
        return manager
    
    @pytest_asyncio.fixture
    async def logger(self, config):
        """Create test logger."""
        return TestLogger("test_workflow", config)
    
    @pytest_asyncio.fixture
    async def simulator(self, config, agent_manager, logger):
        """Create workflow simulator."""
        simulator = WorkflowSimulator(config, agent_manager, logger)
        
        # Mock HTTP client
        mock_client = AsyncMock()
        simulator.http_client = mock_client
        
        # Set up temp directory
        simulator.temp_dir = Path(tempfile.mkdtemp())
        simulator.mock_cache_dir = simulator.temp_dir / "cache"
        simulator.mock_cache_dir.mkdir(parents=True, exist_ok=True)
        
        yield simulator
        
        # Cleanup
        if simulator.temp_dir and simulator.temp_dir.exists():
            shutil.rmtree(simulator.temp_dir, ignore_errors=True)
    
    def test_workflow_definitions(self, simulator):
        """Test that all workflow types are defined."""
        for workflow_type in WorkflowType:
            assert workflow_type in simulator.workflows
            steps = simulator.workflows[workflow_type]
            assert isinstance(steps, list)
            assert len(steps) > 0
            assert all(isinstance(step, WorkflowStep) for step in steps)
    
    def test_terrain_loading_workflow_definition(self, simulator):
        """Test terrain loading workflow definition."""
        steps = simulator.workflows[WorkflowType.TERRAIN_LOADING]
        
        step_names = [step.name for step in steps]
        expected_steps = [
            "select_ski_area",
            "configure_grid_size",
            "request_terrain_data",
            "process_elevation_data",
            "validate_terrain_mesh",
            "cache_terrain_data"
        ]
        
        assert step_names == expected_steps
        assert all(step.required for step in steps)
    
    def test_cache_integration_workflow_definition(self, simulator):
        """Test cache integration workflow definition."""
        steps = simulator.workflows[WorkflowType.CACHE_INTEGRATION]
        
        step_names = [step.name for step in steps]
        expected_steps = [
            "initialize_cache",
            "store_terrain_data",
            "retrieve_cached_data",
            "validate_cache_integrity",
            "test_cache_invalidation",
            "test_cache_cleanup"
        ]
        
        assert step_names == expected_steps
    
    def test_offline_mode_workflow_definition(self, simulator):
        """Test offline mode workflow definition."""
        steps = simulator.workflows[WorkflowType.OFFLINE_MODE]
        
        step_names = [step.name for step in steps]
        expected_steps = [
            "populate_cache",
            "simulate_network_failure",
            "test_offline_terrain_loading",
            "validate_fallback_behavior",
            "test_partial_data_scenarios",
            "restore_connectivity"
        ]
        
        assert step_names == expected_steps
    
    def test_error_scenarios_workflow_definition(self, simulator):
        """Test error scenarios workflow definition."""
        steps = simulator.workflows[WorkflowType.ERROR_SCENARIOS]
        
        step_names = [step.name for step in steps]
        expected_steps = [
            "test_agent_unavailable",
            "test_invalid_terrain_data",
            "test_network_timeouts",
            "test_memory_constraints",
            "test_cache_corruption",
            "validate_error_messages"
        ]
        
        assert step_names == expected_steps
    
    def test_performance_validation_workflow_definition(self, simulator):
        """Test performance validation workflow definition."""
        steps = simulator.workflows[WorkflowType.PERFORMANCE_VALIDATION]
        
        step_names = [step.name for step in steps]
        expected_steps = [
            "baseline_performance",
            "test_large_terrain_loading",
            "test_concurrent_requests",
            "test_memory_usage",
            "validate_response_times"
        ]
        
        assert step_names == expected_steps
    
    @pytest.mark.asyncio
    async def test_simulate_workflow_success(self, simulator):
        """Test successful workflow simulation."""
        # Mock all step executions to succeed
        with patch.object(simulator, '_execute_workflow_step', return_value=True):
            result = await simulator.simulate_workflow(WorkflowType.TERRAIN_LOADING)
        
        assert result.workflow_type == WorkflowType.TERRAIN_LOADING
        assert result.state == SimulationState.COMPLETED
        assert result.success is True
        assert result.error is None
        assert result.steps_completed == result.steps_total
        assert result.duration > 0
    
    @pytest.mark.asyncio
    async def test_simulate_workflow_failure(self, simulator):
        """Test workflow simulation with failure."""
        # Mock step execution to fail on third step
        def mock_execute_step(step, context):
            return step.name != "request_terrain_data"
        
        with patch.object(simulator, '_execute_workflow_step', side_effect=mock_execute_step):
            result = await simulator.simulate_workflow(WorkflowType.TERRAIN_LOADING)
        
        assert result.workflow_type == WorkflowType.TERRAIN_LOADING
        assert result.state == SimulationState.FAILED
        assert result.success is False
        assert result.error is not None
        assert result.steps_completed < result.steps_total
    
    @pytest.mark.asyncio
    async def test_simulate_workflow_exception(self, simulator):
        """Test workflow simulation with exception."""
        # Mock step execution to raise exception
        with patch.object(simulator, '_execute_workflow_step', side_effect=Exception("Test error")):
            result = await simulator.simulate_workflow(WorkflowType.TERRAIN_LOADING)
        
        assert result.workflow_type == WorkflowType.TERRAIN_LOADING
        assert result.state == SimulationState.FAILED
        assert result.success is False
        assert result.error is not None
        assert "Test error" in result.error.message
    
    @pytest.mark.asyncio
    async def test_simulate_workflow_invalid_type(self, simulator):
        """Test workflow simulation with invalid type."""
        with pytest.raises(ValueError, match="Unknown workflow type"):
            await simulator.simulate_workflow("invalid_workflow")
    
    # Test individual workflow steps
    
    @pytest.mark.asyncio
    async def test_step_select_ski_area_success(self, simulator):
        """Test successful ski area selection."""
        context = {"ski_area": "chamonix"}
        result = await simulator._step_select_ski_area(context)
        
        assert result is True
        assert context["selected_ski_area"] == "chamonix"
    
    @pytest.mark.asyncio
    async def test_step_select_ski_area_invalid(self, simulator):
        """Test ski area selection with invalid area."""
        context = {"ski_area": "invalid_area"}
        result = await simulator._step_select_ski_area(context)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_step_configure_grid_size_success(self, simulator):
        """Test successful grid size configuration."""
        context = {"grid_size": (64, 64)}
        result = await simulator._step_configure_grid_size(context)
        
        assert result is True
        assert context["configured_grid_size"] == (64, 64)
    
    @pytest.mark.asyncio
    async def test_step_configure_grid_size_invalid(self, simulator):
        """Test grid size configuration with invalid size."""
        context = {"grid_size": (256, 256)}  # Too large
        result = await simulator._step_configure_grid_size(context)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_step_request_terrain_data_success(self, simulator):
        """Test successful terrain data request."""
        # Mock agent as healthy
        simulator.agent_manager.is_agent_healthy.return_value = True
        
        # Mock HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": {
                "ski_area": "chamonix",
                "grid_size": (64, 64),
                "elevation_data": [[1, 2], [3, 4]]
            }
        }
        simulator.http_client.post.return_value = mock_response
        
        context = {
            "agent": "hill_metrics",
            "selected_ski_area": "chamonix",
            "configured_grid_size": (64, 64)
        }
        
        result = await simulator._step_request_terrain_data(context)
        
        assert result is True
        assert "terrain_data" in context
        assert context["terrain_data"]["ski_area"] == "chamonix"
    
    @pytest.mark.asyncio
    async def test_step_request_terrain_data_agent_unhealthy(self, simulator):
        """Test terrain data request with unhealthy agent."""
        # Mock agent as unhealthy
        simulator.agent_manager.is_agent_healthy.return_value = False
        
        context = {"agent": "hill_metrics"}
        result = await simulator._step_request_terrain_data(context)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_step_request_terrain_data_http_error(self, simulator):
        """Test terrain data request with HTTP error."""
        # Mock agent as healthy
        simulator.agent_manager.is_agent_healthy.return_value = True
        
        # Mock HTTP error response
        mock_response = Mock()
        mock_response.status_code = 500
        simulator.http_client.post.return_value = mock_response
        
        context = {
            "agent": "hill_metrics",
            "selected_ski_area": "chamonix",
            "configured_grid_size": (64, 64)
        }
        
        result = await simulator._step_request_terrain_data(context)
        
        # Should fallback to mock data
        assert result is True
        assert "terrain_data" in context
    
    @pytest.mark.asyncio
    async def test_step_process_elevation_data_success(self, simulator):
        """Test successful elevation data processing."""
        context = {
            "terrain_data": {
                "elevation_data": [
                    [1.0, 2.0, 3.0],
                    [4.0, 5.0, 6.0],
                    [7.0, 8.0, 9.0]
                ]
            }
        }
        
        result = await simulator._step_process_elevation_data(context)
        
        assert result is True
        assert "processed_terrain" in context
        processed = context["processed_terrain"]
        assert processed["dimensions"] == (3, 3)
        assert processed["min_elevation"] == 1.0
        assert processed["max_elevation"] == 9.0
        assert processed["total_points"] == 9
    
    @pytest.mark.asyncio
    async def test_step_process_elevation_data_invalid(self, simulator):
        """Test elevation data processing with invalid data."""
        context = {
            "terrain_data": {
                "elevation_data": [
                    [1, 2, 3],
                    [4, 5]  # Invalid - inconsistent row length
                ]
            }
        }
        
        result = await simulator._step_process_elevation_data(context)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_step_validate_terrain_mesh_success(self, simulator):
        """Test successful terrain mesh validation."""
        context = {
            "processed_terrain": {
                "dimensions": (32, 32)
            }
        }
        
        result = await simulator._step_validate_terrain_mesh(context)
        
        assert result is True
        assert "mesh_validation" in context
        validation = context["mesh_validation"]
        assert validation["vertices"] == 32 * 32
        assert validation["triangles"] == 31 * 31 * 2
        assert validation["valid"] is True
    
    @pytest.mark.asyncio
    async def test_step_cache_terrain_data_success(self, simulator):
        """Test successful terrain data caching."""
        context = {
            "terrain_data": {
                "ski_area": "test_area",
                "grid_size": (32, 32),
                "elevation_data": [[1, 2], [3, 4]]
            }
        }
        
        result = await simulator._step_cache_terrain_data(context)
        
        assert result is True
        assert "cached_data" in context
        cached = context["cached_data"]
        assert "cache_key" in cached
        assert "cache_file" in cached
        
        # Verify file was created
        cache_file = Path(cached["cache_file"])
        assert cache_file.exists()
        
        # Verify file content
        with open(cache_file, 'r') as f:
            cached_content = json.load(f)
        assert cached_content["ski_area"] == "test_area"
    
    @pytest.mark.asyncio
    async def test_step_initialize_cache_success(self, simulator):
        """Test successful cache initialization."""
        context = {}
        result = await simulator._step_initialize_cache(context)
        
        assert result is True
        assert context["cache_initialized"] is True
        assert "cache_metadata_file" in context
        
        # Verify metadata file was created
        metadata_file = Path(context["cache_metadata_file"])
        assert metadata_file.exists()
        
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        assert metadata["version"] == "1.0"
        assert "created" in metadata
    
    @pytest.mark.asyncio
    async def test_step_store_terrain_data_success(self, simulator):
        """Test successful terrain data storage."""
        context = {}
        result = await simulator._step_store_terrain_data(context)
        
        assert result is True
        assert "stored_cache_key" in context
        assert "stored_cache_file" in context
        
        # Verify file was created
        cache_file = Path(context["stored_cache_file"])
        assert cache_file.exists()
        
        with open(cache_file, 'r') as f:
            stored_data = json.load(f)
        assert stored_data["ski_area"] == "test_area"
        assert "cached_at" in stored_data
    
    @pytest.mark.asyncio
    async def test_step_retrieve_cached_data_success(self, simulator):
        """Test successful cached data retrieval."""
        # First store data
        context = {}
        await simulator._step_store_terrain_data(context)
        
        # Then retrieve it
        result = await simulator._step_retrieve_cached_data(context)
        
        assert result is True
        assert "retrieved_data" in context
        retrieved = context["retrieved_data"]
        assert retrieved["ski_area"] == "test_area"
        assert "cached_at" in retrieved
    
    @pytest.mark.asyncio
    async def test_step_retrieve_cached_data_missing(self, simulator):
        """Test cached data retrieval with missing file."""
        context = {"stored_cache_key": "nonexistent_key"}
        result = await simulator._step_retrieve_cached_data(context)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_step_validate_cache_integrity_success(self, simulator):
        """Test successful cache integrity validation."""
        context = {
            "retrieved_data": {
                "ski_area": "test_area",
                "grid_size": (32, 32),
                "elevation_data": [[1, 2], [3, 4]],
                "metadata": {"test": "data"}
            }
        }
        
        result = await simulator._step_validate_cache_integrity(context)
        
        assert result is True
        assert context["cache_integrity_valid"] is True
    
    @pytest.mark.asyncio
    async def test_step_validate_cache_integrity_invalid(self, simulator):
        """Test cache integrity validation with invalid data."""
        context = {
            "retrieved_data": {
                "ski_area": "test_area",
                "grid_size": (2, 2),
                "elevation_data": [[1, 2], [3]],  # Invalid - inconsistent row length
                "metadata": {}
            }
        }
        
        result = await simulator._step_validate_cache_integrity(context)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_step_test_cache_invalidation_success(self, simulator):
        """Test successful cache invalidation."""
        # First store data
        context = {}
        await simulator._step_store_terrain_data(context)
        
        # Then test invalidation
        result = await simulator._step_test_cache_invalidation(context)
        
        assert result is True
        assert context["cache_invalidated"] is True
        
        # Verify file was deleted
        cache_file = Path(context["stored_cache_file"])
        assert not cache_file.exists()
    
    @pytest.mark.asyncio
    async def test_step_test_cache_cleanup_success(self, simulator):
        """Test successful cache cleanup."""
        context = {}
        result = await simulator._step_test_cache_cleanup(context)
        
        assert result is True
        assert context["cache_cleanup_successful"] is True
        
        # Verify some files remain
        remaining_files = list(simulator.mock_cache_dir.glob("test_cleanup_*.json"))
        assert len(remaining_files) == 3
    
    @pytest.mark.asyncio
    async def test_step_populate_cache_success(self, simulator):
        """Test successful cache population."""
        context = {}
        result = await simulator._step_populate_cache(context)
        
        assert result is True
        assert context["cache_populated"] is True
        assert "cached_ski_areas" in context
        
        # Verify cache files were created
        for ski_area in context["cached_ski_areas"]:
            cache_file = simulator.mock_cache_dir / f"{ski_area}_(32, 32).json"
            assert cache_file.exists()
    
    @pytest.mark.asyncio
    async def test_step_simulate_network_failure_success(self, simulator):
        """Test network failure simulation."""
        context = {}
        result = await simulator._step_simulate_network_failure(context)
        
        assert result is True
        assert context["network_available"] is False
        assert context["network_failure_simulated"] is True
    
    @pytest.mark.asyncio
    async def test_step_test_offline_terrain_loading_success(self, simulator):
        """Test successful offline terrain loading."""
        # First populate cache
        context = {}
        await simulator._step_populate_cache(context)
        
        # Simulate network failure
        await simulator._step_simulate_network_failure(context)
        
        # Test offline loading
        result = await simulator._step_test_offline_terrain_loading(context)
        
        assert result is True
        assert context["offline_terrain_loaded"] is True
        assert "offline_terrain_data" in context
    
    @pytest.mark.asyncio
    async def test_step_validate_fallback_behavior_success(self, simulator):
        """Test successful fallback behavior validation."""
        context = {
            "offline_terrain_loaded": True,
            "offline_terrain_data": {
                "ski_area": "chamonix",
                "cached_at": 1234567890
            }
        }
        
        result = await simulator._step_validate_fallback_behavior(context)
        
        assert result is True
        assert context["fallback_behavior_valid"] is True
    
    @pytest.mark.asyncio
    async def test_step_test_partial_data_scenarios_success(self, simulator):
        """Test successful partial data scenarios."""
        # First populate cache
        context = {}
        await simulator._step_populate_cache(context)
        
        # Test partial data handling
        result = await simulator._step_test_partial_data_scenarios(context)
        
        assert result is True
        assert context["partial_data_handled"] is True
    
    @pytest.mark.asyncio
    async def test_step_restore_connectivity_success(self, simulator):
        """Test successful connectivity restoration."""
        context = {"network_available": False}
        result = await simulator._step_restore_connectivity(context)
        
        assert result is True
        assert context["network_available"] is True
        assert context["network_failure_simulated"] is False
    
    @pytest.mark.asyncio
    async def test_step_test_agent_unavailable_success(self, simulator):
        """Test successful agent unavailable handling."""
        # Mock HTTP client to raise exception
        simulator.http_client.get.side_effect = Exception("Connection refused")
        
        context = {}
        result = await simulator._step_test_agent_unavailable(context)
        
        assert result is True
        assert context["agent_unavailable_handled"] is True
    
    @pytest.mark.asyncio
    async def test_step_test_invalid_terrain_data_success(self, simulator):
        """Test successful invalid terrain data handling."""
        context = {}
        result = await simulator._step_test_invalid_terrain_data(context)
        
        assert result is True
        assert context["invalid_data_detected"] is True
    
    @pytest.mark.asyncio
    async def test_step_test_network_timeouts_success(self, simulator):
        """Test successful network timeout handling."""
        context = {}
        result = await simulator._step_test_network_timeouts(context)
        
        assert result is True
        assert "timeout_handled" in context or "network_error_handled" in context
    
    @pytest.mark.asyncio
    async def test_step_test_memory_constraints_success(self, simulator):
        """Test successful memory constraints handling."""
        context = {}
        result = await simulator._step_test_memory_constraints(context)
        
        assert result is True
        assert "large_data_handled" in context or "memory_constraint_handled" in context
    
    @pytest.mark.asyncio
    async def test_step_test_cache_corruption_success(self, simulator):
        """Test successful cache corruption handling."""
        context = {}
        result = await simulator._step_test_cache_corruption(context)
        
        assert result is True
        assert context["corruption_detected"] is True
    
    @pytest.mark.asyncio
    async def test_step_validate_error_messages_success(self, simulator):
        """Test successful error message validation."""
        context = {
            "agent_unavailable_handled": True,
            "invalid_data_detected": True,
            "timeout_handled": True
        }
        
        result = await simulator._step_validate_error_messages(context)
        
        assert result is True
        assert context["error_messages_validated"] is True
    
    @pytest.mark.asyncio
    async def test_step_baseline_performance_success(self, simulator):
        """Test successful baseline performance measurement."""
        context = {}
        result = await simulator._step_baseline_performance(context)
        
        assert result is True
        assert "baseline_metrics" in context
        metrics = context["baseline_metrics"]
        assert "terrain_generation_time" in metrics
        assert "grid_size" in metrics
        assert "data_points" in metrics
    
    @pytest.mark.asyncio
    async def test_step_test_large_terrain_loading_success(self, simulator):
        """Test successful large terrain loading."""
        context = {"grid_size": (128, 128)}
        result = await simulator._step_test_large_terrain_loading(context)
        
        assert result is True
        assert "large_terrain_metrics" in context
        metrics = context["large_terrain_metrics"]
        assert "loading_time" in metrics
        assert metrics["loading_time"] < 5.0
    
    @pytest.mark.asyncio
    async def test_step_test_concurrent_requests_success(self, simulator):
        """Test successful concurrent requests."""
        context = {}
        result = await simulator._step_test_concurrent_requests(context)
        
        assert result is True
        assert "concurrent_metrics" in context
        metrics = context["concurrent_metrics"]
        assert metrics["requests"] == 5
        assert metrics["responses"] == 5
        assert metrics["total_time"] < 2.0
    
    @pytest.mark.asyncio
    async def test_step_test_memory_usage_success(self, simulator):
        """Test successful memory usage monitoring."""
        context = {}
        result = await simulator._step_test_memory_usage(context)
        
        assert result is True
        assert "memory_metrics" in context
        metrics = context["memory_metrics"]
        assert "initial_memory_mb" in metrics
        assert "peak_memory_mb" in metrics
        assert "memory_increase_mb" in metrics
    
    @pytest.mark.asyncio
    async def test_step_validate_response_times_success(self, simulator):
        """Test successful response time validation."""
        context = {
            "baseline_metrics": {"terrain_generation_time": 0.5},
            "large_terrain_metrics": {"loading_time": 2.0},
            "concurrent_metrics": {"avg_time_per_request": 0.3}
        }
        
        result = await simulator._step_validate_response_times(context)
        
        assert result is True
        assert context["performance_requirements_met"] is True
    
    @pytest.mark.asyncio
    async def test_step_validate_response_times_failure(self, simulator):
        """Test response time validation failure."""
        context = {
            "baseline_metrics": {"terrain_generation_time": 2.0},  # Too slow
            "large_terrain_metrics": {"loading_time": 10.0},  # Too slow
            "concurrent_metrics": {"avg_time_per_request": 1.0}  # Too slow
        }
        
        result = await simulator._step_validate_response_times(context)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_simulate_all_workflows(self, simulator):
        """Test simulating all workflows."""
        # Mock all step executions to succeed
        with patch.object(simulator, '_execute_workflow_step', return_value=True):
            results = await simulator.simulate_all_workflows()
        
        assert len(results) == len(WorkflowType)
        
        for workflow_type in WorkflowType:
            assert workflow_type in results
            result = results[workflow_type]
            assert result.workflow_type == workflow_type
            assert result.success is True
            assert result.state == SimulationState.COMPLETED
    
    def test_create_test_results_success(self, simulator):
        """Test creating test results from successful workflows."""
        workflow_results = {
            WorkflowType.TERRAIN_LOADING: WorkflowResult(
                workflow_type=WorkflowType.TERRAIN_LOADING,
                state=SimulationState.COMPLETED,
                duration=1.5,
                steps_completed=6,
                steps_total=6,
                success=True
            )
        }
        
        test_results = simulator.create_test_results(workflow_results)
        
        assert len(test_results) == 1
        result = test_results[0]
        assert result.name == "workflow_terrain_loading"
        assert result.category == TestCategory.WORKFLOWS
        assert result.status == TestStatus.PASSED
        assert result.duration == 1.5
        assert result.context["steps_completed"] == 6
        assert result.context["steps_total"] == 6
    
    def test_create_test_results_failure(self, simulator):
        """Test creating test results from failed workflows."""
        from .models import TestError
        
        error = TestError(
            category="workflow",
            severity=Severity.HIGH,
            message="Step failed"
        )
        
        workflow_results = {
            WorkflowType.TERRAIN_LOADING: WorkflowResult(
                workflow_type=WorkflowType.TERRAIN_LOADING,
                state=SimulationState.FAILED,
                duration=0.8,
                steps_completed=2,
                steps_total=6,
                success=False,
                error=error
            )
        }
        
        test_results = simulator.create_test_results(workflow_results)
        
        assert len(test_results) == 1
        result = test_results[0]
        assert result.name == "workflow_terrain_loading"
        assert result.category == TestCategory.WORKFLOWS
        assert result.status == TestStatus.FAILED
        assert result.duration == 0.8
        assert result.error == error
        assert result.message == "Step failed"
        assert result.context["steps_completed"] == 2
        assert result.context["steps_total"] == 6


if __name__ == "__main__":
    pytest.main([__file__])