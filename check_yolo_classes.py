#!/usr/bin/env python3
"""Script to check YOLO model classes."""

import os
import sys
from ultralytics import YOLO

PROJ_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(PROJ_DIR, "typefly/serving/models/yolov8m.pt")

def main():
    if not os.path.exists(MODEL_PATH):
        print(f"Model not found at: {MODEL_PATH}")
        print("Please download the model first or check the path.")
        return
    
    model = YOLO(MODEL_PATH)
    
    print("YOLO Model Classes:")
    print("-" * 40)
    for class_id, class_name in model.names.items():
        print(f"ID {class_id}: {class_name}")
    print("-" * 40)
    print(f"Total classes: {len(model.names)}")

if __name__ == "__main__":
    main()
