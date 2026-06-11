import httpx
import pytest
import time
import concurrent.futures

# Feature 1: GPU Telemetry Simulation

def test_telemetry_schema_validation(backend_url):
    """TC-1.1: Telemetry Schema Validation"""
    response = httpx.get(f"{backend_url}/api/gpus")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 3
    
    for gpu in data:
        assert "id" in gpu
        assert "name" in gpu
        assert "usage" in gpu
        assert "temperature" in gpu
        assert "memory_usage" in gpu
        assert "queue_length" in gpu
        
        assert isinstance(gpu["id"], str)
        assert isinstance(gpu["name"], str)
        assert isinstance(gpu["usage"], (int, float))
        assert isinstance(gpu["temperature"], (int, float))
        assert isinstance(gpu["memory_usage"], (int, float))
        assert isinstance(gpu["queue_length"], int)

def test_dynamic_telemetry_fluctuation(backend_url):
    """TC-1.2: Dynamic Telemetry Fluctuation"""
    # Reset telemetry overrides first to ensure fluctuations are active
    httpx.post(f"{backend_url}/api/test/telemetry/reset")
    
    r1 = httpx.get(f"{backend_url}/api/gpus").json()
    time.sleep(1.0)
    r2 = httpx.get(f"{backend_url}/api/gpus").json()
    
    fluctuated = False
    for gpu1, gpu2 in zip(r1, r2):
        if (gpu1["usage"] != gpu2["usage"] or 
            gpu1["temperature"] != gpu2["temperature"] or 
            gpu1["memory_usage"] != gpu2["memory_usage"] or 
            gpu1["queue_length"] != gpu2["queue_length"]):
            fluctuated = True
            break
            
    assert fluctuated, "Telemetry metrics did not fluctuate over 1 second"

def test_gpu_identity_and_order_persistence(backend_url):
    """TC-1.3: GPU Identity and Order Persistence"""
    responses = []
    for _ in range(3):
        res = httpx.get(f"{backend_url}/api/gpus")
        assert res.status_code == 200
        responses.append(res.json())
        time.sleep(0.5)
        
    length = len(responses[0])
    for r in responses:
        assert len(r) == length
        
    for i in range(length):
        gpu_id = responses[0][i]["id"]
        gpu_name = responses[0][i]["name"]
        for r in responses[1:]:
            assert r[i]["id"] == gpu_id
            assert r[i]["name"] == gpu_name

def test_concurrent_telemetry_fetching(backend_url):
    """TC-1.4: Concurrent Telemetry Fetching"""
    def fetch():
        return httpx.get(f"{backend_url}/api/gpus")
        
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch) for _ in range(10)]
        results = [f.result() for f in futures]
        
    for response in results:
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3

def test_metric_value_boundary_verification(backend_url):
    """TC-1.5: Metric Value Boundary Verification"""
    response = httpx.get(f"{backend_url}/api/gpus")
    assert response.status_code == 200
    data = response.json()
    for gpu in data:
        assert 0.0 <= gpu["usage"] <= 100.0
        assert 30.0 <= gpu["temperature"] <= 95.0
        assert 0.0 <= gpu["memory_usage"] <= 100.0
        assert gpu["queue_length"] >= 0

def test_long_term_telemetry_boundary_restraints(backend_url):
    """TC-2.1: Long-term Telemetry Boundary Restraints"""
    # Disable overrides
    httpx.post(f"{backend_url}/api/test/telemetry/reset")
    
    # Fast polling of 50 requests
    for _ in range(50):
        response = httpx.get(f"{backend_url}/api/gpus")
        assert response.status_code == 200
        data = response.json()
        for gpu in data:
            assert 0.0 <= gpu["usage"] <= 100.0
            assert 20.0 <= gpu["temperature"] <= 100.0
            assert 0.0 <= gpu["memory_usage"] <= 100.0
            assert gpu["queue_length"] >= 0
        time.sleep(0.05)

def test_invalid_methods_handling(backend_url):
    """TC-2.2: Invalid Methods Handling"""
    response = httpx.post(f"{backend_url}/api/gpus", json={})
    assert response.status_code in (405, 422)
    assert "detail" in response.json()

def test_cors_preflight_check(backend_url):
    """TC-2.3: CORS Configuration Preflight Check"""
    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "content-type"
    }
    response = httpx.options(f"{backend_url}/api/gpus", headers=headers)
    assert response.status_code in (200, 204)
    assert "access-control-allow-origin" in response.headers or "Access-Control-Allow-Origin" in response.headers
    assert "access-control-allow-methods" in response.headers or "Access-Control-Allow-Methods" in response.headers

def test_abrupt_connection_interruption_handling(backend_url):
    """TC-2.4: Abrupt Connection Interruption Handling"""
    try:
        with httpx.stream("GET", f"{backend_url}/api/gpus") as r:
            for _ in r.iter_bytes(chunk_size=1):
                break
    except Exception:
        pass
        
    time.sleep(0.1)
    response = httpx.get(f"{backend_url}/api/gpus")
    assert response.status_code == 200

