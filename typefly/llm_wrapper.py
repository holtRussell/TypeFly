# hello world
import os
import requests
from enum import Enum

class ModelType(Enum):
    LLAMA3_8B = "llama3:8b-10k"
    LLAMA3 = "llama3"
    LLAMA3_70B = "llama3:70b"
    LLAMA3_1 = "llama3.1"
    LLAMA3_2 = "llama3.2"

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CHAT_LOG_FILE = os.path.join(CURRENT_DIR, "assets/chat_log.txt")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")

class LLMWrapper:
    """
    A wrapper for the LLM API.
    """
    def __init__(self, temperature: float=0.1):
        self.temperature = temperature
        self.ollama_url = OLLAMA_URL

    def request(self, prompt, model_type: ModelType | str) -> str:        
        """
        Request the LLM API with the prompt and model type.
        """
        model_name = model_type.value if isinstance(model_type, ModelType) else model_type

        payload = {
            "model": model_name,
            "prompt": prompt,
            "temperature": self.temperature,
            "stream": False
        }

        response = requests.post(f"{self.ollama_url}/api/generate", json=payload)
        response.raise_for_status()
        
        ret = response.json().get("response", "")

        with open(CHAT_LOG_FILE, "a") as f:
            f.write(prompt + "\n---\n")
            f.write(ret + "\n--------------------------------\n")

        return ret