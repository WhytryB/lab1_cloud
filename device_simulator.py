import json
import time
import random
from datetime import datetime
import requests

def generate_telemetry(device_id):
    return {
        "device_id": device_id,
        "timestamp": datetime.now().isoformat(),
        "metrics": {
            "cpu_usage": random.uniform(20, 95),
            "memory_usage": random.uniform(30, 90), 
            "temperature": random.uniform(25, 85),
            "battery_level": random.uniform(10, 100),
            "network_quality": random.choice(["good", "fair", "poor"])
        }
    }

def simulate_device(device_id="device-001", api_url="http://localhost:8080"):
    print(f"Starting simulation for {device_id}")
    
    while True:
        try:
            telemetry = generate_telemetry(device_id)
            print(f"Generated: {telemetry}")
            time.sleep(30)  # Send every 30 seconds
        except KeyboardInterrupt:
            print("Simulation stopped")
            break

if __name__ == "__main__":
    simulate_device()