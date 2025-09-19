"""
Example usage of the comprehensive error handling and diagnostics system.

This example demonstrates how to use the error handling components
for robust integration testing with proper error recovery and diagnostics.
"""

import asyncio
import logging
from typing import Dict, Any

from ..error_handler import (
    ErrorCategory,
    ErrorType,
    IntegrationTestErrorHandler,
    ErrorRecoveryManager,
    RetryConfig,
    EnhancedTestError
)
from ..models import TestCategory, TestResult, TestStatus


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExampleTestRunner:
    """Example test runner demonstrating error handling usage."""
    
    def __init__(self):
        self.error_handler = IntegrationTestErrorHandler(logger)
        self.setup_recovery_strategies()
    
    def setup_recovery_strategies(self):
        """Set up recovery strategies for common errors."""
        recovery_manager = self.error_handler.recovery_manager
        
        # Recovery strategy for agent startup failures
        async def restart_agents(exc: Exception, context: Dict[str, Any]):
            logger.info("Attempting to restart agents...")
            # Simulate agent restart logic
            await asyncio.sleep(1)
            logger.info("Agents restarted successfully")
        
        recovery_manager.register_recovery_strategy(
            "connection refused",
            restart_agents,
            RetryConfig(max_attempts=3, base_delay=2.0)
        )
        
        # Recovery strategy for import failures
        def fix_imports(exc: Exception, context: Dict[str, Any]):
            logger.info("Attempting to fix import issues...")
            # Simulate dependency installation
            logger.info("Dependencies checked and updated")
        
        recovery_manager.register_recovery_strategy(
            "no module named",
            fix_imports,
            RetryConfig(max_attempts=2, base_delay=1.0)
        )
    
    async def run_test_with_error_handling(
        self,
        test_name: str,
        test_func,
        category: TestCategory,
        context: Dict[str, Any] = None
    ) -> TestResult:
        """Run a test with comprehensive error handling."""
        logger.info(f"Running test: {test_name}")
        
        result = TestResult(
            name=test_name,
            category=category,
            status=TestStatus.RUNNING,
            duration=0.0,
            context=context or {}
        )
        
        try:
            # Execute test with retry logic
            test_result = await self.error_handler.recovery_manager.execute_with_recovery(
                test_func,
                retry_config=RetryConfig(max_attempts=3, base_delay=1.0),
                context=context
            )
            
            result.mark_passed(f"Test completed successfully: {test_result}")
            logger.info(f"✅ {test_name} passed")
            
        except EnhancedTestError as e:
            # Enhanced error already has diagnostics
            result.mark_failed(e)
            logger.error(f"❌ {test_name} failed: {e.message}")
            
        except Exception as e:
            # Handle unexpected errors
            enhanced_error = self.error_handler.handle_test_error(
                e,
                test_name,
                ErrorCategory.INFRASTRUCTURE,
                ErrorType.SERVICE_UNAVAILABLE,
                context
            )
            result.mark_failed(enhanced_error)
            logger.error(f"❌ {test_name} failed unexpectedly: {e}")
        
        return result
    
    async def demonstrate_error_scenarios(self):
        """Demonstrate various error scenarios and handling."""
        logger.info("🚀 Starting error handling demonstration")
        
        results = []
        
        # Scenario 1: Successful test
        async def successful_test():
            await asyncio.sleep(0.1)
            return "success"
        
        result1 = await self.run_test_with_error_handling(
            "successful_test",
            successful_test,
            TestCategory.WORKFLOWS,
            {"scenario": "success"}
        )
        results.append(result1)
        
        # Scenario 2: Recoverable network error
        call_count = 0
        async def network_error_test():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary network issue")
            return "recovered"
        
        result2 = await self.run_test_with_error_handling(
            "network_recovery_test",
            network_error_test,
            TestCategory.COMMUNICATION,
            {"scenario": "network_recovery"}
        )
        results.append(result2)
        
        # Scenario 3: Import error (simulated)
        async def import_error_test():
            raise ImportError("No module named 'nonexistent_module'")
        
        result3 = await self.run_test_with_error_handling(
            "import_error_test",
            import_error_test,
            TestCategory.ENVIRONMENT,
            {"scenario": "import_error"}
        )
        results.append(result3)
        
        # Scenario 4: Persistent failure
        async def persistent_failure_test():
            raise TimeoutError("Service consistently unavailable")
        
        result4 = await self.run_test_with_error_handling(
            "persistent_failure_test",
            persistent_failure_test,
            TestCategory.COMMUNICATION,
            {"scenario": "persistent_failure"}
        )
        results.append(result4)
        
        # Print summary
        self.print_test_summary(results)
        
        # Export diagnostics
        self.error_handler.export_diagnostics("temp/error_handling_demo_diagnostics.json")
        logger.info("📊 Diagnostics exported to temp/error_handling_demo_diagnostics.json")
        
        return results
    
    def print_test_summary(self, results: list):
        """Print a summary of test results."""
        logger.info("\n" + "="*60)
        logger.info("TEST SUMMARY")
        logger.info("="*60)
        
        passed = sum(1 for r in results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in results if r.status == TestStatus.FAILED)
        
        logger.info(f"Total tests: {len(results)}")
        logger.info(f"Passed: {passed}")
        logger.info(f"Failed: {failed}")
        logger.info(f"Success rate: {(passed/len(results)*100):.1f}%")
        
        logger.info("\nDetailed Results:")
        for result in results:
            status_icon = "✅" if result.status == TestStatus.PASSED else "❌"
            logger.info(f"{status_icon} {result.name}: {result.message}")
            
            if result.error and hasattr(result.error, 'suggested_fix'):
                logger.info(f"   💡 Suggested fix: {result.error.suggested_fix}")
        
        # Print error summary
        error_summary = self.error_handler.get_error_summary()
        if error_summary["total_errors"] > 0:
            logger.info(f"\nError Summary:")
            logger.info(f"Total errors: {error_summary['total_errors']}")
            logger.info(f"By category: {error_summary['by_category']}")
            logger.info(f"By type: {error_summary['by_type']}")


