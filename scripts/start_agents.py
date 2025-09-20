#!/usr/bin/env python3
"""Script to start all agent servers."""

import asyncio
import signal
import subprocess
import sys
import time
from pathlib import Path

import structlog

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agents.monitoring.health_checker import AgentHealthChecker
from agents.shared.logging_config import setup_logging

# Set up logging
setup_logging()
logger = structlog.get_logger(__name__)

# Agent server configurations
AGENTS = {
    "hill_metrics": {
        "module": "agents.hill_metrics.server",
        "port": 8001,
        "description": "Hill Metrics Agent - Topographical data processing",
    },
    "weather": {
        "module": "agents.weather.server",
        "port": 8002,
        "description": "Weather Agent - Real-time and historical weather data",
    },
    "equipment": {
        "module": "agents.equipment.server",
        "port": 8003,
        "description": "Equipment Agent - Ski infrastructure and facility information",
    },
}

MONITORING_DASHBOARD = {
    "module": "agents.monitoring.dashboard",
    "port": 8000,
    "description": "Monitoring Dashboard - Agent health and performance monitoring",
}


class AgentManager:
    """Manager for starting and stopping agent servers."""

    def __init__(self):
        self.processes: dict[str, subprocess.Popen] = {}
        self.shutdown_requested = False

        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, initiating shutdown")
        self.shutdown_requested = True

    def start_agent(self, agent_name: str, config: dict) -> bool:
        """
        Start a single agent server.

        Args:
            agent_name: Name of the agent
            config: Agent configuration

        Returns:
            True if started successfully
        """
        try:
            logger.info(
                "Starting agent",
                agent=agent_name,
                module=config["module"],
                port=config["port"],
            )

            # Start the agent process
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    config["module"],
                ],
                cwd=project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            self.processes[agent_name] = process

            # Give the process a moment to start
            time.sleep(1)

            # Check if process is still running
            if process.poll() is None:
                logger.info(
                    "Agent started successfully",
                    agent=agent_name,
                    pid=process.pid,
                )
                return True
            else:
                stdout, stderr = process.communicate()
                logger.error(
                    "Agent failed to start",
                    agent=agent_name,
                    stdout=stdout,
                    stderr=stderr,
                )
                return False

        except Exception as e:
            logger.error(
                "Failed to start agent",
                agent=agent_name,
                error=str(e),
                exc_info=True,
            )
            return False

    def start_monitoring_dashboard(self) -> bool:
        """Start the monitoring dashboard."""
        try:
            logger.info(
                "Starting monitoring dashboard",
                module=MONITORING_DASHBOARD["module"],
                port=MONITORING_DASHBOARD["port"],
            )

            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    MONITORING_DASHBOARD["module"],
                ],
                cwd=project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            self.processes["monitoring"] = process

            # Give the process a moment to start
            time.sleep(1)

            if process.poll() is None:
                logger.info(
                    "Monitoring dashboard started successfully",
                    pid=process.pid,
                )
                return True
            else:
                stdout, stderr = process.communicate()
                logger.error(
                    "Monitoring dashboard failed to start",
                    stdout=stdout,
                    stderr=stderr,
                )
                return False

        except Exception as e:
            logger.error(
                "Failed to start monitoring dashboard",
                error=str(e),
                exc_info=True,
            )
            return False

    def stop_all_agents(self):
        """Stop all running agent processes."""
        logger.info("Stopping all agents")

        for agent_name, process in self.processes.items():
            try:
                if process.poll() is None:  # Process is still running
                    logger.info(f"Stopping {agent_name}", pid=process.pid)
                    process.terminate()

                    # Wait for graceful shutdown
                    try:
                        process.wait(timeout=10)
                        logger.info(f"Agent {agent_name} stopped gracefully")
                    except subprocess.TimeoutExpired:
                        logger.warning(f"Force killing {agent_name}")
                        process.kill()
                        process.wait()

            except Exception as e:
                logger.error(
                    f"Error stopping {agent_name}",
                    error=str(e),
                    exc_info=True,
                )

        self.processes.clear()

    async def wait_for_agents_healthy(self, timeout: float = 60.0) -> bool:
        """Wait for all agents to become healthy."""
        agent_urls = {
            name: f"http://localhost:{config['port']}"
            for name, config in AGENTS.items()
        }

        health_checker = AgentHealthChecker(agent_urls)

        try:
            return await health_checker.wait_for_agents(timeout)
        finally:
            await health_checker.close()

    async def run(self):
        """Main run loop."""
        logger.info("Starting Alpine Ski Simulator Agent Servers")

        # Start all agents
        failed_agents = []
        for agent_name, config in AGENTS.items():
            if not self.start_agent(agent_name, config):
                failed_agents.append(agent_name)

        if failed_agents:
            logger.error(
                "Some agents failed to start",
                failed_agents=failed_agents,
            )
            self.stop_all_agents()
            return 1

        # Start monitoring dashboard
        if not self.start_monitoring_dashboard():
            logger.error("Failed to start monitoring dashboard")
            self.stop_all_agents()
            return 1

        # Wait for agents to become healthy
        logger.info("Waiting for agents to become healthy...")
        if not await self.wait_for_agents_healthy():
            logger.error("Agents did not become healthy within timeout")
            self.stop_all_agents()
            return 1

        logger.info("All agents are healthy and ready")

        # Print status
        print("\n" + "=" * 60)
        print("Alpine Ski Simulator Agent Servers - READY")
        print("=" * 60)

        for _agent_name, config in AGENTS.items():
            print(f"• {config['description']}")
            print(f"  URL: http://localhost:{config['port']}")
            print(f"  Health: http://localhost:{config['port']}/health")
            print()

        print(f"• {MONITORING_DASHBOARD['description']}")
        print(f"  URL: http://localhost:{MONITORING_DASHBOARD['port']}")
        print()

        print("Press Ctrl+C to stop all agents")
        print("=" * 60)

        # Main loop - wait for shutdown signal
        try:
            while not self.shutdown_requested:
                await asyncio.sleep(1)

                # Check if any processes have died
                dead_processes = []
                for agent_name, process in self.processes.items():
                    if process.poll() is not None:
                        dead_processes.append(agent_name)

                if dead_processes:
                    logger.error(
                        "Some agents have died",
                        dead_agents=dead_processes,
                    )
                    break

        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")

        # Shutdown
        self.stop_all_agents()
        logger.info("All agents stopped")
        return 0


async def main():
    """Main function."""
    manager = AgentManager()
    return await manager.run()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
