from PIL import Image
import queue, io, base64
from typing import Optional, List, Dict, Any
import threading
import json
import builtins
from datetime import datetime

from .llm_wrapper import ModelType, LLMWrapper
from .robot_wrapper import RobotWrapper
from .skill_item import SkillItem
from .utils import print_t
from .robot_info import RobotInfo

_USER_LOG_QUEUE = queue.Queue()

class AgentLoop:
    """
    Agent loop with tool calling support for Ollama.
    Manages message history and tool execution loop.
    """
    
    def __init__(self, robot: RobotWrapper, llm: LLMWrapper, model_type: ModelType = ModelType.GEMMA3):
        self.robot = robot
        self.llm = llm
        self.model_type = model_type
        self.messages: list[dict] = []
        self.context: Optional[list] = None
        self.max_tool_calls = 10
        self._tool_map: dict[str, SkillItem] = {}
        
    def register_tools(self, skillset) -> list[dict]:
        """Register skills as Ollama tools and return tool definitions"""
        tools = []
        for skill_name, skill_item in skillset.skills.items():
            tool_def = skill_item.to_ollama_tool()
            tools.append(tool_def)
            self._tool_map[skill_item.name] = skill_item
        return tools

    def add_message(self, role: str, content: str = "", tool_calls: Optional[list] = None, 
                   tool_name: Optional[str] = None, tool_result: Optional[str] = None):
        """Add a message to the conversation history"""
        message = {"role": role, "content": content}
        
        if tool_calls is not None:
            message["tool_calls"] = tool_calls
            
        if tool_name is not None:
            message["tool_name"] = tool_name
            
        if tool_result is not None:
            message["content"] = tool_result
            
        self.messages.append(message)

    def execute_tool(self, tool_name: str, arguments: dict) -> str:
        """Execute a tool and return the result"""
        if tool_name not in self._tool_map:
            return f"Error: Tool '{tool_name}' not found"
        
        skill = self._tool_map[tool_name]
        
        try:
            result = skill(**arguments)
            return str(result)
        except Exception as e:
            return f"Error executing tool '{tool_name}': {str(e)}"

    def run_agent_turn(self, user_prompt: str, image: Image.Image, tools: Optional[list] = None) -> tuple[str, list]:
        """
        Run one full agent turn (may involve multiple tool calls).
        
        Returns:
            Tuple of (final_response, messages)
        """
        iteration = 0
        
        while iteration < self.max_tool_calls:
            iteration += 1
            
            content, tool_calls, done_reason = self.llm.request_multimodal(
                user_prompt, image, self.model_type, tools
            )
            
            self.add_message("assistant", content, tool_calls if tool_calls else None)
            
            if done_reason == "end_turn" or not tool_calls:
                return content, self.messages
            
            if done_reason == "stop" and tool_calls:
                tool_results = []
                
                for tool_call in tool_calls:
                    if "function" in tool_call:
                        function = tool_call["function"]
                        tool_name = function.get("name", "")
                        tool_args = function.get("arguments", {})
                        
                        if isinstance(tool_args, str):
                            try:
                                tool_args = json.loads(tool_args)
                            except:
                                tool_args = {}
                        
                        print_t(f"  Tool: {tool_name}({json.dumps(tool_args)})")
                        result = self.execute_tool(tool_name, tool_args)
                        
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_call.get("id", f"tool_{iteration}"),
                            "content": str(result)
                        })
                        
                        self.add_message("tool", str(result), tool_name=tool_name)
                
                return content, self.messages
                
            return content, self.messages
        
        print_t(f"[AgentLoop] Max iterations ({self.max_tool_calls}) reached")
        return "I have completed my maximum number of tool calls. Please try again.", self.messages

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
        
        self.llm = LLMWrapper()
        self.planner = None
        self.agent_loop = AgentLoop(self.robot, self.llm, model_type)
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
        if self.planner:
            return self.planner.probe(query, robot_info)
        return ""

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

        self.planner = VLMPlanner(self.robot, self.model_type)

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

            print_t("[VLM] Using VLMPlanner for planning...")
            plan = self.planner.plan_with_reasoning(user_instruction, current_image)

            import json
            _USER_LOG_QUEUE.put(f'[VLM] Analysis: {plan.get("analysis", "N/A")}')
            _USER_LOG_QUEUE.put(f'[VLM] Decision: {plan.get("decision", "N/A")}')
            _USER_LOG_QUEUE.put(f'[VLM] Reasoning: {plan.get("reasoning", "N/A")}')

            if plan.get("decision") == "target_found":
                target_found = True
                self.robot.log(f"I found the target object!")
                break

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

                if action_target_found:
                    target_found = True
                    print_t("[VLM] Target found during action execution!")
                    break

                import time
                time.sleep(1.0)
                current_image = self.robot.obs.wait_for_new_frame(timeout=2.0)
                if current_image is None:
                    current_image = self.robot.obs.image

                if not target_found:
                    found, msg = self.planner.verify_object_found(current_image, "TV")
                    print_t(f"[VLM] Verification: {msg}")
                    
                    if found:
                        _USER_LOG_QUEUE.put(f'[VLM] Repositioning to show target...')
                        self.planner.reposition_for_show(current_image, "TV")
                        
                        target_found = True
                        self.robot.log("Target object found and verified!")
                        break

            if target_found:
                break

            print_t("[VLM] Target not found yet, continuing exploration...")

        if not target_found:
            print_t("[VLM] Max iterations reached, target not found")
            self.robot.log(f"I searched the area but couldn't find the target object.")

        print_t("[VLM] Plan loop complete")
        _USER_LOG_QUEUE.put('#end')

    def put_instruction(self, user_instruction: str):
        print_t(f"[VLM] Queuing instruction: {user_instruction}")
        self.current_plan_loop_thread = threading.Thread(target=self.plan_loop, args=(user_instruction,), daemon=True)
        self.current_plan_loop_thread.start()
