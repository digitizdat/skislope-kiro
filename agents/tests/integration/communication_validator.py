"""
Cross-System Communication Validator for CORS and protocol testing.

Validates cross-system communication including CORS configuration, JSON-RPC
protocol compliance, MCP protocol support, and network timeout/retry mechanisms.
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse
import socket

import structlog
import aiohttp
from aiohttp import ClientTimeout, ClientError

from agents.tests.integration.models import (
    TestError, TestResult, TestCategory, TestStatus, Severity, AgentHealthStatus
)
from agents.tests.integration.config import TestConfig, AgentConfig


logger = structlog.get_logger(__name__)


@dataclass
class CORSTestResult:
    """Result of CORS validation testing."""
    agent_name: str
    endpoint: str
    allowed_origins: List[str] = field(default_factory=list)
    allowed_methods: List[str] = field(default_factory=list)
    allowed_headers: List[str] = field(default_factory=list)
    supports_credentials: bool = False
    preflight_successful: bool = False
    cors_violations: List[str] = field(default_factory=list)
    is_valid: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "agent_name": self.agent_name,
            "endpoint": self.endpoint,
            "allowed_origins": self.allowed_origins,
            "allowed_methods": self.allowed_methods,
            "allowed_headers": self.allowed_headers,
            "supports_credentials": self.supports_credentials,
            "preflight_successful": self.preflight_successful,
            "cors_violations": self.cors_violations,
            "is_valid": self.is_valid
        }


@dataclass
class JSONRPCTestResult:
    """Result of JSON-RPC protocol validation."""
    agent_name: str
    endpoint: str
    protocol_version: str = "2.0"
    supported_methods: List[str] = field(default_factory=list)
    request_response_valid: bool = False
    error_handling_valid: bool = False
    batch_requests_supported: bool = False
    notification_handling_valid: bool = False
    protocol_violations: List[str] = field(default_factory=list)
    is_valid: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "agent_name": self.agent_name,
            "endpoint": self.endpoint,
            "protocol_version": self.protocol_version,
            "supported_methods": self.supported_methods,
            "request_response_valid": self.request_response_valid,
            "error_handling_valid": self.error_handling_valid,
            "batch_requests_supported": self.batch_requests_supported,
            "notification_handling_valid": self.notification_handling_valid,
            "protocol_violations": self.protocol_violations,
            "is_valid": self.is_valid
        }


@dataclass
class MCPTestResult:
    """Result of MCP protocol compliance testing."""
    agent_name: str
    endpoint: str
    mcp_supported: bool = False
    protocol_version: Optional[str] = None
    available_tools: List[str] = field(default_factory=list)
    tool_discovery_valid: bool = False
    tool_execution_valid: bool = False
    mcp_violations: List[str] = field(default_factory=list)
    is_valid: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "agent_name": self.agent_name,
            "endpoint": self.endpoint,
            "mcp_supported": self.mcp_supported,
            "protocol_version": self.protocol_version,
            "available_tools": self.available_tools,
            "tool_discovery_valid": self.tool_discovery_valid,
            "tool_execution_valid": self.tool_execution_valid,
            "mcp_violations": self.mcp_violations,
            "is_valid": self.is_valid
        }


@dataclass
class NetworkTestResult:
    """Result of network timeout and retry mechanism testing."""
    agent_name: str
    endpoint: str
    timeout_handling_valid: bool = False
    retry_mechanism_valid: bool = False
    connection_pooling_valid: bool = False
    large_payload_handling: bool = False
    concurrent_request_handling: bool = False
    network_issues: List[str] = field(default_factory=list)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    is_valid: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "agent_name": self.agent_name,
            "endpoint": self.endpoint,
            "timeout_handling_valid": self.timeout_handling_valid,
            "retry_mechanism_valid": self.retry_mechanism_valid,
            "connection_pooling_valid": self.connection_pooling_valid,
            "large_payload_handling": self.large_payload_handling,
            "concurrent_request_handling": self.concurrent_request_handling,
            "network_issues": self.network_issues,
            "performance_metrics": self.performance_metrics,
            "is_valid": self.is_valid
        }


@dataclass
class CommunicationValidationResult:
    """Complete communication validation result."""
    agent_name: str
    cors_result: Optional[CORSTestResult] = None
    jsonrpc_result: Optional[JSONRPCTestResult] = None
    mcp_result: Optional[MCPTestResult] = None
    network_result: Optional[NetworkTestResult] = None
    overall_valid: bool = True
    validation_errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "agent_name": self.agent_name,
            "cors_result": self.cors_result.to_dict() if self.cors_result else None,
            "jsonrpc_result": self.jsonrpc_result.to_dict() if self.jsonrpc_result else None,
            "mcp_result": self.mcp_result.to_dict() if self.mcp_result else None,
            "network_result": self.network_result.to_dict() if self.network_result else None,
            "overall_valid": self.overall_valid,
            "validation_errors": self.validation_errors
        }


class CommunicationValidator:
    """
    Validates cross-system communication protocols and configurations.
    
    Tests CORS configuration, JSON-RPC protocol compliance, MCP protocol support,
    and network timeout/retry mechanisms.
    """
    
    def __init__(self, config: TestConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Expected origins for CORS testing
        self.expected_origins = [
            "http://localhost:3000",  # Development server
            "http://localhost:5173",  # Vite dev server
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            "https://localhost:3000",
            "https://localhost:5173"
        ]
        
        # Standard JSON-RPC error codes
        self.jsonrpc_error_codes = {
            -32700: "Parse error",
            -32600: "Invalid Request",
            -32601: "Method not found",
            -32602: "Invalid params",
            -32603: "Internal error"
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        timeout = ClientTimeout(
            total=self.config.timeouts.network_request,
            connect=self.config.timeouts.network_request // 2
        )
        self.session = aiohttp.ClientSession(timeout=timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def validate_all_communication(self) -> List[CommunicationValidationResult]:
        """
        Validate communication for all configured agents.
        
        Returns:
            List of communication validation results
        """
        results = []
        
        for agent_name, agent_config in self.config.agents.items():
            if not agent_config.enabled:
                logger.info(f"Skipping disabled agent: {agent_name}")
                continue
            
            try:
                result = await self.validate_agent_communication(agent_name, agent_config)
                results.append(result)
            except Exception as e:
                logger.error(
                    f"Failed to validate communication for agent {agent_name}",
                    error=str(e),
                    exc_info=True
                )
                # Create failed result
                result = CommunicationValidationResult(
                    agent_name=agent_name,
                    overall_valid=False,
                    validation_errors=[f"Communication validation failed: {str(e)}"]
                )
                results.append(result)
        
        return results
    
    async def validate_agent_communication(
        self, 
        agent_name: str, 
        agent_config: AgentConfig
    ) -> CommunicationValidationResult:
        """
        Validate communication for a specific agent.
        
        Args:
            agent_name: Name of the agent
            agent_config: Agent configuration
            
        Returns:
            Communication validation result
        """
        logger.info(f"Validating communication for agent: {agent_name}")
        
        result = CommunicationValidationResult(agent_name=agent_name)
        
        try:
            # Test CORS configuration
            result.cors_result = await self._test_cors_configuration(agent_name, agent_config)
            
            # Test JSON-RPC protocol compliance
            result.jsonrpc_result = await self._test_jsonrpc_protocol(agent_name, agent_config)
            
            # Test MCP protocol support
            result.mcp_result = await self._test_mcp_protocol(agent_name, agent_config)
            
            # Test network timeout and retry mechanisms
            result.network_result = await self._test_network_mechanisms(agent_name, agent_config)
            
            # Determine overall validity
            result.overall_valid = all([
                result.cors_result.is_valid if result.cors_result else True,
                result.jsonrpc_result.is_valid if result.jsonrpc_result else True,
                result.mcp_result.is_valid if result.mcp_result else True,
                result.network_result.is_valid if result.network_result else True
            ])
            
            logger.info(
                f"Communication validation completed for {agent_name}",
                overall_valid=result.overall_valid,
                cors_valid=result.cors_result.is_valid if result.cors_result else None,
                jsonrpc_valid=result.jsonrpc_result.is_valid if result.jsonrpc_result else None,
                mcp_valid=result.mcp_result.is_valid if result.mcp_result else None,
                network_valid=result.network_result.is_valid if result.network_result else None
            )
            
        except Exception as e:
            logger.error(
                f"Communication validation failed for {agent_name}",
                error=str(e),
                exc_info=True
            )
            result.overall_valid = False
            result.validation_errors.append(f"Validation error: {str(e)}")
        
        return result
    
    async def _test_cors_configuration(
        self, 
        agent_name: str, 
        agent_config: AgentConfig
    ) -> CORSTestResult:
        """
        Test CORS configuration for cross-origin requests.
        
        Args:
            agent_name: Name of the agent
            agent_config: Agent configuration
            
        Returns:
            CORS test result
        """
        endpoint = f"http://{agent_config.host}:{agent_config.port}/jsonrpc"
        result = CORSTestResult(agent_name=agent_name, endpoint=endpoint)
        
        try:
            # Test 1: Preflight request (OPTIONS)
            for origin in self.expected_origins:
                headers = {
                    "Origin": origin,
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "Content-Type"
                }
                
                async with self.session.options(endpoint, headers=headers) as response:
                    if response.status == 200:
                        result.preflight_successful = True
                        
                        # Check CORS headers
                        cors_origin = response.headers.get("Access-Control-Allow-Origin")
                        if cors_origin:
                            if cors_origin == "*" or cors_origin == origin:
                                result.allowed_origins.append(origin)
                            else:
                                result.cors_violations.append(
                                    f"Origin {origin} not allowed, got: {cors_origin}"
                                )
                        else:
                            result.cors_violations.append(
                                f"No Access-Control-Allow-Origin header for origin: {origin}"
                            )
                        
                        # Check allowed methods
                        allowed_methods = response.headers.get("Access-Control-Allow-Methods", "")
                        if "POST" not in allowed_methods:
                            result.cors_violations.append(
                                f"POST method not allowed, got: {allowed_methods}"
                            )
                        else:
                            result.allowed_methods = allowed_methods.split(", ")
                        
                        # Check allowed headers
                        allowed_headers = response.headers.get("Access-Control-Allow-Headers", "")
                        if "Content-Type" not in allowed_headers:
                            result.cors_violations.append(
                                f"Content-Type header not allowed, got: {allowed_headers}"
                            )
                        else:
                            result.allowed_headers = allowed_headers.split(", ")
                        
                        # Check credentials support
                        credentials = response.headers.get("Access-Control-Allow-Credentials")
                        result.supports_credentials = credentials == "true"
                        
                        break  # Success with at least one origin
                    else:
                        result.cors_violations.append(
                            f"Preflight failed for origin {origin}: HTTP {response.status}"
                        )
            
            # Test 2: Actual CORS request
            if result.allowed_origins:
                test_origin = result.allowed_origins[0]
                headers = {
                    "Origin": test_origin,
                    "Content-Type": "application/json"
                }
                
                test_request = {
                    "jsonrpc": "2.0",
                    "method": "healthCheck",
                    "params": {},
                    "id": 1
                }
                
                async with self.session.post(
                    endpoint, 
                    json=test_request, 
                    headers=headers
                ) as response:
                    cors_origin = response.headers.get("Access-Control-Allow-Origin")
                    if not cors_origin or (cors_origin != "*" and cors_origin != test_origin):
                        result.cors_violations.append(
                            f"Actual request CORS header mismatch: {cors_origin}"
                        )
            
            result.is_valid = len(result.cors_violations) == 0 and result.preflight_successful
            
        except Exception as e:
            result.cors_violations.append(f"CORS test failed: {str(e)}")
            result.is_valid = False
        
        return result
    
    async def _test_jsonrpc_protocol(
        self, 
        agent_name: str, 
        agent_config: AgentConfig
    ) -> JSONRPCTestResult:
        """
        Test JSON-RPC protocol compliance.
        
        Args:
            agent_name: Name of the agent
            agent_config: Agent configuration
            
        Returns:
            JSON-RPC test result
        """
        endpoint = f"http://{agent_config.host}:{agent_config.port}/jsonrpc"
        result = JSONRPCTestResult(agent_name=agent_name, endpoint=endpoint)
        
        try:
            # Test 1: Valid request/response cycle
            valid_request = {
                "jsonrpc": "2.0",
                "method": "healthCheck",
                "params": {},
                "id": 1
            }
            
            async with self.session.post(endpoint, json=valid_request) as response:
                if response.status == 200:
                    response_data = await response.json()
                    if self._validate_jsonrpc_response(response_data, valid_request["id"]):
                        result.request_response_valid = True
                        if "result" in response_data:
                            result.supported_methods.append("healthCheck")
                    else:
                        result.protocol_violations.append(
                            "Valid request did not return valid JSON-RPC response"
                        )
                else:
                    result.protocol_violations.append(
                        f"Valid request returned HTTP {response.status}"
                    )
            
            # Test 2: Error handling
            error_tests = [
                # Parse error
                {
                    "data": "invalid json",
                    "expected_code": -32700,
                    "description": "Parse error"
                },
                # Invalid request
                {
                    "data": {"jsonrpc": "2.0"},
                    "expected_code": -32600,
                    "description": "Invalid request (missing method)"
                },
                # Method not found
                {
                    "data": {
                        "jsonrpc": "2.0",
                        "method": "nonexistent_method_12345",
                        "params": {},
                        "id": 2
                    },
                    "expected_code": -32601,
                    "description": "Method not found"
                }
            ]
            
            error_handling_valid = True
            for test in error_tests:
                try:
                    if isinstance(test["data"], str):
                        # Send invalid JSON
                        async with self.session.post(
                            endpoint,
                            data=test["data"],
                            headers={"Content-Type": "application/json"}
                        ) as response:
                            if response.status == 200:
                                response_data = await response.json()
                                if not self._validate_jsonrpc_error(
                                    response_data, 
                                    test["expected_code"]
                                ):
                                    result.protocol_violations.append(
                                        f"{test['description']}: Invalid error response"
                                    )
                                    error_handling_valid = False
                            else:
                                result.protocol_violations.append(
                                    f"{test['description']}: Should return 200 with JSON-RPC error"
                                )
                                error_handling_valid = False
                    else:
                        # Send invalid JSON-RPC
                        async with self.session.post(endpoint, json=test["data"]) as response:
                            if response.status == 200:
                                response_data = await response.json()
                                if not self._validate_jsonrpc_error(
                                    response_data, 
                                    test["expected_code"]
                                ):
                                    result.protocol_violations.append(
                                        f"{test['description']}: Invalid error response"
                                    )
                                    error_handling_valid = False
                            else:
                                result.protocol_violations.append(
                                    f"{test['description']}: Should return 200 with JSON-RPC error"
                                )
                                error_handling_valid = False
                except Exception as e:
                    result.protocol_violations.append(
                        f"{test['description']} test failed: {str(e)}"
                    )
                    error_handling_valid = False
            
            result.error_handling_valid = error_handling_valid
            
            # Test 3: Batch requests (optional)
            batch_request = [
                {
                    "jsonrpc": "2.0",
                    "method": "healthCheck",
                    "params": {},
                    "id": 1
                },
                {
                    "jsonrpc": "2.0",
                    "method": "healthCheck",
                    "params": {},
                    "id": 2
                }
            ]
            
            try:
                async with self.session.post(endpoint, json=batch_request) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        if isinstance(response_data, list) and len(response_data) == 2:
                            result.batch_requests_supported = True
                        else:
                            # Batch requests not supported, but that's okay
                            result.batch_requests_supported = False
                    else:
                        result.batch_requests_supported = False
            except Exception:
                result.batch_requests_supported = False
            
            # Test 4: Notification handling (requests without id)
            notification_request = {
                "jsonrpc": "2.0",
                "method": "healthCheck",
                "params": {}
                # No id field - this is a notification
            }
            
            try:
                async with self.session.post(endpoint, json=notification_request) as response:
                    # Notifications should not return a response
                    if response.status == 200:
                        response_text = await response.text()
                        if not response_text or response_text.strip() == "":
                            result.notification_handling_valid = True
                        else:
                            # Some implementations might return empty JSON object
                            try:
                                response_data = json.loads(response_text)
                                if response_data == {} or response_data is None:
                                    result.notification_handling_valid = True
                                else:
                                    result.notification_handling_valid = False
                            except json.JSONDecodeError:
                                result.notification_handling_valid = False
                    else:
                        result.notification_handling_valid = False
            except Exception:
                result.notification_handling_valid = False
            
            result.is_valid = (
                result.request_response_valid and 
                result.error_handling_valid
            )
            
        except Exception as e:
            result.protocol_violations.append(f"JSON-RPC protocol test failed: {str(e)}")
            result.is_valid = False
        
        return result
    
    async def _test_mcp_protocol(
        self, 
        agent_name: str, 
        agent_config: AgentConfig
    ) -> MCPTestResult:
        """
        Test MCP (Model Context Protocol) compliance.
        
        Args:
            agent_name: Name of the agent
            agent_config: Agent configuration
            
        Returns:
            MCP test result
        """
        # MCP typically runs on a different endpoint or protocol
        # For now, we'll test if the agent supports MCP-style tool discovery
        endpoint = f"http://{agent_config.host}:{agent_config.port}/mcp"
        result = MCPTestResult(agent_name=agent_name, endpoint=endpoint)
        
        try:
            # Test 1: Check if MCP endpoint exists
            async with self.session.get(endpoint) as response:
                if response.status == 200:
                    result.mcp_supported = True
                    response_data = await response.json()
                    
                    # Check for MCP protocol version
                    if "protocol_version" in response_data:
                        result.protocol_version = response_data["protocol_version"]
                    
                    # Check for available tools
                    if "tools" in response_data:
                        result.available_tools = response_data["tools"]
                        result.tool_discovery_valid = True
                else:
                    result.mcp_supported = False
                    result.mcp_violations.append(f"MCP endpoint not available: HTTP {response.status}")
            
            # Test 2: Tool execution (if tools are available)
            if result.available_tools:
                # Try to execute the first available tool
                test_tool = result.available_tools[0]
                tool_request = {
                    "tool": test_tool,
                    "parameters": {}
                }
                
                try:
                    async with self.session.post(
                        f"{endpoint}/execute", 
                        json=tool_request
                    ) as response:
                        if response.status == 200:
                            result.tool_execution_valid = True
                        else:
                            result.mcp_violations.append(
                                f"Tool execution failed: HTTP {response.status}"
                            )
                except Exception as e:
                    result.mcp_violations.append(f"Tool execution test failed: {str(e)}")
            
            result.is_valid = (
                not result.mcp_supported or  # If MCP not supported, that's okay
                (result.tool_discovery_valid and result.tool_execution_valid)
            )
            
        except Exception as e:
            # MCP support is optional, so failures here don't invalidate the agent
            result.mcp_supported = False
            result.mcp_violations.append(f"MCP test failed: {str(e)}")
            result.is_valid = True  # MCP is optional
        
        return result
    
    async def _test_network_mechanisms(
        self, 
        agent_name: str, 
        agent_config: AgentConfig
    ) -> NetworkTestResult:
        """
        Test network timeout and retry mechanisms.
        
        Args:
            agent_name: Name of the agent
            agent_config: Agent configuration
            
        Returns:
            Network test result
        """
        endpoint = f"http://{agent_config.host}:{agent_config.port}/jsonrpc"
        result = NetworkTestResult(agent_name=agent_name, endpoint=endpoint)
        
        try:
            # Test 1: Timeout handling
            start_time = time.time()
            timeout_session = aiohttp.ClientSession(
                timeout=ClientTimeout(total=1.0)  # Very short timeout
            )
            
            try:
                # Create a request that might take longer than timeout
                slow_request = {
                    "jsonrpc": "2.0",
                    "method": "healthCheck",
                    "params": {},
                    "id": 1
                }
                
                async with timeout_session.post(endpoint, json=slow_request) as response:
                    # If we get here, the request completed within timeout
                    result.timeout_handling_valid = True
                    result.performance_metrics["fast_response_time"] = time.time() - start_time
                    
            except asyncio.TimeoutError:
                # Timeout occurred - this is expected behavior
                result.timeout_handling_valid = True
                result.performance_metrics["timeout_duration"] = time.time() - start_time
            except Exception as e:
                result.network_issues.append(f"Timeout test failed: {str(e)}")
                result.timeout_handling_valid = False
            finally:
                await timeout_session.close()
            
            # Test 2: Retry mechanism (simulate by making multiple requests)
            retry_success_count = 0
            retry_attempts = 3
            
            for attempt in range(retry_attempts):
                try:
                    request = {
                        "jsonrpc": "2.0",
                        "method": "healthCheck",
                        "params": {},
                        "id": attempt + 1
                    }
                    
                    async with self.session.post(endpoint, json=request) as response:
                        if response.status == 200:
                            retry_success_count += 1
                        
                except Exception as e:
                    result.network_issues.append(f"Retry attempt {attempt + 1} failed: {str(e)}")
            
            result.retry_mechanism_valid = retry_success_count >= (retry_attempts * 0.7)  # 70% success rate
            result.performance_metrics["retry_success_rate"] = retry_success_count / retry_attempts
            
            # Test 3: Connection pooling (multiple concurrent requests)
            concurrent_requests = 5
            concurrent_tasks = []
            
            for i in range(concurrent_requests):
                request = {
                    "jsonrpc": "2.0",
                    "method": "healthCheck",
                    "params": {},
                    "id": i + 1
                }
                task = self._make_concurrent_request(endpoint, request)
                concurrent_tasks.append(task)
            
            start_time = time.time()
            concurrent_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
            concurrent_duration = time.time() - start_time
            
            successful_concurrent = sum(
                1 for r in concurrent_results 
                if not isinstance(r, Exception) and r
            )
            
            result.concurrent_request_handling = successful_concurrent >= (concurrent_requests * 0.8)
            result.performance_metrics["concurrent_success_rate"] = successful_concurrent / concurrent_requests
            result.performance_metrics["concurrent_duration"] = concurrent_duration
            
            # Test 4: Large payload handling
            large_payload_request = {
                "jsonrpc": "2.0",
                "method": "healthCheck",
                "params": {
                    "large_data": "x" * 10000  # 10KB of data
                },
                "id": 999
            }
            
            try:
                start_time = time.time()
                async with self.session.post(endpoint, json=large_payload_request) as response:
                    if response.status == 200:
                        result.large_payload_handling = True
                        result.performance_metrics["large_payload_response_time"] = time.time() - start_time
                    else:
                        result.network_issues.append(f"Large payload failed: HTTP {response.status}")
                        result.large_payload_handling = False
            except Exception as e:
                result.network_issues.append(f"Large payload test failed: {str(e)}")
                result.large_payload_handling = False
            
            result.is_valid = (
                result.timeout_handling_valid and
                result.retry_mechanism_valid and
                result.concurrent_request_handling and
                result.large_payload_handling
            )
            
        except Exception as e:
            result.network_issues.append(f"Network mechanism test failed: {str(e)}")
            result.is_valid = False
        
        return result
    
    async def _make_concurrent_request(self, endpoint: str, request: Dict[str, Any]) -> bool:
        """
        Make a concurrent request for connection pooling test.
        
        Args:
            endpoint: Agent endpoint
            request: JSON-RPC request
            
        Returns:
            True if request was successful
        """
        try:
            async with self.session.post(endpoint, json=request) as response:
                return response.status == 200
        except Exception:
            return False
    
    def _validate_jsonrpc_response(self, response_data: Dict[str, Any], expected_id: Any) -> bool:
        """
        Validate JSON-RPC response format.
        
        Args:
            response_data: Response data to validate
            expected_id: Expected request ID
            
        Returns:
            True if response is valid
        """
        # Must have jsonrpc field with value "2.0"
        if response_data.get("jsonrpc") != "2.0":
            return False
        
        # Must have either result or error, but not both
        has_result = "result" in response_data
        has_error = "error" in response_data
        
        if not (has_result ^ has_error):  # XOR
            return False
        
        # Must have correct id
        if response_data.get("id") != expected_id:
            return False
        
        return True
    
    def _validate_jsonrpc_error(self, response_data: Dict[str, Any], expected_code: int) -> bool:
        """
        Validate JSON-RPC error response.
        
        Args:
            response_data: Response data to validate
            expected_code: Expected error code
            
        Returns:
            True if error response is valid
        """
        if response_data.get("jsonrpc") != "2.0":
            return False
        
        if "error" not in response_data:
            return False
        
        error = response_data["error"]
        if not isinstance(error, dict):
            return False
        
        if error.get("code") != expected_code:
            return False
        
        if "message" not in error or not isinstance(error["message"], str):
            return False
        
        return True
    
    async def run_communication_tests(self) -> List[TestResult]:
        """
        Run all communication validation tests.
        
        Returns:
            List of test results
        """
        test_results = []
        
        try:
            validation_results = await self.validate_all_communication()
            
            for validation_result in validation_results:
                # Create test results for each validation aspect
                
                # CORS test
                if validation_result.cors_result:
                    cors_test = TestResult(
                        name=f"CORS Configuration - {validation_result.agent_name}",
                        category=TestCategory.COMMUNICATION,
                        status=TestStatus.RUNNING,
                        duration=0.0,
                        context=validation_result.cors_result.to_dict()
                    )
                    
                    if validation_result.cors_result.is_valid:
                        cors_test.mark_passed(
                            f"CORS configuration valid for {validation_result.agent_name}"
                        )
                    else:
                        cors_test.mark_failed(
                            TestError(
                                category="communication",
                                severity=Severity.HIGH,
                                message=f"CORS violations: {validation_result.cors_result.cors_violations}",
                                context=validation_result.cors_result.to_dict(),
                                suggested_fix="Configure CORS headers to allow frontend origins"
                            )
                        )
                    
                    test_results.append(cors_test)
                
                # JSON-RPC test
                if validation_result.jsonrpc_result:
                    jsonrpc_test = TestResult(
                        name=f"JSON-RPC Protocol - {validation_result.agent_name}",
                        category=TestCategory.COMMUNICATION,
                        status=TestStatus.RUNNING,
                        duration=0.0,
                        context=validation_result.jsonrpc_result.to_dict()
                    )
                    
                    if validation_result.jsonrpc_result.is_valid:
                        jsonrpc_test.mark_passed(
                            f"JSON-RPC protocol compliance valid for {validation_result.agent_name}"
                        )
                    else:
                        jsonrpc_test.mark_failed(
                            TestError(
                                category="communication",
                                severity=Severity.HIGH,
                                message=f"Protocol violations: {validation_result.jsonrpc_result.protocol_violations}",
                                context=validation_result.jsonrpc_result.to_dict(),
                                suggested_fix="Fix JSON-RPC protocol compliance issues"
                            )
                        )
                    
                    test_results.append(jsonrpc_test)
                
                # MCP test
                if validation_result.mcp_result:
                    mcp_test = TestResult(
                        name=f"MCP Protocol - {validation_result.agent_name}",
                        category=TestCategory.COMMUNICATION,
                        status=TestStatus.RUNNING,
                        duration=0.0,
                        context=validation_result.mcp_result.to_dict()
                    )
                    
                    if validation_result.mcp_result.is_valid:
                        mcp_test.mark_passed(
                            f"MCP protocol support valid for {validation_result.agent_name}"
                        )
                    else:
                        mcp_test.mark_failed(
                            TestError(
                                category="communication",
                                severity=Severity.MEDIUM,  # MCP is optional
                                message=f"MCP violations: {validation_result.mcp_result.mcp_violations}",
                                context=validation_result.mcp_result.to_dict(),
                                suggested_fix="Fix MCP protocol implementation or disable MCP support"
                            )
                        )
                    
                    test_results.append(mcp_test)
                
                # Network test
                if validation_result.network_result:
                    network_test = TestResult(
                        name=f"Network Mechanisms - {validation_result.agent_name}",
                        category=TestCategory.COMMUNICATION,
                        status=TestStatus.RUNNING,
                        duration=0.0,
                        context=validation_result.network_result.to_dict()
                    )
                    
                    if validation_result.network_result.is_valid:
                        network_test.mark_passed(
                            f"Network timeout and retry mechanisms valid for {validation_result.agent_name}"
                        )
                    else:
                        network_test.mark_failed(
                            TestError(
                                category="communication",
                                severity=Severity.HIGH,
                                message=f"Network issues: {validation_result.network_result.network_issues}",
                                context=validation_result.network_result.to_dict(),
                                suggested_fix="Fix network timeout handling and retry mechanisms"
                            )
                        )
                    
                    test_results.append(network_test)
        
        except Exception as e:
            # Create failed test result for overall validation
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