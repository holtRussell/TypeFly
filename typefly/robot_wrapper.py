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
                await asyncio.sleep(max(0, self.interval - elapsed_time))
        loop.run_until_complete(schedule_tasks())

    @abstractmethod
    async def process_image(self, image: Image.Image):
        pass
    
    @abstractmethod
    def fetch_processed_result(self) -> dict[str, Any]:
        pass

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
            (self.scan, "Scan for a specific object"),
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

    def scan(self, object_name: str) -> bool:
        print(f"-> Scan for {object_name}")
        for _ in range(8):
            self.rotate_left(45)
        return True
