"""
Environment Validator for dependency checking.

Validates Python environment setup, package manager consistency,
SSL/TLS configuration, and import dependencies to ensure the
system is properly configured for integration testing.
"""

import importlib
import importlib.util
import json
import platform
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import TestConfig
from .config import get_test_config
from .models import EnvironmentIssue
from .models import Severity


@dataclass
class PackageInfo:
    """Information about an installed package."""

    name: str
    version: str
    location: str
    installer: str | None = None  # 'uv', 'pip', 'conda', etc.


@dataclass
class EnvironmentValidationResult:
    """Result of environment validation."""

    is_valid: bool
    issues: list[EnvironmentIssue]
    package_info: dict[str, PackageInfo]
    python_info: dict[str, Any]
    ssl_info: dict[str, Any]
    system_info: dict[str, Any]


class EnvironmentValidator:
    """Validates system environment and dependencies for integration testing."""

    def __init__(self, config: TestConfig | None = None):
        """Initialize the environment validator."""
        self.config = config or get_test_config()
        self.issues: list[EnvironmentIssue] = []
        self.package_info: dict[str, PackageInfo] = {}

        # Required packages for the project
        self.required_packages = {
            "fastapi",
            "uvicorn",
            "structlog",
            "rasterio",
            "shapely",
            "numpy",
            "requests",
            "aiohttp",
            "pytest",
        }

        # Agent modules that must be importable
        self.required_agent_modules = [
            "agents.hill_metrics.server",
            "agents.weather.server",
            "agents.equipment.server",
            "agents.shared.jsonrpc",
            "agents.shared.mcp",
            "agents.shared.monitoring",
        ]

    def validate_environment(self) -> EnvironmentValidationResult:
        """Perform comprehensive environment validation."""
        self.issues.clear()
        self.package_info.clear()

        # Collect system information
        python_info = self._get_python_info()
        ssl_info = self._validate_ssl_configuration()
        system_info = self._get_system_info()

        # Run validation checks
        self._validate_python_environment()
        self._validate_package_manager_consistency()
        self._validate_required_packages()
        self._validate_import_dependencies()
        self._validate_ssl_connectivity()
        self._validate_system_resources()

        is_valid = not any(
            issue.severity in [Severity.CRITICAL, Severity.HIGH]
            for issue in self.issues
        )

        return EnvironmentValidationResult(
            is_valid=is_valid,
            issues=self.issues,
            package_info=self.package_info,
            python_info=python_info,
            ssl_info=ssl_info,
            system_info=system_info,
        )

    def _get_python_info(self) -> dict[str, Any]:
        """Get Python environment information."""
        return {
            "version": sys.version,
            "version_info": {
                "major": sys.version_info.major,
                "minor": sys.version_info.minor,
                "micro": sys.version_info.micro,
            },
            "executable": sys.executable,
            "platform": sys.platform,
            "prefix": sys.prefix,
            "path": sys.path[:5],  # First 5 entries to avoid clutter
            "modules_count": len(sys.modules),
        }

    def _get_system_info(self) -> dict[str, Any]:
        """Get system information."""
        return {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_implementation": platform.python_implementation(),
            "architecture": platform.architecture(),
        }

    def _validate_python_environment(self) -> None:
        """Validate Python environment setup."""
        # Check Python version
        min_version = (3, 8, 0)
        current_version = sys.version_info[:3]

        if current_version < min_version:
            self.issues.append(
                EnvironmentIssue(
                    component="python",
                    issue_type="version",
                    description=f"Python version {'.'.join(map(str, current_version))} is too old. Minimum required: {'.'.join(map(str, min_version))}",
                    severity=Severity.CRITICAL,
                    suggested_fix=f"Upgrade Python to version {'.'.join(map(str, min_version))} or higher",
                )
            )

        # Check if we're in a virtual environment
        in_venv = hasattr(sys, "real_prefix") or (
            hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
        )

        if not in_venv:
            self.issues.append(
                EnvironmentIssue(
                    component="python",
                    issue_type="virtual_environment",
                    description="Not running in a virtual environment",
                    severity=Severity.HIGH,
                    suggested_fix="Create and activate a virtual environment with 'uv venv' and 'source .venv/bin/activate'",
                )
            )

        # Check for uv installation
        try:
            result = subprocess.run(
                ["uv", "--version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                raise subprocess.CalledProcessError(result.returncode, "uv")
        except (
            subprocess.CalledProcessError,
            FileNotFoundError,
            subprocess.TimeoutExpired,
        ):
            self.issues.append(
                EnvironmentIssue(
                    component="uv",
                    issue_type="missing_tool",
                    description="uv package manager not found or not working",
                    severity=Severity.CRITICAL,
                    suggested_fix="Install uv following instructions at https://docs.astral.sh/uv/getting-started/installation/",
                )
            )

    def _validate_package_manager_consistency(self) -> None:
        """Detect package manager consistency (uv vs pip)."""
        # Check for pyproject.toml (uv project indicator)
        project_root = Path(__file__).parent.parent.parent.parent
        pyproject_path = project_root / "pyproject.toml"

        if not pyproject_path.exists():
            self.issues.append(
                EnvironmentIssue(
                    component="project_structure",
                    issue_type="missing_file",
                    description="pyproject.toml not found",
                    severity=Severity.HIGH,
                    suggested_fix="This appears to be a uv project but pyproject.toml is missing",
                )
            )
            return

        # Check for mixed package manager usage by examining package metadata
        mixed_installers = self._detect_mixed_package_managers()

        if mixed_installers:
            installer_list = ", ".join(mixed_installers)
            self.issues.append(
                EnvironmentIssue(
                    component="package_manager",
                    issue_type="mixed_managers",
                    description=f"Mixed package managers detected: {installer_list}",
                    severity=Severity.HIGH,
                    suggested_fix="Use only 'uv' for this project. Remove packages installed with pip and reinstall with 'uv add'",
                )
            )

    def _detect_mixed_package_managers(self) -> set[str]:
        """Detect which package managers have been used."""
        installers = set()

        try:
            # Try to get package information using pip
            result = subprocess.run(
                [sys.executable, "-m", "pip", "list", "--format=json"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                packages = json.loads(result.stdout)
                for pkg in packages:
                    # Store package info
                    self.package_info[pkg["name"].lower()] = PackageInfo(
                        name=pkg["name"],
                        version=pkg["version"],
                        location="",  # pip list doesn't provide location
                        installer="pip",  # Assume pip for now
                    )

                # If we have packages and uv.lock exists, it suggests mixed usage
                project_root = Path(__file__).parent.parent.parent.parent
                if packages and (project_root / "uv.lock").exists():
                    installers.add("uv")
                    installers.add("pip")

        except (
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
            json.JSONDecodeError,
        ):
            pass

        return installers

    def _validate_required_packages(self) -> None:
        """Validate that required packages are installed."""
        missing_packages = []

        for package_name in self.required_packages:
            try:
                # Try to import the package
                importlib.import_module(package_name)
            except ImportError:
                missing_packages.append(package_name)

        if missing_packages:
            missing_list = ", ".join(missing_packages)
            self.issues.append(
                EnvironmentIssue(
                    component="dependencies",
                    issue_type="missing_packages",
                    description=f"Required packages not installed: {missing_list}",
                    severity=Severity.CRITICAL,
                    suggested_fix=f"Install missing packages with 'uv add {' '.join(missing_packages)}'",
                )
            )

    def _validate_import_dependencies(self) -> None:
        """Test that all agent modules can be imported successfully."""
        failed_imports = []

        for module_name in self.required_agent_modules:
            try:
                importlib.import_module(module_name)
            except ImportError as e:
                failed_imports.append((module_name, str(e)))

        if failed_imports:
            for module_name, error in failed_imports:
                self.issues.append(
                    EnvironmentIssue(
                        component="imports",
                        issue_type="import_failure",
                        description=f"Cannot import {module_name}: {error}",
                        severity=Severity.CRITICAL,
                        suggested_fix="Check that all dependencies are installed with 'uv sync'",
                    )
                )

    def _validate_ssl_configuration(self) -> dict[str, Any]:
        """Validate SSL/TLS configuration."""
        ssl_info = {
            "version": ssl.OPENSSL_VERSION,
            "version_info": ssl.OPENSSL_VERSION_INFO,
        }

        # Test SSL context creation
        try:
            context = ssl.create_default_context()
            ssl_info["context_created"] = True
            ssl_info["default_context_check_hostname"] = context.check_hostname
            ssl_info["default_context_verify_mode"] = context.verify_mode.name
        except Exception as e:
            ssl_info["context_created"] = False
            ssl_info["context_error"] = str(e)

            self.issues.append(
                EnvironmentIssue(
                    component="ssl",
                    issue_type="context_creation",
                    description=f"Cannot create SSL context: {e}",
                    severity=Severity.HIGH,
                    suggested_fix="Check SSL/TLS installation and certificates",
                )
            )

        return ssl_info

    def _validate_ssl_connectivity(self) -> None:
        """Test SSL connectivity to common endpoints."""
        test_urls = [
            "https://httpbin.org/get",
            "https://api.github.com",
        ]

        for url in test_urls:
            try:
                with urllib.request.urlopen(url, timeout=10) as response:
                    if response.status != 200:
                        raise urllib.error.HTTPError(
                            url, response.status, "Non-200 response", None, None
                        )
            except urllib.error.URLError as e:
                self.issues.append(
                    EnvironmentIssue(
                        component="ssl",
                        issue_type="connectivity",
                        description=f"SSL connectivity test failed for {url}: {e}",
                        severity=Severity.MEDIUM,
                        suggested_fix="Check network connectivity and SSL certificate configuration",
                    )
                )
                break  # Don't test all URLs if one fails
            except Exception as e:
                self.issues.append(
                    EnvironmentIssue(
                        component="ssl",
                        issue_type="connectivity",
                        description=f"Unexpected error testing SSL connectivity to {url}: {e}",
                        severity=Severity.MEDIUM,
                        suggested_fix="Check network and SSL configuration",
                    )
                )
                break

    def _validate_system_resources(self) -> None:
        """Validate system resources are adequate."""
        # Check available disk space
        try:
            import shutil

            project_root = Path(__file__).parent.parent.parent.parent
            _total, _used, free = shutil.disk_usage(project_root)

            # Require at least 1GB free space
            if free < 1024 * 1024 * 1024:
                self.issues.append(
                    EnvironmentIssue(
                        component="system",
                        issue_type="disk_space",
                        description="Low disk space available",
                        severity=Severity.MEDIUM,
                        detected_value=f"{free // (1024 * 1024)} MB",
                        expected_value=">1024 MB",
                        suggested_fix="Free up disk space before running tests",
                    )
                )
        except Exception:
            # Don't fail if we can't check disk space
            pass

    def get_diagnostic_info(self) -> dict[str, Any]:
        """Get comprehensive diagnostic information."""
        result = self.validate_environment()

        return {
            "validation_result": {
                "is_valid": result.is_valid,
                "issue_count": len(result.issues),
                "critical_issues": len(
                    [i for i in result.issues if i.severity == Severity.CRITICAL]
                ),
                "high_issues": len(
                    [i for i in result.issues if i.severity == Severity.HIGH]
                ),
            },
            "python_info": result.python_info,
            "ssl_info": result.ssl_info,
            "system_info": result.system_info,
            "package_count": len(result.package_info),
            "issues": [issue.to_dict() for issue in result.issues],
        }

    def generate_fix_script(self) -> str:
        """Generate a shell script to fix common issues."""
        script_lines = [
            "#!/bin/bash",
            "# Auto-generated environment fix script",
            "set -e",
            "",
            "echo 'Fixing environment issues...'",
            "",
        ]

        # Check current issues (use existing issues if validation was already run)
        if not self.issues:
            result = self.validate_environment()
            issues = result.issues
        else:
            issues = self.issues

        has_uv_issues = any(
            issue.component == "uv" or issue.issue_type == "mixed_managers"
            for issue in issues
        )

        has_dependency_issues = any(
            issue.component == "dependencies" or issue.component == "imports"
            for issue in issues
        )

        if has_uv_issues:
            script_lines.extend(
                [
                    "# Install uv if missing",
                    "if ! command -v uv &> /dev/null; then",
                    "    echo 'Installing uv...'",
                    "    curl -LsSf https://astral.sh/uv/install.sh | sh",
                    "    source $HOME/.cargo/env",
                    "fi",
                    "",
                ]
            )

        if has_dependency_issues:
            script_lines.extend(
                [
                    "# Sync dependencies with uv",
                    "echo 'Syncing dependencies...'",
                    "uv sync",
                    "",
                ]
            )

        script_lines.extend(
            [
                "echo 'Environment fixes completed!'",
                "echo 'Run the integration tests again to verify.'",
            ]
        )

        return "\n".join(script_lines)
