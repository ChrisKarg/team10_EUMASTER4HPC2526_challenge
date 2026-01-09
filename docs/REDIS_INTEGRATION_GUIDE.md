# Redis Integration Guide

This guide details the integration of Redis service and benchmarking in the HPC Orchestrator.

## Overview

The Redis integration provides:
1. **Redis Service**: A standalone Redis 7 server running in an Apptainer container.
2. **Redis Benchmark**: A native benchmarking client using the standard `redis-benchmark` tool wrapped in Python for metrics parsing.

## Architecture

```mermaid
graph LR
    subgraph Compute Node
        S[Redis Server (Apptainer)] 
        B[Python Wrapper (Host)] --> |Exec| C[redis-benchmark (Apptainer)]
        C --> |TCP/IP| S
    end
```

- **Server**: Runs `redis-server` inside an Apptainer container.
- **Client**: The `redis_benchmark.py` script runs on the Host OS (using system Python 3). It invokes `apptainer exec redis.sif redis-benchmark ...` to generate load and parses the CSV output.

## Configuration

### Service Recipe (`recipes/services/redis.yaml`)

Configures the Redis server settings.

| Parameter | Description | Default |
|-----------|-------------|---------|
| `REDIS_PERSISTENCE` | Persistence mode (`none`, `rdb`, `aof`, `both`) | `both` |
| `REDIS_PASSWORD` | Optional authentication password | None |
| `resources.mem` | RAM allocation for the job | `4GB` |

### Client Recipe (`recipes/clients/redis_benchmark.yaml`)

Configures the benchmark workload.

| Parameter | Flag | Description | Default |
|-----------|------|-------------|---------|
| `num_operations` | `-n` | Total requests | 100000 |
| `clients` | `-c` | Parallel connections | 50 |
| `value_size` | `-d` | Data payload size (bytes) | 256 |
| `pipeline` | `-P` | Pipelining requests | 1 |
| `native_tests` | `-t` | Comma-separated tests (e.g. `set,get`) | `ping,set,get` |

## Usage

### 1. Start Redis Service
```bash
python main.py --recipe recipes/services/redis.yaml
```

### 2. Run Benchmark
```bash
python main.py --recipe recipes/clients/redis_benchmark.yaml --target-service <JOB_ID>
```

## Parametric Benchmarking

For comprehensive performance analysis, use the **parametric benchmark suite** that automatically sweeps across multiple parameter combinations.

### What is Parametric Benchmarking?

The parametric benchmark runs `redis-benchmark` across a grid of parameters:
- **Client counts**: 1, 10, 50, 100, 200, 500
- **Data sizes**: 64B, 256B, 1KB, 4KB, 16KB, 64KB
- **Pipeline depths**: 1, 4, 16, 64, 256
- **Operations**: SET, GET, LPUSH, LPOP, SADD, HSET, SPOP, ZADD, ZPOPMIN

This generates comprehensive performance data for creating analysis plots like:
- Throughput vs. number of clients
- Throughput vs. data size
- Throughput vs. pipeline depth
- Latency percentiles (P50, P95, P99)
- Operation comparisons
- Performance heatmaps

### Running Parametric Benchmarks

**Option 1: Automated Workflow (Recommended)**

Use the all-in-one helper script:

```bash
./scripts/run_redis_parametric.sh
```

This script:
1. Checks for/starts Redis service
2. Submits the parametric benchmark job
3. Waits for completion (1-4 hours)
4. Downloads results automatically
5. Generates all analysis plots
6. Opens the plots directory

**Option 2: Manual Steps**

```bash
# 1. Start Redis service
python main.py --recipe recipes/services/redis.yaml

# 2. Get service ID
python main.py --list-running-services

# 3. Submit parametric benchmark
python main.py --recipe recipes/clients/redis_parametric.yaml --target-service <SERVICE_ID>

# 4. Wait for completion (monitor with --status)
python main.py --status

# 5. Download results
python main.py --download-results

# 6. Generate plots
python analysis/plot_redis_results.py
```

### Customizing Parameter Ranges

Edit `recipes/clients/redis_parametric.yaml` to customize the sweep:

```yaml
parameters:
  client_counts: "1,50,200"          # Fewer points for faster runs
  data_sizes: "256,1024,4096"        # Focus on specific sizes
  pipeline_depths: "1,16,64"         # Test key pipeline values
  operations_per_test: 50000         # Reduce for faster testing
```

### Analysis Plots

The analysis script generates 6 plots in `analysis/plots/`:

1. **Throughput vs Clients**: Shows how performance scales with concurrent connections
2. **Throughput vs Data Size**: Reveals impact of payload size on performance
3. **Throughput vs Pipeline**: Demonstrates pipelining benefits
4. **Latency vs Clients**: P99 latency under different loads
5. **Performance Heatmap**: 2D visualization of throughput across parameters
6. **Operations Comparison**: Bar chart comparing different Redis operations

### Interpreting Results

**High Throughput Scenarios:**
- Small data sizes (64-256B) with high pipeline depths
- Multiple clients (100-500) to saturate cores
- Simple operations (GET/SET vs. sorted sets)

**Low Latency Scenarios:**
- Low client counts (1-10)
- Pipeline depth of 1 (no batching)
- Monitor P99 latency to catch tail latencies

**Optimal Configuration:**
- Depends on your use case (throughput vs. latency)
- The plots help identify sweet spots for your hardware
- Watch for performance cliffs (e.g., when exceeding CPU capacity)

## Single-Run Benchmarking

For quick tests with specific parameters, use the standard benchmark recipe:

```bash
python main.py --recipe recipes/clients/redis_benchmark.yaml --target-service <SERVICE_ID>
```

## Results

Results are saved as JSON files in `$HOME/results/` on the cluster:

**Single-run results**: `redis_benchmark_{JOB_ID}.json`
**Parametric results**: `redis_parametric_{JOB_ID}.json`

Download to local machine:
```bash
python main.py --download-results
```

Example single-run output structure:
```json
{
  "timestamp": "2023-10-27T10:00:00",
  "config": {
    "endpoint": "redis://node-01:6379",
    "requests": 100000,
    "clients": 50,
    "payload_size": 256
  },
  "results": {
    "tests": {
      "SET": { "requests_per_second": 45000.50 },
      "GET": { "requests_per_second": 48000.20 }
    }
  }
}
```

Example parametric output structure:
```json
{
  "metadata": {
    "endpoint": "redis://node-01:6379",
    "operations_per_test": 100000,
    "tests": ["set", "get", "lpush", ...]
  },
  "parameter_ranges": {
    "clients": [1, 10, 50, 100, 200, 500],
    "data_sizes": [64, 256, 1024, ...],
    "pipeline_depths": [1, 4, 16, 64, 256]
  },
  "results": [
    {
      "parameters": {"clients": 50, "data_size_bytes": 256, "pipeline": 1},
      "tests": {
        "SET": {"requests_per_second": 45000.50, "latency_p99_ms": 2.1},
        "GET": {"requests_per_second": 48000.20, "latency_p99_ms": 1.9}
      }
    },
    ...
  ]
}
```
