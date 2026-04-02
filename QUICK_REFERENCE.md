# Quick Reference: VLM Scan Fix

## What Was Fixed
**Problem**: VLM couldn't detect objects after scanning because it never updated to the current frame.

**Solution**: Added frame refresh mechanism and scan result integration.

## Key Components

### 1. ScanResult Dataclass
```python
@dataclass
class ScanResult:
    found: bool          # Whether object was found
    location: str        # "left", "right", "center", "not visible"
    distance: str        # "close", "medium", "far", "unknown"
    description: str     # VLM analysis of object
```

### 2. Frame Freshness
```python
def wait_for_new_frame(self, timeout: float = 2.0) -> Optional[Image.Image]:
    """Wait for the latest camera frame"""
    # Blocks until current frame available or timeout
```

### 3. Enhanced Scan Method
```python
def scan_for_object(self, object_description: str) -> ScanResult:
    """Scan 360° and return detailed results"""
    # Returns: ScanResult(found=True, location="left", ...)
```

### 4. Context Integration
```python
if scan_pending:
    current_image = self.robot.obs.wait_for_new_frame(timeout=3.0)
    scene_desc = self.planner.describe_scene_vlm(current_image)
    
    if scan_result is not None:
        scan_context = f"\n\n## SCAN RESULTS\nObject found: {scan_result.found}\n..."
        scene_desc += scan_context
```

## Usage

### Basic Scan
```python
from typefly.robot_info import RobotInfo
from typefly.vlm_controller import VLMController

controller = VLMController(RobotInfo.from_dict(config))
controller.put_instruction("Scan for a blue backpack")

# VLM will:
# 1. Decide to scan
# 2. Rotate 360° checking each frame
# 3. Update scene analysis with fresh frame
# 4. Return scan results (found/location/distance)
# 5. Make next decision with full context
```

### Get Scan Results
```python
result = robot.scan_for_object("red chair")
print(f"Found: {result.found}")
print(f"Location: {result.location}")
print(f"Distance: {result.distance}")
```

### Check Frame Freshness
```python
image = robot.obs.wait_for_new_frame(timeout=2.0)
if image:
    # Use fresh frame
    pass
```

## What Changed

| Component | Before | After |
|-----------|--------|-------|
| Scan return | `bool` | `ScanResult` |
| Server frame | Stale (initial) | Fresh (current) |
| Location info | None | left/right/center |
| Distance info | None | close/medium/far |
| Context | No scan results | Integrated into ## SCENE ANALYSIS |

## Testing

```bash
# Run unit tests
python test_scan_fix.py

# Run demo
python demo_scan_fix.py

# Full system test
python -m typefly.webui
```

## Configuration

No changes needed. Existing config works as-is:

```json
{
    "extra": {
        "yolo_enabled": false
    }
}
```

## Key Files

- `typefly/robot_wrapper.py` - Base class + ScanResult
- `typefly/vlm_controller.py` - Scan feedback loop
- `typefly/platforms/*.py` - Platform wait_for_new_frame
- `test_scan_fix.py` - Unit tests
- `demo_scan_fix.py` - Demo script

## What Happens During Scan

1. **User**: "Scan for red backpack"
2. **VLM**: `[ACTION] scan for red backpack`
3. **Robot**: Rotates 45° × 8 (360°)
   - At each step: Fresh frame → VLM checks for backpack
4. **After rotation**: Wait for fresh frame → Re-analyze scene
5. **Context updated**: `## SCAN RESULTS` added to scene analysis
6. **VLM decides**: Next action with full context

## Benefits

✅ **Real-time awareness**: Always see current frame  
✅ **Rich results**: Location + distance included  
✅ **Context-aware**: VLM makes informed decisions  
✅ **Cross-platform**: Works on Virtual/Tello/Go2/Pod  
✅ **No YOLO**: 100% VLM-based perception  

## Migration Guide

### For Code Calling scan_for_object()

**Before:**
```python
found = robot.scan_for_object("backpack")
if found:
    # do something
```

**After:**
```python
result = robot.scan_for_object("backpack")
if result.found:
    print(f"Found at {result.location}, {result.distance} away")
    # do something
```

### For Code Using VLMController

No changes needed! The controller handles everything automatically.

## Troubleshooting

### Frame not updating
- Check camera is running: `robot.obs.image`
- Check wait timeout is sufficient: Increase from 2.0s
- Check camera thread is running: `robot.obs.running`

### Scan results not integrated
- Verify VLM output contains "scan" keyword
- Check scan_result is not None before inserting context
- Verify scene_image_log is enabled for logging

### Platform-specific issues
- **Virtual**: Check camera index in robot_info.extra["capture"]
- **Tello**: Ensure drone is connected and streaming
- **Go2**: Verify ROS camera topics are available
- **Pod**: Check podtp connection is active

## Summary

**3 Lines to Remember:**
1. Use `wait_for_new_frame()` to ensure fresh frames
2. `scan_for_object()` returns `ScanResult` with location/distance
3. VLMController automatically integrates scan results into context
