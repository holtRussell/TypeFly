# TypeFly with VLM

TypeFly now uses **Gemma3 Visual Language Models** for end-to-end drone control. The VLM observes raw camera images and makes direct control decisions through a two-stage process:
1. **Scene Analysis**: VLM describes what it sees in the current image
2. **Action Decision**: VLM decides actions based on scene + user instruction

## 1. Installation
[Optional] Create a conda environment.
```bash
conda create -n typefly python=3.12
conda activate typefly
```

Clone this repo and install the package.
```bash
git clone https://github.com/typefly/TypeFly.git
cd TypeFly
pip install -e .
```

## 2. Hardware Requirement

### Test without Robot (Virtual Mode) - Recommended for Testing
By default, typefly will try to access your camera with `cv2.VideoCapture(0)` and let the VLM control movement. This is perfect for testing without physical hardware.

### Tello Drone
TypeFly works with the DJI Tello drone. Since Tello requires WiFi and TypeFly needs Internet, you need both WiFi adapter and ethernet adapter. Change `robot_type` from `virtual` to `tello` in `typefly/config/robot_info.json`.

### Go2 Dog
To control a Unitree Go2 robot dog, install ROS2 and run the [go2_ros2_sdk](https://github.com/abizovnuralem/go2_ros2_sdk). Change `robot_type` to `go2`.

### Other Robots
Implement robot control interface based on `RobotWrapper` (see `typefly/platforms/*`).

## 3. OLLAMA API Requirement

TypeFly uses OLLAMA as the local VLM planner. Connects to `http://localhost:11434` by default. Configure via `OLLAMA_URL` environment variable.

### Pull the VLM Model
```bash
ollama pull gemma3:12b
```

## 4. Configuration

Edit `typefly/config/robot_info.json` to configure your system:

### Virtual Mode (Default)
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

### Tello Drone Mode
```json
{
    "robot_id": "tello1",
    "robot_type": "tello",
    "extra": {
        "yolo_enabled": false
    }
}
```

### Configuration Options
- `capture`: Camera index (0 for default webcam)
- `yolo_enabled`: Set to `true` to enable optional YOLO object detection (disabled by default)
- `scene_image_log`: Set to `true` to display analyzed images in chat log
- `debug_mode`: Set to `true` to log full VLM responses for debugging

## 5. Vision System

**VLM-Only Architecture!** The VLM (Gemma3-12b) observes raw camera images directly and makes control decisions through two stages:
1. Scene Analysis: Describes visible objects and layout
2. Action Decision: Chooses actions based on scene + user instruction

**YOLO is optional**: YOLO service can be enabled via config but is disabled by default.

## 6. Start TypeFly Web UI
```bash
python -m typefly.webui
```
Then open http://localhost:50000 in your browser.

### Testing Steps:
1. Verify setup: `python test_vlm_setup.py`
2. Start web UI: `python -m typefly.webui`
3. Type commands in the chat box (e.g., "move forward 2 meters")
4. Watch the VLM analyze the scene and execute commands

### Sample Commands:
- "Move forward 2 meters"
- "Rotate left 90 degrees"
- "Fly in a square pattern"
- "Hover and observe surroundings"
- "Describe the scene"

