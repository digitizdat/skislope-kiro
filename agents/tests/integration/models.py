"""
Test result data models and interfaces.

Defines the data structures for test results, diagnostics, and reporting
used throughout the integration testing infrastructure.
"""

import traceback
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from enum import Enum
from typing import Any


class TestStatus(Enum):
    """Test execution status."""

    NOT_STARTED = "not_started"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class TestCategory(Enum):
    """Test category types."""

    API_CONTRACTS = "api_contracts"
    COMMUNICATION = "communication"
    ENVIRONMENT = "environment"
    WORKFLOWS = "workflows"
    PERFORMANCE = "performance"
    SECURITY = "security"


class Severity(Enum):
    """Issue severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class TestError:
    """Represents a test error with context and diagnostics."""

    category: str
    severity: Severity
    message: str
    context: dict[str, Any] = field(default_factory=dict)
    suggested_fix: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)
    stack_trace: str | None = None
    error_type: str | None = None
    recovery_strategy: str | None = None

    @classmethod
    def from_exception(
        cls, exc: Exception, category: str, severity: Severity = Severity.HIGH
    ) -> "TestError":
        """Create TestError from an exception."""
        return cls(
            category=category,
            severity=severity,
            message=str(exc),
            stack_trace=traceback.format_exc(),
            context={"exception_type": type(exc).__name__},
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "category": self.category,
            "severity": self.severity.value,
            "message": self.message,
            "context": self.context,
            "suggested_fix": self.suggested_fix,
            "timestamp": self.timestamp.isoformat(),
            "stack_trace": self.stack_trace,
            "error_type": self.error_type,
            "recovery_strategy": self.recovery_strategy,
        }


@dataclass
class AgentHealthStatus:
    """Health status for an individual agent."""

    name: str
    status: str  # 'healthy', 'degraded', 'failed'
    response_time: float | None = None
    last_error: str | None = None
    available_methods: list[str] = field(default_factory=list)
    missing_methods: list[str] = field(default_factory=list)
    endpoint: str | None = None
    version: str | None = None
    uptime: float | None = None
    memory_usage: float | None = None
    last_check: float | None = None

    @property
    def is_healthy(self) -> bool:
        """Check if agent is healthy."""
        return self.status == "healthy"

    @property
    def is_available(self) -> bool:
        """Check if agent is available (healthy or degraded)."""
        return self.status in ["healthy", "degraded"]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "status": self.status,
            "response_time": self.response_time,
            "last_error": self.last_error,
            "available_methods": self.available_methods,
            "missing_methods": self.missing_methods,
            "endpoint": self.endpoint,
            "version": self.version,
            "uptime": self.uptime,
            "memory_usage": self.memory_usage,
            "last_check": self.last_check,
            "is_healthy": self.is_healthy,
            "is_available": self.is_available,
        }


@dataclass
class PerformanceMetrics:
    """Performance metrics for test execution."""

    total_duration: float
    setup_duration: float
    execution_duration: float
    teardown_duration: float
    memory_peak: float | None = None
    memory_average: float | None = None
    cpu_peak: float | None = None
    cpu_average: float | None = None
    network_requests: int = 0
    network_bytes_sent: int = 0
    network_bytes_received: int = 0

    @property
    def requests_per_second(self) -> float:
        """Calculate requests per second."""
        if self.execution_duration > 0:
            return self.network_requests / self.execution_duration
        return 0.0


@dataclass
class EnvironmentIssue:
    """Represents an environment configuration issue."""

    component: str
    issue_type: str
    description: str
    severity: Severity
    suggested_fix: str | None = None
    detected_value: str | None = None
    expected_value: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "component": self.component,
            "issue_type": self.issue_type,
            "description": self.description,
            "severity": self.severity.value,
            "suggested_fix": self.suggested_fix,
            "detected_value": self.detected_value,
            "expected_value": self.expected_value,
        }


@dataclass
class TestResult:
    """Individual test result."""

    name: str
    category: TestCategory
    status: TestStatus
    duration: float
    message: str | None = None
    error: TestError | None = None
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime | None = None
    context: dict[str, Any] = field(default_factory=dict)

    def mark_passed(self, message: str | None = None) -> None:
        """Mark test as passed."""
        self.status = TestStatus.PASSED
        self.end_time = datetime.now()
        self.message = message
        if self.start_time:
            self.duration = (self.end_time - self.start_time).total_seconds()

    def mark_failed(
        self, error: TestError | Exception | str, message: str | None = None
    ) -> None:
        """Mark test as failed."""
        self.status = TestStatus.FAILED
        self.end_time = datetime.now()
        self.message = message

        if isinstance(error, TestError):
            self.error = error
        elif isinstance(error, Exception):
            self.error = TestError.from_exception(error, self.category.value)
        else:
            self.error = TestError(
                category=self.category.value, severity=Severity.HIGH, message=str(error)
            )

        if self.start_time:
            self.duration = (self.end_time - self.start_time).total_seconds()

    def mark_skipped(self, reason: str) -> None:
        """Mark test as skipped."""
        self.status = TestStatus.SKIPPED
        self.end_time = datetime.now()
        self.message = reason
        if self.start_time:
            self.duration = (self.end_time - self.start_time).total_seconds()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        error_dict = None
        if self.error:
            error_dict = {
                "category": self.error.category,
                "severity": self.error.severity.value,
                "message": self.error.message,
                "context": self.error.context,
                "suggested_fix": self.error.suggested_fix,
                "timestamp": self.error.timestamp.isoformat(),
                "stack_trace": self.error.stack_trace,
            }

        return {
            "name": self.name,
            "category": self.category.value,
            "status": self.status.value,
            "duration": self.duration,
            "message": self.message,
            "error": error_dict,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "context": self.context,
        }


@dataclass
class CategoryResults:
    """Results for a test category."""

    category: TestCategory
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    duration: float = 0.0
    tests: list[TestResult] = field(default_factory=list)

    def add_result(self, result: TestResult) -> None:
        """Add a test result to this category."""
        self.tests.append(result)
        self.total_tests += 1
        self.duration += result.duration

        if result.status == TestStatus.PASSED:
            self.passed += 1
        elif result.status == TestStatus.FAILED:
            self.failed += 1
        elif result.status == TestStatus.SKIPPED:
            self.skipped += 1
        elif result.status == TestStatus.ERROR:
            self.errors += 1

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_tests == 0:
            return 0.0
        return (self.passed / self.total_tests) * 100

    @property
    def has_failures(self) -> bool:
        """Check if category has any failures."""
        return self.failed > 0 or self.errors > 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "category": self.category.value,
            "total_tests": self.total_tests,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "errors": self.errors,
            "duration": self.duration,
            "success_rate": self.success_rate,
            "tests": [test.to_dict() for test in self.tests],
        }


@dataclass
class TestSummary:
    """Overall test execution summary."""

    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    duration: float = 0.0
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime | None = None

    @property
    def success_rate(self) -> float:
        """Calculate overall success rate."""
        if self.total_tests == 0:
            return 0.0
        return (self.passed / self.total_tests) * 100

    @property
    def is_successful(self) -> bool:
        """Check if test run was successful."""
        return self.failed == 0 and self.errors == 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "total_tests": self.total_tests,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "errors": self.errors,
            "duration": self.duration,
            "success_rate": self.success_rate,
            "is_successful": self.is_successful,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
        }


@dataclass
class TestResults:
    """Complete test results with diagnostics."""

    summary: TestSummary = field(default_factory=TestSummary)
    categories: dict[TestCategory, CategoryResults] = field(default_factory=dict)
    agent_health: list[AgentHealthStatus] = field(default_factory=list)
    environment_issues: list[EnvironmentIssue] = field(default_factory=list)
    performance_metrics: PerformanceMetrics | None = None
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def add_result(self, result: TestResult) -> None:
        """Add a test result."""
        # Update summary
        self.summary.total_tests += 1
        self.summary.duration += result.duration

        if result.status == TestStatus.PASSED:
            self.summary.passed += 1
        elif result.status == TestStatus.FAILED:
            self.summary.failed += 1
        elif result.status == TestStatus.SKIPPED:
            self.summary.skipped += 1
        elif result.status == TestStatus.ERROR:
            self.summary.errors += 1

        # Add to category
        if result.category not in self.categories:
            self.categories[result.category] = CategoryResults(category=result.category)

        self.categories[result.category].add_result(result)

    def finalize(self) -> None:
        """Finalize test results."""
        self.summary.end_time = datetime.now()
        if self.summary.start_time:
            self.summary.duration = (
                self.summary.end_time - self.summary.start_time
            ).total_seconds()

    def get_failed_tests(self) -> list[TestResult]:
        """Get all failed tests."""
        failed_tests = []
        for category_results in self.categories.values():
            failed_tests.extend(
                [
                    test
                    for test in category_results.tests
                    if test.status in [TestStatus.FAILED, TestStatus.ERROR]
                ]
            )
        return failed_tests

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        agent_health_list = []
        for agent in self.agent_health:
            if hasattr(agent, "to_dict"):
                agent_health_list.append(agent.to_dict())
            else:
                # Convert dataclass to dict manually
                agent_dict = {
                    "name": agent.name,
                    "status": agent.status,
                    "response_time": agent.response_time,
                    "last_error": agent.last_error,
                    "available_methods": agent.available_methods,
                    "missing_methods": agent.missing_methods,
                    "endpoint": agent.endpoint,
                    "version": agent.version,
                    "uptime": agent.uptime,
                    "memory_usage": agent.memory_usage,
                }
                agent_health_list.append(agent_dict)

        return {
            "summary": self.summary.to_dict(),
            "categories": {
                category.value: results.to_dict()
                for category, results in self.categories.items()
            },
            "agent_health": agent_health_list,
            "environment_issues": [
                issue.to_dict() for issue in self.environment_issues
            ],
            "performance_metrics": self.performance_metrics.__dict__
            if self.performance_metrics
            else None,
            "diagnostics": self.diagnostics,
        }


# Type aliases for convenience
TestResultDict = dict[str, Any]
DiagnosticData = dict[str, Any]
