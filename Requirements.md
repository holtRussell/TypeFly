# AI Vision Pipeline Benchmark — Requirements Specification

## 1. Overview

This project benchmarks multiple vision-processing methods on an edge device using the VisDrone dataset. The goal is to evaluate tradeoffs between **latency, resource usage, and scene understanding accuracy**.

### Pipelines to Compare

* YOLO (local inference)
* YOLO via MCP server
* Vision-Language Model (VLM) — direct processing
* Vision-Language Model (VLM) — multi-agent pipeline

### Constraint

All components in the pipeline MUST remain identical except for the **vision-processing method**.

### Controller Model

* Primary model: Gemma4:e4b
* Serving: vLLM instance

---

## 2. System Architecture

### 2.1 Agent-Centric Pipeline (Updated)

```
Input (Image + Prompt)
        ↓
Controller LLM (decision step)
        ↓
Tool Selection / Vision Processing (variable)
        ↓
Intermediate Representation (standardized)
        ↓
Controller LLM (reasoning + response)
        ↓
Structured Output (counts + description)
```

### 2.2 Design Rationale

This simulates a real-world **tool-calling agent**:

* The LLM decides whether to invoke vision tools
* Direct VLM pipelines represent "internal perception"
* Tool-based pipelines represent "external perception"

---

## 3. Functional Requirements

### 3.1 Input Requirements

* Dataset: VisDrone dataset
* Image format: JPG/PNG
* Resolution: Standardized (e.g., 640px max dimension)
* Prompt templates must be identical across pipelines
* Each request MUST pass through Controller LLM first

---

### 3.2 Controller LLM (Updated)

#### Responsibilities

1. Decide whether to call a vision tool
2. Route to appropriate pipeline
3. Process intermediate representation
4. Generate final answers

#### Requirements

* Same model across all pipelines
* Fixed configuration:

  * Temperature: 0–0.2
  * Max tokens: fixed
  * System prompt: identical
* Tool-calling behavior must be deterministic where possible

#### Decision Logging (NEW)

Must log:

* Whether tool was invoked
* Which tool was selected
* Decision latency

---

### 3.3 Vision Processing Module

Each pipeline MUST implement:

```python
process(image) -> vision_output
```

#### Requirements:

* Deterministic (where possible)
* Measurable latency
* Output must be serializable (JSON-compatible)

---

### 3.4 Intermediate Representation Layer

All pipelines MUST normalize outputs into:

```json
{
  "cars": int,
  "pedestrians": int,
  "bicycles": int,
  "raw_description": "string (optional)"
}
```

#### Requirements:

* Missing values must be explicitly set to `null` or `0`
* No free-form outputs beyond defined schema
* Must support parsing from:

  * YOLO detections
  * VLM text outputs

---

### 3.5 Prompt Templates

#### Atomic Queries

```
How many cars are there?
How many pedestrians are there?
How many bicycles are there?
```

#### Composite Query

```
Describe the scene. Include:
- Number of cars
- Number of pedestrians
- Number of bicycles
- One sentence describing the environment
```

#### Requirements:

* Prompts MUST NOT vary across pipelines
* Prompts MUST be version-controlled

---

## 4. Non-Functional Requirements

### 4.1 Detailed Timing (Expanded)

System MUST record granular timing for:

* Controller decision time
* Vision processing time
* LLM atomic query time
* LLM composite query time
* Total pipeline latency

All times must be in milliseconds.

---

### 4.2 Resource Monitoring

System must track:

* CPU usage (%)
* Memory usage (MB)
* GPU usage (%)
* VRAM usage (MB)

---

### 4.3 Caching Requirements (NEW)

System MUST support caching:

#### Vision Output Cache

* Key: (image_id, pipeline)
* Stores: vision_output

#### LLM Output Cache (optional)

* Key: (input_hash)
* Stores: LLM responses

#### Requirements:

* Cache must be toggleable
* Cache hits must be logged

---

### 4.4 Reproducibility

* Fixed random seeds (where applicable)
* Deterministic preprocessing
* Versioned dependencies

---

### 4.5 Scalability

* Must support batch processing

---

## 5. Evaluation Requirements

### 5.1 Ground Truth

* Extract object counts from VisDrone annotations:

  * Cars
  * Pedestrians
  * Bicycles

---

### 5.2 Metrics

#### Counting Accuracy

* Mean Absolute Error (MAE)
* Root Mean Squared Error (RMSE)
* Exact Match Accuracy (%)

#### Consistency

* Atomic vs composite agreement

#### Description Quality

* Correctness (1–5)
* Completeness (1–5)
* Hallucination (1–5)

#### Performance

* Latency (ms)
* Throughput (images/sec)

---

## 6. Logging Requirements

Each run MUST produce structured logs including:

* Decision behavior
* Vision outputs
* Latency breakdown
* Resource usage
* Cache hits

---

## 7. Experiment Design Requirements

### 7.1 Dataset Sampling

* Minimum: 100–200 images
* Include varied scene densities

---

### 7.2 Execution Protocol

For each image:

1. Controller LLM decision
2. Vision processing
3. Normalize output
4. Run atomic queries
5. Run composite query
6. Log everything

---

### 7.3 Repetition

* Run each pipeline multiple times
* Report mean and standard deviation

---

## 8. Analysis Requirements

System must support:

* Accuracy vs latency plots
* Pipeline comparison
* Failure analysis
* Tool usage analysis

---

## 9. Success Criteria

* Clear tradeoffs identified
* Reproducible results
* Insight into agent behavior

---
