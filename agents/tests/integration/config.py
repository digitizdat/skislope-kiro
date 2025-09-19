"""
Test configuration system with environment detection.

Provides centralized configuration management for integration tests,
including environment detection, timeout settings, and test parameters.
"""

import os
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any
import platform
import subprocess


class TestEnvironment(Enum):
    """Test environment types."""
    LOCAL = "local"
    CI = "ci"
    PRODUCTION = "production"


class LogLevel(Enum):
    """Logging levels for test execution."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass
class AgentConfig:
    """Configuration for individual agent servers."""
    name: str
    host: str = "localhost"
    port: int = 8000
    startup_timeout: int = 30
    health_endpoint: str = "/health"
    enabled: bool = True
    required_methods: List[str] = field(default_factory=list)


@dataclass
class TimeoutConfig:
    """Timeout configuration for various test operations."""
    agent_startup: int = 30
    test_execution: int = 300
    network_request: int = 10
    health_check: int = 5
    shutdown: int = 15


@dataclass
class EnvironmentConfig:
    """Environment-specific configuration."""
    python_path: str = sys.executable
    node_version: Optional[str] = None
    ssl_validation: bool = True
    temp_dir: Optional[Path] = None
    log_dir: Optional[Path] = None


@dataclass
class ReportingConfig:
    """Test reporting configuration."""
    output_format: str = "json"  # json, html, junit
    detail_level: str = "standard"  # minimal, standard, verbose
    include_diagnostics: bool = True
    save_artifacts: bool = True
    artifact_retention_days: int = 7


@dataclass
class TestConfig:
    """Main test configuration class."""
    environment: TestEnvironment = TestEnvironment.LOCAL
    agents: Dict[str, AgentConfig] = field(default_factory=dict)
    timeouts: TimeoutConfig = field(default_factory=TimeoutConfig)
    env_config: EnvironmentConfig = field(default_factory=EnvironmentConfig)
    reporting: ReportingConfig = field(default_factory=ReportingConfig)
    log_level: LogLevel = LogLevel.INFO
    parallel_execution: bool = True
    max_workers: int = 4
    retry_attempts: int = 3
    retry_delay: float = 1.0
    
    def __post_init__(self):
        """Initialize default agent configurations."""
        if not self.agents:
            self.agents = {
                "hill_metrics": AgentConfig(
                    name="hill_metrics",
                    port=8001,
                    required_methods=["get_terrain_data", "process_elevation"]
                ),
                "weather": AgentConfig(
                    name="weather",
                    port=8002,
                    required_methods=["get_weather_data", "get_conditions"]
                ),
                "equipment": AgentConfig(
                    name="equipment",
                    port=8003,
                    required_methods=["get_equipment_status", "list_facilities"]
                )
            }


class ConfigManager:
    """Manages test configuration with environment detection."""
    
    def __init__(self):
        self._config: Optional[TestConfig] = None
        self._environment = self._detect_environment()
    
    def _detect_environment(self) -> TestEnvironment:
        """Detect the current test environment."""
        # Check for CI environment variables
        ci_indicators = [
            "CI", "CONTINUOUS_INTEGRATION", "GITHUB_ACTIONS",
            "JENKINS_URL", "TRAVIS", "CIRCLECI"
        ]
        
        if any(os.getenv(var) for var in ci_indicators):
            return TestEnvironment.CI
        
        # Check for production indicators
        if os.getenv("NODE_ENV") == "production" or os.getenv("ENVIRONMENT") == "production":
            return TestEnvironment.PRODUCTION
        
        return TestEnvironment.LOCAL
    
    def _get_node_version(self) -> Optional[str]:
        """Get Node.js version if available."""
        try:
            result = subprocess.run(
                ["node", "--version"], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return None
    
    def _setup_directories(self, config: TestConfig) -> None:
        """Set up required directories for testing."""
        project_root = Path(__file__).parent.parent.parent.parent
        
        # Set up temp directory
        if not config.env_config.temp_dir:
            config.env_config.temp_dir = project_root / "temp" / "integration_tests"
        config.env_config.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Set up log directory
        if not config.env_config.log_dir:
            config.env_config.log_dir = project_root / "logs" / "integration_tests"
        config.env_config.log_dir.mkdir(parents=True, exist_ok=True)
    
    def get_config(self, overrides: Optional[Dict[str, Any]] = None) -> TestConfig:
        """Get test configuration with environment-specific settings."""
        if self._config is None:
            self._config = TestConfig(environment=self._environment)
            
            # Environment-specific adjustments
            if self._environment == TestEnvironment.CI:
                self._config.timeouts.agent_startup = 60
                self._config.timeouts.test_execution = 600
                self._config.log_level = LogLevel.INFO
                self._config.reporting.detail_level = "verbose"
                self._config.parallel_execution = True
                
            elif self._environment == TestEnvironment.PRODUCTION:
                self._config.timeouts.agent_startup = 45
                self._config.timeouts.test_execution = 300
                self._config.log_level = LogLevel.WARNING
                self._config.reporting.detail_level = "minimal"
                self._config.parallel_execution = False
                self._config.retry_attempts = 5
                
            else:  # LOCAL
                self._config.log_level = LogLevel.DEBUG
                self._config.reporting.detail_level = "standard"
                self._config.parallel_execution = True
            
            # Set Node.js version
            self._config.env_config.node_version = self._get_node_version()
            
            # Set up directories
            self._setup_directories(self._config)
        
        # Apply any overrides
        if overrides:
            self._apply_overrides(self._config, overrides)
        
        return self._config
    
    def _apply_overrides(self, config: TestConfig, overrides: Dict[str, Any]) -> None:
        """Apply configuration overrides."""
        for key, value in overrides.items():
            if hasattr(config, key):
                # Handle enum conversions
                if key == "log_level" and isinstance(value, str):
                    value = LogLevel(value)
                setattr(config, key, value)
            elif "." in key:
                # Handle nested attributes like "timeouts.agent_startup"
                parts = key.split(".")
                obj = config
                for part in parts[:-1]:
                    obj = getattr(obj, part)
                setattr(obj, parts[-1], value)
        
        # Re-setup directories after overrides
        self._setup_directories(config)
    
    @property
    def environment(self) -> TestEnvironment:
        """Get the detected environment."""
        return self._environment
    
    def is_ci(self) -> bool:
        """Check if running in CI environment."""
        return self._environment == TestEnvironment.CI
    
    def is_local(self) -> bool:
        """Check if running in local environment."""
        return self._environment == TestEnvironment.LOCAL
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self._environment == TestEnvironment.PRODUCTION


# Global configuration manager instance
config_manager = ConfigManager()


def get_test_config(overrides: Optional[Dict[str, Any]] = None) -> TestConfig:
    """Get the current test configuration."""
    return config_manager.get_config(overrides)


def get_environment() -> TestEnvironment:
    """Get the current test environment."""
    return config_manager.environment