import os
import sys
import time
import socket
import subprocess
import httpx

def is_port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0

def main():
    # 1. Custom Host and Port Configuration
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    
    # Check if model exists, if not, train it (RW-5 requirement)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(base_dir, "backend", "model.joblib")
    train_path = os.path.join(base_dir, "backend", "train.py")
    if not os.path.exists(model_path) and os.path.exists(train_path):
        print("Model file missing. Running backend/train.py to generate it...")
        try:
            subprocess.run([sys.executable, train_path], check=True)
        except Exception as e:
            print(f"Error running training script: {e}")
            sys.exit(1)
            
    backend_url = f"http://{host}:{port}"
    print(f"Verifying MVP against backend at {backend_url}")
    
    started_server = False
    proc = None
    
    # Check if target port is already in use
    port_in_use = is_port_open(host, port)
    
    # 2. Server Lifecycle Autostart Management
    if not port_in_use:
        print(f"Port {port} is closed. Attempting to autostart backend server...")
        
        # Decide which server target to run (prefer real backend if it exists, otherwise fallback to mock_backend)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        real_backend_exists = os.path.exists(os.path.join(base_dir, "backend", "main.py"))
        
        if real_backend_exists:
            server_target = "backend.main:app"
        elif os.path.exists(os.path.join(base_dir, "tests", "mock_backend.py")):
            server_target = "tests.mock_backend:app"
        else:
            print("Error: No backend code found to autostart.")
            sys.exit(1)
            
        try:
            # We run uvicorn
            proc = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", server_target, "--host", host, "--port", str(port)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            started_server = True
            
            # Await startup
            for _ in range(50):
                if is_port_open(host, port):
                    break
                time.sleep(0.1)
            else:
                print(f"Error: Autostarted server failed to bind to {host}:{port}")
                sys.exit(1)
                
            print("Backend server started successfully.")
        except Exception as e:
            print(f"Error starting server: {e}")
            sys.exit(1)
    else:
        print(f"Port {port} is already active. Using running server.")

    try:
        # 3. Telemetry Fluctuation Validation Check
        print("Checking GPU telemetry fluctuation...")
        try:
            r1 = httpx.get(f"{backend_url}/api/gpus", timeout=5.0)
        except Exception as e:
            print(f"Error fetching telemetry: {e}")
            sys.exit(1)
            
        if r1.status_code != 200:
            print(f"Error: Telemetry endpoint returned status {r1.status_code}")
            sys.exit(1)
            
        gpus_data_1 = r1.json()
        
        # Wait slightly and query again to check for fluctuation
        time.sleep(1.0)
        
        try:
            r2 = httpx.get(f"{backend_url}/api/gpus", timeout=5.0)
        except Exception as e:
            print(f"Error fetching telemetry again: {e}")
            sys.exit(1)
            
        if r2.status_code != 200:
            print(f"Error: Telemetry endpoint returned status {r2.status_code}")
            sys.exit(1)
            
        gpus_data_2 = r2.json()
        
        # Assert fluctuation
        fluctuated = False
        for g1, g2 in zip(gpus_data_1, gpus_data_2):
            if (g1["usage"] != g2["usage"] or 
                g1["temperature"] != g2["temperature"] or 
                g1["memory_usage"] != g2["memory_usage"] or 
                g1["queue_length"] != g2["queue_length"]):
                fluctuated = True
                break
                
        if not fluctuated:
            print("Error: Telemetry values are stagnant (TC-2.2 violation).")
            sys.exit(1)
            
        print("Telemetry fluctuation check passed.")

        # 4. Script-Executed Job Scheduling Verification
        print("Checking job scheduling...")
        payload = {"task_type": "inference", "required_memory": 4.0}
        try:
            s_res = httpx.post(f"{backend_url}/api/schedule", json=payload, timeout=5.0)
        except Exception as e:
            print(f"Error posting job schedule: {e}")
            sys.exit(1)
            
        if s_res.status_code != 200:
            print(f"Error: Scheduling endpoint returned status {s_res.status_code}")
            # API Error Propagation check
            sys.exit(1)
            
        rec_data = s_res.json()
        if "recommended_gpu" not in rec_data or "confidence" not in rec_data:
            print("Error: Missing scheduling response fields.")
            sys.exit(1)
            
        valid_gpus = [g["id"] for g in gpus_data_1]
        recommended = rec_data["recommended_gpu"]
        
        if recommended not in valid_gpus:
            print(f"Error: Recommended GPU '{recommended}' not in cluster {valid_gpus}")
            sys.exit(1)
            
        print(f"Job scheduling check passed. Recommended GPU: {recommended} (confidence: {rec_data['confidence']})")
        print("All MVP verification checks completed successfully.")
        
    finally:
        # Clean shutdown of autostarted server
        if started_server and proc:
            print("Stopping autostarted server...")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()

if __name__ == "__main__":
    main()
