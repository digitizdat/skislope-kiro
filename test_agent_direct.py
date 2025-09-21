#!/usr/bin/env python3
"""Direct test of agent JSON-RPC calls to debug the empty response issue."""

import json

import requests


def test_agent_call():
    """Test calling the hill metrics agent directly."""

    # Test data
    request_data = {
        "jsonrpc": "2.0",
        "method": "getHillMetrics",
        "params": {
            "bounds": {"north": 46.0, "south": 45.9, "east": 7.1, "west": 7.0},
            "grid_size": "64x64",
            "include_surface_classification": True,
        },
        "id": 1,
    }

    try:
        # Test health endpoint first
        health_response = requests.get("http://localhost:8001/health", timeout=5)
        print(f"Health check: {health_response.status_code} - {health_response.text}")

        # Test JSON-RPC call
        response = requests.post(
            "http://localhost:8001/jsonrpc",
            json=request_data,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )

        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        print(f"Response: {response.text}")

        if response.text:
            try:
                json_response = response.json()
                print(f"Parsed JSON: {json.dumps(json_response, indent=2)}")
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")


if __name__ == "__main__":
    test_agent_call()
