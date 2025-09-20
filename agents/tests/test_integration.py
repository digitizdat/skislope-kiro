"""Integration tests for agent servers and API contracts."""

import asyncio
import json
import time
from typing import Dict, Any

import httpx
import pytest
import structlog
from fastapi.testclient import TestClient

# Import all agent servers
from agents.hill_metrics.server import app as hill_metrics_app
from agents.weather.server import app as weather_app
from agents.equipment.server import app as equipment_app

logger = structlog.get_logger(__name__)


class TestAgentServerIntegration:
    """Integration tests for agent servers."""
    
    @pytest.fixture
    def hill_metrics_client(self):
        """Test client for Hill Metrics agent."""
        return TestClient(hill_metrics_app)
    
    @pytest.fixture
    def weather_client(self):
        """Test client for Weather agent."""
        return TestClient(weather_app)
    
    @pytest.fixture
    def equipment_client(self):
        """Test client for Equipment agent."""
        return TestClient(equipment_app)
    
    def test_hill_metrics_health_check(self, hill_metrics_client):
        """Test Hill Metrics agent health check."""
        response = hill_metrics_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "Hill Metrics Agent" in data["service"]
    
    def test_weather_health_check(self, weather_client):
        """Test Weather agent health check."""
        response = weather_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "Weather Agent" in data["service"]
    
    def test_equipment_health_check(self, equipment_client):
        """Test Equipment agent health check."""
        response = equipment_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "Equipment Agent" in data["service"]


