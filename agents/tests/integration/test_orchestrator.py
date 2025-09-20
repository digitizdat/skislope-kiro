"""
Integration Test Orchestrator for coordinated execution.

Provides the main entry point for integration testing with parallel test execution,
result aggregation, selective test category execution, and comprehensive reporting.
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Any, Callable, Awaitable
import json

import structlog

from .config import TestConfig, get_test_config
from .models import (
    TestResult, TestResults, TestCategory, TestStatus, TestSummary,
    CategoryResults, PerformanceMetrics, TestError, Severity
)
from .logging_utils import TestLogger
from .agent_lifecycle import AgentLifecycleManager
from .api_contract_validator import APIContractValidator
from .environment_validator import EnvironmentValidator
from .communication_validator import CommunicationValidator
from .workflow_simulator import WorkflowSimulator, WorkflowType
from .report_generator import ReportGenerator
from .dashboard import TestResultsDashboard
from .performance_tracker import PerformanceTracker


logger = structlog.get_logger(__name__)


class ExecutionMode(Enum):
    """Test execution modes."""
    FULL_SUITE = "full_suite"
    SELECTIVE = "selective"
    SMOKE_TESTS = "smoke_tests"
    PERFORMANCE_ONLY = "performance_only"


@dataclass
class ExecutionPlan:
    """Plan for test execution."""
    mode: ExecutionMode
    categories: Set[TestCategory]
    parallel_execution: bool = True
    max_workers: int = 4
    timeout: float = 300.0
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionContext:
    """Context for test execution."""
    config: TestConfig
    agent_manager: AgentLifecycleManager
    start_time: datetime
    execution_id: str
    temp_dir: Path
    log_dir: Path
    artifacts_dir: Path


class IntegrationTestOrchestrator:
    """
    Main orchestrator for integration test execution.
    
    Coordinates all test components, manages parallel execution, aggregates results,
    and provides comprehensive reporting capabilities.
    """
    
    def __init__(self, config: Optional[TestConfig] = None):
        """
        Initialize the test orchestrator.
        
        Args:
            config: Optional test configuration (uses default if None)
        """
        self.config = config or get_test_config()
        self.logger = TestLogger("test_orchestrator", self.config)
        
        # Test component instances
        self.agent_manager: Optional[AgentLifecycleManager] = None
        self.api_validator: Optional[APIContractValidator] = None
        self.env_validator: Optional[EnvironmentValidator] = None
        self.comm_validator: Optional[CommunicationValidator] = None
        self.workflow_simulator: Optional[WorkflowSimulator] = None
        
        # Reporting and monitoring components
        self.report_generator: Optional[ReportGenerator] = None
        self.dashboard: Optional[TestResultsDashboard] = None
        self.performance_tracker: Optional[PerformanceTracker] = None
        
        # Execution state
        self.execution_context: Optional[ExecutionContext] = None
        self.results: Optional[TestResults] = None
        self._shutdown_requested = False
        
        # Test category handlers
        self.category_handlers: Dict[TestCategory, Callable[[ExecutionContext], Awaitable[List[TestResult]]]] = {
            TestCategory.ENVIRONMENT: self._run_environment_tests,
            TestCategory.API_CONTRACTS: self._run_api_contract_tests,
            TestCategory.COMMUNICATION: self._run_communication_tests,
            TestCategory.WORKFLOWS: self._run_workflow_tests,
            TestCategory.PERFORMANCE: self._run_performance_tests
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._initialize_components()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._cleanup_components()
    
    async def _initialize_components(self) -> None:
        """Initialize all test components."""
        self.logger.info("Initializing test components")
        
        # Initialize agent manager
        self.agent_manager = AgentLifecycleManager(self.config, self.logger)
        await self.agent_manager.__aenter__()
        
        # Initialize validators
        self.api_validator = APIContractValidator(self.config)
        await self.api_validator.__aenter__()
        
        self.env_validator = EnvironmentValidator(self.config)
        
        self.comm_validator = CommunicationValidator(self.config)
        await self.comm_validator.__aenter__()
        
        # Initialize workflow simulator
        self.workflow_simulator = WorkflowSimulator(
            self.config, 
            self.agent_manager, 
            self.logger
        )
        await self.workflow_simulator.__aenter__()
        
        # Initialize reporting components
        self.report_generator = ReportGenerator(self.config)
        self.dashboard = TestResultsDashboard(self.config)
        self.performance_tracker = PerformanceTracker(
            sampling_interval=1.0,
            max_samples=1000
        )
        
        self.logger.info("Test components initialized successfully")
    
    async def _cleanup_components(self) -> None:
        """Clean up all test components."""
        self.logger.info("Cleaning up test components")
        
        cleanup_tasks = []
        
        if self.workflow_simulator:
            cleanup_tasks.append(self.workflow_simulator.__aexit__(None, None, None))
        
        if self.comm_validator:
            cleanup_tasks.append(self.comm_validator.__aexit__(None, None, None))
        
        if self.api_validator:
            cleanup_tasks.append(self.api_validator.__aexit__(None, None, None))
        
        if self.agent_manager:
            cleanup_tasks.append(self.agent_manager.__aexit__(None, None, None))
        
        # Clean up reporting components
        if self.dashboard:
            self.dashboard.stop_server()
        
        if self.performance_tracker and self.performance_tracker.is_tracking:
            self.performance_tracker.stop_tracking()
        
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        self.logger.info("Test components cleaned up")
    
    async def run_full_suite(self, context: Optional[Dict[str, Any]] = None) -> TestResults:
        """
        Run the complete integration test suite.
        
        Args:
            context: Additional context for test execution
            
        Returns:
            Complete test results
        """
        execution_plan = ExecutionPlan(
            mode=ExecutionMode.FULL_SUITE,
            categories={
                TestCategory.ENVIRONMENT,
                TestCategory.API_CONTRACTS,
                TestCategory.COMMUNICATION,
                TestCategory.WORKFLOWS,
                TestCategory.PERFORMANCE
            },
            parallel_execution=self.config.parallel_execution,
            max_workers=self.config.max_workers,
            timeout=self.config.timeouts.test_execution,
            context=context or {}
        )
        
        return await self._execute_plan(execution_plan)
    
    async def run_selective_tests(
        self, 
        categories: List[TestCategory], 
        context: Optional[Dict[str, Any]] = None
    ) -> TestResults:
        """
        Run tests for specific categories.
        
        Args:
            categories: List of test categories to run
            context: Additional context for test execution
            
        Returns:
            Test results for selected categories
        """
        execution_plan = ExecutionPlan(
            mode=ExecutionMode.SELECTIVE,
            categories=set(categories),
            parallel_execution=self.config.parallel_execution,
            max_workers=min(self.config.max_workers, len(categories)),
            timeout=self.config.timeouts.test_execution,
            context=context or {}
        )
        
        return await self._execute_plan(execution_plan)
    
    async def run_smoke_tests(self, context: Optional[Dict[str, Any]] = None) -> TestResults:
        """
        Run smoke tests for quick validation.
        
        Args:
            context: Additional context for test execution
            
        Returns:
            Smoke test results
        """
        execution_plan = ExecutionPlan(
            mode=ExecutionMode.SMOKE_TESTS,
            categories={TestCategory.ENVIRONMENT, TestCategory.API_CONTRACTS},
            parallel_execution=True,
            max_workers=2,
            timeout=60.0,  # Quick smoke tests
            context=context or {}
        )
        
        return await self._execute_plan(execution_plan)
    
    async def run_performance_tests(self, context: Optional[Dict[str, Any]] = None) -> TestResults:
        """
        Run performance tests only.
        
        Args:
            context: Additional context for test execution
            
        Returns:
            Performance test results
        """
        execution_plan = ExecutionPlan(
            mode=ExecutionMode.PERFORMANCE_ONLY,
            categories={TestCategory.PERFORMANCE},
            parallel_execution=False,  # Performance tests should run sequentially
            max_workers=1,
            timeout=600.0,  # Performance tests may take longer
            context=context or {}
        )
        
        return await self._execute_plan(execution_plan)
    
    async def _execute_plan(self, plan: ExecutionPlan) -> TestResults:
        """
        Execute a test plan.
        
        Args:
            plan: Execution plan to run
            
        Returns:
            Test results
        """
        # Set up execution context
        execution_id = f"test_run_{int(time.time())}"
        temp_dir = self.config.env_config.temp_dir / execution_id
        log_dir = self.config.env_config.log_dir / execution_id
        artifacts_dir = temp_dir / "artifacts"
        
        # Create directories
        for directory in [temp_dir, log_dir, artifacts_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        self.execution_context = ExecutionContext(
            config=self.config,
            agent_manager=self.agent_manager,
            start_time=datetime.now(),
            execution_id=execution_id,
            temp_dir=temp_dir,
            log_dir=log_dir,
            artifacts_dir=artifacts_dir
        )
        
        # Initialize results
        self.results = TestResults()
        self.results.summary.start_time = self.execution_context.start_time
        
        self.logger.info(
            f"Starting test execution",
            execution_id=execution_id,
            mode=plan.mode.value,
            categories=[cat.value for cat in plan.categories],
            parallel=plan.parallel_execution,
            max_workers=plan.max_workers
        )
        
        try:
            # Pre-execution setup
            await self._pre_execution_setup()
            
            # Execute tests
            if plan.parallel_execution and len(plan.categories) > 1:
                await self._execute_parallel(plan)
            else:
                await self._execute_sequential(plan)
            
            # Post-execution cleanup and reporting
            await self._post_execution_cleanup()
            
        except Exception as e:
            self.logger.error(
                f"Test execution failed",
                execution_id=execution_id,
                error=str(e),
                exc_info=True
            )
            
            # Add error to results
            error_result = TestResult(
                name="Test Execution Error",
                category=TestCategory.ENVIRONMENT,
                status=TestStatus.ERROR,
                duration=0.0
            )
            error_result.mark_failed(
                TestError.from_exception(e, "orchestrator", Severity.CRITICAL)
            )
            self.results.add_result(error_result)
        
        finally:
            # Finalize results
            self.results.finalize()
            
            # Add performance metrics from tracker
            if self.performance_tracker:
                self.results.performance_metrics = self.performance_tracker.create_performance_metrics()
            
            # Update dashboard with results
            if self.dashboard:
                self.dashboard.add_test_results(self.results)
            
            # Save results and generate reports
            await self._save_results()
            await self._generate_reports()
            
            self.logger.info(
                f"Test execution completed",
                execution_id=execution_id,
                duration=self.results.summary.duration,
                total_tests=self.results.summary.total_tests,
                passed=self.results.summary.passed,
                failed=self.results.summary.failed,
                success_rate=self.results.summary.success_rate
            )
        
        return self.results
    
    async def _pre_execution_setup(self) -> None:
        """Perform pre-execution setup."""
        self.logger.info("Performing pre-execution setup")
        
        # Start performance tracking
        if self.performance_tracker:
            self.performance_tracker.start_phase("setup")
        
        # Start agents if needed
        if any(cat in [TestCategory.API_CONTRACTS, TestCategory.COMMUNICATION, TestCategory.WORKFLOWS] 
               for cat in self.execution_context.config.agents.keys()):
            
            self.logger.info("Starting agent servers")
            successful_agents, failed_agents = await self.agent_manager.start_all_agents(parallel=True)
            
            if failed_agents:
                self.logger.warning(
                    f"Some agents failed to start",
                    successful=successful_agents,
                    failed=failed_agents
                )
            
            # Wait for agents to be ready
            if successful_agents:
                ready = await self.agent_manager.wait_for_agents_ready(
                    successful_agents,
                    timeout=self.config.timeouts.agent_startup
                )
                
                if not ready:
                    self.logger.warning("Not all agents became ready within timeout")
        
        # End setup phase and start execution phase
        if self.performance_tracker:
            self.performance_tracker.end_phase()
            self.performance_tracker.start_phase("execution")
        
        # Collect initial system state
        await self._collect_system_diagnostics()
    
    async def _post_execution_cleanup(self) -> None:
        """Perform post-execution cleanup."""
        self.logger.info("Performing post-execution cleanup")
        
        # End execution phase and start teardown phase
        if self.performance_tracker:
            self.performance_tracker.end_phase()
            self.performance_tracker.start_phase("teardown")
        
        # Collect final system state
        await self._collect_system_diagnostics()
        
        # Stop agents
        if self.agent_manager:
            failed_to_stop = await self.agent_manager.stop_all_agents()
            if failed_to_stop:
                self.logger.warning(f"Some agents failed to stop cleanly: {failed_to_stop}")
        
        # End teardown phase
        if self.performance_tracker:
            self.performance_tracker.end_phase()
    
    async def _execute_parallel(self, plan: ExecutionPlan) -> None:
        """Execute test categories in parallel."""
        self.logger.info(f"Executing {len(plan.categories)} test categories in parallel")
        
        # Create semaphore to limit concurrent workers
        semaphore = asyncio.Semaphore(plan.max_workers)
        
        async def run_category_with_semaphore(category: TestCategory) -> List[TestResult]:
            async with semaphore:
                return await self._run_category_tests(category)
        
        # Execute all categories concurrently
        tasks = [
            run_category_with_semaphore(category)
            for category in plan.categories
        ]
        
        try:
            # Wait for all tasks with timeout
            category_results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=plan.timeout
            )
            
            # Process results
            for i, result in enumerate(category_results):
                category = list(plan.categories)[i]
                
                if isinstance(result, Exception):
                    self.logger.error(
                        f"Category {category.value} failed with exception",
                        error=str(result),
                        exc_info=True
                    )
                    
                    # Create error result
                    error_result = TestResult(
                        name=f"{category.value} - Execution Error",
                        category=category,
                        status=TestStatus.ERROR,
                        duration=0.0
                    )
                    error_result.mark_failed(
                        TestError.from_exception(result, category.value, Severity.CRITICAL)
                    )
                    self.results.add_result(error_result)
                else:
                    # Add successful results
                    for test_result in result:
                        self.results.add_result(test_result)
        
        except asyncio.TimeoutError:
            self.logger.error(f"Parallel execution timed out after {plan.timeout}s")
            
            # Create timeout error
            timeout_result = TestResult(
                name="Parallel Execution Timeout",
                category=TestCategory.ENVIRONMENT,
                status=TestStatus.ERROR,
                duration=plan.timeout
            )
            timeout_result.mark_failed(
                TestError(
                    category="orchestrator",
                    severity=Severity.CRITICAL,
                    message=f"Test execution timed out after {plan.timeout}s",
                    suggested_fix="Increase timeout or reduce test scope"
                )
            )
            self.results.add_result(timeout_result)
    
    async def _execute_sequential(self, plan: ExecutionPlan) -> None:
        """Execute test categories sequentially."""
        self.logger.info(f"Executing {len(plan.categories)} test categories sequentially")
        
        for category in plan.categories:
            if self._shutdown_requested:
                self.logger.info("Shutdown requested, stopping test execution")
                break
            
            try:
                category_results = await asyncio.wait_for(
                    self._run_category_tests(category),
                    timeout=plan.timeout / len(plan.categories)
                )
                
                for test_result in category_results:
                    self.results.add_result(test_result)
                    
            except asyncio.TimeoutError:
                self.logger.error(f"Category {category.value} timed out")
                
                timeout_result = TestResult(
                    name=f"{category.value} - Timeout",
                    category=category,
                    status=TestStatus.ERROR,
                    duration=plan.timeout / len(plan.categories)
                )
                timeout_result.mark_failed(
                    TestError(
                        category=category.value,
                        severity=Severity.HIGH,
                        message=f"Category tests timed out",
                        suggested_fix="Increase timeout or optimize tests"
                    )
                )
                self.results.add_result(timeout_result)
                
            except Exception as e:
                self.logger.error(
                    f"Category {category.value} failed with exception",
                    error=str(e),
                    exc_info=True
                )
                
                error_result = TestResult(
                    name=f"{category.value} - Execution Error",
                    category=category,
                    status=TestStatus.ERROR,
                    duration=0.0
                )
                error_result.mark_failed(
                    TestError.from_exception(e, category.value, Severity.CRITICAL)
                )
                self.results.add_result(error_result)
    
    async def _run_category_tests(self, category: TestCategory) -> List[TestResult]:
        """
        Run tests for a specific category.
        
        Args:
            category: Test category to run
            
        Returns:
            List of test results for the category
        """
        if category not in self.category_handlers:
            self.logger.warning(f"No handler for category: {category.value}")
            return []
        
        self.logger.info(f"Running {category.value} tests")
        start_time = time.time()
        
        try:
            handler = self.category_handlers[category]
            results = await handler(self.execution_context)
            
            duration = time.time() - start_time
            self.logger.info(
                f"Completed {category.value} tests",
                duration=duration,
                test_count=len(results),
                passed=len([r for r in results if r.status == TestStatus.PASSED]),
                failed=len([r for r in results if r.status == TestStatus.FAILED])
            )
            
            return results
            
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(
                f"Failed to run {category.value} tests",
                duration=duration,
                error=str(e),
                exc_info=True
            )
            
            # Return error result
            error_result = TestResult(
                name=f"{category.value} - Handler Error",
                category=category,
                status=TestStatus.ERROR,
                duration=duration
            )
            error_result.mark_failed(
                TestError.from_exception(e, category.value, Severity.CRITICAL)
            )
            
            return [error_result]
    
    # Category test handlers
    
    async def _run_environment_tests(self, context: ExecutionContext) -> List[TestResult]:
        """Run environment validation tests."""
        self.logger.debug("Running environment validation tests")
        
        validation_result = self.env_validator.validate_environment()
        
        # Create test result
        test_result = TestResult(
            name="Environment Validation",
            category=TestCategory.ENVIRONMENT,
            status=TestStatus.RUNNING,
            duration=0.0,
            context={
                "python_info": validation_result.python_info,
                "ssl_info": validation_result.ssl_info,
                "system_info": validation_result.system_info,
                "package_count": len(validation_result.package_info)
            }
        )
        
        if validation_result.is_valid:
            test_result.mark_passed("Environment validation successful")
        else:
            critical_issues = [
                issue for issue in validation_result.issues 
                if issue.severity in [Severity.CRITICAL, Severity.HIGH]
            ]
            
            error_message = f"Environment validation failed with {len(critical_issues)} critical/high issues"
            test_result.mark_failed(
                TestError(
                    category="environment",
                    severity=Severity.HIGH,
                    message=error_message,
                    context={"issues": [issue.to_dict() for issue in critical_issues]},
                    suggested_fix="Fix environment issues before running integration tests"
                )
            )
        
        # Store environment issues in results
        self.results.environment_issues.extend(validation_result.issues)
        
        return [test_result]
    
    async def _run_api_contract_tests(self, context: ExecutionContext) -> List[TestResult]:
        """Run API contract validation tests."""
        self.logger.debug("Running API contract validation tests")
        
        return await self.api_validator.run_contract_tests()
    
    async def _run_communication_tests(self, context: ExecutionContext) -> List[TestResult]:
        """Run cross-system communication tests."""
        self.logger.debug("Running communication validation tests")
        
        test_results = []
        
        try:
            validation_results = await self.comm_validator.validate_all_communication()
            
            for validation_result in validation_results:
                # Create test result for each agent
                test_result = TestResult(
                    name=f"Communication Validation - {validation_result.agent_name}",
                    category=TestCategory.COMMUNICATION,
                    status=TestStatus.RUNNING,
                    duration=0.0,
                    context=validation_result.to_dict()
                )
                
                if validation_result.overall_valid:
                    test_result.mark_passed(
                        f"All communication protocols valid for {validation_result.agent_name}"
                    )
                else:
                    error_messages = []
                    if validation_result.cors_result and not validation_result.cors_result.is_valid:
                        error_messages.append(f"CORS issues: {len(validation_result.cors_result.cors_violations)}")
                    if validation_result.jsonrpc_result and not validation_result.jsonrpc_result.is_valid:
                        error_messages.append(f"JSON-RPC issues: {len(validation_result.jsonrpc_result.protocol_violations)}")
                    if validation_result.network_result and not validation_result.network_result.is_valid:
                        error_messages.append(f"Network issues: {len(validation_result.network_result.network_issues)}")
                    
                    test_result.mark_failed(
                        TestError(
                            category="communication",
                            severity=Severity.HIGH,
                            message="; ".join(error_messages),
                            context=validation_result.to_dict(),
                            suggested_fix="Fix communication protocol issues in agent configuration"
                        )
                    )
                
                test_results.append(test_result)
        
        except Exception as e:
            # Create failed test result for overall communication validation
            test_result = TestResult(
                name="Communication Validation - Overall",
                category=TestCategory.COMMUNICATION,
                status=TestStatus.ERROR,
                duration=0.0
            )
            test_result.mark_failed(
                TestError.from_exception(e, "communication", Severity.CRITICAL)
            )
            test_results.append(test_result)
        
        return test_results
    
    async def _run_workflow_tests(self, context: ExecutionContext) -> List[TestResult]:
        """Run end-to-end workflow tests."""
        self.logger.debug("Running workflow simulation tests")
        
        test_results = []
        
        # Define workflows to test
        workflows_to_test = [
            WorkflowType.TERRAIN_LOADING,
            WorkflowType.CACHE_INTEGRATION,
            WorkflowType.OFFLINE_MODE,
            WorkflowType.ERROR_SCENARIOS
        ]
        
        for workflow_type in workflows_to_test:
            try:
                workflow_result = await self.workflow_simulator.simulate_workflow(workflow_type)
                
                # Create test result
                test_result = TestResult(
                    name=f"Workflow Simulation - {workflow_type.value}",
                    category=TestCategory.WORKFLOWS,
                    status=TestStatus.RUNNING,
                    duration=workflow_result.duration,
                    context={
                        "workflow_type": workflow_type.value,
                        "state": workflow_result.state.value,
                        "steps_completed": workflow_result.steps_completed,
                        "steps_total": workflow_result.steps_total,
                        "context": workflow_result.context
                    }
                )
                
                if workflow_result.success:
                    test_result.mark_passed(
                        f"Workflow {workflow_type.value} completed successfully "
                        f"({workflow_result.steps_completed}/{workflow_result.steps_total} steps)"
                    )
                else:
                    error_message = f"Workflow {workflow_type.value} failed"
                    if workflow_result.error:
                        error_message += f": {workflow_result.error.message}"
                    
                    test_result.mark_failed(
                        workflow_result.error or TestError(
                            category="workflows",
                            severity=Severity.HIGH,
                            message=error_message,
                            suggested_fix="Review workflow simulation logs for specific issues"
                        )
                    )
                
                test_results.append(test_result)
                
            except Exception as e:
                # Create error result for failed workflow
                test_result = TestResult(
                    name=f"Workflow Simulation - {workflow_type.value}",
                    category=TestCategory.WORKFLOWS,
                    status=TestStatus.ERROR,
                    duration=0.0
                )
                test_result.mark_failed(
                    TestError.from_exception(e, "workflows", Severity.HIGH)
                )
                test_results.append(test_result)
        
        return test_results
    
    async def _save_results(self) -> None:
        """Save test results to files."""
        if not self.results or not self.execution_context:
            return
        
        try:
            # Save raw results as JSON
            results_file = self.execution_context.artifacts_dir / "test_results.json"
            results_data = self.results.to_dict()
            
            with open(results_file, 'w') as f:
                json.dump(results_data, f, indent=2, default=str)
            
            self.logger.info(f"Test results saved to {results_file}")
            
            # Save summary
            summary_file = self.execution_context.artifacts_dir / "test_summary.json"
            summary_data = {
                "execution_id": self.execution_context.execution_id,
                "summary": self.results.summary.to_dict(),
                "categories": {
                    cat.value: results.to_dict() 
                    for cat, results in self.results.categories.items()
                },
                "agent_health_summary": {
                    agent.name: agent.status 
                    for agent in self.results.agent_health
                },
                "environment_issues_count": len(self.results.environment_issues),
                "performance_summary": (
                    self.results.performance_metrics.__dict__ 
                    if self.results.performance_metrics else None
                )
            }
            
            with open(summary_file, 'w') as f:
                json.dump(summary_data, f, indent=2, default=str)
            
            self.logger.info(f"Test summary saved to {summary_file}")
            
            # Save failed tests separately for easy access
            failed_tests = self.results.get_failed_tests()
            if failed_tests:
                failed_file = self.execution_context.artifacts_dir / "failed_tests.json"
                failed_data = [test.to_dict() for test in failed_tests]
                
                with open(failed_file, 'w') as f:
                    json.dump(failed_data, f, indent=2, default=str)
                
                self.logger.info(f"Failed tests saved to {failed_file}")
        
        except Exception as e:
            self.logger.error(f"Failed to save test results: {e}", exc_info=True)
    
    async def _generate_reports(self) -> None:
        """Generate test reports in multiple formats."""
        if not self.results or not self.execution_context or not self.report_generator:
            return
        
        try:
            report_formats = ["json", "html", "junit", "markdown"]
            
            report_paths = self.report_generator.generate_multiple_formats(
                results=self.results,
                formats=report_formats,
                output_dir=self.execution_context.artifacts_dir,
                include_diagnostics=True
            )
            
            self.logger.info(
                f"Generated reports in {len(report_paths)} formats",
                formats=list(report_paths.keys()),
                paths=[str(path) for path in report_paths.values()]
            )
            
            # Store report paths in execution context for later access
            if not hasattr(self.execution_context, 'report_paths'):
                self.execution_context.report_paths = {}
            self.execution_context.report_paths.update(report_paths)
        
        except Exception as e:
            self.logger.error(f"Failed to generate reports: {e}", exc_info=True)
    
    async def _collect_system_diagnostics(self) -> None:
        """Collect system diagnostic information."""
        if not self.results:
            return
        
        try:
            diagnostics = {}
            
            # Collect agent health if available
            if self.agent_manager:
                agent_health = await self.agent_manager.get_all_agent_health()
                self.results.agent_health = agent_health
                diagnostics["agent_health_collected"] = len(agent_health)
            
            # Collect performance snapshot if available
            if self.performance_tracker:
                current_metrics = self.performance_tracker.get_current_metrics()
                if current_metrics:
                    diagnostics["performance_snapshot"] = {
                        "cpu_percent": current_metrics.cpu_percent,
                        "memory_percent": current_metrics.memory_percent,
                        "memory_used_mb": current_metrics.memory_used_mb,
                        "timestamp": current_metrics.timestamp.isoformat()
                    }
            
            # Add system information
            import platform
            import sys
            
            diagnostics["system_info"] = {
                "platform": platform.platform(),
                "python_version": sys.version,
                "architecture": platform.architecture(),
                "processor": platform.processor(),
                "timestamp": datetime.now().isoformat()
            }
            
            # Update results diagnostics
            self.results.diagnostics.update(diagnostics)
        
        except Exception as e:
            self.logger.error(f"Failed to collect system diagnostics: {e}", exc_info=True)
    
    def start_dashboard(self, port: int = 8080, open_browser: bool = True) -> Optional[str]:
        """
        Start the test results dashboard.
        
        Args:
            port: Port to run dashboard on
            open_browser: Whether to open browser automatically
            
        Returns:
            Dashboard URL or None if failed
        """
        if not self.dashboard:
            self.logger.warning("Dashboard not initialized")
            return None
        
        try:
            url = self.dashboard.start_server(port=port, open_browser=open_browser)
            self.logger.info(f"Dashboard started at {url}")
            return url
        except Exception as e:
            self.logger.error(f"Failed to start dashboard: {e}")
            return None
    
    def stop_dashboard(self) -> None:
        """Stop the test results dashboard."""
        if self.dashboard:
            self.dashboard.stop_server()
            self.logger.info("Dashboard stopped")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get performance summary from tracker.
        
        Returns:
            Performance summary data
        """
        if self.performance_tracker:
            return self.performance_tracker.get_performance_summary()
        return {"message": "Performance tracking not available"}
    
    def export_dashboard_data(self, output_path: Path) -> None:
        """
        Export dashboard data to file.
        
        Args:
            output_path: Path to export data to
        """
        if self.dashboard:
            self.dashboard.export_data(output_path)
            self.logger.info(f"Dashboard data exported to {output_path}")
        else:
            self.logger.warning("Dashboard not available for data export")
    
    async def _run_performance_tests(self, context: ExecutionContext) -> List[TestResult]:
        """Run performance validation tests."""
        self.logger.debug("Running performance validation tests")
        
        test_results = []
        
        try:
            # Run performance workflow
            workflow_result = await self.workflow_simulator.simulate_workflow(
                WorkflowType.PERFORMANCE_VALIDATION
            )
            
            # Create test result
            test_result = TestResult(
                name="Performance Validation",
                category=TestCategory.PERFORMANCE,
                status=TestStatus.RUNNING,
                duration=workflow_result.duration,
                context={
                    "workflow_result": {
                        "state": workflow_result.state.value,
                        "steps_completed": workflow_result.steps_completed,
                        "steps_total": workflow_result.steps_total
                    }
                }
            )
            
            if workflow_result.success:
                test_result.mark_passed("Performance validation completed successfully")
                
                # Store performance metrics
                if workflow_result.performance_metrics:
                    self.results.performance_metrics = workflow_result.performance_metrics
            else:
                error_message = "Performance validation failed"
                if workflow_result.error:
                    error_message += f": {workflow_result.error.message}"
                
                test_result.mark_failed(
                    workflow_result.error or TestError(
                        category="performance",
                        severity=Severity.MEDIUM,
                        message=error_message,
                        suggested_fix="Review performance test logs and optimize system performance"
                    )
                )
            
            test_results.append(test_result)
            
        except Exception as e:
            # Create error result for performance tests
            test_result = TestResult(
                name="Performance Validation",
                category=TestCategory.PERFORMANCE,
                status=TestStatus.ERROR,
                duration=0.0
            )
            test_result.mark_failed(
                TestError.from_exception(e, "performance", Severity.MEDIUM)
            )
            test_results.append(test_result)
        
        return test_results
    
    async def _collect_system_diagnostics(self) -> None:
        """Collect system diagnostic information."""
        try:
            # Collect agent health status
            if self.agent_manager:
                agent_health = await self.agent_manager.check_all_agents_health()
                self.results.agent_health = list(agent_health.values())
            
            # Collect environment diagnostics
            if self.env_validator:
                env_diagnostics = self.env_validator.get_diagnostic_info()
                self.results.diagnostics.update(env_diagnostics)
            
        except Exception as e:
            self.logger.warning(f"Failed to collect system diagnostics: {e}")
    
    async def _save_results(self) -> None:
        """Save test results to files."""
        if not self.execution_context or not self.results:
            return
        
        try:
            # Save JSON results
            results_file = self.execution_context.artifacts_dir / "test_results.json"
            with open(results_file, 'w') as f:
                json.dump(self.results.to_dict(), f, indent=2, default=str)
            
            # Save summary
            summary_file = self.execution_context.artifacts_dir / "test_summary.json"
            with open(summary_file, 'w') as f:
                json.dump(self.results.summary.to_dict(), f, indent=2, default=str)
            
            # Save failed tests details
            failed_tests = self.results.get_failed_tests()
            if failed_tests:
                failed_file = self.execution_context.artifacts_dir / "failed_tests.json"
                with open(failed_file, 'w') as f:
                    json.dump([test.to_dict() for test in failed_tests], f, indent=2, default=str)
            
            self.logger.info(
                f"Test results saved",
                results_file=str(results_file),
                summary_file=str(summary_file),
                failed_tests_count=len(failed_tests)
            )
            
        except Exception as e:
            self.logger.error(f"Failed to save test results: {e}")
    
    def request_shutdown(self) -> None:
        """Request graceful shutdown of test execution."""
        self.logger.info("Shutdown requested")
        self._shutdown_requested = True
    
    def get_execution_status(self) -> Dict[str, Any]:
        """Get current execution status."""
        if not self.execution_context or not self.results:
            return {"status": "not_running"}
        
        return {
            "status": "running",
            "execution_id": self.execution_context.execution_id,
            "start_time": self.execution_context.start_time.isoformat(),
            "duration": (datetime.now() - self.execution_context.start_time).total_seconds(),
            "tests_completed": self.results.summary.total_tests,
            "tests_passed": self.results.summary.passed,
            "tests_failed": self.results.summary.failed,
            "categories_completed": len(self.results.categories)
        }