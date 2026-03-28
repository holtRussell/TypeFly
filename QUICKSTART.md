# Quick Start Guide

## Prerequisites

1. **Python 3.10+**
2. **OLLAMA** installed and running on port 11434

## Installation

```bash
# Create virtual environment
conda create -n typefly python=3.12
conda activate typefly

# Clone and install
git clone https://github.com/typefly/TypeFly.git
cd TypeFly
pip install -e .
```

## Step 1: Start OLLAMA

Make sure OLLAMA is running:

```bash
# Check if OLLAMA is running
curl http://localhost:11434

# Pull Llama3 model if not already pulled
ollama pull llama3:8b
```

## Step 2: Setup Vision System (YOLO)

```bash
# Generate protobuf files
cd typefly/proto && bash generate.sh && cd ../..

# Start YOLO server (separate terminal)
python -m typefly.serving
```

This starts YOLO on port 50050 (gRPC) and gateway on port 50049 (HTTP).

## Step 3: Run TypeFly Web UI

```bash
python -m typefly.webui
```

The web UI will be available at `http://localhost:50000`.

## Quick Test (No Robot)

By default, TypeFly runs in `virtual` mode using your webcam.

This uses your webcam for vision and simulates robot movement.

## Services Overview

| Service | Port | Purpose |
|---------|------|---------|
| OLLAMA | 11434 | LLM (Llama3) |
| YOLO gRPC | 50050 | Object detection |
| TypeFly Gateway | 50049 | HTTP to gRPC bridge |
| Web UI | 50000 | User interface |
