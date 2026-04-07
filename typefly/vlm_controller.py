from PIL import Image
import queue, io, base64
from typing import Optional
import threading
import json
import builtins

from .llm_wrapper import ModelType
from .robot_wrapper import RobotWrapper
from .vlm_planner import VLMPlanner
from .utils import print_t
from .robot_info import RobotInfo

_USER_LOG_QUEUE = queue.Queue()

class VLMController():
    def __init__(self, robot_info: RobotInfo, model_type: ModelType = ModelType.GEMMA3):
        self.controller_func = [
            self._user_log,
            self._probe
        ]
        RobotWrapper.set_controller_func(self.controller_func)

        if robot_info.robot_type == "virtual":
            from .platforms.virtual_robot_wrapper import VirtualRobotWrapper
            self.robot = VirtualRobotWrapper(robot_info)
        elif robot_info.robot_type == "tello":
            from .platforms.tello_wrapper import TelloWrapper
            self.robot = TelloWrapper(robot_info)
        elif robot_info.robot_type == "go2":
            from .platforms.go2_wrapper import Go2Wrapper
            self.robot = Go2Wrapper(robot_info)
        elif robot_info.robot_type == "pod":
            from .platforms.pod_wrapper import PodWrapper
            self.robot = PodWrapper(robot_info)
        self.planner = VLMPlanner(self.robot, model_type)
        self.current_plan_loop_thread = None

    def _user_log(self, msg: str | Image.Image) -> bool:
        if isinstance(msg, Image.Image):
            buffer = io.BytesIO()
            msg.save(buffer, format="JPEG")
            encoded_img = base64.b64encode(buffer.getvalue()).decode("utf-8")
            _USER_LOG_QUEUE.put(f'<img src="data:image/jpeg;base64,{encoded_img}" />')
        else:
            text = str(msg).strip('\'')
            _USER_LOG_QUEUE.put(f'[ROBOT] {text}')
            print_t(f'[ROBOT] {text}')
        return True

    def _probe(self, query: str, robot_info: RobotInfo) -> str:
        return self.planner.probe(query, robot_info)

    def start_controller(self):
        self.robot.start()
        
    def stop_controller(self):
        self.robot.stop()

    def fetch_robot_pov(self) -> Optional[Image.Image]:
        print_t(f"[UI] Fetching robot POV...")
        img = self.robot.obs.image
        print_t(f"[UI] Image size: {img.size if img else None}")
        return img

    def extract_object_context(self, user_instruction: str) -> tuple[str, str]:
        import re
        
        find_pattern = r'(find|look for|search for|locate)\s+([a-zA-Z0-9\s]+?)(?:\b(in|at|near)\b|$)'
        match = re.search(find_pattern, user_instruction.lower())
        
        if match:
            object_desc = match.group(2).strip()
            return object_desc, user_instruction
        
        scan_pattern = r'scan for\s+([a-zA-Z0-9\s]+?)(?:\b(with|that has)\b|$)'
        match = re.search(scan_pattern, user_instruction.lower())
        
        if match:
            object_desc = match.group(1).strip()
            return object_desc, user_instruction
        
        return "", user_instruction

    def plan_loop(self, user_instruction: str):
        from .vlm_planner import VLMPlanner
        from .robot_wrapper import ScanResult

        print_t(f"[VLM] Starting plan loop for: {user_instruction}")

        max_iterations = 10
        iterations = 0
        target_found = False
        target_verification_attempts = 0

        while iterations < max_iterations and not target_found:
            iterations += 1
            print_t(f"[VLM] Iteration {iterations}/{max_iterations}")

            current_image = self.robot.obs.image
            if current_image is None:
                print_t("[VLM] No image available, waiting...")
                import time
                time.sleep(0.5)
                continue

            print_t(f"[VLM] Got image: {current_image.size}")

            # Use reasoning-based planning
            print_t("[VLM] Asking LLM to reason about next steps...")
            plan = self.planner.plan_with_reasoning(user_instruction, current_image)

            # Log the plan
            import json
            _USER_LOG_QUEUE.put(f'[VLM] Analysis: {plan.get("analysis", "N/A")}')
            _USER_LOG_QUEUE.put(f'[VLM] Decision: {plan.get("decision", "N/A")}')
            _USER_LOG_QUEUE.put(f'[VLM] Reasoning: {plan.get("reasoning", "N/A")}')

            # Check for target found decision
            if plan.get("decision") == "target_found":
                target_found = True
                self.robot.log(f"I found the target object!")
                break

            # Execute plan actions
            actions = plan.get("actions", [])
            
            if not actions:
                print_t("[VLM] No actions in plan, continuing...")
                continue

            print_t(f"[VLM] Executing {len(actions)} actions...")
            
            for i, action in enumerate(actions):
                action_text = json.dumps(action)
                success, action_target_found = self.planner.execute_action(action_text, current_image)
                
                if not success:
                    print_t(f"[VLM] Action failed at step {i+1}/{len(actions)}")
                    break

                # Check if target was found during execution
                if action_target_found:
                    target_found = True
                    print_t("[VLM] Target found during action execution!")
                    break

                # Get fresh image after each action
                import time
                time.sleep(1.0)  # Allow time for action to complete
                current_image = self.robot.obs.wait_for_new_frame(timeout=2.0)
                if current_image is None:
                    current_image = self.robot.obs.image

                # Verify target after each major action sequence
                if target_verification_attempts < 3:
                    target_verification_attempts += 1
                    found, msg = self.planner.verify_object_found(current_image, "TV")
                    print_t(f"[VLM] Verification attempt {target_verification_attempts}: {msg}")
                    
                    if found:
                        # Reposition for showing to user
                        _USER_LOG_QUEUE.put(f'[VLM] Repositioning to show target...')
                        self.planner.reposition_for_show(current_image, "TV")
                        
                        target_found = True
                        self.robot.log("Target object found and verified!")
                        break

            if target_found:
                break

            # If we haven't found the target, continue loop for next iteration
            print_t("[VLM] Target not found yet, continues exploration...")

        if not target_found:
            print_t("[VLM] Max iterations reached, target not found")
            self.robot.log(f"I searched the area but couldn't find the target object.")

        print_t("[VLM] Plan loop complete")
        _USER_LOG_QUEUE.put('#end')

    def put_instruction(self, user_instruction: str):
        print_t(f"[VLM] Queuing instruction: {user_instruction}")
        self.current_plan_loop_thread = threading.Thread(target=self.plan_loop, args=(user_instruction,), daemon=True)
        self.current_plan_loop_thread.start()
