#!/usr/bin/env python3
"""Script to test all agent servers with sample requests."""

import asyncio
import json
import sys
import time
from pathlib import Path

import httpx
import structlog

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agents.shared.logging_config import setup_logging

# Set up logging
setup_logging()
logger = structlog.get_logger(__name__)

# Test configurations
AGENTS = {
    "hill_metrics": {
        "url": "http://localhost:8001",
        "name": "Hill Metrics Agent",
        "test_request": {
            "jsonrpc": "2.0",
            "method": "get_hill_metrics",
            "params": {
                "bounds": {"north": 46.0, "south": 45.9, "east": 7.1, "west": 7.0},
                "grid_size": "32x32",
                "include_surface_classification": True,
            },
            "id": "test_hill_metrics",
        },
    },
    "weather": {
        "url": "http://localhost:8002",
        "name": "Weather Agent",
        "test_request": {
            "jsonrpc": "2.0",
            "method": "get_weather",
            "params": {
                "latitude": 46.0,
                "longitude": 7.0,
                "include_forecast": True,
                "forecast_days": 3,
            },
            "id": "test_weather",
        },
    },
    "equipment": {
        "url": "http://localhost:8003",
        "name": "Equipment Agent",
        "test_request": {
            "jsonrpc": "2.0",
            "method": "get_equipment_data",
            "params": {
                "north": 46.0,
                "south": 45.9,
                "east": 7.1,
                "west": 7.0,
                "include_lifts": True,
                "include_trails": True,
                "include_facilities": True,
                "include_safety_equipment": True,
            },
            "id": "test_equipment",
        },
    },
}


class AgentTester:
    """Test runner for agent servers."""

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.results = {}

    async def test_agent_health(self, agent_id: str, config: dict) -> dict:
        """Test agent health endpoint."""
        result = {
            "agent": agent_id,
            "test": "health_check",
            "success": False,
            "response_time_ms": None,
            "error": None,
        }

        try:
            start_time = time.time()
            response = await self.client.get(f"{config['url']}/health")
            response_time = (time.time() - start_time) * 1000

            result["response_time_ms"] = response_time
            result["status_code"] = response.status_code

            if response.status_code == 200:
                result["success"] = True
                result["response"] = response.json()
            else:
                result["error"] = f"HTTP {response.status_code}"

        except Exception as e:
            result["error"] = str(e)

        return result

    async def test_agent_jsonrpc(self, agent_id: str, config: dict) -> dict:
        """Test agent JSON-RPC endpoint."""
        result = {
            "agent": agent_id,
            "test": "jsonrpc_request",
            "success": False,
            "response_time_ms": None,
            "error": None,
        }

        try:
            start_time = time.time()
            response = await self.client.post(
                f"{config['url']}/jsonrpc",
                json=config["test_request"],
                headers={"Content-Type": "application/json"},
            )
            response_time = (time.time() - start_time) * 1000

            result["response_time_ms"] = response_time
            result["status_code"] = response.status_code

            if response.status_code == 200:
                response_data = response.json()

                # Check for JSON-RPC error
                if "error" in response_data:
                    result["error"] = f"JSON-RPC error: {response_data['error']}"
                else:
                    result["success"] = True
                    result["response"] = response_data
            else:
                result["error"] = f"HTTP {response.status_code}"

        except Exception as e:
            result["error"] = str(e)

        return result

    async def test_agent_mcp(self, agent_id: str, config: dict) -> dict:
        """Test agent MCP endpoint."""
        result = {
            "agent": agent_id,
            "test": "mcp_tools",
            "success": False,
            "response_time_ms": None,
            "error": None,
        }

        try:
            start_time = time.time()
            response = await self.client.get(f"{config['url']}/mcp/tools")
            response_time = (time.time() - start_time) * 1000

            result["response_time_ms"] = response_time
            result["status_code"] = response.status_code

            if response.status_code == 200:
                result["success"] = True
                result["response"] = response.json()
            else:
                result["error"] = f"HTTP {response.status_code}"

        except Exception as e:
            result["error"] = str(e)

        return result

    async def test_single_agent(self, agent_id: str, config: dict) -> dict:
        """Run all tests for a single agent."""
        print(f"\nTesting {config['name']} ({config['url']})...")

        agent_results = {
            "agent": agent_id,
            "name": config["name"],
            "url": config["url"],
            "tests": {},
        }

        # Test health endpoint
        print("  • Health check...", end=" ")
        health_result = await self.test_agent_health(agent_id, config)
        agent_results["tests"]["health"] = health_result

        if health_result["success"]:
            print(f"✓ ({health_result['response_time_ms']:.0f}ms)")
        else:
            print(f"✗ ({health_result.get('error', 'Unknown error')})")

        # Test JSON-RPC endpoint
        print("  • JSON-RPC request...", end=" ")
        jsonrpc_result = await self.test_agent_jsonrpc(agent_id, config)
        agent_results["tests"]["jsonrpc"] = jsonrpc_result

        if jsonrpc_result["success"]:
            print(f"✓ ({jsonrpc_result['response_time_ms']:.0f}ms)")
        else:
            print(f"✗ ({jsonrpc_result.get('error', 'Unknown error')})")

        # Test MCP endpoint
        print("  • MCP tools...", end=" ")
        mcp_result = await self.test_agent_mcp(agent_id, config)
        agent_results["tests"]["mcp"] = mcp_result

        if mcp_result["success"]:
            print(f"✓ ({mcp_result['response_time_ms']:.0f}ms)")
        else:
            print(f"✗ ({mcp_result.get('error', 'Unknown error')})")

        # Calculate overall success
        all_tests_passed = all(
            test_result["success"] for test_result in agent_results["tests"].values()
        )
        agent_results["overall_success"] = all_tests_passed

        return agent_results

    async def test_all_agents(self) -> dict:
        """Test all agents."""
        print("Alpine Ski Simulator - Agent Testing")
        print("=" * 50)

        all_results = {
            "timestamp": time.time(),
            "agents": {},
        }

        for agent_id, config in AGENTS.items():
            agent_result = await self.test_single_agent(agent_id, config)
            all_results["agents"][agent_id] = agent_result

        return all_results

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


