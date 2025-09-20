"""
Agent Lifecycle Manager for test orchestration.

Provides comprehensive agent server lifecycle management during integration testing,
including startup, health validation, graceful shutdown, and timeout handling.
"""

import asyncio
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import httpx

from .config import AgentConfig
from .config import TestConfig
from .logging_utils import TestLogger
from .models import AgentHealthStatus


class AgentState(Enum):
    """Agent server states."""

    STOPPED = "stopped"
    STARTING = "starting"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    STOPPING = "stopping"


@dataclass
class AgentProcess:
    """Information about a running agent process."""

    name: str
    config: AgentConfig
    process: subprocess.Popen | None = None
    state: AgentState = AgentState.STOPPED
    start_time: float | None = None
    health_status: AgentHealthStatus | None = None
    startup_attempts: int = 0
    last_error: str | None = None


class AgentLifecycleManager:
    """
    Manages agent server lifecycle during integration testing.

    Provides comprehensive control over agent startup, health monitoring,
    and graceful shutdown with proper timeout handling and error recovery.
    """

    def __init__(self, config: TestConfig, logger: TestLogger | None = None):
        """
        Initialize the agent lifecycle manager.

        Args:
            config: Test configuration
            logger: Optional test logger
        """
        self.config = config
        self.logger = logger or TestLogger("agent_lifecycle", config)
        self.agents: dict[str, AgentProcess] = {}
        self.http_client: httpx.AsyncClient | None = None
        self.shutdown_requested = False

        # Set up project root path
        self.project_root = Path(__file__).parent.parent.parent.parent

        # Initialize agent processes
        for name, agent_config in config.agents.items():
            if agent_config.enabled:
                self.agents[name] = AgentProcess(name=name, config=agent_config)

    async def __aenter__(self):
        """Async context manager entry."""
        self.http_client = httpx.AsyncClient(
            timeout=self.config.timeouts.network_request
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop_all_agents()
        if self.http_client:
            await self.http_client.aclose()

    def _get_agent_module_path(self, agent_name: str) -> str:
        """Get the Python module path for an agent."""
        module_map = {
            "hill_metrics": "agents.hill_metrics.server",
            "weather": "agents.weather.server",
            "equipment": "agents.equipment.server",
        }

        # For testing, allow any agent name and construct module path
        if agent_name in module_map:
            return module_map[agent_name]
        else:
            # For test agents or unknown agents, construct a generic path
            return f"agents.{agent_name}.server"

    async def start_agent(self, agent_name: str, max_attempts: int = 3) -> bool:
        """
        Start a single agent server.

        Args:
            agent_name: Name of the agent to start
            max_attempts: Maximum startup attempts

        Returns:
            True if agent started successfully and is healthy
        """
        if agent_name not in self.agents:
            self.logger.error(f"Unknown agent: {agent_name}")
            return False

        agent = self.agents[agent_name]

        for attempt in range(1, max_attempts + 1):
            agent.startup_attempts = attempt

            self.logger.info(
                f"Starting agent {agent_name} (attempt {attempt}/{max_attempts})",
                agent=agent_name,
                port=agent.config.port,
                attempt=attempt,
            )

            try:
                # Update state
                agent.state = AgentState.STARTING
                agent.start_time = time.time()

                # Get module path
                module_path = self._get_agent_module_path(agent_name)

                # Start the process
                agent.process = subprocess.Popen(
                    [sys.executable, "-m", module_path],
                    cwd=self.project_root,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    env=dict(os.environ, PYTHONPATH=str(self.project_root)),
                )

                self.logger.debug(
                    "Agent process started", agent=agent_name, pid=agent.process.pid
                )

                # Wait for agent to become ready
                if await self._wait_for_agent_ready(agent):
                    agent.state = AgentState.HEALTHY
                    self.logger.info(
                        f"Agent {agent_name} started successfully",
                        agent=agent_name,
                        pid=agent.process.pid,
                        startup_time=time.time() - agent.start_time,
                    )
                    return True
                else:
                    # Agent failed to become ready
                    await self._cleanup_failed_agent(agent)

            except Exception as e:
                agent.last_error = str(e)
                agent.state = AgentState.FAILED

                self.logger.error(
                    f"Failed to start agent {agent_name}",
                    agent=agent_name,
                    attempt=attempt,
                    error=str(e),
                    exc_info=True,
                )

                await self._cleanup_failed_agent(agent)

            # Wait before retry (except on last attempt)
            if attempt < max_attempts:
                await asyncio.sleep(self.config.retry_delay)

        # All attempts failed
        agent.state = AgentState.FAILED
        self.logger.error(
            f"Agent {agent_name} failed to start after {max_attempts} attempts",
            agent=agent_name,
            last_error=agent.last_error,
        )
        return False

    async def _wait_for_agent_ready(self, agent: AgentProcess) -> bool:
        """
        Wait for an agent to become ready and healthy.

        Args:
            agent: Agent process to wait for

        Returns:
            True if agent becomes ready within timeout
        """
        timeout = self.config.timeouts.agent_startup
        start_time = time.time()
        check_interval = 1.0

        while time.time() - start_time < timeout:
            # Check if process is still running
            if agent.process and agent.process.poll() is not None:
                # Process has terminated
                _stdout, stderr = agent.process.communicate()
                agent.last_error = f"Process terminated: {stderr}"
                return False

            # Try health check
            health_status = await self._check_agent_health(agent)
            if health_status and health_status.is_healthy:
                agent.health_status = health_status
                return True

            await asyncio.sleep(check_interval)

        # Timeout reached
        agent.last_error = f"Timeout waiting for agent to become ready ({timeout}s)"
        return False

    async def _check_agent_health(
        self, agent: AgentProcess
    ) -> AgentHealthStatus | None:
        """
        Check the health of an agent server.

        Args:
            agent: Agent process to check

        Returns:
            AgentHealthStatus if check succeeded, None otherwise
        """
        if not self.http_client:
            return None

        try:
            url = f"http://{agent.config.host}:{agent.config.port}{agent.config.health_endpoint}"
            start_time = time.time()

            response = await self.http_client.get(url)
            response_time = time.time() - start_time

            if response.status_code == 200:
                # Try to get available methods
                available_methods = []
                try:
                    methods_response = await self.http_client.post(
                        f"http://{agent.config.host}:{agent.config.port}",
                        json={
                            "jsonrpc": "2.0",
                            "method": "system.listMethods",
                            "id": 1,
                        },
                    )
                    if methods_response.status_code == 200:
                        methods_data = methods_response.json()
                        if "result" in methods_data:
                            available_methods = methods_data["result"]
                except Exception:
                    # Method discovery failed, but agent is still healthy
                    pass

                # Check for missing required methods
                missing_methods = []
                for required_method in agent.config.required_methods:
                    if required_method not in available_methods:
                        missing_methods.append(required_method)

                status = "healthy" if not missing_methods else "degraded"

                return AgentHealthStatus(
                    name=agent.name,
                    status=status,
                    response_time=response_time,
                    endpoint=url,
                    available_methods=available_methods,
                    missing_methods=missing_methods,
                    last_check=time.time(),
                )
            else:
                return AgentHealthStatus(
                    name=agent.name,
                    status="failed",
                    response_time=response_time,
                    endpoint=url,
                    last_error=f"HTTP {response.status_code}",
                    last_check=time.time(),
                )

        except Exception as e:
            return AgentHealthStatus(
                name=agent.name,
                status="failed",
                endpoint=f"http://{agent.config.host}:{agent.config.port}{agent.config.health_endpoint}",
                last_error=str(e),
                last_check=time.time(),
            )

    async def _cleanup_failed_agent(self, agent: AgentProcess) -> None:
        """Clean up a failed agent process."""
        if agent.process:
            try:
                if agent.process.poll() is None:
                    agent.process.terminate()
                    try:
                        agent.process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        agent.process.kill()
                        agent.process.wait()

                # Capture output for debugging
                if agent.process.stdout and agent.process.stderr:
                    _stdout, stderr = agent.process.communicate()
                    if stderr:
                        self.logger.debug(
                            f"Agent {agent.name} stderr output",
                            agent=agent.name,
                            stderr=stderr,
                        )

            except Exception as e:
                self.logger.warning(
                    f"Error cleaning up failed agent {agent.name}",
                    agent=agent.name,
                    error=str(e),
                )
            finally:
                agent.process = None

    async def start_all_agents(
        self, parallel: bool = True
    ) -> tuple[list[str], list[str]]:
        """
        Start all enabled agents.

        Args:
            parallel: Whether to start agents in parallel

        Returns:
            Tuple of (successful_agents, failed_agents)
        """
        enabled_agents = [
            name for name, agent in self.agents.items() if agent.config.enabled
        ]

        if not enabled_agents:
            self.logger.warning("No agents enabled for startup")
            return [], []

        self.logger.info(
            f"Starting {len(enabled_agents)} agents",
            agents=enabled_agents,
            parallel=parallel,
        )

        successful = []
        failed = []

        if parallel:
            # Start all agents in parallel
            tasks = [
                self.start_agent(agent_name, max_attempts=self.config.retry_attempts)
                for agent_name in enabled_agents
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for agent_name, result in zip(enabled_agents, results, strict=False):
                if isinstance(result, Exception):
                    failed.append(agent_name)
                    self.logger.error(
                        f"Exception starting agent {agent_name}",
                        agent=agent_name,
                        error=str(result),
                    )
                elif result:
                    successful.append(agent_name)
                else:
                    failed.append(agent_name)
        else:
            # Start agents sequentially
            for agent_name in enabled_agents:
                if await self.start_agent(
                    agent_name, max_attempts=self.config.retry_attempts
                ):
                    successful.append(agent_name)
                else:
                    failed.append(agent_name)

        self.logger.info(
            "Agent startup complete",
            successful=successful,
            failed=failed,
            success_rate=f"{len(successful)}/{len(enabled_agents)}",
        )

        return successful, failed

    async def stop_agent(self, agent_name: str, timeout: float | None = None) -> bool:
        """
        Stop a single agent server gracefully.

        Args:
            agent_name: Name of the agent to stop
            timeout: Shutdown timeout (uses config default if None)

        Returns:
            True if agent stopped successfully
        """
        if agent_name not in self.agents:
            return False

        agent = self.agents[agent_name]
        if not agent.process or agent.process.poll() is not None:
            # Process is not running
            agent.state = AgentState.STOPPED
            return True

        timeout = timeout or self.config.timeouts.shutdown
        agent.state = AgentState.STOPPING

        self.logger.info(
            f"Stopping agent {agent_name}",
            agent=agent_name,
            pid=agent.process.pid,
            timeout=timeout,
        )

        try:
            # Send SIGTERM for graceful shutdown
            agent.process.terminate()

            # Wait for graceful shutdown
            try:
                agent.process.wait(timeout=timeout)
                agent.state = AgentState.STOPPED
                self.logger.info(f"Agent {agent_name} stopped gracefully")
                return True

            except subprocess.TimeoutExpired:
                # Force kill if graceful shutdown failed
                self.logger.warning(
                    f"Agent {agent_name} did not stop gracefully, force killing",
                    agent=agent_name,
                )
                agent.process.kill()
                agent.process.wait()
                agent.state = AgentState.STOPPED
                return True

        except Exception as e:
            self.logger.error(
                f"Error stopping agent {agent_name}",
                agent=agent_name,
                error=str(e),
                exc_info=True,
            )
            agent.state = AgentState.FAILED
            return False
        finally:
            agent.process = None

    async def stop_all_agents(self, timeout: float | None = None) -> list[str]:
        """
        Stop all running agents gracefully.

        Args:
            timeout: Shutdown timeout per agent

        Returns:
            List of agents that failed to stop
        """
        running_agents = [
            name
            for name, agent in self.agents.items()
            if agent.process and agent.process.poll() is None
        ]

        if not running_agents:
            return []

        self.logger.info(
            f"Stopping {len(running_agents)} agents", agents=running_agents
        )

        # Stop all agents in parallel
        tasks = [self.stop_agent(agent_name, timeout) for agent_name in running_agents]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        failed_to_stop = []
        for agent_name, result in zip(running_agents, results, strict=False):
            if isinstance(result, Exception) or not result:
                failed_to_stop.append(agent_name)

        if failed_to_stop:
            self.logger.warning(
                "Some agents failed to stop cleanly", failed_agents=failed_to_stop
            )
        else:
            self.logger.info("All agents stopped successfully")

        return failed_to_stop

    async def restart_agent(self, agent_name: str) -> bool:
        """
        Restart a single agent server.

        Args:
            agent_name: Name of the agent to restart

        Returns:
            True if agent restarted successfully
        """
        self.logger.info(f"Restarting agent {agent_name}")

        # Stop the agent first
        await self.stop_agent(agent_name)

        # Wait a moment for cleanup
        await asyncio.sleep(1.0)

        # Start the agent again
        return await self.start_agent(agent_name)

    async def check_all_agents_health(self) -> dict[str, AgentHealthStatus]:
        """
        Check health of all running agents.

        Returns:
            Dictionary mapping agent names to their health status
        """
        running_agents = [
            name
            for name, agent in self.agents.items()
            if agent.state in [AgentState.HEALTHY, AgentState.DEGRADED]
        ]

        if not running_agents:
            return {}

        # Check all agents in parallel
        tasks = [
            self._check_agent_health(self.agents[agent_name])
            for agent_name in running_agents
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        health_status = {}
        for agent_name, result in zip(running_agents, results, strict=False):
            if isinstance(result, Exception):
                health_status[agent_name] = AgentHealthStatus(
                    name=agent_name,
                    status="failed",
                    last_error=str(result),
                    last_check=time.time(),
                )
            elif result:
                health_status[agent_name] = result
                # Update agent state based on health
                agent = self.agents[agent_name]
                if result.is_healthy:
                    agent.state = AgentState.HEALTHY
                elif result.is_available:
                    agent.state = AgentState.DEGRADED
                else:
                    agent.state = AgentState.FAILED
                agent.health_status = result

        return health_status

    async def wait_for_agents_ready(
        self, agent_names: list[str] | None = None, timeout: float | None = None
    ) -> bool:
        """
        Wait for specified agents to become ready and healthy.

        Args:
            agent_names: List of agent names to wait for (all if None)
            timeout: Maximum time to wait

        Returns:
            True if all specified agents are ready
        """
        if agent_names is None:
            agent_names = list(self.agents.keys())

        timeout = timeout or self.config.timeouts.agent_startup
        start_time = time.time()
        check_interval = 2.0

        self.logger.info(
            "Waiting for agents to become ready", agents=agent_names, timeout=timeout
        )

        while time.time() - start_time < timeout:
            health_status = await self.check_all_agents_health()

            ready_agents = [
                name
                for name in agent_names
                if name in health_status and health_status[name].is_healthy
            ]

            if len(ready_agents) == len(agent_names):
                elapsed = time.time() - start_time
                self.logger.info(
                    "All agents are ready", agents=agent_names, elapsed_time=elapsed
                )
                return True

            # Log progress
            self.logger.debug(
                f"Waiting for agents: {len(ready_agents)}/{len(agent_names)} ready",
                ready=ready_agents,
                waiting=[name for name in agent_names if name not in ready_agents],
            )

            await asyncio.sleep(check_interval)

        # Timeout reached
        health_status = await self.check_all_agents_health()
        ready_agents = [
            name
            for name in agent_names
            if name in health_status and health_status[name].is_healthy
        ]

        self.logger.warning(
            "Timeout waiting for agents to become ready",
            timeout=timeout,
            ready=ready_agents,
            not_ready=[name for name in agent_names if name not in ready_agents],
        )

        return False

    def get_agent_status(self, agent_name: str) -> dict | None:
        """
        Get detailed status information for an agent.

        Args:
            agent_name: Name of the agent

        Returns:
            Agent status dictionary or None if agent not found
        """
        if agent_name not in self.agents:
            return None

        agent = self.agents[agent_name]

        status = {
            "name": agent.name,
            "state": agent.state.value,
            "config": {
                "host": agent.config.host,
                "port": agent.config.port,
                "enabled": agent.config.enabled,
                "required_methods": agent.config.required_methods,
            },
            "startup_attempts": agent.startup_attempts,
            "last_error": agent.last_error,
        }

        if agent.process:
            status["process"] = {
                "pid": agent.process.pid,
                "running": agent.process.poll() is None,
            }

        if agent.start_time:
            status["uptime"] = time.time() - agent.start_time

        if agent.health_status:
            status["health"] = agent.health_status.to_dict()

        return status

    def get_all_agent_status(self) -> dict[str, dict]:
        """
        Get status information for all agents.

        Returns:
            Dictionary mapping agent names to their status
        """
        return {name: self.get_agent_status(name) for name in self.agents}

    def is_agent_healthy(self, agent_name: str) -> bool:
        """Check if a specific agent is healthy."""
        if agent_name not in self.agents:
            return False

        agent = self.agents[agent_name]
        return agent.state == AgentState.HEALTHY

    def are_all_agents_healthy(self, agent_names: list[str] | None = None) -> bool:
        """Check if all specified agents are healthy."""
        if agent_names is None:
            agent_names = list(self.agents.keys())

        return all(self.is_agent_healthy(name) for name in agent_names)

    def get_healthy_agents(self) -> list[str]:
        """Get list of healthy agent names."""
        return [
            name
            for name, agent in self.agents.items()
            if agent.state == AgentState.HEALTHY
        ]

    def get_failed_agents(self) -> list[str]:
        """Get list of failed agent names."""
        return [
            name
            for name, agent in self.agents.items()
            if agent.state == AgentState.FAILED
        ]
