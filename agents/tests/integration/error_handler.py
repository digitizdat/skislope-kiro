"""
Comprehensive error handling and diagnostics for integration testing.

This module provides enhanced error handling capabilities including:
- Categorized error types with suggested fixes
- Diagnostic collection for failed tests
- Error recovery and retry strategies
- Comprehensive error reporting
"""

import asyncio
import logging
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Union, Type
import json
import sys
import os
from pathlib import Path

from .models import TestError, Severity, TestStatus, TestResult


class ErrorCategory(Enum):
    """Categorized error types for better diagnostics."""
    ENVIRONMENT = "environment"
    COMMUNICATION = "communication"
    API_CONTRACT = "api_contract"
    WORKFLOW = "workflow"
    PERFORMANCE = "performance"
    SECURITY = "security"
    INFRASTRUCTURE = "infrastructure"
    DATA = "data"
    TIMEOUT = "timeout"
    AUTHENTICATION = "authentication"


class ErrorType(Enum):
    """Specific error types within categories."""
    # Environment errors
    MISSING_DEPENDENCY = "missing_dependency"
    PACKAGE_MANAGER_CONFLICT = "package_manager_conflict"
    SSL_CONFIGURATION = "ssl_configuration"
    IMPORT_FAILURE = "import_failure"
    PYTHON_VERSION = "python_version"
    
    # Communication errors
    CORS_FAILURE = "cors_failure"
    NETWORK_TIMEOUT = "network_timeout"
    CONNECTION_REFUSED = "connection_refused"
    PROTOCOL_VIOLATION = "protocol_violation"
    SERIALIZATION_ERROR = "serialization_error"
    
    # API Contract errors
    METHOD_NOT_FOUND = "method_not_found"
    PARAMETER_MISMATCH = "parameter_mismatch"
    RESPONSE_FORMAT_ERROR = "response_format_error"
    VERSION_INCOMPATIBILITY = "version_incompatibility"
    
    # Workflow errors
    AGENT_STARTUP_FAILURE = "agent_startup_failure"
    CACHE_CORRUPTION = "cache_corruption"
    DATA_INCONSISTENCY = "data_inconsistency"
    WORKFLOW_INTERRUPTION = "workflow_interruption"
    
    # Performance errors
    RESPONSE_TIME_EXCEEDED = "response_time_exceeded"
    MEMORY_LIMIT_EXCEEDED = "memory_limit_exceeded"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    
    # Infrastructure errors
    SERVICE_UNAVAILABLE = "service_unavailable"
    CONFIGURATION_ERROR = "configuration_error"
    PERMISSION_DENIED = "permission_denied"


@dataclass
class DiagnosticInfo:
    """Diagnostic information collected during test failures."""
    timestamp: datetime = field(default_factory=datetime.now)
    system_info: Dict[str, Any] = field(default_factory=dict)
    environment_vars: Dict[str, str] = field(default_factory=dict)
    process_info: Dict[str, Any] = field(default_factory=dict)
    network_info: Dict[str, Any] = field(default_factory=dict)
    logs: List[str] = field(default_factory=list)
    stack_traces: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "system_info": self.system_info,
            "environment_vars": self.environment_vars,
            "process_info": self.process_info,
            "network_info": self.network_info,
            "logs": self.logs,
            "stack_traces": self.stack_traces,
            "context": self.context
        }


