# Client Recipes

Client recipes define benchmark workloads that run against deployed services.

## Available Client Recipes

| Recipe | Target Service | Type |
|--------|----------------|------|
| `ollama_benchmark.yaml` | Ollama | Single run |
| `ollama_parametric.yaml` | Ollama | Parametric sweep |
| `redis_benchmark.yaml` | Redis | Single run |
| `redis_parametric.yaml` | Redis | Parametric sweep |
| `chroma_benchmark.yaml` | Chroma | Single run |
| `chroma_parametric.yaml` | Chroma | Parametric sweep |
| `mysql_benchmark.yaml` | MySQL | Single run |

## Recipe Fields Reference

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Client identifier |
| `type` | string | Benchmark type (e.g., `ollama_benchmark`) |

### Parameter Fields

| Field | Type | Description |
|-------|------|-------------|
| `parameters.*` | various | Benchmark-specific parameters |
| `parameters.output_file` | string | Results output path |

### Resource Fields

Same as service recipes, but typically lighter:

| Field | Default | Description |
|-------|---------|-------------|
| `cpus_per_task` | 2 | CPUs for benchmark |
| `mem` | "4G" | Memory allocation |
| `time` | "00:30:00" | Time limit |
| `partition` | "cpu" | Usually CPU partition |

## Example: Ollama Benchmark

```yaml
# recipes/clients/ollama_benchmark.yaml
client:
  name: ollama_benchmark
  type: ollama_benchmark
  description: "LLM inference benchmark"
  
  parameters:
    model: "llama2"
    num_requests: 50
    concurrent_requests: 5
    max_tokens: 100
    temperature: 0.7
    output_file: "$HOME/results/ollama_benchmark.json"
  
  resources:
    cpus_per_task: 2
    mem: "4G"
    time: "00:30:00"
    partition: cpu
```

## Example: Redis Benchmark

```yaml
# recipes/clients/redis_benchmark.yaml
client:
  name: redis_benchmark
  type: redis_benchmark
  description: "Redis performance benchmark"
  
  parameters:
    clients: 50
    requests: 100000
    data_size: 256
    pipeline: 1
    tests: "SET,GET,LPUSH,LPOP,SADD,SPOP"
    output_file: "$HOME/results/redis_benchmark.json"
  
  resources:
    cpus_per_task: 4
    mem: "4G"
    time: "00:30:00"
    partition: cpu
```

## Parametric Benchmarks

Parametric recipes test across multiple configurations:

### Redis Parametric

```yaml
# recipes/clients/redis_parametric.yaml
client:
  name: redis_parametric
  type: redis_parametric_benchmark
  description: "Comprehensive Redis performance sweep"
  
  parameters:
    # Parameter ranges to sweep
    client_counts: [1, 10, 50, 100, 200, 500]
    data_sizes: [64, 256, 1024, 4096, 16384, 65536]
    pipeline_depths: [1, 10, 50, 100, 256]
    requests_per_config: 100000
    tests: "SET,GET"
    output_dir: "$HOME/results/redis_parametric/"
  
  resources:
    cpus_per_task: 4
    mem: "8G"
    time: "02:00:00"
    partition: cpu
```

### Ollama Parametric

```yaml
# recipes/clients/ollama_parametric.yaml
client:
  name: ollama_parametric
  type: ollama_parametric_benchmark
  
  parameters:
    models: ["llama2", "mistral", "codellama"]
    concurrent_requests: [1, 2, 4, 8]
    max_tokens: [50, 100, 200]
    num_requests_per_config: 20
    output_dir: "$HOME/results/ollama_parametric/"
```

## Using Client Recipes

### With Target Service ID

```bash
# Start service first
python main.py --recipe recipes/services/ollama.yaml
# Output: Service started: ollama_abc123

# Run client with service ID
python main.py --recipe recipes/clients/ollama_benchmark.yaml --target-service ollama_abc123
```

### With Direct Endpoint

```bash
# If you know the node
python main.py --recipe recipes/clients/ollama_benchmark.yaml --target-endpoint http://mel2073:11434
```

## Running Parametric Sweeps

Use the automation scripts:

```bash
# Redis parametric (tests all combinations)
./scripts/run_redis_parametric.sh

# Ollama parametric
./scripts/run_ollama_parametric.sh

# Chroma parametric
./scripts/run_chroma_parametric.sh
```

## Benchmark Output Format

All benchmarks produce JSON output:

```json
{
  "benchmark": "redis_benchmark",
  "timestamp": "2026-01-15T14:30:22Z",
  "target": "mel0182:6379",
  "config": {
    "clients": 50,
    "requests": 100000,
    "data_size": 256
  },
  "results": {
    "SET": {
      "ops_per_second": 125000,
      "latency_avg_ms": 0.4,
      "latency_p50_ms": 0.35,
      "latency_p95_ms": 0.8,
      "latency_p99_ms": 1.2
    },
    "GET": {
      "ops_per_second": 145000,
      "latency_avg_ms": 0.35,
      "latency_p50_ms": 0.3,
      "latency_p95_ms": 0.7,
      "latency_p99_ms": 1.0
    }
  },
  "summary": {
    "total_operations": 200000,
    "total_duration_seconds": 1.5,
    "success_rate": 100.0
  }
}
```

## Results Analysis

After running benchmarks:

```bash
# Download results
python main.py --download-results

# Analyze with provided scripts
python analysis/plot_redis_results.py
python analysis/plot_ollama_results.py
```

---

Next: [Writing Custom Recipes](custom.md)
