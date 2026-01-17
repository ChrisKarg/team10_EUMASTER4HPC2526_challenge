# Redis Service

Redis is an in-memory data structure store, used as a database, cache, and message broker.

## Overview

| Property | Value |
|----------|-------|
| **Type** | In-Memory Database |
| **Default Port** | 6379 |
| **GPU Required** | No |
| **Container** | `docker://redis:latest` |

## Quick Start

```bash
# Start Redis service
python main.py --recipe recipes/services/redis.yaml

# Run benchmark
python main.py --recipe recipes/clients/redis_benchmark.yaml --target-service redis_xxx

# Download results
python main.py --download-results
```

## Recipe Configuration

### Basic Recipe

```yaml
# recipes/services/redis.yaml
service:
  name: redis
  description: "Redis in-memory database"
  
  container:
    docker_source: docker://redis:latest
    image_path: $HOME/containers/redis_latest.sif
  
  resources:
    nodes: 1
    ntasks: 1
    cpus_per_task: 4
    mem: "8G"
    time: "02:00:00"
    partition: cpu
    qos: default
  
  environment:
    REDIS_PORT: "6379"
  
  ports:
    - 6379
```

### With Persistence

```yaml
service:
  name: redis
  
  environment:
    REDIS_PORT: "6379"
    REDIS_APPENDONLY: "yes"
    REDIS_APPENDFSYNC: "everysec"
  
  # Bind data directory for persistence
  bind_mounts:
    - "$HOME/redis/data:/data"
```

### With Monitoring

```yaml
# recipes/services/redis_with_cadvisor.yaml
service:
  name: redis
  enable_cadvisor: true
  cadvisor_port: 8080
  # ... rest of config
```

## Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `maxmemory` | Maximum memory limit | No limit |
| `maxmemory-policy` | Eviction policy | `noeviction` |
| `appendonly` | Enable AOF persistence | `no` |
| `save` | RDB snapshot intervals | Disabled |

## Benchmark Client

### Single-Run Benchmark

```yaml
# recipes/clients/redis_benchmark.yaml
client:
  name: redis_benchmark
  type: redis_benchmark
  
  parameters:
    clients: 50
    requests: 100000
    data_size: 256
    tests: "SET,GET,LPUSH,LPOP,SADD"
    output_file: "$HOME/results/redis_benchmark.json"
```

### Parametric Benchmark

Run comprehensive sweeps across multiple parameters:

```yaml
# recipes/clients/redis_parametric.yaml
client:
  name: redis_parametric
  type: redis_parametric_benchmark
  
  parameters:
    client_counts: [1, 10, 50, 100, 200]
    data_sizes: [64, 256, 1024, 4096]
    pipeline_depths: [1, 10, 50]
    tests: "SET,GET"
```

Run with:

```bash
./scripts/run_redis_parametric.sh
```

### Benchmark Metrics

| Metric | Description |
|--------|-------------|
| `ops_per_second` | Operations per second |
| `latency_avg` | Average latency (ms) |
| `latency_p50` | Median latency |
| `latency_p95` | 95th percentile |
| `latency_p99` | 99th percentile |

## CLI Operations

Connect to Redis via `redis-cli`:

```bash
# Via SSH tunnel
ssh -L 6379:mel0182:6379 -N u103227@login.lxp.lu -p 8822

# Then locally
redis-cli
> SET key "value"
> GET key
> INFO
```

## Performance Tuning

### High Throughput

```yaml
environment:
  REDIS_TCP_BACKLOG: "511"
  REDIS_MAXCLIENTS: "10000"
```

### Memory Optimization

```yaml
environment:
  REDIS_MAXMEMORY: "4gb"
  REDIS_MAXMEMORY_POLICY: "allkeys-lru"
```

## Results Analysis

After running parametric benchmarks, analyze with:

```bash
# Generate plots
python analysis/plot_redis_results.py

# View summary
cat results/redis_parametric_summary.json | jq .
```

Generated plots include:

- Throughput vs. clients
- Latency distribution
- Data size impact
- Pipeline depth analysis

---

See also: [Services Overview](overview.md) | [Parametric Benchmarks](../recipes/clients.md)
