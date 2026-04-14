import os
import re
import json
from typing import Optional, List
from PIL import Image

from .llm_wrapper import LLMWrapper, ModelType
from .utils import print_t, CURRENT_PROJ_DIR
from .robot_wrapper import RobotWrapper
from .robot_info import RobotInfo
from .skill_item import SkillItem


class VLMPlanner:
    def __init__(self, robot: RobotWrapper, model_type: ModelType = ModelType.GEMMA4):
        self.llm = LLMWrapper()
        self.robot = robot
        self.model_type = model_type

        assets_path = os.path.join(CURRENT_PROJ_DIR, f"./assets")
        with open(os.path.join(assets_path, "prompt_vlm_stage1_scene.txt"), "r") as f:
            self.prompt_scene_stage1 = f.read()
        with open(os.path.join(assets_path, "prompt_vlm_stage2_action.txt"), "r") as f:
            self.prompt_action_stage2 = f.read()

    def _encode_image(self, image) -> str:
        import io
        import base64
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")

    def _call_llm(self, prompt: str, image: Image.Image, num_visual_tokens: Optional[int] = None, system_prompt: Optional[str] = None) -> tuple[str, Optional[List], str]:
        """Call LLM with Gemma4 optimizations for faster image analysis"""
        return self.llm.request_multimodal(
            prompt, image, self.model_type,
            temperature=1.0,
            num_visual_tokens=num_visual_tokens,
            system_prompt=system_prompt
        )

    def _scale_image(self, image, target_width=320):
        w, h = image.size
        if w <= target_width:
            return image
        scale = target_width / w
        new_size = (target_width, int(h * scale))
        return image.resize(new_size, Image.LANCZOS)

    def describe_scene_vlm(self, image: Image.Image) -> str:
        scaled_image = self._scale_image(image)
        prompt = self.prompt_scene_stage1.format(
            robot_skills=str(self.robot.skillset)
        )
        
        scene_description, _, _ = self._call_llm(prompt, scaled_image, num_visual_tokens=70)
        return scene_description.strip()

    def plan_action(self, user_instruction: str, scene_description: str, image: Image.Image) -> str:
        scaled_image = self._scale_image(image)
        
        prompt = self.prompt_action_stage2.format(
            robot_skills=str(self.robot.skillset),
            user_instruction=user_instruction,
            scene_context=scene_description
        )
        
        result, _, _ = self._call_llm(prompt, scaled_image, num_visual_tokens=140)
        return result

    def describe_scene_vlm_with_target(self, image: Image.Image, target_object: str) -> str:
        scaled_image = self._scale_image(image)
        
        prompt_template = """# STAGE 1: SCENE ANALYSIS WITH TARGET FOCUS
You are analyzing a current camera image from a drone to find a specific object.

# OBJECT TO FIND
{target_object}

# INPUT
- You receive the current camera image
- Observe the scene carefully

# TASK
Provide a concise analysis of:
1. Is the target object visible? (YES/NO/Unclear)
2. If visible: location (left/right/center), approximate distance, distinctive features
3. If not visible: areas that should be checked next
4. Overall scene context (room layout, obstacles, lighting)

# OUTPUT FORMAT
- Visibility: [YES/NO/Unclear]
- Location: [description]
- Features: [description]
- Scene context: [1-2 sentences]

# VISIBILITY CUE
If the object is visible, you MUST respond with [YES] at the start of your response.
If the object is not visible, you MUST respond with [NO] at the start of your response."""
        
        prompt = prompt_template.format(target_object=target_object)
        scene_description, _, _ = self._call_llm(prompt, scaled_image, num_visual_tokens=70)
        return scene_description.strip()

    def plan_with_target(self, user_instruction: str, target_object: str, image=None) -> str:
        from .skill_item import SkillItem

        if image is None:
            raise ValueError("Image is required for VLM planning")

        scene_description = self.describe_scene_vlm_with_target(image, target_object)
        print_t(f"[VLM] Scene (target: {target_object}): {scene_description}")

        vlm_output = self.plan_action(user_instruction, scene_description, image)
        print_t(f"[VLM] Action: {vlm_output}")

        return vlm_output

    def plan_with_reasoning(self, user_instruction: str, image: Image.Image) -> dict:
        from .skill_item import SkillItem
        import json

        if image is None:
            raise ValueError("Image is required for VLM planning")

        scaled_image = self._scale_image(image)
        
        assets_path = os.path.join(CURRENT_PROJ_DIR, f"./assets")
        with open(os.path.join(assets_path, "prompt_exploration_reasoning.txt"), "r") as f:
            prompt_reasoning = f.read()
        
        system_prompt = "<|think|>\nYou are a precise robot controller that reasons step-by-step before acting."
        
        # Escape JSON braces in prompt before formatting
        prompt_text = prompt_reasoning.replace("{", "{{").replace("}", "}}")
        prompt_text = prompt_text.replace("[user_instruction]", "{user_instruction}")
        prompt_text = prompt_text.format(user_instruction=user_instruction)
        
        response, _, _ = self._call_llm(prompt_text, scaled_image, num_visual_tokens=280, system_prompt=system_prompt)
        
        print_t(f"[VLM] Reasoning response: {response}")
        
        try:
            response_clean = response.strip()
            if response_clean.startswith('```json'):
                response_clean = response_clean[7:]
            if response_clean.startswith('```'):
                response_clean = response_clean[3:]
            if response_clean.endswith('```'):
                response_clean = response_clean[:-3]
            response_clean = response_clean.strip()
            
            plan = json.loads(response_clean)
            print_t(f"[VLM] Parsed plan: {json.dumps(plan, indent=2)}")
            
            return plan
        except json.JSONDecodeError:
            print_t(f"[VLM] Error parsing JSON, returning as text plan")
            return {
                "analysis": response,
                "decision": "text_plan",
                "reasoning": "LLM provided text-based plan",
                "actions": [{"action": "text_plan", "text": response}]
            }

    def verify_object_found(self, image: Image.Image, target_object: str) -> tuple[bool, str]:
        """Verify if the target object is present in the image"""
        scaled_image = self._scale_image(image)
        
        prompt = f"""# OBJECT VERIFICATION
You are analyzing a camera image to verify if a specific object is present.

# OBJECT TO VERIFY
{target_object}

# INSTRUCTIONS
1. Look carefully at the image
2. Determine if {target_object} is present and visible
3. Check for key identifying features
4. Respond with:
   - [YES] if the object is clearly visible and matches key features
   - [NO] if the object is not visible or doesn't match
   - [UNCLEAR] if you cannot determine safely

# OUTPUT FORMAT
Respond with ONLY: [YES], [NO], or [UNCLEAR]"""
        
        try:
            response, _, _ = self._call_llm(prompt, scaled_image, num_visual_tokens=70)
            response_lower = response.strip().lower()
            
            is_found = "[yes]" in response_lower or response_lower.startswith("yes")
            confirmation_msg = f"Verified: {target_object} is visible" if is_found else f"Not verified: {target_object} not confirmed"
            
            return is_found, confirmation_msg
        except Exception as e:
            print_t(f"[verify_object_found] Error: {e}")
            return False, f"Error during verification: {str(e)}"

    def reposition_for_show(self, image: Image.Image, target_object: str) -> bool:
        """Reposition the robot to show the target object to the user"""
        scaled_image = self._scale_image(image)
        
        prompt = f"""# REPOSITIONING FOR DISPLAY
You need to reposition the robot to show the target object to the user.

# TARGET OBJECT
{target_object}

# OBJECT STATUS
- Object is confirmed visible
- You need to reposition for optimal viewing

# REPOSITIONING STRATEGY
1. If object is on left/right: rotate to face it
2. If object is far: move closer (1-2m)
3. If object is blocked: move around obstacle
4. Target object centered in frame, optimal viewing angle

# OUTPUT FORMAT
Return JSON with:
{{
  "analysis": "Current position relative to object",
  "reasoning": "Why this repositioning makes sense",
  "actions": [
    {{"action": "move_forward", "dist": 1.5}},
    {{"action": "rotate", "deg": 45}}
  ]
}}

# EXAMPLE
If object is on the right side:
{{
  "analysis": "Object visible on right side, 2m away",
   "reasoning": "Need to rotate right to face object, move closer for better view",
   "actions": [
     {{"action": "move_forward", "dist": 1.0}},
     {{"action": "rotate", "deg": 90}}
   ]
 }}"""
        
        try:
            system_prompt = "<|think|>\nYou are a precise robot controller that reasons about positioning."
            response, _, _ = self._call_llm(prompt, scaled_image, num_visual_tokens=140, system_prompt=system_prompt)
            
            response_clean = response.strip()
            if response_clean.startswith('```json'):
                response_clean = response_clean[7:]
            if response_clean.startswith('```'):
                response_clean = response_clean[3:]
            if response_clean.endswith('```'):
                response_clean = response_clean[:-3]
            response_clean = response_clean.strip()
            
            plan = json.loads(response_clean)
            
            print_t(f"[reposition_for_show] Plan: {json.dumps(plan, indent=2)}")
            
            for action in plan.get("actions", []):
                action_str = f"[ACTION] {action.get('action')} {action.get('dist', '')} {action.get('deg', '')}".strip()
                self.execute_action(action_str)
                import time
                time.sleep(1.0)
            
            return True
        except Exception as e:
            print_t(f"[reposition_for_show] Error: {e}")
            return False
    def execute_action(self, action_text: str, image: Image.Image = None) -> tuple[bool, bool]:
        import time
        from .skill_item import SkillItem

        action_line = action_text.strip()
        print_t(f"[VLM] Raw action: {action_line}")

        if not action_line:
            return False, False

        # Handle JSON format: {"action": "rotate", "deg": 90}
        if action_line.strip().startswith('{'):
            try:
                action_obj = json.loads(action_line)
                action_body = action_obj.get("action", "")
                deg = action_obj.get("deg", 0)
                dist = action_obj.get("dist", 0)
                
                action_lower = action_body.lower()
                
                if action_lower == "move_forward":
                    self.robot.move_forward(float(dist))
                    return True, False
                elif action_lower == "move_backward":
                    self.robot.move_backward(float(dist))
                    return True, False
                elif action_lower == "move_left":
                    self.robot.move_left(float(dist))
                    return True, False
                elif action_lower == "move_right":
                    self.robot.move_right(float(dist))
                    return True, False
                elif action_lower == "rotate" and deg > 0:
                    self.robot.rotate_right(int(deg))
                    return True, False
                elif action_lower == "rotate" and deg < 0:
                    self.robot.rotate_left(abs(int(deg)))
                    return True, False
                else:
                    print_t(f"[VLM] Unknown action in JSON: {action_lower}")
                    return False, False
            except (json.JSONDecodeError, ValueError, TypeError) as e:
                print_t(f"[VLM] Error parsing JSON action: {e}")
                return False, False

        match = re.match(r'\[ACTION\]\s*(.+)', action_line)
        if match:
            action_body = match.group(1).strip()
        else:
            action_body = action_line

        action_lower = action_body.lower()

        skills = self.robot.skillset.skills

        if 'move forward' in action_lower:
            match = re.search(r'(\d+(?:\.\d+)?)\s*(m|meter|metre)?', action_body)
            dist = float(match.group(1)) if match else 1.0
            self.robot.move_forward(dist)
        elif 'move backward' in action_lower or 'move back' in action_lower:
            match = re.search(r'(\d+(?:\.\d+)?)\s*(m|meter|metre)?', action_body)
            dist = float(match.group(1)) if match else 1.0
            self.robot.move_backward(dist)
        elif 'move left' in action_lower:
            match = re.search(r'(\d+(?:\.\d+)?)\s*(m|meter|metre)?', action_body)
            dist = float(match.group(1)) if match else 1.0
            self.robot.move_left(dist)
        elif 'move right' in action_lower:
            match = re.search(r'(\d+(?:\.\d+)?)\s*(m|meter|metre)?', action_body)
            dist = float(match.group(1)) if match else 1.0
            self.robot.move_right(dist)
        elif 'rotate left' in action_lower or 'turn left' in action_lower:
            match = re.search(r'(\d+)', action_body)
            deg = int(match.group(1)) if match else 45
            self.robot.rotate_left(deg)
        elif 'rotate right' in action_lower or 'turn right' in action_lower:
            match = re.search(r'(\d+)', action_body)
            deg = int(match.group(1)) if match else 45
            self.robot.rotate_right(deg)
        elif 'move up' in action_lower or 'lift' in action_lower:
            match = re.search(r'(\d+(?:\.\d+)?)\s*(m|meter|metre|cm)?', action_body)
            if match:
                val = float(match.group(1))
                unit = match.group(2)
                if unit and 'cm' in unit:
                    dist = val / 100.0
                else:
                    dist = val
            else:
                dist = 1.0
            if hasattr(self.robot, 'lift'):
                self.robot.lift(dist * 100)
            else:
                self.robot.move_forward(dist)
        elif 'move down' in action_lower or 'land' in action_lower:
            print_t("[VLM] Move down command received")
        elif 'stop' in action_lower or 'hover' in action_lower or 'wait' in action_lower:
            time.sleep(2.0)
        elif 'scan for' in action_lower:
            match = re.search(r'([a-zA-Z0-9\s]+?)(?:\bat\b|$)', action_body, re.IGNORECASE)
            object_desc = match.group(1).strip() if match else ""
            if object_desc:
                self.robot.scan_for_object(object_desc)
            else:
                print_t("[VLM] No object description in scan command")
                return False, False
            return True, False
        elif 'scan' in action_lower:
            self.robot.scan_for_object("object")
            return True, False
        elif 'describe' in action_lower or 'observation' in action_lower:
            current_image = self.robot.obs.image
            if current_image:
                scene_description = self.describe_scene_vlm(current_image)
                self.robot.log(scene_description)
            else:
                self.robot.log("I cannot see any image from my camera.")
            return True, False
        elif action_lower.startswith('log '):
            message = action_body[4:]
            self.robot.log(message)
            return True, False
        else:
            print_t(f"[VLM] Unknown action: {action_body}")
            return False, False

        return True, False
