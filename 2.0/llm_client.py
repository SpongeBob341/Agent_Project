import os
import requests
from typing import Optional, List

class LLMClient:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY", "cse476")
        self.api_base = os.getenv("API_BASE", "http://10.4.58.53:41701/v1")
        self.model = os.getenv("MODEL_NAME", "bens_model")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def chat_completion(self, 
                        messages: list, 
                        temperature: float = 0.0, 
                        max_tokens: int = 512,
                        stop: Optional[List[str]] = None,
                        timeout: int = 120) -> Optional[str]:
        url = f"{self.api_base}/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 8000,
        }
        if stop:
            payload["stop"] = stop

        try:
            resp = requests.post(url, headers=self.headers, json=payload, timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("choices", [{}])[0].get("message", {}).get("content", "")
            else:
                return None
        except Exception:
            return None
