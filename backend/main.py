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

# ─── Firebase Firestore Setup ────────────────────────────────────────────────
USE_FIRESTORE = False
db = None

if os.environ.get("K_SERVICE") or os.environ.get("FIREBASE_CONFIG"):
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
        if not firebase_admin._apps:
            firebase_admin.initialize_app()
        db = firestore.client()
        USE_FIRESTORE = True
        print("Firestore initialized successfully in Cloud Functions environment.")
    except Exception as e:
        print(f"Failed to initialize Firestore: {e}. Falling back to in-memory store.")

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

    # Determine job number using Firestore if active
    if USE_FIRESTORE and db is not None:
        try:
            counter_ref = db.collection("metadata").document("counters")
            @firestore.transactional
            def update_counter(transaction, ref):
                snapshot = ref.get(transaction=transaction)
                count = 0
                if snapshot.exists:
                    count = snapshot.to_dict().get("job_count", 0)
                new_count = count + 1
                transaction.update(ref, {"job_count": new_count})
                return new_count

            if not counter_ref.get().exists:
                counter_ref.set({"job_count": 0})
            
            transaction = db.transaction()
            current_job_num = update_counter(transaction, counter_ref)
        except Exception as e:
            print(f"Firestore counter failed, using local: {e}")
            _job_counter += 1
            current_job_num = _job_counter
    else:
        _job_counter += 1
        current_job_num = _job_counter

    job_id = f"job-{current_job_num:04d}"
    job_record = {
        "job_id": job_id,
        "task_type": job.task_type,
        "required_memory": job.required_memory,
        "recommended_gpu": result["recommended_gpu"],
        "confidence": float(result["confidence"]),
        "timestamp": time.time(),
        "gpu_snapshot": gpu_telemetry,
    }

    # Save job using Firestore if active
    if USE_FIRESTORE and db is not None:
        try:
            db.collection("jobs").document(job_id).set(job_record)
        except Exception as e:
            print(f"Failed to save job to Firestore: {e}")
            _job_history.append(job_record)
            if len(_job_history) > 50:
                _job_history.pop(0)
    else:
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
    if USE_FIRESTORE and db is not None:
        try:
            jobs_ref = db.collection("jobs")
            docs = jobs_ref.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(50).stream()
            history = []
            for doc in docs:
                history.append(doc.to_dict())
            return history
        except Exception as e:
            print(f"Failed to query jobs from Firestore: {e}")
            return list(reversed(_job_history))
    return list(reversed(_job_history))


@app.get("/api/metrics", summary="Get cluster-level summary metrics")
def get_cluster_metrics():
    """Returns aggregate performance metrics for the dashboard cost panel."""
    telemetry = [_simulate_telemetry(i) for i in range(3)]
    avg_usage = sum(g["usage"] for g in telemetry) / 3
    avg_temp = sum(g["temperature"] for g in telemetry) / 3
    idle_count = sum(1 for g in telemetry if g["usage"] < 25)

    total_jobs = _job_counter
    if USE_FIRESTORE and db is not None:
        try:
            counter_ref = db.collection("metadata").document("counters")
            counter_doc = counter_ref.get()
            if counter_doc.exists:
                total_jobs = counter_doc.to_dict().get("job_count", 0)
        except Exception as e:
            print(f"Failed to query job count from Firestore: {e}")

    return {
        "avg_usage": round(avg_usage, 2),
        "avg_temperature": round(avg_temp, 2),
        "idle_gpu_count": idle_count,
        "jobs_scheduled": total_jobs,
        "estimated_cost_savings_pct": round(min(42.0, 15.0 + (total_jobs * 0.8)), 1),
        "scheduling_efficiency_pct": round(min(97.0, 78.0 + (total_jobs * 0.5)), 1),
    }


@app.get("/health")
def health_check():
    return {"status": "ok", "uptime_seconds": round(time.time() - _start_time, 1)}


# ─── Firebase Cloud Function Export ──────────────────────────────────────────
# Expose the FastAPI app as a Firebase Cloud Function named "clusterai"
try:
    from firebase_functions import https_fn
    clusterai = https_fn.on_request(app)
except Exception:
    pass

