import os
import requests
from enum import Enum
import base64
import io
from PIL import Image

class ModelType(Enum):
    LLAMA3_8B = "llama3:8b-10k"
    LLAMA3 = "llama3"
    LLAMA3_70B = "llama3:70b"
    LLAMA3_1 = "llama3.1"
    LLAMA3_2 = "llama3.2"
    GEMMA3N = "gemma3n:e4b"
    GEMMA3 = "gemma3:12b"

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

    def request_multimodal(self, prompt: str, image: Image.Image, model_type: ModelType | str = ModelType.GEMMA3) -> str:
        model_name = model_type.value if isinstance(model_type, ModelType) else model_type

        buffered = io.BytesIO()
        image.save(buffered, format="JPEG")
        image_bytes = buffered.getvalue()
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        
        import os
        debug_mode = os.environ.get("VLM_DEBUG", "false").lower() == "true"
        if debug_mode:
            print_t(f"[DEBUG] Image size: {image.size}, Bytes: {len(image_bytes)}, Base64: {len(image_base64)}")
            print_t(f"[DEBUG] Prompt length: {len(prompt)} chars")
            print_t(f"[DEBUG] Model: {model_name}")

        payload = {
            "model": model_name,
            "messages": [{
                "role": "user",
                "content": prompt,
                "images": [image_base64]
            }],
            "stream": False
        }

        response = requests.post(f"{self.ollama_url}/api/chat", json=payload)
        response.raise_for_status()
        
        ret = response.json().get("message", {}).get("content", "")

        with open(CHAT_LOG_FILE, "a") as f:
            f.write(prompt + "\n---\n")
            f.write(ret + "\n--------------------------------\n")

        return ret
