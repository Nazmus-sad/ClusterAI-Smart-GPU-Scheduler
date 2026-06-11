import os
import joblib
import pandas as pd

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model.joblib")
_pipeline = None

def load_model(reload=False):
    """Lazy load the serialized model pipeline."""
    global _pipeline
    if reload:
        _pipeline = None
    if _pipeline is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                f"Model file not found at {MODEL_PATH}. "
                "Please run 'python backend/train.py' first to generate and train the model."
            )
        _pipeline = joblib.load(MODEL_PATH)
    return _pipeline

def clear_model_cache():
    """Clear the cached pipeline to force reloading from disk."""
    global _pipeline
    _pipeline = None

def predict_best_gpu(gpu_telemetry: list, task_type: str, required_memory: float) -> dict:
    """
    Predicts the best GPU using the trained Random Forest model.
    Falls back to a rule-based heuristic prediction logic if the model fails to load.
    
    Inputs:
    - gpu_telemetry: list of dicts (each having: usage, temperature, memory_usage, queue_length, name, id)
    - task_type: string ('training', 'inference', 'data_processing')
    - required_memory: float (memory required by the task in GB)
    
    Outputs:
    - dict containing:
        - recommended_gpu: string (GPU ID, e.g., 'gpu-0')
        - confidence: float (model prediction probability [0.0, 1.0] or 1.0 for heuristic fallback)
    """
    try:
        pipeline = load_model()
        
        # Reorganize telemetry by GPU ID to construct consistent model features
        telemetry_by_id = {gpu["id"]: gpu for gpu in gpu_telemetry}
        
        row = {}
        for i in range(3):
            gpu_id = f"gpu-{i}"
            # Fallback values if telemetry for a specific GPU ID is missing
            gpu = telemetry_by_id.get(gpu_id, {
                "usage": 50.0,
                "temperature": 50.0,
                "memory_usage": 50.0,
                "queue_length": 0
            })
            row[f"gpu{i}_usage"] = float(gpu["usage"])
            row[f"gpu{i}_temp"] = float(gpu["temperature"])
            row[f"gpu{i}_mem"] = float(gpu["memory_usage"])
            row[f"gpu{i}_queue"] = int(gpu["queue_length"])
            
        row["task_type"] = task_type
        row["required_memory"] = float(required_memory)
        
        # Construct DataFrame and enforce exact feature order from training
        df = pd.DataFrame([row])
        columns_order = []
        for i in range(3):
            columns_order.extend([f"gpu{i}_usage", f"gpu{i}_temp", f"gpu{i}_mem", f"gpu{i}_queue"])
        columns_order.extend(["task_type", "required_memory"])
        df = df[columns_order]
        
        recommended_gpu = pipeline.predict(df)[0]
        
        # Fetch prediction confidence (probability)
        probs = pipeline.predict_proba(df)[0]
        classes = list(pipeline.classes_)
        class_idx = classes.index(recommended_gpu)
        confidence = float(probs[class_idx])
        
        return {
            "recommended_gpu": recommended_gpu,
            "confidence": confidence
        }
        
    except Exception as e:
        print(f"Prediction failed or model not loaded. Error: {e}. Falling back to cost heuristic.")
        
        # Heuristic implementation matching the target label rules
        if not gpu_telemetry:
            return {"recommended_gpu": "gpu-0", "confidence": 0.0}
            
        best_gpu_id = None
        best_cost = float("inf")
        
        for gpu in gpu_telemetry:
            gpu_id = gpu.get("id", "gpu-0")
            u = float(gpu.get("usage", 50.0))
            t = float(gpu.get("temperature", 50.0))
            m = float(gpu.get("memory_usage", 50.0))
            q = int(gpu.get("queue_length", 0))
            
            # Available VRAM
            available_mem_gb = 24.0 * (1.0 - m / 100.0)
            penalty = 10000.0 if available_mem_gb < required_memory else 0.0
            
            # Thermal cost
            temp_cost = t + max(0.0, t - 80.0) * 5.0
            queue_cost = q * 15.0
            
            if task_type == 'training':
                cost = penalty + 0.5 * u + 0.4 * temp_cost + 0.1 * queue_cost
            elif task_type == 'inference':
                cost = penalty + 0.3 * u + 0.1 * temp_cost + 0.6 * queue_cost
            elif task_type == 'data_processing':
                cost = penalty + 0.2 * u + 0.1 * temp_cost + 0.4 * queue_cost + 0.3 * m
            else:
                cost = penalty + 0.3 * u + 0.3 * temp_cost + 0.4 * queue_cost
                
            if cost < best_cost:
                best_cost = cost
                best_gpu_id = gpu_id
                
        return {
            "recommended_gpu": best_gpu_id if best_gpu_id is not None else "gpu-0",
            "confidence": 1.0
        }
