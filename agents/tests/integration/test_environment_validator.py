"""
Unit tests for EnvironmentValidator.

Tests the environment validation functionality including Python environment,
package manager consistency, SSL configuration, and import dependencies.
"""

import os
import sys
import ssl
import subprocess
import tempfile
import unittest.mock
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

from .environment_validator import EnvironmentValidator, PackageInfo, EnvironmentValidationResult
from .models import EnvironmentIssue, Severity
from .config import TestConfig, EnvironmentConfig


class TestEnvironmentValidator:
    """Test cases for EnvironmentValidator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = TestConfig()
        self.validator = EnvironmentValidator(self.config)
    
    def test_init(self):
        """Test EnvironmentValidator initialization."""
        assert self.validator.config == self.config
        assert isinstance(self.validator.required_packages, set)
        assert isinstance(self.validator.required_agent_modules, list)
        assert len(self.validator.issues) == 0
        assert len(self.validator.package_info) == 0
    
    def test_init_with_default_config(self):
        """Test initialization with default config."""
        validator = EnvironmentValidator()
        assert validator.config is not None
        assert hasattr(validator.config, 'environment')
    
    def test_get_python_info(self):
        """Test Python information collection."""
        python_info = self.validator._get_python_info()
        
        assert 'version' in python_info
        assert 'version_info' in python_info
        assert 'executable' in python_info
        assert 'platform' in python_info
        assert 'prefix' in python_info
        assert 'path' in python_info
        assert 'modules_count' in python_info
        
        assert python_info['version'] == sys.version
        assert python_info['executable'] == sys.executable
        assert isinstance(python_info['modules_count'], int)
    
    def test_get_system_info(self):
        """Test system information collection."""
        system_info = self.validator._get_system_info()
        
        required_keys = [
            'platform', 'system', 'release', 'machine', 
            'processor', 'python_implementation', 'architecture'
        ]
        
        for key in required_keys:
            assert key in system_info
            assert system_info[key] is not None
    
    @patch('sys.version_info', (3, 7, 0))
    def test_validate_python_environment_old_version(self):
        """Test validation with old Python version."""
        self.validator._validate_python_environment()
        
        version_issues = [
            issue for issue in self.validator.issues 
            if issue.component == "python" and issue.issue_type == "version"
        ]
        
        assert len(version_issues) == 1
        assert version_issues[0].severity == Severity.CRITICAL
        assert "too old" in version_issues[0].description
    
    @patch('sys.version_info', (3, 9, 0))
    def test_validate_python_environment_good_version(self):
        """Test validation with acceptable Python version."""
        initial_issue_count = len(self.validator.issues)
        self.validator._validate_python_environment()
        
        version_issues = [
            issue for issue in self.validator.issues 
            if issue.component == "python" and issue.issue_type == "version"
        ]
        
        assert len(version_issues) == 0
    
    @patch('sys.prefix', '/usr')
    @patch('sys.base_prefix', '/usr')
    def test_validate_python_environment_no_venv(self):
        """Test validation when not in virtual environment."""
        self.validator._validate_python_environment()
        
        venv_issues = [
            issue for issue in self.validator.issues 
            if issue.component == "python" and issue.issue_type == "virtual_environment"
        ]
        
        assert len(venv_issues) == 1
        assert venv_issues[0].severity == Severity.HIGH
        assert "virtual environment" in venv_issues[0].description
    
    @patch('subprocess.run')
    def test_validate_python_environment_uv_missing(self, mock_run):
        """Test validation when uv is missing."""
        mock_run.side_effect = FileNotFoundError()
        
        self.validator._validate_python_environment()
        
        uv_issues = [
            issue for issue in self.validator.issues 
            if issue.component == "uv"
        ]
        
        assert len(uv_issues) == 1
        assert uv_issues[0].severity == Severity.CRITICAL
        assert "uv package manager" in uv_issues[0].description
    
    @patch('subprocess.run')
    def test_validate_python_environment_uv_working(self, mock_run):
        """Test validation when uv is working."""
        mock_run.return_value = Mock(returncode=0, stdout="uv 0.1.0")
        
        initial_issue_count = len(self.validator.issues)
        self.validator._validate_python_environment()
        
        uv_issues = [
            issue for issue in self.validator.issues 
            if issue.component == "uv"
        ]
        
        assert len(uv_issues) == 0
    
    @patch('pathlib.Path.exists')
    def test_validate_package_manager_consistency_no_pyproject(self, mock_exists):
        """Test validation when pyproject.toml is missing."""
        mock_exists.return_value = False
        
        self.validator._validate_package_manager_consistency()
        
        project_issues = [
            issue for issue in self.validator.issues 
            if issue.component == "project_structure"
        ]
        
        assert len(project_issues) == 1
        assert project_issues[0].severity == Severity.HIGH
        assert "pyproject.toml" in project_issues[0].description
    
    @patch('pathlib.Path.exists')
    @patch.object(EnvironmentValidator, '_detect_mixed_package_managers')
    def test_validate_package_manager_consistency_mixed_managers(self, mock_detect, mock_exists):
        """Test validation with mixed package managers."""
        mock_exists.return_value = True
        mock_detect.return_value = {'uv', 'pip'}
        
        self.validator._validate_package_manager_consistency()
        
        mixed_issues = [
            issue for issue in self.validator.issues 
            if issue.issue_type == "mixed_managers"
        ]
        
        assert len(mixed_issues) == 1
        assert mixed_issues[0].severity == Severity.HIGH
        assert "Mixed package managers" in mixed_issues[0].description
    
    @patch('subprocess.run')
    def test_detect_mixed_package_managers(self, mock_run):
        """Test detection of mixed package managers."""
        # Mock pip list output
        mock_run.return_value = Mock(
            returncode=0,
            stdout='[{"name": "fastapi", "version": "0.68.0"}]'
        )
        
        # Mock uv.lock existence
        with patch('pathlib.Path.exists', return_value=True):
            installers = self.validator._detect_mixed_package_managers()
        
        assert 'uv' in installers
        assert 'pip' in installers
        assert len(self.validator.package_info) == 1
        assert 'fastapi' in self.validator.package_info
    
    @patch('importlib.import_module')
    def test_validate_required_packages_missing(self, mock_import):
        """Test validation with missing required packages."""
        # Make some imports fail
        def side_effect(module_name):
            if module_name in ['fastapi', 'uvicorn']:
                raise ImportError(f"No module named '{module_name}'")
            return Mock()
        
        mock_import.side_effect = side_effect
        
        self.validator._validate_required_packages()
        
        dependency_issues = [
            issue for issue in self.validator.issues 
            if issue.component == "dependencies"
        ]
        
        assert len(dependency_issues) == 1
        assert dependency_issues[0].severity == Severity.CRITICAL
        assert "fastapi" in dependency_issues[0].description
        assert "uvicorn" in dependency_issues[0].description
    
    @patch('importlib.import_module')
    def test_validate_required_packages_all_present(self, mock_import):
        """Test validation when all required packages are present."""
        mock_import.return_value = Mock()
        
        initial_issue_count = len(self.validator.issues)
        self.validator._validate_required_packages()
        
        dependency_issues = [
            issue for issue in self.validator.issues 
            if issue.component == "dependencies"
        ]
        
        assert len(dependency_issues) == 0
    
    @patch('importlib.import_module')
    def test_validate_import_dependencies_failures(self, mock_import):
        """Test validation with import failures."""
        def side_effect(module_name):
            if 'hill_metrics' in module_name:
                raise ImportError("Missing shapely dependency")
            return Mock()
        
        mock_import.side_effect = side_effect
        
        self.validator._validate_import_dependencies()
        
        import_issues = [
            issue for issue in self.validator.issues 
            if issue.component == "imports"
        ]
        
        assert len(import_issues) == 1
        assert import_issues[0].severity == Severity.CRITICAL
        assert "hill_metrics" in import_issues[0].description
        assert "shapely" in import_issues[0].description
    
    @patch('importlib.import_module')
    def test_validate_import_dependencies_success(self, mock_import):
        """Test validation when all imports succeed."""
        mock_import.return_value = Mock()
        
        initial_issue_count = len(self.validator.issues)
        self.validator._validate_import_dependencies()
        
        import_issues = [
            issue for issue in self.validator.issues 
            if issue.component == "imports"
        ]
        
        assert len(import_issues) == 0
    
    @patch('ssl.create_default_context')
    def test_validate_ssl_configuration_success(self, mock_create_context):
        """Test SSL configuration validation success."""
        mock_context = Mock()
        mock_context.check_hostname = True
        mock_context.verify_mode.name = 'CERT_REQUIRED'
        mock_create_context.return_value = mock_context
        
        ssl_info = self.validator._validate_ssl_configuration()
        
        assert ssl_info['context_created'] is True
        assert 'version' in ssl_info
        assert 'version_info' in ssl_info
        
        ssl_issues = [
            issue for issue in self.validator.issues 
            if issue.component == "ssl"
        ]
        
        assert len(ssl_issues) == 0
    
    @patch('ssl.create_default_context')
    def test_validate_ssl_configuration_failure(self, mock_create_context):
        """Test SSL configuration validation failure."""
        mock_create_context.side_effect = Exception("SSL context creation failed")
        
        ssl_info = self.validator._validate_ssl_configuration()
        
        assert ssl_info['context_created'] is False
        assert 'context_error' in ssl_info
        
        ssl_issues = [
            issue for issue in self.validator.issues 
            if issue.component == "ssl" and issue.issue_type == "context_creation"
        ]
        
        assert len(ssl_issues) == 1
        assert ssl_issues[0].severity == Severity.HIGH
    
    @patch('urllib.request.urlopen')
    def test_validate_ssl_connectivity_success(self, mock_urlopen):
        """Test SSL connectivity validation success."""
        mock_response = Mock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        self.validator._validate_ssl_connectivity()
        
        connectivity_issues = [
            issue for issue in self.validator.issues 
            if issue.component == "ssl" and issue.issue_type == "connectivity"
        ]
        
        assert len(connectivity_issues) == 0
    
    @patch('urllib.request.urlopen')
    def test_validate_ssl_connectivity_failure(self, mock_urlopen):
        """Test SSL connectivity validation failure."""
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("Connection failed")
        
        self.validator._validate_ssl_connectivity()
        
        connectivity_issues = [
            issue for issue in self.validator.issues 
            if issue.component == "ssl" and issue.issue_type == "connectivity"
        ]
        
        assert len(connectivity_issues) == 1
        assert connectivity_issues[0].severity == Severity.MEDIUM
    
    @patch('shutil.disk_usage')
    def test_validate_system_resources_low_disk(self, mock_disk_usage):
        """Test system resource validation with low disk space."""
        # Mock low disk space (500MB free)
        mock_disk_usage.return_value = (1000000000, 500000000, 500000000)
        
        self.validator._validate_system_resources()
        
        disk_issues = [
            issue for issue in self.validator.issues 
            if issue.component == "system" and issue.issue_type == "disk_space"
        ]
        
        assert len(disk_issues) == 1
        assert disk_issues[0].severity == Severity.MEDIUM
    
    @patch('shutil.disk_usage')
    def test_validate_system_resources_adequate_disk(self, mock_disk_usage):
        """Test system resource validation with adequate disk space."""
        # Mock adequate disk space (2GB free)
        mock_disk_usage.return_value = (10000000000, 8000000000, 2000000000)
        
        self.validator._validate_system_resources()
        
        disk_issues = [
            issue for issue in self.validator.issues 
            if issue.component == "system" and issue.issue_type == "disk_space"
        ]
        
        assert len(disk_issues) == 0
    
    def test_validate_environment_integration(self):
        """Test complete environment validation integration."""
        with patch.multiple(
            self.validator,
            _validate_python_environment=Mock(),
            _validate_package_manager_consistency=Mock(),
            _validate_required_packages=Mock(),
            _validate_import_dependencies=Mock(),
            _validate_ssl_connectivity=Mock(),
            _validate_system_resources=Mock()
        ):
            result = self.validator.validate_environment()
        
        assert isinstance(result, EnvironmentValidationResult)
        assert hasattr(result, 'is_valid')
        assert hasattr(result, 'issues')
        assert hasattr(result, 'package_info')
        assert hasattr(result, 'python_info')
        assert hasattr(result, 'ssl_info')
        assert hasattr(result, 'system_info')
    
    def test_validate_environment_with_critical_issues(self):
        """Test validation result when critical issues exist."""
        def add_critical_issue():
            self.validator.issues.append(EnvironmentIssue(
                component="test",
                issue_type="critical_test",
                description="Critical test issue",
                severity=Severity.CRITICAL
            ))
        
        with patch.multiple(
            self.validator,
            _validate_python_environment=Mock(side_effect=add_critical_issue),
            _validate_package_manager_consistency=Mock(),
            _validate_required_packages=Mock(),
            _validate_import_dependencies=Mock(),
            _validate_ssl_connectivity=Mock(),
            _validate_system_resources=Mock()
        ):
            result = self.validator.validate_environment()
        
        assert result.is_valid is False
    
    def test_validate_environment_with_low_severity_issues(self):
        """Test validation result when only low severity issues exist."""
        # Add a low severity issue
        self.validator.issues.append(EnvironmentIssue(
            component="test",
            issue_type="info_test",
            description="Info test issue",
            severity=Severity.INFO
        ))
        
        with patch.multiple(
            self.validator,
            _validate_python_environment=Mock(),
            _validate_package_manager_consistency=Mock(),
            _validate_required_packages=Mock(),
            _validate_import_dependencies=Mock(),
            _validate_ssl_connectivity=Mock(),
            _validate_system_resources=Mock()
        ):
            result = self.validator.validate_environment()
        
        assert result.is_valid is True
    
    def test_get_diagnostic_info(self):
        """Test diagnostic information generation."""
        with patch.object(self.validator, 'validate_environment') as mock_validate:
            mock_result = EnvironmentValidationResult(
                is_valid=True,
                issues=[],
                package_info={},
                python_info={'version': '3.9.0'},
                ssl_info={'version': 'OpenSSL 1.1.1'},
                system_info={'platform': 'Linux'}
            )
            mock_validate.return_value = mock_result
            
            diagnostic_info = self.validator.get_diagnostic_info()
        
        assert 'validation_result' in diagnostic_info
        assert 'python_info' in diagnostic_info
        assert 'ssl_info' in diagnostic_info
        assert 'system_info' in diagnostic_info
        assert 'package_count' in diagnostic_info
        assert 'issues' in diagnostic_info
        
        assert diagnostic_info['validation_result']['is_valid'] is True
    
    def test_generate_fix_script_with_uv_issues(self):
        """Test fix script generation with uv issues."""
        # Add uv-related issue
        self.validator.issues.append(EnvironmentIssue(
            component="uv",
            issue_type="missing_tool",
            description="uv not found",
            severity=Severity.CRITICAL
        ))
        
        script = self.validator.generate_fix_script()
        
        assert "#!/bin/bash" in script
        assert "Installing uv" in script
        assert "curl -LsSf https://astral.sh/uv/install.sh" in script
    
    def test_generate_fix_script_with_dependency_issues(self):
        """Test fix script generation with dependency issues."""
        # Add dependency issue
        self.validator.issues.append(EnvironmentIssue(
            component="dependencies",
            issue_type="missing_packages",
            description="Missing packages",
            severity=Severity.CRITICAL
        ))
        
        script = self.validator.generate_fix_script()
        
        assert "#!/bin/bash" in script
        assert "uv sync" in script
        assert "Syncing dependencies" in script
    
    def test_generate_fix_script_no_issues(self):
        """Test fix script generation with no issues."""
        # Mock validate_environment to return no issues
        mock_result = EnvironmentValidationResult(
            is_valid=True,
            issues=[],
            package_info={},
            python_info={},
            ssl_info={},
            system_info={}
        )
        
        with patch.object(self.validator, 'validate_environment', return_value=mock_result):
            script = self.validator.generate_fix_script()
        
        assert "#!/bin/bash" in script
        assert "Environment fixes completed!" in script
        # Should not contain specific fix commands
        assert "Installing uv" not in script
        assert "uv sync" not in script


class TestPackageInfo:
    """Test cases for PackageInfo dataclass."""
    
    def test_package_info_creation(self):
        """Test PackageInfo creation."""
        pkg = PackageInfo(
            name="fastapi",
            version="0.68.0",
            location="/path/to/package",
            installer="uv"
        )
        
        assert pkg.name == "fastapi"
        assert pkg.version == "0.68.0"
        assert pkg.location == "/path/to/package"
        assert pkg.installer == "uv"
    
    def test_package_info_optional_installer(self):
        """Test PackageInfo with optional installer."""
        pkg = PackageInfo(
            name="fastapi",
            version="0.68.0",
            location="/path/to/package"
        )
        
        assert pkg.installer is None


class TestEnvironmentValidationResult:
    """Test cases for EnvironmentValidationResult dataclass."""
    
    def test_environment_validation_result_creation(self):
        """Test EnvironmentValidationResult creation."""
        issues = [EnvironmentIssue(
            component="test",
            issue_type="test",
            description="Test issue",
            severity=Severity.INFO
        )]
        
        result = EnvironmentValidationResult(
            is_valid=True,
            issues=issues,
            package_info={},
            python_info={'version': '3.9.0'},
            ssl_info={'version': 'OpenSSL'},
            system_info={'platform': 'Linux'}
        )
        
        assert result.is_valid is True
        assert len(result.issues) == 1
        assert result.python_info['version'] == '3.9.0'
        assert result.ssl_info['version'] == 'OpenSSL'
        assert result.system_info['platform'] == 'Linux'