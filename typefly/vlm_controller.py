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

        scan_result: ScanResult = None
        scan_pending = False

        while True:
            if scan_pending:
                print_t("[VLM] Waiting for fresh frame after scan...")
                current_image = self.robot.obs.wait_for_new_frame(timeout=3.0)
                if current_image is None:
                    print_t("[VLM] Timeout waiting for fresh frame, using latest available...")
                    current_image = self.robot.obs.image
                else:
                    print_t(f"[VLM] Got fresh frame: {current_image.size}")
                
                if current_image is not None:
                    scene_desc = self.planner.describe_scene_vlm(current_image)
                    print_t(f"[VLM] Scene (post-scan): {scene_desc}")
                    
                    scene_image_log = self.robot.robot_info.get_scene_image_log()
                    if scene_image_log:
                        buffer = io.BytesIO()
                        current_image.save(buffer, format="JPEG")
                        encoded_img = base64.b64encode(buffer.getvalue()).decode("utf-8")
                        _USER_LOG_QUEUE.put(f'<img src="data:image/jpeg;base64,{encoded_img}" />')
                    
                    _USER_LOG_QUEUE.put(f'[VLM] Scene: {scene_desc}')
                    
                    if scan_result is not None:
                        scan_context = f"\n\n## SCAN RESULTS\nObject found: {scan_result.found}\nLocation: {scan_result.location}\nDistance: {scan_result.distance}\nDescription: {scan_result.description}"
                        scene_desc_with_scan = scene_desc + scan_context
                        _USER_LOG_QUEUE.put(f'[VLM] Scan Results: {str(scan_result)}')
                    else:
                        scene_desc_with_scan = scene_desc
                else:
                    print_t("[VLM] No image available after scan")
                    import time
                    time.sleep(1.0)
                    continue
                
                scan_pending = False
            else:
                current_image = self.robot.obs.image
                if current_image is None:
                    print_t("[VLM] No image available, waiting...")
                    import time
                    time.sleep(0.5)
                    continue

                print_t(f"[VLM] Got image: {current_image.size}")

                scene_desc = self.planner.describe_scene_vlm(current_image)
                print_t(f"[VLM] Scene: {scene_desc}")
                
                scene_image_log = self.robot.robot_info.get_scene_image_log()
                if scene_image_log:
                    buffer = io.BytesIO()
                    current_image.save(buffer, format="JPEG")
                    encoded_img = base64.b64encode(buffer.getvalue()).decode("utf-8")
                    _USER_LOG_QUEUE.put(f'<img src="data:image/jpeg;base64,{encoded_img}" />')
                
                _USER_LOG_QUEUE.put(f'[VLM] Scene: {scene_desc}')

                if scan_result is not None and scan_result.found:
                    scan_context = f"\n\n## SCAN RESULTS\nObject found: {scan_result.found}\nLocation: {scan_result.location}\nDistance: {scan_result.distance}\nDescription: {scan_result.description}"
                    scene_desc_with_scan = scene_desc + scan_context
                else:
                    scene_desc_with_scan = scene_desc

            vlm_output = self.planner.plan_action(user_instruction, scene_desc_with_scan, current_image)
            print_t(f"[VLM] Action: {vlm_output}")
            
            if self.robot.robot_info.get_debug_mode():
                _USER_LOG_QUEUE.put(f'[VLM] Full response: {vlm_output}')
            
            _USER_LOG_QUEUE.put(f'[VLM] Action: {vlm_output}')

            success = self.planner.execute_action(vlm_output)

            if "scan" in vlm_output.lower():
                print_t("[VLM] Scan action detected, gathering results...")
                import re
                match = re.search(r'([a-zA-Z0-9\s]+?)(?:\bat\b|$)', vlm_output, re.IGNORECASE)
                object_desc = match.group(1).strip() if match else ""
                if object_desc:
                    scan_result = self.robot.scan_for_object(object_desc)
                else:
                    scan_result = self.robot.scan_for_object("object")
                scan_pending = True
                print_t(f"[VLM] Scan complete. Found: {scan_result.found}")
            else:
                scan_result = None

            _USER_LOG_QUEUE.put(f'[VLM] Executed: {vlm_output}')

            break

        print_t("[VLM] Plan loop complete")
        _USER_LOG_QUEUE.put('#end')

    def put_instruction(self, user_instruction: str):
        print_t(f"[VLM] Queuing instruction: {user_instruction}")
        self.current_plan_loop_thread = threading.Thread(target=self.plan_loop, args=(user_instruction,), daemon=True)
        self.current_plan_loop_thread.start()
