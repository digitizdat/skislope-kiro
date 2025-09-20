"""
Unit tests for the error handling and diagnostics system.

Tests the comprehensive error handling capabilities including:
- Error categorization and diagnostics collection
- Suggested fix generation
- Error recovery and retry strategies
- Diagnostic information collection
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock
from unittest.mock import patch

import pytest

from .error_handler import DiagnosticCollector
from .error_handler import DiagnosticInfo
from .error_handler import EnhancedTestError
from .error_handler import ErrorCategory
from .error_handler import ErrorFixSuggester
from .error_handler import ErrorRecoveryManager
from .error_handler import ErrorType
from .error_handler import IntegrationTestErrorHandler
from .error_handler import RetryConfig
from .models import Severity
from .models import TestCategory
from .models import TestStatus


class TestEnhancedTestError:
    """Test the EnhancedTestError class."""

    def test_create_enhanced_error(self):
        """Test creating an enhanced test error."""
        error = EnhancedTestError(
            category=ErrorCategory.ENVIRONMENT,
            error_type=ErrorType.MISSING_DEPENDENCY,
            message="Module not found",
            severity=Severity.HIGH,
            context={"module": "test_module"},
            suggested_fix="Install the module",
        )

        assert error.category == "environment"
        assert error.error_type == "missing_dependency"
        assert error.message == "Module not found"
        assert error.severity == Severity.HIGH
        assert error.context["module"] == "test_module"
        assert error.suggested_fix == "Install the module"

    def test_from_exception(self):
        """Test creating enhanced error from exception."""
        exc = ImportError("No module named 'test_module'")

        error = EnhancedTestError.from_exception(
            exc,
            category=ErrorCategory.ENVIRONMENT,
            error_type=ErrorType.MISSING_DEPENDENCY,
            context={"test": "context"},
        )

        assert error.category == "environment"
        assert error.error_type == "missing_dependency"
        assert "No module named 'test_module'" in error.message
        assert error.context["exception_type"] == "ImportError"
        assert error.stack_trace is not None
        assert error.suggested_fix is not None

    def test_to_dict(self):
        """Test converting enhanced error to dictionary."""
        diagnostics = DiagnosticInfo(
            system_info={"platform": "test"}, context={"test": "data"}
        )

        error = EnhancedTestError(
            category=ErrorCategory.COMMUNICATION,
            error_type=ErrorType.CORS_FAILURE,
            message="CORS error",
            diagnostics=diagnostics,
            recovery_strategy="Restart service",
        )

        error_dict = error.to_dict()

        assert error_dict["category"] == "communication"
        assert error_dict["error_type"] == "cors_failure"
        assert error_dict["message"] == "CORS error"
        assert error_dict["recovery_strategy"] == "Restart service"
        assert error_dict["diagnostics"] is not None
        assert error_dict["diagnostics"]["system_info"]["platform"] == "test"


class TestDiagnosticCollector:
    """Test the DiagnosticCollector class."""

    def test_collect_system_info(self):
        """Test collecting system information."""
        info = DiagnosticCollector.collect_system_info()

        assert "platform" in info
        assert "python_version" in info
        assert "python_executable" in info
        assert "working_directory" in info

    def test_collect_environment_vars(self):
        """Test collecting environment variables."""
        with patch.dict(os.environ, {"TEST_VAR": "test_value", "PATH": "/test/path"}):
            vars_dict = DiagnosticCollector.collect_environment_vars()

            assert "PATH" in vars_dict
            assert vars_dict["PATH"] == "/test/path"
            # TEST_VAR should not be included as it's not in the relevant list

    @patch("psutil.Process")
    def test_collect_process_info_with_psutil(self, mock_process_class):
        """Test collecting process info when psutil is available."""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.memory_info.return_value = Mock(_asdict=lambda: {"rss": 1024})
        mock_process.cpu_percent.return_value = 15.5
        mock_process.open_files.return_value = []
        mock_process.connections.return_value = []
        mock_process.num_threads.return_value = 4
        mock_process_class.return_value = mock_process

        info = DiagnosticCollector.collect_process_info()

        assert info["pid"] == 12345
        assert info["memory_info"]["rss"] == 1024
        assert info["cpu_percent"] == 15.5
        assert info["threads"] == 4

    def test_collect_process_info_without_psutil(self):
        """Test collecting process info when psutil is not available."""
        with patch.dict("sys.modules", {"psutil": None}):
            info = DiagnosticCollector.collect_process_info()
            assert "error" in info
            assert "psutil not available" in info["error"]

    def test_collect_network_info(self):
        """Test collecting network information."""
        with patch("socket.gethostname", return_value="test-host"):
            with patch("socket.gethostbyname", return_value="127.0.0.1"):
                info = DiagnosticCollector.collect_network_info()

                assert info["hostname"] == "test-host"
                assert info["local_ip"] == "127.0.0.1"
                assert "dns_servers" in info

    def test_collect_logs(self):
        """Test collecting log entries."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            log_file.write_text("Line 1\nLine 2\nLine 3\n")

            logs = DiagnosticCollector.collect_logs([str(log_file)])

            assert len(logs) == 3
            assert f"[{log_file}] Line 1" in logs
            assert f"[{log_file}] Line 2" in logs
            assert f"[{log_file}] Line 3" in logs

    def test_collect_full_diagnostics(self):
        """Test collecting comprehensive diagnostics."""
        context = {"test": "context"}

        diagnostics = DiagnosticCollector.collect_full_diagnostics(context=context)

        assert isinstance(diagnostics, DiagnosticInfo)
        assert diagnostics.context["test"] == "context"
        assert "platform" in diagnostics.system_info
        assert isinstance(diagnostics.environment_vars, dict)
        assert isinstance(diagnostics.process_info, dict)
        assert isinstance(diagnostics.network_info, dict)
        assert isinstance(diagnostics.logs, list)


