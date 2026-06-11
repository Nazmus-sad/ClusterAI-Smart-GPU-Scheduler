# E2E Test Infrastructure

This document outlines the architecture, layout, configuration, and execution guidelines for the **Simulated GPU Scheduler MVP** E2E testing suite.

---

## 1. Directory Structure

The E2E test suite resides entirely within the `tests/` directory at the project root. This structure isolates E2E testing code from the production FastAPI backend and React frontend code.

```
tests/
├── mock_frontend/
│   └── index.html           # Static HTML dashboard mockup matching React selectors
├── requirements.txt         # Isolated E2E testing dependencies (pytest, playwright, uvicorn, fastapi)
├── conftest.py              # Pytest configuration, server lifecycle hooks, and global fixtures
├── mock_backend.py          # FastAPI mock backend simulating APIs, overrides, and serving index.html
├── run_tests.py             # Cross-platform entrypoint script to run E2E test suite
├── test_api.py              # Tier 1 & Tier 2 API tests (contracts, limits, concurrency)
├── test_ui.py               # Tier 1 & Tier 2 Playwright UI tests (styling, dark mode, validation)
├── test_cli.py              # E2E CLI tests verifying the verify_mvp.py script execution
├── test_tier3_combinations.py # Tier 3 pairwise interaction test cases (T3.1 - T3.6)
└── test_tier4_real_world.py # Tier 4 complex workload simulation scenarios (RW-1 - RW-5)
```

---

## 2. Configuration & Environment Variables

The E2E test suite is fully configurable via environment variables, enabling execution against mock stubs or live production environments.

*   `USE_MOCK_SERVERS`: When `true`, pytest starts a local mock FastAPI server on port `8001` and redirects all tests to it. Defaults to `false`.
*   `BACKEND_URL`: URL of the FastAPI backend. Defaults to `http://localhost:8000` (real backend) or `http://127.0.0.1:8001` (mock mode).
*   `FRONTEND_URL`: URL of the React dashboard. Defaults to `http://localhost:3000` (real frontend) or `http://127.0.0.1:8001` (mock mode).
*   `PLAYWRIGHT_HEADLESS`: Runs Playwright tests headlessly. Defaults to `true`.

---

## 3. Mock Server Mode (FastAPI & HTML Stub)

To enable test-driven development (TDD), the test suite contains a self-contained mock mode.
1.  **Mock Backend (`tests/mock_backend.py`)**: Exposes simulated endpoints `/api/gpus` and `/api/schedule` matching standard JSON schemas.
2.  **Mock Frontend (`tests/mock_frontend/index.html`)**: Serves a static HTML page rendering the GPU cards grid and job submission panel using `data-testid` attributes.
3.  **Unified Routing**: The mock backend serves `index.html` on the root route (`/`). This allows Playwright to test the entire E2E system against a single unified mock port (`8001`).

---

## 4. Telemetry Override & Reset Mechanism

To prevent flakiness in testing caused by dynamic, continuously fluctuating telemetry simulation values (R1), we introduce two developer-only test API endpoints:

### POST `/api/test/telemetry/override`
Receives a JSON list of GPU states and forces the simulation to freeze at those static metrics.
*   **Payload**: List of `GPUMetricsOverride` containing `id`, `usage`, `temperature`, `memory_usage`, and/or `queue_length`.

### POST `/api/test/telemetry/reset`
Resumes normal dynamic telemetry fluctuations and restores default metrics.

By utilizing this hook, E2E tests can systematically configure precise cluster conditions (e.g. "Full memory", "Hot thermal warnings") to verify scheduling decisions with **100% reproducibility**.

---

## 5. Running the Tests

Ensure dependencies are installed and run the wrapper runner script:

```bash
# 1. Install dependencies
pip install -r tests/requirements.txt

# 2. Install Playwright browser
playwright install chromium

# 3. Run E2E tests in Mock Mode
python tests/run_tests.py --mock

# 4. Run E2E tests against live services
python tests/run_tests.py --backend-url http://localhost:8000 --frontend-url http://localhost:3000
```
