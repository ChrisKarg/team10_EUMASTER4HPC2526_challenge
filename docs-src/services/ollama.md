# Ollama Service

Ollama provides high-performance LLM inference with GPU acceleration.

## Overview

| Property | Value |
|----------|-------|
| **Type** | LLM Inference |
| **Default Port** | 11434 |
| **GPU Required** | Yes |
| **Container** | `docker://ollama/ollama:latest` |

## Quick Start

```bash
# Start Ollama service
python main.py --recipe recipes/services/ollama.yaml

# Check status
python main.py --status

# Run benchmark
python main.py --recipe recipes/clients/ollama_benchmark.yaml --target-service ollama_xxx
```

## Recipe Configuration

### Basic Recipe

```yaml
# recipes/services/ollama.yaml
service:
  name: ollama
  description: "Ollama LLM inference server"
  
  container:
    docker_source: docker://ollama/ollama:latest
    image_path: $HOME/containers/ollama_latest.sif
  
  resources:
    nodes: 1
    ntasks: 1
    cpus_per_task: 4
    mem: "32G"
    time: "04:00:00"
    partition: gpu
    qos: default
    gres: "gpu:1"
  
  environment:
    OLLAMA_HOST: "0.0.0.0:11434"
    OLLAMA_MODELS: "$HOME/.ollama/models"
    OLLAMA_NUM_PARALLEL: "4"
  
  ports:
    - 11434
```

### With Monitoring

```yaml
# recipes/services/ollama_with_cadvisor.yaml
service:
  name: ollama
  # ... same as above ...
  
  enable_cadvisor: true
  cadvisor_port: 8080
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OLLAMA_HOST` | Bind address and port | `0.0.0.0:11434` |
| `OLLAMA_MODELS` | Model storage directory | `$HOME/.ollama/models` |
| `OLLAMA_NUM_PARALLEL` | Concurrent requests | `4` |
| `OLLAMA_NUM_GPU` | GPUs to use | All available |
| `OLLAMA_GPU_LAYERS` | Layers to offload to GPU | All |

## Supported Models

Models are pulled automatically on first use:

| Model | Size | Description |
|-------|------|-------------|
| `llama2` | 3.8GB | Meta's Llama 2 |
| `llama2:13b` | 7.4GB | Llama 2 13B |
| `codellama` | 3.8GB | Code-focused Llama |
| `mistral` | 4.1GB | Mistral 7B |
| `qwen2.5:0.5b` | 0.4GB | Qwen 0.5B (fast) |

## API Endpoints

Once running, Ollama exposes:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/generate` | POST | Generate text completion |
| `/api/chat` | POST | Chat completion |
| `/api/tags` | GET | List available models |
| `/api/pull` | POST | Pull a model |
| `/api/embeddings` | POST | Generate embeddings |

### Example: Generate Text

```bash
curl http://mel2073:11434/api/generate -d '{
  "model": "llama2",
  "prompt": "What is machine learning?",
  "stream": false
}'
```

### Example: Chat

```bash
curl http://mel2073:11434/api/chat -d '{
  "model": "llama2",
  "messages": [
    {"role": "user", "content": "Hello!"}
  ]
}'
```

## Benchmark Client

The Ollama benchmark client tests inference performance:

```yaml
# recipes/clients/ollama_benchmark.yaml
client:
  name: ollama_benchmark
  type: ollama_benchmark
  
  parameters:
    model: "llama2"
    num_requests: 50
    concurrent_requests: 5
    prompt_file: "prompts.txt"  # Optional
    output_file: "$HOME/results/ollama_benchmark.json"
  
  resources:
    cpus_per_task: 2
    mem: "4G"
    time: "00:30:00"
    partition: cpu
```

### Benchmark Metrics

| Metric | Description |
|--------|-------------|
| `requests_per_second` | Throughput |
| `tokens_per_second` | Generation speed |
| `latency_mean` | Average response time |
| `latency_p95` | 95th percentile latency |
| `latency_p99` | 99th percentile latency |
| `success_rate` | Percentage of successful requests |

## Multi-GPU Configuration

For larger models or higher throughput:

```yaml
resources:
  gres: "gpu:4"  # Request 4 GPUs

environment:
  OLLAMA_NUM_GPU: "4"
```

## Troubleshooting

### Model Not Loading

```bash
# Check GPU availability
nvidia-smi

# Check Ollama logs
cat slurm-*.out | grep -i error

# Verify model exists
curl http://localhost:11434/api/tags
```

### Out of Memory

- Reduce `OLLAMA_NUM_PARALLEL`
- Use a smaller model
- Request more GPU memory in resources

### Connection Refused

- Verify `OLLAMA_HOST` is set to `0.0.0.0:11434`
- Check firewall/network settings
- Ensure service is in RUNNING state

---

See also: [Services Overview](overview.md) | [Benchmark Examples](../cli/examples.md)
