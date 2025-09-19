"""
Unit tests for API Contract Validator.

Tests the contract validation logic, method discovery, signature comparison,
and JSON-RPC protocol compliance validation.
"""

import asyncio
import json
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List
import aiohttp
from aiohttp import web
import inspect

from agents.tests.integration.api_contract_validator import (
    APIContractValidator, MethodSignature, ContractValidationResult
)
from agents.tests.integration.models import TestCategory, TestStatus, Severity
from agents.tests.integration.config import TestConfig, AgentConfig, TimeoutConfig


class TestMethodSignature:
    """Test MethodSignature class."""
    
    def test_method_signature_creation(self):
        """Test creating a method signature."""
        signature = MethodSignature(
            name="test_method",
            parameters={"param1": {"type": "string", "required": True}},
            return_type="Dict",
            is_async=True,
            docstring="Test method"
        )
        
        assert signature.name == "test_method"
        assert signature.parameters["param1"]["type"] == "string"
        assert signature.return_type == "Dict"
        assert signature.is_async is True
        assert signature.docstring == "Test method"
    
    def test_method_signature_to_dict(self):
        """Test converting method signature to dictionary."""
        signature = MethodSignature(
            name="test_method",
            parameters={"param1": {"type": "string", "required": True}},
            return_type="Dict"
        )
        
        result = signature.to_dict()
        
        assert result["name"] == "test_method"
        assert result["parameters"]["param1"]["type"] == "string"
        assert result["return_type"] == "Dict"


