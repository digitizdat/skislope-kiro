"""
Unit tests for Agent Lifecycle Manager.

Tests agent startup, health checking, graceful shutdown, timeout handling,
and error recovery scenarios for the integration testing infrastructure.
"""

import subprocess
import time
from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

import httpx
import pytest

from .agent_lifecycle import AgentLifecycleManager
from .agent_lifecycle import AgentProcess
from .agent_lifecycle import AgentState
from .config import AgentConfig
from .config import TestConfig
from .config import TimeoutConfig
from .logging_utils import TestLogger
from .models import AgentHealthStatus


class TestAgentProcess:
    """Test AgentProcess data class."""

    def test_agent_process_creation(self):
        """Test AgentProcess creation with defaults."""
        config = AgentConfig(name="test_agent", port=8001)
        process = AgentProcess(name="test_agent", config=config)

        assert process.name == "test_agent"
        assert process.config == config
        assert process.process is None
        assert process.state == AgentState.STOPPED
        assert process.start_time is None
        assert process.health_status is None
        assert process.startup_attempts == 0
        assert process.last_error is None


class TestAgentLifecycleManager:
    """Test Agent Lifecycle Manager functionality."""

    @pytest.fixture
    def test_config(self):
        """Create test configuration."""
        return TestConfig(
            agents={
                "test_agent": AgentConfig(
                    name="test_agent", port=8001, required_methods=["test_method"]
                ),
                "disabled_agent": AgentConfig(
                    name="disabled_agent", port=8002, enabled=False
                ),
            },
            timeouts=TimeoutConfig(agent_startup=10, shutdown=5, network_request=3),
        )

    @pytest.fixture
    def mock_logger(self):
        """Create mock logger."""
        logger = Mock(spec=TestLogger)
        logger.info = Mock()
        logger.debug = Mock()
        logger.warning = Mock()
        logger.error = Mock()
        return logger

    @pytest.fixture
    def lifecycle_manager(self, test_config, mock_logger):
        """Create lifecycle manager with test config."""
        return AgentLifecycleManager(test_config, mock_logger)

    def test_initialization(self, lifecycle_manager, test_config):
        """Test lifecycle manager initialization."""
        assert lifecycle_manager.config == test_config
        assert len(lifecycle_manager.agents) == 1  # Only enabled agents
        assert "test_agent" in lifecycle_manager.agents
        assert "disabled_agent" not in lifecycle_manager.agents
        assert lifecycle_manager.http_client is None
        assert not lifecycle_manager.shutdown_requested

    def test_get_agent_module_path(self, lifecycle_manager):
        """Test agent module path resolution."""
        assert (
            lifecycle_manager._get_agent_module_path("hill_metrics")
            == "agents.hill_metrics.server"
        )
        assert (
            lifecycle_manager._get_agent_module_path("weather")
            == "agents.weather.server"
        )
        assert (
            lifecycle_manager._get_agent_module_path("equipment")
            == "agents.equipment.server"
        )

        # Test unknown agent (should construct generic path for testing)
        assert (
            lifecycle_manager._get_agent_module_path("unknown_agent")
            == "agents.unknown_agent.server"
        )

    @pytest.mark.asyncio
    async def test_context_manager(self, lifecycle_manager):
        """Test async context manager functionality."""
        async with lifecycle_manager as manager:
            assert manager.http_client is not None
            assert isinstance(manager.http_client, httpx.AsyncClient)

        # Client should be closed after context exit
        assert lifecycle_manager.http_client is not None  # Reference still exists

    @pytest.mark.asyncio
    async def test_check_agent_health_success(self, lifecycle_manager):
        """Test successful agent health check."""
        agent = lifecycle_manager.agents["test_agent"]

        # Mock HTTP client
        mock_client = AsyncMock()
        lifecycle_manager.http_client = mock_client

        # Mock health endpoint response
        health_response = Mock()
        health_response.status_code = 200
        mock_client.get.return_value = health_response

        # Mock methods endpoint response
        methods_response = Mock()
        methods_response.status_code = 200
        methods_response.json.return_value = {"result": ["test_method", "other_method"]}
        mock_client.post.return_value = methods_response

        with patch(
            "time.time", side_effect=[1000.0, 1000.1, 1000.2]
        ):  # Multiple calls to time.time()
            health_status = await lifecycle_manager._check_agent_health(agent)

        assert health_status is not None
        assert health_status.name == "test_agent"
        assert health_status.status == "healthy"
        assert health_status.response_time > 0
        assert "test_method" in health_status.available_methods
        assert len(health_status.missing_methods) == 0

    @pytest.mark.asyncio
    async def test_check_agent_health_degraded(self, lifecycle_manager):
        """Test agent health check with missing methods."""
        agent = lifecycle_manager.agents["test_agent"]

        mock_client = AsyncMock()
        lifecycle_manager.http_client = mock_client

        # Mock health endpoint response
        health_response = Mock()
        health_response.status_code = 200
        mock_client.get.return_value = health_response

        # Mock methods endpoint response with missing method
        methods_response = Mock()
        methods_response.status_code = 200
        methods_response.json.return_value = {
            "result": ["other_method"]  # Missing "test_method"
        }
        mock_client.post.return_value = methods_response

        health_status = await lifecycle_manager._check_agent_health(agent)

        assert health_status is not None
        assert health_status.status == "degraded"
        assert "test_method" in health_status.missing_methods
        assert health_status.is_available
        assert not health_status.is_healthy

    @pytest.mark.asyncio
    async def test_check_agent_health_failed(self, lifecycle_manager):
        """Test agent health check failure."""
        agent = lifecycle_manager.agents["test_agent"]

        mock_client = AsyncMock()
        lifecycle_manager.http_client = mock_client

        # Mock failed health endpoint response
        health_response = Mock()
        health_response.status_code = 500
        mock_client.get.return_value = health_response

        health_status = await lifecycle_manager._check_agent_health(agent)

        assert health_status is not None
        assert health_status.status == "failed"
        assert health_status.last_error == "HTTP 500"
        assert not health_status.is_healthy
        assert not health_status.is_available

    @pytest.mark.asyncio
    async def test_check_agent_health_network_error(self, lifecycle_manager):
        """Test agent health check with network error."""
        agent = lifecycle_manager.agents["test_agent"]

        mock_client = AsyncMock()
        lifecycle_manager.http_client = mock_client

        # Mock network error
        mock_client.get.side_effect = httpx.ConnectError("Connection failed")

        health_status = await lifecycle_manager._check_agent_health(agent)

        assert health_status is not None
        assert health_status.status == "failed"
        assert "Connection failed" in health_status.last_error

    @pytest.mark.asyncio
    async def test_wait_for_agent_ready_success(self, lifecycle_manager):
        """Test waiting for agent to become ready - success case."""
        agent = lifecycle_manager.agents["test_agent"]

        # Mock process
        mock_process = Mock()
        mock_process.poll.return_value = None  # Process is running
        agent.process = mock_process

        # Mock health check to return healthy after first call
        with patch.object(lifecycle_manager, "_check_agent_health") as mock_health:
            healthy_status = AgentHealthStatus(
                name="test_agent", status="healthy", response_time=0.1
            )
            mock_health.return_value = healthy_status

            result = await lifecycle_manager._wait_for_agent_ready(agent)

            assert result is True
            assert agent.health_status == healthy_status

    @pytest.mark.asyncio
    async def test_wait_for_agent_ready_timeout(self, lifecycle_manager):
        """Test waiting for agent to become ready - timeout case."""
        agent = lifecycle_manager.agents["test_agent"]

        # Mock process
        mock_process = Mock()
        mock_process.poll.return_value = None  # Process is running
        agent.process = mock_process

        # Mock health check to always return unhealthy
        with patch.object(lifecycle_manager, "_check_agent_health") as mock_health:
            unhealthy_status = AgentHealthStatus(
                name="test_agent", status="failed", last_error="Not ready"
            )
            mock_health.return_value = unhealthy_status

            # Use very short timeout for test
            lifecycle_manager.config.timeouts.agent_startup = 0.1

            result = await lifecycle_manager._wait_for_agent_ready(agent)

            assert result is False
            assert "Timeout waiting" in agent.last_error

    @pytest.mark.asyncio
    async def test_wait_for_agent_ready_process_died(self, lifecycle_manager):
        """Test waiting for agent when process dies."""
        agent = lifecycle_manager.agents["test_agent"]

        # Mock process that terminates
        mock_process = Mock()
        mock_process.poll.return_value = 1  # Process terminated
        mock_process.communicate.return_value = ("", "Process error")
        agent.process = mock_process

        result = await lifecycle_manager._wait_for_agent_ready(agent)

        assert result is False
        assert "Process terminated" in agent.last_error

    @pytest.mark.asyncio
    async def test_cleanup_failed_agent(self, lifecycle_manager):
        """Test cleanup of failed agent process."""
        agent = lifecycle_manager.agents["test_agent"]

        # Mock running process
        mock_process = Mock()
        mock_process.poll.return_value = None  # Still running
        mock_process.communicate.return_value = ("stdout", "stderr")
        agent.process = mock_process

        await lifecycle_manager._cleanup_failed_agent(agent)

        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once()
        assert agent.process is None

    @pytest.mark.asyncio
    async def test_cleanup_failed_agent_force_kill(self, lifecycle_manager):
        """Test cleanup with force kill when terminate fails."""
        agent = lifecycle_manager.agents["test_agent"]

        # Mock process that doesn't terminate gracefully
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_process.wait.side_effect = subprocess.TimeoutExpired("cmd", 5)
        agent.process = mock_process

        await lifecycle_manager._cleanup_failed_agent(agent)

        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()
        assert agent.process is None

    @pytest.mark.asyncio
    async def test_start_agent_success(self, lifecycle_manager):
        """Test successful agent startup."""
        with (
            patch("subprocess.Popen") as mock_popen,
            patch.object(lifecycle_manager, "_wait_for_agent_ready", return_value=True),
        ):
            mock_process = Mock()
            mock_process.pid = 12345
            mock_popen.return_value = mock_process

            result = await lifecycle_manager.start_agent("test_agent")

            assert result is True
            agent = lifecycle_manager.agents["test_agent"]
            assert agent.state == AgentState.HEALTHY
            assert agent.process == mock_process
            assert agent.startup_attempts == 1

    @pytest.mark.asyncio
    async def test_start_agent_failure(self, lifecycle_manager):
        """Test agent startup failure."""
        with (
            patch("subprocess.Popen") as mock_popen,
            patch.object(
                lifecycle_manager, "_wait_for_agent_ready", return_value=False
            ),
            patch.object(lifecycle_manager, "_cleanup_failed_agent") as mock_cleanup,
        ):
            mock_process = Mock()
            mock_popen.return_value = mock_process

            result = await lifecycle_manager.start_agent("test_agent", max_attempts=2)

            assert result is False
            agent = lifecycle_manager.agents["test_agent"]
            assert agent.state == AgentState.FAILED
            assert agent.startup_attempts == 2
            assert mock_cleanup.call_count == 2  # Called for each failed attempt

    @pytest.mark.asyncio
    async def test_start_agent_unknown(self, lifecycle_manager):
        """Test starting unknown agent."""
        result = await lifecycle_manager.start_agent("unknown_agent")
        assert result is False

    @pytest.mark.asyncio
    async def test_start_all_agents_parallel(self, lifecycle_manager):
        """Test starting all agents in parallel."""
        with patch.object(
            lifecycle_manager, "start_agent", return_value=True
        ) as mock_start:
            successful, failed = await lifecycle_manager.start_all_agents(parallel=True)

            assert successful == ["test_agent"]
            assert failed == []
            mock_start.assert_called_once_with("test_agent", max_attempts=3)

    @pytest.mark.asyncio
    async def test_start_all_agents_sequential(self, lifecycle_manager):
        """Test starting all agents sequentially."""
        with patch.object(
            lifecycle_manager, "start_agent", return_value=True
        ) as mock_start:
            successful, failed = await lifecycle_manager.start_all_agents(
                parallel=False
            )

            assert successful == ["test_agent"]
            assert failed == []
            mock_start.assert_called_once_with("test_agent", max_attempts=3)

    @pytest.mark.asyncio
    async def test_start_all_agents_with_failures(self, lifecycle_manager):
        """Test starting agents with some failures."""
        with patch.object(lifecycle_manager, "start_agent", return_value=False):
            successful, failed = await lifecycle_manager.start_all_agents()

            assert successful == []
            assert failed == ["test_agent"]

    @pytest.mark.asyncio
    async def test_stop_agent_success(self, lifecycle_manager):
        """Test successful agent stop."""
        agent = lifecycle_manager.agents["test_agent"]

        # Mock running process
        mock_process = Mock()
        mock_process.poll.return_value = None  # Running
        agent.process = mock_process
        agent.state = AgentState.HEALTHY

        result = await lifecycle_manager.stop_agent("test_agent")

        assert result is True
        assert agent.state == AgentState.STOPPED
        assert agent.process is None
        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_agent_force_kill(self, lifecycle_manager):
        """Test agent stop with force kill."""
        agent = lifecycle_manager.agents["test_agent"]

        # Mock process that doesn't terminate gracefully
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_process.wait.side_effect = [
            subprocess.TimeoutExpired("cmd", 5),
            None,
        ]  # First call times out, second succeeds
        agent.process = mock_process
        agent.state = AgentState.HEALTHY

        result = await lifecycle_manager.stop_agent("test_agent")

        assert result is True
        assert agent.state == AgentState.STOPPED
        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_agent_not_running(self, lifecycle_manager):
        """Test stopping agent that's not running."""
        result = await lifecycle_manager.stop_agent("test_agent")
        assert result is True  # Should succeed for already stopped agent

    @pytest.mark.asyncio
    async def test_stop_all_agents(self, lifecycle_manager):
        """Test stopping all agents."""
        # Set up running agent
        agent = lifecycle_manager.agents["test_agent"]
        mock_process = Mock()
        mock_process.poll.return_value = None
        agent.process = mock_process

        with patch.object(
            lifecycle_manager, "stop_agent", return_value=True
        ) as mock_stop:
            failed = await lifecycle_manager.stop_all_agents()

            assert failed == []
            mock_stop.assert_called_once_with("test_agent", None)

    @pytest.mark.asyncio
    async def test_restart_agent(self, lifecycle_manager):
        """Test agent restart."""
        with (
            patch.object(
                lifecycle_manager, "stop_agent", return_value=True
            ) as mock_stop,
            patch.object(
                lifecycle_manager, "start_agent", return_value=True
            ) as mock_start,
        ):
            result = await lifecycle_manager.restart_agent("test_agent")

            assert result is True
            mock_stop.assert_called_once_with("test_agent")
            mock_start.assert_called_once_with("test_agent")

    @pytest.mark.asyncio
    async def test_check_all_agents_health(self, lifecycle_manager):
        """Test checking health of all agents."""
        # Set agent state to healthy
        agent = lifecycle_manager.agents["test_agent"]
        agent.state = AgentState.HEALTHY

        healthy_status = AgentHealthStatus(
            name="test_agent", status="healthy", response_time=0.1
        )

        with patch.object(
            lifecycle_manager, "_check_agent_health", return_value=healthy_status
        ):
            health_status = await lifecycle_manager.check_all_agents_health()

            assert "test_agent" in health_status
            assert health_status["test_agent"] == healthy_status
            assert agent.health_status == healthy_status

    @pytest.mark.asyncio
    async def test_wait_for_agents_ready_success(self, lifecycle_manager):
        """Test waiting for agents to become ready - success."""
        healthy_status = AgentHealthStatus(
            name="test_agent", status="healthy", response_time=0.1
        )

        with patch.object(
            lifecycle_manager,
            "check_all_agents_health",
            return_value={"test_agent": healthy_status},
        ):
            result = await lifecycle_manager.wait_for_agents_ready(timeout=1.0)

            assert result is True

    @pytest.mark.asyncio
    async def test_wait_for_agents_ready_timeout(self, lifecycle_manager):
        """Test waiting for agents to become ready - timeout."""
        unhealthy_status = AgentHealthStatus(
            name="test_agent", status="failed", last_error="Not ready"
        )

        with patch.object(
            lifecycle_manager,
            "check_all_agents_health",
            return_value={"test_agent": unhealthy_status},
        ):
            result = await lifecycle_manager.wait_for_agents_ready(timeout=0.1)

            assert result is False

    def test_get_agent_status(self, lifecycle_manager):
        """Test getting agent status."""
        agent = lifecycle_manager.agents["test_agent"]
        agent.state = AgentState.HEALTHY
        agent.startup_attempts = 2
        agent.last_error = "Previous error"

        # Mock process
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        agent.process = mock_process
        agent.start_time = time.time() - 100  # 100 seconds ago

        # Mock health status
        agent.health_status = AgentHealthStatus(
            name="test_agent", status="healthy", response_time=0.1
        )

        status = lifecycle_manager.get_agent_status("test_agent")

        assert status is not None
        assert status["name"] == "test_agent"
        assert status["state"] == "healthy"
        assert status["startup_attempts"] == 2
        assert status["last_error"] == "Previous error"
        assert status["process"]["pid"] == 12345
        assert status["process"]["running"] is True
        assert status["uptime"] > 0
        assert "health" in status

    def test_get_agent_status_unknown(self, lifecycle_manager):
        """Test getting status for unknown agent."""
        status = lifecycle_manager.get_agent_status("unknown_agent")
        assert status is None

    def test_get_all_agent_status(self, lifecycle_manager):
        """Test getting status for all agents."""
        with patch.object(
            lifecycle_manager, "get_agent_status", return_value={"test": "status"}
        ):
            all_status = lifecycle_manager.get_all_agent_status()

            assert "test_agent" in all_status
            assert all_status["test_agent"] == {"test": "status"}

    def test_is_agent_healthy(self, lifecycle_manager):
        """Test checking if agent is healthy."""
        agent = lifecycle_manager.agents["test_agent"]

        # Test healthy state
        agent.state = AgentState.HEALTHY
        assert lifecycle_manager.is_agent_healthy("test_agent") is True

        # Test unhealthy state
        agent.state = AgentState.FAILED
        assert lifecycle_manager.is_agent_healthy("test_agent") is False

        # Test unknown agent
        assert lifecycle_manager.is_agent_healthy("unknown_agent") is False

    def test_are_all_agents_healthy(self, lifecycle_manager):
        """Test checking if all agents are healthy."""
        agent = lifecycle_manager.agents["test_agent"]

        # Test all healthy
        agent.state = AgentState.HEALTHY
        assert lifecycle_manager.are_all_agents_healthy() is True

        # Test not all healthy
        agent.state = AgentState.FAILED
        assert lifecycle_manager.are_all_agents_healthy() is False

    def test_get_healthy_agents(self, lifecycle_manager):
        """Test getting list of healthy agents."""
        agent = lifecycle_manager.agents["test_agent"]

        # Test healthy agent
        agent.state = AgentState.HEALTHY
        healthy = lifecycle_manager.get_healthy_agents()
        assert healthy == ["test_agent"]

        # Test unhealthy agent
        agent.state = AgentState.FAILED
        healthy = lifecycle_manager.get_healthy_agents()
        assert healthy == []

    def test_get_failed_agents(self, lifecycle_manager):
        """Test getting list of failed agents."""
        agent = lifecycle_manager.agents["test_agent"]

        # Test healthy agent
        agent.state = AgentState.HEALTHY
        failed = lifecycle_manager.get_failed_agents()
        assert failed == []

        # Test failed agent
        agent.state = AgentState.FAILED
        failed = lifecycle_manager.get_failed_agents()
        assert failed == ["test_agent"]


