# Alpine Ski Simulator - Comprehensive Testing Guide

## Overview

The Alpine Ski Simulator employs a multi-layered testing strategy that ensures reliability across the entire system architecture. This comprehensive guide covers all testing infrastructure components, from individual unit tests to full end-to-end integration validation.

## Table of Contents

1. [Testing Architecture Overview](#testing-architecture-overview)
2. [Frontend Testing Environment](#frontend-testing-environment)
3. [Agent Testing Infrastructure](#agent-testing-infrastructure)
4. [Integration Testing Infrastructure](#integration-testing-infrastructure)
5. [Deployment Validation](#deployment-validation)
6. [CI/CD Pipeline Integration](#cicd-pipeline-integration)
7. [Development Workflow](#development-workflow)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Best Practices](#best-practices)

## Testing Architecture Overview

### System Architecture

```mermaid
graph TB
    subgraph "Testing Layers"
        A[Unit Tests] --> B[Integration Tests]
        B --> C[End-to-End Tests]
        C --> D[Deployment Validation]
    end
    
    subgraph "Frontend Testing"
        E[Component Tests] --> F[Service Tests]
        F --> G[Browser API Mocks]
        G --> H[WebGL/Three.js Tests]
    end
    
    subgraph "Backend Testing"
        I[Agent Unit Tests] --> J[JSON-RPC Tests]
        J --> K[MCP Protocol Tests]
        K --> L[Agent Integration]
    end
    
    subgraph "Cross-System Testing"
        M[API Contract Validation] --> N[Communication Tests]
        N --> O[Environment Validation]
        O --> P[Workflow Simulation]
    end
    
    subgraph "Production Validation"
        Q[Smoke Tests] --> R[Performance Tests]
        R --> S[Security Validation]
        S --> T[Monitoring Integration]
    end
```

### Testing Components

| Component | Purpose | Technology | Location |
|-----------|---------|------------|----------|
| **Frontend Tests** | UI components, services, browser APIs | Vitest, jsdom, Testing Library | `src/test/` |
| **Agent Tests** | Python agent servers, JSON-RPC, MCP | pytest, httpx, asyncio | `agents/tests/` |
| **Integration Tests** | Cross-system validation, API contracts | Python, TypeScript | `agents/tests/integration/` |
| **Deployment Tests** | Production readiness, smoke tests | Python scripts | `scripts/` |
| **CI/CD Tests** | Automated validation, pre-commit hooks | GitHub Actions, Lefthook | `.github/`, `.lefthook.yml` |

## Frontend Testing Environment

### Quick Start

```bash
# Run frontend unit tests (jsdom environment)
npm test

# Run with coverage
npm run test:coverage

# Run in watch mode
npm run test:watch

# Run integration tests (Node environment for real network calls)
npm run test:integration
```

### Environment Configuration

The frontend testing uses **two different environments** based on test type:

1. **Unit Tests** (`vitest.config.ts`): Use `jsdom` environment for component and service testing with mocked browser APIs
2. **Integration Tests** (`vitest.integration.config.ts`): Use `Node` environment to enable real network calls to agent servers

**Why Two Environments?**
- **jsdom**: Perfect for isolated unit tests with mocked fetch, localStorage, WebGL context
- **Node**: Required for integration tests that make real HTTP requests to localhost agent servers
- **Breaking Change**: Integration tests switched from jsdom to Node in commit 269531d to enable real network communication

### Key Features

- **WebGL Context Mocking**: Headless Three.js testing using canvas package
- **IndexedDB Mocking**: Complete cache system testing with fake-indexeddb
- **Browser API Mocks**: localStorage, fetch, Web Audio API, File APIs
- **Async Testing Utilities**: Promise handling, timeout management, race condition testing
- **Component Testing**: React component testing with Testing Library

### Example Frontend Unit Test (jsdom)

```typescript
import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { initializeTestEnvironment } from '../test/testSetup';
import { TerrainViewer } from './TerrainViewer';

describe('TerrainViewer Component', () => {
  beforeEach(async () => {
    await initializeTestEnvironment();
  });

  it('should render terrain data', async () => {
    const mockData = { elevation: [100, 200, 300] };
    
    render(<TerrainViewer terrainData={mockData} />);
    
    expect(screen.getByText('Terrain Loaded')).toBeInTheDocument();
  });
});
```

### Example Frontend Integration Test (Node)

```typescript
import { describe, it, expect, beforeAll } from 'vitest';
import { AgentClient, createAgentClient } from '../services/AgentClient';

// Fetch polyfill for Node environment
if (typeof globalThis.fetch === 'undefined') {
  try {
    const { fetch } = await import('undici');
    globalThis.fetch = fetch as any;
  } catch {
    const fetch = (await import('node-fetch')).default;
    globalThis.fetch = fetch as any;
  }
}

describe('AgentClient Integration Tests', () => {
  let agentClient: AgentClient;
  let agentsAvailable = false;

  beforeAll(async () => {
    agentClient = createAgentClient();
    
    // Check if agents are running
    try {
      const healthChecks = await Promise.allSettled([
        fetch('http://localhost:8001/health'),
        fetch('http://localhost:8002/health'),
        fetch('http://localhost:8003/health')
      ]);
      
      agentsAvailable = healthChecks.every(result => 
        result.status === 'fulfilled' && result.value.ok
      );
    } catch (error) {
      console.warn('⚠️  Could not connect to agent servers');
    }
  });

  it('should communicate with hill metrics agent', async () => {
    if (!agentsAvailable) {
      console.log('⏭️  Skipping - agents not available');
      return;
    }

    const response = await agentClient.callHillMetricsAgent({
      area: mockSkiArea,
      gridSize: GridSize.MEDIUM,
      includeAnalysis: true
    });
    
    expect(response.data).toBeDefined();
  });
});
```

**📖 Detailed Documentation**: [Frontend Test Environment Guide](./FRONTEND_TEST_ENVIRONMENT.md)

## Agent Testing Infrastructure

### Quick Start

```bash
# Run all agent tests
uv run pytest agents/tests/ -v

# Run specific agent tests
uv run pytest agents/tests/test_hill_metrics.py -v

# Test agents with live servers
uv run python scripts/test_agents.py

# Run agent integration tests
uv run pytest agents/tests/test_integration.py -v
```

### Agent Test Structure

```
agents/tests/
├── test_hill_metrics.py      # Hill metrics agent unit tests
├── test_weather.py           # Weather agent unit tests  
├── test_equipment.py         # Equipment agent unit tests
├── test_integration.py       # Agent integration tests
└── integration/              # Integration test infrastructure
    ├── api_contract_validator.py
    ├── environment_validator.py
    ├── communication_validator.py
    └── workflow_simulator.py
```

### Agent Unit Tests

Each agent has comprehensive unit tests covering:

- **JSON-RPC Method Testing**: All exposed methods with various parameters
- **Data Processing**: Terrain processing, weather data parsing, equipment status
- **Error Handling**: Invalid inputs, network failures, data corruption
- **Protocol Compliance**: JSON-RPC 2.0 specification adherence
- **MCP Integration**: Model Context Protocol tool registration

### Example Agent Test

```python
import pytest
from agents.hill_metrics.server import HillMetricsAgent

@pytest.mark.asyncio
async def test_get_hill_metrics():
    agent = HillMetricsAgent()
    
    params = {
        "bounds": {"north": 46.0, "south": 45.9, "east": 7.1, "west": 7.0},
        "grid_size": "32x32"
    }
    
    result = await agent.get_hill_metrics(params)
    
    assert "elevation_data" in result
    assert "slope_analysis" in result
    assert len(result["elevation_data"]) == 32 * 32
```

### Agent Integration Testing

The agent integration tests validate:

- **Server Startup**: Agents start correctly and respond to health checks
- **JSON-RPC Communication**: Request/response handling with real network calls
- **MCP Tool Registration**: Tools are properly registered and discoverable
- **Cross-Agent Communication**: Agents can communicate when needed
- **Performance**: Response times meet requirements under load

## Integration Testing Infrastructure

### Quick Start

```bash
# Run full integration test suite
uv run python scripts/test_integration.py

# Run with CI mode
uv run python scripts/test_integration.py --ci-mode

# Run specific integration test categories
uv run python agents/tests/integration/run_integration_tests.py --categories api_contracts,communication

# View integration test dashboard
uv run python agents/tests/integration/dashboard.py
```

### Integration Test Categories

#### 1. API Contract Validation

Ensures frontend and backend API compatibility:

```python
from agents.tests.integration.api_contract_validator import APIContractValidator

validator = APIContractValidator()

# Validate all agent contracts
results = await validator.validate_all_contracts()

# Check specific method signatures
hill_metrics_methods = validator.discover_agent_methods("hill_metrics")
assert "getHillMetrics" in hill_metrics_methods
```

**Key Features**:
- Method signature validation
- Parameter structure verification
- Response format checking
- Missing method detection

#### 2. Cross-System Communication

Validates network communication between components:

```python
from agents.tests.integration.communication_validator import CommunicationValidator

validator = CommunicationValidator()

# Test CORS configuration
cors_results = await validator.validate_cors_configuration()

# Test JSON-RPC protocol compliance
jsonrpc_results = await validator.validate_jsonrpc_protocol()

# Test MCP protocol support
mcp_results = await validator.validate_mcp_protocol()
```

**Key Features**:
- CORS header validation
- Protocol compliance testing
- Network timeout handling
- Data serialization verification

#### 3. Environment Validation

Ensures system dependencies and configuration:

```python
from agents.tests.integration.environment_validator import EnvironmentValidator

validator = EnvironmentValidator()

# Check Python environment
python_issues = await validator.validate_python_environment()

# Check package consistency (uv vs pip)
package_issues = await validator.validate_package_consistency()

# Check SSL configuration
ssl_issues = await validator.validate_ssl_configuration()
```

**Key Features**:
- Dependency verification
- Package manager consistency
- SSL/TLS validation
- Import testing

#### 4. Workflow Simulation

Tests complete user scenarios end-to-end:

```python
from agents.tests.integration.workflow_simulator import WorkflowSimulator

simulator = WorkflowSimulator()

# Simulate terrain loading workflow
result = await simulator.simulate_terrain_loading_workflow(
    ski_area="whistler",
    run_id="peak-2-creek",
    grid_size="medium"
)

# Test offline mode workflow
offline_result = await simulator.simulate_offline_mode_workflow()
```

**Key Features**:
- Complete user journey simulation
- Cache integration testing
- Error scenario validation
- Performance benchmarking

### Integration Test Dashboard

The integration testing infrastructure includes a web-based dashboard for monitoring test results:

```bash
# Start the dashboard
uv run python agents/tests/integration/dashboard.py

# Access at http://localhost:8080
```

**Dashboard Features**:
- Real-time test execution monitoring
- Historical test result trends
- Performance metrics visualization
- Error analysis and diagnostics
- Agent health monitoring

## Deployment Validation

### Smoke Tests

Lightweight tests for production readiness:

```bash
# Run deployment smoke tests
uv run python scripts/deployment_smoke_tests.py

# Generate detailed reports
uv run python scripts/deployment_smoke_tests.py --output-dir deployment-results
```

### Smoke Test Categories

1. **Environment Setup**: Python environment, package consistency, SSL configuration
2. **Import Validation**: All critical modules can be imported
3. **Build Verification**: Frontend builds successfully
4. **Configuration Validation**: All config files are valid
5. **Production Readiness**: Security checks, performance validation

### Example Smoke Test

```python
async def test_environment_setup(self):
    """Test that the environment is properly configured."""
    validator = EnvironmentValidator()
    
    # Check Python environment
    python_issues = await validator.validate_python_environment()
    if python_issues:
        raise Exception(f"Python environment issues: {python_issues}")
    
    # Check package consistency
    package_issues = await validator.validate_package_consistency()
    if package_issues:
        raise Exception(f"Package consistency issues: {package_issues}")
```

## CI/CD Pipeline Integration

### GitHub Actions Workflow

The testing infrastructure integrates with GitHub Actions for automated validation:

```yaml
name: Comprehensive Testing

on: [push, pull_request]

jobs:
  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Install dependencies
        run: npm install
      - name: Run frontend unit tests (jsdom)
        run: npm test
      - name: Run frontend integration tests (Node)
        run: npm run test:integration
      - name: Run frontend build
        run: npm run build

  agent-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python with uv
        uses: astral-sh/setup-uv@v1
      - name: Install dependencies
        run: uv sync
      - name: Run agent tests
        run: uv run pytest agents/tests/ -v
      - name: Run integration tests
        run: uv run python scripts/test_integration.py --ci-mode

  deployment-validation:
    runs-on: ubuntu-latest
    needs: [frontend-tests, agent-tests]
    steps:
      - uses: actions/checkout@v3
      - name: Setup environment
        run: |
          uv sync
          npm install
      - name: Run smoke tests
        run: uv run python scripts/deployment_smoke_tests.py
```

### Pre-commit Hooks

Lightweight validation using Lefthook:

```yaml
# .lefthook.yml
pre-commit:
  commands:
    dependency-check:
      run: scripts/check_dependencies.py
    api-contract-check:
      run: uv run python agents/tests/integration/api_contract_validator.py --quick
    python-imports:
      run: scripts/validate_imports.py
    quick-test:
      run: |
        npm run build
        uv run pytest agents/tests/ -x --tb=short
```

## Development Workflow

### Local Development Testing

```bash
# 1. Run quick validation before committing
npm test
uv run pytest agents/tests/ -x

# 2. Run integration tests for major changes
uv run python scripts/test_integration.py

# 3. Run smoke tests before deployment
uv run python scripts/deployment_smoke_tests.py
```

### Test-Driven Development

1. **Write Tests First**: Create tests for new features before implementation
2. **Red-Green-Refactor**: Follow TDD cycle for reliable development
3. **Integration Testing**: Add integration tests for cross-system features
4. **Performance Testing**: Include performance tests for critical paths

### Debugging Test Failures

```bash
# Debug frontend tests
npm test -- --reporter=verbose src/path/to/test.ts

# Debug agent tests with detailed output
uv run pytest agents/tests/test_hill_metrics.py -v -s

# Debug integration tests with logging
DEBUG=true uv run python scripts/test_integration.py

# Check test environment
uv run python scripts/validate-test-env.js
```

## Troubleshooting Guide

For detailed troubleshooting across all testing layers, see the [Comprehensive Testing Troubleshooting Guide](./COMPREHENSIVE_TESTING_TROUBLESHOOTING.md).

### Quick Issue Resolution

#### Frontend Test Issues

**Issue**: WebGL context creation fails
```bash
# Solution: Install canvas package dependencies
# macOS
brew install pkg-config cairo pango libpng jpeg giflib librsvg

# Ubuntu/Debian  
sudo apt-get install build-essential libcairo2-dev libpango1.0-dev libjpeg-dev libgif-dev librsvg2-dev
```

**Issue**: IndexedDB tests fail
```bash
# Solution: Ensure fake-indexeddb is properly imported
import 'fake-indexeddb/auto';
```

#### Agent Test Issues

**Issue**: Agent import failures
```bash
# Solution: Check Python environment
uv run python -c "import agents.hill_metrics.server"

# Fix dependency issues
uv sync
```

**Issue**: JSON-RPC method not found
```bash
# Solution: Verify method names match between frontend and backend
uv run python agents/tests/integration/api_contract_validator.py
```

#### Integration Test Issues

**Issue**: Agents fail to start
```bash
# Solution: Check port availability and dependencies
lsof -i :8001-8003
uv run python scripts/start_agents.py
```

**Issue**: CORS errors in tests
```bash
# Solution: Verify CORS configuration
uv run python agents/tests/integration/communication_validator.py
```

### Debug Information Collection

When reporting issues, collect this information:

```bash
# System information
uv --version
node --version
npm --version

# Test environment status
uv run python scripts/validate-test-env.js

# Integration test diagnostics
uv run python agents/tests/integration/dashboard.py --diagnostics
```

## Best Practices

### Test Organization

1. **Layer Tests Appropriately**: Unit → Integration → E2E → Deployment
2. **Use Appropriate Environments**: 
   - **jsdom** for unit tests with mocked browser APIs
   - **Node** for integration tests requiring real network calls
3. **Use Appropriate Mocks**: Mock external dependencies, use real implementations for integration
4. **Test Error Scenarios**: Include failure cases and edge conditions
5. **Maintain Test Data**: Use realistic test fixtures and mock data
6. **File Naming Convention**:
   - `*.test.ts` - Unit tests (jsdom environment)
   - `*.integration.test.ts` - Integration tests (Node environment)

### Performance Guidelines

1. **Fast Feedback**: Unit tests < 1s, Integration tests < 30s
2. **Parallel Execution**: Run independent tests concurrently
3. **Selective Testing**: Support running specific test categories
4. **Resource Management**: Clean up resources properly

### Maintenance

1. **Keep Tests Updated**: Update tests when APIs change
2. **Monitor Test Health**: Track test execution times and failure rates
3. **Refactor Tests**: Keep test code clean and maintainable
4. **Document Changes**: Update documentation when test infrastructure changes

### Security

1. **No Sensitive Data**: Use mock data, never real credentials
2. **Isolated Environments**: Keep test environments separate
3. **Secure CI/CD**: Protect test infrastructure and results
4. **Audit Testing**: Log test activities for security review

## Test Coverage Requirements

### Coverage Targets

- **Frontend**: 80% line coverage minimum
- **Agents**: 85% line coverage minimum  
- **Integration**: 100% critical path coverage
- **API Contracts**: 100% method coverage

### Coverage Reporting

```bash
# Frontend coverage
npm run test:coverage

# Agent coverage
uv run pytest agents/tests/ --cov=agents --cov-report=html

# Integration coverage
uv run python scripts/test_integration.py --coverage
```

## Monitoring and Alerting

### Continuous Testing

- **Scheduled Tests**: Run integration tests periodically in production
- **Health Monitoring**: Continuous agent health checks
- **Performance Tracking**: Monitor test execution times and system performance
- **Alert Thresholds**: Automated notifications for test failures

### Metrics Collection

- **Test Execution Times**: Track performance trends
- **Failure Rates**: Monitor test reliability
- **Coverage Trends**: Ensure coverage doesn't decrease
- **System Health**: Monitor agent and system health

## Conclusion

The Alpine Ski Simulator's comprehensive testing infrastructure ensures system reliability through multiple layers of validation. From individual component tests to full end-to-end workflows, the testing strategy catches issues early and maintains confidence in deployments.

**Key Benefits**:
- **Early Issue Detection**: Problems caught before reaching production
- **Regression Prevention**: Automated validation prevents breaking changes
- **Development Confidence**: Developers can refactor and add features safely
- **Production Reliability**: Deployment validation ensures system readiness

**Related Documentation**:
- [Testing Architecture Changes](./TESTING_ARCHITECTURE_CHANGES.md) - Key architectural decisions and breaking changes
- [Frontend Test Scripts Guide](./FRONTEND_TEST_SCRIPTS_GUIDE.md) - Complete reference for all npm test scripts
- [Comprehensive Testing Troubleshooting Guide](./COMPREHENSIVE_TESTING_TROUBLESHOOTING.md)
- [Frontend Test Environment Guide](./FRONTEND_TEST_ENVIRONMENT.md)
- [Frontend Test Troubleshooting](./FRONTEND_TEST_TROUBLESHOOTING.md)
- [Mock Usage Patterns](./FRONTEND_TEST_MOCK_PATTERNS.md)
- [Async Testing Best Practices](./FRONTEND_TEST_ASYNC_PATTERNS.md)

For specific testing scenarios or troubleshooting, refer to the detailed guides linked above or consult the integration test dashboard for real-time system status.