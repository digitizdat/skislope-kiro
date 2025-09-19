"""
Integration Patterns for WorkflowSimulator

This module demonstrates how to integrate WorkflowSimulator with existing
test infrastructure, CI/CD pipelines, and monitoring systems.
"""

import asyncio
import pytest
import json
import time
from pathlib import Path
from unittest.mock import Mock, AsyncMock
from dataclasses import asdict

from ..workflow_simulator import WorkflowSimulator, WorkflowType
from ..config import get_test_config
from ..agent_lifecycle import AgentLifecycleManager
from ..logging_utils import TestLogger
from ..models import TestResults, TestResult, TestCategory, TestStatus


class TestIntegrationPatterns:
    """Integration patterns for WorkflowSimulator in test suites."""
    
    @pytest.mark.asyncio
    async def test_ci_cd_integration(self):
        """
        Example: Integration with CI/CD pipeline testing.
        
        This shows how to use WorkflowSimulator in automated testing
        pipelines with proper reporting and failure handling.
        """
        config = get_test_config()
        agent_manager = Mock()
        agent_manager.is_agent_healthy.return_value = True
        
        # CI/CD specific configuration
        ci_context = {
            "build_id": "build-12345",
            "commit_sha": "abc123def456",
            "branch": "main",
            "environment": "ci"
        }
        
        test_results = TestResults()
        
        async with WorkflowSimulator(config, agent_manager) as simulator:
            # Run critical workflows for CI/CD
            critical_workflows = [
                WorkflowType.TERRAIN_LOADING,
                WorkflowType.CACHE_INTEGRATION,
                WorkflowType.ERROR_SCENARIOS
            ]
            
            for workflow_type in critical_workflows:
                result = await simulator.simulate_workflow(workflow_type, ci_context)
                
                # Convert to test result
                test_result = TestResult(
                    name=f"ci_workflow_{workflow_type.value}",
                    category=TestCategory.WORKFLOWS,
                    status=TestStatus.PASSED if result.success else TestStatus.FAILED,
                    duration=result.duration,
                    context={
                        **ci_context,
                        "steps_completed": result.steps_completed,
                        "steps_total": result.steps_total
                    }
                )
                
                if result.error:
                    test_result.error = result.error
                    test_result.message = result.error.message
                
                test_results.add_result(test_result)
                
                # Fail fast for critical workflows in CI
                if not result.success and workflow_type == WorkflowType.TERRAIN_LOADING:
                    pytest.fail(f"Critical workflow {workflow_type.value} failed: {result.error.message}")
        
        # Generate CI/CD report
        test_results.finalize()
        
        # Assert CI/CD requirements
        assert test_results.summary.success_rate >= 66.0, "CI/CD requires at least 66% success rate"
        assert test_results.summary.duration < 60.0, "CI/CD tests must complete within 60 seconds"
        
        print(f"CI/CD Results: {test_results.summary.success_rate:.1f}% success in {test_results.summary.duration:.3f}s")
    
    @pytest.mark.asyncio
    async def test_monitoring_integration(self):
        """
        Example: Integration with monitoring and alerting systems.
        
        This demonstrates how to collect metrics and generate alerts
        based on workflow simulation results.
        """
        config = get_test_config()
        agent_manager = Mock()
        agent_manager.is_agent_healthy.return_value = True
        
        # Monitoring configuration
        monitoring_config = {
            "alert_thresholds": {
                "max_duration": 30.0,
                "min_success_rate": 80.0,
                "max_error_rate": 20.0
            },
            "metrics_collection": True,
            "alert_webhook": "https://monitoring.example.com/alerts"
        }
        
        metrics_data = {
            "workflow_durations": [],
            "success_count": 0,
            "failure_count": 0,
            "error_categories": {},
            "performance_metrics": {}
        }
        
        async with WorkflowSimulator(config, agent_manager) as simulator:
            # Run workflows with monitoring
            for workflow_type in WorkflowType:
                result = await simulator.simulate_workflow(workflow_type)
                
                # Collect metrics
                metrics_data["workflow_durations"].append(result.duration)
                
                if result.success:
                    metrics_data["success_count"] += 1
                else:
                    metrics_data["failure_count"] += 1
                    
                    if result.error:
                        category = result.error.category
                        metrics_data["error_categories"][category] = \
                            metrics_data["error_categories"].get(category, 0) + 1
                
                # Extract performance metrics
                if "baseline_metrics" in result.context:
                    baseline = result.context["baseline_metrics"]
                    metrics_data["performance_metrics"][workflow_type.value] = baseline
        
        # Analyze metrics and generate alerts
        total_workflows = metrics_data["success_count"] + metrics_data["failure_count"]
        success_rate = (metrics_data["success_count"] / total_workflows) * 100
        avg_duration = sum(metrics_data["workflow_durations"]) / len(metrics_data["workflow_durations"])
        max_duration = max(metrics_data["workflow_durations"])
        
        alerts = []
        
        # Check thresholds
        if success_rate < monitoring_config["alert_thresholds"]["min_success_rate"]:
            alerts.append({
                "type": "LOW_SUCCESS_RATE",
                "value": success_rate,
                "threshold": monitoring_config["alert_thresholds"]["min_success_rate"]
            })
        
        if max_duration > monitoring_config["alert_thresholds"]["max_duration"]:
            alerts.append({
                "type": "HIGH_DURATION",
                "value": max_duration,
                "threshold": monitoring_config["alert_thresholds"]["max_duration"]
            })
        
        # Log monitoring results
        print(f"📊 Monitoring Results:")
        print(f"  Success Rate: {success_rate:.1f}%")
        print(f"  Average Duration: {avg_duration:.3f}s")
        print(f"  Max Duration: {max_duration:.3f}s")
        print(f"  Alerts Generated: {len(alerts)}")
        
        for alert in alerts:
            print(f"  🚨 {alert['type']}: {alert['value']:.1f} (threshold: {alert['threshold']:.1f})")
    
    @pytest.mark.asyncio
    async def test_regression_testing_integration(self):
        """
        Example: Integration with regression testing suites.
        
        This shows how to use WorkflowSimulator for regression testing
        by comparing results against baseline performance.
        """
        config = get_test_config()
        agent_manager = Mock()
        agent_manager.is_agent_healthy.return_value = True
        
        # Load baseline performance data (would normally be from file)
        baseline_data = {
            WorkflowType.TERRAIN_LOADING: {"duration": 0.5, "steps": 6},
            WorkflowType.CACHE_INTEGRATION: {"duration": 0.3, "steps": 6},
            WorkflowType.OFFLINE_MODE: {"duration": 0.4, "steps": 6}
        }
        
        regression_results = {}
        
        async with WorkflowSimulator(config, agent_manager) as simulator:
            for workflow_type, baseline in baseline_data.items():
                result = await simulator.simulate_workflow(workflow_type)
                
                # Compare against baseline
                duration_ratio = result.duration / baseline["duration"]
                steps_ratio = result.steps_completed / baseline["steps"]
                
                regression_results[workflow_type] = {
                    "current_duration": result.duration,
                    "baseline_duration": baseline["duration"],
                    "duration_ratio": duration_ratio,
                    "current_steps": result.steps_completed,
                    "baseline_steps": baseline["steps"],
                    "steps_ratio": steps_ratio,
                    "regression": duration_ratio > 1.2 or steps_ratio < 0.8  # 20% tolerance
                }
                
                status = "🔴" if regression_results[workflow_type]["regression"] else "🟢"
                print(f"{status} {workflow_type.value}:")
                print(f"  Duration: {result.duration:.3f}s (baseline: {baseline['duration']:.3f}s)")
                print(f"  Steps: {result.steps_completed}/{baseline['steps']}")
        
        # Check for regressions
        regressions = [wf for wf, data in regression_results.items() if data["regression"]]
        
        if regressions:
            regression_details = []
            for workflow_type in regressions:
                data = regression_results[workflow_type]
                regression_details.append(
                    f"{workflow_type.value}: {data['duration_ratio']:.2f}x duration, "
                    f"{data['steps_ratio']:.2f}x steps"
                )
            
            pytest.fail(f"Performance regressions detected: {'; '.join(regression_details)}")
        
        print(f"✅ No regressions detected in {len(baseline_data)} workflows")
    
    @pytest.mark.asyncio
    async def test_load_testing_integration(self):
        """
        Example: Integration with load testing frameworks.
        
        This demonstrates how to use WorkflowSimulator for load testing
        by running multiple concurrent workflow simulations.
        """
        config = get_test_config()
        agent_manager = Mock()
        agent_manager.is_agent_healthy.return_value = True
        
        # Load testing configuration
        load_config = {
            "concurrent_users": 5,
            "test_duration": 10.0,  # seconds
            "ramp_up_time": 2.0,    # seconds
            "target_workflows": [WorkflowType.TERRAIN_LOADING, WorkflowType.CACHE_INTEGRATION]
        }
        
        async def simulate_user_load(user_id: int, simulator: WorkflowSimulator):
            """Simulate load from a single user."""
            user_results = []
            start_time = time.time()
            
            while time.time() - start_time < load_config["test_duration"]:
                # Select random workflow
                import random
                workflow_type = random.choice(load_config["target_workflows"])
                
                result = await simulator.simulate_workflow(workflow_type)
                user_results.append({
                    "user_id": user_id,
                    "workflow": workflow_type.value,
                    "duration": result.duration,
                    "success": result.success,
                    "timestamp": time.time()
                })
                
                # Small delay between requests
                await asyncio.sleep(0.1)
            
            return user_results
        
        async with WorkflowSimulator(config, agent_manager) as simulator:
            # Start concurrent user simulations
            user_tasks = []
            
            for user_id in range(load_config["concurrent_users"]):
                # Stagger user start times (ramp up)
                await asyncio.sleep(load_config["ramp_up_time"] / load_config["concurrent_users"])
                
                task = asyncio.create_task(simulate_user_load(user_id, simulator))
                user_tasks.append(task)
            
            # Wait for all users to complete
            all_results = await asyncio.gather(*user_tasks)
            
            # Analyze load test results
            flat_results = [result for user_results in all_results for result in user_results]
            
            total_requests = len(flat_results)
            successful_requests = sum(1 for r in flat_results if r["success"])
            avg_duration = sum(r["duration"] for r in flat_results) / total_requests
            max_duration = max(r["duration"] for r in flat_results)
            
            requests_per_second = total_requests / load_config["test_duration"]
            success_rate = (successful_requests / total_requests) * 100
            
            print(f"🔥 Load Test Results:")
            print(f"  Concurrent Users: {load_config['concurrent_users']}")
            print(f"  Test Duration: {load_config['test_duration']}s")
            print(f"  Total Requests: {total_requests}")
            print(f"  Requests/Second: {requests_per_second:.1f}")
            print(f"  Success Rate: {success_rate:.1f}%")
            print(f"  Average Duration: {avg_duration:.3f}s")
            print(f"  Max Duration: {max_duration:.3f}s")
            
            # Assert load test requirements
            assert success_rate >= 95.0, f"Load test requires 95% success rate, got {success_rate:.1f}%"
            assert avg_duration < 2.0, f"Load test requires avg duration < 2s, got {avg_duration:.3f}s"


