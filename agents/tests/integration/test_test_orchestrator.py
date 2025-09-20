"""
Unit tests for the Integration Test Orchestrator.

Tests the orchestrator's ability to coordinate test execution, manage parallel
execution, aggregate results, and handle various execution scenarios.
"""

import asyncio
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest

from agents.tests.integration.config import AgentConfig
from agents.tests.integration.config import TestConfig
from agents.tests.integration.config import TimeoutConfig
from agents.tests.integration.models import AgentHealthStatus
from agents.tests.integration.models import Severity
from agents.tests.integration.models import TestCategory
from agents.tests.integration.models import TestResult
from agents.tests.integration.models import TestResults
from agents.tests.integration.models import TestStatus
from agents.tests.integration.test_orchestrator import ExecutionMode
from agents.tests.integration.test_orchestrator import ExecutionPlan
from agents.tests.integration.test_orchestrator import IntegrationTestOrchestrator


@pytest.fixture
def test_config():
    """Create test configuration."""
    config = TestConfig()
    config.agents = {
        "test_agent": AgentConfig(name="test_agent", port=8001, enabled=True)
    }
    config.timeouts = TimeoutConfig(
        agent_startup=10, test_execution=60, network_request=5
    )
    config.parallel_execution = True
    config.max_workers = 2

    # Set up temp directories
    temp_dir = Path(tempfile.mkdtemp())
    config.env_config.temp_dir = temp_dir / "integration_tests"
    config.env_config.log_dir = temp_dir / "logs"

    yield config

    # Cleanup
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_components():
    """Create mock test components."""
    components = {
        "agent_manager": AsyncMock(),
        "api_validator": AsyncMock(),
        "env_validator": Mock(),
        "comm_validator": AsyncMock(),
        "workflow_simulator": AsyncMock(),
    }

    # Configure mock behaviors
    components["agent_manager"].start_all_agents.return_value = (["test_agent"], [])
    components["agent_manager"].wait_for_agents_ready.return_value = True
    components["agent_manager"].stop_all_agents.return_value = []
    components["agent_manager"].check_all_agents_health.return_value = {
        "test_agent": AgentHealthStatus(
            name="test_agent", status="healthy", response_time=0.1
        )
    }

    return components