class TestJSONRPCAPIContracts:
    """Test JSON-RPC API contracts between frontend and backend."""
    
    @pytest.fixture
    def hill_metrics_client(self):
        return TestClient(hill_metrics_app)
    
    @pytest.fixture
    def weather_client(self):
        return TestClient(weather_app)
    
    @pytest.fixture
    def equipment_client(self):
        return TestClient(equipment_app)
    
    def _make_jsonrpc_request(self, client: TestClient, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make a JSON-RPC request and return the response."""
        request_data = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": "test-request"
        }
        
        response = client.post(
            "/jsonrpc",
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200, f"HTTP error: {response.status_code} - {response.text}"
        return response.json()
    
    def test_hill_metrics_api_contract(self, hill_metrics_client):
        """Test Hill Metrics API contract matches frontend expectations."""
        # Test the exact method name the frontend calls
        params = {
            "bounds": {
                "north": 46.0,
                "south": 45.9,
                "east": 7.1,
                "west": 7.0
            },
            "grid_size": "64x64",
            "include_surface_classification": True
        }
        
        response = self._make_jsonrpc_request(
            hill_metrics_client, 
            "getHillMetrics",  # Frontend expects camelCase
            params
        )
        
        # Should not have an error
        assert "error" not in response, f"JSON-RPC error: {response.get('error')}"
        assert "result" in response
        
        # Validate response structure
        result = response["result"]
        assert "hill_metrics" in result
        assert "processing_time_ms" in result
        
        logger.info("Hill Metrics API contract test passed", method="getHillMetrics")
    
    def test_weather_api_contract(self, weather_client):
        """Test Weather API contract matches frontend expectations."""
        params = {
            "area": {
                "id": "test-area",
                "name": "Test Area",
                "location": "Test Location",
                "country": "Test Country",
                "bounds": {
                    "northEast": {"lat": 46.0, "lng": 7.1},
                    "southWest": {"lat": 45.9, "lng": 7.0}
                },
                "elevation": {"min": 1000, "max": 3000},
                "previewImage": "test.jpg",
                "agentEndpoints": {
                    "hillMetrics": "http://localhost:8001",
                    "weather": "http://localhost:8002",
                    "equipment": "http://localhost:8003"
                },
                "fisCompatible": True
            },
            "timestamp": "2024-01-01T12:00:00Z",
            "include_forecast": True
        }
        
        response = self._make_jsonrpc_request(
            weather_client,
            "getWeatherData",  # Frontend expects camelCase
            params
        )
        
        # Should not have an error
        assert "error" not in response, f"JSON-RPC error: {response.get('error')}"
        assert "result" in response
        
        logger.info("Weather API contract test passed", method="getWeatherData")
    
    def test_equipment_api_contract(self, equipment_client):
        """Test Equipment API contract matches frontend expectations."""
        params = {
            "area": {
                "id": "test-area",
                "name": "Test Area",
                "location": "Test Location",
                "country": "Test Country",
                "bounds": {
                    "northEast": {"lat": 46.0, "lng": 7.1},
                    "southWest": {"lat": 45.9, "lng": 7.0}
                },
                "elevation": {"min": 1000, "max": 3000},
                "previewImage": "test.jpg",
                "agentEndpoints": {
                    "hillMetrics": "http://localhost:8001",
                    "weather": "http://localhost:8002",
                    "equipment": "http://localhost:8003"
                },
                "fisCompatible": True
            },
            "include_status": True
        }
        
        response = self._make_jsonrpc_request(
            equipment_client,
            "getEquipmentData",  # Frontend expects camelCase
            params
        )
        
        # Should not have an error
        assert "error" not in response, f"JSON-RPC error: {response.get('error')}"
        assert "result" in response
        
        logger.info("Equipment API contract test passed", method="getEquipmentData")
    
    def test_method_not_found_error(self, hill_metrics_client):
        """Test that calling non-existent methods returns proper error."""
        response = self._make_jsonrpc_request(
            hill_metrics_client,
            "nonExistentMethod",
            {}
        )
        
        # Should have an error
        assert "error" in response
        assert response["error"]["code"] == -32601  # Method not found
        assert "not found" in response["error"]["message"].lower()
    
    def test_invalid_params_error(self, hill_metrics_client):
        """Test that invalid parameters return proper error."""
        # Missing required bounds parameter
        response = self._make_jsonrpc_request(
            hill_metrics_client,
            "getHillMetrics",
            {"invalid_param": "test"}
        )
        
        # Should have an error (either validation error or method-specific error)
        assert "error" in response
        logger.info("Invalid params test passed", error_code=response["error"]["code"])


class TestCORSIntegration:
    """Test CORS configuration for cross-origin requests."""
    
    @pytest.fixture
    def hill_metrics_client(self):
        return TestClient(hill_metrics_app)
    
    def test_cors_preflight_request(self, hill_metrics_client):
        """Test CORS preflight OPTIONS request."""
        response = hill_metrics_client.options(
            "/jsonrpc",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            }
        )
        
        # Should allow the request
        assert response.status_code in [200, 204]
        
        # Check CORS headers
        headers = response.headers
        assert "access-control-allow-origin" in headers
        assert "access-control-allow-methods" in headers
        assert "POST" in headers.get("access-control-allow-methods", "")
    
    def test_cors_actual_request(self, hill_metrics_client):
        """Test actual CORS request with Origin header."""
        request_data = {
            "jsonrpc": "2.0",
            "method": "getHillMetrics",
            "params": {
                "bounds": {
                    "north": 46.0,
                    "south": 45.9,
                    "east": 7.1,
                    "west": 7.0
                }
            },
            "id": "cors-test"
        }
        
        response = hill_metrics_client.post(
            "/jsonrpc",
            json=request_data,
            headers={
                "Origin": "http://localhost:5173",
                "Content-Type": "application/json"
            }
        )
        
        assert response.status_code == 200
        
        # Check CORS headers in response
        headers = response.headers
        assert "access-control-allow-origin" in headers


class TestEndToEndIntegration:
    """End-to-end integration tests simulating frontend behavior."""
    
    @pytest.fixture
    def all_clients(self):
        """All agent clients for end-to-end testing."""
        return {
            "hill_metrics": TestClient(hill_metrics_app),
            "weather": TestClient(weather_app),
            "equipment": TestClient(equipment_app)
        }
    
    def test_terrain_loading_workflow(self, all_clients):
        """Test the complete terrain loading workflow."""
        # Simulate the exact workflow the frontend uses
        
        # 1. Check all agents are healthy
        for agent_name, client in all_clients.items():
            response = client.get("/health")
            assert response.status_code == 200, f"{agent_name} agent not healthy"
        
        # 2. Request hill metrics (primary data for terrain)
        hill_metrics_params = {
            "bounds": {
                "north": 46.0,
                "south": 45.9,
                "east": 7.1,
                "west": 7.0
            },
            "grid_size": "64x64",
            "include_surface_classification": True
        }
        
        hill_response = self._make_jsonrpc_request(
            all_clients["hill_metrics"],
            "getHillMetrics",
            hill_metrics_params
        )
        
        assert "error" not in hill_response
        assert "result" in hill_response
        
        # 3. Request weather data (supplementary)
        weather_params = {
            "area": {
                "id": "test-area",
                "name": "Test Area",
                "location": "Test Location", 
                "country": "Test Country",
                "bounds": {
                    "northEast": {"lat": 46.0, "lng": 7.1},
                    "southWest": {"lat": 45.9, "lng": 7.0}
                },
                "elevation": {"min": 1000, "max": 3000},
                "previewImage": "test.jpg",
                "agentEndpoints": {
                    "hillMetrics": "http://localhost:8001",
                    "weather": "http://localhost:8002", 
                    "equipment": "http://localhost:8003"
                },
                "fisCompatible": True
            }
        }
        
        weather_response = self._make_jsonrpc_request(
            all_clients["weather"],
            "getWeatherData",
            weather_params
        )
        
        assert "error" not in weather_response
        assert "result" in weather_response
        
        # 4. Request equipment data (supplementary)
        equipment_response = self._make_jsonrpc_request(
            all_clients["equipment"],
            "getEquipmentData",
            weather_params  # Same area params
        )
        
        assert "error" not in equipment_response
        assert "result" in equipment_response
        
        logger.info("End-to-end terrain loading workflow test passed")
    
    def _make_jsonrpc_request(self, client: TestClient, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make a JSON-RPC request and return the response."""
        request_data = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": f"e2e-test-{int(time.time())}"
        }
        
        response = client.post(
            "/jsonrpc",
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200, f"HTTP error: {response.status_code} - {response.text}"
        return response.json()


class TestAgentMethodRegistry:
    """Test that all expected methods are registered correctly."""
    
    EXPECTED_METHODS = {
        "hill_metrics": ["getHillMetrics", "getElevationProfile"],
        "weather": ["getWeatherData", "getSkiConditions", "getWeatherAlerts"],
        "equipment": ["getEquipmentData", "getLiftStatus", "getTrailConditions", "getFacilities"]
    }
    
    @pytest.fixture
    def all_clients(self):
        return {
            "hill_metrics": TestClient(hill_metrics_app),
            "weather": TestClient(weather_app),
            "equipment": TestClient(equipment_app)
        }
    
    def test_all_expected_methods_registered(self, all_clients):
        """Test that all expected methods are registered and callable."""
        for agent_name, expected_methods in self.EXPECTED_METHODS.items():
            client = all_clients[agent_name]
            
            for method in expected_methods:
                # Try to call the method (it may fail due to params, but should not be "method not found")
                response = self._make_jsonrpc_request(client, method, {})
                
                # Should not be "method not found" error
                if "error" in response:
                    error_code = response["error"]["code"]
                    assert error_code != -32601, f"Method '{method}' not found in {agent_name} agent"
                    # Other errors (like invalid params) are acceptable for this test
                
                logger.info(f"Method '{method}' is registered in {agent_name} agent")
    
    def _make_jsonrpc_request(self, client: TestClient, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make a JSON-RPC request and return the response."""
        request_data = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": "method-registry-test"
        }
        
        response = client.post(
            "/jsonrpc",
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        return response.json() if response.status_code == 200 else {"error": {"code": response.status_code}}


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v"])