import os
import time
import httpx
import pytest
from playwright.sync_api import Page, expect

# Setup helper for model state (Trained vs Fallback)
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

# Telemetry override profiles
NORM_PROFILE = [
    {"id": "gpu-0", "usage": 15.0, "temperature": 50.0, "memory_usage": 20.0, "queue_length": 0},
    {"id": "gpu-1", "usage": 12.0, "temperature": 48.0, "memory_usage": 18.0, "queue_length": 0},
    {"id": "gpu-2", "usage": 10.0, "temperature": 45.0, "memory_usage": 15.0, "queue_length": 0}
]

HOT_PROFILE = [
    {"id": "gpu-0", "usage": 70.0, "temperature": 85.0, "memory_usage": 40.0, "queue_length": 1},
    {"id": "gpu-1", "usage": 30.0, "temperature": 55.0, "memory_usage": 25.0, "queue_length": 0},
    {"id": "gpu-2", "usage": 35.0, "temperature": 58.0, "memory_usage": 30.0, "queue_length": 0}
]

BUSY_PROFILE = [
    {"id": "gpu-0", "usage": 95.0, "temperature": 75.0, "memory_usage": 80.0, "queue_length": 8},
    {"id": "gpu-1", "usage": 90.0, "temperature": 72.0, "memory_usage": 75.0, "queue_length": 6},
    {"id": "gpu-2", "usage": 20.0, "temperature": 55.0, "memory_usage": 15.0, "queue_length": 0}
]

FULLMEM_PROFILE = [
    {"id": "gpu-0", "usage": 35.0, "temperature": 60.0, "memory_usage": 98.0, "queue_length": 1},
    {"id": "gpu-1", "usage": 40.0, "temperature": 62.0, "memory_usage": 95.0, "queue_length": 0},
    {"id": "gpu-2", "usage": 30.0, "temperature": 55.0, "memory_usage": 20.0, "queue_length": 0}
]

@pytest.fixture(autouse=True)
def cleanup_after_test(backend_url):
    yield
    # Always reset telemetry and model files after each test
    httpx.post(f"{backend_url}/api/test/telemetry/reset")
    set_model_trained(True)  # default to trained

# T3.1: Happy-Path Inference Job under Balanced Telemetry (UI-Driven)
def test_t3_1_inference_under_balanced_telemetry(page: Page, frontend_url, backend_url):
    # Setup
    set_model_trained(True)
    httpx.post(f"{backend_url}/api/test/telemetry/override", json=NORM_PROFILE)
    
    # UI actions
    page.goto(frontend_url)
    page.wait_for_selector("[data-testid='gpu-card']")
    
    page.select_option("[data-testid='task-type-select']", "inference")
    page.fill("[data-testid='required-memory-input']", "2.0")
    page.click("[data-testid='submit-job-btn']")
    
    # Assertions
    result_container = page.locator("[data-testid='recommendation-result']")
    expect(result_container).to_be_visible()
    
    gpu_res = page.locator("[data-testid='recommended-gpu']").text_content()
    conf_res = float(page.locator("[data-testid='recommendation-confidence']").text_content())
    
    assert gpu_res in ("gpu-0", "gpu-1", "gpu-2")
    assert conf_res >= 0.75

