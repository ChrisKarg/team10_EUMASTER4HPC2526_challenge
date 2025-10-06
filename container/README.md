# AI Benchmark Container

This folder contains the container definition and benchmark scripts.

## Benchmarks
- `run_inference.py` - Simple CPU benchmark
- `gpu_benchmark.py` - GPU benchmark
- `ollama_benchmark.py` - Placeholder for Ollama integration
- `utils/helpers.py` - Helper functions for timing, logging

## Usage
1. Build container:
   ```bash
   sudo apptainer build ai-benchmark.sif ai-benchmark.def