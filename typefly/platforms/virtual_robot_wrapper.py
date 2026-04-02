import cv2
import time
from typing import Any, Optional
from PIL import Image
import threading
from overrides import overrides

from ..robot_wrapper import RobotWrapper
from ..robot_info import RobotInfo

SKILL_EXECUTION_TIME = 0.2

class VirtualObservation:
    def __init__(self, robot_info: RobotInfo, rate: int = 10):
        self.interval: float = 1.0 / rate
        self.robot_info = robot_info
        self._image: Optional[Image.Image] = None

        if "capture" not in robot_info.extra:
            raise ValueError("Robot info must contain 'capture' key in extra, which is the camera index")

        self.cap = None
        self._cam_thread_running = False
        
        def _capture_spin():
            self.cap = cv2.VideoCapture(int(self.robot_info.extra["capture"]))
            if not self.cap.isOpened():
                raise RuntimeError("Failed to open camera")
            while self._cam_thread_running:
                ret, frame = self.cap.read()
                if ret:
                    self._image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                cv2.waitKey(1)
                time.sleep(0.1)
        self.capture_thread = threading.Thread(target=_capture_spin)
    
    def start(self):
        self._cam_thread_running = True
        self.capture_thread.start()

    def stop(self):
        self._cam_thread_running = False
        self.capture_thread.join()
        if self.cap is not None:
            self.cap.release()
        self.cap = None

    def process_image(self, image: Image.Image):
        pass
    
    def fetch_processed_result(self) -> dict[str, Any]:
        return {}

    @property
    def image(self) -> Optional[Image.Image]:
        return self._image
    
    def wait_for_new_frame(self, timeout: float = 2.0) -> Optional[Image.Image]:
        """Wait for a new frame from the camera stream"""
        import time
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self._image is not None:
                return self._image
            time.sleep(0.1)
        return None

class VirtualRobotWrapper(RobotWrapper):
    def __init__(self, robot_info: RobotInfo):
        super().__init__(robot_info, VirtualObservation(robot_info))

        self.skillset.add_skill(self.lift, "Lift the robot by a certain distance")

    @overrides
    def start(self) -> bool:
        print("-> Starting Virtual Robot...")
        self.obs.start()
        print("-> Camera initialized, waiting for first frame...")
        import time
        while self.obs.image is None:
            time.sleep(0.1)
        print("-> Camera feed ready!")
        return True

    @overrides
    def stop(self) -> bool:
        self.obs.stop()
        return True

    @overrides
    def _move(self, dx: float, dy: float):
        print(f"-> Move by ({dx}, {dy}) cm")
        time.sleep(SKILL_EXECUTION_TIME)

    @overrides
    def _rotate(self, deg: float):
        print(f"-> Rotate by {deg} degrees")
        time.sleep(SKILL_EXECUTION_TIME)

    def lift(self, dist: float):
        print(f"-> Lift for {dist} cm")
        time.sleep(SKILL_EXECUTION_TIME)
