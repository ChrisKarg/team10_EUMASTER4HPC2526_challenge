# CLI Examples

Practical examples for common workflows.

## Basic Service Operations

### Start a Service

```bash
# Start Ollama LLM service
python main.py --recipe recipes/services/ollama.yaml

# Start with verbose output
python main.py --verbose --recipe recipes/services/ollama.yaml
```

### Check Status

```bash
# Simple status
python main.py --status

# Detailed status
python main.py --verbose --status
```

### Stop Services

```bash
# Stop specific service
python main.py --stop-service ollama_abc123

# Stop all services
python main.py --stop-all-services
```

---

## Running Benchmarks

### Ollama LLM Benchmark

```bash
# 1. Start Ollama service
python main.py --recipe recipes/services/ollama.yaml
# Output: Service started: ollama_abc123

# 2. Check service is running and get node
python main.py --status
# Output: ollama_abc123 | RUNNING | mel2073

# 3. Run benchmark client
python main.py --recipe recipes/clients/ollama_benchmark.yaml --target-service ollama_abc123

# 4. Download results
python main.py --download-results
```

### Redis Benchmark

```bash
# 1. Start Redis
python main.py --recipe recipes/services/redis.yaml

# 2. Run benchmark
python main.py --recipe recipes/clients/redis_benchmark.yaml --target-service redis_xyz789

# 3. Download results
python main.py --download-results
cat results/redis_benchmark_*.json
```

### Chroma Vector DB Benchmark

```bash
# 1. Start Chroma
python main.py --recipe recipes/services/chroma.yaml

# 2. Run benchmark
python main.py --recipe recipes/clients/chroma_benchmark.yaml --target-service chroma_abc123
```

### MySQL Benchmark

```bash
# 1. Start MySQL with monitoring
python main.py --recipe recipes/services/mysql_with_cadvisor.yaml

# 2. Run benchmark
python main.py --recipe recipes/clients/mysql_benchmark.yaml --target-service mysql_def456
```

---

## Monitoring Workflows

### Full Monitoring Stack

```bash
# Start all services with monitoring
./scripts/start_all_services.sh

# Output shows:
#   ✓ Ollama started on mel2073
#   ✓ Redis started on mel0182
#   ✓ Chroma started on mel0058
#   ✓ MySQL started on mel0222
#   ✓ Prometheus started on mel0210
#   ✓ Grafana started on mel0164
#
# SSH Tunnels:
#   Prometheus: ssh -L 9090:mel0210:9090 ...
#   Grafana:    ssh -L 3000:mel0164:3000 ...
```

### Create SSH Tunnels

```bash
# Prometheus tunnel (in one terminal)
ssh -i ~/.ssh/id_ed25519_mlux -L 9090:mel0210:9090 -N u103227@login.lxp.lu -p 8822

# Grafana tunnel (in another terminal)
ssh -i ~/.ssh/id_ed25519_mlux -L 3000:mel0164:3000 -N u103227@login.lxp.lu -p 8822

# Then open in browser:
#   http://localhost:9090 - Prometheus
#   http://localhost:3000 - Grafana (admin/admin)
```

### Query Metrics

```bash
# Get memory usage
python main.py --query-metrics prometheus_abc123 "container_memory_usage_bytes"

# Get CPU usage rate
python main.py --query-metrics prometheus_abc123 "rate(container_cpu_usage_seconds_total[5m])"

# Get network traffic
python main.py --query-metrics prometheus_abc123 "rate(container_network_receive_bytes_total[1m])"
```

---

## Automated Sessions

### Complete Benchmark Session

```bash
# Start service + client + monitoring in one command
python main.py --start-session \
    recipes/services/ollama_with_cadvisor.yaml \
    recipes/clients/ollama_benchmark.yaml \
    recipes/services/prometheus_with_cadvisor.yaml
```

### Service + Monitoring Only

```bash
# Start service with monitoring (no client)
python main.py --start-monitoring \
    recipes/services/redis_with_cadvisor.yaml \
    recipes/services/prometheus_with_cadvisor.yaml
```

---

## Parametric Benchmarks

### Redis Parametric Sweep

```bash
# Run comprehensive Redis benchmark across multiple configurations
./scripts/run_redis_parametric.sh

# This tests:
#   - Client counts: 1, 10, 50, 100
#   - Data sizes: 64B, 256B, 1KB, 4KB
#   - Pipeline depths: 1, 10, 50
```

### Chroma Parametric Sweep

```bash
./scripts/run_chroma_parametric.sh
```

### Ollama Parametric Sweep

```bash
./scripts/run_ollama_parametric.sh
```

---

## Results Management

### Download All Results

```bash
# Download to default ./results/ directory
python main.py --download-results

# Download to custom directory
python main.py --download-results --output-dir ./benchmark-results-2026
```

### View Results

```bash
# List downloaded results
ls -la results/

# View JSON results
cat results/ollama_benchmark_20260115_143022.json | jq .

# View summary
cat results/ollama_benchmark_20260115_143022.json | jq '.summary'
```

---

## Debugging

### Verbose Mode

```bash
# See full SSH and SLURM interaction
python main.py --verbose --recipe recipes/services/ollama.yaml
```

### View Generated Script

```bash
# Scripts are saved in scripts/ directory
ls scripts/
cat scripts/service_ollama_*.sh
```

### Check SLURM Logs

```bash
# SSH to MeluXina
ssh -p 8822 u103227@login.lxp.lu

# View job output
cat slurm-3656789.out
cat slurm-3656789.err
```

---

## Multiple Services

### Start Multiple Services

```bash
# Start services in sequence
python main.py --recipe recipes/services/ollama.yaml
python main.py --recipe recipes/services/redis.yaml
python main.py --recipe recipes/services/chroma.yaml

# Or use automation script
./scripts/start_all_services.sh
```

### Run Multiple Clients

```bash
# After services are running
./scripts/start_all_clients.sh

# Or manually
python main.py --recipe recipes/clients/ollama_benchmark.yaml --target-service ollama_xxx
python main.py --recipe recipes/clients/redis_benchmark.yaml --target-service redis_xxx
```

---

## Error Recovery

### Service Failed to Start

```bash
# Check status for error
python main.py --status

# View SLURM logs
ssh -p 8822 u103227@login.lxp.lu "cat slurm-*.err"

# Try again with verbose
python main.py --verbose --recipe recipes/services/ollama.yaml
```

### Stop Stuck Jobs

```bash
# Stop all services
python main.py --stop-all-services

# Or directly via SLURM
ssh -p 8822 u103227@login.lxp.lu "scancel -u \$USER"
```

### Clean Up

```bash
# Stop everything
python main.py --stop-all-services

# Remove generated scripts
rm -f scripts/service_*.sh scripts/client_*.sh

# Clear local service ID cache
rm -f .service_ids
```

---

## Tips & Best Practices

!!! tip "Always Check Status"
    Run `python main.py --status` before starting new services to avoid resource conflicts.

!!! tip "Use Verbose Mode for Debugging"
    Add `--verbose` when something isn't working to see detailed logs.

!!! tip "Create Tunnels in Background"
    Use `-f` flag for SSH tunnels: `ssh -f -N -L 3000:mel0164:3000 ...`

!!! warning "Resource Limits"
    Be mindful of your SLURM allocation limits. Stop services when not in use.