class TestIntegrationTestOrchestrator:
    """Test cases for IntegrationTestOrchestrator."""

    @pytest.mark.asyncio
    async def test_initialization(self, test_config):
        """Test orchestrator initialization."""
        orchestrator = IntegrationTestOrchestrator(test_config)

        assert orchestrator.config == test_config
        assert orchestrator.agent_manager is None
        assert orchestrator.results is None
        assert not orchestrator._shutdown_requested

        # Test category handlers are registered
        expected_categories = {
            TestCategory.ENVIRONMENT,
            TestCategory.API_CONTRACTS,
            TestCategory.COMMUNICATION,
            TestCategory.WORKFLOWS,
            TestCategory.PERFORMANCE,
        }
        assert set(orchestrator.category_handlers.keys()) == expected_categories

    @pytest.mark.asyncio
    async def test_context_manager(self, test_config, mock_components):
        """Test async context manager functionality."""
        orchestrator = IntegrationTestOrchestrator(test_config)

        with patch.multiple(
            orchestrator,
            _initialize_components=AsyncMock(),
            _cleanup_components=AsyncMock(),
        ):
            async with orchestrator:
                assert orchestrator._initialize_components.called

            assert orchestrator._cleanup_components.called

    @pytest.mark.asyncio
    async def test_component_initialization(self, test_config):
        """Test component initialization."""
        orchestrator = IntegrationTestOrchestrator(test_config)

        with patch.multiple(
            "agents.tests.integration.test_orchestrator",
            AgentLifecycleManager=Mock(return_value=AsyncMock()),
            APIContractValidator=Mock(return_value=AsyncMock()),
            EnvironmentValidator=Mock(return_value=Mock()),
            CommunicationValidator=Mock(return_value=AsyncMock()),
            WorkflowSimulator=Mock(return_value=AsyncMock()),
        ):
            await orchestrator._initialize_components()

            assert orchestrator.agent_manager is not None
            assert orchestrator.api_validator is not None
            assert orchestrator.env_validator is not None
            assert orchestrator.comm_validator is not None
            assert orchestrator.workflow_simulator is not None

    @pytest.mark.asyncio
    async def test_run_full_suite(self, test_config, mock_components):
        """Test running the full test suite."""
        orchestrator = IntegrationTestOrchestrator(test_config)

        # Mock the execution plan
        with patch.object(orchestrator, "_execute_plan") as mock_execute:
            mock_results = TestResults()
            mock_execute.return_value = mock_results

            results = await orchestrator.run_full_suite()

            assert results == mock_results
            mock_execute.assert_called_once()

            # Check execution plan
            call_args = mock_execute.call_args[0][0]
            assert call_args.mode == ExecutionMode.FULL_SUITE
            assert len(call_args.categories) == 5  # All categories
            assert call_args.parallel_execution == test_config.parallel_execution

    @pytest.mark.asyncio
    async def test_run_selective_tests(self, test_config):
        """Test running selective test categories."""
        orchestrator = IntegrationTestOrchestrator(test_config)

        selected_categories = [TestCategory.ENVIRONMENT, TestCategory.API_CONTRACTS]

        with patch.object(orchestrator, "_execute_plan") as mock_execute:
            mock_results = TestResults()
            mock_execute.return_value = mock_results

            results = await orchestrator.run_selective_tests(selected_categories)

            assert results == mock_results
            mock_execute.assert_called_once()

            # Check execution plan
            call_args = mock_execute.call_args[0][0]
            assert call_args.mode == ExecutionMode.SELECTIVE
            assert call_args.categories == set(selected_categories)

    @pytest.mark.asyncio
    async def test_run_smoke_tests(self, test_config):
        """Test running smoke tests."""
        orchestrator = IntegrationTestOrchestrator(test_config)

        with patch.object(orchestrator, "_execute_plan") as mock_execute:
            mock_results = TestResults()
            mock_execute.return_value = mock_results

            results = await orchestrator.run_smoke_tests()

            assert results == mock_results
            mock_execute.assert_called_once()

            # Check execution plan
            call_args = mock_execute.call_args[0][0]
            assert call_args.mode == ExecutionMode.SMOKE_TESTS
            assert call_args.categories == {
                TestCategory.ENVIRONMENT,
                TestCategory.API_CONTRACTS,
            }
            assert call_args.timeout == 60.0  # Quick smoke tests

    @pytest.mark.asyncio
    async def test_run_performance_tests(self, test_config):
        """Test running performance tests only."""
        orchestrator = IntegrationTestOrchestrator(test_config)

        with patch.object(orchestrator, "_execute_plan") as mock_execute:
            mock_results = TestResults()
            mock_execute.return_value = mock_results

            results = await orchestrator.run_performance_tests()

            assert results == mock_results
            mock_execute.assert_called_once()

            # Check execution plan
            call_args = mock_execute.call_args[0][0]
            assert call_args.mode == ExecutionMode.PERFORMANCE_ONLY
            assert call_args.categories == {TestCategory.PERFORMANCE}
            assert (
                not call_args.parallel_execution
            )  # Performance tests run sequentially
            assert call_args.max_workers == 1

    @pytest.mark.asyncio
    async def test_execute_plan_setup(self, test_config):
        """Test execution plan setup."""
        orchestrator = IntegrationTestOrchestrator(test_config)

        # Mock all the methods called during execution
        with patch.multiple(
            orchestrator,
            _initialize_components=AsyncMock(),
            _cleanup_components=AsyncMock(),
            _pre_execution_setup=AsyncMock(),
            _execute_sequential=AsyncMock(),
            _post_execution_cleanup=AsyncMock(),
            _save_results=AsyncMock(),
        ):
            plan = ExecutionPlan(
                mode=ExecutionMode.SELECTIVE,
                categories={TestCategory.ENVIRONMENT},
                parallel_execution=False,
            )

            async with orchestrator:
                await orchestrator._execute_plan(plan)

            # Check that execution context was set up
            assert orchestrator.execution_context is not None
            assert orchestrator.results is not None

            # Check that setup and cleanup were called
            orchestrator._pre_execution_setup.assert_called_once()
            orchestrator._post_execution_cleanup.assert_called_once()
            orchestrator._save_results.assert_called_once()

    @pytest.mark.asyncio
    async def test_parallel_execution(self, test_config):
        """Test parallel test execution."""
        orchestrator = IntegrationTestOrchestrator(test_config)

        # Mock category test methods
        mock_results = [
            TestResult("Test 1", TestCategory.ENVIRONMENT, TestStatus.PASSED, 1.0),
            TestResult("Test 2", TestCategory.API_CONTRACTS, TestStatus.PASSED, 2.0),
        ]

        with patch.object(orchestrator, "_run_category_tests") as mock_run_category:
            mock_run_category.side_effect = [
                [mock_results[0]],  # Environment tests
                [mock_results[1]],  # API contract tests
            ]

            orchestrator.results = TestResults()

            plan = ExecutionPlan(
                mode=ExecutionMode.SELECTIVE,
                categories={TestCategory.ENVIRONMENT, TestCategory.API_CONTRACTS},
                parallel_execution=True,
                max_workers=2,
                timeout=60.0,
            )

            await orchestrator._execute_parallel(plan)

            # Check that both categories were run
            assert mock_run_category.call_count == 2

            # Check that results were added
            assert orchestrator.results.summary.total_tests == 2
            assert orchestrator.results.summary.passed == 2

    @pytest.mark.asyncio
    async def test_sequential_execution(self, test_config):
        """Test sequential test execution."""
        orchestrator = IntegrationTestOrchestrator(test_config)

        # Mock category test methods
        mock_results = [
            TestResult("Test 1", TestCategory.ENVIRONMENT, TestStatus.PASSED, 1.0),
            TestResult("Test 2", TestCategory.API_CONTRACTS, TestStatus.FAILED, 2.0),
        ]

        with patch.object(orchestrator, "_run_category_tests") as mock_run_category:
            mock_run_category.side_effect = [
                [mock_results[0]],  # Environment tests
                [mock_results[1]],  # API contract tests
            ]

            orchestrator.results = TestResults()

            plan = ExecutionPlan(
                mode=ExecutionMode.SELECTIVE,
                categories={TestCategory.ENVIRONMENT, TestCategory.API_CONTRACTS},
                parallel_execution=False,
                timeout=60.0,
            )

            await orchestrator._execute_sequential(plan)

            # Check that both categories were run in order
            assert mock_run_category.call_count == 2

            # Check that results were added
            assert orchestrator.results.summary.total_tests == 2
            assert orchestrator.results.summary.passed == 1
            assert orchestrator.results.summary.failed == 1

    @pytest.mark.asyncio
    async def test_parallel_execution_timeout(self, test_config):
        """Test parallel execution timeout handling."""
        orchestrator = IntegrationTestOrchestrator(test_config)
        orchestrator.results = TestResults()

        # Mock a slow category test
        async def slow_category_test(category):
            await asyncio.sleep(2.0)  # Longer than timeout
            return [TestResult("Slow Test", category, TestStatus.PASSED, 2.0)]

        with patch.object(
            orchestrator, "_run_category_tests", side_effect=slow_category_test
        ):
            plan = ExecutionPlan(
                mode=ExecutionMode.SELECTIVE,
                categories={TestCategory.ENVIRONMENT},
                parallel_execution=True,
                timeout=0.5,  # Very short timeout
            )

            await orchestrator._execute_parallel(plan)

            # Should have created a timeout error result
            assert orchestrator.results.summary.total_tests == 1
            assert orchestrator.results.summary.failed == 1

            # Check the error result
            failed_tests = orchestrator.results.get_failed_tests()
            assert len(failed_tests) == 1
            assert "timed out" in failed_tests[0].error.message.lower()

    @pytest.mark.asyncio
    async def test_category_handler_error(self, test_config):
        """Test handling of category handler errors."""
        orchestrator = IntegrationTestOrchestrator(test_config)

        # Mock a failing category handler
        async def failing_handler(context):
            raise ValueError("Test handler error")

        orchestrator.category_handlers[TestCategory.ENVIRONMENT] = failing_handler

        # Mock execution context
        orchestrator.execution_context = Mock()

        results = await orchestrator._run_category_tests(TestCategory.ENVIRONMENT)

        # Should return error result
        assert len(results) == 1
        assert results[0].status == TestStatus.FAILED
        assert "Test handler error" in results[0].error.message

    @pytest.mark.asyncio
    async def test_environment_tests(self, test_config):
        """Test environment validation tests."""
        orchestrator = IntegrationTestOrchestrator(test_config)
        orchestrator.results = TestResults()

        # Mock environment validator
        mock_env_validator = Mock()
        mock_validation_result = Mock()
        mock_validation_result.is_valid = True
        mock_validation_result.issues = []
        mock_validation_result.python_info = {"version": "3.9.0"}
        mock_validation_result.ssl_info = {"version": "OpenSSL 1.1.1"}
        mock_validation_result.system_info = {"platform": "linux"}
        mock_validation_result.package_info = {}

        mock_env_validator.validate_environment.return_value = mock_validation_result
        orchestrator.env_validator = mock_env_validator

        # Mock execution context
        context = Mock()

        results = await orchestrator._run_environment_tests(context)

        assert len(results) == 1
        assert results[0].category == TestCategory.ENVIRONMENT
        assert results[0].status == TestStatus.PASSED
        assert "Environment validation successful" in results[0].message

    @pytest.mark.asyncio
    async def test_environment_tests_with_issues(self, test_config):
        """Test environment validation with issues."""
        orchestrator = IntegrationTestOrchestrator(test_config)
        orchestrator.results = TestResults()

        # Mock environment validator with issues
        mock_env_validator = Mock()
        mock_validation_result = Mock()
        mock_validation_result.is_valid = False
        mock_validation_result.issues = [
            Mock(severity=Severity.CRITICAL, to_dict=lambda: {"severity": "critical"})
        ]
        mock_validation_result.python_info = {"version": "3.9.0"}
        mock_validation_result.ssl_info = {"version": "OpenSSL 1.1.1"}
        mock_validation_result.system_info = {"platform": "linux"}
        mock_validation_result.package_info = {}

        mock_env_validator.validate_environment.return_value = mock_validation_result
        orchestrator.env_validator = mock_env_validator

        # Mock execution context
        context = Mock()

        results = await orchestrator._run_environment_tests(context)

        assert len(results) == 1
        assert results[0].category == TestCategory.ENVIRONMENT
        assert results[0].status == TestStatus.FAILED
        assert "Environment validation failed" in results[0].error.message

    @pytest.mark.asyncio
    async def test_api_contract_tests(self, test_config):
        """Test API contract validation tests."""
        orchestrator = IntegrationTestOrchestrator(test_config)

        # Mock API validator
        mock_api_validator = AsyncMock()
        mock_test_results = [
            TestResult(
                "API Test 1", TestCategory.API_CONTRACTS, TestStatus.PASSED, 1.0
            ),
            TestResult(
                "API Test 2", TestCategory.API_CONTRACTS, TestStatus.FAILED, 2.0
            ),
        ]
        mock_api_validator.run_contract_tests.return_value = mock_test_results
        orchestrator.api_validator = mock_api_validator

        # Mock execution context
        context = Mock()

        results = await orchestrator._run_api_contract_tests(context)

        assert results == mock_test_results
        mock_api_validator.run_contract_tests.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_request(self, test_config):
        """Test graceful shutdown request."""
        orchestrator = IntegrationTestOrchestrator(test_config)

        assert not orchestrator._shutdown_requested

        orchestrator.request_shutdown()

        assert orchestrator._shutdown_requested

    @pytest.mark.asyncio
    async def test_execution_status(self, test_config):
        """Test execution status reporting."""
        orchestrator = IntegrationTestOrchestrator(test_config)

        # Test not running status
        status = orchestrator.get_execution_status()
        assert status["status"] == "not_running"

        # Mock running status
        orchestrator.execution_context = Mock()
        orchestrator.execution_context.execution_id = "test_123"
        orchestrator.execution_context.start_time = datetime.now()

        orchestrator.results = TestResults()
        orchestrator.results.summary.total_tests = 5
        orchestrator.results.summary.passed = 3
        orchestrator.results.summary.failed = 2

        status = orchestrator.get_execution_status()
        assert status["status"] == "running"
        assert status["execution_id"] == "test_123"
        assert status["tests_completed"] == 5
        assert status["tests_passed"] == 3
        assert status["tests_failed"] == 2

    @pytest.mark.asyncio
    async def test_save_results(self, test_config):
        """Test saving test results to files."""
        orchestrator = IntegrationTestOrchestrator(test_config)

        # Set up execution context and results
        temp_dir = Path(tempfile.mkdtemp())
        artifacts_dir = temp_dir / "artifacts"
        artifacts_dir.mkdir(parents=True)

        orchestrator.execution_context = Mock()
        orchestrator.execution_context.artifacts_dir = artifacts_dir

        orchestrator.results = TestResults()
        orchestrator.results.summary.total_tests = 2
        orchestrator.results.summary.passed = 1
        orchestrator.results.summary.failed = 1

        # Add a failed test
        failed_test = TestResult(
            "Failed Test", TestCategory.ENVIRONMENT, TestStatus.FAILED, 1.0
        )
        failed_test.mark_failed("Test error")
        orchestrator.results.add_result(failed_test)

        try:
            await orchestrator._save_results()

            # Check that files were created
            assert (artifacts_dir / "test_results.json").exists()
            assert (artifacts_dir / "test_summary.json").exists()
            assert (artifacts_dir / "failed_tests.json").exists()

        finally:
            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_collect_system_diagnostics(self, test_config):
        """Test system diagnostics collection."""
        orchestrator = IntegrationTestOrchestrator(test_config)
        orchestrator.results = TestResults()

        # Mock agent manager
        mock_agent_manager = AsyncMock()
        mock_agent_health = {
            "test_agent": AgentHealthStatus(
                name="test_agent", status="healthy", response_time=0.1
            )
        }
        mock_agent_manager.check_all_agents_health.return_value = mock_agent_health
        orchestrator.agent_manager = mock_agent_manager

        # Mock environment validator
        mock_env_validator = Mock()
        mock_env_validator.get_diagnostic_info.return_value = {
            "validation_result": {"is_valid": True}
        }
        orchestrator.env_validator = mock_env_validator

        await orchestrator._collect_system_diagnostics()

        # Check that diagnostics were collected
        assert len(orchestrator.results.agent_health) == 1
        assert orchestrator.results.agent_health[0].name == "test_agent"
        assert "validation_result" in orchestrator.results.diagnostics


if __name__ == "__main__":
    pytest.main([__file__])
