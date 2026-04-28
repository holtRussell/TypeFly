# Quick Start Guide

## Prerequisites

1. **Python 3.10+**
2. **Docker** installed and running (for vLLM)
3. **Webcam** (for virtual mode)

## Installation

```bash
# Create virtual environment
conda create -n typefly python=3.12
conda activate typefly

# Clone and install
git clone https://github.com/typefly/TypeFly.git
cd TypeFly
pip install -e .
```

## Step 1: Start vLLM

vLLM runs as a Docker container and hosts the Gemma3-12b vision model.

```bash
# Start vLLM container (runs on port 8000)
make vllm_start

# Watch logs until ready (look for "Uvicorn running on http://0.0.0.0:8000")
make vllm_logs

# Verify vLLM is running
curl http://localhost:8000/v1/models
```

Alternatively, run vLLM locally:
```bash
pip install vllm
vllm serve google/gemma-3-12b-it --port 8000
```

## Step 2: Verify Setup (Recommended)

Run the setup test to verify everything works:

```bash
python test_vlm_setup.py
```

You should see:
```
✓ Camera: PASS
✓ Image Encoding: PASS
✓ vLLM: PASS
✓ Model: PASS
```

If any test fails, fix it before proceeding.

## Step 3: Run TypeFly Web UI

```bash
python -m typefly.webui
```

The web UI will open at `http://localhost:50000`.

**You should see:**
1. A window showing your webcam video feed
2. A chat interface for sending commands to the VLM

## Quick Test (Virtual Mode - No Physical Robot)

TypeFly runs in `virtual` mode by default, using your webcam for vision.

### Testing Steps

1. **Open** `http://localhost:50000` in your browser
2. **Wait** for the video feed to appear (your webcam)
3. **Type a command** in the chat box, e.g.:
   - "Move forward 2 meters"
   - "Rotate left 90 degrees"
   - "Move right 1 meter"
   - "Hover"
4. **Press Enter** and watch the system:
   - The VLM analyzes the image
   - Decides on an action
   - Prints the action to the chat
5. The VLM will loop and wait for more commands

### Sample Commands to Try

**Basic Movement:**
- "Move forward 2 meters"
- "Move backward 1 meter"
- "Move left 1.5 meters"
- "Move right 0.5 meters"
- "Rotate left 90 degrees"
- "Rotate right 45 degrees"

**Patterns:**
- "Fly in a square pattern"
- "Move forward, then turn left"
- "Go forward 2m, turn right, go forward 1m"

**Other Actions:**
- "Hover and observe surroundings"
- "Take a picture"

## How It Works

1. **Camera Frame** → Virtual robot captures webcam feed at 10 FPS
2. **VLM Analysis** → Gemma3-12b model analyzes the image and decides actions
3. **Action Execution** → Virtual robot simulates movement responses

**No YOLO server needed!** The VLM directly processes images.

## Services Overview

| Service | Port | Purpose |
|---------|------|---------|
| vLLM | 8000 | VLM (Gemma3-12b for vision + control) |
| Web UI | 50000 | User interface with video feed |

**No separate YOLO server required** - the VLM processes raw images directly.

## Troubleshooting

**No video feed?**
- Check camera permissions in OS settings
- Verify camera works in other applications
- Open `http://localhost:50000/robot-pov/` directly in browser

**Commands not executing?**
- Ensure vLLM is running: `make vllm_status`
- Check vLLM logs: `make vllm_logs`
- Wait a few seconds for the model to load on first request

**vLLM slow to respond?**
- First request takes longer (model loading)
- Subsequent requests should be faster
- Consider using GPU if available

**Web UI doesn't start?**
- Kill existing processes: `pkill -f "typefly.webui"`
- Check if port 50000 is available
- Watch terminal output for errors

**"Failed to open camera" error?**
- Check camera device index (default: 0)
- Try `capture: 1` or `capture: 2` in `typefly/config/robot_info.json`
- Verify camera works in other apps

**No response in chat after sending command?**
- Check terminal for VLM output
- Wait for the plan loop to complete
- Verify vLLM is running on port 8000

## Configuration

### Environment Variables

Set these to customize vLLM connection:

```bash
export VLLM_URL=http://localhost:8000/v1
export VLLM_API_KEY=token-abc123
```

### Robot Modes

Edit `typefly/config/robot_info.json` to change settings:

#### Virtual Mode (Default)
```json
{
    "robot_id": "virtual_robot",
    "robot_type": "virtual",
    "extra": {
        "capture": 0
    }
}
```

#### Tello Drone Mode
```json
{
    "robot_id": "tello1",
    "robot_type": "tello",
    "extra": {}
}
```

#### Go2 Dog Mode
```json
{
    "robot_id": "go21",
    "robot_type": "go2",
    "extra": {}
}
```

### Optional Features

```json
{
    "robot_id": "virtual_robot",
    "robot_type": "virtual",
    "extra": {
        "capture": 0,
        "yolo_enabled": false,
        "scene_image_log": false,
        "debug_mode": false
    }
}
```

- `yolo_enabled`: Enable YOLO object detection (requires YOLO server on port 50050)
- `scene_image_log`: Log analyzed images to chat
- `debug_mode`: Log full VLM responses

## Docker Commands

```bash
make vllm_start      # Start vLLM container
make vllm_stop       # Stop vLLM container
make vllm_restart    # Restart vLLM container
make vllm_logs       # View vLLM logs
make vllm_status     # Check vLLM status
make vllm_test       # Test vLLM endpoint
make vllm_remove     # Remove vLLM container
```
