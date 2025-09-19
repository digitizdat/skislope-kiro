# WorkflowSimulator Usage Examples

This directory contains comprehensive examples of how to use the WorkflowSimulator for end-to-end testing in the Alpine Ski Slope Environment Viewer project.

## Overview

The WorkflowSimulator provides powerful capabilities for testing complete user workflows including:

- **Terrain Loading**: Complete user journey from ski area selection to cached terrain data
- **Cache Integration**: Full cache lifecycle testing with integrity validation  
- **Offline Mode**: Network failure simulation with graceful fallback testing
- **Error Scenarios**: Comprehensive error handling and graceful degradation validation
- **Performance Validation**: Real performance metrics collection and validation

## Example Files

### 📚 [example_usage.py](../example_usage.py)
**Main examples file** - Start here for basic usage patterns
- Quick start example (minimal setup)
- All workflows execution
- Mock data generation
- Error handling demonstration
- Context passing between steps
- Test infrastructure integration

### 🔧 [basic_usage.py](basic_usage.py)
**Fundamental usage patterns** - Core testing scenarios
- Single workflow execution with result validation
- Custom context data passing
- Batch workflow execution
- Converting results to standard test format
- Standalone examples for copy-paste usage

### 🚀 [advanced_usage.py](advanced_usage.py)
**Advanced techniques** - Complex testing scenarios
- Custom HTTP response mocking
- Error injection and testing
- Performance benchmarking
- Individual step execution
- Real file system operations
- Custom terrain data generation

### 🌍 [real_world_scenarios.py](real_world_scenarios.py)
**Realistic user scenarios** - Production-like testing
- Complete user session simulation
- Multi-ski area comparison testing
- Network degradation scenarios
- Performance under load testing
- Error recovery workflows
- Daily usage pattern simulation
- User behavior pattern testing

### 🔗 [integration_patterns.py](integration_patterns.py)
**CI/CD and monitoring integration** - Production deployment patterns
- CI/CD pipeline integration
- Monitoring and alerting setup
- Regression testing patterns
- Load testing integration
- Comprehensive test reporting
- Metrics collection and analysis

## Quick Start

```python
import asyncio
from unittest.mock import Mock
from agents.tests.integration.workflow_simulator import WorkflowSimulator, WorkflowType
from agents.tests.integration.config import get_test_config

async def quick_example():
    config = get_test_config()
    agent_manager = Mock()
    agent_manager.is_agent_healthy.return_value = True
    
    async with WorkflowSimulator(config, agent_manager) as simulator:
        result = await simulator.simulate_workflow(WorkflowType.TERRAIN_LOADING)
        print(f"Status: {'✅' if result.success else '❌'}")

asyncio.run(quick_example())
```

## Common Usage Patterns

### 1. Basic Workflow Testing

```python
# Test a single workflow
async with WorkflowSimulator(config, agent_manager) as simulator:
    result = await simulator.simulate_workflow(WorkflowType.TERRAIN_LOADING)
    assert result.duration > 0
    assert result.steps_total > 0
```

### 2. Batch Workflow Testing

```python
# Test all workflows
async with WorkflowSimulator(config, agent_manager) as simulator:
    results = await simulator.simulate_all_workflows()
    successful = sum(1 for r in results.values() if r.success)
    print(f"Success rate: {successful}/{len(results)}")
```

### 3. Custom Context Testing

```python
# Test with custom user data
context = {
    "ski_area": "chamonix",
    "grid_size": (128, 128),
    "user_preferences": {"detail_level": "ultra_high"}
}

async with WorkflowSimulator(config, agent_manager) as simulator:
    result = await simulator.simulate_workflow(WorkflowType.TERRAIN_LOADING, context)
    assert "user_preferences" in result.context
```

### 4. Error Scenario Testing

```python
# Test error handling
agent_manager = Mock()
agent_manager.is_agent_healthy.return_value = False  # Simulate failure

async with WorkflowSimulator(config, agent_manager) as simulator:
    result = await simulator.simulate_workflow(WorkflowType.TERRAIN_LOADING)
    assert not result.success  # Should fail gracefully
    assert result.error is not None
```

### 5. Performance Testing

```python
# Test performance characteristics
async with WorkflowSimulator(config, agent_manager) as simulator:
    result = await simulator.simulate_workflow(WorkflowType.PERFORMANCE_VALIDATION)
    
    if "baseline_metrics" in result.context:
        baseline = result.context["baseline_metrics"]
        assert baseline["terrain_generation_time"] < 1.0  # Performance requirement
```

