# Development Workflow Guidelines

> **🚨 CRITICAL RULE**: See `.kiro/steering/task-completion-rules.md` - **Tasks are NOT complete until ALL precommit checks pass cleanly.** If precommit checks fail, the task remains `in_progress`.

## Critical Lessons Learned

### Dependency Management Disasters to Avoid

#### The Problem We Encountered
- Agent servers failed to start due to missing `shapely` dependency
- Tests didn't catch the issue because they never ran (import failures during collection)
- Mixed use of `pip` and `uv` caused environment inconsistencies
- Dependencies were declared in `pyproject.toml` but not properly installed

#### Root Cause Analysis
1. **Package Manager Mixing**: Using `pip install` in a `uv` project
2. **Test Coverage Gaps**: No integration tests that actually import agent modules
3. **Silent Test Failures**: Tests failed during collection phase, not execution
4. **Environment Drift**: Development environment differed from declared dependencies

### Mandatory Development Practices

#### 1. Dependency Management Protocol

**Python Backend (uv project):**
```bash
# ✅ ALWAYS use uv commands
uv add package-name                    # Add runtime dependency
uv add --dev package-name             # Add development dependency
uv remove package-name                # Remove dependency
uv sync                               # Install from pyproject.toml

# ❌ NEVER use pip commands
pip install package-name              # DON'T DO THIS
pip uninstall package-name            # DON'T DO THIS
```

**Frontend (npm project):**
```bash
# ✅ Use npm commands
npm install package-name              # Add runtime dependency
npm install --save-dev package-name   # Add dev dependency
npm uninstall package-name            # Remove dependency
npm install                           # Install from package.json
```

#### 2. Pre-Commit Testing Protocol

**MANDATORY: Run this checklist before every commit:**

```bash
# Step 1: Verify environment setup
uv sync                               # Ensure Python deps installed
npm install                           # Ensure Node deps installed

# Step 2: Import verification (catches missing deps immediately)
uv run python -c "import agents.hill_metrics.server"
uv run python -c "import agents.weather.server" 
uv run python -c "import agents.equipment.server"

# Step 3: Run all tests
uv run pytest agents/tests/ -v       # Backend unit tests
npm test                              # Frontend unit tests
uv run python scripts/test_integration.py  # Integration tests (CRITICAL)

# Step 4: Build verification
npm run build                         # Must succeed

# Step 5: Integration smoke test (if agents available)
uv run python scripts/start_agents.py &  # Start agents
sleep 5                               # Wait for startup
curl http://localhost:8002/health     # Verify at least one agent
pkill -f "python.*agents"            # Stop agents
```

#### 3. Test Coverage Requirements

**Backend Testing:**
- **Import Tests**: Every module must have a basic import test
- **Unit Tests**: All business logic functions must be tested
- **Integration Tests**: Agent startup and health checks must be tested
- **API Contract Tests**: All JSON-RPC methods must be verified (CRITICAL)

**Frontend Testing:**
- **Unit Tests**: All services, utilities, and components
- **Integration Tests**: Cache system and agent communication
- **API Contract Tests**: Verify frontend calls match backend methods (CRITICAL)
- **Build Tests**: Ensure TypeScript compilation succeeds

#### 4. Environment Consistency Rules

**Never Mix Package Managers:**
- Python project uses `uv` exclusively
- Frontend project uses `npm` exclusively
- Document any exceptions clearly

**Lock File Management:**
- Always commit `uv.lock` and `package-lock.json`
- Never manually edit lock files
- Regenerate lock files when dependencies change

#### 5. Debugging Failed Tests

**When tests fail to collect/import:**
```bash
# 1. Check for missing dependencies
uv run python -c "import problematic_module"

# 2. Verify environment
uv sync --verbose

# 3. Check for mixed package managers
pip list | grep -E "(fastapi|uvicorn)"  # Should be empty in uv project

# 4. Reinstall from scratch if needed
rm -rf .venv
uv sync
```

**When agents fail to start:**
```bash
# 1. Check individual agent imports
uv run python -m agents.hill_metrics.server --help

# 2. Check dependencies
uv run python -c "from agents.hill_metrics.terrain_processor import DEMProcessor"

# 3. Check for missing system dependencies
# Some packages (rasterio, shapely) need system libraries
```

### Project-Specific Guidelines

#### Agent Development
- All new agents must have health check endpoints
- All agents must handle graceful shutdown
- Agent dependencies must be declared in `pyproject.toml`
- Agent startup must be tested in CI/CD

#### Frontend Development  
- All new services must integrate with caching system
- All API calls must handle offline mode gracefully
- TypeScript strict mode must be maintained
- Build must succeed without warnings

#### Integration Points
- Cache system must work with all agents
- Offline mode must degrade gracefully
- Error handling must be user-friendly
- Performance monitoring must be maintained

### Emergency Procedures

#### When Dependencies Break
1. **Don't panic** - Document the exact error
2. **Check environment** - Verify package manager usage
3. **Isolate the issue** - Test individual imports
4. **Fix systematically** - Use proper package manager commands
5. **Test thoroughly** - Run full test suite before committing

#### When Tests Fail Mysteriously
1. **Check test collection** - Run `pytest --collect-only`
2. **Verify imports** - Test module imports individually  
3. **Check environment** - Ensure dependencies are installed
4. **Clear caches** - Remove `.pytest_cache`, `node_modules/.cache`
5. **Restart fresh** - Recreate virtual environment if needed

### Success Metrics

#### Green Build Indicators
- All tests pass (backend and frontend)
- All imports succeed
- Build completes without errors
- Agents start successfully
- Health checks return 200 OK

#### Red Flags to Watch For
- Import errors during test collection
- Mixed package manager usage
- Missing dependencies in lock files
- Silent test failures
- Environment drift between developers

Remember: **Prevention is better than debugging**. Following these protocols prevents 90% of environment and dependency issues.