class TestAgentLifecycleIntegration:
    """Integration tests for agent lifecycle management."""

    @pytest.mark.asyncio
    async def test_full_lifecycle_with_mock_agents(self):
        """Test complete agent lifecycle with mocked processes."""
        config = TestConfig(
            agents={
                "mock_agent": AgentConfig(
                    name="mock_agent", port=8001, required_methods=["test_method"]
                )
            },
            timeouts=TimeoutConfig(agent_startup=5, shutdown=3),
        )

        async with AgentLifecycleManager(config) as manager:
            # Mock subprocess and HTTP calls
            with (
                patch("subprocess.Popen") as mock_popen,
                patch.object(manager, "_check_agent_health") as mock_health,
            ):
                # Mock successful process
                mock_process = Mock()
                mock_process.pid = 12345
                mock_process.poll.return_value = None
                mock_popen.return_value = mock_process

                # Mock healthy status
                healthy_status = AgentHealthStatus(
                    name="mock_agent", status="healthy", response_time=0.1
                )
                mock_health.return_value = healthy_status

                # Test startup
                successful, failed = await manager.start_all_agents()
                assert successful == ["mock_agent"]
                assert failed == []

                # Test health check
                health = await manager.check_all_agents_health()
                assert "mock_agent" in health
                assert health["mock_agent"].is_healthy

                # Test status
                assert manager.is_agent_healthy("mock_agent")
                assert manager.are_all_agents_healthy()

                # Test shutdown
                failed_to_stop = await manager.stop_all_agents()
                assert failed_to_stop == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
