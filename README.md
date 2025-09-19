# Alpine Ski Simulator

A browser-based 3D web application that provides immersive exploration of realistic ski slope environments using real topographical data from five world-renowned ski areas.

## Features

- 🎿 Explore famous ski slopes: Chamonix, Whistler, Saint Anton am Arlberg, Zermatt, and Copper Mountain
- 🌐 WebGL-based 3D terrain rendering with configurable detail levels (32x32 to 128x128 grid cells)
- 🌤️ Real-time weather and environmental effects
- 📷 Multiple camera modes (freefly, orbital, cinematic, aerial)
- 🔧 Independent agent server architecture for hill metrics, weather, and equipment data
- 💾 Offline caching and performance optimization
- 🏁 Foundation for future FIS World Cup alpine skiing event simulation

## Tech Stack

### Frontend
- **React** + **TypeScript** for UI components
- **Three.js** for 3D rendering with WebGL
- **Vite** for build tooling
- **Zustand** for state management

### Backend
- **Python** agent servers for data processing
- **uv** for dependency management
- **ruff** for code formatting and linting
- **semgrep** for static analysis

## Getting Started

### Prerequisites
- Node.js 18+ 
- Python 3.11+
- uv (for Python dependency management)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd alpine-ski-simulator
```

2. Install frontend dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

4. Open your browser to `http://localhost:3000`

### Development Commands

#### Frontend
```bash
npm run dev          # Start development server
npm run build        # Production build
npm run lint         # Run ESLint
npm run type-check   # TypeScript type checking
npm run cache:clear  # Clear Vite cache
```

#### Backend (Python Agents)
```bash
uv venv                              # Create virtual environment
uv pip install -r pyproject.toml    # Install dependencies
uv run python -m agents.hill_metrics # Start hill metrics agent
uv run python -m agents.weather      # Start weather agent
uv run python -m agents.equipment    # Start equipment agent
```

## Project Structure

```
/
├── src/                    # Frontend source code (React + TypeScript)
├── agents/                 # Backend agent servers (Python)
├── public/                 # Static assets
├── dist/                   # Production build output
├── .kiro/                  # Kiro configuration and specs
├── package.json            # Frontend dependencies
└── pyproject.toml          # Python dependencies
```

## Development Standards

### Commit Messages
This project follows [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/):

```bash
feat(terrain): add LOD system for terrain rendering
fix(agents): resolve hill metrics timeout issue
docs(api): update agent communication protocol
```

## Architecture

The system uses an agent-based architecture with independent servers providing:
- **Hill Metrics Agent**: Topographical data processing
- **Weather Agent**: Real-time and historical weather conditions
- **Equipment Agent**: Ski infrastructure and facility information

Communication protocols:
- Primary: JSON-RPC over HTTP
- Secondary: MCP (Model Context Protocol) for tool integration

## Performance Requirements

- Maintain minimum 30 FPS on supported hardware
- Support grid sizes from 32x32 to 128x128 cells
- Graceful degradation for lower-end devices
- Memory-efficient terrain streaming for large areas

## Contributing

1. Follow the established project structure
2. Use TypeScript for all frontend code
3. Follow Conventional Commits for commit messages
4. Ensure all tests pass before submitting PRs
5. Add appropriate logging and error handling

## License

[License information to be added]