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

## Results

Results are saved as JSON files containing:
- **Configuration**: Client count, payload size, etc.
- **Metrics**: Requests per second for each test type.
- **Raw Output**: Full stdout from the `redis-benchmark` tool.

Example output structure:
```json
{
  "timestamp": "2023-10-27T10:00:00",
  "config": { ... },
  "results": {
    "tests": {
      "SET": { "requests_per_second": 45000.50 },
      "GET": { "requests_per_second": 48000.20 }
    }
  }
}
```
