import os
import random
import time
import math
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

try:
    from backend.scheduler import predict_best_gpu
except ImportError:
    from scheduler import predict_best_gpu

app = FastAPI(title="GPU Cluster Scheduler API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── GPU Cluster State ───────────────────────────────────────────────────────

GPU_MODELS = [
    "NVIDIA RTX 4090",
    "NVIDIA A100 80GB",
    "NVIDIA H100 SXM5",
]

_start_time = time.time()

# Each GPU has a unique "personality" for realistic-looking fluctuation
_gpu_profiles = [
    {"base_usage": 45.0, "base_temp": 55.0, "base_mem": 38.0, "phase": 0.0},
    {"base_usage": 72.0, "base_temp": 71.0, "base_mem": 61.0, "phase": 2.1},
    {"base_usage": 28.0, "base_temp": 44.0, "base_mem": 25.0, "phase": 4.2},
]

_job_history: list = []
_job_counter = 0


def _simulate_telemetry(gpu_index: int) -> dict:
    """Generate realistically fluctuating telemetry for a GPU."""
    profile = _gpu_profiles[gpu_index]
    t = time.time() - _start_time
    phase = profile["phase"]

    # Oscillating usage with small noise
    usage = profile["base_usage"] + 12.0 * math.sin(t * 0.15 + phase) + random.uniform(-3.0, 3.0)
    usage = max(5.0, min(98.0, usage))

    # Temperature tracks usage with slight lag and noise
    temperature = 35.0 + 0.55 * usage + 5.0 * math.sin(t * 0.1 + phase + 0.5) + random.uniform(-1.5, 1.5)
    temperature = max(35.0, min(95.0, temperature))

    # Memory usage oscillates somewhat independently
    memory_usage = profile["base_mem"] + 8.0 * math.sin(t * 0.08 + phase + 1.0) + random.uniform(-2.0, 2.0)
    memory_usage = max(5.0, min(95.0, memory_usage))

    # Queue length: discrete, changes less frequently
    queue_tick = int(t * 0.3 + phase * 2) % 7
    queue_length = max(0, queue_tick + random.randint(-1, 1))

    return {
        "id": f"gpu-{gpu_index}",
        "name": GPU_MODELS[gpu_index],
        "usage": round(usage, 2),
        "temperature": round(temperature, 2),
        "memory_usage": round(memory_usage, 2),
        "queue_length": queue_length,
        "available_memory_gb": round(24.0 * (1.0 - memory_usage / 100.0), 2),
        "status": "critical" if temperature > 88 or usage > 92 else "busy" if usage > 65 else "idle" if usage < 25 else "normal",
    }


# ─── Models ──────────────────────────────────────────────────────────────────

class JobRequest(BaseModel):
    task_type: str = "inference"
    required_memory: float = 4.0


# ─── Endpoints ───────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
def root():
    """Redirect root to interactive API docs."""
    return RedirectResponse(url="/docs")


@app.get("/api/gpus", summary="Get current GPU cluster telemetry")
def get_gpu_status():
    """Returns real-time simulated telemetry for all GPUs in the cluster."""
    return [_simulate_telemetry(i) for i in range(3)]


@app.post("/api/schedule", summary="Schedule a job on the optimal GPU")
def schedule_job(job: JobRequest):
    """Accepts a job specification and returns the ML-recommended GPU."""
    global _job_counter

    valid_task_types = ["training", "inference", "data_processing"]
    if job.task_type not in valid_task_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid task_type '{job.task_type}'. Must be one of: {valid_task_types}"
        )
    if job.required_memory <= 0 or job.required_memory > 80:
        raise HTTPException(
            status_code=400,
            detail="required_memory must be between 0 and 80 GB."
        )

    gpu_telemetry = [_simulate_telemetry(i) for i in range(3)]
    result = predict_best_gpu(gpu_telemetry, job.task_type, job.required_memory)

    _job_counter += 1
    job_record = {
        "job_id": f"job-{_job_counter:04d}",
        "task_type": job.task_type,
        "required_memory": job.required_memory,
        "recommended_gpu": result["recommended_gpu"],
        "confidence": result["confidence"],
        "timestamp": time.time(),
        "gpu_snapshot": gpu_telemetry,
    }
    _job_history.append(job_record)
    if len(_job_history) > 50:
        _job_history.pop(0)

    return {
        "status": "success",
        "job_id": job_record["job_id"],
        "recommended_gpu": result["recommended_gpu"],
        "confidence": result["confidence"],
        "gpu_snapshot": gpu_telemetry,
    }


@app.get("/api/jobs", summary="Get recent job scheduling history")
def get_job_history():
    """Returns the last 50 scheduled jobs and their outcomes."""
    return list(reversed(_job_history))


@app.get("/api/metrics", summary="Get cluster-level summary metrics")
def get_cluster_metrics():
    """Returns aggregate performance metrics for the dashboard cost panel."""
    telemetry = [_simulate_telemetry(i) for i in range(3)]
    avg_usage = sum(g["usage"] for g in telemetry) / 3
    avg_temp = sum(g["temperature"] for g in telemetry) / 3
    idle_count = sum(1 for g in telemetry if g["usage"] < 25)
    return {
        "avg_usage": round(avg_usage, 2),
        "avg_temperature": round(avg_temp, 2),
        "idle_gpu_count": idle_count,
        "jobs_scheduled": _job_counter,
        "estimated_cost_savings_pct": round(min(42.0, 15.0 + (_job_counter * 0.8)), 1),
        "scheduling_efficiency_pct": round(min(97.0, 78.0 + (_job_counter * 0.5)), 1),
    }


@app.get("/health")
def health_check():
    return {"status": "ok", "uptime_seconds": round(time.time() - _start_time, 1)}
