# Redis Quick Reference Guide

## Quick Start

### 1. Start Redis Service
```bash
python main.py --recipe recipes/services/redis.yaml
```

### 2. Check Status
```bash
python main.py --status
```

### 3. Run Benchmark
```bash
# Using service ID
python main.py --recipe recipes/clients/redis_benchmark.yaml --target-service <SERVICE_ID>

# Using direct endpoint
python main.py --recipe recipes/clients/redis_benchmark.yaml --target-endpoint <NODE>:6379
```

### 4. View Results
```bash
# Results are printed in SLURM logs (recommended)
ssh meluxina
cat slurm-<CLIENT_JOB_ID>.out

# Or view JSON file (if saved successfully)
cat /tmp/redis_benchmark_results.json
```

**Note**: All benchmark results are printed to stdout and captured in the SLURM log file, making them easy to view and analyze!

## Common Commands

### Service Management

| Command | Description |
|---------|-------------|
| `python main.py --list-services` | List available service types |
| `python main.py --status` | Show all running services |
| `python main.py --stop-service <ID>` | Stop specific service |
| `python main.py --stop-all-services` | Stop all services |

### Client Management

| Command | Description |
|---------|-------------|
| `python main.py --list-clients` | List available client types |
| `python main.py --recipe <CLIENT_YAML> --target-service <ID>` | Run benchmark |

### Debugging

| Command | Description |
|---------|-------------|
| `python main.py --verbose --recipe <YAML>` | Verbose logging |
| `python main.py --debug-services` | Detailed service info |
| `python main.py --service-endpoint <ID>` | Get service endpoint |

## Configuration Cheat Sheet

### Persistence Modes

```yaml
# No persistence (fastest)
environment:
  REDIS_PERSISTENCE: "none"

# AOF only (best durability)
environment:
  REDIS_PERSISTENCE: "aof"

# RDB only (good balance)
environment:
  REDIS_PERSISTENCE: "rdb"

# Both (maximum safety)
environment:
  REDIS_PERSISTENCE: "both"
```

### Security

```yaml
# Enable password authentication
# Service:
environment:
  REDIS_PASSWORD: "your_password"

# Client:
parameters:
  password: "your_password"
```

### Resource Allocation

```yaml
# Light workload
resources:
  mem: "2GB"
  time: "00:30:00"

# Standard workload
resources:
  mem: "4GB"
  time: "01:00:00"

# Heavy workload
resources:
  mem: "8GB"
  time: "02:00:00"
```

### Benchmark Parameters

```yaml
# Quick test
parameters:
  num_operations: 1000
  value_size: 100
  test_persistence: false

# Standard test
parameters:
  num_operations: 10000
  value_size: 100
  test_persistence: true

# Stress test
parameters:
  num_operations: 100000
  value_size: 1000
  test_persistence: true
```

## Performance Targets

### Typical Performance on MeluXina

| Operation | Small Values (100B) | Medium Values (1KB) | Large Values (10KB) |
|-----------|-------------------|-------------------|-------------------|
| SET ops/s | 15,000-25,000 | 10,000-15,000 | 3,000-5,000 |
| GET ops/s | 20,000-35,000 | 15,000-25,000 | 5,000-10,000 |
| DEL ops/s | 15,000-25,000 | 12,000-18,000 | 4,000-8,000 |

### Latency Expectations

| Category | P99 Latency | Use Case |
|----------|-------------|----------|
| Excellent | < 0.1 ms | Real-time applications |
| Good | 0.1-1 ms | Web caching |
| Acceptable | 1-10 ms | Session storage |
| Poor | > 10 ms | Investigate issues |

## Common Use Cases

### Use Case 1: Cache Performance Testing

**Goal:** Test Redis as a cache layer

**Configuration:**
```yaml
# Service: No persistence needed
environment:
  REDIS_PERSISTENCE: "none"
resources:
  mem: "4GB"

# Client: Many small reads/writes
parameters:
  num_operations: 50000
  value_size: 100
  test_persistence: false
```

**Command:**
```bash
python main.py --recipe recipes/services/redis.yaml
python main.py --recipe recipes/clients/redis_benchmark.yaml --target-service <ID>
```

