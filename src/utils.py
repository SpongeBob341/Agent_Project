import os
import requests
import time


# Configuration constants
API_KEY  = os.getenv("OPENAI_API_KEY", "cse476")
API_BASE = os.getenv("API_BASE", "http://10.4.58.53:41701/v1")
MODEL    = os.getenv("MODEL_NAME", "bens_model")

def call_model_chat_completions(prompt: str,
                                system: str = "You are a helpful assistant. Reply with only the final answer—no explanation.",
                                model: str = MODEL,
                                temperature: float = 0.0,
                                timeout: int = 60) -> dict:
    """
    Calls the specific /v1/chat/completions endpoint provided for the class.
    
    Args:
        prompt (str): The user query.
        system (str): The system instruction.
        model (str): The model name (default: bens_model).
        temperature (float): Determinism setting (0.0 = deterministic).
        timeout (int): Request timeout in seconds.

    Returns:
        dict: Contains 'ok' (bool), 'text' (str), 'status' (int), etc.
    """
    url = f"{API_BASE}/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type":  "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt}
        ],
        "temperature": temperature,
        "max_tokens": 8000,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
        status = resp.status_code
        hdrs   = dict(resp.headers)
        
        if status == 200:
            data = resp.json()
            # Extract content safely
            text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return {"ok": True, "text": text, "raw": data, "status": status, "error": None, "headers": hdrs}
        else:
            # Try best-effort to surface error text
            err_text = None
            try:
                err_text = resp.json()
            except Exception:
                err_text = resp.text
            return {"ok": False, "text": None, "raw": None, "status": status, "error": str(err_text), "headers": hdrs}
            
    except requests.RequestException as e:
        return {"ok": False, "text": None, "raw": None, "status": -1, "error": str(e), "headers": {}}