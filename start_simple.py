#!/usr/bin/env python3
"""Simple script to start agents without package complications."""

import subprocess
import sys
import time
import os

def start_agent(module_name, port):
    """Start a single agent."""
    print(f"Starting {module_name} on port {port}...")
    
    # Set PYTHONPATH to current directory
    env = os.environ.copy()
    env['PYTHONPATH'] = os.getcwd()
    
    try:
        process = subprocess.Popen([
            sys.executable, '-m', module_name
        ], env=env)
        
        time.sleep(2)  # Give it time to start
        
        if process.poll() is None:
            print(f"✅ {module_name} started successfully (PID: {process.pid})")
            return process
        else:
            print(f"❌ {module_name} failed to start")
            return None
            
    except Exception as e:
        print(f"❌ Error starting {module_name}: {e}")
        return None

def main():
    print("🚀 Starting Alpine Ski Simulator Agents...")
    print("=" * 50)
    
    agents = [
        ("agents.hill_metrics.server", 8001),
        ("agents.weather.server", 8002), 
        ("agents.equipment.server", 8003)
    ]
    
    processes = []
    
    for module, port in agents:
        process = start_agent(module, port)
        if process:
            processes.append(process)
        else:
            print(f"Failed to start {module}, stopping...")
            # Kill any started processes
            for p in processes:
                p.terminate()
            return 1
    
    print("\n✅ All agents started successfully!")
    print("\nAgent URLs:")
    print("- Hill Metrics: http://localhost:8001")
    print("- Weather: http://localhost:8002") 
    print("- Equipment: http://localhost:8003")
    print("\nPress Ctrl+C to stop all agents")
    
    try:
        # Wait for keyboard interrupt
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping all agents...")
        for process in processes:
            process.terminate()
        print("✅ All agents stopped")
        return 0

if __name__ == "__main__":
    sys.exit(main())