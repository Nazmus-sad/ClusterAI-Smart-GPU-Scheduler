# Original User Request

## Initial Request — 2026-06-11T11:46:18+06:00

A simulated GPU Scheduler MVP consisting of a FastAPI Python backend that simulates GPU cluster telemetry, a Scikit-learn model to schedule jobs on the best GPU, and a premium dark-themed React frontend dashboard using Tailwind CSS to visualize telemetry and submit jobs.

Working directory: c:/Users/PC/Documents/Hackathon Project
Integrity mode: development

## Requirements

### R1. GPU Simulation Backend (FastAPI)
A Python FastAPI server that simulates telemetry (usage, temperature, memory, queue length) for at least 3 GPUs. The metrics must fluctuate dynamically over time. It must expose:
- `GET /api/gpus` returning status for all GPUs.
- `POST /api/schedule` taking a job (e.g. task type, resources requested) and returning a recommended GPU.

### R2. Machine Learning Scheduling Engine
A Scikit-learn machine learning model (e.g. Random Forest, Linear Regression, or similar classifier/regressor) trained on simulated/generated GPU dataset. The model should evaluate telemetry and select the best GPU for a given job to balance load and thermals. A training script must be provided to generate mock historical training data and train the model.

### R3. Premium Dashboard Frontend (React / Tailwind CSS)
A beautiful, responsive React dashboard styled with Tailwind CSS (dark mode). It must show a real-time updating grid/visualization of the GPUs and their current metrics (usage %, temp °C, memory %, queue length). It should feature a "Submit Job" panel that sends requests to the backend and displays the recommended GPU.

### R4. Automated Verification Script
A Python verification script `verify_mvp.py` that can be run to launch the FastAPI backend, query endpoints, assert that telemetry changes, submit a sample job, verify the response, and output success status.

## Acceptance Criteria

### API & Model
- [ ] Running the training script generates a trained Scikit-learn model artifact (e.g., joblib/pickle file).
- [ ] `GET /api/gpus` returns valid JSON showing metrics (usage, temp, memory, queue) for at least 3 GPUs, with values fluctuating on subsequent calls.
- [ ] `POST /api/schedule` successfully uses the trained ML model to recommend a GPU.

### Frontend Dashboard
- [ ] The React app compiles and runs, styled in a sleek dark theme using Tailwind CSS.
- [ ] The dashboard periodically fetches telemetry data and updates the UI automatically.
- [ ] The dashboard includes interactive charts or visual indicator gauges (e.g. thermals, memory usage) for each GPU.
- [ ] Submitting a job via the UI displays the recommended GPU selected by the ML backend.

### Verification
- [ ] Running `python verify_mvp.py` starts the server, checks all endpoints, makes asserts, and exits with a 0 status code on success.