async def generate_test_report():
    """
    Generate a comprehensive test report from workflow simulations.
    
    This example shows how to create detailed reports for stakeholders.
    """
    print("📋 Generating Comprehensive Test Report")
    print("=" * 50)
    
    config = get_test_config()
    agent_manager = Mock()
    agent_manager.is_agent_healthy.return_value = True
    
    report_data = {
        "test_execution": {
            "timestamp": time.time(),
            "environment": config.environment.value,
            "configuration": {
                "agents": list(config.agents.keys()),
                "timeouts": {
                    "agent_startup": config.timeouts.agent_startup,
                    "test_execution": config.timeouts.test_execution
                }
            }
        },
        "workflow_results": {},
        "summary": {},
        "recommendations": []
    }
    
    async with WorkflowSimulator(config, agent_manager) as simulator:
        # Execute all workflows
        results = await simulator.simulate_all_workflows()
        
        # Process results for report
        for workflow_type, result in results.items():
            report_data["workflow_results"][workflow_type.value] = {
                "success": result.success,
                "duration": result.duration,
                "steps_completed": result.steps_completed,
                "steps_total": result.steps_total,
                "error": result.error.message if result.error else None,
                "context_keys": list(result.context.keys())
            }
        
        # Generate summary statistics
        total_workflows = len(results)
        successful_workflows = sum(1 for r in results.values() if r.success)
        total_duration = sum(r.duration for r in results.values())
        
        report_data["summary"] = {
            "total_workflows": total_workflows,
            "successful_workflows": successful_workflows,
            "success_rate": (successful_workflows / total_workflows) * 100,
            "total_duration": total_duration,
            "average_duration": total_duration / total_workflows
        }
        
        # Generate recommendations
        if report_data["summary"]["success_rate"] < 80:
            report_data["recommendations"].append(
                "Success rate is below 80%. Review error handling and agent reliability."
            )
        
        if report_data["summary"]["average_duration"] > 1.0:
            report_data["recommendations"].append(
                "Average workflow duration exceeds 1 second. Consider performance optimization."
            )
        
        # Display report
        print(f"📊 Test Execution Summary:")
        print(f"  Environment: {report_data['test_execution']['environment']}")
        print(f"  Total Workflows: {report_data['summary']['total_workflows']}")
        print(f"  Success Rate: {report_data['summary']['success_rate']:.1f}%")
        print(f"  Total Duration: {report_data['summary']['total_duration']:.3f}s")
        print(f"  Average Duration: {report_data['summary']['average_duration']:.3f}s")
        
        print(f"\n🔍 Workflow Details:")
        for workflow_name, workflow_data in report_data["workflow_results"].items():
            status = "✅" if workflow_data["success"] else "❌"
            print(f"  {status} {workflow_name}: {workflow_data['duration']:.3f}s "
                  f"({workflow_data['steps_completed']}/{workflow_data['steps_total']} steps)")
            
            if workflow_data["error"]:
                print(f"    Error: {workflow_data['error']}")
        
        if report_data["recommendations"]:
            print(f"\n💡 Recommendations:")
            for i, recommendation in enumerate(report_data["recommendations"], 1):
                print(f"  {i}. {recommendation}")
        
        # Save report to file (optional)
        report_file = Path("workflow_test_report.json")
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        print(f"\n📄 Report saved to: {report_file}")


if __name__ == "__main__":
    # Run integration pattern examples
    asyncio.run(generate_test_report())