def print_summary(results: dict):
    """Print test summary."""
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)

    total_agents = len(results["agents"])
    successful_agents = sum(
        1
        for agent_result in results["agents"].values()
        if agent_result["overall_success"]
    )

    print(f"Agents tested: {total_agents}")
    print(f"Successful: {successful_agents}")
    print(f"Failed: {total_agents - successful_agents}")
    print()

    for _agent_id, agent_result in results["agents"].items():
        status = "✓" if agent_result["overall_success"] else "✗"
        print(f"{status} {agent_result['name']}")

        for test_name, test_result in agent_result["tests"].items():
            test_status = "✓" if test_result["success"] else "✗"
            response_time = (
                f"{test_result['response_time_ms']:.0f}ms"
                if test_result["response_time_ms"]
                else "N/A"
            )
            error = f" ({test_result['error']})" if test_result.get("error") else ""
            print(f"    {test_status} {test_name}: {response_time}{error}")

    print()

    if successful_agents == total_agents:
        print("🎉 All agents are working correctly!")
        return 0
    else:
        print("❌ Some agents have issues. Check the logs for details.")
        return 1


async def main():
    """Main function."""
    tester = AgentTester()

    try:
        results = await tester.test_all_agents()

        # Save results to file
        results_file = Path("test_results.json")
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2, default=str)

        print(f"\nDetailed results saved to: {results_file}")

        # Print summary and return exit code
        return print_summary(results)

    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        return 1
    except Exception as e:
        logger.error("Test failed with exception", error=str(e), exc_info=True)
        print(f"\nTest failed: {e}")
        return 1
    finally:
        await tester.close()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
