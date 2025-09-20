#!/usr/bin/env python3
"""
Integration test runner that starts agents and runs tests.
This script would have caught the method name mismatches.
"""

import asyncio
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import httpx
import structlog

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logger = structlog.get_logger(__name__)


class IntegrationTestRunner:
    """Manages agent startup and integration test execution."""

    def __init__(self):
        self.agent_processes = []
        self.agents_started = False

    async def start_agents(self) -> bool:
        """Start all agent servers for testing."""
        logger.info("Starting agents for integration testing...")

        try:
            # Start agents using the existing script
            process = subprocess.Popen(
                [sys.executable, "scripts/start_agents.py"],
                cwd=project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            self.agent_processes.append(process)

            # Wait for agents to start
            max_wait = 30  # seconds
            start_time = time.time()

            while time.time() - start_time < max_wait:
                if await self.check_agents_health():
                    logger.info("All agents started successfully")
                    self.agents_started = True
                    return True

                await asyncio.sleep(1)

            logger.error("Agents failed to start within timeout")
            return False

        except Exception as e:
            logger.error("Failed to start agents", error=str(e))
            return False

    async def check_agents_health(self) -> bool:
        """Check if all agents are healthy."""
        agent_urls = [
            "http://localhost:8001/health",
            "http://localhost:8002/health",
            "http://localhost:8003/health",
        ]

        try:
            async with httpx.AsyncClient() as client:
                tasks = [client.get(url, timeout=5.0) for url in agent_urls]
                responses = await asyncio.gather(*tasks, return_exceptions=True)

                for response in responses:
                    if isinstance(response, Exception):
                        return False
                    if response.status_code != 200:
                        return False

                return True

        except Exception:
            return False

    def stop_agents(self):
        """Stop all agent processes."""
        logger.info("Stopping agents...")

        for process in self.agent_processes:
            try:
                # Send SIGTERM
                process.terminate()

                # Wait for graceful shutdown
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    # Force kill if needed
                    process.kill()
                    process.wait()

            except Exception as e:
                logger.error("Error stopping agent process", error=str(e))

        self.agent_processes.clear()
        self.agents_started = False

    async def run_python_integration_tests(self) -> bool:
        """Run Python integration tests."""
        logger.info("Running Python integration tests...")

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "agents/tests/test_integration.py",
                    "-v",
                ],
                cwd=project_root,
                capture_output=True,
                text=True,
            )

            print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)

            if result.returncode == 0:
                logger.info("Python integration tests passed")
                return True
            else:
                logger.error(
                    "Python integration tests failed", return_code=result.returncode
                )
                return False

        except Exception as e:
            logger.error("Failed to run Python integration tests", error=str(e))
            return False

    async def run_frontend_integration_tests(self) -> bool:
        """Run frontend integration tests."""
        logger.info("Running frontend integration tests...")

        try:
            result = subprocess.run(
                ["npm", "run", "test:integration"],
                cwd=project_root,
                capture_output=True,
                text=True,
            )

            print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)

            if result.returncode == 0:
                logger.info("Frontend integration tests passed")
                return True
            else:
                logger.error(
                    "Frontend integration tests failed", return_code=result.returncode
                )
                return False

        except Exception as e:
            logger.error("Failed to run frontend integration tests", error=str(e))
            return False

    async def run_api_contract_tests(self) -> bool:
        """Run API contract verification tests."""
        logger.info("Running API contract tests...")

        # Test method name contracts
        expected_methods = {
            "http://localhost:8001": ["getHillMetrics", "getElevationProfile"],
            "http://localhost:8002": [
                "getWeatherData",
                "getSkiConditions",
                "getWeatherAlerts",
            ],
            "http://localhost:8003": [
                "getEquipmentData",
                "getLiftStatus",
                "getTrailConditions",
                "getFacilities",
            ],
        }

        try:
            async with httpx.AsyncClient() as client:
                for endpoint, methods in expected_methods.items():
                    for method in methods:
                        # Test that method exists (not necessarily that it works with empty params)
                        response = await client.post(
                            f"{endpoint}/jsonrpc",
                            json={
                                "jsonrpc": "2.0",
                                "method": method,
                                "params": {},
                                "id": "contract-test",
                            },
                            timeout=10.0,
                        )

                        if response.status_code != 200:
                            logger.error(
                                f"HTTP error for {method} at {endpoint}",
                                status=response.status_code,
                            )
                            return False

                        data = response.json()

                        # Should not be "method not found" error
                        if "error" in data and data["error"]["code"] == -32601:
                            logger.error(f"Method '{method}' not found at {endpoint}")
                            return False

                        logger.info(f"✅ Method '{method}' exists at {endpoint}")

            logger.info("API contract tests passed")
            return True

        except Exception as e:
            logger.error("API contract tests failed", error=str(e))
            return False

    async def run_all_tests(self) -> bool:
        """Run all integration tests."""
        logger.info("Starting comprehensive integration test suite...")

        # Start agents
        if not await self.start_agents():
            logger.error("Failed to start agents - aborting tests")
            return False

        try:
            # Run all test suites
            results = []

            # 1. API Contract Tests (most important)
            results.append(await self.run_api_contract_tests())

            # 2. Python Integration Tests
            results.append(await self.run_python_integration_tests())

            # 3. Frontend Integration Tests
            results.append(await self.run_frontend_integration_tests())

            # Check results
            passed = sum(results)
            total = len(results)

            if all(results):
                logger.info(f"🎉 All integration tests passed ({passed}/{total})")
                return True
            else:
                logger.error(f"❌ Some integration tests failed ({passed}/{total})")
                return False

        finally:
            # Always stop agents
            self.stop_agents()


