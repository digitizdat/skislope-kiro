# Integration Testing Infrastructure

This package provides comprehensive end-to-end validation for the Alpine Ski Slope Environment Viewer's multi-agent architecture. The infrastructure validates API contracts, cross-system communication, environment consistency, and complete user workflows.

## Overview

The integration testing infrastructure consists of four core components:

1. **Configuration System** - Environment detection and test configuration management
2. **Data Models** - Structured test results, diagnostics, and reporting
3. **Logging & Diagnostics** - Comprehensive logging and system diagnostic collection
4. **Test Orchestration** - Coordinated test execution and result aggregation

## Quick Start

### Basic Usage

```python
from agents.tests.integration import get_test_config, TestLogger, TestResults
from agents.tests.integration.models import TestResult, TestCategory, TestStatus

# Get configuration (automatically detects environment)
config = get_test_config()

# Set up logging
logger = TestLogger("my_test", config)
logger.info("Starting integration test")

# Create test results
results = TestResults()
test = TestResult("api_test", TestCategory.API_CONTRACTS, TestStatus.NOT_STARTED, 0.0)
test.mark_passed("All API contracts validated")
results.add_result(test)

# Save results
results.finalize()
print(f"Success rate: {results.summary.success_rate:.1f}%")
```

### Using Context Manager

```python
from agents.tests.integration.logging_utils import integration_test_context

config = get_test_config()

with integration_test_context("my_test", config, test_id="001") as logger:
    logger.info("Running test within managed context")
    # Test logic here
    logger.info("Test completed successfully")
```

### Configuration Overrides

```python
# Override specific settings
overrides = {
    "max_workers": 8,
    "timeouts.agent_startup": 60,
    "log_level": "INFO",
    "reporting.detail_level": "verbose"
}

config = get_test_config(overrides)
```

## Core Components

### Configuration System (`config.py`)

Provides centralized configuration management with automatic environment detection:

- **Environment Detection**: Automatically detects LOCAL, CI, or PRODUCTION environments
- **Agent Configuration**: Manages settings for hill_metrics, weather, and equipment agents
- **Timeout Management**: Configurable timeouts for different operations
- **Directory Setup**: Automatic creation of temp and log directories

**Key Classes:**
- `TestConfig` - Main configuration dataclass
- `ConfigManager` - Manages configuration with environment detection
- `AgentConfig` - Individual agent server configuration

### Data Models (`models.py`)

Structured data models for test results and diagnostics:

- **Test Results**: Hierarchical test result tracking with categories
- **Error Handling**: Structured error information with context and suggestions
- **Agent Health**: Health status tracking for agent servers
- **Performance Metrics**: Performance and resource usage tracking

**Key Classes:**
- `TestResult` - Individual test result with lifecycle methods
- `TestResults` - Aggregated results with summary statistics
- `TestError` - Structured error information
- `AgentHealthStatus` - Agent health and availability tracking

### Logging & Diagnostics (`logging_utils.py`)

Comprehensive logging and diagnostic collection:

- **Structured Logging**: Context-aware logging with multiple output formats
- **System Diagnostics**: Automatic collection of system, environment, and network info
- **Artifact Management**: Test artifact creation and cleanup
- **Context Management**: Test execution context with automatic cleanup

**Key Classes:**
- `TestLogger` - Enhanced logger with structured output
- `DiagnosticCollector` - System diagnostic information collection
- `TestArtifactManager` - Test artifact lifecycle management

## Environment Detection

The system automatically detects the execution environment:

### Local Development
- Default configuration for development
- Debug logging enabled
- Parallel execution enabled
- Standard reporting detail

### CI/CD Environment
- Extended timeouts for slower CI systems
- Verbose reporting for debugging
- Parallel execution optimized for CI
- Artifact retention configured

### Production Environment
- Conservative timeouts and retry settings
- Minimal reporting to reduce noise
- Sequential execution for stability
- Enhanced error handling

## Test Categories

Tests are organized into categories for better organization and selective execution:

- `API_CONTRACTS` - Frontend/backend API compatibility
- `COMMUNICATION` - Cross-system communication protocols
- `ENVIRONMENT` - System dependencies and configuration
- `WORKFLOWS` - End-to-end user scenarios
- `PERFORMANCE` - Performance and load testing
- `SECURITY` - Security and data handling validation

## Error Handling

Comprehensive error handling with structured information:

