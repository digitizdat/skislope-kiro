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
uv sync                     # Install dependencies from pyproject.toml
uv add <package>            # Add new dependency (ALWAYS use this, never pip install)
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

# Run tests (CRITICAL: Always run before commits)
uv run pytest agents/tests/ -v        # Backend unit tests
uv run pytest --cov=agents           # With coverage
npm test                              # Frontend unit tests
npm run test:integration              # Frontend integration tests
uv run python scripts/test_integration.py  # Full integration test suite (CRITICAL)

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

> **📋 IMPORTANT**: See `.kiro/steering/development-workflow.md` for detailed development practices and lessons learned from dependency management issues.

### Dependency Management Rules
**CRITICAL: Always use the correct package manager for each part of the project**

#### Python Dependencies (Backend)
- **ALWAYS use `uv add`** - Never use `pip install` in this project
- **NEVER mix package managers** - This causes environment inconsistencies
- **Always commit pyproject.toml changes** when adding dependencies

```bash
# ✅ CORRECT: Add Python dependencies
uv add fastapi uvicorn structlog
uv add --dev pytest ruff mypy

# ❌ WRONG: Never use pip in a uv project
pip install fastapi  # DON'T DO THIS

# ✅ CORRECT: Install from existing project
uv sync
```

#### Node Dependencies (Frontend)
```bash
# ✅ CORRECT: Add Node dependencies
npm install three @types/three
npm install --save-dev vitest

# ✅ CORRECT: Install from existing project
npm install
```

### Testing Requirements
**MANDATORY: All tests must pass before any commit or deployment**

#### Test Coverage Requirements
- **Backend**: All agent modules must have import tests at minimum
- **Frontend**: All services and utilities must have unit tests
- **Integration**: Critical paths must have end-to-end tests

#### Pre-Commit Testing Checklist
```bash
# 1. Backend tests (MUST pass)
uv run pytest agents/tests/ -v

# 2. Frontend tests (MUST pass)  
npm test

# 3. Build verification (MUST succeed)
npm run build

# 4. Import verification (MUST succeed)
uv run python -c "import agents.hill_metrics.server"
uv run python -c "import agents.weather.server"
uv run python -c "import agents.equipment.server"
```

#### Test Failure Investigation
When tests fail:
1. **Check import errors first** - Often indicates missing dependencies
2. **Verify environment setup** - Ensure `uv sync` and `npm install` completed
3. **Check for mixed package managers** - Never mix `pip` and `uv`
4. **Run tests in isolation** - Test individual modules to isolate issues

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