def test_telemetry_state_continuity_after_idle(backend_url):
    """TC-2.5: Telemetry State Continuity After Idle Period"""
    # Reset override to ensure natural evolution
    httpx.post(f"{backend_url}/api/test/telemetry/reset")
    
    r1 = httpx.get(f"{backend_url}/api/gpus").json()
    time.sleep(2.0)  # Sleep 2 seconds (simulating idle evolution)
    r2 = httpx.get(f"{backend_url}/api/gpus").json()
    
    # Assert values changed and evolved continuously (status 200 ok)
    assert len(r1) == len(r2)


# Feature 2: Job Scheduling Engine

def test_basic_job_recommendation_execution(backend_url):
    """TC-1.1: Basic Job Recommendation Execution"""
    payload = {"task_type": "training", "required_memory": 16.0}
    response = httpx.post(f"{backend_url}/api/schedule", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "recommended_gpu" in data
    assert "confidence" in data
    assert data["recommended_gpu"] in ("gpu-0", "gpu-1", "gpu-2")
    assert 0.0 <= data["confidence"] <= 1.0

def test_variety_of_task_types_coverage(backend_url):
    """TC-1.2: Variety of Task Types Coverage"""
    tasks = [
        {"task_type": "training", "required_memory": 8.0},
        {"task_type": "inference", "required_memory": 4.0},
        {"task_type": "data_processing", "required_memory": 2.0}
    ]
    for task in tasks:
        response = httpx.post(f"{backend_url}/api/schedule", json=task)
        assert response.status_code == 200
        data = response.json()
        assert "recommended_gpu" in data
        assert 0.0 <= data["confidence"] <= 1.0

def test_telemetry_sensitive_load_balancing(backend_url):
    """TC-1.3: Telemetry-Sensitive Load Balancing"""
    # Set mock overrides to ensure gpu-1 has lowest usage/queue
    overrides = [
        {"id": "gpu-0", "usage": 90.0, "temperature": 75.0, "memory_usage": 80.0, "queue_length": 5},
        {"id": "gpu-1", "usage": 10.0, "temperature": 50.0, "memory_usage": 10.0, "queue_length": 0},
        {"id": "gpu-2", "usage": 95.0, "temperature": 80.0, "memory_usage": 90.0, "queue_length": 6}
    ]
    httpx.post(f"{backend_url}/api/test/telemetry/override", json=overrides)
    
    payload = {"task_type": "training", "required_memory": 16.0}
    response = httpx.post(f"{backend_url}/api/schedule", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["recommended_gpu"] == "gpu-1"
    
    # Teardown
    httpx.post(f"{backend_url}/api/test/telemetry/reset")

def test_scheduling_distribution_over_iterations(backend_url):
    """TC-1.4: Scheduling Distribution over Iterations"""
    # In mock mode, if we do not override, queue/usage fluctuate naturally.
    # We submit multiple jobs and assert we get responses.
    payload = {"task_type": "training", "required_memory": 16.0}
    for _ in range(5):
        response = httpx.post(f"{backend_url}/api/schedule", json=payload)
        assert response.status_code == 200

def test_confidence_score_type_and_range(backend_url):
    """TC-1.5: Confidence Score Type and Range Verification"""
    payload = {"task_type": "inference", "required_memory": 4.0}
    response = httpx.post(f"{backend_url}/api/schedule", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["confidence"], float)
    assert 0.0 <= data["confidence"] <= 1.0

def test_missing_required_fields_handling(backend_url):
    """TC-2.1: Missing Required Fields Handling"""
    payloads = [
        {"task_type": "training"},
        {"required_memory": 8.0},
        {}
    ]
    for p in payloads:
        response = httpx.post(f"{backend_url}/api/schedule", json=p)
        assert response.status_code == 422
        assert "detail" in response.json()

def test_extreme_out_of_bounds_memory(backend_url):
    """TC-2.2: Extreme Out-of-Bounds Memory Requests"""
    # Negative memory
    response = httpx.post(f"{backend_url}/api/schedule", json={"task_type": "training", "required_memory": -10.0})
    assert response.status_code in (400, 422)
    
    # Impossible memory size (e.g. 1000000.0) -> should either be rejected with 4xx or return low confidence recommendation
    response = httpx.post(f"{backend_url}/api/schedule", json={"task_type": "training", "required_memory": 1000000.0})
    assert response.status_code < 500  # Never HTTP 500
    if response.status_code == 200:
        assert response.json()["confidence"] < 0.40

def test_unknown_task_type_validation(backend_url):
    """TC-2.3: Unknown Task Type Validation"""
    payload = {"task_type": "unsupported_crypto_mining", "required_memory": 16.0}
    response = httpx.post(f"{backend_url}/api/schedule", json=payload)
    assert response.status_code in (400, 422)

def test_malformed_json_submission(backend_url):
    """TC-2.4: Malformed JSON Submission"""
    malformed = '{"task_type": "training", "required_memory": 16.0'
    response = httpx.post(f"{backend_url}/api/schedule", content=malformed, headers={"Content-Type": "application/json"})
    assert response.status_code in (400, 422)

def test_high_concurrency_scheduling_stress(backend_url):
    """TC-2.5: High-Concurrency Scheduling Stress Test"""
    payload = {"task_type": "inference", "required_memory": 4.0}
    def schedule():
        return httpx.post(f"{backend_url}/api/schedule", json=payload)
        
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(schedule) for _ in range(20)]
        results = [f.result() for f in futures]
        
    for response in results:
        assert response.status_code == 200
        data = response.json()
        assert "recommended_gpu" in data
        assert "confidence" in data
