#!/usr/bin/env python3
"""
Deployment validation smoke tests for production readiness.

This script runs lightweight smoke tests to validate that a deployment
is ready for production use. It focuses on critical functionality
without requiring full integration test infrastructure.
"""

import asyncio
import json
import logging
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from agents.tests.integration.api_contract_validator import APIContractValidator
from agents.tests.integration.environment_validator import EnvironmentValidator


@dataclass
class SmokeTestResult:
    """Result of a smoke test."""

    name: str
    passed: bool
    duration: float
    message: str
    details: dict | None = None


class DeploymentSmokeTests:
    """Lightweight smoke tests for deployment validation."""

    def __init__(self, output_dir: str = "deployment-test-results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.results: list[SmokeTestResult] = []
        self.start_time = time.time()

        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(self.output_dir / "smoke_tests.log"),
                logging.StreamHandler(),
            ],
        )
        self.logger = logging.getLogger(__name__)

    async def run_all_tests(self) -> bool:
        """Run all smoke tests and return overall success."""
        self.logger.info("Starting deployment smoke tests...")

        tests = [
            self.test_environment_setup,
            self.test_python_imports,
            self.test_frontend_build,
            self.test_agent_static_validation,
            self.test_configuration_files,
            self.test_logging_setup,
            self.test_cache_directories,
            self.test_production_readiness,
        ]

        for test in tests:
            await self._run_test(test)

        # Generate summary report
        self._generate_report()

        # Return overall success
        passed_tests = sum(1 for r in self.results if r.passed)
        total_tests = len(self.results)

        self.logger.info(f"Smoke tests completed: {passed_tests}/{total_tests} passed")
        return passed_tests == total_tests

    async def _run_test(self, test_func):
        """Run a single test and record results."""
        test_name = test_func.__name__.replace("test_", "").replace("_", " ").title()
        start_time = time.time()

        try:
            self.logger.info(f"Running: {test_name}")
            await test_func()
            duration = time.time() - start_time

            result = SmokeTestResult(
                name=test_name,
                passed=True,
                duration=duration,
                message="Test passed successfully",
            )
            self.logger.info(f"✓ {test_name} passed ({duration:.2f}s)")

        except Exception as e:
            duration = time.time() - start_time
            result = SmokeTestResult(
                name=test_name,
                passed=False,
                duration=duration,
                message=str(e),
                details={"error_type": type(e).__name__},
            )
            self.logger.error(f"✗ {test_name} failed: {e}")

        self.results.append(result)

    async def test_environment_setup(self):
        """Test that the environment is properly configured."""
        validator = EnvironmentValidator()

        # Check Python environment
        python_issues = await validator.validate_python_environment()
        if python_issues:
            raise Exception(f"Python environment issues: {python_issues}")

        # Check package consistency
        package_issues = await validator.validate_package_consistency()
        if package_issues:
            raise Exception(f"Package consistency issues: {package_issues}")

        # Check SSL configuration
        ssl_issues = await validator.validate_ssl_configuration()
        if ssl_issues:
            self.logger.warning(f"SSL configuration warnings: {ssl_issues}")

    async def test_python_imports(self):
        """Test that all critical Python modules can be imported."""
        critical_imports = [
            "agents.hill_metrics.server",
            "agents.weather.server",
            "agents.equipment.server",
            "agents.shared.jsonrpc",
            "agents.shared.mcp",
            "agents.tests.integration.api_contract_validator",
            "agents.tests.integration.environment_validator",
        ]

        for module in critical_imports:
            try:
                __import__(module)
            except ImportError as e:
                raise Exception(f"Failed to import {module}: {e}") from e

    async def test_frontend_build(self):
        """Test that the frontend builds successfully."""
        try:
            # Run frontend build
            result = subprocess.run(
                ["npm", "run", "build"],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode != 0:
                raise Exception(f"Frontend build failed: {result.stderr}")

            # Check that build artifacts exist
            dist_dir = project_root / "dist"
            if not dist_dir.exists():
                raise Exception("Build directory 'dist' not created")

            # Check for essential files
            essential_files = ["index.html", "assets"]
            for file_name in essential_files:
                if not (dist_dir / file_name).exists():
                    raise Exception(f"Essential build artifact missing: {file_name}")

        except subprocess.TimeoutExpired:
            raise Exception("Frontend build timed out after 120 seconds") from None

    async def test_agent_static_validation(self):
        """Test agent API contracts without starting servers."""
        validator = APIContractValidator()

        agent_files = [
            "agents/hill_metrics/server.py",
            "agents/weather/server.py",
            "agents/equipment/server.py",
        ]

        for agent_file in agent_files:
            try:
                methods = validator.discover_agent_methods_static(agent_file)
                if not methods:
                    raise Exception(f"No methods discovered in {agent_file}")

            except Exception as e:
                raise Exception(
                    f"Static validation failed for {agent_file}: {e}"
                ) from e

    async def test_configuration_files(self):
        """Test that all required configuration files exist and are valid."""
        required_configs = [
            ("package.json", self._validate_package_json),
            ("pyproject.toml", self._validate_pyproject_toml),
            ("logging.yaml", self._validate_logging_config),
            ("ruff.toml", self._validate_ruff_config),
        ]

        for config_file, validator_func in required_configs:
            config_path = project_root / config_file
            if not config_path.exists():
                raise Exception(f"Required configuration file missing: {config_file}")

            try:
                validator_func(config_path)
            except Exception as e:
                raise Exception(f"Invalid configuration in {config_file}: {e}") from e

    def _validate_package_json(self, path: Path):
        """Validate package.json structure."""
        with open(path) as f:
            data = json.load(f)

        required_fields = ["name", "version", "scripts", "dependencies"]
        for field in required_fields:
            if field not in data:
                raise Exception(f"Missing required field: {field}")

        # Check for essential scripts
        essential_scripts = ["dev", "build", "test"]
        for script in essential_scripts:
            if script not in data.get("scripts", {}):
                raise Exception(f"Missing essential script: {script}")

    def _validate_pyproject_toml(self, path: Path):
        """Validate pyproject.toml structure."""
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib

        with open(path, "rb") as f:
            data = tomllib.load(f)

        # Check for essential sections
        if "project" not in data:
            raise Exception("Missing [project] section")

        if "dependencies" not in data["project"]:
            raise Exception("Missing project dependencies")

    def _validate_logging_config(self, path: Path):
        """Validate logging configuration."""
        try:
            import yaml

            with open(path) as f:
                yaml.safe_load(f)
        except Exception as e:
            raise Exception(f"Invalid YAML: {e}") from e

    def _validate_ruff_config(self, path: Path):
        """Validate ruff configuration."""
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib

        with open(path, "rb") as f:
            tomllib.load(f)

    async def test_logging_setup(self):
        """Test that logging is properly configured."""
        logs_dir = project_root / "logs"

        # Create logs directory if it doesn't exist
        logs_dir.mkdir(exist_ok=True)

        # Test that we can write to logs directory
        test_log = logs_dir / "smoke_test.log"
        try:
            with open(test_log, "w") as f:
                f.write("Smoke test log entry\n")
            test_log.unlink()  # Clean up
        except Exception as e:
            raise Exception(f"Cannot write to logs directory: {e}") from e

    async def test_cache_directories(self):
        """Test that cache directories can be created and used."""
        cache_dirs = ["cache", "temp"]

        for cache_dir in cache_dirs:
            cache_path = project_root / cache_dir
            cache_path.mkdir(exist_ok=True)

            # Test write access
            test_file = cache_path / "smoke_test.tmp"
            try:
                with open(test_file, "w") as f:
                    f.write("test")
                test_file.unlink()  # Clean up
            except Exception as e:
                raise Exception(
                    f"Cannot write to cache directory {cache_dir}: {e}"
                ) from e

    async def test_production_readiness(self):
        """Test production-specific requirements."""
        # Check that development dependencies are not required in production
        try:
            # This should work without dev dependencies
            from agents.hill_metrics.server import HillMetricsAgent  # noqa: F401
            from agents.shared.jsonrpc import JSONRPCServer  # noqa: F401
        except ImportError as e:
            raise Exception(f"Production imports failed: {e}") from e

        # Check that sensitive files are not included
        sensitive_patterns = [".env", "*.key", "*.pem", "secrets.*"]
        for pattern in sensitive_patterns:
            matches = list(project_root.glob(pattern))
            if matches:
                self.logger.warning(f"Sensitive files found: {matches}")

        # Check build size (basic check)
        dist_dir = project_root / "dist"
        if dist_dir.exists():
            total_size = sum(
                f.stat().st_size for f in dist_dir.rglob("*") if f.is_file()
            )
            # Warn if build is unusually large (>50MB)
            if total_size > 50 * 1024 * 1024:
                self.logger.warning(
                    f"Large build size: {total_size / 1024 / 1024:.1f}MB"
                )

    def _generate_report(self):
        """Generate comprehensive test report."""
        total_duration = time.time() - self.start_time
        passed_tests = sum(1 for r in self.results if r.passed)
        failed_tests = len(self.results) - passed_tests

        # JSON report
        report_data = {
            "summary": {
                "total_tests": len(self.results),
                "passed": passed_tests,
                "failed": failed_tests,
                "duration": total_duration,
                "timestamp": time.time(),
            },
            "results": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "duration": r.duration,
                    "message": r.message,
                    "details": r.details,
                }
                for r in self.results
            ],
        }

        with open(self.output_dir / "smoke_test_results.json", "w") as f:
            json.dump(report_data, f, indent=2)

        # HTML report
        self._generate_html_report(report_data)

        # JUnit XML for CI integration
        self._generate_junit_xml()

    def _generate_html_report(self, report_data):
        """Generate HTML report."""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Deployment Smoke Test Results</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; }}
                .passed {{ color: green; }}
                .failed {{ color: red; }}
                .test-result {{ margin: 10px 0; padding: 10px; border: 1px solid #ddd; }}
                .test-result.passed {{ border-left: 5px solid green; }}
                .test-result.failed {{ border-left: 5px solid red; }}
            </style>
        </head>
        <body>
            <h1>Deployment Smoke Test Results</h1>

            <div class="summary">
                <h2>Summary</h2>
                <p>Total Tests: {report_data["summary"]["total_tests"]}</p>
                <p class="passed">Passed: {report_data["summary"]["passed"]}</p>
                <p class="failed">Failed: {report_data["summary"]["failed"]}</p>
                <p>Duration: {report_data["summary"]["duration"]:.2f} seconds</p>
            </div>

            <h2>Test Results</h2>
        """

        for result in report_data["results"]:
            status_class = "passed" if result["passed"] else "failed"
            status_text = "✓ PASSED" if result["passed"] else "✗ FAILED"

            html_content += f"""
            <div class="test-result {status_class}">
                <h3>{result["name"]} - {status_text}</h3>
                <p>Duration: {result["duration"]:.2f}s</p>
                <p>Message: {result["message"]}</p>
            </div>
            """

        html_content += """
        </body>
        </html>
        """

        with open(self.output_dir / "smoke_test_report.html", "w") as f:
            f.write(html_content)

    def _generate_junit_xml(self):
        """Generate JUnit XML for CI integration."""
        total_duration = sum(r.duration for r in self.results)
        failed_count = sum(1 for r in self.results if not r.passed)

        xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="DeploymentSmokeTests" tests="{len(self.results)}" failures="{failed_count}" time="{total_duration:.2f}">
"""

        for result in self.results:
            xml_content += (
                f'  <testcase name="{result.name}" time="{result.duration:.2f}"'
            )

            if result.passed:
                xml_content += " />\n"
            else:
                xml_content += (
                    f'>\n    <failure message="{result.message}" />\n  </testcase>\n'
                )

        xml_content += "</testsuite>\n"

        with open(self.output_dir / "smoke_test_results.xml", "w") as f:
            f.write(xml_content)


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Run deployment smoke tests")
    parser.add_argument(
        "--output-dir",
        default="deployment-test-results",
        help="Output directory for test results",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    smoke_tests = DeploymentSmokeTests(args.output_dir)
    success = await smoke_tests.run_all_tests()

    if success:
        print("\n✓ All deployment smoke tests passed!")
        sys.exit(0)
    else:
        print("\n✗ Some deployment smoke tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