@dataclass
class RetryConfig:
    """Configuration for retry strategies."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_backoff: bool = True
    jitter: bool = True
    retry_on_exceptions: List[Type[Exception]] = field(default_factory=list)
    
    def __post_init__(self):
        """Set default retry exceptions if none provided."""
        if not self.retry_on_exceptions:
            self.retry_on_exceptions = [
                ConnectionError,
                TimeoutError,
                OSError,
                asyncio.TimeoutError
            ]


class EnhancedTestError(Exception):
    """Enhanced test error with comprehensive diagnostics."""
    
    def __init__(
        self,
        category: Union[str, ErrorCategory],
        error_type: Union[str, ErrorType],
        message: str,
        severity: Severity = Severity.HIGH,
        context: Optional[Dict[str, Any]] = None,
        suggested_fix: Optional[str] = None,
        diagnostics: Optional[DiagnosticInfo] = None,
        recovery_strategy: Optional[str] = None,
        related_errors: Optional[List['EnhancedTestError']] = None
    ):
        super().__init__(message)
        
        # Convert enums to strings
        self.category = category.value if isinstance(category, ErrorCategory) else category
        self.error_type = error_type.value if isinstance(error_type, ErrorType) else error_type
        self.message = message
        self.severity = severity
        self.context = context or {}
        self.suggested_fix = suggested_fix
        self.diagnostics = diagnostics
        self.recovery_strategy = recovery_strategy
        self.related_errors = related_errors or []
        self.timestamp = datetime.now()
        self.stack_trace = None
    
    @classmethod
    def from_exception(
        cls,
        exc: Exception,
        category: Union[str, ErrorCategory],
        error_type: Union[str, ErrorType],
        severity: Severity = Severity.HIGH,
        context: Optional[Dict[str, Any]] = None,
        diagnostics: Optional[DiagnosticInfo] = None
    ) -> 'EnhancedTestError':
        """Create enhanced error from exception with diagnostics."""
        error = cls(
            category=category,
            error_type=error_type,
            message=str(exc),
            severity=severity,
            context=context or {},
            diagnostics=diagnostics
        )
        error.stack_trace = traceback.format_exc()
        error.context["exception_type"] = type(exc).__name__
        
        # Add suggested fix based on exception type
        error.suggested_fix = ErrorFixSuggester.get_fix_for_exception(exc, category, error_type)
        
        return error
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with enhanced information."""
        base_dict = super().__dict__.copy()
        base_dict.update({
            "error_type": self.error_type,
            "recovery_strategy": self.recovery_strategy,
            "diagnostics": self.diagnostics.to_dict() if self.diagnostics else None,
            "related_errors": [err.to_dict() for err in self.related_errors]
        })
        return base_dict


