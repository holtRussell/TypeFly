import json
from typing import Optional

class RobotInfo:
    """
    Information about a robot, including its ID, type, and any extra parameters.
    """
    def __init__(self, robot_id: str, robot_type: str, extra: Optional[dict] = None):
        self.robot_id = robot_id
        self.robot_type = robot_type
        self.extra = extra
    
    def __hash__(self) -> int:
        return hash(self.robot_id)

    def __eq__(self, other) -> bool:
        if not isinstance(other, RobotInfo):
            return False
        return self.robot_id == other.robot_id
    
    def to_dict(self) -> dict:
        info = {
            "robot_id": self.robot_id,
            "robot_type": self.robot_type
        }
        if self.extra:
            info["extra"] = self.extra
        return info

    def to_json(self) -> str:
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: dict) -> 'RobotInfo':
        extra = data.get("extra", {})
        if extra is None:
            extra = {}
        return cls(data["robot_id"], data["robot_type"], extra)
    
    def get_yolo_enabled(self) -> bool:
        return self.extra.get("yolo_enabled", False) if self.extra else False
    
    def get_scene_image_log(self) -> bool:
        return self.extra.get("scene_image_log", False) if self.extra else False
    
    def get_debug_mode(self) -> bool:
        return self.extra.get("debug_mode", False) if self.extra else False