#!/usr/bin/env python3
"""
Example usage of the Agent Lifecycle Manager.

This script demonstrates how to use the AgentLifecycleManager for integration testing,
including starting agents, checking their health, and graceful shutdown.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from agents.tests.integration.agent_lifecycle import AgentLifecycleManager
from agents.tests.integration.config import get_test_config
from agents.tests.integration.logging_utils import TestLogger


async def main():
    """Demonstrate agent lifecycle management."""
    print("Agent Lifecycle Manager Example")
    print("=" * 40)

    # Get test configuration
    config = get_test_config(
        {"timeouts.agent_startup": 30, "timeouts.shutdown": 10, "log_level": "INFO"}
    )

    # Create logger
    logger = TestLogger("example", config)

    # Use the lifecycle manager
    async with AgentLifecycleManager(config, logger) as manager:
        print(f"\nConfigured agents: {list(manager.agents.keys())}")

        # Start all agents
        print("\n1. Starting all agents...")
        successful, failed = await manager.start_all_agents(parallel=True)

        if successful:
            print(f"✓ Successfully started: {successful}")
        if failed:
            print(f"✗ Failed to start: {failed}")

        if not successful:
            print(
                "No agents started successfully. This is expected if agent servers are not available."
            )
            return

        # Wait for agents to be ready
        print("\n2. Waiting for agents to become ready...")
        ready = await manager.wait_for_agents_ready(timeout=30.0)

        if ready:
            print("✓ All agents are ready and healthy")
        else:
            print("✗ Some agents are not ready")

        # Check agent health
        print("\n3. Checking agent health...")
        health_status = await manager.check_all_agents_health()

        for agent_name, status in health_status.items():
            health_indicator = "✓" if status.is_healthy else "✗"
            print(
                f"{health_indicator} {agent_name}: {status.status} "
                f"(response: {status.response_time:.3f}s)"
            )

            if status.missing_methods:
                print(f"  Missing methods: {status.missing_methods}")

        # Get detailed status
        print("\n4. Agent status details...")
        for agent_name in manager.agents:
            status = manager.get_agent_status(agent_name)
            if status:
                print(f"\n{agent_name}:")
                print(f"  State: {status['state']}")
                print(f"  Port: {status['config']['port']}")
                if "process" in status:
                    print(f"  PID: {status['process']['pid']}")
                    print(f"  Running: {status['process']['running']}")
                if "uptime" in status:
                    print(f"  Uptime: {status['uptime']:.1f}s")

        # Test restart functionality
        if successful:
            print(f"\n5. Testing restart of {successful[0]}...")
            restart_success = await manager.restart_agent(successful[0])
            if restart_success:
                print(f"✓ Successfully restarted {successful[0]}")
            else:
                print(f"✗ Failed to restart {successful[0]}")

        # Agents will be stopped automatically when exiting the context manager
        print("\n6. Stopping all agents...")

    print("\n✓ Agent lifecycle management complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
