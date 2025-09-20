---
inclusion: always
---

# Task Completion Rules

## Core Principle: Clean Precommit = Task Complete

**A task is NOT considered complete until ALL precommit checks pass cleanly.**

### Rationale

If precommit checks are failing, the changes cannot be committed to the repository. Since the purpose of completing a task is to deliver working, committable code, a task with failing precommit checks is by definition incomplete.

### Task Completion Checklist

Before marking any task as "completed", the following MUST be verified:

#### 1. Stage Files for Commit ✅
```bash
git add .
```

**CRITICAL**: Precommit checks are only triggered when files are staged for commit. If no files are staged, the checks will be skipped with messages like "(skip) no matching staged files".

#### 2. Precommit Checks Pass ✅
```bash
uv run npx lefthook run pre-commit
```

**All checks must show ✔️ status:**
- ✔️ dependency-check
- ✔️ api-contract-check  
- ✔️ python-imports
- ✔️ quick-test (including frontend build)
- ✔️ Any other enabled precommit checks

#### 2. Build Success ✅
```bash
npm run build
```
Must complete without errors.

#### 3. Tests Pass ✅
```bash
# Backend tests
uv run pytest agents/tests/ -v

# Frontend tests  
npm test

# Integration tests (if applicable)
uv run python scripts/test_integration.py
```

#### 4. No Linting/Formatting Issues ✅
```bash
# Python formatting and linting
uv run ruff format --check
uv run ruff check

# Frontend linting (when enabled)
npm run lint
npm run type-check
```

### Implementation Workflow

When working on any task:

1. **During Development**: Run checks frequently to catch issues early
2. **Before Marking Complete**: 
   - Stage all changes: `git add .`
   - Run full precommit check suite: `uv run npx lefthook run pre-commit`
3. **If Checks Fail**: 
   - Fix all issues
   - Re-stage files: `git add .`
   - Re-run precommit checks
   - Only mark complete when ALL checks pass
4. **Task Status Updates**:
   - `in_progress` → Continue working until precommit checks pass
   - `completed` → Only when precommit checks are clean

### Common Precommit Issues and Solutions

#### Staging Issues
- **Problem**: Checks show "(skip) no matching staged files"
- **Solution**: Run `git add .` to stage files before running precommit checks

#### Dependency Issues
- **Problem**: Virtual environment not activated
- **Solution**: Always use `uv run` prefix for Python commands

#### Build Failures
- **Problem**: TypeScript errors in test files
- **Solution**: Ensure test files are excluded from production builds in `tsconfig.json`

#### Import Errors
- **Problem**: Missing dependencies or import failures
- **Solution**: Verify all agent imports work: `uv run python -c "import agents.module"`

#### Linting Issues
- **Problem**: Code style violations
- **Solution**: Run `uv run ruff format` and `uv run ruff check --fix`

### Emergency Procedures

If precommit checks are blocking critical work:

1. **Verify Files Are Staged**: Ensure `git add .` was run - checks won't run on unstaged files
2. **Identify Root Cause**: Run individual check commands to isolate the issue
3. **Fix Systematically**: Address one category of errors at a time
4. **Document Workarounds**: If temporary disabling is needed, document why and create follow-up tasks
5. **Never Skip**: Avoid committing with failing checks - this breaks the build for everyone

### Enforcement

- **AI Assistants**: Must verify precommit status before marking tasks complete
- **Developers**: Should run precommit checks before requesting task reviews
- **Code Reviews**: Reviewers should verify precommit status before approval
- **CI/CD**: Automated systems should block merges with failing precommit checks

### Benefits

- **Consistent Quality**: Every completed task meets quality standards
- **Reduced Debugging**: Catch issues before they reach main branch
- **Team Efficiency**: No broken builds blocking other developers
- **Professional Standards**: Maintain high code quality throughout development

### Task Status Definitions

- **`not_started`**: Task has not been begun
- **`in_progress`**: Task is being worked on, precommit checks may be failing
- **`completed`**: Task is finished AND all precommit checks pass cleanly

**Remember: If precommit checks fail, the task is still `in_progress`, not `completed`.**

---

*This rule applies to ALL tasks across ALL specs and projects. No exceptions.*