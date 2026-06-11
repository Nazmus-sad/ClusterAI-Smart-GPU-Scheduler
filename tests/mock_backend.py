import random
import os
import copy
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Default GPU database
DEFAULT_GPUS = [
    {"id": "gpu-0", "name": "NVIDIA RTX 4090", "usage": 40.0, "temperature": 70.0, "memory_usage": 50.0, "queue_length": 2},
    {"id": "gpu-1", "name": "NVIDIA RTX 3080", "usage": 20.0, "temperature": 60.0, "memory_usage": 30.0, "queue_length": 0},
    {"id": "gpu-2", "name": "NVIDIA A100", "usage": 80.0, "temperature": 75.0, "memory_usage": 85.0, "queue_length": 4},
]

# Shared in-memory mock database
gpus_db = copy.deepcopy(DEFAULT_GPUS)
is_overridden = False

class JobRequest(BaseModel):
    task_type: str
    required_memory: float

class ScheduleResponse(BaseModel):
    recommended_gpu: str
    confidence: float

class GPUMetricsOverride(BaseModel):
    id: str
    name: Optional[str] = None
    usage: Optional[float] = None
    temperature: Optional[float] = None
    memory_usage: Optional[float] = None
    queue_length: Optional[int] = None

def check_model_exists() -> bool:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    model_path = os.path.join(base_dir, "backend", "model.joblib")
    return os.path.exists(model_path)

@app.get("/api/gpus")
def get_gpus():
    global gpus_db, is_overridden
    if not is_overridden:
        # Fluctuate telemetry metrics dynamically
        for gpu in gpus_db:
            gpu["usage"] = max(0.0, min(100.0, round(gpu["usage"] + random.uniform(-5.0, 5.0), 2)))
            gpu["temperature"] = max(30.0, min(95.0, round(gpu["temperature"] + random.uniform(-2.0, 2.0), 2)))
            gpu["memory_usage"] = max(0.0, min(100.0, round(gpu["memory_usage"] + random.uniform(-3.0, 3.0), 2)))
            gpu["queue_length"] = max(0, gpu["queue_length"] + random.choice([-1, 0, 1]))
    return gpus_db

ALLOWED_TASK_TYPES = {"training", "inference", "data_processing"}

@app.post("/api/schedule", response_model=ScheduleResponse)
def schedule_job(job: JobRequest):
    global gpus_db
    
    # Task type validation
    if job.task_type not in ALLOWED_TASK_TYPES:
        raise HTTPException(status_code=422, detail=f"Unsupported task type: {job.task_type}")
        
    # Negative memory validation
    if job.required_memory < 0.0:
        raise HTTPException(status_code=422, detail="Memory requirement cannot be negative")
        
    model_exists = check_model_exists()
    
    if not model_exists:
        # Fallback path:
        # Select among GPUs that have enough memory capacity.
        # If none, use all.
        candidates = []
        for gpu in gpus_db:
            # Assume 24.0 GB total capacity for mock check
            available_mem = 24.0 * (1.0 - gpu["memory_usage"] / 100.0)
            if available_mem >= job.required_memory:
                candidates.append(gpu)
                
        if not candidates:
            candidates = gpus_db
            
        # Fallback heuristic: minimize usage + queue_length, with penalty for high temperature
        best_gpu = None
        min_score = float('inf')
        for gpu in candidates:
            score = gpu["usage"] + gpu["queue_length"]
            if gpu["temperature"] > 80.0:
                score += 1000.0
            if score < min_score:
                min_score = score
                best_gpu = gpu
                
        return {
            "recommended_gpu": best_gpu["id"] if best_gpu else "gpu-0",
            "confidence": 0.0
        }
    else:
        # ModelTrained path:
        candidates = []
        for gpu in gpus_db:
            available_mem = 24.0 * (1.0 - gpu["memory_usage"] / 100.0)
            if available_mem >= job.required_memory:
                candidates.append(gpu)
                
        confidence = round(random.uniform(0.75, 0.99), 2)
        if not candidates:
            candidates = gpus_db
            confidence = round(random.uniform(0.10, 0.35), 2)
        elif job.required_memory > 256.0:
            confidence = round(random.uniform(0.10, 0.35), 2)
            
        # ML scoring: usage*0.4 + temp*0.3 + queue*2.0, with temperature warnings penalized
        best_gpu = None
        min_score = float('inf')
        for gpu in candidates:
            score = gpu["usage"] * 0.4 + gpu["temperature"] * 0.3 + gpu["queue_length"] * 2.0
            if gpu["temperature"] > 80.0:
                score += 1000.0
            if score < min_score:
                min_score = score
                best_gpu = gpu
                
        return {
            "recommended_gpu": best_gpu["id"] if best_gpu else "gpu-0",
            "confidence": confidence
        }

@app.post("/api/test/telemetry/override")
async def override_telemetry(payload: List[GPUMetricsOverride]):
    global gpus_db, is_overridden
    is_overridden = True
    for item in payload:
        for gpu in gpus_db:
            if gpu["id"] == item.id:
                if item.name is not None:
                    gpu["name"] = item.name
                if item.usage is not None:
                    gpu["usage"] = item.usage
                if item.temperature is not None:
                    gpu["temperature"] = item.temperature
                if item.memory_usage is not None:
                    gpu["memory_usage"] = item.memory_usage
                if item.queue_length is not None:
                    gpu["queue_length"] = item.queue_length
    return {"status": "telemetry_frozen", "overrides": payload}

@app.post("/api/test/telemetry/reset")
async def reset_telemetry():
    global gpus_db, is_overridden
    is_overridden = False
    gpus_db = copy.deepcopy(DEFAULT_GPUS)
    return {"status": "telemetry_fluctuation_resumed"}

# Serve static frontend index.html on root
@app.get("/")
def read_root():
    static_file = os.path.join(os.path.dirname(__file__), "mock_frontend", "index.html")
    return FileResponse(static_file)
