import os
import pytest
import numpy as np
import pandas as pd
from backend.train import generate_mock_data, train_model
from backend.scheduler import predict_best_gpu, MODEL_PATH, clear_model_cache

def remove_file_robustly(path):
    if os.path.exists(path):
        try:
            os.remove(path)
        except PermissionError:
            import subprocess
            subprocess.run(["powershell", "-Command", f"Remove-Item -Path '{path}' -Force"], capture_output=True)

def test_dataset_generation():
    df = generate_mock_data(size=100)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 100
    assert "target" in df.columns
    # Ensure targets are valid GPU IDs
    assert set(df["target"].unique()).issubset({"gpu-0", "gpu-1", "gpu-2"})
    
    # Ensure telemetry fields exist and have valid bounds
    for i in range(3):
        assert f"gpu{i}_usage" in df.columns
        assert df[f"gpu{i}_usage"].between(10, 90).all()
        assert df[f"gpu{i}_temp"].between(30, 95).all()

def test_model_training_and_serialization():
    # If model.joblib exists, remove it to test fresh creation
    remove_file_robustly(MODEL_PATH)
    clear_model_cache()
        
    train_model()
    assert os.path.exists(MODEL_PATH)

def test_scheduler_inference():
    # First make sure model is trained
    if not os.path.exists(MODEL_PATH):
        train_model()
    clear_model_cache()
    
    # Test loading and prediction
    gpu_telemetry = [
        {"id": "gpu-0", "name": "GPU 0", "usage": 10.0, "temperature": 40.0, "memory_usage": 10.0, "queue_length": 0},
        {"id": "gpu-1", "name": "GPU 1", "usage": 80.0, "temperature": 80.0, "memory_usage": 80.0, "queue_length": 4},
        {"id": "gpu-2", "name": "GPU 2", "usage": 90.0, "temperature": 85.0, "memory_usage": 90.0, "queue_length": 5}
    ]
    
    res = predict_best_gpu(gpu_telemetry, "training", 2.0)
    assert "recommended_gpu" in res
    assert "confidence" in res
    assert res["recommended_gpu"] == "gpu-0"  # GPU 0 is clearly the best
    assert 0.0 <= res["confidence"] <= 1.0

def test_scheduler_unseen_task_type():
    # First make sure model is trained
    if not os.path.exists(MODEL_PATH):
        train_model()
    clear_model_cache()
    
    # Ensure pipeline handles unknown task types without throwing errors (using 'ignore' in OneHotEncoder)
    gpu_telemetry = [
        {"id": "gpu-0", "name": "GPU 0", "usage": 30.0, "temperature": 50.0, "memory_usage": 30.0, "queue_length": 1},
        {"id": "gpu-1", "name": "GPU 1", "usage": 30.0, "temperature": 50.0, "memory_usage": 30.0, "queue_length": 1},
        {"id": "gpu-2", "name": "GPU 2", "usage": 30.0, "temperature": 50.0, "memory_usage": 30.0, "queue_length": 1}
    ]
    res = predict_best_gpu(gpu_telemetry, "new_unseen_task", 4.0)
    assert res["recommended_gpu"] in {"gpu-0", "gpu-1", "gpu-2"}

def test_scheduler_fallback_logic():
    # Force fallback by temporarily redirecting scheduler.MODEL_PATH to a non-existent path
    import backend.scheduler as scheduler
    original_model_path = scheduler.MODEL_PATH
    scheduler.MODEL_PATH = "backend/non_existent_model.joblib"
    clear_model_cache()
    
    try:
        gpu_telemetry = [
            {"id": "gpu-0", "name": "GPU 0", "usage": 10.0, "temperature": 40.0, "memory_usage": 10.0, "queue_length": 0},
            {"id": "gpu-1", "name": "GPU 1", "usage": 80.0, "temperature": 80.0, "memory_usage": 80.0, "queue_length": 4},
            {"id": "gpu-2", "name": "GPU 2", "usage": 90.0, "temperature": 85.0, "memory_usage": 90.0, "queue_length": 5}
        ]
        
        res = predict_best_gpu(gpu_telemetry, "training", 2.0)
        assert res["recommended_gpu"] == "gpu-0"
        assert res["confidence"] == 1.0
    finally:
        scheduler.MODEL_PATH = original_model_path
        clear_model_cache()
