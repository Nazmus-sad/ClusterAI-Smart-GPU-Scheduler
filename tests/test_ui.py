import re
import time
import json
import httpx
import pytest
from playwright.sync_api import Page, expect

# Feature 3: React Dashboard Frontend UI

def test_dashboard_dark_mode_styling(page: Page, frontend_url):
    """TC-1.1: Dashboard Dark Mode & Styling Inspection"""
    page.goto(frontend_url)
    body = page.locator("body")
    expect(body).to_have_class(re.compile(r"bg-gray-900"))
    
    # Verify background color is dark (evaluates to rgb(17, 24, 39) which is #111827)
    bg_color = body.evaluate("element => window.getComputedStyle(element).backgroundColor")
    assert bg_color in ("rgb(17, 24, 39)", "#111827")

def test_gpu_metrics_grid_rendering(page: Page, frontend_url):
    """TC-1.2: Real-time GPU Metrics Grid Rendering"""
    page.goto(frontend_url)
    page.wait_for_selector("[data-testid='gpu-card']")
    
    cards = page.locator("[data-testid='gpu-card']")
    expect(cards).to_have_count(3)
    
    # Inspect card contents
    for i in range(3):
        card = cards.nth(i)
        expect(card.locator("[data-testid='gpu-usage']")).not_to_be_empty()
        expect(card.locator("[data-testid='gpu-temp']")).not_to_be_empty()
        expect(card.locator("[data-testid='gpu-mem']")).not_to_be_empty()
        expect(card.locator("[data-testid='gpu-queue']")).not_to_be_empty()

def test_real_time_ui_polling_auto_refresh(page: Page, frontend_url, backend_url):
    """TC-1.3: Real-time UI Polling & Auto-Refresh"""
    # Reset telemetry overrides first
    httpx.post(f"{backend_url}/api/test/telemetry/reset")
    
    page.goto(frontend_url)
    page.wait_for_selector("[data-testid='gpu-card']")
    
    # Record initial values
    initial_values = []
    usages = page.locator("[data-testid='gpu-usage']").all()
    for u in usages:
        initial_values.append(u.text_content())
        
    # Wait for polling update (2000ms interval, so 3 seconds is safe)
    time.sleep(3.0)
    
    new_values = []
    usages = page.locator("[data-testid='gpu-usage']").all()
    for u in usages:
        new_values.append(u.text_content())
        
    assert initial_values != new_values, "UI did not auto-refresh metrics dynamically"

def test_job_submission_form_action(page: Page, frontend_url):
    """TC-1.4: Job Submission Panel Form Action"""
    page.goto(frontend_url)
    page.wait_for_selector("[data-testid='gpu-card']")
    
    page.select_option("[data-testid='task-type-select']", "training")
    page.fill("[data-testid='required-memory-input']", "16.0")
    page.click("[data-testid='submit-job-btn']")
    
    result_container = page.locator("[data-testid='recommendation-result']")
    expect(result_container).to_be_visible()
    
    gpu_res = page.locator("[data-testid='recommended-gpu']")
    expect(gpu_res).not_to_be_empty()
    assert gpu_res.text_content() in ("gpu-0", "gpu-1", "gpu-2")
    
    conf_res = page.locator("[data-testid='recommendation-confidence']")
    expect(conf_res).not_to_be_empty()
    assert 0.0 <= float(conf_res.text_content()) <= 1.0

def test_desktop_and_mobile_responsive_layout(page: Page, frontend_url):
    """TC-1.5: Desktop and Mobile Responsive Layout"""
    page.goto(frontend_url)
    page.wait_for_selector("[data-testid='gpu-card']")
    
    card0 = page.locator("#gpu-0")
    card1 = page.locator("#gpu-1")
    
    # Desktop: Row/grid layout (side-by-side)
    page.set_viewport_size({"width": 1280, "height": 800})
    time.sleep(0.5)
    box0_desc = card0.bounding_box()
    box1_desc = card1.bounding_box()
    assert box0_desc["y"] == box1_desc["y"], "GPU cards did not align horizontally on desktop viewport"
    
    # Mobile: Vertical stacked layout
    page.set_viewport_size({"width": 375, "height": 667})
    time.sleep(0.5)
    box0_mob = card0.bounding_box()
    box1_mob = card1.bounding_box()
    assert box0_mob["x"] == box1_mob["x"], "GPU cards did not stack vertically on mobile viewport"
    assert box0_mob["y"] < box1_mob["y"], "Stacked cards order is incorrect on mobile viewport"

