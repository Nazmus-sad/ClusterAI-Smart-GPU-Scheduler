# Project: Simulated GPU Scheduler MVP

## Architecture
The Simulated GPU Scheduler MVP is a multi-module system composed of:
1. **Machine Learning Scheduling Engine**: Scikit-learn model trained on simulated telemetry datasets to balance load and thermals across a GPU cluster.
2. **GPU Simulation Backend**: FastAPI Python server simulating dynamic GPU telemetry and exposing scheduling endpoints.
3. **Premium Dashboard Frontend**: React + Tailwind CSS single page dashboard with real-time telemetry updates and job submission interface.
4. **Automated Verification**: Python script `verify_mvp.py` to automate end-to-end service validation.

```
       [ React Frontend ]
               │
      (HTTP JSON Requests)
               │
               ▼
      [ FastAPI Backend ] ◄──► [ ML Scheduling Engine (Scikit-learn) ]
```

## Code Layout
- `backend/`: Python FastAPI source code, ML model files, data generation, and training scripts.
  - `backend/main.py`: FastAPI server.
  - `backend/scheduler.py`: Scikit-learn model loading and recommendation logic.
  - `backend/train.py`: ML training data generation and Scikit-learn training script.
  - `backend/requirements.txt`: Python dependencies.
- `frontend/`: React + Tailwind CSS dashboard.
  - `frontend/src/`: React components.
  - `frontend/package.json`: Frontend configuration.
- `tests/`: End-to-end testing suite.
- `verify_mvp.py`: The root verification script.

## Milestones
| # | Name | Scope | Dependencies | Status | Conversation ID |
|---|------|-------|--------------|--------|-----------------|
| 1 | E2E Testing Track | Define test infra, feature inventory, Tier 1-4 test suite, publish `TEST_READY.md` | None | DONE | c3c8c861-3c05-4e92-820b-cf59d87a1653 |
| 2 | ML Scheduling Engine | Mock dataset generation, Scikit-learn training script, and trained model artifact | None | IN_PROGRESS | 241dc790-0d12-4f3f-9eba-aff7a06f0025 |
| 3 | GPU Simulation Backend | FastAPI server simulating 3+ GPUs, exposing `/api/gpus` and `/api/schedule` | M2 | PLANNED | TBD |
| 4 | React Dashboard Frontend | Sleek dark-themed dashboard visualizing metrics and job submission | M3 | PLANNED | TBD |
| 5 | End-to-End & Hardening | Implementation track validation against E2E tests, Tier 5 white-box hardening | M1, M4 | PLANNED | TBD |

## Interface Contracts
### GET `/api/gpus`
- **Response Format**: List of GPU telemetry objects.
- **Fields**:
  - `id`: string (e.g. `gpu-0`, `gpu-1`, `gpu-2`)
  - `name`: string (e.g. `NVIDIA RTX 4090`)
  - `usage`: float (percentage 0-100)
  - `temperature`: float (celsius)
  - `memory_usage`: float (percentage 0-100)
  - `queue_length`: int (number of pending jobs)

### POST `/api/schedule`
- **Request Format**: JSON object containing job characteristics.
- **Fields**:
  - `task_type`: string (e.g. `training`, `inference`, `data_processing`)
  - `required_memory`: float (GB or percentage representation)
- **Response Format**: Recommended GPU object.
- **Fields**:
  - `recommended_gpu`: string (GPU ID)
  - `confidence`: float (model score/probability)
