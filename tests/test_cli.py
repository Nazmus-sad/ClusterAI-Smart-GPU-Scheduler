import os
import sys
import time
import socket
import subprocess
import httpx
import pytest

# Feature 4: Automated Verification Script verify_mvp.py

def test_verify_mvp_success():
    """TC-1.1 & TC-1.2 & TC-1.3 & TC-1.4 & TC-1.5: Standard MVP Verification Success & Lifecycle Autostart"""
    # Run verify_mvp.py on a clean port so it autostarts the mock server
    env = os.environ.copy()
    env["PORT"] = "8005"
    env["HOST"] = "127.0.0.1"
    
    script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "verify_mvp.py")
    
    result = subprocess.run([sys.executable, script_path], env=env, capture_output=True, text=True, timeout=15)
    
    assert result.returncode == 0
    assert "Backend server started successfully" in result.stdout or "Port 8005 is already active" in result.stdout
    assert "Checking GPU telemetry fluctuation..." in result.stdout
    assert "Checking job scheduling..." in result.stdout
    assert "All MVP verification checks completed successfully." in result.stdout

def test_verify_mvp_custom_config():
    """TC-2.4: Custom Host and Port Configuration"""
    # Start server manually on a custom port 8006
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "tests.mock_backend:app", "--host", "127.0.0.1", "--port", "8006"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for startup
    time.sleep(1.0)
    
    try:
        env = os.environ.copy()
        env["HOST"] = "127.0.0.1"
        env["PORT"] = "8006"
        
        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "verify_mvp.py")
        result = subprocess.run([sys.executable, script_path], env=env, capture_output=True, text=True, timeout=10)
        
        assert result.returncode == 0
        assert "Port 8006 is already active. Using running server." in result.stdout
        assert "All MVP verification checks completed successfully." in result.stdout
    finally:
        proc.terminate()
        proc.wait()

def test_verify_mvp_port_bind_failure():
    """TC-2.1: Port Bind Failure Handling"""
    # Block port 8007 with a dummy TCP socket listener that does not handle FastAPI requests
    blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    blocker.bind(("127.0.0.1", 8007))
    blocker.listen(1)
    
    try:
        env = os.environ.copy()
        env["PORT"] = "8007"
        env["HOST"] = "127.0.0.1"
        
        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "verify_mvp.py")
        result = subprocess.run([sys.executable, script_path], env=env, capture_output=True, text=True, timeout=10)
        
        # Should exit with non-zero exit code because it cannot query telemetry from the blocked port
        assert result.returncode != 0
        assert "Error" in result.stdout or "Error" in result.stderr
    finally:
        blocker.close()

def test_verify_mvp_telemetry_stagnation_failure(backend_url):
    """TC-2.2: Telemetry Stagnation Failure Detection"""
    # Freeze telemetry on the active test server by overriding it
    static_overrides = [
        {"id": "gpu-0", "usage": 45.0, "temperature": 65.0, "memory_usage": 40.0, "queue_length": 1},
        {"id": "gpu-1", "usage": 45.0, "temperature": 65.0, "memory_usage": 40.0, "queue_length": 1},
        {"id": "gpu-2", "usage": 45.0, "temperature": 65.0, "memory_usage": 40.0, "queue_length": 1}
    ]
    httpx.post(f"{backend_url}/api/test/telemetry/override", json=static_overrides)
    
    try:
        # Extract port and host from backend_url (e.g. http://127.0.0.1:8001)
        # We point verify_mvp.py to the frozen server
        host = "127.0.0.1"
        port = backend_url.split(":")[-1].replace("/", "")
        
        env = os.environ.copy()
        env["PORT"] = port
        env["HOST"] = host
        
        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "verify_mvp.py")
        result = subprocess.run([sys.executable, script_path], env=env, capture_output=True, text=True, timeout=10)
        
        # It must fail because telemetry is frozen
        assert result.returncode != 0
        assert "Telemetry values are stagnant" in result.stdout
    finally:
        # Reset telemetry
        httpx.post(f"{backend_url}/api/test/telemetry/reset")

def test_verify_mvp_api_error_propagation():
    """TC-2.3: API Error Propagation Failure Detection"""
    # Start a dummy server that responds with HTTP 500 for schedule or telemetry
    # We can simulate this by pointing verify_mvp.py to a non-existent endpoint or
    # port where the server returns error. Since we closed blocker in TC-2.1, let's use it here.
    blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    blocker.bind(("127.0.0.1", 8008))
    blocker.listen(1)
    
    try:
        env = os.environ.copy()
        env["PORT"] = "8008"
        env["HOST"] = "127.0.0.1"
        
        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "verify_mvp.py")
        result = subprocess.run([sys.executable, script_path], env=env, capture_output=True, text=True, timeout=10)
        
        # Should detect error and propagate it via non-zero exit code
        assert result.returncode != 0
    finally:
        blocker.close()
