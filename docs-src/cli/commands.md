# CLI Commands Reference

Complete reference for all command-line interface commands.

## Synopsis

```bash
python main.py [OPTIONS]
```

## Global Options

| Option | Description |
|--------|-------------|
| `--help`, `-h` | Show help message and exit |
| `--verbose`, `-v` | Enable verbose logging output |
| `--config CONFIG` | Path to config file (default: `config.yaml`) |

---

## Service Management

### `--recipe RECIPE`

Start a service or client from a YAML recipe file.

```bash
python main.py --recipe recipes/services/ollama.yaml
python main.py --recipe recipes/clients/redis_benchmark.yaml --target-service redis_abc123
```

**Output:**
```
Service started: ollama_a1b2c3d4
Monitor the job status through SLURM or check logs.

  To check status:
    python main.py --status
```

---

### `--target-service SERVICE_ID`

Specify the target service for a client recipe. The orchestrator resolves the service's node and port automatically.

```bash
python main.py --recipe recipes/clients/ollama_benchmark.yaml --target-service ollama_abc123
```

---

### `--target-endpoint URL`

Specify the target endpoint directly (alternative to `--target-service`).

```bash
python main.py --recipe recipes/clients/ollama_benchmark.yaml --target-endpoint http://mel2073:11434
```

---

### `--stop-service SERVICE_ID`

Stop a specific running service by its ID or SLURM job ID.

```bash
python main.py --stop-service ollama_abc123
python main.py --stop-service 3656789
```

**Output:**
```
Successfully cancelled SLURM job: 3656789
Service ollama_abc123 stopped.
```

---

### `--stop-all-services`

Stop all running services at once.

```bash
python main.py --stop-all-services
```

**Output:**
```
Stopping all running services...
✅ Stopped 4/4 services
```

---

## Status & Information

### `--status`

Show status of all running SLURM jobs (services and clients).

```bash
python main.py --status
```

**Output:**
```
SLURM Job Status:
  Total Jobs: 3
  Services: 2
  Clients: 1
  Other: 0

Services:
  JOB_ID  | SERVICE_ID        | STATUS  | RUNTIME  | NODE
  3656789 | ollama_a1b2c3d4   | RUNNING | 0:15:30  | mel2073
  3656790 | redis_e5f6g7h8    | RUNNING | 0:10:15  | mel0182

Clients:
  JOB_ID  | CLIENT_ID              | STATUS  | RUNTIME  | NODE
  3656791 | ollama_bench_i9j0k1l2  | RUNNING | 0:05:45  | mel2074
```

---

### `--list-services`

List all available service types.

```bash
python main.py --list-services
```

**Output:**
```
Available Services:
  - ollama          LLM inference server
  - redis           In-memory database
  - chroma          Vector database
  - mysql           Relational database
  - prometheus      Metrics collection
  - grafana         Visualization dashboard
```

---

### `--list-clients`

List all available client/benchmark types.

```bash
python main.py --list-clients
```

**Output:**
```
Available Clients:
  - ollama_benchmark      LLM inference benchmark
  - redis_benchmark       Redis performance test
  - chroma_benchmark      Vector DB benchmark
  - mysql_benchmark       MySQL CRUD benchmark
```

---

### `--list-running-services`

List currently running services with their endpoints.

```bash
python main.py --list-running-services
```

**Output:**
```
Running Services:
  SERVICE_ID        | JOB_ID  | NODE     | ENDPOINT
  ollama_a1b2c3d4   | 3656789 | mel2073  | http://mel2073:11434
  redis_e5f6g7h8    | 3656790 | mel0182  | redis://mel0182:6379
```

---

## Sessions & Automation

### `--start-session SERVICE_RECIPE CLIENT_RECIPE [MONITOR_RECIPE]`

Start a complete benchmark session with service, client, and optional monitoring.

```bash
python main.py --start-session \
    recipes/services/ollama_with_cadvisor.yaml \
    recipes/clients/ollama_benchmark.yaml \
    recipes/services/prometheus_with_cadvisor.yaml
```

**Output:**
```
Starting benchmark session...
  ✓ Service started: ollama_abc123
  ✓ Waiting for service to be ready...
  ✓ Client started: ollama_bench_def456
  ✓ Prometheus started: prometheus_ghi789

Session ID: session_20260115_143022
Monitor at: http://mel0XXX:9090 (create tunnel first)
```

---

### `--start-monitoring SERVICE_RECIPE PROMETHEUS_RECIPE`

Start a service with monitoring (without client).

```bash
python main.py --start-monitoring \
    recipes/services/ollama_with_cadvisor.yaml \
    recipes/services/prometheus_with_cadvisor.yaml
```

---

### `--stop-session SESSION_ID`

Stop all jobs in a benchmark session.

```bash
python main.py --stop-session session_20260115_143022
```

---

## Monitoring & Metrics

### `--query-metrics PROMETHEUS_ID QUERY`

Query Prometheus metrics using PromQL.

```bash
python main.py --query-metrics prometheus_abc123 "container_memory_usage_bytes"
python main.py --query-metrics prometheus_abc123 "rate(container_cpu_usage_seconds_total[5m])"
```

**Output:**
```
Query: container_memory_usage_bytes
Results:
  {name="ollama"}: 4294967296 (4.0 GB)
  {name="redis"}: 134217728 (128 MB)
```

---

### `--create-tunnel SERVICE_ID LOCAL_PORT REMOTE_PORT`

Generate SSH tunnel command for accessing a service.

```bash
python main.py --create-tunnel prometheus_abc123 9090 9090
```

**Output:**
```
SSH Tunnel Command:
  ssh -i ~/.ssh/id_ed25519_mlux -L 9090:mel0182:9090 -N u103227@login.lxp.lu -p 8822

Then access: http://localhost:9090
```

---

## Results & Data

### `--download-results`

Download benchmark results from the HPC cluster to local machine.

```bash
python main.py --download-results
```

**Output:**
```
Downloading results from MeluXina...
  ✓ Downloaded: ollama_benchmark_20260115_143022.json
  ✓ Downloaded: redis_benchmark_20260115_150000.json

Results saved to: ./results/
```

---

### `--download-results --output-dir PATH`

Download results to a specific directory.

```bash
python main.py --download-results --output-dir ./my-results
```

---

## Interactive Mode

### No arguments

Run the orchestrator in interactive mode.

```bash
python main.py
```

**Output:**
```
HPC AI Benchmarking Orchestrator
================================

Commands:
  status      - Show running jobs
  start       - Start a service or client
  stop        - Stop a service
  list        - List available services/clients
  quit        - Exit

> status
```

---

## Verbose Mode

Add `--verbose` to any command for detailed output:

```bash
python main.py --verbose --recipe recipes/services/ollama.yaml
```

**Output includes:**

- SSH connection details
- Generated SLURM script content
- SLURM submission output
- Service host resolution steps

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Configuration error |
| 3 | SSH connection failed |
| 4 | SLURM submission failed |
| 5 | Service not found |

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `HPC_CONFIG` | Path to config file (alternative to `--config`) |
| `HPC_VERBOSE` | Set to `1` for verbose mode |
| `SSH_AUTH_SOCK` | SSH agent socket (for key forwarding) |

---

## Examples

See [CLI Examples](examples.md) for common usage patterns.
