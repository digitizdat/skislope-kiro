# Project Structure

## Root Directory Organization
```
/
├── src/                    # Frontend source code (React + TypeScript)
├── agents/                 # Backend agent servers (Python)
├── public/                 # Static assets
├── dist/                   # Production build output
├── tests/                  # Frontend test files
├── docs/                   # Documentation
├── .kiro/                  # Kiro configuration and specs
├── logs/                   # Log files directory
│   ├── agents.log         # Agent server logs
│   ├── performance.log    # Performance metrics
│   └── frontend.log       # Frontend application logs
├── package.json            # Frontend dependencies and scripts
├── pyproject.toml          # Python project configuration (uv)
├── ruff.toml              # Ruff linting and formatting config
├── logging.yaml           # Logging configuration
└── .semgrepignore         # Semgrep ignore patterns
```

## Frontend Structure (React + TypeScript)
```
src/
├── components/             # React UI components
│   ├── StartPage/         # Ski area selection interface
│   ├── SlopeSelector/     # Grid size and detail selection
│   ├── EnvironmentView/   # Main 3D viewer component
│   └── SettingsPanel/     # User preferences
├── managers/              # Core system managers
│   ├── RenderManager/     # 3D rendering coordination
│   ├── CameraManager/     # Camera controls and states
│   ├── InputManager/      # Multi-input handling
│   └── LODManager/        # Level of detail optimization
├── services/              # Business logic services
│   ├── TerrainService/    # Terrain data processing
│   ├── AudioService/      # 3D spatial audio
│   ├── AgentClient/       # Agent server communication
│   └── DataService/       # Data loading and caching
├── stores/                # Zustand state management
│   ├── EnvironmentStore/  # Environment state
│   ├── TerrainStore/      # Terrain data state
│   ├── CameraStore/       # Camera state
│   └── WeatherStore/      # Weather data state
├── models/                # TypeScript interfaces and types
│   ├── SkiArea.ts         # Ski area definitions
│   ├── TerrainData.ts     # Terrain data structures
│   ├── CameraState.ts     # Camera state types
│   └── AgentTypes.ts      # Agent communication types
├── utils/                 # Utility functions
│   ├── DataParser/        # Data parsing utilities
│   ├── MathUtils/         # Vector and coordinate math
│   ├── CacheManager/      # IndexedDB caching
│   ├── GridGenerator/     # Terrain grid generation
│   ├── Logger/            # Structured frontend logging
│   ├── PerformanceMonitor/ # FPS and memory tracking
│   └── ProgressTracker/   # Progress indicators for long operations
└── assets/                # Images, textures, audio files
    ├── textures/          # Surface textures
    ├── audio/             # Environmental sounds
    └── images/            # UI images and previews
```

## Backend Structure (Python Agent Servers)
```
agents/
├── hill_metrics/          # Hill metrics agent server
│   ├── __init__.py
│   ├── server.py          # JSON-RPC server implementation
│   ├── terrain_processor.py # Topographical data processing
│   └── models.py          # Data models and types
├── weather/               # Weather agent server
│   ├── __init__.py
│   ├── server.py          # JSON-RPC server implementation
│   ├── weather_service.py # Weather data processing
│   └── models.py          # Weather data models
├── equipment/             # Equipment agent server
│   ├── __init__.py
│   ├── server.py          # JSON-RPC server implementation
│   ├── equipment_service.py # Equipment data processing
│   └── models.py          # Equipment data models
├── shared/                # Shared utilities across agents
│   ├── __init__.py
│   ├── jsonrpc.py         # JSON-RPC protocol implementation
│   ├── mcp.py             # MCP protocol implementation
│   ├── logging_config.py  # Structured logging configuration
│   ├── monitoring.py      # Performance and health monitoring
│   ├── metrics.py         # Metrics collection and reporting
│   └── utils.py           # Common utilities
├── monitoring/            # Observability infrastructure
│   ├── __init__.py
│   ├── dashboard.py       # Monitoring dashboard server
│   ├── health_checker.py  # Agent health monitoring
│   └── log_aggregator.py  # Log collection and analysis
└── tests/                 # Python agent tests
    ├── test_hill_metrics.py
    ├── test_weather.py
    └── test_equipment.py
```

## Key Architectural Principles
- **Separation of Concerns**: Clear boundaries between rendering, data, and UI layers
- **Agent Independence**: Loose coupling with external agent servers
- **Performance First**: LOD and caching systems integrated throughout
- **Type Safety**: Comprehensive TypeScript interfaces for all data structures
- **Modular Design**: Each manager/service handles a specific domain

## Predefined Ski Areas
Five world-renowned ski areas are hardcoded in the system:
- Chamonix (France)
- Whistler (Canada) 
- Saint Anton am Arlberg (Austria)
- Zermatt (Switzerland)
- Copper Mountain (United States)

## Configuration Files

### Frontend Configuration
- `package.json` - Frontend dependencies, scripts, and metadata
- `vite.config.ts` - Vite build configuration
- `tsconfig.json` - TypeScript configuration

### Backend Configuration  
- `pyproject.toml` - Python project configuration with uv dependencies
- `ruff.toml` - Ruff linting, formatting, and import sorting rules
- `.semgrepignore` - Files/patterns to exclude from static analysis
- `logging.yaml` - Structured logging configuration for agents

### Project Configuration
- `.kiro/specs/` - Project specifications and requirements
- `.kiro/steering/` - AI assistant guidance documents
- `.vscode/settings.json` - IDE configuration with MCP enabled

## Data Flow Pattern
1. UI components trigger actions in stores
2. Stores coordinate with services for data operations
3. Services communicate with managers for rendering/processing
4. Managers handle low-level operations (WebGL, audio, input)
5. Agent clients provide external data via JSON-RPC/MCP protocols

## Observability Patterns

### Frontend Observability
- **Progress Indicators**: Visual feedback for operations >2 seconds (terrain loading, data processing)
- **Performance Monitoring**: Real-time FPS counter, memory usage display, frame time tracking
- **Error Boundaries**: React error boundaries with user-friendly error messages and recovery options
- **Structured Logging**: Contextual logs with user actions, performance metrics, and error details
- **User Experience Metrics**: Load times, interaction responsiveness, cache hit rates

### Backend Observability  
- **Request Tracing**: Correlation IDs for tracking requests across agent services
- **Health Monitoring**: Continuous health checks with detailed status reporting
- **Performance Metrics**: Request/response times, data processing duration, memory usage
- **Structured Logging**: JSON-formatted logs with timestamps, levels, and contextual data
- **Data Transfer Monitoring**: Progress tracking for large topographical data operations

### Cross-System Observability
- **End-to-End Tracing**: Request flow from frontend through agents with timing data
- **Centralized Logging**: Aggregated logs from frontend and all agent services
- **Alert Thresholds**: Automated alerts for performance degradation or service failures
- **Operational Dashboard**: Real-time system status, performance metrics, and health indicators