class TestContractValidationResult:
    """Test ContractValidationResult class."""
    
    def test_contract_validation_result_creation(self):
        """Test creating a contract validation result."""
        result = ContractValidationResult(agent_name="test_agent")
        
        assert result.agent_name == "test_agent"
        assert result.is_valid is True
        assert len(result.frontend_methods) == 0
        assert len(result.backend_methods) == 0
    
    def test_contract_validation_result_to_dict(self):
        """Test converting validation result to dictionary."""
        method = MethodSignature(name="test_method")
        result = ContractValidationResult(
            agent_name="test_agent",
            frontend_methods=[method],
            missing_backend_methods=["missing_method"],
            is_valid=False
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["agent_name"] == "test_agent"
        assert len(result_dict["frontend_methods"]) == 1
        assert result_dict["missing_backend_methods"] == ["missing_method"]
        assert result_dict["is_valid"] is False


class TestAPIContractValidator:
    """Test APIContractValidator class."""
    
    @pytest.fixture
    def test_config(self):
        """Create test configuration."""
        config = TestConfig()
        config.agents = {
            "hill_metrics": AgentConfig(
                name="hill_metrics",
                host="localhost",
                port=8001,
                enabled=True
            ),
            "weather": AgentConfig(
                name="weather",
                host="localhost",
                port=8002,
                enabled=True
            )
        }
        config.timeouts = TimeoutConfig(network_request=5)
        return config
    
    @pytest.fixture
    def validator(self, test_config):
        """Create API contract validator."""
        return APIContractValidator(test_config)
    
    def test_validator_initialization(self, validator, test_config):
        """Test validator initialization."""
        assert validator.config == test_config
        assert validator.session is None
        assert "hill_metrics" in validator.frontend_method_mappings
        assert "weather" in validator.frontend_method_mappings
        assert "equipment" in validator.frontend_method_mappings
    
    @pytest.mark.asyncio
    async def test_context_manager(self, validator):
        """Test async context manager functionality."""
        async with validator as v:
            assert v.session is not None
            assert isinstance(v.session, aiohttp.ClientSession)
        
        # Session should be closed after context exit
        assert v.session.closed
    
    def test_get_type_string(self, validator):
        """Test type string conversion."""
        # Test basic types
        assert validator._get_type_string(str) == "str"
        assert validator._get_type_string(int) == "int"
        assert validator._get_type_string(inspect.Parameter.empty) == "Any"
        
        # Test complex type
        from typing import Dict
        result = validator._get_type_string(Dict[str, Any])
        assert "Dict" in result or "dict" in result
    
    def test_extract_method_signature(self, validator):
        """Test method signature extraction."""
        async def test_method(param1: str, param2: int = 10) -> Dict[str, Any]:
            """Test method docstring."""
            return {}
        
        signature = validator._extract_method_signature("test_method", test_method)
        
        assert signature.name == "test_method"
        assert signature.is_async is True
        assert signature.docstring == "Test method docstring."
        assert "param1" in signature.parameters
        assert signature.parameters["param1"]["required"] is True
        assert signature.parameters["param2"]["required"] is False
        assert signature.parameters["param2"]["default"] == 10
    
    def test_get_frontend_methods(self, validator):
        """Test getting frontend methods from mapping."""
        methods = validator._get_frontend_methods("hill_metrics")
        
        assert len(methods) > 0
        method_names = [m.name for m in methods]
        assert "getHillMetrics" in method_names
        assert "getElevationProfile" in method_names
        
        # Check specific method details
        hill_metrics_method = next(m for m in methods if m.name == "getHillMetrics")
        assert "bounds" in hill_metrics_method.parameters
        assert hill_metrics_method.parameters["bounds"]["required"] is True
        assert hill_metrics_method.return_type == "HillMetricsResponse"
    
    def test_get_frontend_methods_unknown_agent(self, validator):
        """Test getting frontend methods for unknown agent."""
        methods = validator._get_frontend_methods("unknown_agent")
        assert len(methods) == 0
    
    def test_are_types_compatible(self, validator):
        """Test type compatibility checking."""
        # Exact match
        assert validator._are_types_compatible("string", "string") is True
        
        # Compatible mappings
        assert validator._are_types_compatible("string", "str") is True
        assert validator._are_types_compatible("number", "float") is True
        assert validator._are_types_compatible("number", "int") is True
        assert validator._are_types_compatible("boolean", "bool") is True
        assert validator._are_types_compatible("object", "dict") is True
        assert validator._are_types_compatible("array", "list") is True
        
        # Reverse mappings
        assert validator._are_types_compatible("str", "string") is True
        assert validator._are_types_compatible("int", "number") is True
        
        # Unknown types (default to compatible)
        assert validator._are_types_compatible("unknown1", "unknown2") is True
    
    def test_compare_method_signatures_compatible(self, validator):
        """Test comparing compatible method signatures."""
        frontend_method = MethodSignature(
            name="test_method",
            parameters={
                "param1": {"type": "string", "required": True},
                "param2": {"type": "number", "required": False, "default": 10}
            }
        )
        
        backend_method = MethodSignature(
            name="test_method",
            parameters={
                "param1": {"type": "str", "required": True},
                "param2": {"type": "int", "required": False, "default": 10}
            }
        )
        
        result = validator._compare_method_signatures(frontend_method, backend_method)
        assert result is None  # No mismatch
    
    def test_compare_method_signatures_missing_backend_param(self, validator):
        """Test comparing signatures with missing backend parameter."""
        frontend_method = MethodSignature(
            name="test_method",
            parameters={
                "param1": {"type": "string", "required": True},
                "param2": {"type": "number", "required": True}
            }
        )
        
        backend_method = MethodSignature(
            name="test_method",
            parameters={
                "param1": {"type": "str", "required": True}
            }
        )
        
        result = validator._compare_method_signatures(frontend_method, backend_method)
        assert result is not None
        assert "Missing backend parameters" in result["mismatches"][0]
        assert "param2" in result["mismatches"][0]
    
    def test_compare_method_signatures_extra_required_backend_param(self, validator):
        """Test comparing signatures with extra required backend parameter."""
        frontend_method = MethodSignature(
            name="test_method",
            parameters={
                "param1": {"type": "string", "required": True}
            }
        )
        
        backend_method = MethodSignature(
            name="test_method",
            parameters={
                "param1": {"type": "str", "required": True},
                "param2": {"type": "int", "required": True}  # Extra required param
            }
        )
        
        result = validator._compare_method_signatures(frontend_method, backend_method)
        assert result is not None
        assert "Extra required backend parameters" in result["mismatches"][0]
        assert "param2" in result["mismatches"][0]
    
    def test_compare_method_signatures_type_mismatch(self, validator):
        """Test comparing signatures with type mismatch."""
        frontend_method = MethodSignature(
            name="test_method",
            parameters={
                "param1": {"type": "string", "required": True}
            }
        )
        
        backend_method = MethodSignature(
            name="test_method",
            parameters={
                "param1": {"type": "CustomType", "required": True}
            }
        )
        
        # Mock type compatibility to return False
        with patch.object(validator, '_are_types_compatible', return_value=False):
            result = validator._compare_method_signatures(frontend_method, backend_method)
            assert result is not None
            assert "type mismatch" in result["mismatches"][0]
            assert "param1" in result["mismatches"][0]
    
    def test_compare_methods(self, validator):
        """Test comparing frontend and backend methods."""
        result = ContractValidationResult(agent_name="test_agent")
        
        # Set up test methods
        result.frontend_methods = [
            MethodSignature(name="method1"),
            MethodSignature(name="method2"),
            MethodSignature(name="common_method")
        ]
        
        result.backend_methods = [
            MethodSignature(name="method3"),
            MethodSignature(name="method4"),
            MethodSignature(name="common_method")
        ]
        
        validator._compare_methods(result)
        
        # Check missing methods
        assert "method1" in result.missing_backend_methods
        assert "method2" in result.missing_backend_methods
        assert "method3" in result.missing_frontend_methods
        assert "method4" in result.missing_frontend_methods
        
        # Common method should not be in missing lists
        assert "common_method" not in result.missing_backend_methods
        assert "common_method" not in result.missing_frontend_methods
    
    def test_is_valid_jsonrpc_response_valid(self, validator):
        """Test validating a valid JSON-RPC response."""
        valid_response = {
            "jsonrpc": "2.0",
            "result": {"data": "test"},
            "id": 1
        }
        
        assert validator._is_valid_jsonrpc_response(valid_response) is True
    
    def test_is_valid_jsonrpc_response_valid_error(self, validator):
        """Test validating a valid JSON-RPC error response."""
        valid_error_response = {
            "jsonrpc": "2.0",
            "error": {
                "code": -32601,
                "message": "Method not found"
            },
            "id": 1
        }
        
        assert validator._is_valid_jsonrpc_response(valid_error_response) is True
    
    def test_is_valid_jsonrpc_response_invalid_version(self, validator):
        """Test validating JSON-RPC response with invalid version."""
        invalid_response = {
            "jsonrpc": "1.0",  # Wrong version
            "result": {"data": "test"},
            "id": 1
        }
        
        assert validator._is_valid_jsonrpc_response(invalid_response) is False
    
    def test_is_valid_jsonrpc_response_both_result_and_error(self, validator):
        """Test validating JSON-RPC response with both result and error."""
        invalid_response = {
            "jsonrpc": "2.0",
            "result": {"data": "test"},
            "error": {"code": -1, "message": "error"},
            "id": 1
        }
        
        assert validator._is_valid_jsonrpc_response(invalid_response) is False
    
    def test_is_valid_jsonrpc_response_no_result_or_error(self, validator):
        """Test validating JSON-RPC response with neither result nor error."""
        invalid_response = {
            "jsonrpc": "2.0",
            "id": 1
        }
        
        assert validator._is_valid_jsonrpc_response(invalid_response) is False
    
    def test_is_valid_jsonrpc_response_no_id(self, validator):
        """Test validating JSON-RPC response without id."""
        invalid_response = {
            "jsonrpc": "2.0",
            "result": {"data": "test"}
        }
        
        assert validator._is_valid_jsonrpc_response(invalid_response) is False
    
    def test_is_valid_jsonrpc_response_invalid_error_format(self, validator):
        """Test validating JSON-RPC response with invalid error format."""
        invalid_response = {
            "jsonrpc": "2.0",
            "error": {
                "message": "Missing code"  # Missing required 'code' field
            },
            "id": 1
        }
        
        assert validator._is_valid_jsonrpc_response(invalid_response) is False
    
    def test_generate_suggested_fix(self, validator):
        """Test generating suggested fixes for validation issues."""
        result = ContractValidationResult(
            agent_name="test_agent",
            missing_backend_methods=["method1", "method2"],
            signature_mismatches=[{"method": "method3"}],
            protocol_violations=["Invalid response format"]
        )
        
        fix = validator._generate_suggested_fix(result)
        
        assert "Implement missing backend methods" in fix
        assert "method1" in fix
        assert "method2" in fix
        assert "Review method signatures" in fix
        assert "Fix JSON-RPC protocol compliance" in fix
    
    def test_generate_suggested_fix_no_issues(self, validator):
        """Test generating suggested fix when no specific issues found."""
        result = ContractValidationResult(agent_name="test_agent")
        
        fix = validator._generate_suggested_fix(result)
        
        assert "Review contract validation details" in fix
    
    @pytest.mark.asyncio
    async def test_discover_backend_methods_import_error(self, validator):
        """Test backend method discovery with import error."""
        with pytest.raises(ImportError):
            await validator._discover_backend_methods("nonexistent_agent")
    
    @pytest.mark.asyncio
    async def test_validate_agent_contract_disabled_agent(self, validator):
        """Test validating contract for disabled agent."""
        # Disable agent
        validator.config.agents["hill_metrics"].enabled = False
        
        results = await validator.validate_all_contracts()
        
        # Should not include disabled agent
        agent_names = [r.agent_name for r in results]
        assert "hill_metrics" not in agent_names
    
    @pytest.mark.asyncio
    async def test_run_contract_tests_success(self, validator):
        """Test running contract tests with successful validation."""
        # Mock successful validation
        mock_result = ContractValidationResult(
            agent_name="test_agent",
            is_valid=True
        )
        
        with patch.object(validator, 'validate_all_contracts', return_value=[mock_result]):
            test_results = await validator.run_contract_tests()
        
        assert len(test_results) == 1
        assert test_results[0].status == TestStatus.PASSED
        assert test_results[0].category == TestCategory.API_CONTRACTS
        assert "test_agent" in test_results[0].name
    
    @pytest.mark.asyncio
    async def test_run_contract_tests_failure(self, validator):
        """Test running contract tests with validation failure."""
        # Mock failed validation
        mock_result = ContractValidationResult(
            agent_name="test_agent",
            is_valid=False,
            missing_backend_methods=["missing_method"],
            protocol_violations=["Protocol error"]
        )
        
        with patch.object(validator, 'validate_all_contracts', return_value=[mock_result]):
            test_results = await validator.run_contract_tests()
        
        assert len(test_results) == 1
        assert test_results[0].status == TestStatus.FAILED
        assert test_results[0].error is not None
        assert test_results[0].error.severity == Severity.HIGH
        assert "missing_method" in test_results[0].error.message
    
    @pytest.mark.asyncio
    async def test_run_contract_tests_exception(self, validator):
        """Test running contract tests with exception."""
        # Mock exception during validation
        with patch.object(validator, 'validate_all_contracts', side_effect=Exception("Test error")):
            test_results = await validator.run_contract_tests()
        
        assert len(test_results) == 1
        assert test_results[0].status == TestStatus.FAILED  # Changed from ERROR to FAILED
        assert test_results[0].error is not None
        assert test_results[0].error.severity == Severity.CRITICAL
        assert "Test error" in test_results[0].error.message


class TestJSONRPCProtocolValidation:
    """Test JSON-RPC protocol validation."""
    
    @pytest.mark.asyncio
    async def test_jsonrpc_protocol_validation_no_session(self):
        """Test JSON-RPC protocol validation when no session is available."""
        config = TestConfig()
        config.agents = {
            "test_agent": AgentConfig(
                name="test_agent",
                host="localhost",
                port=8999,
                enabled=True
            )
        }
        
        validator = APIContractValidator(config)
        result = ContractValidationResult(agent_name="test_agent")
        
        # Test without session (should add protocol violation)
        await validator._validate_jsonrpc_compliance(
            "test_agent", 
            config.agents["test_agent"], 
            result
        )
        
        # Should have protocol violation about missing session
        assert len(result.protocol_violations) == 1
        assert "No HTTP session available" in result.protocol_violations[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])