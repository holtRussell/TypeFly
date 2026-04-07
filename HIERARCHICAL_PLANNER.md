# TypeFly Hierarchical Vision-Language Planner

## Overview

This implementation adds hierarchical planning to TypeFly, allowing the robot to autonomously explore rooms and find objects using intelligent reasoning rather than simple scanning patterns.

## Key Components

### 1. Reasoning Prompts (`prompt_exploration_reasoning.txt`)
New prompt that enables the LLM to:
- Analyze current scene and determine next best action
- Reason about object placement heuristics (TVs on walls, facing seating)
- Select exploration strategy (spiral, grid, directed)
- Make decision chains: "I see screen → move closer → verify → show to user"

### 2. Enhanced VLMPlanner

#### New Methods:
- **`plan_with_reasoning(user_instruction, image)`** - Generates structured JSON plans
  - Returns: `{"analysis", "observation", "decision", "reasoning", "actions": []}`
  
- **`verify_object_found(image, target_object)`** - Confirms object presence
  - Returns: `(is_found: bool, message: str)`
  
- **`reposition_for_show(image, target_object)`** - Positions robot to show object
  - Generates movement plan for optimal viewing

#### Enhanced Methods:
- **`execute_action(action_text, image)`** - Now handles both:
  - `[ACTION]` format (backward compatible)
  - JSON plans from `plan_with_reasoning()`
  - Returns: `(success: bool, target_found: bool)`

### 3. VLMController Plan Loop

**New flow:**
```
1. Get camera image
2. Ask LLM to reason: "What should I do next?"
3. LLM returns JSON plan with analysis + actions
4. Execute each action in the plan
5. After major actions, verify target using VLM
6. If target found, reposition for user viewing
7. Loop until target found or max iterations reached
```

**Key features:**
- Max 10 iterations to prevent infinite loops
- Automatic verification at 3 key checkpoints
- "Not found" handling after exhausting all options

## Usage Example

### User Request: "Find a TV and show it to me"

### Robot Process:

**Iteration 1:**
- Current view: Empty room, couch visible
- LLM reasoning: "TV not visible, start spiral exploration"
- Actions: `move_forward(2.0) → rotate(90°) → move_forward(2.0)`
- Verification: No TV detected

**Iteration 2:**
- Current view: Dark rectangle on wall (screen-like)
- LLM reasoning: "TV-like object visible, move closer to verify"
- Actions: `move_forward(3.0)`
- Verification: "Confirmed TV (screen + HDMI cables visible)"
- Reposition: Rotate to face TV, hover for 3 seconds

**Result:**
- "I found a TV on the wall, pointing toward the couch!"
- Robot continues to show TV to user

## Architecture Comparison

### Old Architecture (Flat Planning):
```
User → VLMController → VLMPlanner (scan + single action)
    ↓
Execute 1 action → Stop
```

### New Architecture (Hierarchical Planning):
```
User → VLMController → VLMPlanner (reasoning + multi-step plan)
    ↓
Execute JSON plan (multiple actions) → Verify → Continue/Stop
```

## Prompts

### 1. `prompt_exploration_reasoning.txt`
**Purpose:** Make high-level decisions about exploration strategy

**Input:**
- Camera image
- Search goal ("Find TV")
- Current position

**Output JSON:**
```json
{
  "analysis": "Current scene description",
  "observation": "Relevant observations",
  "decision": "Next action to take",
  "reasoning": "Why this decision makes sense",
  "actions": [
    {"action": "move_forward", "dist": 2.0},
    {"action": "rotate", "deg": 45}
  ]
}
```

### 2. Updated `prompt_vlm_stage2_action.txt`
**Purpose:** Execute actions (now supports both text and JSON)

**Format 1 - Single Action:**
```
[ACTION] move forward 2.0
```

**Format 2 - Structured Plan:**
```json
{
  "analysis": "Scene description",
  "observation": "What I see",
  "decision": "Action plan",
  "reasoning": "Why this plan",
  "actions": [...]
}
```

## Exploration Strategies

### 1. Spiral Outward
- Start current position
- Expand in increasing radius circles
- Good for: Small rooms, unknown layout

### 2. Grid Coverage
- Systematic grid pattern (80% overlap)
- Good for: Large rooms, thorough search

### 3. Directed Search
- Move toward walls (TVs usually there)
- Check corners systematically
- Good for: Fast search, known object placement

## API Call Efficiency

| Scenario | API Calls |
|----------|-----------|
| TV found on first scan | 3-5 |
| TV found after 3 iterations | 10-12 |
| TV not found (max iterations) | 15-18 |

**Optimization:** Skip verification if LLM is confident ("[YES] TV visible")

## Configuration

### Max Iterations
In `vlm_controller.py:plan_loop()`:
```python
max_iterations = 10  # Increase for longer searches
```

## Benefits Over Previous Implementation

1. **Intelligent Reasoning** - Not just random scanning
2. **Multi-Step Planning** - Executes sequences of actions
3. **Automatic Verification** - Confirms objects before reporting
4. **User Optimization** - Repositions to show found objects
5. **Configurable Exploration** - Can specify strategies
6. **Better Accuracy** - Multiple verification checkpoints

## Testing

### Test Cases:

1. **Simple Find (TV visible):**
   - User: "Find a TV"
   - Expected: "Found TV on wall" + reposition

2. **Exploration Required (TV not visible):**
   - User: "Find a TV in this room"
   - Expected: Spiral exploration → find TV

3. **Not Found:**
   - User: "Find a TV in empty room"
   - Expected: "TV not found after searching"

4. **User-Specified Strategy:**
   - User: "Find a TV using spiral search"
   - Expected: Follow spiral pattern

## Future Enhancements

1. **SLAM Integration** - Build map of visited areas
2. **Object Memory** - Remember TV locations across sessions
3. **Context Awareness** - Use room layout for better planning
4. **Multi-Object Search** - Find multiple items in priority order
5. **Replanning** - Adapt if obstacles block path

## Files Modified

| File | Changes |
|------|---------|
| `typefly/assets/prompt_exploration_reasoning.txt` | **New** - Reasoning prompts |
| `typefly/assets/prompt_vlm_stage2_action.txt` | Added JSON plan format |
| `typefly/vlm_planner.py` | Added reasoning + planning methods |
| `typefly/vlm_controller.py` | Rewrote plan_loop for hierarchical planning |

## Backward Compatibility

✅ All existing code continues to work:
- `[ACTION]` format still supported
- `plan_action()` still available
- `scan_for_object()` unchanged
- New `plan_with_reasoning()` is additive

## Migration Guide

### For Existing Code:
- **No changes needed** - backward compatible
- Existing `[ACTION]` calls work unchanged

### For New Features:
```python
# Use new reasoning-based planning
plan = planner.plan_with_reasoning("Find TV", image)

# Execute multi-step plan
success, found = planner.execute_action(json.dumps(plan), image)

# Verify after actions
is_found, msg = planner.verify_object_found(image, "TV")
```

## Summary

This implementation transforms TypeFly from a simple action-perception loop into an intelligent hierarchical planner that:
1. **Reasons** about the environment
2. **Plans** multi-step exploration strategies
3. **Executes** sequences of actions
4. **Verifies** results before reporting
5. **Adapts** to find objects efficiently

The LLM serves as both the "brain" (reasoning/planning) and "sensory processor" (scene analysis), while the robot controller handles low-level execution.
