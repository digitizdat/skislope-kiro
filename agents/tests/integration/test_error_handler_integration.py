"""
Integration tests for error handling with existing test infrastructure.

Tests that the error handling system integrates properly with the
existing integration testing components.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch

from .error_handler import (
    ErrorCategory,
    ErrorType,
    IntegrationTestErrorHandler,
    EnhancedTestError
)
from .models import TestCategory, TestResult, TestStatus
from .test_orchestrator import IntegrationTestOrchestrator


class TestErrorHandlerIntegration:
    """Test integration of error handler with test orchestrator."""
    
    def test_error_handler_with_test_result(self):
        """Test that error handler creates proper test results."""
        handler = IntegrationTestErrorHandler()
        
        # Simulate a test failure
        exc = ConnectionError("Agent connection failed")
        
        result = handler.create_test_result_with_error(
            "test_agent_connection",
            "communication",
            exc,
            ErrorCategory.COMMUNICATION,
            ErrorType.CONNECTION_REFUSED,
            {"agent": "hill_metrics", "port": 8001}
        )
        
        # Verify the result structure
        assert result.name == "test_agent_connection"
        assert result.category == TestCategory.COMMUNICATION
        assert result.status == TestStatus.FAILED
        assert result.error is not None
        assert isinstance(result.error, EnhancedTestError)
        
        # Verify error details
        assert result.error.category == "communication"
        assert result.error.error_type == "connection_refused"
        assert result.error.diagnostics is not None
        assert result.error.suggested_fix is not None
    
    def test_error_handler_diagnostics_collection(self):
        """Test that diagnostics are properly collected."""
        handler = IntegrationTestErrorHandler()
        
        exc = ImportError("No module named 'test_module'")
        context = {
            "test_name": "import_test",
            "module": "test_module",
            "expected_location": "/path/to/module"
        }
        
        error = handler.handle_test_error(
            exc,
            "import_test",
            ErrorCategory.ENVIRONMENT,
            ErrorType.MISSING_DEPENDENCY,
            context
        )
        
        # Verify diagnostics were collected
        assert error.diagnostics is not None
        assert error.diagnostics.system_info
        assert error.diagnostics.environment_vars
        assert error.diagnostics.context["test_name"] == "import_test"
        assert error.diagnostics.context["module"] == "test_module"
    
    def test_error_summary_generation(self):
        """Test error summary generation with multiple errors."""
        handler = IntegrationTestErrorHandler()
        
        # Add multiple errors of different types
        errors = [
            (ImportError("Missing module 1"), ErrorCategory.ENVIRONMENT, ErrorType.MISSING_DEPENDENCY),
            (ImportError("Missing module 2"), ErrorCategory.ENVIRONMENT, ErrorType.MISSING_DEPENDENCY),
            (ConnectionError("Connection 1 failed"), ErrorCategory.COMMUNICATION, ErrorType.CONNECTION_REFUSED),
            (TimeoutError("Request timed out"), ErrorCategory.COMMUNICATION, ErrorType.NETWORK_TIMEOUT),
        ]
        
        for i, (exc, category, error_type) in enumerate(errors):
            handler.handle_test_error(exc, f"test_{i}", category, error_type)
        
        summary = handler.get_error_summary()
        
        # Verify summary statistics
        assert summary["total_errors"] == 4
        assert summary["by_category"]["environment"] == 2
        assert summary["by_category"]["communication"] == 2
        assert summary["by_type"]["missing_dependency"] == 2
        assert summary["by_type"]["connection_refused"] == 1
        assert summary["by_type"]["network_timeout"] == 1
    
    @pytest.mark.asyncio
    async def test_error_recovery_integration(self):
        """Test error recovery integration with async operations."""
        handler = IntegrationTestErrorHandler()
        
        # Set up a recovery strategy
        recovery_called = False
        
        async def mock_recovery(exc, context):
            nonlocal recovery_called
            recovery_called = True
            # Simulate successful recovery
            pass
        
        handler.recovery_manager.register_recovery_strategy(
            "connection refused",
            mock_recovery
        )
        
        # Test function that fails then succeeds
        call_count = 0
        
        async def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Connection refused")
            return "success"
        
        # Execute with recovery
        result = await handler.recovery_manager.execute_with_recovery(
            test_function,
            context={"test": "recovery_integration"}
        )
        
        assert result == "success"
        assert call_count == 2
        assert recovery_called
    
    def test_error_serialization(self):
        """Test that errors can be properly serialized."""
        handler = IntegrationTestErrorHandler()
        
        exc = ValueError("Test validation error")
        error = handler.handle_test_error(
            exc,
            "serialization_test",
            ErrorCategory.DATA,
            ErrorType.SERIALIZATION_ERROR,
            {"data_type": "json", "field": "test_field"}
        )
        
        # Test serialization
        error_dict = error.to_dict()
        
        # Verify all fields are present and serializable
        assert error_dict["category"] == "data"
        assert error_dict["error_type"] == "serialization_error"
        assert error_dict["message"] == "Test validation error"
        assert error_dict["context"]["data_type"] == "json"
        assert error_dict["diagnostics"] is not None
        assert isinstance(error_dict["diagnostics"], dict)
        
        # Verify diagnostics are serializable
        diagnostics = error_dict["diagnostics"]
        assert "timestamp" in diagnostics
        assert "system_info" in diagnostics
        assert "environment_vars" in diagnostics
    
    def test_error_fix_suggestions(self):
        """Test that appropriate fix suggestions are generated."""
        handler = IntegrationTestErrorHandler()
        
        test_cases = [
            (
                ImportError("No module named 'rasterio'"),
                ErrorCategory.ENVIRONMENT,
                ErrorType.MISSING_DEPENDENCY,
                "uv add"
            ),
            (
                ConnectionRefusedError("Connection refused"),
                ErrorCategory.COMMUNICATION,
                ErrorType.CONNECTION_REFUSED,
                "agent servers"
            ),
            (
                AttributeError("'dict' object has no attribute 'get_data'"),
                ErrorCategory.API_CONTRACT,
                ErrorType.METHOD_NOT_FOUND,
                "attribute"
            )
        ]
        
        for exc, category, error_type, expected_fix_keyword in test_cases:
            error = handler.handle_test_error(
                exc, "fix_suggestion_test", category, error_type
            )
            
            assert error.suggested_fix is not None
            assert expected_fix_keyword.lower() in error.suggested_fix.lower()


class TestErrorHandlerWithMockOrchestrator:
    """Test error handler integration with mocked orchestrator."""
    
    @patch('agents.tests.integration.test_orchestrator.IntegrationTestOrchestrator')
    def test_orchestrator_error_handling_integration(self, mock_orchestrator_class):
        """Test that orchestrator can use error handler."""
        # Create mock orchestrator instance
        mock_orchestrator = Mock()
        mock_orchestrator_class.return_value = mock_orchestrator
        
        # Create error handler
        error_handler = IntegrationTestErrorHandler()
        
        # Simulate orchestrator using error handler
        exc = RuntimeError("Test orchestrator error")
        result = error_handler.create_test_result_with_error(
            "orchestrator_test",
            "infrastructure",
            exc,
            ErrorCategory.INFRASTRUCTURE,
            ErrorType.SERVICE_UNAVAILABLE
        )
        
        # Verify the result can be used by orchestrator
        assert result.name == "orchestrator_test"
        assert result.status == TestStatus.FAILED
        assert result.error is not None
        
        # Verify error has comprehensive information
        error = result.error
        assert error.category == "infrastructure"
        assert error.diagnostics is not None
        # Note: suggested_fix might be None for generic RuntimeError, which is acceptable
    
    def test_multiple_error_aggregation(self):
        """Test aggregating multiple errors from different test categories."""
        handler = IntegrationTestErrorHandler()
        
        # Simulate errors from different test categories
        test_errors = [
            ("api_test_1", TestCategory.API_CONTRACTS, ImportError("Missing API module")),
            ("comm_test_1", TestCategory.COMMUNICATION, ConnectionError("CORS failure")),
            ("env_test_1", TestCategory.ENVIRONMENT, OSError("Permission denied")),
            ("workflow_test_1", TestCategory.WORKFLOWS, TimeoutError("Workflow timeout")),
        ]
        
        results = []
        for test_name, category, exc in test_errors:
            # Map test category to error category
            error_category_map = {
                TestCategory.API_CONTRACTS: ErrorCategory.API_CONTRACT,
                TestCategory.COMMUNICATION: ErrorCategory.COMMUNICATION,
                TestCategory.ENVIRONMENT: ErrorCategory.ENVIRONMENT,
                TestCategory.WORKFLOWS: ErrorCategory.WORKFLOW,
            }
            
            error_type_map = {
                ImportError: ErrorType.MISSING_DEPENDENCY,
                ConnectionError: ErrorType.CONNECTION_REFUSED,
                OSError: ErrorType.PERMISSION_DENIED,
                TimeoutError: ErrorType.NETWORK_TIMEOUT,
            }
            
            result = handler.create_test_result_with_error(
                test_name,
                category.value,
                exc,
                error_category_map[category],
                error_type_map[type(exc)]
            )
            results.append(result)
        
        # Verify all results have proper error information
        assert len(results) == 4
        for result in results:
            assert result.status == TestStatus.FAILED
            assert result.error is not None
            assert result.error.diagnostics is not None
        
        # Verify error summary
        summary = handler.get_error_summary()
        assert summary["total_errors"] == 4
        assert len(summary["by_category"]) == 4  # All different categories
        assert len(summary["by_type"]) == 4      # All different types