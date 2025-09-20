#!/bin/bash

# Task Completion Readiness Checker
# Verifies that all precommit checks pass before marking a task as complete

set -e

echo "🔍 Checking if task is ready for completion..."
echo "================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track overall status
OVERALL_STATUS=0

echo ""
echo "1️⃣  Checking precommit hooks..."
echo "--------------------------------"

if uv run npx lefthook run pre-commit; then
    echo -e "${GREEN}✅ All precommit checks passed!${NC}"
else
    echo -e "${RED}❌ Precommit checks failed!${NC}"
    OVERALL_STATUS=1
fi

echo ""
echo "2️⃣  Checking frontend build..."
echo "------------------------------"

if npm run build > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Frontend build successful!${NC}"
else
    echo -e "${RED}❌ Frontend build failed!${NC}"
    echo "Run 'npm run build' to see detailed errors"
    OVERALL_STATUS=1
fi

echo ""
echo "3️⃣  Checking backend tests..."
echo "-----------------------------"

if uv run pytest agents/tests/ -v --tb=short > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Backend tests passed!${NC}"
else
    echo -e "${RED}❌ Backend tests failed!${NC}"
    echo "Run 'uv run pytest agents/tests/ -v' to see detailed errors"
    OVERALL_STATUS=1
fi

echo ""
echo "4️⃣  Checking frontend tests..."
echo "------------------------------"

if npm test > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Frontend tests passed!${NC}"
else
    echo -e "${RED}❌ Frontend tests failed!${NC}"
    echo "Run 'npm test' to see detailed errors"
    OVERALL_STATUS=1
fi

echo ""
echo "================================================"

if [ $OVERALL_STATUS -eq 0 ]; then
    echo -e "${GREEN}🎉 TASK READY FOR COMPLETION!${NC}"
    echo -e "${GREEN}All checks passed. You can mark this task as 'completed'.${NC}"
else
    echo -e "${RED}🚫 TASK NOT READY FOR COMPLETION!${NC}"
    echo -e "${RED}Fix the failing checks above before marking task as 'completed'.${NC}"
    echo -e "${YELLOW}Task should remain 'in_progress' until all checks pass.${NC}"
fi

echo ""
echo "📋 Remember: A task is only complete when ALL precommit checks pass!"
echo "See .kiro/steering/task-completion-rules.md for details."

exit $OVERALL_STATUS