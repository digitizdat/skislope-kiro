#!/bin/bash
# Setup script for CI/CD integration

set -e

echo "Setting up CI/CD integration for Alpine Ski Simulator..."

# Create necessary directories
echo "Creating directories..."
mkdir -p .github/workflows
mkdir -p test-results
mkdir -p deployment-test-results
mkdir -p test-artifacts
mkdir -p logs
mkdir -p temp/integration_tests

# Install Lefthook if not already installed
if ! command -v lefthook &> /dev/null; then
    echo "Installing Lefthook..."
    npm install lefthook --save-dev
fi

# Install git hooks
echo "Installing git hooks..."
npx lefthook install

# Make scripts executable
echo "Making scripts executable..."
chmod +x scripts/deployment_smoke_tests.py
chmod +x scripts/collect_test_artifacts.py
chmod +x scripts/setup_ci_cd.sh

# Verify Python environment
echo "Verifying Python environment..."
if command -v uv &> /dev/null; then
    echo "✓ uv is installed"
    uv sync
    echo "✓ Python dependencies synced"
else
    echo "✗ uv is not installed. Please install uv first:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Verify Node environment
echo "Verifying Node environment..."
if command -v npm &> /dev/null; then
    echo "✓ npm is installed"
    npm install
    echo "✓ Node dependencies installed"
else
    echo "✗ npm is not installed. Please install Node.js first."
    exit 1
fi

# Test critical imports
echo "Testing critical imports..."
uv run python -c "import agents.hill_metrics.server" && echo "✓ Hill metrics agent import successful"
uv run python -c "import agents.weather.server" && echo "✓ Weather agent import successful"
uv run python -c "import agents.equipment.server" && echo "✓ Equipment agent import successful"

# Test frontend build
echo "Testing frontend build..."
npm run build && echo "✓ Frontend build successful"

# Run smoke tests
echo "Running deployment smoke tests..."
uv run python scripts/deployment_smoke_tests.py --output-dir test-setup-results

echo ""
echo "✅ CI/CD integration setup complete!"
echo ""
echo "Next steps:"
echo "1. Commit the new CI/CD files to your repository"
echo "2. Push to trigger the GitHub Actions workflow"
echo "3. Review the test results in the Actions tab"
echo ""
echo "Available commands:"
echo "  npm run hooks:install    - Install git hooks"
echo "  npm run ci:integration   - Run integration tests locally"
echo "  npm run ci:smoke         - Run deployment smoke tests"
echo "  npm run ci:artifacts     - Collect test artifacts"
echo ""
echo "Git hooks are now active and will run on commit/push!"