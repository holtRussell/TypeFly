#!/usr/bin/env python
"""Test Ollama streaming behavior"""
import cv2
import base64
import io
from PIL import Image
import requests
import json

# Capture image
cap = cv2.VideoCapture(0)
ret, frame = cap.read()
cap.release()
image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

# Encode
buffered = io.BytesIO()
image.save(buffered, format='JPEG')
img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')

# Test with stream=False
payload = {
    'model': 'gemma4:26b',
    'messages': [{
        'role': 'user',
        'content': 'What do you see?',
        'images': [img_str]
    }],
    'stream': False
}

print('Testing with stream=False...')
response = requests.post('http://localhost:11434/api/chat', json=payload, timeout=60)

print('Status:', response.status_code)
print('Content-Type:', response.headers.get('Content-Type'))

# Check if it's streaming by looking at lines
lines = response.text.strip().split('\n')
print(f'Number of lines: {len(lines)}')

for i, line in enumerate(lines[:3]):
    print(f'Line {i}:', line[:100] if len(line) > 100 else line)

# Try to parse as JSON
try:
    result = response.json()
    print('Parsed as single JSON!')
    print('Content:', result.get('message', {}).get('content', '')[:200])
except Exception as e:
    print('Error parsing JSON:', e)
    print('Need to parse as NDJSON (newline-delimited JSON)')
