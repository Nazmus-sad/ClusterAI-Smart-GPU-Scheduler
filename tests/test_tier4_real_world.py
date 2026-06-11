import os
import sys
import time
import shutil
import httpx
import pytest
import subprocess
from playwright.sync_api import Page, expect

# Setup helper for model state
def set_model_trained(active: bool):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    backend_dir = os.path.join(base_dir, "backend")
    os.makedirs(backend_dir, exist_ok=True)
    model_path = os.path.join(backend_dir, "model.joblib")
    
    if active:
        with open(model_path, "w") as f:
            f.write("mock_trained_model_data")
    else:
        if os.path.exists(model_path):
            os.remove(model_path)

@pytest.fixture(autouse=True)
def cleanup_after_test(backend_url):
    yield
    # Cleanup after test
    httpx.post(f"{backend_url}/api/test/telemetry/reset")
    set_model_trained(True)
    
    # Remove backup file if it exists
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bak_path = os.path.join(base_dir, "backend", "model.joblib.bak")
    if os.path.exists(bak_path):
        os.remove(bak_path)

# RW-1: Dynamic Thermal Spikes & Route Correction
def test_rw_1_thermal_spikes_route_correction(page: Page, frontend_url, backend_url):
    # Phase 1: Baseline (balanced telemetry)
    balanced_telemetry = [
        {"id": "gpu-0", "usage": 20.0, "temperature": 55.0, "memory_usage": 20.0, "queue_length": 0},
        {"id": "gpu-1", "usage": 20.0, "temperature": 55.0, "memory_usage": 20.0, "queue_length": 0},
        {"id": "gpu-2", "usage": 20.0, "temperature": 55.0, "memory_usage": 20.0, "queue_length": 0}
    ]
    httpx.post(f"{backend_url}/api/test/telemetry/override", json=balanced_telemetry)
    
    page.goto(frontend_url)
    page.wait_for_selector("[data-testid='gpu-card']")
    
    # Submit 3 sequential inference jobs
    for _ in range(3):
        page.select_option("[data-testid='task-type-select']", "inference")
        page.fill("[data-testid='required-memory-input']", "2.0")
        page.click("[data-testid='submit-job-btn']")
        expect(page.locator("[data-testid='recommendation-result']")).to_be_visible()
        
    # Phase 2: Thermal Spike (gpu-0 temp = 88.0°C)
    hot_telemetry = [
        {"id": "gpu-0", "usage": 20.0, "temperature": 88.0, "memory_usage": 20.0, "queue_length": 0},
        {"id": "gpu-1", "usage": 20.0, "temperature": 55.0, "memory_usage": 20.0, "queue_length": 0},
        {"id": "gpu-2", "usage": 20.0, "temperature": 55.0, "memory_usage": 20.0, "queue_length": 0}
    ]
    httpx.post(f"{backend_url}/api/test/telemetry/override", json=hot_telemetry)
    
    # Wait for polling or force page navigation to load new state
    page.goto(frontend_url)
    page.wait_for_selector("[data-testid='gpu-card']")
    
    # Phase 3: Submit 3 more inference jobs
    recommendations = []
    for _ in range(3):
        page.select_option("[data-testid='task-type-select']", "inference")
        page.fill("[data-testid='required-memory-input']", "2.0")
        page.click("[data-testid='submit-job-btn']")
        
        page.wait_for_selector("[data-testid='recommended-gpu']")
        rec_gpu = page.locator("[data-testid='recommended-gpu']").text_content()
        recommendations.append(rec_gpu)
        
    # Phase 4: Validation
    # None of the new recommendations should go to gpu-0 since it has active thermal warning
    for rec in recommendations:
        assert rec != "gpu-0", f"Job was scheduled on hot gpu-0: {rec}"
        
    # Check that gpu-0 temp element turned red (metric-red class)
    gpu0_card = page.locator("#gpu-0")
    temp_elem = gpu0_card.locator("[data-testid='gpu-temp']")
    expect(temp_elem).to_have_class("metric-red")

# RW-2: Extreme Cluster Congestion and Graceful Degradation
def test_rw_2_extreme_congestion_degradation(page: Page, frontend_url, backend_url):
    # Phase 1: Saturate Cluster
    congested_telemetry = [
        {"id": "gpu-0", "usage": 98.0, "temperature": 82.0, "memory_usage": 98.0, "queue_length": 10},
        {"id": "gpu-1", "usage": 98.0, "temperature": 82.0, "memory_usage": 98.0, "queue_length": 10},
        {"id": "gpu-2", "usage": 98.0, "temperature": 82.0, "memory_usage": 98.0, "queue_length": 10}
    ]
    httpx.post(f"{backend_url}/api/test/telemetry/override", json=congested_telemetry)
    
    page.goto(frontend_url)
    page.wait_for_selector("[data-testid='gpu-card']")
    
    # Phase 2 & 3: Submit large training job and verify low confidence
    page.select_option("[data-testid='task-type-select']", "training")
    page.fill("[data-testid='required-memory-input']", "16.0")
    
    # We trigger the submission
    page.click("[data-testid='submit-job-btn']")
    
    # Assert result is visible and confidence is low
    result_container = page.locator("[data-testid='recommendation-result']")
    expect(result_container).to_be_visible()
    
    conf_res = float(page.locator("[data-testid='recommendation-confidence']").text_content())
    assert conf_res < 0.40, f"Expected low confidence for congested cluster, got {conf_res}"
    
    # Phase 4: Drain (step down telemetry to show recovery)
    drained_telemetry = [
        {"id": "gpu-0", "usage": 10.0, "temperature": 50.0, "memory_usage": 10.0, "queue_length": 0},
        {"id": "gpu-1", "usage": 10.0, "temperature": 50.0, "memory_usage": 10.0, "queue_length": 0},
        {"id": "gpu-2", "usage": 10.0, "temperature": 50.0, "memory_usage": 10.0, "queue_length": 0}
    ]
    httpx.post(f"{backend_url}/api/test/telemetry/override", json=drained_telemetry)
    
    # Wait for auto-refresh
    time.sleep(3.0)
    
    # Check that UI elements show lower values
    usage_text = page.locator("#gpu-0 [data-testid='gpu-usage']").text_content()
    assert float(usage_text) <= 15.0

