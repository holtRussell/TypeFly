#!/usr/bin/env python
"""Quick test script to verify VLM setup and image capture."""
import os
import cv2
from PIL import Image


def test_camera():
    """Test if camera is accessible."""
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: Camera not accessible")
        return False
    
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        print("ERROR: Failed to read frame")
        return False
    
    print("✓ Camera test passed")
    return True


def test_image_encoding():
    """Test image encoding for VLM."""
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        print("ERROR: Failed to capture image")
        return False
    
    image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    
    target_width = 320
    w, h = image.size
    if w > target_width:
        scale = target_width / w
        image = image.resize((target_width, int(h * scale)), Image.LANCZOS)
    
    import io, base64
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    
    print(f"✓ Image encoding test passed ({len(img_str)} base64 chars)")
    return True


def test_vllm():
    """Test vLLM connection."""
    import requests
    
    vllm_url = os.environ.get("VLLM_URL", "http://localhost:8000/v1")
    vllm_api_key = os.environ.get("VLLM_API_KEY", "token-abc123")
    
    try:
        response = requests.get(
            f"{vllm_url.rsplit('/v1', 1)[0]}/models",
            headers={"Authorization": f"Bearer {vllm_api_key}"},
            timeout=5
        )
        if response.status_code == 200:
            print("✓ vLLM test passed")
            return True
        else:
            print(f"ERROR: vLLM returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"ERROR: Cannot connect to vLLM: {e}")
        return False


def test_model():
    """Test if Gemma3 model is available via vLLM."""
    import requests
    
    vllm_url = os.environ.get("VLLM_URL", "http://localhost:8000/v1")
    vllm_api_key = os.environ.get("VLLM_API_KEY", "token-abc123")
    
    try:
        response = requests.get(
            f"{vllm_url.rsplit('/v1', 1)[0]}/models",
            headers={"Authorization": f"Bearer {vllm_api_key}"},
            timeout=5
        )
        data = response.json()
        models = [m.get("id", "") for m in data.get("data", [])]
        
        target_models = ["gemma-4-E2B-it", "gemma-4-e2b-it", "gemma-4-e2b", "gemma-3n-e4b-it"]
        found = any(tm in models for tm in target_models)
        
        if found:
            print(f"✓ Gemma model found: {[m for m in models if 'gemma' in m.lower()]}")
            return True
        else:
            print(f"ERROR: Gemma model not found. Available models: {models}")
            print("Start vLLM with: vllm serve google/gemma-4-E2B-it")
            return False
    except Exception as e:
        print(f"ERROR: Cannot check models: {e}")
        return False


def main():
    print("=" * 50)
    print("TypeFly vLLM VLM Setup Test")
    print("=" * 50)
    
    results = []
    results.append(("Camera", test_camera()))
    results.append(("Image Encoding", test_image_encoding()))
    results.append(("vLLM", test_vllm()))
    results.append(("Model", test_model()))
    
    print("=" * 50)
    print("Summary:")
    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False
    
    print("=" * 50)
    if all_passed:
        print("✓ All tests passed! Ready to run: python -m typefly.webui")
    else:
        print("✗ Some tests failed. Please fix before running.")
    
    return all_passed


if __name__ == "__main__":
    import sys
    sys.exit(0 if main() else 1)