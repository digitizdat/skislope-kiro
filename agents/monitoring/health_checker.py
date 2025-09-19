"""Health checking utility for agent servers."""

import asyncio
import time
from typing import Dict
from typing import List

import httpx
import structlog

from agents.shared.logging_config import setup_logging

# Set up logging
setup_logging()
logger = structlog.get_logger(__name__)


class AgentHealthChecker:
    """Health checker for agent servers."""
    
    def __init__(self, agents: Dict[str, str]):
        """
        Initialize health checker.
        
        Args:
            agents: Dictionary mapping agent names to their URLs
        """
        self.agents = agents
        self.client = httpx.AsyncClient(timeout=10.0)
    
    async def check_agent_health(self, agent_name: str, agent_url: str) -> Dict:
        """
        Check health of a single agent.
        
        Args:
            agent_name: Name of the agent
            agent_url: URL of the agent
            
        Returns:
            Health check result
        """
        result = {
            "agent": agent_name,
            "url": agent_url,
            "timestamp": time.time(),
            "healthy": False,
            "response_time_ms": None,
            "error": None,
        }
        
        try:
            start_time = time.time()
            
            # Basic health check
            response = await self.client.get(f"{agent_url}/health")
            response_time = (time.time() - start_time) * 1000
            
            result["response_time_ms"] = response_time
            
            if response.status_code == 200:
                result["healthy"] = True
                
                # Try to get detailed health info
                try:
                    detailed_response = await self.client.get(f"{agent_url}/health/detailed")
                    if detailed_response.status_code == 200:
                        result["detailed"] = detailed_response.json()
                except Exception as e:
                    logger.debug(
                        "Failed to get detailed health info",
                        agent=agent_name,
                        error=str(e),
                    )
            else:
                result["error"] = f"HTTP {response.status_code}"
                
        except Exception as e:
            result["error"] = str(e)
            logger.warning(
                "Health check failed",
                agent=agent_name,
                url=agent_url,
                error=str(e),
            )
        
        return result
    
    async def check_all_agents(self) -> List[Dict]:
        """
        Check health of all agents.
        
        Returns:
            List of health check results
        """
        tasks = [
            self.check_agent_health(name, url)
            for name, url in self.agents.items()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                agent_name = list(self.agents.keys())[i]
                final_results.append({
                    "agent": agent_name,
                    "url": self.agents[agent_name],
                    "timestamp": time.time(),
                    "healthy": False,
                    "error": str(result),
                })
            else:
                final_results.append(result)
        
        return final_results
    
    async def wait_for_agents(
        self,
        timeout: float = 60.0,
        check_interval: float = 2.0,
    ) -> bool:
        """
        Wait for all agents to become healthy.
        
        Args:
            timeout: Maximum time to wait in seconds
            check_interval: Time between checks in seconds
            
        Returns:
            True if all agents are healthy, False if timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            results = await self.check_all_agents()
            
            healthy_count = sum(1 for r in results if r["healthy"])
            total_count = len(results)
            
            logger.info(
                "Agent health check",
                healthy=healthy_count,
                total=total_count,
                elapsed_time=time.time() - start_time,
            )
            
            if healthy_count == total_count:
                logger.info("All agents are healthy")
                return True
            
            # Wait before next check
            await asyncio.sleep(check_interval)
        
        logger.warning(
            "Timeout waiting for agents to become healthy",
            timeout=timeout,
        )
        return False
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


async def main():
    """Main function for standalone health checking."""
    agents = {
        "hill_metrics": "http://localhost:8001",
        "weather": "http://localhost:8002",
        "equipment": "http://localhost:8003",
    }
    
    health_checker = AgentHealthChecker(agents)
    
    try:
        logger.info("Starting agent health check")
        
        # Check all agents
        results = await health_checker.check_all_agents()
        
        # Print results
        for result in results:
            status = "✓" if result["healthy"] else "✗"
            response_time = f"{result['response_time_ms']:.0f}ms" if result["response_time_ms"] else "N/A"
            error = f" ({result['error']})" if result.get("error") else ""
            
            print(f"{status} {result['agent']}: {response_time}{error}")
        
        # Summary
        healthy_count = sum(1 for r in results if r["healthy"])
        total_count = len(results)
        
        print(f"\nSummary: {healthy_count}/{total_count} agents healthy")
        
        if healthy_count == total_count:
            logger.info("All agents are healthy")
            return 0
        else:
            logger.warning("Some agents are unhealthy")
            return 1
            
    finally:
        await health_checker.close()


if __name__ == "__main__":
    import sys
    
    exit_code = asyncio.run(main())
    sys.exit(exit_code)