# RW-3: Live Model Degradation, Fallback, and Recovery (Hot-Reload)
def test_rw_3_model_degradation_fallback_recovery(backend_url):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    model_path = os.path.join(base_dir, "backend", "model.joblib")
    bak_path = os.path.join(base_dir, "backend", "model.joblib.bak")
    
    # Phase 1: Normal Operations
    set_model_trained(True)
    payload = {"task_type": "training", "required_memory": 8.0}
    res1 = httpx.post(f"{backend_url}/api/schedule", json=payload)
    assert res1.status_code == 200
    assert res1.json()["confidence"] >= 0.75
    
    # Phase 2: Model Corruption
    if os.path.exists(model_path):
        shutil.move(model_path, bak_path)
        
    # Phase 3: Assert Fallback
    res2 = httpx.post(f"{backend_url}/api/schedule", json=payload)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["confidence"] == 0.0  # Fallback code
    
    # Phase 4: Retrain and Restore
    train_script = os.path.join(base_dir, "backend", "train.py")
    subprocess.run([sys.executable, train_script], check=True)
    
    # Phase 5: Assert Auto-recovery (reloads automatically without server restart)
    res3 = httpx.post(f"{backend_url}/api/schedule", json=payload)
    assert res3.status_code == 200
    assert res3.json()["confidence"] >= 0.75

# RW-4: Multi-Tenant Mixed Workloads (Co-location Optimization)
def test_rw_4_multi_tenant_mixed_workloads(backend_url):
    # Phase 1: Initial Setup
    # gpu-0 has 50% memory usage (representing 12GB used out of 24GB capacity).
    # gpu-1 and gpu-2 are idle (0% memory usage).
    telemetry = [
        {"id": "gpu-0", "usage": 20.0, "temperature": 50.0, "memory_usage": 50.0, "queue_length": 0},
        {"id": "gpu-1", "usage": 10.0, "temperature": 45.0, "memory_usage": 0.0, "queue_length": 0},
        {"id": "gpu-2", "usage": 10.0, "temperature": 45.0, "memory_usage": 0.0, "queue_length": 0}
    ]
    httpx.post(f"{backend_url}/api/test/telemetry/override", json=telemetry)
    
    # Phase 2 & 3: Submit mixed workloads
    # Heavy training job requesting 12.0 GB
    heavy_payload = {"task_type": "training", "required_memory": 12.0}
    res_heavy = httpx.post(f"{backend_url}/api/schedule", json=heavy_payload)
    assert res_heavy.status_code == 200
    rec_heavy = res_heavy.json()["recommended_gpu"]
    
    # Phase 4: Assert Optimal Placement
    # Training job must go to gpu-1 or gpu-2 because gpu-0 already has 12GB used (12GB free).
    # Adding 12GB would make it 24GB which is exactly the limit, but wait: 
    # Available memory check in mock backend: available_mem = 24.0 * (1 - 50/100) = 12.0 GB.
    # Since 12.0 >= 12.0, gpu-0 could technically barely fit it, but mock backend selects the best candidate
    # among candidates with enough memory based on lowest score. 
    # Let's see: gpu-0 score is usage*0.4 = 20*0.4 = 8.
    # gpu-1 and gpu-2 score is usage*0.4 = 10*0.4 = 4.
    # So gpu-1 or gpu-2 has a lower score and is preferred, which perfectly avoids overloading gpu-0!
    assert rec_heavy in ("gpu-1", "gpu-2")

# RW-5: Clean Bootstrap, Telemetry Drift, and End-to-End Validation
def test_rw_5_clean_bootstrap_telemetry_drift(backend_url):
    # Phase 1: Clean Slate
    set_model_trained(False) # Remove model
    
    # Get verify_mvp.py script path
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    script_path = os.path.join(base_dir, "verify_mvp.py")
    
    # Phase 2: Run verification script on port 8010.
    # It must detect the missing model, run train.py to regenerate model.joblib,
    # start the server, and validate successfully.
    env = os.environ.copy()
    env["PORT"] = "8010"
    env["HOST"] = "127.0.0.1"
    
    result = subprocess.run([sys.executable, script_path], env=env, capture_output=True, text=True, timeout=20)
    
    assert result.returncode == 0
    assert "Model file missing. Running backend/train.py to generate it..." in result.stdout
    assert "Model successfully saved" in result.stdout
    assert "Backend server started successfully" in result.stdout or "Port 8010 is already active" in result.stdout
    assert "All MVP verification checks completed successfully." in result.stdout
    
    # Verify that model.joblib was actually recreated
    model_path = os.path.join(base_dir, "backend", "model.joblib")
    assert os.path.exists(model_path)
