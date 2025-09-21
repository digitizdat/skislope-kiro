# Testing Architecture Changes and Key Decisions

## Overview

This document tracks important architectural changes and decisions in the Alpine Ski Simulator testing infrastructure, particularly those that affect how tests are written and executed.

## Major Architectural Changes

### Integration Test Environment Change (Commit 269531d)

**Date**: September 21, 2025  
**Commit**: `269531d6b5ea1a87e5549aa2bfacdd23ed5c1487`  
**Breaking Change**: Integration tests now require Node environment instead of jsdom

#### Problem Solved

Integration tests were originally configured to use jsdom environment with mocked browser APIs. However, this prevented real network calls needed for testing communication with agent servers running on localhost.

**Symptoms**:
- Integration tests couldn't connect to agent servers
- Fetch calls were being mocked instead of making real HTTP requests
- "No result in JSON-RPC response" errors in AgentClient
- API contract validation failures due to mocked responses

#### Solution Implemented

**1. Separate Vitest Configuration**

Created `vitest.integration.config.ts` with Node environment:

```typescript
export default defineConfig({
  test: {
    // Use Node environment for integration tests to support real network calls
    environment: 'node',
    
    // Only run integration test files
    include: [
      'src/**/*.integration.test.{js,mjs,cjs,ts,mts,cts,jsx,tsx}'
    ],
    
    // Environment variables
    env: {
      NODE_ENV: 'test',
      INTEGRATION_TEST: 'true',
    }
  }
});
```

**2. Fetch Polyfill for Node Environment**

Added fetch polyfill support in integration tests:

```typescript
// For Node environment, we need to provide fetch if it's not available
if (typeof globalThis.fetch === 'undefined') {
  try {
    const { fetch } = await import('undici');
    globalThis.fetch = fetch as any;
  } catch {
    const fetch = (await import('node-fetch')).default;
    globalThis.fetch = fetch as any;
  }
}
```

**3. Updated Package Scripts**

```json
{
  "scripts": {
    "test": "vitest --run --reporter=verbose",
    "test:integration": "vitest run --config=vitest.integration.config.ts --reporter=verbose"
  }
}
```

**4. File Naming Convention**

- `*.test.ts` - Unit tests (jsdom environment with mocked APIs)
- `*.integration.test.ts` - Integration tests (Node environment with real network calls)

#### Results Achieved

✅ **Hill Metrics Agent** - JSON-RPC communication working  
✅ **Equipment Agent** - JSON-RPC communication working  
✅ **Weather Agent** - JSON-RPC communication working  
✅ **Method Name Contract Verification** - all methods detected  
✅ **CORS Configuration** - working properly  
✅ **Real network calls** - fetch polyfill functional  

#### Impact on Development

**Positive Impacts**:
- Integration tests now properly validate real agent communication
- API contract validation catches actual method mismatches
- CORS configuration is properly tested
- Real network timeouts and error scenarios can be tested

**Developer Considerations**:
- Must use correct file naming convention for test environment
- Integration tests require running agent servers locally
- Fetch polyfill needed for Node environment compatibility
- Different setup patterns for unit vs integration tests

## Current Testing Architecture

### Environment Matrix

| Test Type | Environment | Configuration File | Purpose |
|-----------|-------------|-------------------|---------|
| **Unit Tests** | jsdom | `vitest.config.ts` | Component testing, service testing with mocked APIs |
| **Integration Tests** | Node | `vitest.integration.config.ts` | Real network calls to agent servers |
| **Agent Tests** | Node | pytest | Python agent server testing |
| **E2E Tests** | Node | Python scripts | Complete workflow validation |

### File Organization

```
src/
├── components/
│   ├── TerrainViewer.test.ts          # Unit test (jsdom)
│   └── TerrainViewer.integration.test.ts # Integration test (Node)
├── services/
│   ├── AgentClient.test.ts            # Unit test (jsdom, mocked fetch)
│   └── AgentClient.integration.test.ts # Integration test (Node, real fetch)
└── test/
    ├── setup.ts                       # Unit test setup (jsdom)
    └── testSetup.ts                   # Test utilities
```

### Command Reference

```bash
# Unit tests (jsdom environment, mocked APIs)
npm test
npm run test:watch
npm run test:coverage

# Integration tests (Node environment, real network calls)
npm run test:integration

# All frontend tests
npm run test:all

# Agent tests (Python)
uv run pytest agents/tests/ -v

# Full integration suite (Python + agents)
uv run python scripts/test_integration.py
```

## Best Practices

### When to Use Each Environment

**Use jsdom (Unit Tests)**:
- Testing React components in isolation
- Testing services with mocked dependencies
- Testing browser API interactions (localStorage, WebGL, etc.)
- Fast feedback during development
- No external dependencies required

**Use Node (Integration Tests)**:
- Testing real communication with agent servers
- Validating API contracts between frontend and backend
- Testing CORS configuration
- Testing network error scenarios and timeouts
- Requires running agent servers locally

### Development Workflow

1. **Write Unit Tests First**: Use jsdom environment for fast feedback
2. **Add Integration Tests**: Use Node environment for cross-system validation
3. **Local Development**: Run unit tests frequently, integration tests before commits
4. **CI/CD Pipeline**: Run both unit and integration tests automatically

### Troubleshooting

**Common Issues**:
- **Wrong Environment**: Using jsdom for integration tests prevents real network calls
- **Missing Fetch**: Node environment needs fetch polyfill
- **Agent Availability**: Integration tests require running agent servers
- **File Naming**: Incorrect naming convention affects which config is used

**Debug Commands**:
```bash
# Check which environment is being used
npm test -- --reporter=verbose src/services/AgentClient.test.ts

# Check integration test environment
npm run test:integration -- --reporter=verbose

# Verify agent servers are running
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
```

## Future Considerations

### Potential Improvements

1. **Automatic Agent Management**: Start/stop agents automatically for integration tests
2. **Environment Detection**: Automatically detect and warn about environment mismatches
3. **Hybrid Testing**: Support both mocked and real network calls in same test suite
4. **Performance Optimization**: Cache agent responses for faster integration test execution

### Migration Guidelines

When adding new tests:

1. **Determine Test Type**: Unit (isolated) vs Integration (cross-system)
2. **Choose Environment**: jsdom for units, Node for integration
3. **Use Correct Naming**: `*.test.ts` vs `*.integration.test.ts`
4. **Add Appropriate Setup**: Mocks for units, fetch polyfill for integration
5. **Document Dependencies**: Note if integration tests require running services

## Related Documentation

- [Comprehensive Testing Guide](./COMPREHENSIVE_TESTING_GUIDE.md)
- [Comprehensive Testing Troubleshooting](./COMPREHENSIVE_TESTING_TROUBLESHOOTING.md)
- [Frontend Test Environment Guide](./FRONTEND_TEST_ENVIRONMENT.md)
- [Frontend Test Troubleshooting](./FRONTEND_TEST_TROUBLESHOOTING.md)

This architectural change represents a significant improvement in testing reliability and ensures that integration tests properly validate real system behavior rather than mocked interactions.