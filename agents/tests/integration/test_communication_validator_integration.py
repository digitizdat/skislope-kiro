"""
Integration tests for CommunicationValidator.

These tests focus on the core functionality and integration with the test framework
without complex HTTP mocking.
"""

import pytest
from unittest.mock import AsyncMock, patch

from agents.tests.integration.communication_validator import (
    CommunicationValidator,
    CORSTestResult,
    JSONRPCTestResult,
    MCPTestResult,
    NetworkTestResult,
    CommunicationValidationResult
)
from agents.tests.integration.config import TestConfig, AgentConfig
from agents.tests.integration.models import TestCategory, TestStatus, Severity


class TestCommunicationValidatorIntegration:
    """Integration test cases for CommunicationValidator."""
    
    @pytest.fixture
    def test_config(self):
        """Create test configuration."""
        config = TestConfig()
        config.agents = {
            "test_agent": AgentConfig(
                name="test_agent",
                host="localhost",
                port=8001,
                enabled=True
            )
        }
        return config
    
    @pytest.fixture
    def validator(self, test_config):
        """Create CommunicationValidator instance."""
        return CommunicationValidator(test_config)
    
    def test_validator_initialization(self, validator):
        """Test validator initialization."""
        assert validator.config is not None
        assert validator.session is None
        assert len(validator.expected_origins) > 0
        assert len(validator.jsonrpc_error_codes) > 0
        
        # Check expected origins include common development URLs
        assert "http://localhost:3000" in validator.expected_origins
        assert "http://localhost:5173" in validator.expected_origins
        
        # Check JSON-RPC error codes
        assert -32700 in validator.jsonrpc_error_codes  # Parse error
        assert -32601 in validator.jsonrpc_error_codes  # Method not found
    
    def test_cors_test_result_serialization(self):
        """Test CORSTestResult serialization."""
        result = CORSTestResult(
            agent_name="test_agent",
            endpoint="http://localhost:8001/jsonrpc",
            allowed_origins=["http://localhost:3000"],
            allowed_methods=["POST", "OPTIONS"],
            allowed_headers=["Content-Type"],
            supports_credentials=True,
            preflight_successful=True,
            is_valid=True
        )
        
        data = result.to_dict()
        assert data["agent_name"] == "test_agent"
        assert data["endpoint"] == "http://localhost:8001/jsonrpc"
        assert data["allowed_origins"] == ["http://localhost:3000"]
        assert data["allowed_methods"] == ["POST", "OPTIONS"]
        assert data["allowed_headers"] == ["Content-Type"]
        assert data["supports_credentials"] is True
        assert data["preflight_successful"] is True
        assert data["is_valid"] is True
    
    def test_jsonrpc_test_result_serialization(self):
        """Test JSONRPCTestResult serialization."""
        result = JSONRPCTestResult(
            agent_name="test_agent",
            endpoint="http://localhost:8001/jsonrpc",
            protocol_version="2.0",
            supported_methods=["healthCheck", "getStatus"],
            request_response_valid=True,
            error_handling_valid=True,
            batch_requests_supported=False,
            notification_handling_valid=True,
            is_valid=True
        )
        
        data = result.to_dict()
        assert data["agent_name"] == "test_agent"
        assert data["protocol_version"] == "2.0"
        assert data["supported_methods"] == ["healthCheck", "getStatus"]
        assert data["request_response_valid"] is True
        assert data["error_handling_valid"] is True
        assert data["batch_requests_supported"] is False
        assert data["notification_handling_valid"] is True
        assert data["is_valid"] is True
    
    def test_mcp_test_result_serialization(self):
        """Test MCPTestResult serialization."""
        result = MCPTestResult(
            agent_name="test_agent",
            endpoint="http://localhost:8001/mcp",
            mcp_supported=True,
            protocol_version="1.0",
            available_tools=["terrain_analysis", "weather_forecast"],
            tool_discovery_valid=True,
            tool_execution_valid=True,
            is_valid=True
        )
        
        data = result.to_dict()
        assert data["agent_name"] == "test_agent"
        assert data["mcp_supported"] is True
        assert data["protocol_version"] == "1.0"
        assert data["available_tools"] == ["terrain_analysis", "weather_forecast"]
        assert data["tool_discovery_valid"] is True
        assert data["tool_execution_valid"] is True
        assert data["is_valid"] is True
    
    def test_network_test_result_serialization(self):
        """Test NetworkTestResult serialization."""
        result = NetworkTestResult(
            agent_name="test_agent",
            endpoint="http://localhost:8001/jsonrpc",
            timeout_handling_valid=True,
            retry_mechanism_valid=True,
            connection_pooling_valid=True,
            large_payload_handling=True,
            concurrent_request_handling=True,
            performance_metrics={
                "response_time": 0.1,
                "retry_success_rate": 0.9,
                "concurrent_success_rate": 0.95
            },
            is_valid=True
        )
        
        data = result.to_dict()
        assert data["agent_name"] == "test_agent"
        assert data["timeout_handling_valid"] is True
        assert data["retry_mechanism_valid"] is True
        assert data["connection_pooling_valid"] is True
        assert data["large_payload_handling"] is True
        assert data["concurrent_request_handling"] is True
        assert data["performance_metrics"]["response_time"] == 0.1
        assert data["performance_metrics"]["retry_success_rate"] == 0.9
        assert data["performance_metrics"]["concurrent_success_rate"] == 0.95
        assert data["is_valid"] is True
    
    def test_communication_validation_result_serialization(self):
        """Test CommunicationValidationResult serialization."""
        cors_result = CORSTestResult(
            agent_name="test_agent",
            endpoint="http://localhost:8001/jsonrpc",
            is_valid=True
        )
        
        jsonrpc_result = JSONRPCTestResult(
            agent_name="test_agent",
            endpoint="http://localhost:8001/jsonrpc",
            is_valid=True
        )
        
        result = CommunicationValidationResult(
            agent_name="test_agent",
            cors_result=cors_result,
            jsonrpc_result=jsonrpc_result,
            overall_valid=True
        )
        
        data = result.to_dict()
        assert data["agent_name"] == "test_agent"
        assert data["cors_result"] is not None
        assert data["jsonrpc_result"] is not None
        assert data["mcp_result"] is None
        assert data["network_result"] is None
        assert data["overall_valid"] is True
        assert data["validation_errors"] == []
    
    def test_jsonrpc_response_validation_edge_cases(self, validator):
        """Test JSON-RPC response validation edge cases."""
        # Valid response with null result
        valid_null_result = {
            "jsonrpc": "2.0",
            "result": None,
            "id": 1
        }
        assert validator._validate_jsonrpc_response(valid_null_result, 1)
        
        # Valid error response
        valid_error = {
            "jsonrpc": "2.0",
            "error": {"code": -32601, "message": "Method not found"},
            "id": 1
        }
        assert validator._validate_jsonrpc_response(valid_error, 1)
        
        # Invalid: missing jsonrpc
        invalid_missing_jsonrpc = {
            "result": "ok",
            "id": 1
        }
        assert not validator._validate_jsonrpc_response(invalid_missing_jsonrpc, 1)
        
        # Invalid: wrong jsonrpc version
        invalid_version = {
            "jsonrpc": "1.0",
            "result": "ok",
            "id": 1
        }
        assert not validator._validate_jsonrpc_response(invalid_version, 1)
        
        # Invalid: both result and error
        invalid_both = {
            "jsonrpc": "2.0",
            "result": "ok",
            "error": {"code": -32000, "message": "Error"},
            "id": 1
        }
        assert not validator._validate_jsonrpc_response(invalid_both, 1)
        
        # Invalid: neither result nor error
        invalid_neither = {
            "jsonrpc": "2.0",
            "id": 1
        }
        assert not validator._validate_jsonrpc_response(invalid_neither, 1)
        
        # Invalid: wrong id
        invalid_id = {
            "jsonrpc": "2.0",
            "result": "ok",
            "id": 2
        }
        assert not validator._validate_jsonrpc_response(invalid_id, 1)
    
    def test_jsonrpc_error_validation_edge_cases(self, validator):
        """Test JSON-RPC error validation edge cases."""
        # Valid error with data field
        valid_error_with_data = {
            "jsonrpc": "2.0",
            "error": {
                "code": -32602,
                "message": "Invalid params",
                "data": {"param": "value"}
            },
            "id": 1
        }
        assert validator._validate_jsonrpc_error(valid_error_with_data, -32602)
        
        # Invalid: wrong error code
        invalid_code = {
            "jsonrpc": "2.0",
            "error": {
                "code": -32600,
                "message": "Invalid Request"
            },
            "id": 1
        }
        assert not validator._validate_jsonrpc_error(invalid_code, -32601)
        
        # Invalid: missing message
        invalid_no_message = {
            "jsonrpc": "2.0",
            "error": {
                "code": -32601
            },
            "id": 1
        }
        assert not validator._validate_jsonrpc_error(invalid_no_message, -32601)
        
        # Invalid: message not string
        invalid_message_type = {
            "jsonrpc": "2.0",
            "error": {
                "code": -32601,
                "message": 123
            },
            "id": 1
        }
        assert not validator._validate_jsonrpc_error(invalid_message_type, -32601)
        
        # Invalid: error not dict
        invalid_error_type = {
            "jsonrpc": "2.0",
            "error": "Method not found",
            "id": 1
        }
        assert not validator._validate_jsonrpc_error(invalid_error_type, -32601)
    
    @pytest.mark.asyncio
    async def test_context_manager_lifecycle(self, validator):
        """Test async context manager lifecycle."""
        assert validator.session is None
        
        async with validator as v:
            assert v is validator
            assert v.session is not None
            # Session should have proper timeout configuration
            assert v.session.timeout.total == validator.config.timeouts.network_request
        
        # After context exit, session should be closed
        # Note: We can't easily test if close() was called without mocking
    
    @pytest.mark.asyncio
    async def test_validate_all_communication_disabled_agents(self, validator):
        """Test that disabled agents are skipped."""
        # Add disabled agent to config
        validator.config.agents["disabled_agent"] = AgentConfig(
            name="disabled_agent",
            port=8999,
            enabled=False
        )
        
        with patch.object(validator, 'validate_agent_communication') as mock_validate:
            mock_validate.return_value = CommunicationValidationResult(
                agent_name="test_agent",
                overall_valid=True
            )
            
            results = await validator.validate_all_communication()
        
        # Should only validate enabled agents
        assert len(results) == 1
        assert results[0].agent_name == "test_agent"
        
        # Verify only enabled agent was validated
        mock_validate.assert_called_once_with("test_agent", validator.config.agents["test_agent"])
    
    @pytest.mark.asyncio
    async def test_validate_all_communication_exception_handling(self, validator):
        """Test exception handling in validate_all_communication."""
        with patch.object(validator, 'validate_agent_communication') as mock_validate:
            mock_validate.side_effect = Exception("Network error")
            
            results = await validator.validate_all_communication()
        
        # Should return failed result for the agent
        assert len(results) == 1
        assert results[0].agent_name == "test_agent"
        assert not results[0].overall_valid
        assert len(results[0].validation_errors) > 0
        assert "Communication validation failed" in results[0].validation_errors[0]
    
    @pytest.mark.asyncio
    async def test_run_communication_tests_exception_handling(self, validator):
        """Test exception handling in run_communication_tests."""
        with patch.object(validator, 'validate_all_communication') as mock_validate:
            mock_validate.side_effect = Exception("Validation error")
            
            test_results = await validator.run_communication_tests()
        
        # Should return failed test result
        assert len(test_results) == 1
        assert test_results[0].name == "Communication Validation - Overall"
        assert test_results[0].category == TestCategory.COMMUNICATION
        assert test_results[0].status == TestStatus.FAILED
        assert test_results[0].error is not None
        assert test_results[0].error.severity == Severity.CRITICAL


if __name__ == "__main__":
    pytest.main([__file__])