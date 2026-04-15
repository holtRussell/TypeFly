# llama.cpp Setup for TypeFly

## M4 MacBook (Apple Silicon) - Metal Acceleration

This setup uses llama.cpp with Metal GPU acceleration for optimal performance on M4 chip.

## Quick Start

### 1. Download Model

```bash
# Install huggingface-cli if needed
pip install -U huggingface-hub

# Create models directory
mkdir -p models

# Download GGUF model (Q4 quantization ~2.5GB)
huggingface-cli download ggml-org/gemma-4-E2B-it-GGUF gemma-4-E2B-it-Q4_K_M.gguf \
    --local-dir models --local-dir-use-symlinks False

# Download multimodal projector (required for vision)
huggingface-cli download ggml-org/gemma-4-E2B-it-GGUF mmproj-gemma-4-e2b-it-q4_k_m.gguf \
    --local-dir models --local-dir-use-symlinks False
```

Or use the Makefile:
```bash
cd docker
make -f Makefile.llama llama_download
```

### 2. Start llama.cpp Server

```bash
cd docker
make -f Makefile.llama llama_start
```

### 3. Verify

```bash
make -f Makefile.llama llama_test
```

### 4. Run TypeFly

```bash
python -m typefly.webui
```

---

## Available Commands

| Command | Description |
|---------|-------------|
| `make -f Makefile.llama llama_start` | Start llama.cpp server |
| `make -f Makefile.llama llama_stop` | Stop server |
| `make -f Makefile.llama llama_restart` | Restart server |
| `make -f Makefile.llama llama_logs` | View logs |
| `make -f Makefile.llama llama_status` | Check status |
| `make -f Makefile.llama llama_test` | Test API |
| `make -f Makefile.llama llama_download` | Download model |

---

## Environment Variables

Set in `env.llama.list` or shell:
- `LLAMA_SERVER_URL` - Server URL (default: `http://localhost:8080/v1`)
- `LLAMA_SERVER_API_KEY` - API key (default: `token-abc123`)

---

## Model Details

- **Model**: gemma-4-E2B-it (Q4_K_M quantization)
- **Size**: ~2.5GB (compressed from ~5GB)
- **Context**: 8K tokens
- **Features**: Vision (images), Text, Function calling

---

## Troubleshooting

### Metal not working?
Check container logs: `make -f Makefile.llama llama_logs`

### Model not found?
Ensure both `.gguf` and `mmproj-*.gguf` are in `models/` directory.

### Slow inference?
M4 should handle Q4_K_M well. For faster inference, try Q8_0 (4.9GB):
```yaml
# Edit docker-compose.llama.yml, change:
# -m /models/gemma-4-E2B-it-Q8_0.gguf
# --mmproj /models/mmproj-gemma-4-e2b-it-q8_0.gguf
```

---

## Alternative: Native Mac (no Docker)

If you prefer running llama.cpp directly on Mac:

```bash
# Install llama.cpp with Metal
brew install llama.cpp

# Run server
llama-server -m models/gemma-4-E2B-it-Q4_K_M.gguf \
  --mmproj models/mmproj-gemma-4-e2b-it-q4_k_m.gguf \
  -c 8192 --port 8080 --host 0.0.0.0
```