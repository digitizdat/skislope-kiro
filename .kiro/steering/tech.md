# Technology Stack

## Core Technologies
- **Frontend Framework**: React for UI components
- **3D Rendering**: Three.js with WebGL for high-performance 3D graphics
- **Build System**: Vite for modern development tooling
- **Frontend Language**: TypeScript for type safety and better developer experience
- **Backend Language**: Python for agent servers and data processing
- **Python Tooling**: uv for dependency management, ruff for formatting/linting, semgrep for static analysis
- **State Management**: Zustand for React application state

## Architecture Patterns
- **Agent-Based Architecture**: Independent agent servers for hill metrics, weather, and equipment data
- **Communication Protocols**: 
  - Primary: JSON-RPC over HTTP
  - Secondary: MCP (Model Context Protocol) for tool integration
- **Data Storage**: IndexedDB for terrain caching, LocalStorage for settings
- **Performance**: Level of Detail (LOD) system, frustum culling, texture streaming

## Key Libraries & APIs
- **Audio**: Web Audio API for 3D spatial environmental sounds
- **Input**: Multi-input support (mouse, keyboard, gamepad, touch)
- **Caching**: Service Workers for offline functionality
- **Performance**: WebAssembly for intensive terrain processing

## Observability & Monitoring
- **Frontend Logging**: Structured logging with log levels (DEBUG, INFO, WARN, ERROR)
- **Backend Logging**: Python structured logging with correlation IDs
- **Performance Monitoring**: Frame rate tracking, memory usage, load times
- **Agent Monitoring**: Request/response times, health checks, data transfer metrics
- **User Experience**: Progress indicators for long operations (terrain loading, data processing)
- **Error Tracking**: Comprehensive error capture with context and stack traces

## Development Commands

### Frontend (React + TypeScript)
```bash
# Development server
npm run dev

# Production build
npm run build

# Type checking
npm run type-check

# Linting
npm run lint

# Testing
npm run test
npm run test:integration
npm run test:performance

# Cache management
npm run cache:clear
```

### Backend (Python Agent Servers)
```bash
# Environment and dependency management with uv
uv venv                     # Create virtual environment
uv pip install -r pyproject.toml  # Install dependencies
uv add <package>            # Add new dependency
uv remove <package>         # Remove dependency

# Code quality with ruff
ruff check                  # Lint code
ruff check --fix            # Auto-fix linting issues
ruff format                 # Format code
ruff format --check         # Check formatting without changes

# Static analysis with semgrep
semgrep --config=auto       # Run security and bug analysis
semgrep --config=p/python   # Python-specific rules

# Start agent servers
uv run python -m agents.hill_metrics
uv run python -m agents.weather
uv run python -m agents.equipment

# Agent server health checks
uv run python -m agents.health_check

# Run tests
uv run pytest agents/tests/
uv run pytest --cov=agents  # With coverage

# Monitoring and observability
uv run python -m agents.monitor  # Start monitoring dashboard
tail -f logs/agents.log          # View agent logs
tail -f logs/performance.log     # View performance metrics
```

## Performance Requirements
- Maintain minimum 30 FPS on supported hardware
- Support grid sizes from 32x32 to 128x128 cells
- Graceful degradation for lower-end devices
- Memory-efficient terrain streaming for large areas

## Observability Requirements
- **Progress Tracking**: Visual progress bars for terrain loading (>2 seconds)
- **Performance Metrics**: Real-time FPS, memory usage, and load time monitoring
- **Agent Health**: Continuous health checks with status indicators
- **Error Context**: Detailed error messages with actionable recovery steps
- **Data Transfer**: Progress indicators for large topographical data downloads
- **User Feedback**: Clear status messages during long operations
- **Debug Information**: Comprehensive logging for troubleshooting without overwhelming users

## Agent Server Integration
- Hill Metrics Agent: Topographical data processing
- Weather Agent: Real-time and historical weather conditions  
- Equipment Agent: Ski infrastructure and facility information
- Health monitoring with exponential backoff retry logic

## Development Standards

### Commit Message Guidelines
Follow Conventional Commits specification (https://www.conventionalcommits.org/en/v1.0.0/):

**Format**: `<type>[optional scope]: <description>`

**Types**:
- `feat`: New feature for the user
- `fix`: Bug fix for the user
- `docs`: Documentation changes
- `style`: Code style changes (formatting, missing semicolons, etc.)
- `refactor`: Code refactoring without changing functionality
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Maintenance tasks, dependency updates
- `ci`: CI/CD pipeline changes

**Examples**:
```bash
feat(terrain): add LOD system for terrain rendering
fix(agents): resolve hill metrics timeout issue
docs(api): update agent communication protocol
perf(rendering): optimize mesh generation for large grids
test(camera): add unit tests for camera movement
chore(deps): update Three.js to latest version
```

**Breaking Changes**: Add `!` after type or include `BREAKING CHANGE:` in footer
```bash
feat(api)!: change agent response format
feat(terrain): add new grid sizes

BREAKING CHANGE: Agent response format changed from array to object
```