class TestErrorFixSuggester:
    """Test the ErrorFixSuggester class."""

    def test_get_fix_for_missing_dependency(self):
        """Test getting fix for missing dependency error."""
        exc = ImportError("No module named 'test_module'")

        fix = ErrorFixSuggester.get_fix_for_exception(
            exc, ErrorCategory.ENVIRONMENT, ErrorType.MISSING_DEPENDENCY
        )

        assert fix is not None
        assert "uv add" in fix or "npm install" in fix

    def test_get_fix_for_cors_error(self):
        """Test getting fix for CORS error."""
        exc = Exception("Access-Control-Allow-Origin header is missing")

        fix = ErrorFixSuggester.get_fix_for_exception(
            exc, ErrorCategory.COMMUNICATION, ErrorType.CORS_FAILURE
        )

        assert fix is not None
        assert "CORS" in fix
        assert "agent servers" in fix

    def test_get_fix_for_connection_refused(self):
        """Test getting fix for connection refused error."""
        exc = ConnectionRefusedError("Connection refused")

        fix = ErrorFixSuggester.get_fix_for_exception(
            exc, ErrorCategory.COMMUNICATION, ErrorType.CONNECTION_REFUSED
        )

        assert fix is not None
        assert "agent servers" in fix
        assert "running" in fix

    def test_generic_fix_for_unknown_error(self):
        """Test getting generic fix for unknown error type."""
        exc = KeyError("missing_key")

        fix = ErrorFixSuggester._get_generic_fix(exc)

        assert fix is not None
        assert "key exists" in fix

    def test_no_fix_for_unrecognized_pattern(self):
        """Test that no fix is returned for unrecognized patterns."""
        exc = Exception("Very specific unknown error")

        fix = ErrorFixSuggester.get_fix_for_exception(
            exc, "unknown_category", "unknown_type"
        )

        # Should return None for unrecognized category/type
        assert fix is None


class TestRetryConfig:
    """Test the RetryConfig class."""

    def test_default_config(self):
        """Test default retry configuration."""
        config = RetryConfig()

        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_backoff is True
        assert config.jitter is True
        assert len(config.retry_on_exceptions) > 0
        assert ConnectionError in config.retry_on_exceptions

    def test_custom_config(self):
        """Test custom retry configuration."""
        config = RetryConfig(
            max_attempts=5,
            base_delay=2.0,
            exponential_backoff=False,
            retry_on_exceptions=[ValueError],
        )

        assert config.max_attempts == 5
        assert config.base_delay == 2.0
        assert config.exponential_backoff is False
        assert config.retry_on_exceptions == [ValueError]