class DiagnosticCollector:
    """Collects diagnostic information for failed tests."""
    
    @staticmethod
    def collect_system_info() -> Dict[str, Any]:
        """Collect system information."""
        return {
            "platform": sys.platform,
            "python_version": sys.version,
            "python_executable": sys.executable,
            "working_directory": os.getcwd(),
            "user": os.getenv("USER", "unknown"),
            "hostname": os.getenv("HOSTNAME", "unknown")
        }
    
    @staticmethod
    def collect_environment_vars() -> Dict[str, str]:
        """Collect relevant environment variables."""
        relevant_vars = [
            "PATH", "PYTHONPATH", "VIRTUAL_ENV", "UV_PYTHON",
            "NODE_ENV", "npm_config_registry", "UV_INDEX_URL",
            "SSL_CERT_FILE", "SSL_CERT_DIR", "REQUESTS_CA_BUNDLE"
        ]
        
        return {
            var: os.getenv(var, "")
            for var in relevant_vars
            if os.getenv(var)
        }
    
    @staticmethod
    def collect_process_info() -> Dict[str, Any]:
        """Collect process information."""
        try:
            import psutil
            process = psutil.Process()
            return {
                "pid": process.pid,
                "memory_info": process.memory_info()._asdict(),
                "cpu_percent": process.cpu_percent(),
                "open_files": len(process.open_files()),
                "connections": len(process.connections()),
                "threads": process.num_threads()
            }
        except ImportError:
            return {"error": "psutil not available"}
        except Exception as e:
            return {"error": f"Failed to collect process info: {e}"}
    
    @staticmethod
    def collect_network_info() -> Dict[str, Any]:
        """Collect network configuration information."""
        import socket
        
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            
            return {
                "hostname": hostname,
                "local_ip": local_ip,
                "dns_servers": DiagnosticCollector._get_dns_servers()
            }
        except Exception as e:
            return {"error": f"Failed to collect network info: {e}"}
    
    @staticmethod
    def _get_dns_servers() -> List[str]:
        """Get DNS server configuration."""
        try:
            if sys.platform == "darwin":  # macOS
                import subprocess
                result = subprocess.run(
                    ["scutil", "--dns"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                # Parse DNS servers from output (simplified)
                return ["system_configured"]
            else:
                # Try to read /etc/resolv.conf
                try:
                    with open("/etc/resolv.conf", "r") as f:
                        lines = f.readlines()
                        dns_servers = []
                        for line in lines:
                            if line.strip().startswith("nameserver"):
                                dns_servers.append(line.split()[1])
                        return dns_servers
                except:
                    return ["unknown"]
        except Exception:
            return ["error_collecting"]
    
    @staticmethod
    def collect_logs(log_files: Optional[List[str]] = None) -> List[str]:
        """Collect recent log entries."""
        if not log_files:
            log_files = [
                "logs/agents.log",
                "logs/integration_tests/test_results.log"
            ]
        
        logs = []
        for log_file in log_files:
            try:
                if os.path.exists(log_file):
                    with open(log_file, "r") as f:
                        # Get last 50 lines
                        lines = f.readlines()
                        recent_lines = lines[-50:] if len(lines) > 50 else lines
                        logs.extend([f"[{log_file}] {line.strip()}" for line in recent_lines])
            except Exception as e:
                logs.append(f"[{log_file}] Error reading log: {e}")
        
        return logs
    
    @classmethod
    def collect_full_diagnostics(
        self,
        context: Optional[Dict[str, Any]] = None,
        log_files: Optional[List[str]] = None
    ) -> DiagnosticInfo:
        """Collect comprehensive diagnostic information."""
        return DiagnosticInfo(
            system_info=self.collect_system_info(),
            environment_vars=self.collect_environment_vars(),
            process_info=self.collect_process_info(),
            network_info=self.collect_network_info(),
            logs=self.collect_logs(log_files),
            context=context or {}
        )


class ErrorFixSuggester:
    """Generates suggested fixes for common errors."""
    
    # Error pattern to fix mapping
    FIX_PATTERNS = {
        # Environment errors
        (ErrorCategory.ENVIRONMENT, ErrorType.MISSING_DEPENDENCY): {
            "patterns": ["No module named", "ModuleNotFoundError", "ImportError"],
            "fix": "Install missing dependency using 'uv add <package>' for Python or 'npm install <package>' for Node.js"
        },
        (ErrorCategory.ENVIRONMENT, ErrorType.PACKAGE_MANAGER_CONFLICT): {
            "patterns": ["pip", "mixed package managers"],
            "fix": "Use 'uv' exclusively for Python dependencies. Remove pip-installed packages and reinstall with 'uv add'"
        },
        (ErrorCategory.ENVIRONMENT, ErrorType.SSL_CONFIGURATION): {
            "patterns": ["SSL", "certificate", "CERTIFICATE_VERIFY_FAILED"],
            "fix": "Check SSL certificate configuration. Set SSL_CERT_FILE environment variable or update certificates"
        },
        
        # Communication errors
        (ErrorCategory.COMMUNICATION, ErrorType.CORS_FAILURE): {
            "patterns": ["CORS", "Access-Control-Allow-Origin"],
            "fix": "Configure CORS headers in agent servers to allow frontend origin"
        },
        (ErrorCategory.COMMUNICATION, ErrorType.CONNECTION_REFUSED): {
            "patterns": ["Connection refused", "ConnectionRefusedError"],
            "fix": "Ensure agent servers are running. Start agents with 'uv run python -m agents.<agent_name>'"
        },
        (ErrorCategory.COMMUNICATION, ErrorType.NETWORK_TIMEOUT): {
            "patterns": ["timeout", "TimeoutError"],
            "fix": "Increase timeout values or check network connectivity. Verify agent responsiveness"
        },
        
        # API Contract errors
        (ErrorCategory.API_CONTRACT, ErrorType.METHOD_NOT_FOUND): {
            "patterns": ["method not found", "Method not found"],
            "fix": "Verify API method exists in agent server. Check method name spelling and availability"
        },
        (ErrorCategory.API_CONTRACT, ErrorType.PARAMETER_MISMATCH): {
            "patterns": ["parameter", "argument", "TypeError"],
            "fix": "Check method parameter types and names match between frontend and backend"
        }
    }
    
    @classmethod
    def get_fix_for_exception(
        cls,
        exc: Exception,
        category: Union[str, ErrorCategory],
        error_type: Union[str, ErrorType]
    ) -> Optional[str]:
        """Get suggested fix for an exception."""
        exc_str = str(exc)
        exc_type = type(exc).__name__
        
        # Convert to enums if needed
        if isinstance(category, str):
            try:
                category = ErrorCategory(category)
            except ValueError:
                return None
        
        if isinstance(error_type, str):
            try:
                error_type = ErrorType(error_type)
            except ValueError:
                return None
        
        # Look for pattern match
        pattern_key = (category, error_type)
        if pattern_key in cls.FIX_PATTERNS:
            fix_info = cls.FIX_PATTERNS[pattern_key]
            patterns = fix_info["patterns"]
            
            # Check if any pattern matches
            for pattern in patterns:
                if pattern.lower() in exc_str.lower() or pattern.lower() in exc_type.lower():
                    return fix_info["fix"]
        
        # Generic fixes based on exception type
        return cls._get_generic_fix(exc)
    
    @classmethod
    def _get_generic_fix(cls, exc: Exception) -> Optional[str]:
        """Get generic fix based on exception type."""
        exc_type = type(exc).__name__
        
        generic_fixes = {
            "ModuleNotFoundError": "Install the missing module using the appropriate package manager",
            "ImportError": "Check that all dependencies are installed and importable",
            "ConnectionError": "Verify network connectivity and service availability",
            "TimeoutError": "Increase timeout values or check service responsiveness",
            "PermissionError": "Check file/directory permissions or run with appropriate privileges",
            "FileNotFoundError": "Ensure the required file exists at the specified path",
            "JSONDecodeError": "Verify JSON format and encoding of the data",
            "KeyError": "Check that the required key exists in the data structure",
            "AttributeError": "Verify that the object has the expected attribute or method"
        }
        
        return generic_fixes.get(exc_type)


class ErrorRecoveryManager:
    """Manages error recovery and retry strategies."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.recovery_strategies: Dict[str, Callable] = {}
        self.retry_configs: Dict[str, RetryConfig] = {}
    
    def register_recovery_strategy(
        self,
        error_pattern: str,
        strategy: Callable,
        retry_config: Optional[RetryConfig] = None
    ) -> None:
        """Register a recovery strategy for an error pattern."""
        self.recovery_strategies[error_pattern] = strategy
        if retry_config:
            self.retry_configs[error_pattern] = retry_config
    
    async def execute_with_recovery(
        self,
        func: Callable,
        *args,
        retry_config: Optional[RetryConfig] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """Execute function with error recovery and retry logic."""
        config = retry_config or RetryConfig()
        attempt = 0
        last_exception = None
        
        while attempt < config.max_attempts:
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
                    
            except Exception as exc:
                attempt += 1
                last_exception = exc
                
                self.logger.warning(
                    f"Attempt {attempt}/{config.max_attempts} failed: {exc}",
                    extra={"context": context}
                )
                
                # Check if we should retry this exception
                if not any(isinstance(exc, exc_type) for exc_type in config.retry_on_exceptions):
                    self.logger.error(f"Non-retryable exception: {type(exc).__name__}")
                    break
                
                # Try recovery strategy
                recovery_attempted = await self._attempt_recovery(exc, context)
                
                if attempt < config.max_attempts:
                    delay = self._calculate_delay(attempt, config)
                    self.logger.info(f"Retrying in {delay:.2f} seconds...")
                    await asyncio.sleep(delay)
        
        # All attempts failed
        if last_exception:
            # Collect diagnostics for the final failure
            diagnostics = DiagnosticCollector.collect_full_diagnostics(context)
            
            # Create enhanced error
            enhanced_error = EnhancedTestError.from_exception(
                last_exception,
                category=ErrorCategory.INFRASTRUCTURE,
                error_type=ErrorType.SERVICE_UNAVAILABLE,
                context=context,
                diagnostics=diagnostics
            )
            enhanced_error.recovery_strategy = "All retry attempts exhausted"
            
            raise enhanced_error
        
        raise RuntimeError("Unexpected error in retry logic")
    
    async def _attempt_recovery(
        self,
        exc: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Attempt to recover from an error."""
        exc_str = str(exc).lower()
        
        # Look for matching recovery strategy
        for pattern, strategy in self.recovery_strategies.items():
            if pattern.lower() in exc_str:
                try:
                    self.logger.info(f"Attempting recovery strategy for pattern: {pattern}")
                    if asyncio.iscoroutinefunction(strategy):
                        await strategy(exc, context)
                    else:
                        strategy(exc, context)
                    return True
                except Exception as recovery_exc:
                    self.logger.error(f"Recovery strategy failed: {recovery_exc}")
        
        return False
    
    def _calculate_delay(self, attempt: int, config: RetryConfig) -> float:
        """Calculate delay for retry attempt."""
        if config.exponential_backoff:
            delay = min(config.base_delay * (2 ** (attempt - 1)), config.max_delay)
        else:
            delay = config.base_delay
        
        if config.jitter:
            import random
            delay *= (0.5 + random.random() * 0.5)  # Add 0-50% jitter
        
        return delay


class IntegrationTestErrorHandler:
    """Main error handler for integration tests."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.recovery_manager = ErrorRecoveryManager(logger)
        self.error_history: List[EnhancedTestError] = []
        self.diagnostic_collector = DiagnosticCollector()
    
    def handle_test_error(
        self,
        exc: Exception,
        test_name: str,
        category: Union[str, ErrorCategory],
        error_type: Union[str, ErrorType],
        context: Optional[Dict[str, Any]] = None
    ) -> EnhancedTestError:
        """Handle a test error with comprehensive diagnostics."""
        # Collect diagnostics
        diagnostics = self.diagnostic_collector.collect_full_diagnostics(
            context={"test_name": test_name, **(context or {})}
        )
        
        # Create enhanced error
        enhanced_error = EnhancedTestError.from_exception(
            exc,
            category=category,
            error_type=error_type,
            context=context,
            diagnostics=diagnostics
        )
        
        # Add to history
        self.error_history.append(enhanced_error)
        
        # Log the error
        self.logger.error(
            f"Test error in {test_name}: {enhanced_error.message}",
            extra={
                "category": enhanced_error.category,
                "error_type": enhanced_error.error_type,
                "severity": enhanced_error.severity.value,
                "suggested_fix": enhanced_error.suggested_fix
            }
        )
        
        return enhanced_error
    
    def create_test_result_with_error(
        self,
        test_name: str,
        category: str,
        exc: Exception,
        error_category: Union[str, ErrorCategory],
        error_type: Union[str, ErrorType],
        context: Optional[Dict[str, Any]] = None
    ) -> TestResult:
        """Create a test result with enhanced error handling."""
        from .models import TestCategory
        
        # Convert category string to enum
        try:
            test_category = TestCategory(category)
        except ValueError:
            test_category = TestCategory.WORKFLOWS  # Default fallback
        
        # Handle the error
        enhanced_error = self.handle_test_error(
            exc, test_name, error_category, error_type, context
        )
        
        # Create test result
        result = TestResult(
            name=test_name,
            category=test_category,
            status=TestStatus.FAILED,
            duration=0.0
        )
        
        result.error = enhanced_error
        result.message = f"Test failed: {enhanced_error.message}"
        
        return result
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of all errors encountered."""
        if not self.error_history:
            return {"total_errors": 0}
        
        # Group errors by category and type
        by_category = {}
        by_type = {}
        by_severity = {}
        
        for error in self.error_history:
            # By category
            if error.category not in by_category:
                by_category[error.category] = 0
            by_category[error.category] += 1
            
            # By type
            if error.error_type not in by_type:
                by_type[error.error_type] = 0
            by_type[error.error_type] += 1
            
            # By severity
            severity_str = error.severity.value
            if severity_str not in by_severity:
                by_severity[severity_str] = 0
            by_severity[severity_str] += 1
        
        return {
            "total_errors": len(self.error_history),
            "by_category": by_category,
            "by_type": by_type,
            "by_severity": by_severity,
            "most_recent": self.error_history[-1].to_dict() if self.error_history else None
        }
    
    def export_diagnostics(self, output_path: str) -> None:
        """Export comprehensive diagnostics to file."""
        diagnostics_data = {
            "timestamp": datetime.now().isoformat(),
            "error_summary": self.get_error_summary(),
            "error_history": [error.to_dict() for error in self.error_history],
            "system_diagnostics": self.diagnostic_collector.collect_full_diagnostics().to_dict()
        }
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(diagnostics_data, f, indent=2, default=str)
        
        self.logger.info(f"Diagnostics exported to {output_path}")