def test_frontend_resilience_backend_downtime(page: Page, frontend_url):
    """TC-2.1: Frontend Resilience During Backend Downtime"""
    # Block /api/gpus
    page.route("**/api/gpus", lambda route: route.fulfill(status=503, body="Service Unavailable"))
    
    page.goto(frontend_url)
    
    error_alert = page.locator("#error-alert")
    expect(error_alert).to_be_visible()
    expect(error_alert).to_contain_text("Telemetry server offline")
    
    submit_btn = page.locator("[data-testid='submit-job-btn']")
    expect(submit_btn).to_be_disabled()

def test_frontend_form_input_boundaries_validation(page: Page, frontend_url):
    """TC-2.2: Frontend Form Input Boundaries & Validation"""
    page.goto(frontend_url)
    page.wait_for_selector("[data-testid='gpu-card']")
    
    # Intercept and log /api/schedule requests
    schedule_requests = []
    page.on("request", lambda r: schedule_requests.append(r) if "/api/schedule" in r.url else None)
    
    # Fill invalid negative memory
    page.fill("[data-testid='required-memory-input']", "-5.0")
    page.click("[data-testid='submit-job-btn']")
    
    # Error message should display on form
    form_error = page.locator("#form-error")
    expect(form_error).to_contain_text("Memory must be greater than 0")
    
    # Verify no backend schedule request was dispatched
    time.sleep(0.5)
    assert len(schedule_requests) == 0

def test_double_submission_prevention(page: Page, frontend_url):
    """TC-2.3: Rapid Double-Submission Prevention (Throttling)"""
    page.goto(frontend_url)
    page.wait_for_selector("[data-testid='gpu-card']")
    
    schedule_requests = []
    page.on("request", lambda r: schedule_requests.append(r) if "/api/schedule" in r.url else None)
    
    # Fill form
    page.select_option("[data-testid='task-type-select']", "training")
    page.fill("[data-testid='required-memory-input']", "16.0")
    
    # Click 5 times rapidly
    submit_btn = page.locator("[data-testid='submit-job-btn']")
    for _ in range(5):
        try:
            submit_btn.click(force=True, no_wait_after=True)
        except Exception:
            pass
            
    time.sleep(1.0)
    # Only 1 request should be dispatched
    assert len(schedule_requests) == 1

def test_critical_value_metric_coloring(page: Page, frontend_url):
    """TC-2.4: High/Critical Value Metric Coloring Indicators"""
    critical_data = [
        {"id": "gpu-0", "name": "NVIDIA RTX 4090", "usage": 95.0, "temperature": 85.0, "memory_usage": 50.0, "queue_length": 2},
        {"id": "gpu-1", "name": "NVIDIA RTX 3080", "usage": 20.0, "temperature": 60.0, "memory_usage": 30.0, "queue_length": 0},
        {"id": "gpu-2", "name": "NVIDIA A100", "usage": 80.0, "temperature": 75.0, "memory_usage": 85.0, "queue_length": 4},
    ]
    
    page.route("**/api/gpus", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(critical_data)
    ))
    
    page.goto(frontend_url)
    page.wait_for_selector("[data-testid='gpu-card']")
    
    gpu0 = page.locator("#gpu-0")
    temp_val = gpu0.locator("[data-testid='gpu-temp']")
    usage_val = gpu0.locator("[data-testid='gpu-usage']")
    
    # Verify critical styles are applied (metric-red class)
    expect(temp_val).to_have_class(re.compile(r"metric-red"))
    expect(usage_val).to_have_class(re.compile(r"metric-red"))

def test_ui_recovery_and_polling_resumption(page: Page, frontend_url):
    """TC-2.5: UI Recovery and Polling Resumption"""
    # 1. Block first
    page.route("**/api/gpus", lambda route: route.fulfill(status=503, body="Offline"))
    page.goto(frontend_url)
    
    error_alert = page.locator("#error-alert")
    expect(error_alert).to_be_visible()
    
    # 2. Restore healthy response
    healthy_data = [
        {"id": "gpu-0", "name": "NVIDIA RTX 4090", "usage": 40.0, "temperature": 70.0, "memory_usage": 50.0, "queue_length": 2},
        {"id": "gpu-1", "name": "NVIDIA RTX 3080", "usage": 20.0, "temperature": 60.0, "memory_usage": 30.0, "queue_length": 0},
        {"id": "gpu-2", "name": "NVIDIA A100", "usage": 80.0, "temperature": 75.0, "memory_usage": 85.0, "queue_length": 4},
    ]
    page.route("**/api/gpus", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(healthy_data)
    ))
    
    # Wait for next update poll (2000ms, so 3 seconds is safe)
    time.sleep(3.0)
    
    # Alert should hide, and cards render successfully
    expect(error_alert).not_to_be_visible()
    cards = page.locator("[data-testid='gpu-card']")
    expect(cards).to_have_count(3)