### Use Case 2: Session Store Testing

**Goal:** Simulate session storage workload

**Configuration:**
```yaml
# Service: RDB for periodic saves
environment:
  REDIS_PERSISTENCE: "rdb"
resources:
  mem: "4GB"

# Client: Medium-sized values
parameters:
  num_operations: 10000
  value_size: 500
  test_persistence: true
```

### Use Case 3: High Durability Testing

**Goal:** Test persistence with maximum safety

**Configuration:**
```yaml
# Service: Both AOF and RDB
environment:
  REDIS_PERSISTENCE: "both"
resources:
  mem: "8GB"

# Client: Test persistence performance
parameters:
  num_operations: 10000
  value_size: 100
  test_persistence: true
```

### Use Case 4: Large Value Storage

**Goal:** Test with large documents/objects

**Configuration:**
```yaml
# Client: Large values
parameters:
  num_operations: 5000
  value_size: 10000  # 10KB
  test_persistence: true
```

## Results Location

### Where to Find Benchmark Results

**Primary Location: SLURM Output (Recommended)**
```bash
ssh meluxina
cat slurm-<CLIENT_JOB_ID>.out
```

The SLURM log contains a formatted summary table like this:
```
================================================================================
BENCHMARK RESULTS SUMMARY
================================================================================

Total Operations: 30000 (SET + GET + DEL)

SET Operations:
  Throughput:       18234.52 ops/sec
  Avg Latency:          0.055 ms
  P95 Latency:          0.087 ms
  P99 Latency:          0.132 ms

GET Operations:
  Throughput:       25678.34 ops/sec
  Cache Hit Rate:      100.0%
  Avg Latency:          0.039 ms
  
... (full detailed output)
```

**Optional Location: JSON File**
```bash
# On the compute node or in ~/results/ directory
cat /tmp/redis_benchmark_results.json
# Or
cat ~/results/redis_benchmark_results.json
```

## Metrics Interpretation

### Understanding the Results

The benchmark outputs both a **formatted summary** (in SLURM logs) and detailed **JSON data**.

### Key Metrics

| Metric | Good Value | Investigation Needed |
|--------|-----------|---------------------|
| SET ops/s | > 10,000 | < 5,000 |
| GET ops/s | > 15,000 | < 7,500 |
| SET P99 latency | < 0.2 ms | > 1 ms |
| GET P99 latency | < 0.15 ms | > 0.5 ms |
| Cache hit rate | > 95% | < 80% |

## Troubleshooting Quick Fixes

### Problem: Connection Timeout

**Quick Fix:**
```bash
# Wait longer for service to start
# In client recipe:
parameters:
  wait_for_service: 120  # Increase from 60
```

### Problem: Out of Memory

**Quick Fix:**
```yaml
# Increase memory allocation
resources:
  mem: "8GB"  # Double current allocation

# Or reduce test size
parameters:
  num_operations: 5000  # Half current value
```

### Problem: Slow Performance

**Quick Fix:**
```yaml
# Disable persistence
environment:
  REDIS_PERSISTENCE: "none"
```

### Problem: Script Not Found

**Quick Fix:**
```bash
# Manually upload script
scp benchmark_scripts/redis_benchmark.py meluxina:~/benchmark_scripts/
```

### Problem: Authentication Error

**Quick Fix:**
```yaml
# Add password to client
parameters:
  password: "your_password"
```

## Advanced Tips

### Tip 1: Run Multiple Benchmarks

```bash
# Test all persistence modes
for mode in none aof rdb both; do
  # Update service recipe with mode
  python main.py --recipe recipes/services/redis_${mode}.yaml
  # Run benchmark
  python main.py --recipe recipes/clients/redis_benchmark.yaml --target-service <ID>
  # Stop service
  python main.py --stop-service <ID>
done
```

### Tip 2: Compare Performance

```bash
# Run baseline without persistence
python main.py --recipe recipes/services/redis.yaml  # mode: none
python main.py --recipe recipes/clients/redis_benchmark.yaml --target-service <ID>

# Run with persistence
python main.py --recipe recipes/services/redis.yaml  # mode: both
python main.py --recipe recipes/clients/redis_benchmark.yaml --target-service <ID>

# Compare results
diff /tmp/redis_benchmark_results_baseline.json /tmp/redis_benchmark_results_persist.json
```

