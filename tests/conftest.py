import os
import sys
import time
import subprocess
import socket
import pytest

def is_port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0

@pytest.fixture(scope="session", autouse=True)
def manage_servers():
    use_mock = os.environ.get("USE_MOCK_SERVERS", "false").lower() == "true"
    proc = None
    
    if use_mock:
        print("\n[Mock Mode] Starting uvicorn server for tests...")
        if is_port_open("127.0.0.1", 8001):
            print("Port 8001 is already in use, assuming server is running.")
        else:
            # Using sys.executable is safer on Windows to ensure correct python environment is used
            proc = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "tests.mock_backend:app", "--host", "127.0.0.1", "--port", "8001"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            # Await server startup
            for _ in range(100):
                if is_port_open("127.0.0.1", 8001):
                    break
                time.sleep(0.1)
            else:
                # Get stderr for diagnosis
                err = ""
                if proc.poll() is not None:
                    err = proc.stderr.read() if proc.stderr else "No stderr available"
                raise RuntimeError(f"Mock server failed to start on port 8001. Error: {err}")
        
        os.environ["BACKEND_URL"] = "http://127.0.0.1:8001"
        os.environ["FRONTEND_URL"] = "http://127.0.0.1:8001"
        
    yield
    
    if proc:
        print("\n[Mock Mode] Terminating uvicorn server...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

@pytest.fixture(scope="session")
def backend_url():
    return os.environ.get("BACKEND_URL", "http://localhost:8000")

@pytest.fixture(scope="session")
def frontend_url():
    return os.environ.get("FRONTEND_URL", "http://localhost:3000")

# Setup Playwright base configurations
@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    # Set default viewport
    return {
        **browser_context_args,
        "viewport": {
            "width": 1280,
            "height": 800,
        }
    }
