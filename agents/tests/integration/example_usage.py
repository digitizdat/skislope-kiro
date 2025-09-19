#!/usr/bin/env python3
"""
Example usage of the integration testing infrastructure.

This script demonstrates how to use the core testing components
for setting up and running integration tests.
"""

import asyncio
import json
from pathlib import Path

from .config import get_test_config, TestEnvironment
from .models import TestResult, TestCategory, TestStatus, TestResults, Severity
from .logging_utils import TestLogger, DiagnosticCollector, integration_test_context


async def example_basic_usage():
    """Example of basic infrastructure usage."""
    print("=== Integration Testing Infrastructure Example ===\n")
    
    # 1. Get configuration
    print("1. Setting up configuration...")
    config = get_test_config()
    print(f"   Environment: {config.environment.value}")
    print(f"   Log level: {config.log_level.value}")
    print(f"   Parallel execution: {config.parallel_execution}")
    print(f"   Max workers: {config.max_workers}")
    print()
    
    # 2. Create logger
    print("2. Setting up logging...")
    logger = TestLogger("example", config)
    logger.info("Integration testing infrastructure initialized")
    logger.debug("Debug logging is working", component="example")
    print()
    
    # 3. Collect diagnostics
    print("3. Collecting system diagnostics...")
    collector = DiagnosticCollector(config)
    diagnostics = collector.collect_all_diagnostics()
    
    print(f"   Platform: {diagnostics['system']['platform']}")
    print(f"   Python version: {diagnostics['system']['python_version'][:20]}...")
    print(f"   Memory available: {diagnostics['system']['memory']['available'] / (1024**3):.1f} GB")
    print(f"   CPU count: {diagnostics['system']['cpu']['count']}")
    print()
    
    # 4. Create test results
    print("4. Creating test results...")
    results = TestResults()
    
    # Add some example test results
    test1 = TestResult("api_contract_test", TestCategory.API_CONTRACTS, TestStatus.NOT_STARTED, 0.0)
    test1.mark_passed("All API contracts validated successfully")
    
    test2 = TestResult("communication_test", TestCategory.COMMUNICATION, TestStatus.NOT_STARTED, 0.0)
    test2.mark_failed("CORS configuration failed", "Network timeout occurred")
    
    test3 = TestResult("environment_test", TestCategory.ENVIRONMENT, TestStatus.NOT_STARTED, 0.0)
    test3.mark_skipped("SSL validation disabled in test environment")
    
    results.add_result(test1)
    results.add_result(test2)
    results.add_result(test3)
    results.finalize()
    
    print(f"   Total tests: {results.summary.total_tests}")
    print(f"   Passed: {results.summary.passed}")
    print(f"   Failed: {results.summary.failed}")
    print(f"   Skipped: {results.summary.skipped}")
    print(f"   Success rate: {results.summary.success_rate:.1f}%")
    print()
    
    # 5. Use context manager
    print("5. Using test context manager...")
    with integration_test_context("example_test", config, test_id="example_001") as ctx_logger:
        ctx_logger.info("Running example test within context")
        ctx_logger.debug("Context includes test_id", test_id="example_001")
        
        # Simulate some work
        await asyncio.sleep(0.1)
        
        ctx_logger.info("Example test completed successfully")
    print()
    
    # 6. Save results
    print("6. Saving test artifacts...")
    if config.env_config.temp_dir:
        results_file = config.env_config.temp_dir / "example_results.json"
        with open(results_file, 'w') as f:
            json.dump(results.to_dict(), f, indent=2)
        print(f"   Results saved to: {results_file}")
        
        diagnostics_file = collector.save_diagnostics()
        print(f"   Diagnostics saved to: {diagnostics_file}")
    print()
    
    print("=== Example completed successfully ===")


def example_configuration_overrides():
    """Example of using configuration overrides."""
    print("=== Configuration Overrides Example ===\n")
    
    # Override specific settings
    overrides = {
        "max_workers": 2,
        "timeouts.agent_startup": 45,
        "log_level": "INFO",
        "reporting.detail_level": "verbose"
    }
    
    config = get_test_config(overrides)
    
    print("Configuration with overrides:")
    print(f"   Max workers: {config.max_workers}")
    print(f"   Agent startup timeout: {config.timeouts.agent_startup}s")
    print(f"   Log level: {config.log_level.value}")
    print(f"   Reporting detail: {config.reporting.detail_level}")
    print()


def example_error_handling():
    """Example of error handling and diagnostics."""
    print("=== Error Handling Example ===\n")
    
    config = get_test_config()
    logger = TestLogger("error_example", config)
    
    # Create a test result with error
    test_result = TestResult("error_test", TestCategory.WORKFLOWS, TestStatus.NOT_STARTED, 0.0)
    
    try:
        # Simulate an error
        raise ConnectionError("Failed to connect to agent server")
    except ConnectionError as e:
        test_result.mark_failed(e, "Agent connection test failed")
        logger.error("Test failed with connection error", error=str(e))
    
    print(f"Test status: {test_result.status.value}")
    print(f"Error category: {test_result.error.category}")
    print(f"Error severity: {test_result.error.severity.value}")
    print(f"Error message: {test_result.error.message}")
    print(f"Stack trace available: {test_result.error.stack_trace is not None}")
    print()


if __name__ == "__main__":
    # Run examples
    asyncio.run(example_basic_usage())
    example_configuration_overrides()
    example_error_handling()