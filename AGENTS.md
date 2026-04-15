# AGENTS.md

## Build Commands

```bash
# Install in editable mode
pip install -e .

# Build Docker serving container
make serving_build

# Stop Docker container
make serving_stop

# Start Docker container
make serving_start
```

## Test Commands

This repository currently does not have automated test files. Tests would be run manually through the web UI or command-line execution.

## Lint Commands

No linting configuration is currently present. Consider adding:
- `ruff` for linting
- `mypy` for type checking
- `black` for formatting

## Code Style Guidelines

### General
- Python 3.10+ required
- Use absolute imports within the package (e.g., `from .skill_item import SkillItem`)
- Keep imports sorted: stdlib, then third-party, then local
- Use type hints throughout

### Naming Conventions
- Classes: `PascalCase` (e.g., `SkillItem`, `LLMWrapper`, `RobotWrapper`)
- Functions/variables: `snake_case` (e.g., `move_forward`, `object_x`)
- Enum members: `UPPERCASE` (e.g., `ModelType.LLAMA3_8B`)
- Constants: `UPPER_CASE_WITH_UNDERSCORES` (e.g., `SKILL_EXECUTION_TIME`)

### Type Hints
- Use `int`, `float`, `str`, `bool`, `None` for primitives
- Use `list[T]`, `dict[K, V]` for collections
- Use `Optional[T]` for nullable types
- Use `ndarray` from numpy for numpy arrays
- Use `Image.Image` for PIL images
- Union types with `|` syntax: `model_type: ModelType | str`

### Error Handling
- Raise `ValueError` for invalid arguments or missing data
- Raise `TypeError` for type mismatches (see `SkillItem.__init__`)
- Check for None before accessing properties
- Validate required config keys (e.g., `robot_info.extra["capture"]`)

### docstrings
- Use triple-quoted docstrings for all public classes and functions
- Include parameter types and return types in docstrings
- Use imperative mood: "Returns", "Sets", "Starts"

### Imports
```python
# Standard library first
import os
import asyncio
from abc import ABC, abstractmethod
from typing import Optional, List, dict

# Third-party second
import cv2
import numpy as np
from PIL import Image

# Local third
from .skill_item import SkillItem
from .utils import print_t
```

### File Organization
- Core logic: `typefly/*.py` (LLM, planning, control)
- Platform-specific: `typefly/platforms/*.py` (robot wrappers)
- Serving: `typefly/serving/*.py` (gRPC services, YOLO)
- Protos: `typefly/proto/` (protocol buffer definitions)

### Comments
- Add docstring at top of files (e.g., `# hello world`)
- Use inline comments sparingly
- Explain why, not what

## Special Notes

- **LLM Integration**: Uses vLLM with OpenAI-compatible API at `http://localhost:8000/v1`. Configure with `VLLM_URL` and `VLLM_API_KEY` environment variables. Default model: `google/gemma-3-12b-it`.
- **Vision**: VLM (Gemma3-12b) analyzes raw camera images through two stages:
  1. Scene Analysis: Describes visible objects and layout
  2. Action Decision: Chooses actions based on scene + user instruction
- **YOLO**: Optional object detection via gRPC service on port 50050 (disabled by default)
- **Robot Platforms**: Supports virtual (webcam), DJI Tello drone, Unitree Go2 dog, and custom robots via `RobotWrapper` interface
- **Web UI**: Flask-based at `typefly/webui.py`, runs on port 50000

## Development

```bash
# Start VLM planning with virtual robot
python -m typefly.webui

# Start YOLO serving (optional)
python -m typefly.serving
```

## Configuration

Edit `typefly/config/robot_info.json` to configure:

```json
{
    "extra": {
        "capture": 0,
        "yolo_enabled": false,
        "scene_image_log": false,
        "debug_mode": false
    }
}
```

- `yolo_enabled`: Enable YOLO object detection (default: false)
- `scene_image_log`: Log analyzed images to chat (default: false)
- `debug_mode`: Log full VLM responses (default: false)
