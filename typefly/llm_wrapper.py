import os
import io
import base64
from enum import Enum
from PIL import Image
from typing import Optional, List, Dict, Any

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


class ModelType(Enum):
    LLAMA3_8B = "meta-llama/Meta-Llama-3-8B-Instruct"
    LLAMA3 = "meta-llama/Meta-Llama-3-8B-Instruct"
    LLAMA3_70B = "meta-llama/Meta-Llama-3-70B-Instruct"
    LLAMA3_1 = "meta-llama/Meta-Llama-3.1-8B-Instruct"
    LLAMA3_2 = "meta-llama/Meta-Llama-3.2-8B-Instruct"
    GEMMA3N = "gemma-4-E2B-it"
    GEMMA3 = "gemma-4-E2B-it"


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CHAT_LOG_FILE = os.path.join(CURRENT_DIR, "assets/chat_log.txt")

LLAMA_SERVER_URL = os.environ.get("LLAMA_SERVER_URL", "http://localhost:8080/v1")
LLAMA_SERVER_API_KEY = os.environ.get("LLAMA_SERVER_API_KEY", "token-abc123")


def print_t(msg: str) -> None:
    print(msg)


class LLMWrapper:
    """
    A wrapper for llama.cpp server (OpenAI-compatible API).
    """
    def __init__(self, temperature: float = 0.1):
        self.temperature = temperature
        self.llama_url = LLAMA_SERVER_URL
        self.api_key = LLAMA_SERVER_API_KEY
        self._client = None

    @property
    def client(self) -> Optional[OpenAI]:
        if self._client is None and OpenAI is not None:
            self._client = OpenAI(
                base_url=self.llama_url,
                api_key=self.api_key
            )
        return self._client

    def request(self, prompt: str, model_type: ModelType | str) -> str:
        model_name = model_type.value if isinstance(model_type, ModelType) else model_type

        if self.client is None:
            raise RuntimeError("OpenAI client not available. Install with: pip install openai")

        response = self.client.completions.create(
            model=model_name,
            prompt=prompt,
            temperature=self.temperature,
            max_tokens=2048
        )

        ret = response.choices[0].text or ""

        with open(CHAT_LOG_FILE, "a") as f:
            f.write(prompt + "\n---\n")
            f.write(ret + "\n--------------------------------\n")

        return ret

    def request_multimodal(
        self,
        prompt: str,
        image: Image.Image,
        model_type: ModelType | str = ModelType.GEMMA3,
        tools: Optional[List] = None
    ) -> tuple[str, Optional[List], str]:
        model_name = model_type.value if isinstance(model_type, ModelType) else model_type

        buffered = io.BytesIO()
        image.save(buffered, format="JPEG")
        image_bytes = buffered.getvalue()
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        debug_mode = os.environ.get("VLM_DEBUG", "false").lower() == "true"
        if debug_mode:
            print_t(f"[DEBUG] Image size: {image.size}, Bytes: {len(image_bytes)}, Base64: {len(image_base64)}")
            print_t(f"[DEBUG] Prompt length: {len(prompt)} chars")
            print_t(f"[DEBUG] Model: {model_name}")

        if self.client is None:
            raise RuntimeError("OpenAI client not available. Install with: pip install openai")

        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
                }
            ]
        }]

        extra_kwargs = {}
        if tools:
            extra_kwargs["tools"] = tools

        response = self.client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=self.temperature,
            max_tokens=2048,
            **extra_kwargs
        )

        message = response.choices[0].message
        content = message.content or ""

        tool_calls = []
        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                })

        finish_reason = response.choices[0].finish_reason

        with open(CHAT_LOG_FILE, "a") as f:
            f.write(prompt + "\n---\n")
            f.write(content + "\n--------------------------------\n")

        return content, tool_calls, finish_reason