class SpecificErrorHandlingExamples:
    """Examples of handling specific error types."""
    
    @staticmethod
    async def handle_agent_startup_error():
        """Example of handling agent startup errors."""
        error_handler = IntegrationTestErrorHandler()
        
        try:
            # Simulate agent startup failure
            raise ConnectionRefusedError("Agent server not responding on port 8001")
            
        except Exception as e:
            enhanced_error = error_handler.handle_test_error(
                e,
                "agent_startup_test",
                ErrorCategory.INFRASTRUCTURE,
                ErrorType.AGENT_STARTUP_FAILURE,
                {
                    "agent": "hill_metrics",
                    "port": 8001,
                    "expected_methods": ["get_terrain_data", "get_elevation"]
                }
            )
            
            print(f"Error: {enhanced_error.message}")
            print(f"Category: {enhanced_error.category}")
            print(f"Type: {enhanced_error.error_type}")
            print(f"Suggested fix: {enhanced_error.suggested_fix}")
            
            return enhanced_error
    
    @staticmethod
    async def handle_api_contract_error():
        """Example of handling API contract errors."""
        error_handler = IntegrationTestErrorHandler()
        
        try:
            # Simulate API contract violation
            raise AttributeError("'AgentClient' object has no attribute 'get_weather_data'")
            
        except Exception as e:
            enhanced_error = error_handler.handle_test_error(
                e,
                "api_contract_test",
                ErrorCategory.API_CONTRACT,
                ErrorType.METHOD_NOT_FOUND,
                {
                    "expected_method": "get_weather_data",
                    "available_methods": ["get_weather_info", "get_conditions"],
                    "agent": "weather"
                }
            )
            
            print(f"Error: {enhanced_error.message}")
            print(f"Suggested fix: {enhanced_error.suggested_fix}")
            
            return enhanced_error
    
    @staticmethod
    async def handle_environment_error():
        """Example of handling environment configuration errors."""
        error_handler = IntegrationTestErrorHandler()
        
        try:
            # Simulate environment error
            raise ImportError("No module named 'rasterio'")
            
        except Exception as e:
            enhanced_error = error_handler.handle_test_error(
                e,
                "environment_test",
                ErrorCategory.ENVIRONMENT,
                ErrorType.MISSING_DEPENDENCY,
                {
                    "missing_package": "rasterio",
                    "package_manager": "uv",
                    "required_for": "terrain processing"
                }
            )
            
            print(f"Error: {enhanced_error.message}")
            print(f"Suggested fix: {enhanced_error.suggested_fix}")
            
            return enhanced_error


async def main():
    """Main demonstration function."""
    print("🔧 Error Handling and Diagnostics Demo")
    print("="*50)
    
    # Run main demonstration
    runner = ExampleTestRunner()
    results = await runner.demonstrate_error_scenarios()
    
    print("\n" + "="*50)
    print("🔍 Specific Error Handling Examples")
    print("="*50)
    
    # Demonstrate specific error types
    examples = SpecificErrorHandlingExamples()
    
    print("\n1. Agent Startup Error:")
    await examples.handle_agent_startup_error()
    
    print("\n2. API Contract Error:")
    await examples.handle_api_contract_error()
    
    print("\n3. Environment Error:")
    await examples.handle_environment_error()
    
    print("\n✨ Demo completed! Check the diagnostics file for detailed information.")


if __name__ == "__main__":
    asyncio.run(main())