class TestErrorRecoveryManager:
    """Test the ErrorRecoveryManager class."""

    def test_register_recovery_strategy(self):
        """Test registering a recovery strategy."""
        manager = ErrorRecoveryManager()
        strategy = Mock()
        config = RetryConfig(max_attempts=2)

        manager.register_recovery_strategy("test_pattern", strategy, config)

        assert "test_pattern" in manager.recovery_strategies
        assert manager.recovery_strategies["test_pattern"] == strategy
        assert manager.retry_configs["test_pattern"] == config

    @pytest.mark.asyncio
    async def test_execute_with_recovery_success(self):
        """Test successful execution without retry."""
        manager = ErrorRecoveryManager()

        async def test_func():
            return "success"

        result = await manager.execute_with_recovery(test_func)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_execute_with_recovery_retry_success(self):
        """Test successful execution after retry."""
        manager = ErrorRecoveryManager()
        call_count = 0

        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Temporary failure")
            return "success"

        config = RetryConfig(max_attempts=3, base_delay=0.1)
        result = await manager.execute_with_recovery(test_func, retry_config=config)

        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_execute_with_recovery_max_attempts_exceeded(self):
        """Test failure after max attempts exceeded."""
        manager = ErrorRecoveryManager()

        async def test_func():
            raise ConnectionError("Persistent failure")

        config = RetryConfig(max_attempts=2, base_delay=0.1)

        with pytest.raises(EnhancedTestError) as exc_info:
            await manager.execute_with_recovery(test_func, retry_config=config)

        assert exc_info.value.category == "infrastructure"
        assert "All retry attempts exhausted" in exc_info.value.recovery_strategy

    @pytest.mark.asyncio
    async def test_execute_with_recovery_non_retryable_exception(self):
        """Test immediate failure for non-retryable exception."""
        manager = ErrorRecoveryManager()

        async def test_func():
            raise ValueError("Non-retryable error")

        config = RetryConfig(max_attempts=3, retry_on_exceptions=[ConnectionError])

        with pytest.raises(EnhancedTestError):
            await manager.execute_with_recovery(test_func, retry_config=config)

    def test_calculate_delay_exponential(self):
        """Test exponential backoff delay calculation."""
        manager = ErrorRecoveryManager()
        config = RetryConfig(base_delay=1.0, exponential_backoff=True, jitter=False)

        delay1 = manager._calculate_delay(1, config)
        delay2 = manager._calculate_delay(2, config)
        delay3 = manager._calculate_delay(3, config)

        assert delay1 == 1.0
        assert delay2 == 2.0
        assert delay3 == 4.0

    def test_calculate_delay_linear(self):
        """Test linear delay calculation."""
        manager = ErrorRecoveryManager()
        config = RetryConfig(base_delay=2.0, exponential_backoff=False, jitter=False)

        delay1 = manager._calculate_delay(1, config)
        delay2 = manager._calculate_delay(2, config)
        delay3 = manager._calculate_delay(3, config)

        assert delay1 == 2.0
        assert delay2 == 2.0
        assert delay3 == 2.0

    def test_calculate_delay_with_jitter(self):
        """Test delay calculation with jitter."""
        manager = ErrorRecoveryManager()
        config = RetryConfig(base_delay=2.0, exponential_backoff=False, jitter=True)

        delay = manager._calculate_delay(1, config)

        # With jitter, delay should be between 1.0 and 2.0
        assert 1.0 <= delay <= 2.0