async def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description="Run integration tests")
    parser.add_argument(
        "--ci-mode",
        action="store_true",
        help="Run in CI mode with additional reporting",
    )
    parser.add_argument(
        "--output-dir", default="test-results", help="Output directory for test results"
    )

    args = parser.parse_args()

    # Set up CI-specific environment
    if args.ci_mode:
        os.environ["CI"] = "true"
        os.environ["INTEGRATION_TEST_TIMEOUT"] = "300"

        # Create output directory
        output_dir = Path(args.output_dir)
        output_dir.mkdir(exist_ok=True)

        # Configure logging for CI
        import logging

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(output_dir / "integration_tests.log"),
                logging.StreamHandler(),
            ],
        )

    runner = IntegrationTestRunner()

    # Handle Ctrl+C gracefully
    def signal_handler(signum, frame):
        logger.info("Received interrupt signal, stopping agents...")
        runner.stop_agents()
        sys.exit(1)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        success = await runner.run_all_tests()

        if args.ci_mode:
            # Generate CI-specific outputs
            await generate_ci_reports(success, args.output_dir)

        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error("Integration test runner failed", error=str(e), exc_info=True)
        runner.stop_agents()
        sys.exit(1)


async def generate_ci_reports(success: bool, output_dir: str):
    """Generate CI-specific test reports."""
    output_path = Path(output_dir)

    # Generate JUnit XML report
    junit_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="IntegrationTests" tests="1" failures="{0 if success else 1}" time="0">
    <testcase name="FullIntegrationSuite" time="0">
        {"" if success else '<failure message="Integration tests failed" />'}
    </testcase>
</testsuite>
"""

    with open(output_path / "integration_tests.xml", "w") as f:
        f.write(junit_xml)

    # Generate JSON summary
    import json

    summary = {
        "success": success,
        "timestamp": time.time(),
        "environment": {
            "ci": os.environ.get("CI", "false"),
            "python_version": sys.version,
            "platform": sys.platform,
        },
    }

    with open(output_path / "integration_summary.json", "w") as f:
        json.dump(summary, f, indent=2)


if __name__ == "__main__":
    asyncio.run(main())
