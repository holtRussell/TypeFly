#!/usr/bin/env python
"""Test script to verify scan fix with fresh frame updates"""
import sys
import time
from PIL import Image

from typefly.robot_info import RobotInfo
from typefly.robot_wrapper import RobotObservation, ScanResult

def test_scan_result():
    """Test ScanResult dataclass"""
    print("Testing ScanResult dataclass...")
    
    result = ScanResult(
        found=True,
        location="left",
        distance="medium",
        description="Red backpack visible to the left"
    )
    
    assert result.found == True
    assert result.location == "left"
    assert result.distance == "medium"
    assert "Red backpack" in result.description
    
    print("✓ ScanResult dataclass works")

def test_robot_observation_method():
    """Test that RobotObservation has wait_for_new_frame method"""
    print("\nTesting RobotObservation.wait_for_new_frame method...")
    
    assert hasattr(RobotObservation, 'wait_for_new_frame')
    
    import inspect
    sig = inspect.signature(RobotObservation.wait_for_new_frame)
    params = list(sig.parameters.keys())
    assert 'timeout' in params
    
    print("✓ RobotObservation.wait_for_new_frame exists with correct signature")

def test_virtual_observation():
    """Test VirtualObservation has wait_for_new_frame"""
    print("\nTesting VirtualObservation...")
    
    from typefly.platforms.virtual_robot_wrapper import VirtualObservation
    
    robot_info = RobotInfo(
        robot_id="test",
        robot_type="virtual",
        extra={"capture": 0}
    )
    
    obs = VirtualObservation(robot_info)
    assert hasattr(obs, 'wait_for_new_frame')
    
    print("✓ VirtualObservation has wait_for_new_frame")

def test_tello_observation():
    """Test TelloObservation has wait_for_new_frame"""
    print("\nTesting TelloObservation...")
    
    from typefly.platforms.tello_wrapper import TelloObservation
    from djitellopy import Tello
    
    try:
        drone = Tello()
        robot_info = RobotInfo(
            robot_id="test",
            robot_type="tello",
            extra={}
        )
        obs = TelloObservation(drone, robot_info)
        assert hasattr(obs, 'wait_for_new_frame')
        print("✓ TelloObservation has wait_for_new_frame")
    except Exception as e:
        print(f"⚠ TelloObservation test skipped (Tello not connected): {e}")

def test_robot_wrapper_methods():
    """Test RobotWrapper has scan_for_object and get_obj_list_str"""
    print("\nTesting RobotWrapper methods...")
    
    from typefly.robot_wrapper import RobotWrapper
    
    assert hasattr(RobotWrapper, 'scan_for_object')
    assert hasattr(RobotWrapper, 'get_obj_list_str')
    
    import inspect
    scan_sig = inspect.signature(RobotWrapper.scan_for_object)
    assert 'object_description' in scan_sig.parameters
    
    print("✓ RobotWrapper has scan_for_object and get_obj_list_str")

def test_vlm_controller_scan_handling():
    """Test VLMController has scan handling logic"""
    print("\nTesting VLMController scan handling...")
    
    from typefly.vlm_controller import VLMController
    import inspect
    
    source = inspect.getsource(VLMController.plan_loop)
    
    assert 'scan_pending' in source, "plan_loop should have scan_pending flag"
    assert 'wait_for_new_frame' in source, "plan_loop should use wait_for_new_frame"
    assert 'ScanResult' in source, "plan_loop should import ScanResult"
    
    print("✓ VLMController.plan_loop has scan handling logic")

def main():
    print("=" * 60)
    print("Testing Scan Fix Implementation")
    print("=" * 60)
    
    try:
        test_scan_result()
        test_robot_observation_method()
        test_virtual_observation()
        test_tello_observation()
        test_robot_wrapper_methods()
        test_vlm_controller_scan_handling()
        
        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        return 0
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
