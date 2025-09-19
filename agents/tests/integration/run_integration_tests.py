#!/usr/bin/env python3
"""
CLI script for running integration tests using the Test Orchestrator.

This script provides a command-line interface for executing integration tests
with various options for test selection, execution mode, and reporting.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import List, Optional

from agents.tests.integration.test_orchestrator import IntegrationTestOrchestrator
from agents.tests.integration.config import get_test_config, TestEnvironment
from agents.tests.integration.models import TestCategory


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run integration tests for the Alpine Ski Slope Environment Viewer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full test suite
  python run_integration_tests.py

  # Run specific test categories
  python run_integration_tests.py --categories environment api_contracts

  # Run smoke tests only
  python run_integration_tests.py --smoke

  # Run performance tests only
  python run_integration_tests.py --performance

  # Run with custom timeout
  python run_integration_tests.py --timeout 600

  # Run in CI mode with verbose output
  python run_integration_tests.py --ci --verbose

  # Save results to custom location
  python run_integration_tests.py --output-dir ./test_results
        """
    )
    
    # Test selection options
    test_group = parser.add_mutually_exclusive_group()
    test_group.add_argument(
        "--categories",
        nargs="+",
        choices=["environment", "api_contracts", "communication", "workflows", "performance"],
        help="Run specific test categories"
    )
    test_group.add_argument(
        "--smoke",
        action="store_true",
        help="Run smoke tests only (environment + api_contracts)"
    )
    test_group.add_argument(
        "--performance",
        action="store_true",
        help="Run performance tests only"
    )
    
    # Execution options
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Test execution timeout in seconds (default: 300)"
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        default=True,
        help="Enable parallel test execution (default: True)"
    )
    parser.add_argument(
        "--no-parallel",
        action="store_true",
        help="Disable parallel test execution"
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="Maximum number of parallel workers (default: 4)"
    )
    
    # Environment options
    parser.add_argument(
        "--ci",
        action="store_true",
        help="Run in CI mode with appropriate timeouts and logging"
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Force local development mode"
    )
    
    # Output options
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress non-essential output"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory to save test results (default: temp/integration_tests)"
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        help="Save results as JSON to specified file"
    )
    
    # Agent options
    parser.add_argument(
        "--skip-agent-startup",
        action="store_true",
        help="Skip automatic agent startup (assume agents are already running)"
    )
    parser.add_argument(
        "--agent-timeout",
        type=int,
        default=30,
        help="Agent startup timeout in seconds (default: 30)"
    )
    
    return parser.parse_args()


def setup_config(args: argparse.Namespace) -> dict:
    """Set up test configuration based on command line arguments."""
    config_overrides = {}
    
    # Set environment
    if args.ci:
        config_overrides["environment"] = TestEnvironment.CI
    elif args.local:
        config_overrides["environment"] = TestEnvironment.LOCAL
    
    # Set timeouts
    config_overrides["timeouts.test_execution"] = args.timeout
    config_overrides["timeouts.agent_startup"] = args.agent_timeout
    
    # Set parallel execution
    if args.no_parallel:
        config_overrides["parallel_execution"] = False
    else:
        config_overrides["parallel_execution"] = args.parallel
    
    config_overrides["max_workers"] = args.max_workers
    
    # Set logging level
    if args.verbose:
        config_overrides["log_level"] = "DEBUG"
    elif args.quiet:
        config_overrides["log_level"] = "WARNING"
    
    # Set output directory
    if args.output_dir:
        config_overrides["env_config.temp_dir"] = args.output_dir / "temp"
        config_overrides["env_config.log_dir"] = args.output_dir / "logs"
    
    return config_overrides


def parse_categories(category_names: List[str]) -> List[TestCategory]:
    """Parse category names to TestCategory enums."""
    category_map = {
        "environment": TestCategory.ENVIRONMENT,
        "api_contracts": TestCategory.API_CONTRACTS,
        "communication": TestCategory.COMMUNICATION,
        "workflows": TestCategory.WORKFLOWS,
        "performance": TestCategory.PERFORMANCE
    }
    
    return [category_map[name] for name in category_names]