### Tip 3: Test Different Value Sizes

```bash
# Small values (typical cache)
parameters:
  value_size: 50

# Medium values (session data)
parameters:
  value_size: 500

# Large values (documents)
parameters:
  value_size: 5000
```

### Tip 4: Monitor Live Performance

```bash
# SSH to service node
ssh mel2073  # Use actual node

# Watch Redis stats
watch -n 1 'redis-cli INFO stats | grep -E "instantaneous_ops_per_sec|total_commands_processed"'
```

## Environment Variables

### Service Environment

```yaml
environment:
  REDIS_PERSISTENCE: "both"           # Persistence mode
  REDIS_PASSWORD: "secret"            # Optional password
```

### Client Environment

```yaml
environment:
  BENCHMARK_DURATION: "300"           # Total duration
  BENCHMARK_TYPE: "redis"             # Benchmark type
  PYTHONUNBUFFERED: "1"               # Real-time output
```

## File Locations

### On Local Machine

```
team10_EUMASTER4HPC2526_challenge/
├── src/services/redis.py           # Service/Client classes
├── benchmark_scripts/
│   └── redis_benchmark.py          # Benchmark script
├── recipes/
│   ├── services/redis.yaml         # Service recipe
│   └── clients/redis_benchmark.yaml # Client recipe
└── docs/
    ├── REDIS_INTEGRATION_GUIDE.md  # Detailed guide
    └── REDIS_QUICK_REFERENCE.md    # This file
```

### On MeluXina

```
$HOME/
├── containers/
│   └── redis_latest.sif            # Container image
├── redis/
│   ├── data/                       # Redis data directory
│   └── config/
│       └── redis.conf              # Generated config
├── benchmark_scripts/
│   └── redis_benchmark.py          # Uploaded script (auto-uploaded)
├── slurm-<JOB_ID>.out              # SLURM logs (PRIMARY RESULTS LOCATION)
├── results/
│   └── redis_benchmark_results.json # Results copy (if successful)
└── /tmp/
    └── redis_benchmark_results.json # Original results (on compute node)
```

**Where to find results**:
1. **SLURM logs** (`slurm-<JOB_ID>.out`) - Always contains full formatted output ✅
2. **~/results/** directory - Copy of JSON results (if copy succeeded)
3. **/tmp/** on compute node - Original JSON file (temporary)

## Getting Help

### Documentation

- **Integration Guide**: [REDIS_INTEGRATION_GUIDE.md](REDIS_INTEGRATION_GUIDE.md)
- **Main README**: [README.md](../README.md)
- **API Documentation**: [API_DOCUMENTATION.md](API_DOCUMENTATION.md)

### Common Issues

1. **Connection problems**: Check service is RUNNING, not PENDING
2. **Performance issues**: Disable persistence, increase memory
3. **Script errors**: Verify script uploaded to `~/benchmark_scripts/`
4. **Authentication errors**: Ensure password matches in service and client

### Debugging Commands

```bash
# Check service logs
ssh meluxina
tail -f slurm-<SERVICE_JOB_ID>.out

# Check client/benchmark logs (CONTAINS RESULTS)
tail -f slurm-<CLIENT_JOB_ID>.out

# Test Redis manually
ssh <NODE>
redis-cli -h localhost -p 6379 ping

# Check container
apptainer exec $HOME/containers/redis_latest.sif redis-server --version

# View formatted results in SLURM log
cat slurm-<CLIENT_JOB_ID>.out

# Or view JSON results
cat /tmp/redis_benchmark_results.json | python -m json.tool
```

### Quick Tips

1. **Always check SLURM logs first** - They contain all output including errors
2. **Results are in client job logs** - Not the service job logs
3. **Script auto-uploads** - No need to manually upload unless troubleshooting
4. **Boolean flags work** - Use `test_persistence: true` in YAML naturally

---

**For detailed information, see:** [REDIS_INTEGRATION_GUIDE.md](REDIS_INTEGRATION_GUIDE.md)

