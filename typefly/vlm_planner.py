import os
import re
from typing import Optional
from PIL import Image

from .llm_wrapper import LLMWrapper, ModelType
from .utils import print_t, CURRENT_PROJ_DIR
from .robot_wrapper import RobotWrapper
from .robot_info import RobotInfo
from .skill_item import SkillItem


class VLMPlanner:
    def __init__(self, robot: RobotWrapper, model_type: ModelType = ModelType.GEMMA3):
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
        
        scene_description = self.llm.request_multimodal(prompt, scaled_image, self.model_type)
        return scene_description.strip()

    def plan_action(self, user_instruction: str, scene_description: str, image: Image.Image) -> str:
        scaled_image = self._scale_image(image)
        
        prompt = self.prompt_action_stage2.format(
            robot_skills=str(self.robot.skillset),
            user_instruction=user_instruction,
            scene_context=scene_description
        )
        
        return self.llm.request_multimodal(prompt, scaled_image, self.model_type)

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
        scene_description = self.llm.request_multimodal(prompt, scaled_image, self.model_type)
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

    def execute_action(self, action_text: str) -> bool:
        import time
        from .skill_item import SkillItem

        action_line = action_text.strip()
        print_t(f"[VLM] Raw action: {action_line}")

        if not action_line:
            return False

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
                return False
        elif 'scan' in action_lower:
            self.robot.scan_for_object("object")
        elif 'describe' in action_lower or 'observation' in action_lower:
            current_image = self.robot.obs.image
            if current_image:
                scene_description = self.describe_scene_vlm(current_image)
                self.robot.log(scene_description)
            else:
                self.robot.log("I cannot see any image from my camera.")
        elif action_lower.startswith('log '):
            message = action_body[4:]
            self.robot.log(message)
        else:
            print_t(f"[VLM] Unknown action: {action_body}")
            return False

        return True
