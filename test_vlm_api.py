#!/usr/bin/env python
"""Test script for vLLM vision API with image file, screen capture, and text prompt."""
import os
import sys
import json
import base64
import io
from PIL import Image

VLLM_URL = os.environ.get("VLLM_URL", "http://localhost:8000/v1")
VLLM_API_KEY = os.environ.get("VLLM_API_KEY", "token-abc123")
MODEL = "google/gemma-3-12b-it"

HAS_TKINTER = False
try:
    import tkinter as tk
    from tkinter import ttk
    HAS_TKINTER = True
except ImportError:
    pass


def capture_image(camera_index: int = 0) -> Image.Image:
    import cv2
    
    print(f"📸 Opening camera index {camera_index}...")
    cap = cv2.VideoCapture(camera_index)
    
    if not cap.isOpened():
        print(f"\n❌ Error: Cannot open camera at index {camera_index}")
        print(f"   Try checking your camera settings or using index 0")
        print(f"   Available test: python test_vlm_api.py --capture --camera-index 0")
        sys.exit(1)
    
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        print(f"\n❌ Error: Failed to capture frame from camera {camera_index}")
        sys.exit(1)
    
    image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    print(f"✅ Camera capture successful: {image.size[0]}x{image.size[1]}")
    return image


def encode_image_to_base64(image: Image.Image) -> str:
    buffered = io.BytesIO()
    image.save(buffered, format='JPEG')
    return base64.b64encode(buffered.getvalue()).decode('utf-8')


def show_image_preview(image: Image.Image, title: str = "Preview"):
    if not HAS_TKINTER:
        print(f"ℹ️  Preview skipped (tkinter not available)")
        return
    
    try:
        from PIL import ImageTk
        root = tk.Tk()
        root.title(title)
        root.geometry("800x600")
        
        display_img = image.copy()
        max_dim = 800
        w, h = display_img.size
        if w > max_dim or h > max_dim:
            scale = max_dim / max(w, h)
            new_size = (int(w * scale), int(h * scale))
            display_img = display_img.resize(new_size, Image.LANCZOS)
        
        tk_image = ImageTk.PhotoImage(display_img)
        
        label = ttk.Label(root, image=tk_image)
        label.pack(fill=tk.BOTH, expand=True)
        
        close_frame = ttk.Frame(root)
        close_frame.pack(fill=tk.X, pady=10)
        
        def close_window():
            root.destroy()
        
        close_btn = ttk.Button(close_frame, text="Close Preview", command=close_window)
        close_btn.pack()
        
        root.mainloop()
    except Exception as e:
        print(f"⚠️  Preview error: {e}")


def test_vision_api(image: Image.Image, prompt: str, show_preview: bool = False):
    from openai import OpenAI
    
    if show_preview:
        print(f"\n🖼️  Showing image preview...")
        show_image_preview(image, "Camera Capture Preview")
    
    img_str = encode_image_to_base64(image)
    w, h = image.size
    
    print(f"\n📊 Image info:")
    print(f"   Size: {w}x{h}")
    print(f"   Base64 length: {len(img_str)} chars")
    
    client = OpenAI(
        base_url=VLLM_URL,
        api_key=VLLM_API_KEY
    )
    
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_str}"}}
            ]
        }
    ]
    
    print(f"\n📤 Sending request to {VLLM_URL}")
    print(f"   Model: {MODEL}")
    print(f"   Prompt: {prompt}")
    
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.1,
            max_tokens=1024
        )
        
        print(f"\n✅ Response received:")
        print(f"   Model: {response.model}")
        
        content = response.choices[0].message.content
        print(f"\n📝 Response content:")
        print(f"   {content}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


def test_image_scale(image: Image.Image, target_width: int = 320):
    w, h = image.size
    
    print(f"\n📐 Image scaling test:")
    print(f"   Original: {w}x{h}")
    
    if w > target_width:
        scale = target_width / w
        new_size = (target_width, int(h * scale))
        scaled = image.resize(new_size, Image.LANCZOS)
        print(f"   Scaled: {new_size[0]}x{new_size[1]} ({scale:.2f}x)")
        
        img_str = encode_image_to_base64(scaled)
        print(f"   Scaled Base64: {len(img_str)} chars")
    else:
        print(f"   Below target width, no scaling needed")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Test vLLM vision API')
    parser.add_argument('image', nargs='?', help='Path to image file (optional, use --capture instead)')
    parser.add_argument('-p', '--prompt', default='Describe this image in one sentence',
                       help='Prompt to send with the image')
    parser.add_argument('-c', '--capture', action='store_true',
                       help='Capture image from camera instead of loading file')
    parser.add_argument('--camera-index', type=int, default=0,
                       help='Camera index to use for capture (default: 0)')
    parser.add_argument('-s', '--scale', action='store_true',
                       help='Show image scaling info')
    parser.add_argument('--no-preview', action='store_true',
                       help='Disable image preview')
    
    args = parser.parse_args()
    
    if args.capture:
        if args.image:
            print("⚠️  Warning: Both --capture and image path provided, using --capture")
        print(f"📸 Capturing image from camera index {args.camera_index}...")
        image = capture_image(args.camera_index)
    else:
        if not args.image:
            print("❌ Error: Must provide image file or use --capture")
            sys.exit(1)
        if not os.path.exists(args.image):
            print(f"❌ Error: Image not found: {args.image}")
            sys.exit(1)
        image = Image.open(args.image)
    
    if args.scale:
        test_image_scale(image)
    
    success = test_vision_api(image, args.prompt, show_preview=not args.no_preview)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()