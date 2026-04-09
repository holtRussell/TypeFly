from abc import ABC, abstractmethod
from typing import Any, Optional
from numpy import ndarray
import time, threading
from PIL import Image
import asyncio
import re
import numpy as np

from .skillset import SkillSet
from .robot_info import RobotInfo
from .skill_item import PROBE_RET_TYPE
from .utils import evaluate_value, print_t

from dataclasses import dataclass

@dataclass
class ScanResult:
    found: bool
    location: str
    distance: str
    description: str

class RobotObservation(ABC):
    def __init__(self, robot_info: RobotInfo, rate: int):
        self.interval: float = 1.0 / rate
        self.robot_info = robot_info

        self._image: Optional[Image.Image] = None
        self._depth: Optional[ndarray] = None
        self._orientation: ndarray = np.zeros(3)
        self._position: ndarray = np.zeros(3)

        self.running: bool = False
        self.processing_thread = threading.Thread(target=self.update_observation, daemon=True)
        self._last_update_time: float = 0.0

    def start(self):
        self.running = True
        self._start()
        self.processing_thread.start()

    def stop(self):
        self.running = False
        self.processing_thread.join()
        self._stop()

    @abstractmethod
    def _start(self):
        pass

    @abstractmethod
    def _stop(self):
        pass

    @property
    def image(self) -> Optional[Image.Image]:
        return self._image

    @property
    def depth(self) -> Optional[ndarray]:
        return self._depth

    @property
    def orientation(self) -> Optional[ndarray]:
        return self._orientation
    
    @property
    def position(self) -> Optional[ndarray]:
        return self._position
    
    def update_observation(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def schedule_tasks():
            tasks: set[asyncio.Task] = set()
            
            while self.running:
                start_time = time.time()

                if self._image is not None:
                    task = asyncio.create_task(self.process_image(self._image))
                    tasks.add(task)
                
                tasks = {t for t in tasks if not t.done()}
                self._image_process_result = self.fetch_processed_result()
                elapsed_time = time.time() - start_time
                if self._image is not None:
                    self._last_update_time = time.time()
                await asyncio.sleep(max(0, self.interval - elapsed_time))
        loop.run_until_complete(schedule_tasks())

    @abstractmethod
    async def process_image(self, image: Image.Image):
        pass
    
    @abstractmethod
    def fetch_processed_result(self) -> dict[str, Any]:
        pass
    
    def wait_for_new_frame(self, timeout: float = 2.0) -> Optional[Image.Image]:
        """Wait for a new frame after the current time"""
        import time
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self._image is not None:
                return self._image
            time.sleep(0.1)
        return None

class RobotWrapper(ABC):
    controller_func: list[callable] = []
    def __init__(self, robot_info: RobotInfo, obs: RobotObservation):
        self.robot_info = robot_info
        self.obs = obs
        common_movement_skill_func = [
            (self.move_forward, "Move forward by a dist (m)"),
            (self.move_backward, "Move backward by a dist (m)"),
            (self.move_left, "Move left by a dist (m)"),
            (self.move_right, "Move right by a dist (m)"),
            (self.rotate_left, "Rotate left by a deg (deg)"),
            (self.rotate_right, "Rotate right by a deg (deg)"),
        ]

        other_skills = [
            (self.take_picture, "Take a picture"),
            (self.log, "Print text to user"),
            (self.delay, "Wait for seconds"),
        ]

        high_level_skills = [
            (self.scan_for_object, "Scan for a specific object with description (e.g., 'scan for blue backpack')"),
        ]

        self.skillset: SkillSet = SkillSet.get_common_skillset(common_movement_skill_func + other_skills + high_level_skills)

    @staticmethod
    def set_controller_func(controller_func: list[callable]):
        RobotWrapper.controller_func = controller_func

    @abstractmethod
    def start(self) -> bool:
        pass

    @abstractmethod
    def stop(self) -> bool:
        pass

    @abstractmethod
    def _move(self, dx: float, dy: float):
        pass

    @abstractmethod
    def _rotate(self, deg: float):
        pass

    def move_forward(self, dist: float):
        print_t(f"-> Move forward by {dist} m")
        self._move(dist, 0)
    
    def move_backward(self, dist: float):
        print_t(f"-> Move backward by {dist} m")
        self._move(-dist, 0)
    
    def move_left(self, dist: float):
        print_t(f"-> Move left by {dist} m")
        self._move(0, dist)
    
    def move_right(self, dist: float):
        print_t(f"-> Move right by {dist} m")
        self._move(0, -dist)
    
    def rotate_left(self, deg: float):
        print_t(f"-> Rotate left by {deg} degrees")
        self._rotate(deg)
    
    def rotate_right(self, deg: float):
        print_t(f"-> Rotate right by {deg} degrees")
        self._rotate(-deg)

    def take_picture(self):
        self.controller_func[0](self.obs.image)
    
    def log(self, message: str):
        self.controller_func[0](message)

    def delay(self, sec: float):
        time.sleep(sec)
    
    def probe(self, query: str) -> PROBE_RET_TYPE:
        return evaluate_value(self.controller_func[1](query, self.robot_info))

    def scan_for_object(self, object_description: str) -> ScanResult:
        print(f"-> Scan for: {object_description}")
        
        for i in range(8):
            self.rotate_left(45)
            
            import time
            time.sleep(0.5)
            
            current_image = self.obs.wait_for_new_frame(timeout=1.0)
            if not current_image:
                continue
            
            if self._check_object_in_frame(current_image, object_description):
                location_analysis = self._analyze_location(current_image, object_description)
                self.log(f"Found {object_description}: {location_analysis['description']}")
                return ScanResult(
                    found=True,
                    location=location_analysis.get("location", "center"),
                    distance=location_analysis.get("distance", "unknown"),
                    description=location_analysis.get("description", "")
                )
        
        self.log(f"Did not find: {object_description}")
        return ScanResult(
            found=False,
            location="not visible",
            distance="unknown",
            description="Object not found after 360° scan"
        )
    
    def _analyze_location(self, image: Image.Image, object_desc: str) -> dict:
        prompt = f"""# LOCATION ANALYSIS
Object: {object_desc}

Observe the current frame and determine:
1. Location (left/right/center of frame)
2. Distance estimate (close/medium/far based on apparent size)
3. Brief description of surroundings

Format: location:X distance:Y description:Z"""
        
        try:
            from .llm_wrapper import LLMWrapper, ModelType
            llm = LLMWrapper()
            response = llm.request_multimodal(prompt, image, ModelType.GEMMA4)
            return self._parse_location_response(response)
        except Exception as e:
            print_t(f"[_analyze_location] Error: {e}")
            return {"location": "center", "distance": "unknown", "description": response}
    
    def _parse_location_response(self, response: str) -> dict:
        result = {"location": "center", "distance": "unknown", "description": response}
        
        response_lower = response.lower()
        
        if "location:left" in response_lower or "left" in response_lower:
            result["location"] = "left"
        elif "location:right" in response_lower or "right" in response_lower:
            result["location"] = "right"
        elif "location:center" in response_lower or "center" in response_lower:
            result["location"] = "center"
        
        if "distance:close" in response_lower or "close" in response_lower:
            result["distance"] = "close"
        elif "distance:medium" in response_lower or "medium" in response_lower:
            result["distance"] = "medium"
        elif "distance:far" in response_lower or "far" in response_lower:
            result["distance"] = "far"
        
        return result
    
    def get_obj_list_str(self) -> str:
        """Return string representation of detected objects"""
        if not hasattr(self.obs, '_image_process_result') or not self.obs._image_process_result:
            return "No objects detected"
        
        objects = self.obs._image_process_result.get("objects", [])
        if not objects:
            return "No objects detected"
        
        return "\n".join(str(obj) for obj in objects)

    def _check_object_in_frame(self, image: Image.Image, object_description: str) -> bool:
        prompt = f"""# TASK: OBJECT VERIFICATION
You are analyzing a drone camera image to verify if a specific object is visible.

# OBJECT TO FIND
{object_description}

# INSTRUCTIONS
1. Look carefully at the image
2. Determine if {object_description} is visible
3. Respond with:
   - [YES] if the object is clearly visible
   - [NO] if the object is not visible or not visible
   - [UNCLEAR] if you cannot determine safely

# OUTPUT FORMAT
Respond with ONLY: [YES], [NO], or [UNCLEAR]"""
        
        try:
            from .llm_wrapper import LLMWrapper, ModelType
            llm = LLMWrapper()
            response = llm.request_multimodal(prompt, image, ModelType.GEMMA4)
            response_lower = response.strip().lower()
            
            return "[yes]" in response_lower or response_lower.startswith("yes")
        except Exception as e:
            print_t(f"[_check_object_in_frame] Error: {e}")
            return False