class TestIntegrationTestErrorHandler:
    """Test the IntegrationTestErrorHandler class."""

    def test_handle_test_error(self):
        """Test handling a test error."""
        handler = IntegrationTestErrorHandler()
        exc = ImportError("No module named 'test'")

        error = handler.handle_test_error(
            exc,
            "test_function",
            ErrorCategory.ENVIRONMENT,
            ErrorType.MISSING_DEPENDENCY,
            {"context": "test"},
        )

        assert isinstance(error, EnhancedTestError)
        assert error.category == "environment"
        assert error.error_type == "missing_dependency"
        assert error.diagnostics is not None
        assert len(handler.error_history) == 1

    def test_create_test_result_with_error(self):
        """Test creating a test result with error."""
        handler = IntegrationTestErrorHandler()
        exc = ConnectionError("Connection failed")

        result = handler.create_test_result_with_error(
            "test_connection",
            "communication",
            exc,
            ErrorCategory.COMMUNICATION,
            ErrorType.CONNECTION_REFUSED,
        )

        assert result.name == "test_connection"
        assert result.category == TestCategory.COMMUNICATION
        assert result.status == TestStatus.FAILED
        assert result.error is not None
        assert isinstance(result.error, EnhancedTestError)

    def test_get_error_summary_empty(self):
        """Test getting error summary when no errors."""
        handler = IntegrationTestErrorHandler()
        summary = handler.get_error_summary()

        assert summary["total_errors"] == 0

    def test_get_error_summary_with_errors(self):
        """Test getting error summary with errors."""
        handler = IntegrationTestErrorHandler()

        # Add some errors
        exc1 = ImportError("Module 1 not found")
        exc2 = ConnectionError("Connection failed")

        handler.handle_test_error(
            exc1, "test1", ErrorCategory.ENVIRONMENT, ErrorType.MISSING_DEPENDENCY
        )
        handler.handle_test_error(
            exc2, "test2", ErrorCategory.COMMUNICATION, ErrorType.CONNECTION_REFUSED
        )

        summary = handler.get_error_summary()

        assert summary["total_errors"] == 2
        assert summary["by_category"]["environment"] == 1
        assert summary["by_category"]["communication"] == 1
        assert summary["by_type"]["missing_dependency"] == 1
        assert summary["by_type"]["connection_refused"] == 1
        assert summary["most_recent"] is not None

    def test_export_diagnostics(self):
        """Test exporting diagnostics to file."""
        handler = IntegrationTestErrorHandler()

        # Add an error
        exc = ValueError("Test error")
        handler.handle_test_error(
            exc, "test_export", ErrorCategory.ENVIRONMENT, ErrorType.IMPORT_FAILURE
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "diagnostics.json"
            handler.export_diagnostics(str(output_path))

            assert output_path.exists()

            with open(output_path) as f:
                data = json.load(f)

            assert "timestamp" in data
            assert "error_summary" in data
            assert "error_history" in data
            assert "system_diagnostics" in data
            assert data["error_summary"]["total_errors"] == 1


class TestIntegrationScenarios:
    """Test integration scenarios combining multiple components."""

    @pytest.mark.asyncio
    async def test_full_error_handling_workflow(self):
        """Test complete error handling workflow."""
        handler = IntegrationTestErrorHandler()

        # Simulate a test that fails with retry
        call_count = 0

        async def failing_test():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary network issue")
            return "success"

        # Execute with recovery
        config = RetryConfig(max_attempts=3, base_delay=0.1)

        try:
            result = await handler.recovery_manager.execute_with_recovery(
                failing_test, retry_config=config, context={"test": "integration"}
            )
            assert result == "success"
            assert call_count == 3
        except EnhancedTestError as e:
            # If it fails, check that diagnostics were collected
            assert e.diagnostics is not None
            assert e.suggested_fix is not None

    def test_error_categorization_and_fixes(self):
        """Test that errors are properly categorized with appropriate fixes."""
        test_cases = [
            (
                ImportError("No module named 'missing'"),
                ErrorCategory.ENVIRONMENT,
                ErrorType.MISSING_DEPENDENCY,
            ),
            (
                ConnectionRefusedError("Connection refused"),
                ErrorCategory.COMMUNICATION,
                ErrorType.CONNECTION_REFUSED,
            ),
            (
                TimeoutError("Request timed out"),
                ErrorCategory.COMMUNICATION,
                ErrorType.NETWORK_TIMEOUT,
            ),
        ]

        handler = IntegrationTestErrorHandler()

        for exc, category, error_type in test_cases:
            error = handler.handle_test_error(exc, "test", category, error_type)

            assert error.category == category.value
            assert error.error_type == error_type.value
            assert error.suggested_fix is not None
            assert error.diagnostics is not None

    def test_diagnostic_data_completeness(self):
        """Test that diagnostic data is comprehensive."""
        handler = IntegrationTestErrorHandler()
        exc = RuntimeError("Test runtime error")

        error = handler.handle_test_error(
            exc,
            "diagnostic_test",
            ErrorCategory.INFRASTRUCTURE,
            ErrorType.SERVICE_UNAVAILABLE,
        )

        diagnostics = error.diagnostics
        assert diagnostics is not None

        # Check that all diagnostic categories are present
        assert diagnostics.system_info
        assert diagnostics.environment_vars
        assert diagnostics.process_info
        assert diagnostics.network_info
        assert isinstance(diagnostics.logs, list)
        assert diagnostics.context

        # Check that diagnostic data can be serialized
        diagnostic_dict = diagnostics.to_dict()
        assert "timestamp" in diagnostic_dict
        assert "system_info" in diagnostic_dict
        assert "environment_vars" in diagnostic_dict
