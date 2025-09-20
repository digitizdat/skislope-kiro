"""
Unit tests for CommunicationValidator.

Tests CORS validation, JSON-RPC protocol compliance, MCP protocol support,
and network timeout/retry mechanism testing.
"""

from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from aiohttp import ClientResponse
from aiohttp import ClientTimeout

from agents.tests.integration.communication_validator import (
    CommunicationValidationResult,
)
from agents.tests.integration.communication_validator import CommunicationValidator
from agents.tests.integration.communication_validator import CORSTestResult
from agents.tests.integration.communication_validator import JSONRPCTestResult
from agents.tests.integration.communication_validator import MCPTestResult
from agents.tests.integration.communication_validator import NetworkTestResult
from agents.tests.integration.config import AgentConfig
from agents.tests.integration.config import TestConfig
from agents.tests.integration.models import Severity
from agents.tests.integration.models import TestCategory
from agents.tests.integration.models import TestStatus


class TestCommunicationValidator:
    """Test cases for CommunicationValidator."""

    @pytest.fixture
    def test_config(self):
        """Create test configuration."""
        config = TestConfig()
        config.agents = {
            "test_agent": AgentConfig(
                name="test_agent", host="localhost", port=8001, enabled=True
            )
        }
        return config

    @pytest.fixture
    def validator(self, test_config):
        """Create CommunicationValidator instance."""
        return CommunicationValidator(test_config)

    @pytest.fixture
    def mock_session(self):
        """Create mock aiohttp session with proper async context manager support."""
        session = MagicMock()

        # Create mock methods that return async context managers
        session.options = MagicMock()
        session.post = MagicMock()
        session.get = MagicMock()

        return session

    def create_mock_response_context(
        self, status=200, json_data=None, headers=None, text=""
    ):
        """Create mock HTTP response with proper async context manager."""
        response = AsyncMock(spec=ClientResponse)
        response.status = status
        response.headers = headers or {}

        if json_data is not None:
            response.json = AsyncMock(return_value=json_data)

        response.text = AsyncMock(return_value=text)

        # Create a proper async context manager
        context_manager = AsyncMock()
        context_manager.__aenter__ = AsyncMock(return_value=response)
        context_manager.__aexit__ = AsyncMock(return_value=None)

        return context_manager

    @pytest.mark.asyncio
    async def test_cors_configuration_valid(self, validator, mock_session):
        """Test valid CORS configuration."""
        validator.session = mock_session

        # Create successful preflight response
        preflight_response = AsyncMock(spec=ClientResponse)
        preflight_response.status = 200
        preflight_response.headers = {
            "Access-Control-Allow-Origin": "http://localhost:3000",
            "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "Access-Control-Allow-Credentials": "true",
        }

        preflight_context = AsyncMock()
        preflight_context.__aenter__ = AsyncMock(return_value=preflight_response)
        preflight_context.__aexit__ = AsyncMock(return_value=None)

        # Create successful actual request response
        actual_response = AsyncMock(spec=ClientResponse)
        actual_response.status = 200
        actual_response.headers = {
            "Access-Control-Allow-Origin": "http://localhost:3000"
        }
        actual_response.json = AsyncMock(
            return_value={"jsonrpc": "2.0", "result": "ok", "id": 1}
        )

        actual_context = AsyncMock()
        actual_context.__aenter__ = AsyncMock(return_value=actual_response)
        actual_context.__aexit__ = AsyncMock(return_value=None)

        mock_session.options.return_value = preflight_context
        mock_session.post.return_value = actual_context

        agent_config = AgentConfig(name="test_agent", port=8001)
        result = await validator._test_cors_configuration("test_agent", agent_config)

        # The test should pass with proper mocking
        assert result.is_valid
        assert result.preflight_successful

    @pytest.mark.asyncio
    async def test_cors_configuration_invalid(self, validator, mock_session):
        """Test invalid CORS configuration."""
        validator.session = mock_session

        # Create mock response
        response = AsyncMock(spec=ClientResponse)
        response.status = 404
        response.headers = {}

        # Create proper context manager
        context_manager = AsyncMock()
        context_manager.__aenter__ = AsyncMock(return_value=response)
        context_manager.__aexit__ = AsyncMock(return_value=None)

        mock_session.options.return_value = context_manager

        agent_config = AgentConfig(name="test_agent", port=8001)
        result = await validator._test_cors_configuration("test_agent", agent_config)

        assert not result.is_valid
        assert not result.preflight_successful
        assert len(result.cors_violations) > 0
        assert any(
            "Preflight failed" in violation for violation in result.cors_violations
        )

    @pytest.mark.asyncio
    async def test_jsonrpc_protocol_valid(self, validator, mock_session):
        """Test valid JSON-RPC protocol compliance."""
        validator.session = mock_session

        def create_response_context(status=200, json_data=None, text=""):
            """Helper to create response with context manager."""
            response = AsyncMock(spec=ClientResponse)
            response.status = status
            response.headers = {}
            if json_data is not None:
                response.json = AsyncMock(return_value=json_data)
            response.text = AsyncMock(return_value=text)

            context_manager = AsyncMock()
            context_manager.__aenter__ = AsyncMock(return_value=response)
            context_manager.__aexit__ = AsyncMock(return_value=None)
            return context_manager

        # Set up mock responses in order
        mock_session.post.side_effect = [
            create_response_context(
                200, {"jsonrpc": "2.0", "result": {"status": "healthy"}, "id": 1}
            ),
            create_response_context(
                200,
                {
                    "jsonrpc": "2.0",
                    "error": {"code": -32700, "message": "Parse error"},
                    "id": None,
                },
            ),
            create_response_context(
                200,
                {
                    "jsonrpc": "2.0",
                    "error": {"code": -32600, "message": "Invalid Request"},
                    "id": None,
                },
            ),
            create_response_context(
                200,
                {
                    "jsonrpc": "2.0",
                    "error": {"code": -32601, "message": "Method not found"},
                    "id": 2,
                },
            ),
            create_response_context(
                200,
                [
                    {"jsonrpc": "2.0", "result": {"status": "healthy"}, "id": 1},
                    {"jsonrpc": "2.0", "result": {"status": "healthy"}, "id": 2},
                ],
            ),
            create_response_context(200, text=""),
        ]

        agent_config = AgentConfig(name="test_agent", port=8001)
        result = await validator._test_jsonrpc_protocol("test_agent", agent_config)

        assert result.is_valid
        assert result.request_response_valid
        assert result.error_handling_valid
        assert result.batch_requests_supported
        assert result.notification_handling_valid
        assert "healthCheck" in result.supported_methods
        assert len(result.protocol_violations) == 0

    @pytest.mark.asyncio
    async def test_jsonrpc_protocol_invalid(self, validator, mock_session):
        """Test invalid JSON-RPC protocol compliance."""
        validator.session = mock_session

        # Create mock response with missing jsonrpc field
        response = AsyncMock(spec=ClientResponse)
        response.status = 200
        response.headers = {}
        response.json = AsyncMock(
            return_value={"result": "ok", "id": 1}
        )  # Missing jsonrpc field

        context_manager = AsyncMock()
        context_manager.__aenter__ = AsyncMock(return_value=response)
        context_manager.__aexit__ = AsyncMock(return_value=None)

        mock_session.post.return_value = context_manager

        agent_config = AgentConfig(name="test_agent", port=8001)
        result = await validator._test_jsonrpc_protocol("test_agent", agent_config)

        assert not result.is_valid
        assert not result.request_response_valid
        assert len(result.protocol_violations) > 0

    @pytest.mark.asyncio
    async def test_mcp_protocol_supported(self, validator, mock_session):
        """Test MCP protocol support detection."""
        validator.session = mock_session

        # Create MCP discovery response
        mcp_response = AsyncMock(spec=ClientResponse)
        mcp_response.status = 200
        mcp_response.headers = {}
        mcp_response.json = AsyncMock(
            return_value={
                "protocol_version": "1.0",
                "tools": ["terrain_analysis", "weather_forecast"],
            }
        )

        mcp_context = AsyncMock()
        mcp_context.__aenter__ = AsyncMock(return_value=mcp_response)
        mcp_context.__aexit__ = AsyncMock(return_value=None)

        # Create tool execution response
        tool_response = AsyncMock(spec=ClientResponse)
        tool_response.status = 200
        tool_response.headers = {}

        tool_context = AsyncMock()
        tool_context.__aenter__ = AsyncMock(return_value=tool_response)
        tool_context.__aexit__ = AsyncMock(return_value=None)

        mock_session.get.return_value = mcp_context
        mock_session.post.return_value = tool_context

        agent_config = AgentConfig(name="test_agent", port=8001)
        result = await validator._test_mcp_protocol("test_agent", agent_config)

        assert result.is_valid
        assert result.mcp_supported
        assert result.protocol_version == "1.0"
        assert "terrain_analysis" in result.available_tools
        assert "weather_forecast" in result.available_tools
        assert result.tool_discovery_valid
        assert result.tool_execution_valid

    @pytest.mark.asyncio
    async def test_mcp_protocol_not_supported(self, validator, mock_session):
        """Test MCP protocol not supported (which is okay)."""
        validator.session = mock_session

        # Create MCP endpoint not found response
        mcp_response = AsyncMock(spec=ClientResponse)
        mcp_response.status = 404
        mcp_response.headers = {}

        mcp_context = AsyncMock()
        mcp_context.__aenter__ = AsyncMock(return_value=mcp_response)
        mcp_context.__aexit__ = AsyncMock(return_value=None)

        mock_session.get.return_value = mcp_context

        agent_config = AgentConfig(name="test_agent", port=8001)
        result = await validator._test_mcp_protocol("test_agent", agent_config)

        assert result.is_valid  # MCP is optional
        assert not result.mcp_supported
        assert len(result.mcp_violations) > 0

    @pytest.mark.asyncio
    async def test_network_mechanisms_valid(self, validator, mock_session):
        """Test valid network timeout and retry mechanisms."""
        validator.session = mock_session

        # Create successful response context manager
        def create_success_response():
            response = AsyncMock(spec=ClientResponse)
            response.status = 200
            response.headers = {}
            response.json = AsyncMock(
                return_value={"jsonrpc": "2.0", "result": "ok", "id": 1}
            )

            context_manager = AsyncMock()
            context_manager.__aenter__ = AsyncMock(return_value=response)
            context_manager.__aexit__ = AsyncMock(return_value=None)
            return context_manager

        mock_session.post.return_value = create_success_response()

        agent_config = AgentConfig(name="test_agent", port=8001)

        with patch("aiohttp.ClientSession") as mock_client_session:
            # Mock timeout session with proper context manager support
            timeout_session = MagicMock()
            timeout_session.post.return_value = create_success_response()
            timeout_session.close = AsyncMock()
            mock_client_session.return_value = timeout_session

            result = await validator._test_network_mechanisms(
                "test_agent", agent_config
            )

        assert result.is_valid
        assert result.timeout_handling_valid
        assert result.retry_mechanism_valid
        assert result.concurrent_request_handling
        assert result.large_payload_handling
        assert len(result.network_issues) == 0
        assert "retry_success_rate" in result.performance_metrics

    @pytest.mark.asyncio
    async def test_network_mechanisms_timeout(self, validator, mock_session):
        """Test network timeout handling."""
        validator.session = mock_session

        agent_config = AgentConfig(name="test_agent", port=8001)

        # Create successful response context manager
        def create_success_response():
            response = AsyncMock(spec=ClientResponse)
            response.status = 200
            response.headers = {}
            response.json = AsyncMock(
                return_value={"jsonrpc": "2.0", "result": "ok", "id": 1}
            )

            context_manager = AsyncMock()
            context_manager.__aenter__ = AsyncMock(return_value=response)
            context_manager.__aexit__ = AsyncMock(return_value=None)
            return context_manager

        with patch("aiohttp.ClientSession") as mock_client_session:
            # Mock timeout session that raises TimeoutError
            timeout_session = MagicMock()
            timeout_session.post.side_effect = TimeoutError()
            timeout_session.close = AsyncMock()
            mock_client_session.return_value = timeout_session

            # Mock other successful responses
            mock_session.post.return_value = create_success_response()

            result = await validator._test_network_mechanisms(
                "test_agent", agent_config
            )

        assert result.timeout_handling_valid  # Timeout is expected behavior
        assert "timeout_duration" in result.performance_metrics

    @pytest.mark.asyncio
    async def test_validate_agent_communication_success(self, validator, mock_session):
        """Test successful agent communication validation."""
        validator.session = mock_session

        # Mock all validation methods to return successful results
        with (
            patch.object(validator, "_test_cors_configuration") as mock_cors,
            patch.object(validator, "_test_jsonrpc_protocol") as mock_jsonrpc,
            patch.object(validator, "_test_mcp_protocol") as mock_mcp,
            patch.object(validator, "_test_network_mechanisms") as mock_network,
        ):
            mock_cors.return_value = CORSTestResult(
                agent_name="test_agent",
                endpoint="http://localhost:8001/jsonrpc",
                is_valid=True,
            )

            mock_jsonrpc.return_value = JSONRPCTestResult(
                agent_name="test_agent",
                endpoint="http://localhost:8001/jsonrpc",
                is_valid=True,
            )

            mock_mcp.return_value = MCPTestResult(
                agent_name="test_agent",
                endpoint="http://localhost:8001/mcp",
                is_valid=True,
            )

            mock_network.return_value = NetworkTestResult(
                agent_name="test_agent",
                endpoint="http://localhost:8001/jsonrpc",
                is_valid=True,
            )

            agent_config = AgentConfig(name="test_agent", port=8001)
            result = await validator.validate_agent_communication(
                "test_agent", agent_config
            )

        assert result.overall_valid
        assert result.cors_result.is_valid
        assert result.jsonrpc_result.is_valid
        assert result.mcp_result.is_valid
        assert result.network_result.is_valid
        assert len(result.validation_errors) == 0

    @pytest.mark.asyncio
    async def test_validate_agent_communication_failure(self, validator, mock_session):
        """Test failed agent communication validation."""
        validator.session = mock_session

        # Mock validation methods to return failed results
        with (
            patch.object(validator, "_test_cors_configuration") as mock_cors,
            patch.object(validator, "_test_jsonrpc_protocol") as mock_jsonrpc,
            patch.object(validator, "_test_mcp_protocol") as mock_mcp,
            patch.object(validator, "_test_network_mechanisms") as mock_network,
        ):
            mock_cors.return_value = CORSTestResult(
                agent_name="test_agent",
                endpoint="http://localhost:8001/jsonrpc",
                is_valid=False,
                cors_violations=["CORS not configured"],
            )

            mock_jsonrpc.return_value = JSONRPCTestResult(
                agent_name="test_agent",
                endpoint="http://localhost:8001/jsonrpc",
                is_valid=False,
                protocol_violations=["Invalid JSON-RPC response"],
            )

            mock_mcp.return_value = MCPTestResult(
                agent_name="test_agent",
                endpoint="http://localhost:8001/mcp",
                is_valid=True,  # MCP is optional
            )

            mock_network.return_value = NetworkTestResult(
                agent_name="test_agent",
                endpoint="http://localhost:8001/jsonrpc",
                is_valid=False,
                network_issues=["Timeout handling failed"],
            )

            agent_config = AgentConfig(name="test_agent", port=8001)
            result = await validator.validate_agent_communication(
                "test_agent", agent_config
            )

        assert not result.overall_valid
        assert not result.cors_result.is_valid
        assert not result.jsonrpc_result.is_valid
        assert result.mcp_result.is_valid  # MCP is optional
        assert not result.network_result.is_valid

    @pytest.mark.asyncio
    async def test_validate_all_communication(self, validator, mock_session):
        """Test validation of all configured agents."""
        validator.session = mock_session

        # Add multiple agents to config
        validator.config.agents = {
            "agent1": AgentConfig(name="agent1", port=8001, enabled=True),
            "agent2": AgentConfig(name="agent2", port=8002, enabled=True),
            "agent3": AgentConfig(name="agent3", port=8003, enabled=False),  # Disabled
        }

        with patch.object(validator, "validate_agent_communication") as mock_validate:
            mock_validate.side_effect = [
                CommunicationValidationResult(agent_name="agent1", overall_valid=True),
                CommunicationValidationResult(agent_name="agent2", overall_valid=False),
            ]

            results = await validator.validate_all_communication()

        assert len(results) == 2  # Only enabled agents
        assert results[0].agent_name == "agent1"
        assert results[0].overall_valid
        assert results[1].agent_name == "agent2"
        assert not results[1].overall_valid

        # Verify disabled agent was skipped
        mock_validate.assert_any_call("agent1", validator.config.agents["agent1"])
        mock_validate.assert_any_call("agent2", validator.config.agents["agent2"])
        assert mock_validate.call_count == 2

    @pytest.mark.asyncio
    async def test_run_communication_tests(self, validator, mock_session):
        """Test running all communication tests and generating test results."""
        validator.session = mock_session

        # Mock validation results
        validation_results = [
            CommunicationValidationResult(
                agent_name="test_agent",
                cors_result=CORSTestResult(
                    agent_name="test_agent",
                    endpoint="http://localhost:8001/jsonrpc",
                    is_valid=True,
                ),
                jsonrpc_result=JSONRPCTestResult(
                    agent_name="test_agent",
                    endpoint="http://localhost:8001/jsonrpc",
                    is_valid=True,
                ),
                mcp_result=MCPTestResult(
                    agent_name="test_agent",
                    endpoint="http://localhost:8001/mcp",
                    is_valid=True,
                ),
                network_result=NetworkTestResult(
                    agent_name="test_agent",
                    endpoint="http://localhost:8001/jsonrpc",
                    is_valid=True,
                ),
                overall_valid=True,
            )
        ]

        with patch.object(validator, "validate_all_communication") as mock_validate:
            mock_validate.return_value = validation_results

            test_results = await validator.run_communication_tests()

        # Should have 4 test results (CORS, JSON-RPC, MCP, Network)
        assert len(test_results) == 4

        # Check test result categories
        categories = [result.category for result in test_results]
        assert all(cat == TestCategory.COMMUNICATION for cat in categories)

        # Check test result statuses
        statuses = [result.status for result in test_results]
        assert all(status == TestStatus.PASSED for status in statuses)

        # Check test names
        names = [result.name for result in test_results]
        assert "CORS Configuration - test_agent" in names
        assert "JSON-RPC Protocol - test_agent" in names
        assert "MCP Protocol - test_agent" in names
        assert "Network Mechanisms - test_agent" in names

    @pytest.mark.asyncio
    async def test_run_communication_tests_with_failures(self, validator, mock_session):
        """Test running communication tests with failures."""
        validator.session = mock_session

        # Mock validation results with failures
        validation_results = [
            CommunicationValidationResult(
                agent_name="test_agent",
                cors_result=CORSTestResult(
                    agent_name="test_agent",
                    endpoint="http://localhost:8001/jsonrpc",
                    is_valid=False,
                    cors_violations=["CORS not configured properly"],
                ),
                jsonrpc_result=JSONRPCTestResult(
                    agent_name="test_agent",
                    endpoint="http://localhost:8001/jsonrpc",
                    is_valid=False,
                    protocol_violations=["Invalid JSON-RPC response format"],
                ),
                overall_valid=False,
            )
        ]

        with patch.object(validator, "validate_all_communication") as mock_validate:
            mock_validate.return_value = validation_results

            test_results = await validator.run_communication_tests()

        # Should have 2 test results (CORS and JSON-RPC)
        assert len(test_results) == 2

        # Check that tests failed
        failed_tests = [
            result for result in test_results if result.status == TestStatus.FAILED
        ]
        assert len(failed_tests) == 2

        # Check error details
        cors_test = next(result for result in test_results if "CORS" in result.name)
        assert cors_test.error is not None
        assert cors_test.error.severity == Severity.HIGH
        assert "CORS violations" in cors_test.error.message

    def test_validate_jsonrpc_response_valid(self, validator):
        """Test JSON-RPC response validation with valid response."""
        valid_response = {"jsonrpc": "2.0", "result": {"status": "ok"}, "id": 1}

        assert validator._validate_jsonrpc_response(valid_response, 1)

    def test_validate_jsonrpc_response_invalid(self, validator):
        """Test JSON-RPC response validation with invalid responses."""
        # Missing jsonrpc field
        invalid_response1 = {"result": {"status": "ok"}, "id": 1}
        assert not validator._validate_jsonrpc_response(invalid_response1, 1)

        # Wrong jsonrpc version
        invalid_response2 = {"jsonrpc": "1.0", "result": {"status": "ok"}, "id": 1}
        assert not validator._validate_jsonrpc_response(invalid_response2, 1)

        # Both result and error
        invalid_response3 = {
            "jsonrpc": "2.0",
            "result": {"status": "ok"},
            "error": {"code": -32000, "message": "Error"},
            "id": 1,
        }
        assert not validator._validate_jsonrpc_response(invalid_response3, 1)

        # Wrong ID
        invalid_response4 = {"jsonrpc": "2.0", "result": {"status": "ok"}, "id": 2}
        assert not validator._validate_jsonrpc_response(invalid_response4, 1)

    def test_validate_jsonrpc_error_valid(self, validator):
        """Test JSON-RPC error validation with valid error response."""
        valid_error = {
            "jsonrpc": "2.0",
            "error": {"code": -32601, "message": "Method not found"},
            "id": 1,
        }

        assert validator._validate_jsonrpc_error(valid_error, -32601)

    def test_validate_jsonrpc_error_invalid(self, validator):
        """Test JSON-RPC error validation with invalid error responses."""
        # Wrong error code
        invalid_error1 = {
            "jsonrpc": "2.0",
            "error": {"code": -32600, "message": "Invalid Request"},
            "id": 1,
        }
        assert not validator._validate_jsonrpc_error(invalid_error1, -32601)

        # Missing message
        invalid_error2 = {"jsonrpc": "2.0", "error": {"code": -32601}, "id": 1}
        assert not validator._validate_jsonrpc_error(invalid_error2, -32601)

        # Error not a dict
        invalid_error3 = {"jsonrpc": "2.0", "error": "Method not found", "id": 1}
        assert not validator._validate_jsonrpc_error(invalid_error3, -32601)

    @pytest.mark.asyncio
    async def test_context_manager(self, validator):
        """Test async context manager functionality."""
        assert validator.session is None

        async with validator as v:
            assert v.session is not None
            assert isinstance(v.session.timeout, ClientTimeout)

        # Session should be closed after context exit
        # Note: In real usage, session.close() would be called

    @pytest.mark.asyncio
    async def test_make_concurrent_request_success(self, validator, mock_session):
        """Test concurrent request helper method success."""
        validator.session = mock_session

        # Create successful response context manager
        response = AsyncMock(spec=ClientResponse)
        response.status = 200
        response.headers = {}

        context_manager = AsyncMock()
        context_manager.__aenter__ = AsyncMock(return_value=response)
        context_manager.__aexit__ = AsyncMock(return_value=None)

        mock_session.post.return_value = context_manager

        request = {"jsonrpc": "2.0", "method": "test", "id": 1}
        result = await validator._make_concurrent_request(
            "http://localhost:8001/jsonrpc", request
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_make_concurrent_request_failure(self, validator, mock_session):
        """Test concurrent request helper method failure."""
        validator.session = mock_session

        # Create failure response context manager
        response = AsyncMock(spec=ClientResponse)
        response.status = 500
        response.headers = {}

        context_manager = AsyncMock()
        context_manager.__aenter__ = AsyncMock(return_value=response)
        context_manager.__aexit__ = AsyncMock(return_value=None)

        mock_session.post.return_value = context_manager

        request = {"jsonrpc": "2.0", "method": "test", "id": 1}
        result = await validator._make_concurrent_request(
            "http://localhost:8001/jsonrpc", request
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_make_concurrent_request_exception(self, validator, mock_session):
        """Test concurrent request helper method with exception."""
        validator.session = mock_session

        mock_session.post.side_effect = Exception("Network error")

        request = {"jsonrpc": "2.0", "method": "test", "id": 1}
        result = await validator._make_concurrent_request(
            "http://localhost:8001/jsonrpc", request
        )

        assert result is False


if __name__ == "__main__":
    pytest.main([__file__])
