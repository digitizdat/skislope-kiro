"""
Tests for core testing infrastructure components.

Validates the configuration system, data models, and logging utilities
to ensure the integration testing foundation is working correctly.
"""

import json
import os
import tempfile
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from .config import ConfigManager, TestConfig, TestEnvironment, get_test_config
from .models import (
    TestResult, TestStatus, TestCategory, TestError, Severity,
    AgentHealthStatus, PerformanceMetrics, TestResults
)
from .logging_utils import TestLogger, DiagnosticCollector, TestArtifactManager, integration_test_context


class TestConfigManager:
    """Test configuration management."""
    
    def test_environment_detection_local(self):
        """Test local environment detection."""
        with patch.dict(os.environ, {}, clear=True):
            config_manager = ConfigManager()
            assert config_manager.environment == TestEnvironment.LOCAL
            assert config_manager.is_local()
            assert not config_manager.is_ci()
            assert not config_manager.is_production()
    
    def test_environment_detection_ci(self):
        """Test CI environment detection."""
        with patch.dict(os.environ, {"CI": "true"}, clear=True):
            config_manager = ConfigManager()
            assert config_manager.environment == TestEnvironment.CI
            assert config_manager.is_ci()
            assert not config_manager.is_local()
            assert not config_manager.is_production()
    
    def test_environment_detection_production(self):
        """Test production environment detection."""
        with patch.dict(os.environ, {"NODE_ENV": "production"}, clear=True):
            config_manager = ConfigManager()
            assert config_manager.environment == TestEnvironment.PRODUCTION
            assert config_manager.is_production()
            assert not config_manager.is_local()
            assert not config_manager.is_ci()
    
    def test_config_creation(self):
        """Test configuration creation with defaults."""
        config = get_test_config()
        
        assert isinstance(config, TestConfig)
        assert len(config.agents) == 3
        assert "hill_metrics" in config.agents
        assert "weather" in config.agents
        assert "equipment" in config.agents
        
        # Check agent configurations
        hill_metrics = config.agents["hill_metrics"]
        assert hill_metrics.name == "hill_metrics"
        assert hill_metrics.port == 8001
        assert "get_terrain_data" in hill_metrics.required_methods
    
    def test_config_overrides(self):
        """Test configuration overrides."""
        overrides = {
            "max_workers": 8,
            "timeouts.agent_startup": 60
        }
        
        config = get_test_config(overrides)
        assert config.max_workers == 8
        assert config.timeouts.agent_startup == 60
    
    def test_directory_setup(self):
        """Test directory setup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            overrides = {
                "env_config.temp_dir": Path(temp_dir) / "test_temp",
                "env_config.log_dir": Path(temp_dir) / "test_logs"
            }
            
            config = get_test_config(overrides)
            
            assert config.env_config.temp_dir.exists()
            assert config.env_config.log_dir.exists()


class TestDataModels:
    """Test data models and interfaces."""
    
    def test_test_error_creation(self):
        """Test TestError creation."""
        error = TestError(
            category="test_category",
            severity=Severity.HIGH,
            message="Test error message",
            context={"key": "value"},
            suggested_fix="Try this fix"
        )
        
        assert error.category == "test_category"
        assert error.severity == Severity.HIGH
        assert error.message == "Test error message"
        assert error.context["key"] == "value"
        assert error.suggested_fix == "Try this fix"
        assert isinstance(error.timestamp, datetime)
    
    def test_test_error_from_exception(self):
        """Test TestError creation from exception."""
        try:
            raise ValueError("Test exception")
        except ValueError as e:
            error = TestError.from_exception(e, "test_category")
            
            assert error.category == "test_category"
            assert error.severity == Severity.HIGH
            assert "Test exception" in error.message
            assert error.context["exception_type"] == "ValueError"
            assert error.stack_trace is not None
    
    def test_agent_health_status(self):
        """Test AgentHealthStatus model."""
        status = AgentHealthStatus(
            name="test_agent",
            status="healthy",
            response_time=0.5,
            available_methods=["method1", "method2"],
            endpoint="http://localhost:8001"
        )
        
        assert status.name == "test_agent"
        assert status.is_healthy
        assert status.is_available
        assert len(status.available_methods) == 2
        
        # Test degraded status
        status.status = "degraded"
        assert not status.is_healthy
        assert status.is_available
        
        # Test failed status
        status.status = "failed"
        assert not status.is_healthy
        assert not status.is_available
    
    def test_performance_metrics(self):
        """Test PerformanceMetrics model."""
        metrics = PerformanceMetrics(
            total_duration=10.0,
            setup_duration=2.0,
            execution_duration=6.0,
            teardown_duration=2.0,
            network_requests=100
        )
        
        assert metrics.total_duration == 10.0
        assert metrics.requests_per_second == 100 / 6.0
        
        # Test zero execution duration
        metrics.execution_duration = 0.0
        assert metrics.requests_per_second == 0.0
    
    def test_test_result_lifecycle(self):
        """Test TestResult lifecycle methods."""
        result = TestResult(
            name="test_example",
            category=TestCategory.API_CONTRACTS,
            status=TestStatus.NOT_STARTED,
            duration=0.0
        )
        
        # Test passing
        result.mark_passed("Test passed successfully")
        assert result.status == TestStatus.PASSED
        assert result.message == "Test passed successfully"
        assert result.end_time is not None
        assert result.duration > 0
        
        # Reset for failure test
        result = TestResult(
            name="test_example",
            category=TestCategory.API_CONTRACTS,
            status=TestStatus.NOT_STARTED,
            duration=0.0
        )
        
        # Test failing with exception
        try:
            raise RuntimeError("Test failure")
        except RuntimeError as e:
            result.mark_failed(e, "Test failed")
            
        assert result.status == TestStatus.FAILED
        assert result.message == "Test failed"
        assert result.error is not None
        assert result.error.category == TestCategory.API_CONTRACTS.value
        
        # Test skipping
        result = TestResult(
            name="test_example",
            category=TestCategory.API_CONTRACTS,
            status=TestStatus.NOT_STARTED,
            duration=0.0
        )
        
        result.mark_skipped("Test skipped due to missing dependency")
        assert result.status == TestStatus.SKIPPED
        assert "missing dependency" in result.message
    
    def test_test_results_aggregation(self):
        """Test TestResults aggregation."""
        results = TestResults()
        
        # Add some test results
        result1 = TestResult("test1", TestCategory.API_CONTRACTS, TestStatus.PASSED, 1.0)
        result1.mark_passed()
        
        result2 = TestResult("test2", TestCategory.API_CONTRACTS, TestStatus.FAILED, 2.0)
        result2.mark_failed("Test failed")
        
        result3 = TestResult("test3", TestCategory.COMMUNICATION, TestStatus.PASSED, 1.5)
        result3.mark_passed()
        
        results.add_result(result1)
        results.add_result(result2)
        results.add_result(result3)
        
        # Check summary
        assert results.summary.total_tests == 3
        assert results.summary.passed == 2
        assert results.summary.failed == 1
        assert results.summary.success_rate == (2/3) * 100
        
        # Check categories
        assert len(results.categories) == 2
        assert TestCategory.API_CONTRACTS in results.categories
        assert TestCategory.COMMUNICATION in results.categories
        
        api_category = results.categories[TestCategory.API_CONTRACTS]
        assert api_category.total_tests == 2
        assert api_category.passed == 1
        assert api_category.failed == 1
        
        # Check failed tests
        failed_tests = results.get_failed_tests()
        assert len(failed_tests) == 1
        assert failed_tests[0].name == "test2"
    
    def test_serialization(self):
        """Test model serialization to dict."""
        result = TestResult("test1", TestCategory.API_CONTRACTS, TestStatus.PASSED, 1.0)
        result.mark_passed("Success")
        
        result_dict = result.to_dict()
        assert result_dict["name"] == "test1"
        assert result_dict["category"] == "api_contracts"
        assert result_dict["status"] == "passed"
        assert result_dict["message"] == "Success"
        
        # Test full results serialization
        results = TestResults()
        results.add_result(result)
        results.finalize()
        
        results_dict = results.to_dict()
        assert "summary" in results_dict
        assert "categories" in results_dict
        assert results_dict["summary"]["total_tests"] == 1


class TestLoggingUtils:
    """Test logging and diagnostic utilities."""
    
    def test_test_logger_creation(self):
        """Test TestLogger creation and configuration."""
        config = get_test_config()
        logger = TestLogger("test_logger", config)
        
        assert logger.name == "test_logger"
        assert logger.config == config
        assert len(logger.logger.handlers) >= 1  # At least console handler
    
    def test_logger_context(self):
        """Test logger context management."""
        config = get_test_config()
        logger = TestLogger("test_logger", config)
        
        logger.set_context(test_id="123", component="test")
        assert logger.context["test_id"] == "123"
        assert logger.context["component"] == "test"
        
        logger.clear_context()
        assert len(logger.context) == 0
    
    def test_diagnostic_collector(self):
        """Test diagnostic collection."""
        config = get_test_config()
        collector = DiagnosticCollector(config)
        
        # Test system info collection
        system_info = collector.collect_system_info()
        assert "platform" in system_info
        assert "python_version" in system_info
        assert "memory" in system_info
        assert "cpu" in system_info
        
        # Test environment info collection
        env_info = collector.collect_environment_info()
        assert "environment_variables" in env_info
        assert "working_directory" in env_info
        assert "python_path" in env_info
        
        # Test full diagnostic collection
        diagnostics = collector.collect_all_diagnostics()
        assert "collection_time" in diagnostics
        assert "test_config" in diagnostics
        assert "system" in diagnostics
        assert "environment" in diagnostics
    
    def test_artifact_manager(self):
        """Test artifact management."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = get_test_config({
                "env_config.temp_dir": Path(temp_dir)
            })
            
            manager = TestArtifactManager(config)
            
            # Test saving text artifact
            content = "Test artifact content"
            filepath = manager.save_test_output(content, "test_output.txt")
            
            assert filepath.exists()
            assert filepath.read_text() == content
            assert filepath in manager.artifacts
            
            # Test saving JSON artifact
            data = {"key": "value", "number": 42}
            json_filepath = manager.save_json_artifact(data, "test_data.json")
            
            assert json_filepath.exists()
            loaded_data = json.loads(json_filepath.read_text())
            assert loaded_data == data
            assert json_filepath in manager.artifacts
    
    def test_context_manager(self):
        """Test test context manager."""
        config = get_test_config()
        
        with integration_test_context("test_context", config, test_id="123") as logger:
            assert isinstance(logger, TestLogger)
            assert logger.context["test_id"] == "123"
            
            # Test logging within context
            logger.info("Test message")
            logger.debug("Debug message", extra_data="value")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])