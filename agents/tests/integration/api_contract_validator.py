"""
API Contract Validator for method verification.

Validates API contracts between frontend and backend agents by discovering
agent methods via reflection, comparing method signatures, and ensuring
JSON-RPC protocol compliance.
"""

import asyncio
import inspect
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple, Union, Callable
import importlib
import sys
from pathlib import Path

import structlog
import aiohttp

from agents.tests.integration.models import (
    TestError, TestResult, TestCategory, TestStatus, Severity, AgentHealthStatus
)
from agents.tests.integration.config import TestConfig, AgentConfig


logger = structlog.get_logger(__name__)


@dataclass
class MethodSignature:
    """Represents a method signature for comparison."""
    name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    return_type: Optional[str] = None
    is_async: bool = False
    docstring: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "parameters": self.parameters,
            "return_type": self.return_type,
            "is_async": self.is_async,
            "docstring": self.docstring
        }


@dataclass
class ContractValidationResult:
    """Result of contract validation between frontend and backend."""
    agent_name: str
    frontend_methods: List[MethodSignature] = field(default_factory=list)
    backend_methods: List[MethodSignature] = field(default_factory=list)
    missing_backend_methods: List[str] = field(default_factory=list)
    missing_frontend_methods: List[str] = field(default_factory=list)
    signature_mismatches: List[Dict[str, Any]] = field(default_factory=list)
    protocol_violations: List[str] = field(default_factory=list)
    is_valid: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "agent_name": self.agent_name,
            "frontend_methods": [m.to_dict() for m in self.frontend_methods],
            "backend_methods": [m.to_dict() for m in self.backend_methods],
            "missing_backend_methods": self.missing_backend_methods,
            "missing_frontend_methods": self.missing_frontend_methods,
            "signature_mismatches": self.signature_mismatches,
            "protocol_violations": self.protocol_violations,
            "is_valid": self.is_valid
        }