# T3.2: High Thermals & Missing Model Fallback (CLI-Driven)
def test_t3_2_hot_thermals_missing_model(backend_url):
    # Setup
    set_model_trained(False)
    httpx.post(f"{backend_url}/api/test/telemetry/override", json=HOT_PROFILE)
    
    # Send schedule POST request directly (CLI-driven style)
    payload = {"task_type": "training", "required_memory": 16.0}
    response = httpx.post(f"{backend_url}/api/schedule", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    # Assert fallback logic: gpu-0 is hot (85C), so it should recommend gpu-1 or gpu-2.
    assert data["recommended_gpu"] != "gpu-0"
    assert data["recommended_gpu"] in ("gpu-1", "gpu-2")
    # Missing model returns 0.0 confidence
    assert data["confidence"] == 0.0

# T3.3: Heavy Compute Congestion & Data Processing Scheduling (API-Driven)
def test_t3_3_busy_telemetry_trained_model(backend_url):
    # Setup
    set_model_trained(True)
    httpx.post(f"{backend_url}/api/test/telemetry/override", json=BUSY_PROFILE)
    
    payload = {"task_type": "data_processing", "required_memory": 8.0}
    response = httpx.post(f"{backend_url}/api/schedule", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    # gpu-0 and gpu-1 are heavily congested (queue 8 and 6). gpu-2 is free (queue 0).
    assert data["recommended_gpu"] == "gpu-2"
    assert data["confidence"] >= 0.75

# T3.4: Memory Constrained Cluster with Low-Memory Inference (UI-Driven)
def test_t3_4_full_mem_missing_model(page: Page, frontend_url, backend_url):
    # Setup
    set_model_trained(False)
    httpx.post(f"{backend_url}/api/test/telemetry/override", json=FULLMEM_PROFILE)
    
    # UI actions
    page.goto(frontend_url)
    page.wait_for_selector("[data-testid='gpu-card']")
    
    page.select_option("[data-testid='task-type-select']", "inference")
    page.fill("[data-testid='required-memory-input']", "2.0")
    page.click("[data-testid='submit-job-btn']")
    
    # Assertions
    result_container = page.locator("[data-testid='recommendation-result']")
    expect(result_container).to_be_visible()
    
    gpu_res = page.locator("[data-testid='recommended-gpu']").text_content()
    conf_res = float(page.locator("[data-testid='recommendation-confidence']").text_content())
    
    # gpu-0 has 98% memory usage (2% free -> 0.48GB free)
    # gpu-1 has 95% memory usage (5% free -> 1.20GB free)
    # gpu-2 has 20% memory usage (80% free -> 19.2GB free)
    # For a 2.0 GB job, only gpu-2 has enough space.
    assert gpu_res == "gpu-2"
    assert conf_res == 0.0

# T3.5: Thermal Warning Cluster with Moderate Data Processing Job (UI-Driven)
def test_t3_5_hot_telemetry_trained_model(page: Page, frontend_url, backend_url):
    # Setup
    set_model_trained(True)
    httpx.post(f"{backend_url}/api/test/telemetry/override", json=HOT_PROFILE)
    
    # UI actions
    page.goto(frontend_url)
    page.wait_for_selector("[data-testid='gpu-card']")
    
    page.select_option("[data-testid='task-type-select']", "data_processing")
    page.fill("[data-testid='required-memory-input']", "8.0")
    page.click("[data-testid='submit-job-btn']")
    
    # Assertions
    result_container = page.locator("[data-testid='recommendation-result']")
    expect(result_container).to_be_visible()
    
    gpu_res = page.locator("[data-testid='recommended-gpu']").text_content()
    conf_res = float(page.locator("[data-testid='recommendation-confidence']").text_content())
    
    # gpu-0 is hot (85C). Should recommend cooler gpu-1 or gpu-2.
    assert gpu_res != "gpu-0"
    assert gpu_res in ("gpu-1", "gpu-2")
    assert conf_res >= 0.75

# T3.6: Memory Exhaustion with High-Memory Training Job (API-Driven)
def test_t3_6_full_mem_trained_model(backend_url):
    # Setup
    set_model_trained(True)
    httpx.post(f"{backend_url}/api/test/telemetry/override", json=FULLMEM_PROFILE)
    
    payload = {"task_type": "training", "required_memory": 16.0}
    response = httpx.post(f"{backend_url}/api/schedule", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    # Only gpu-2 has enough memory capacity for 16.0 GB training job.
    assert data["recommended_gpu"] == "gpu-2"
    assert data["confidence"] >= 0.75
