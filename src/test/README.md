# Frontend Test Environment

This directory contains the comprehensive test setup for the frontend application, providing reliable testing infrastructure for both local development and CI/CD environments.

## Browser API Mocks

The test environment includes comprehensive mocks for all major browser APIs:

### Storage APIs
- **localStorage**: Full implementation with getItem, setItem, removeItem, clear, key, and length
- **sessionStorage**: Identical implementation to localStorage with separate storage

### Network APIs
- **fetch**: Complete fetch API mock with configurable responses, error simulation, and proper Promise handling
- **XMLHttpRequest**: Full XHR mock with readyState management, event handling, and async simulation

### Web Audio API
- **AudioContext**: Complete audio context mock with all major audio nodes
- **Audio Nodes**: Oscillator, Gain, Analyser, Buffer, Panner, and other audio processing nodes
- **Audio Buffers**: Mock audio buffer creation and manipulation

### File and Blob APIs
- **Blob**: Full Blob implementation with size calculation, type handling, and stream methods
- **File**: Complete File API extending Blob with name, lastModified, and path properties
- **URL**: Object URL creation and revocation for blob handling

## Test Setup Infrastructure

### Core Components

1. **testSetup.ts**: Main test environment initialization and teardown
2. **setup.ts**: Vitest integration and test lifecycle management
3. **webglMocks.ts**: WebGL context mocking for Three.js compatibility
4. **simpleBrowserMocks.ts**: Comprehensive browser API mocks

### Features

- **WebGL Context Mocking**: Headless WebGL support using canvas package
- **IndexedDB Mocking**: Complete IndexedDB simulation using fake-indexeddb
- **CacheManager Integration**: Automatic cache initialization for tests
- **Environment Isolation**: Clean state between tests with proper reset mechanisms
- **Error Handling**: Comprehensive error simulation and testing support

## Usage

The test environment is automatically initialized when running tests:

```bash
npm test                    # Run all tests
npm run test:watch         # Watch mode
npm run test:integration   # Integration tests only
```

### Test Environment APIs

All browser APIs are automatically available in tests:

```typescript
// Storage APIs
localStorage.setItem('key', 'value');
sessionStorage.getItem('key');

// Network APIs
const response = await fetch('/api/data');
const xhr = new XMLHttpRequest();

// Web Audio API
const audioContext = new AudioContext();
const oscillator = audioContext.createOscillator();

// File APIs
const blob = new Blob(['data'], { type: 'text/plain' });
const file = new File(['data'], 'test.txt');
const url = URL.createObjectURL(blob);
```

## Requirements Satisfied

This implementation satisfies the following requirements from the frontend test environment specification:

- **4.1**: Comprehensive browser API mocks for localStorage, sessionStorage, and IndexedDB
- **4.2**: Complete fetch API and XMLHttpRequest mocking for network operations  
- **4.4**: Full Web Audio API mocks for audio service testing

## Architecture

The test environment uses a layered approach:

1. **Vitest Configuration**: Base test runner setup
2. **Test Setup Layer**: Environment initialization and cleanup
3. **Mock Infrastructure**: Browser API implementations
4. **Integration Layer**: Service-specific test utilities

This ensures reliable, fast, and isolated test execution across all frontend components.