class APIContractValidator:
    """
    Validates API contracts between frontend and backend agents.
    
    Discovers agent methods via reflection, compares method signatures,
    and validates JSON-RPC protocol compliance.
    """
    
    def __init__(self, config: Optional[TestConfig] = None):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Frontend method mappings (based on AgentClient.ts analysis)
        self.frontend_method_mappings = {
            "hill_metrics": {
                "getHillMetrics": {
                    "parameters": {
                        "bounds": {"type": "object", "required": True},
                        "grid_size": {"type": "string", "default": "64x64"},
                        "include_surface_classification": {"type": "boolean", "default": True},
                        "include_safety_zones": {"type": "boolean", "default": False},
                        "include_course_markers": {"type": "boolean", "default": False}
                    },
                    "return_type": "HillMetricsResponse"
                },
                "getElevationProfile": {
                    "parameters": {
                        "start_lat": {"type": "number", "required": True},
                        "start_lng": {"type": "number", "required": True},
                        "end_lat": {"type": "number", "required": True},
                        "end_lng": {"type": "number", "required": True},
                        "num_points": {"type": "integer", "default": 100}
                    },
                    "return_type": "ElevationProfileResponse"
                }
            },
            "weather": {
                "getWeatherData": {
                    "parameters": {
                        "area": {"type": "object", "required": True},
                        "timestamp": {"type": "string", "required": False},
                        "include_forecast": {"type": "boolean", "default": False},
                        "forecast_days": {"type": "integer", "default": 7},
                        "include_historical": {"type": "boolean", "default": False},
                        "historical_days": {"type": "integer", "default": 30}
                    },
                    "return_type": "WeatherResponse"
                },
                "getSkiConditions": {
                    "parameters": {
                        "latitude": {"type": "number", "required": True},
                        "longitude": {"type": "number", "required": True},
                        "elevation_m": {"type": "number", "required": False}
                    },
                    "return_type": "SkiConditionsResponse"
                },
                "getWeatherAlerts": {
                    "parameters": {
                        "latitude": {"type": "number", "required": True},
                        "longitude": {"type": "number", "required": True}
                    },
                    "return_type": "WeatherAlertsResponse"
                }
            },
            "equipment": {
                "getEquipmentData": {
                    "parameters": {
                        "area": {"type": "object", "required": True},
                        "include_status": {"type": "boolean", "default": True},
                        "equipment_types": {"type": "array", "required": False},
                        "include_lifts": {"type": "boolean", "default": True},
                        "include_trails": {"type": "boolean", "default": True},
                        "include_facilities": {"type": "boolean", "default": True},
                        "include_safety_equipment": {"type": "boolean", "default": True},
                        "operational_only": {"type": "boolean", "default": False},
                        "open_trails_only": {"type": "boolean", "default": False}
                    },
                    "return_type": "EquipmentResponse"
                },
                "getLiftStatus": {
                    "parameters": {
                        "lift_ids": {"type": "array", "required": False},
                        "bounds": {"type": "object", "required": False}
                    },
                    "return_type": "LiftStatusResponse"
                },
                "getTrailConditions": {
                    "parameters": {
                        "trail_ids": {"type": "array", "required": False},
                        "bounds": {"type": "object", "required": False},
                        "difficulty_filter": {"type": "string", "required": False}
                    },
                    "return_type": "TrailConditionsResponse"
                },
                "getFacilities": {
                    "parameters": {
                        "bounds": {"type": "object", "required": True},
                        "facility_types": {"type": "array", "required": False},
                        "open_only": {"type": "boolean", "default": False}
                    },
                    "return_type": "FacilitiesResponse"
                }
            }
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        timeout = 30  # Default timeout
        if self.config and hasattr(self.config, 'timeouts'):
            timeout = self.config.timeouts.network_request
            
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=timeout)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def validate_all_contracts(self) -> List[ContractValidationResult]:
        """
        Validate contracts for all configured agents.
        
        Returns:
            List of validation results for each agent
        """
        if not self.config:
            raise ValueError("Config required for validate_all_contracts")
            
        results = []
        
        for agent_name, agent_config in self.config.agents.items():
            if not agent_config.enabled:
                logger.info(f"Skipping disabled agent: {agent_name}")
                continue
            
            try:
                result = await self.validate_agent_contract(agent_name, agent_config)
                results.append(result)
            except Exception as e:
                logger.error(
                    f"Failed to validate contract for agent {agent_name}",
                    error=str(e),
                    exc_info=True
                )
                # Create failed result
                result = ContractValidationResult(
                    agent_name=agent_name,
                    is_valid=False,
                    protocol_violations=[f"Contract validation failed: {str(e)}"]
                )
                results.append(result)
        
        return results
    
    async def validate_agent_contract(
        self, 
        agent_name: str, 
        agent_config: AgentConfig
    ) -> ContractValidationResult:
        """
        Validate contract for a specific agent.
        
        Args:
            agent_name: Name of the agent
            agent_config: Agent configuration
            
        Returns:
            Contract validation result
        """
        logger.info(f"Validating contract for agent: {agent_name}")
        
        result = ContractValidationResult(agent_name=agent_name)
        
        try:
            # Discover backend methods via reflection
            result.backend_methods = await self._discover_backend_methods(agent_name)
            
            # Get frontend methods from mapping
            result.frontend_methods = self._get_frontend_methods(agent_name)
            
            # Compare methods
            self._compare_methods(result)
            
            # Validate JSON-RPC protocol compliance
            await self._validate_jsonrpc_compliance(agent_name, agent_config, result)
            
            # Determine overall validity
            result.is_valid = (
                len(result.missing_backend_methods) == 0 and
                len(result.signature_mismatches) == 0 and
                len(result.protocol_violations) == 0
            )
            
            logger.info(
                f"Contract validation completed for {agent_name}",
                is_valid=result.is_valid,
                backend_methods=len(result.backend_methods),
                frontend_methods=len(result.frontend_methods),
                missing_backend=len(result.missing_backend_methods),
                signature_mismatches=len(result.signature_mismatches),
                protocol_violations=len(result.protocol_violations)
            )
            
        except Exception as e:
            logger.error(
                f"Contract validation failed for {agent_name}",
                error=str(e),
                exc_info=True
            )
            result.is_valid = False
            result.protocol_violations.append(f"Validation error: {str(e)}")
        
        return result
    
    async def _discover_backend_methods(self, agent_name: str) -> List[MethodSignature]:
        """
        Discover backend methods via reflection.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            List of discovered method signatures
        """
        methods = []
        
        try:
            # Import the agent server module
            module_name = f"agents.{agent_name}.server"
            
            # Add project root to Python path if not already there
            project_root = Path(__file__).parent.parent.parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))
            
            module = importlib.import_module(module_name)
            
            # Look for registered JSON-RPC methods
            if hasattr(module, 'jsonrpc_handler') and hasattr(module.jsonrpc_handler, 'methods'):
                for method_name, handler in module.jsonrpc_handler.methods.items():
                    signature = self._extract_method_signature(method_name, handler)
                    methods.append(signature)
            else:
                # Fallback: scan module for async functions that look like RPC methods
                for name, obj in inspect.getmembers(module):
                    if (inspect.iscoroutinefunction(obj) and 
                        not name.startswith('_') and 
                        name not in ['startup_event', 'shutdown_event', 'health_check', 'detailed_health_check']):
                        signature = self._extract_method_signature(name, obj)
                        methods.append(signature)
            
            logger.info(f"Discovered {len(methods)} backend methods for {agent_name}")
            
        except ImportError as e:
            logger.error(f"Failed to import agent module {agent_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to discover methods for {agent_name}: {e}")
            raise
        
        return methods
    
    def _extract_method_signature(self, method_name: str, handler: Callable) -> MethodSignature:
        """
        Extract method signature from a callable.
        
        Args:
            method_name: Name of the method
            handler: Method handler function
            
        Returns:
            Method signature
        """
        sig = inspect.signature(handler)
        parameters = {}
        
        for param_name, param in sig.parameters.items():
            param_info = {
                "type": self._get_type_string(param.annotation),
                "required": param.default == inspect.Parameter.empty,
                "default": param.default if param.default != inspect.Parameter.empty else None
            }
            parameters[param_name] = param_info
        
        return MethodSignature(
            name=method_name,
            parameters=parameters,
            return_type=self._get_type_string(sig.return_annotation),
            is_async=inspect.iscoroutinefunction(handler),
            docstring=inspect.getdoc(handler)
        )
    
    def _get_type_string(self, annotation: Any) -> str:
        """
        Convert type annotation to string representation.
        
        Args:
            annotation: Type annotation
            
        Returns:
            String representation of the type
        """
        if annotation == inspect.Parameter.empty:
            return "Any"
        
        if hasattr(annotation, '__name__'):
            return annotation.__name__
        
        return str(annotation)
    
    def _get_frontend_methods(self, agent_name: str) -> List[MethodSignature]:
        """
        Get frontend methods from predefined mapping.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            List of frontend method signatures
        """
        methods = []
        
        if agent_name in self.frontend_method_mappings:
            for method_name, method_info in self.frontend_method_mappings[agent_name].items():
                signature = MethodSignature(
                    name=method_name,
                    parameters=method_info["parameters"],
                    return_type=method_info["return_type"],
                    is_async=True  # All frontend calls are async
                )
                methods.append(signature)
        
        return methods
    
    def _compare_methods(self, result: ContractValidationResult) -> None:
        """
        Compare frontend and backend methods to find mismatches.
        
        Args:
            result: Contract validation result to update
        """
        frontend_method_names = {m.name for m in result.frontend_methods}
        backend_method_names = {m.name for m in result.backend_methods}
        
        # Find missing methods
        result.missing_backend_methods = list(frontend_method_names - backend_method_names)
        result.missing_frontend_methods = list(backend_method_names - frontend_method_names)
        
        # Compare signatures for common methods
        common_methods = frontend_method_names & backend_method_names
        
        for method_name in common_methods:
            frontend_method = next(m for m in result.frontend_methods if m.name == method_name)
            backend_method = next(m for m in result.backend_methods if m.name == method_name)
            
            mismatch = self._compare_method_signatures(frontend_method, backend_method)
            if mismatch:
                result.signature_mismatches.append(mismatch)
    
    def _compare_method_signatures(
        self, 
        frontend_method: MethodSignature, 
        backend_method: MethodSignature
    ) -> Optional[Dict[str, Any]]:
        """
        Compare two method signatures for compatibility.
        
        Args:
            frontend_method: Frontend method signature
            backend_method: Backend method signature
            
        Returns:
            Mismatch information if signatures are incompatible, None otherwise
        """
        mismatches = []
        
        # Compare parameters
        frontend_params = set(frontend_method.parameters.keys())
        backend_params = set(backend_method.parameters.keys())
        
        missing_backend_params = frontend_params - backend_params
        extra_backend_params = backend_params - frontend_params
        
        if missing_backend_params:
            mismatches.append(f"Missing backend parameters: {missing_backend_params}")
        
        if extra_backend_params:
            # Check if extra parameters have defaults
            extra_required = []
            for param in extra_backend_params:
                if backend_method.parameters[param].get("required", True):
                    extra_required.append(param)
            
            if extra_required:
                mismatches.append(f"Extra required backend parameters: {extra_required}")
        
        # Compare parameter types for common parameters
        common_params = frontend_params & backend_params
        for param in common_params:
            frontend_param = frontend_method.parameters[param]
            backend_param = backend_method.parameters[param]
            
            # Type compatibility check (simplified)
            if not self._are_types_compatible(
                frontend_param.get("type"), 
                backend_param.get("type")
            ):
                mismatches.append(
                    f"Parameter '{param}' type mismatch: "
                    f"frontend={frontend_param.get('type')}, "
                    f"backend={backend_param.get('type')}"
                )
        
        if mismatches:
            return {
                "method": frontend_method.name,
                "mismatches": mismatches,
                "frontend_signature": frontend_method.to_dict(),
                "backend_signature": backend_method.to_dict()
            }
        
        return None
    
    def _are_types_compatible(self, frontend_type: Any, backend_type: Any) -> bool:
        """
        Check if frontend and backend types are compatible.
        
        Args:
            frontend_type: Frontend type specification
            backend_type: Backend type specification
            
        Returns:
            True if types are compatible
        """
        # Simplified type compatibility check
        # In a real implementation, this would be more sophisticated
        
        if frontend_type == backend_type:
            return True
        
        # Handle common type mappings
        type_mappings = {
            "string": ["str", "String"],
            "number": ["float", "int", "Float", "Int"],
            "integer": ["int", "Int"],
            "boolean": ["bool", "Bool"],
            "object": ["dict", "Dict", "Any"],
            "array": ["list", "List"]
        }
        
        for frontend_key, backend_values in type_mappings.items():
            if frontend_type == frontend_key and backend_type in backend_values:
                return True
            if backend_type == frontend_key and frontend_type in backend_values:
                return True
        
        # Default to compatible for unknown types
        return True
    
    async def _validate_jsonrpc_compliance(
        self, 
        agent_name: str, 
        agent_config: AgentConfig, 
        result: ContractValidationResult
    ) -> None:
        """
        Validate JSON-RPC protocol compliance.
        
        Args:
            agent_name: Name of the agent
            agent_config: Agent configuration
            result: Contract validation result to update
        """
        if not self.session:
            result.protocol_violations.append("No HTTP session available for protocol testing")
            return
        
        endpoint = f"http://{agent_config.host}:{agent_config.port}/jsonrpc"
        
        try:
            # Test 1: Valid JSON-RPC request
            valid_request = {
                "jsonrpc": "2.0",
                "method": "healthCheck" if "healthCheck" in [m.name for m in result.backend_methods] else "nonexistent_method",
                "params": {},
                "id": 1
            }
            
            async with self.session.post(endpoint, json=valid_request) as response:
                if response.status != 200:
                    result.protocol_violations.append(
                        f"Invalid HTTP status for valid JSON-RPC request: {response.status}"
                    )
                else:
                    response_data = await response.json()
                    if not self._is_valid_jsonrpc_response(response_data):
                        result.protocol_violations.append(
                            "Response does not conform to JSON-RPC 2.0 specification"
                        )
            
            # Test 2: Invalid JSON-RPC request (should return parse error)
            invalid_request = "invalid json"
            
            async with self.session.post(
                endpoint, 
                data=invalid_request,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    response_data = await response.json()
                    if (not response_data.get("error") or 
                        response_data["error"].get("code") != -32700):
                        result.protocol_violations.append(
                            "Invalid JSON should return parse error (-32700)"
                        )
                else:
                    result.protocol_violations.append(
                        "Invalid JSON should return 200 with JSON-RPC error, not HTTP error"
                    )
            
            # Test 3: Method not found (should return method not found error)
            not_found_request = {
                "jsonrpc": "2.0",
                "method": "definitely_nonexistent_method_12345",
                "params": {},
                "id": 2
            }
            
            async with self.session.post(endpoint, json=not_found_request) as response:
                if response.status == 200:
                    response_data = await response.json()
                    if (not response_data.get("error") or 
                        response_data["error"].get("code") != -32601):
                        result.protocol_violations.append(
                            "Nonexistent method should return method not found error (-32601)"
                        )
                else:
                    result.protocol_violations.append(
                        "Method not found should return 200 with JSON-RPC error"
                    )
            
        except Exception as e:
            result.protocol_violations.append(f"Protocol compliance test failed: {str(e)}")
    
    def _is_valid_jsonrpc_response(self, response_data: Dict[str, Any]) -> bool:
        """
        Check if response conforms to JSON-RPC 2.0 specification.
        
        Args:
            response_data: Response data to validate
            
        Returns:
            True if response is valid JSON-RPC 2.0
        """
        # Must have jsonrpc field with value "2.0"
        if response_data.get("jsonrpc") != "2.0":
            return False
        
        # Must have either result or error, but not both
        has_result = "result" in response_data
        has_error = "error" in response_data
        
        if not (has_result ^ has_error):  # XOR - exactly one should be true
            return False
        
        # Must have id field
        if "id" not in response_data:
            return False
        
        # If error, must have code and message
        if has_error:
            error = response_data["error"]
            if not isinstance(error, dict):
                return False
            if "code" not in error or "message" not in error:
                return False
            if not isinstance(error["code"], int):
                return False
            if not isinstance(error["message"], str):
                return False
        
        return True
    
    async def run_contract_tests(self) -> List[TestResult]:
        """
        Run all contract validation tests.
        
        Returns:
            List of test results
        """
        test_results = []
        
        try:
            validation_results = await self.validate_all_contracts()
            
            for validation_result in validation_results:
                # Create test result for each agent
                test_result = TestResult(
                    name=f"API Contract Validation - {validation_result.agent_name}",
                    category=TestCategory.API_CONTRACTS,
                    status=TestStatus.RUNNING,
                    duration=0.0,
                    context=validation_result.to_dict()
                )
                
                if validation_result.is_valid:
                    test_result.mark_passed(
                        f"All API contracts valid for {validation_result.agent_name}"
                    )
                else:
                    error_messages = []
                    if validation_result.missing_backend_methods:
                        error_messages.append(
                            f"Missing backend methods: {validation_result.missing_backend_methods}"
                        )
                    if validation_result.signature_mismatches:
                        error_messages.append(
                            f"Signature mismatches: {len(validation_result.signature_mismatches)}"
                        )
                    if validation_result.protocol_violations:
                        error_messages.append(
                            f"Protocol violations: {validation_result.protocol_violations}"
                        )
                    
                    test_result.mark_failed(
                        TestError(
                            category="api_contracts",
                            severity=Severity.HIGH,
                            message="; ".join(error_messages),
                            context=validation_result.to_dict(),
                            suggested_fix=self._generate_suggested_fix(validation_result)
                        )
                    )
                
                test_results.append(test_result)
        
        except Exception as e:
            # Create failed test result for overall validation
            test_result = TestResult(
                name="API Contract Validation - Overall",
                category=TestCategory.API_CONTRACTS,
                status=TestStatus.ERROR,
                duration=0.0
            )
            test_result.mark_failed(
                TestError.from_exception(e, "api_contracts", Severity.CRITICAL)
            )
            test_results.append(test_result)
        
        return test_results
    
    def discover_agent_methods_static(self, agent_file_path: str) -> List[MethodSignature]:
        """
        Discover agent methods via static analysis without starting the agent.
        
        This method is used for lightweight contract validation in pre-commit hooks
        and CI environments where starting full agents is not desired.
        
        Args:
            agent_file_path: Path to the agent server file
            
        Returns:
            List of discovered method signatures
        """
        methods = []
        
        try:
            # Convert relative path to absolute
            if not Path(agent_file_path).is_absolute():
                project_root = Path(__file__).parent.parent.parent.parent
                agent_file_path = str(project_root / agent_file_path)
            
            agent_path = Path(agent_file_path)
            if not agent_path.exists():
                raise FileNotFoundError(f"Agent file not found: {agent_file_path}")
            
            # Extract agent name from path
            agent_name = agent_path.parent.name
            
            # Import the agent module
            module_name = f"agents.{agent_name}.server"
            
            # Add project root to Python path if not already there
            project_root = Path(__file__).parent.parent.parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))
            
            module = importlib.import_module(module_name)
            
            # Look for registered JSON-RPC methods
            if hasattr(module, 'jsonrpc_handler') and hasattr(module.jsonrpc_handler, 'methods'):
                for method_name, handler in module.jsonrpc_handler.methods.items():
                    signature = self._extract_method_signature(method_name, handler)
                    methods.append(signature)
            else:
                # Fallback: scan module for async functions that look like RPC methods
                for name, obj in inspect.getmembers(module):
                    if (inspect.iscoroutinefunction(obj) and 
                        not name.startswith('_') and 
                        name not in ['startup_event', 'shutdown_event', 'health_check', 'detailed_health_check']):
                        signature = self._extract_method_signature(name, obj)
                        methods.append(signature)
            
            logger.info(f"Discovered {len(methods)} methods in {agent_file_path}")
            
        except ImportError as e:
            logger.error(f"Failed to import agent module from {agent_file_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to discover methods in {agent_file_path}: {e}")
            raise
        
        return methods
    
    def _generate_suggested_fix(self, validation_result: ContractValidationResult) -> str:
        """
        Generate suggested fix for contract validation issues.
        
        Args:
            validation_result: Validation result with issues
            
        Returns:
            Suggested fix message
        """
        suggestions = []
        
        if validation_result.missing_backend_methods:
            suggestions.append(
                f"Implement missing backend methods: {validation_result.missing_backend_methods}"
            )
        
        if validation_result.signature_mismatches:
            suggestions.append(
                "Review method signatures and ensure parameter compatibility between frontend and backend"
            )
        
        if validation_result.protocol_violations:
            suggestions.append(
                "Fix JSON-RPC protocol compliance issues in the backend implementation"
            )
        
        if not suggestions:
            suggestions.append("Review contract validation details for specific issues")
        
        return "; ".join(suggestions)