```python
from agents.tests.integration.models import TestError, Severity

# Create structured error
error = TestError(
    category="api_contracts",
    severity=Severity.HIGH,
    message="API method not found",
    context={"method": "get_terrain_data", "agent": "hill_metrics"},
    suggested_fix="Ensure agent server is running and method is implemented"
)

# Create from exception
try:
    # Some operation
    pass
except Exception as e:
    error = TestError.from_exception(e, "communication")
```

## Diagnostic Collection

Automatic collection of system diagnostics for debugging:

```python
from agents.tests.integration.logging_utils import DiagnosticCollector

collector = DiagnosticCollector(config)
diagnostics = collector.collect_all_diagnostics()

# Includes:
# - System information (platform, memory, CPU)
# - Environment variables and paths
# - Network configuration
# - Running processes
# - Package versions
```

## Configuration Reference

### TestConfig Structure

```python
@dataclass
class TestConfig:
    environment: TestEnvironment          # AUTO-DETECTED
    agents: Dict[str, AgentConfig]       # Agent configurations
    timeouts: TimeoutConfig              # Operation timeouts
    env_config: EnvironmentConfig        # Environment settings
    reporting: ReportingConfig           # Report generation
    log_level: LogLevel                  # Logging verbosity
    parallel_execution: bool             # Parallel test execution
    max_workers: int                     # Maximum parallel workers
    retry_attempts: int                  # Retry attempts for failures
    retry_delay: float                   # Delay between retries
```

### Agent Configuration

```python
@dataclass
class AgentConfig:
    name: str                           # Agent identifier
    host: str = "localhost"             # Agent host
    port: int = 8000                    # Agent port
    startup_timeout: int = 30           # Startup timeout (seconds)
    health_endpoint: str = "/health"    # Health check endpoint
    enabled: bool = True                # Enable/disable agent
    required_methods: List[str]         # Required API methods
```

### Timeout Configuration

```python
@dataclass
class TimeoutConfig:
    agent_startup: int = 30             # Agent startup timeout
    test_execution: int = 300           # Test execution timeout
    network_request: int = 10           # Network request timeout
    health_check: int = 5               # Health check timeout
    shutdown: int = 15                  # Shutdown timeout
```

## Best Practices

### Test Organization
- Use descriptive test names that indicate what is being tested
- Group related tests into appropriate categories
- Include context information in test results

### Error Handling
- Always provide suggested fixes for common errors
- Include relevant context information
- Use appropriate severity levels

### Performance
- Use parallel execution for independent tests
- Set appropriate timeouts for different environments
- Clean up artifacts regularly

### Logging
- Use structured logging with context
- Include relevant diagnostic information
- Use appropriate log levels

## Integration with Existing Tests

The infrastructure integrates with the existing test suite:

```python
# In existing test files
from agents.tests.integration import get_test_config, TestLogger

def test_agent_integration():
    config = get_test_config()
    logger = TestLogger("agent_test", config)
    
    # Your existing test logic
    logger.info("Running agent integration test")
    
    # Test assertions
    assert agent_is_healthy()
    logger.info("Agent integration test passed")
```

## Running Tests

```bash
# Run core infrastructure tests
uv run pytest agents/tests/integration/test_core_infrastructure.py -v

# Run example usage
uv run python -m agents.tests.integration.example_usage

# Run with specific configuration
ENVIRONMENT=ci uv run pytest agents/tests/integration/ -v
```

## File Structure

```
agents/tests/integration/
├── __init__.py                    # Package initialization
├── config.py                     # Configuration management
├── models.py                     # Data models and interfaces
├── logging_utils.py              # Logging and diagnostics
├── test_core_infrastructure.py   # Core infrastructure tests
├── example_usage.py              # Usage examples
└── README.md                     # This documentation
```

## Requirements Satisfied

This core infrastructure satisfies the following requirements from the specification:

- **Requirement 5.1**: Fast feedback with configurable timeouts and parallel execution
- **Requirement 6.1**: Comprehensive test reporting with detailed diagnostics
- **Environment Detection**: Automatic detection of LOCAL, CI, and PRODUCTION environments
- **Structured Logging**: Context-aware logging with multiple output formats
- **Diagnostic Collection**: Comprehensive system diagnostic information
- **Configuration Management**: Centralized configuration with environment-specific settings

## Next Steps

This core infrastructure provides the foundation for implementing the remaining integration testing components:

1. **Agent Lifecycle Manager** - For starting/stopping agents during tests
2. **API Contract Validator** - For validating frontend/backend API compatibility
3. **Environment Validator** - For checking system dependencies
4. **Communication Validator** - For testing cross-system communication
5. **Workflow Simulator** - For end-to-end scenario testing

Each component will build upon this core infrastructure to provide comprehensive integration testing capabilities.