### 6. Test Integration

```python
# Convert to standard test results
async with WorkflowSimulator(config, agent_manager) as simulator:
    workflow_result = await simulator.simulate_workflow(WorkflowType.CACHE_INTEGRATION)
    test_results = simulator.create_test_results({WorkflowType.CACHE_INTEGRATION: workflow_result})
    
    for test_result in test_results:
        assert test_result.category == TestCategory.WORKFLOWS
        assert test_result.duration > 0
```

## Mock Data Generation

The WorkflowSimulator includes `MockTerrainData` for generating realistic test data:

```python
from agents.tests.integration.workflow_simulator import MockTerrainData

# Generate terrain data for testing
mock_data = MockTerrainData.create_sample("chamonix", (64, 64))
print(f"Generated {len(mock_data.elevation_data) * len(mock_data.elevation_data[0])} data points")
print(f"Elevation range: {mock_data.metadata['min_elevation']}-{mock_data.metadata['max_elevation']}m")
```

## Available Workflows

| Workflow Type | Description | Steps | Use Case |
|---------------|-------------|-------|----------|
| `TERRAIN_LOADING` | Complete terrain loading simulation | 6 | User terrain loading experience |
| `CACHE_INTEGRATION` | Cache system testing | 6 | Offline functionality validation |
| `OFFLINE_MODE` | Offline mode simulation | 6 | Network failure scenarios |
| `ERROR_SCENARIOS` | Error handling testing | 6 | Graceful degradation validation |
| `PERFORMANCE_VALIDATION` | Performance testing | 5 | Performance requirements validation |

## Configuration Options

The WorkflowSimulator uses the standard test configuration system:

```python
from agents.tests.integration.config import get_test_config

# Basic configuration
config = get_test_config()

# Configuration with overrides
config = get_test_config({
    "timeouts.agent_startup": 60,
    "log_level": "DEBUG",
    "max_workers": 2
})
```

## Error Handling

The WorkflowSimulator provides comprehensive error handling:

- **Agent Failures**: Graceful handling when agents are unavailable
- **Network Issues**: Timeout and connectivity error simulation
- **Data Validation**: Invalid data format detection and handling
- **Resource Constraints**: Memory and performance limit testing
- **Cache Corruption**: Cache integrity and recovery testing

## Performance Monitoring

Built-in performance monitoring includes:

- **Execution Time**: Per-step and total workflow duration
- **Memory Usage**: Memory consumption tracking
- **Network Requests**: Request count and timing
- **Concurrent Operations**: Multi-user simulation support
- **Resource Utilization**: CPU and memory utilization tracking

## Best Practices

1. **Always use async context managers** for proper resource cleanup
2. **Mock external dependencies** for reliable testing
3. **Test both success and failure scenarios** for comprehensive coverage
4. **Use custom contexts** to simulate different user scenarios
5. **Convert results to standard test format** for integration
6. **Monitor performance metrics** to catch regressions
7. **Test error recovery** to ensure graceful degradation

## Running Examples

Each example file can be run independently:

```bash
# Run main examples
uv run python agents/tests/integration/example_usage.py

# Run basic usage examples
uv run python agents/tests/integration/examples/basic_usage.py

# Run advanced examples
uv run python agents/tests/integration/examples/advanced_usage.py

# Run real-world scenarios
uv run python agents/tests/integration/examples/real_world_scenarios.py

# Run integration patterns
uv run python agents/tests/integration/examples/integration_patterns.py
```

## Integration with pytest

All examples include pytest-compatible test classes:

```bash
# Run as pytest tests
uv run python -m pytest agents/tests/integration/examples/basic_usage.py -v
uv run python -m pytest agents/tests/integration/examples/advanced_usage.py -v
uv run python -m pytest agents/tests/integration/examples/real_world_scenarios.py -v
```

## Further Reading

- [WorkflowSimulator README](../WORKFLOW_SIMULATOR_README.md) - Detailed implementation documentation
- [Integration Test Infrastructure](../README.md) - Overall testing infrastructure
- [Configuration Guide](../config.py) - Configuration options and environment detection
- [Models Documentation](../models.py) - Data models and result structures

## Support

For questions or issues with the WorkflowSimulator examples:

1. Check the main [WORKFLOW_SIMULATOR_README.md](../WORKFLOW_SIMULATOR_README.md) for implementation details
2. Review the inline documentation in each example file
3. Run the examples to see expected output and behavior
4. Refer to the unit tests for additional usage patterns