async def run_tests(args: argparse.Namespace) -> int:
    """Run the integration tests based on arguments."""
    # Set up configuration
    config_overrides = setup_config(args)
    config = get_test_config(config_overrides)
    
    # Create orchestrator
    orchestrator = IntegrationTestOrchestrator(config)
    
    try:
        async with orchestrator:
            print("🚀 Starting integration test execution...")
            print(f"Environment: {config.environment.value}")
            print(f"Parallel execution: {config.parallel_execution}")
            print(f"Max workers: {config.max_workers}")
            print(f"Timeout: {config.timeouts.test_execution}s")
            print()
            
            # Determine which tests to run
            if args.smoke:
                print("Running smoke tests...")
                results = await orchestrator.run_smoke_tests()
            elif args.performance:
                print("Running performance tests...")
                results = await orchestrator.run_performance_tests()
            elif args.categories:
                categories = parse_categories(args.categories)
                print(f"Running selected categories: {[cat.value for cat in categories]}")
                results = await orchestrator.run_selective_tests(categories)
            else:
                print("Running full test suite...")
                results = await orchestrator.run_full_suite()
            
            # Print results summary
            print("\n" + "="*60)
            print("TEST EXECUTION SUMMARY")
            print("="*60)
            print(f"Total tests: {results.summary.total_tests}")
            print(f"Passed: {results.summary.passed} ✅")
            print(f"Failed: {results.summary.failed} ❌")
            print(f"Skipped: {results.summary.skipped} ⏭️")
            print(f"Errors: {results.summary.errors} 💥")
            print(f"Duration: {results.summary.duration:.2f}s")
            print(f"Success rate: {results.summary.success_rate:.1f}%")
            print()
            
            # Print category breakdown
            if results.categories:
                print("CATEGORY BREAKDOWN")
                print("-" * 40)
                for category, category_results in results.categories.items():
                    status_icon = "✅" if not category_results.has_failures else "❌"
                    print(f"{status_icon} {category.value}: {category_results.passed}/{category_results.total_tests} passed")
                print()
            
            # Print failed tests details
            failed_tests = results.get_failed_tests()
            if failed_tests:
                print("FAILED TESTS")
                print("-" * 40)
                for test in failed_tests:
                    print(f"❌ {test.name}")
                    if test.error:
                        print(f"   Error: {test.error.message}")
                        if test.error.suggested_fix:
                            print(f"   Fix: {test.error.suggested_fix}")
                    print()
            
            # Print agent health status
            if results.agent_health:
                print("AGENT HEALTH STATUS")
                print("-" * 40)
                for agent in results.agent_health:
                    status_icon = "✅" if agent.is_healthy else "❌" if agent.status == "failed" else "⚠️"
                    response_time = f" ({agent.response_time:.3f}s)" if agent.response_time else ""
                    print(f"{status_icon} {agent.name}: {agent.status}{response_time}")
                print()
            
            # Print environment issues
            if results.environment_issues:
                critical_issues = [issue for issue in results.environment_issues if issue.severity.value in ["critical", "high"]]
                if critical_issues:
                    print("CRITICAL ENVIRONMENT ISSUES")
                    print("-" * 40)
                    for issue in critical_issues:
                        print(f"❌ {issue.component}: {issue.description}")
                        if issue.suggested_fix:
                            print(f"   Fix: {issue.suggested_fix}")
                    print()
            
            # Save JSON output if requested
            if args.json_output:
                with open(args.json_output, 'w') as f:
                    json.dump(results.to_dict(), f, indent=2, default=str)
                print(f"📄 Results saved to: {args.json_output}")
            
            # Return appropriate exit code
            return 0 if results.summary.is_successful else 1
            
    except KeyboardInterrupt:
        print("\n⚠️  Test execution interrupted by user")
        orchestrator.request_shutdown()
        return 130  # Standard exit code for SIGINT
    except Exception as e:
        print(f"\n💥 Test execution failed with error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def main() -> int:
    """Main entry point."""
    args = parse_arguments()
    
    # Validate arguments
    if args.no_parallel and args.parallel:
        print("Error: Cannot specify both --parallel and --no-parallel")
        return 1
    
    if args.verbose and args.quiet:
        print("Error: Cannot specify both --verbose and --quiet")
        return 1
    
    # Run tests
    try:
        return asyncio.run(run_tests(args))
    except Exception as e:
        print(f"Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())