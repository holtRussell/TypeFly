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
    
    # Convert to PIL Image
    image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    
    # Downscale (as VLM does)
    target_width = 320
    w, h = image.size
    if w > target_width:
        scale = target_width / w
        image = image.resize((target_width, int(h * scale)), Image.LANCZOS)
    
    # Encode to base64
    import io, base64
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    
    print(f"✓ Image encoding test passed ({len(img_str)} base64 chars)")
    return True

def test_ollama():
    """Test OLLAMA connection."""
    import requests
    
    try:
        response = requests.get("http://localhost:11434", timeout=5)
        if response.status_code == 200:
            print("✓ OLLAMA test passed")
            return True
        else:
            print(f"ERROR: OLLAMA returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"ERROR: Cannot connect to OLLAMA: {e}")
        return False

def test_model():
    """Test if Gemma3N model is available."""
    import requests
    
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        data = response.json()
        models = [m.get("name", "") for m in data.get("models", [])]
        
        if "gemma3n:e4b" in models:
            print("✓ Gemma3N model found")
            return True
        else:
            print(f"ERROR: gemma3n:e4b not found. Available models: {models}")
            print("Run: ollama pull gemma3n:e4b")
            return False
    except Exception as e:
        print(f"ERROR: Cannot check models: {e}")
        return False

def main():
    print("=" * 50)
    print("TypeFly VLM Setup Test")
    print("=" * 50)
    
    results = []
    results.append(("Camera", test_camera()))
    results.append(("Image Encoding", test_image_encoding()))
    results.append(("OLLAMA", test_ollama()))
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
