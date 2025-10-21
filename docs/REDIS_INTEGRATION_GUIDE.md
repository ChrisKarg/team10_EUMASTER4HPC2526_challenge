# Redis Integration Guide for HPC Benchmarking Orchestrator

> **Quick Start**: Jump to [Usage Guide](#usage-guide) to get started immediately, or read [Quick Reference](REDIS_QUICK_REFERENCE.md) for common commands.

## 📋 Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Implementation Details](#implementation-details)
4. [Usage Guide](#usage-guide) ⭐ Start here for step-by-step instructions
5. [Configuration Options](#configuration-options)
6. [Benchmark Metrics](#benchmark-metrics)
7. [Troubleshooting](#troubleshooting)
8. [Performance Tuning](#performance-tuning)

## 🎯 What You'll Learn

This comprehensive guide covers:
- ✅ How to deploy Redis on MeluXina HPC
- ✅ How to run Redis benchmarks and interpret results
- ✅ How to configure persistence modes (AOF, RDB, both, none)
- ✅ How to optimize Redis performance for your workload
- ✅ How to troubleshoot common issues

## 🚀 Quick Example

```bash
# 1. Start Redis
python main.py --recipe recipes/services/redis.yaml

# 2. Run benchmark
python main.py --recipe recipes/clients/redis_benchmark.yaml --target-service <JOB_ID>

# 3. View results
ssh meluxina
cat slurm-<CLIENT_JOB_ID>.out
```

**Result**: Formatted performance summary with ops/sec, latency, and memory usage!

## Overview

This guide describes the **Redis service integration** for the HPC Benchmarking Orchestrator on MeluXina. Redis is an in-memory database that supports various data structures and persistence mechanisms, making it ideal for caching, session storage, and real-time analytics workloads.

### What is Redis?

**Redis** (Remote Dictionary Server) is an open-source, in-memory data structure store that can be used as:
- **Database**: Persistent key-value storage with AOF/RDB persistence
- **Cache**: High-performance caching layer (sub-millisecond latency)
- **Message Broker**: Pub/sub messaging patterns
- **Session Store**: Fast session management for web applications

### Why Benchmark Redis on HPC?

- **Performance Testing**: Measure Redis performance on HPC infrastructure
- **Capacity Planning**: Understand throughput limits for your workload
- **Configuration Optimization**: Compare different persistence modes (AOF, RDB, both, none)
- **Network Performance**: Test Redis performance across HPC nodes
- **Use Case Validation**: Verify Redis suitability for your application

### Integration Components

The Redis integration consists of **four main components**:

1. **RedisService** (`src/services/redis.py`): Service class for deploying Redis on HPC
   - Automatic configuration generation
   - Flexible persistence options
   - Health monitoring

2. **RedisClient** (`src/services/redis.py`): Client class for benchmarking Redis
   - Automatic endpoint resolution
   - Boolean flag handling
   - Parameter configuration from YAML

3. **redis_benchmark.py** (`benchmark_scripts/`): Python benchmark script
   - SET/GET/DEL operations testing
   - Latency statistics (mean, median, p95, p99)
   - Memory usage tracking
   - Optional persistence testing
   - Formatted output to SLURM logs

4. **YAML Recipes** (`recipes/`): Configuration files
   - Service recipe: Redis deployment configuration
   - Client recipe: Benchmark parameters and settings

## Architecture

### System Architecture

```
[User] → [CLI] → [Orchestrator] → [ServersModule] → [JobFactory]
                                                          ↓
                                                    [RedisService]
                                                          ↓
                                                   [SLURM Script]
                                                          ↓
                                                   [HPC Cluster]
                                                          ↓
                                              [Apptainer Container]
                                                          ↓
                                                   [Redis Server]
```

### Data Flow

```
Service Deployment:
1. User provides redis.yaml recipe
2. Orchestrator loads and validates recipe
3. JobFactory creates RedisService instance
4. RedisService generates SLURM script with:
   - Container build commands
   - Redis configuration file generation
   - Service startup commands
   - Health check monitoring
5. SSH client submits job to SLURM
6. Container starts Redis with custom config

Client Deployment:
1. User provides redis_benchmark.yaml recipe
2. Orchestrator resolves target service endpoint
3. JobFactory creates RedisClient instance
4. RedisClient generates SLURM script with:
   - Benchmark script upload verification
   - Container execution with redis-py installation
   - Benchmark execution with parameters
5. Benchmark runs and collects metrics
6. Results saved to JSON file
```

### Class Hierarchy

```
Job (Abstract)
├── Service (Abstract)
│   └── RedisService
│       ├── from_recipe() - Create from YAML
│       ├── get_service_setup_commands() - Generate redis.conf
│       ├── get_container_command() - Redis startup
│       └── get_health_check_commands() - Monitor Redis
│
└── Client (Abstract)
    └── RedisClient
        ├── from_recipe() - Create from YAML
        └── resolve_service_endpoint() - Get Redis endpoint
```

## Implementation Details

### RedisService Class

The `RedisService` class extends the base `Service` class and implements Redis-specific functionality.

#### Key Features

1. **Dynamic Configuration Generation**
   - Creates `redis.conf` based on YAML parameters
   - Supports multiple persistence modes (none, AOF, RDB, both)
   - Configurable memory management policies
   - Optional password authentication

2. **Persistence Modes**

   **None (In-Memory Only)**
   ```yaml
   environment:
     REDIS_PERSISTENCE: "none"
   ```
   - No disk writes
   - Fastest performance
   - Data lost on restart

   **AOF (Append-Only File)**
   ```yaml
   environment:
     REDIS_PERSISTENCE: "aof"
   ```
   - Logs every write operation
   - Better durability
   - Fsync every second (configurable)

   **RDB (Snapshots)**
   ```yaml
   environment:
     REDIS_PERSISTENCE: "rdb"
   ```
   - Periodic snapshots
   - Compact on-disk representation
   - Point-in-time recovery

   **Both (AOF + RDB)**
   ```yaml
   environment:
     REDIS_PERSISTENCE: "both"
   ```
   - Maximum durability
   - Combines benefits of both approaches
   - Redis uses AOF for recovery if both exist

3. **Container Configuration**

   The service uses bind mounts for persistence:
   ```bash
   --bind $HOME/redis/data:/redis/data       # Data directory
   --bind $HOME/redis/config:/redis/config   # Configuration files
   ```

#### Implementation Example

```python
class RedisService(Service):
    def get_service_setup_commands(self) -> List[str]:
        # Creates redis.conf with:
        # - Network settings (bind 0.0.0.0, port 6379)
        # - Persistence configuration (AOF/RDB based on env)
        # - Memory management (maxmemory-policy allkeys-lru)
        # - Security (optional password)
        pass
    
    def get_container_command(self) -> str:
        # Returns: apptainer exec --bind ... redis_latest.sif redis-server /redis/config/redis.conf &
        pass
```

### RedisClient Class

The `RedisClient` class extends the base `Client` class for Redis-specific benchmarking.

#### Key Features

1. **Endpoint Resolution**
   - Automatically resolves service hostname from SLURM
   - Formats endpoint as `host:port` for redis-py
   - Supports direct endpoint override

2. **Script Management**
   - Uploads `redis_benchmark.py` to HPC cluster
   - Installs `redis-py` library at runtime
   - Configures benchmark parameters from YAML

#### Implementation Example

```python
class RedisClient(Client):
    def resolve_service_endpoint(self, target_service_host: str = None, 
                               default_port: int = 6379, protocol: str = "redis") -> str:
        # Returns: "hostname:6379" format for redis-py
        host = target_service_host or "${TARGET_SERVICE_HOST}"
        port = self.target_service.get('port', 6379)
        return f"{host}:{port}"
```

### Benchmark Script Architecture

The `redis_benchmark.py` script implements comprehensive performance testing.

#### Benchmark Operations

1. **SET Operations** (Write Performance)
   ```python
   def benchmark_set_operations(num_operations, key_size, value_size):
       # Measures:
       # - Operations per second
       # - Latency distribution (mean, median, p95, p99)
       # - Memory usage after writes
   ```

2. **GET Operations** (Read Performance)
   ```python
   def benchmark_get_operations(num_operations):
       # Measures:
       # - Operations per second
       # - Latency distribution
       # - Cache hit rate
   ```

3. **DEL Operations** (Delete Performance)
   ```python
   def benchmark_del_operations(num_operations):
       # Measures:
       # - Operations per second
       # - Latency distribution
   ```

4. **Persistence Testing** (Optional)
   ```python
   def benchmark_persistence():
       # Tests:
       # - BGSAVE time (RDB snapshot)
       # - BGREWRITEAOF time (AOF compaction)
   ```

#### Metrics Collection and Output

The benchmark provides **two output formats**:

**1. Formatted Summary (in SLURM logs)** - Primary Output ✅
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
  P95 Latency:          0.062 ms
  P99 Latency:          0.095 ms

DEL Operations:
  Throughput:       20123.45 ops/sec
  Avg Latency:          0.050 ms
  P95 Latency:          0.078 ms
  P99 Latency:          0.115 ms

Memory Usage:
  Initial:            856K
  After SET:          1.2M
  Final:              856K
  Peak:               1.5M
================================================================================
```

**2. Detailed JSON Data** - Optional
```json
{
  "endpoint": "mel0182:6379",
  "timestamp": "2025-10-21T10:25:00",
  "configuration": {
    "num_operations": 10000,
    "key_size": 10,
    "value_size": 100,
    "test_persistence": true
  },
  "results": {
    "set": {
      "operation": "SET",
      "num_operations": 10000,
      "operations_per_second": 18234.52,
      "latency_mean_ms": 0.055,
      "latency_median_ms": 0.052,
      "latency_p95_ms": 0.087,
      "latency_p99_ms": 0.132
    },
    "get": { ... },
    "del": { ... },
    "persistence": {
      "operation": "PERSISTENCE",
      "bgsave_time_sec": 0.234,
      "aof_rewrite_time_sec": 0.456
    }
  },
  "memory": {
    "initial": { "used_memory_human": "856K" },
    "final": { "used_memory_human": "856K", "used_memory_peak_human": "1.5M" }
  }
}
```

**Where to Find Results:**
- **SLURM logs**: `slurm-<CLIENT_JOB_ID>.out` - Always contains formatted summary ✅
- **JSON file**: `/tmp/redis_benchmark_results.json` - Detailed data (if saved)
- **Results copy**: `~/results/redis_benchmark_results.json` - Backup copy (if successful)

## Usage Guide

### Quick Start on MeluXina

#### Step 1: Start Redis Service

```bash
# Start Redis with both AOF and RDB persistence
python main.py --recipe recipes/services/redis.yaml
```

**Expected Output:**
```
Service started: abc12345
Monitor the job status through SLURM or check logs.
```

#### Step 2: Check Service Status

```bash
# Check if service is running
python main.py --status
```

**Expected Output:**
```
SLURM Job Status:
  Total Jobs: 1
  Services: 1

Services:
    12345 |  redis_abc12345 |    RUNNING |  0:02:15 | mel2073
```

Note the node name (`mel2073` in this example).

#### Step 3: Run Benchmark

```bash
# Option 1: Using service ID (automatic endpoint resolution)
python main.py --recipe recipes/clients/redis_benchmark.yaml --target-service abc12345

# Option 2: Using direct endpoint
python main.py --recipe recipes/clients/redis_benchmark.yaml --target-endpoint mel2073:6379
```

**Expected Output:**
```
Client started: def67890
Monitor the job status through SLURM or check logs.
```

#### Step 4: Monitor Progress

```bash
# Watch both service and client
python main.py --status
```

**Expected Output:**
```
SLURM Job Status:
  Total Jobs: 2
  Services: 1
  Clients: 1

Services:
    12345 |  redis_abc12345 |    RUNNING |  0:05:30 | mel2073

Clients:
    12346 | redis_bench_def |    RUNNING |  0:01:45 | mel2074
```

#### Step 5: View Results

After the client job completes, check the **SLURM output file** for formatted results.

```bash
# SSH to MeluXina and view results in SLURM logs (RECOMMENDED)
ssh meluxina
cat slurm-<CLIENT_JOB_ID>.out
```

**Example Output** (formatted summary in SLURM logs):
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
  P95 Latency:          0.062 ms
  P99 Latency:          0.095 ms

DEL Operations:
  Throughput:       20123.45 ops/sec
  Avg Latency:          0.050 ms
  P95 Latency:          0.078 ms
  P99 Latency:          0.115 ms

Memory Usage:
  Initial:            856K
  After SET:          1.2M
  Final:              856K
  Peak:               1.5M

Persistence Performance:
  BGSAVE Time:          0.23 sec
  AOF Rewrite:          0.45 sec
================================================================================

Detailed results saved to: /tmp/redis_benchmark_results.json

✓ Benchmark completed successfully!
```

**Optional**: View detailed JSON results
```bash
cat /tmp/redis_benchmark_results.json
# Or check the results directory
cat ~/results/redis_benchmark_results.json
```

### Advanced Usage Examples

#### Example 1: High-Throughput Testing

```yaml
# recipes/clients/redis_benchmark_high_throughput.yaml
client:
  name: redis_benchmark_throughput
  parameters:
    num_operations: 100000  # More operations
    key_size: 10
    value_size: 100
    test_persistence: false  # Skip persistence tests for speed
```

```bash
python main.py --recipe recipes/clients/redis_benchmark_high_throughput.yaml --target-service <SERVICE_ID>
```

#### Example 2: Large Value Testing

```yaml
# recipes/clients/redis_benchmark_large_values.yaml
client:
  name: redis_benchmark_large
  parameters:
    num_operations: 5000
    key_size: 20
    value_size: 10000  # 10KB values
    test_persistence: true
```

```bash
python main.py --recipe recipes/clients/redis_benchmark_large_values.yaml --target-service <SERVICE_ID>
```

#### Example 3: Memory-Only Configuration

```yaml
# recipes/services/redis_memory_only.yaml
service:
  name: redis
  environment:
    REDIS_PERSISTENCE: "none"  # No persistence
  resources:
    mem: "2GB"  # Smaller allocation
```

```bash
python main.py --recipe recipes/services/redis_memory_only.yaml
```

#### Example 4: Secure Redis with Authentication

```yaml
# recipes/services/redis_secure.yaml
service:
  name: redis
  environment:
    REDIS_PERSISTENCE: "both"
    REDIS_PASSWORD: "my_secure_password_123"  # Enable authentication
```

```yaml
# recipes/clients/redis_benchmark_auth.yaml
client:
  name: redis_benchmark
  parameters:
    password: "my_secure_password_123"  # Match service password
    num_operations: 10000
```

### Programmatic Usage

```python
from src.orchestrator import BenchmarkOrchestrator

# Initialize orchestrator
orch = BenchmarkOrchestrator('config.yaml')

# Start Redis service
service_recipe = orch.load_recipe('recipes/services/redis.yaml')
service_id = orch.servers.start_service(service_recipe)

# Wait for service to be ready
import time
for _ in range(12):  # Wait up to 60 seconds
    status = orch.servers.check_service_status(service_id)
    if status['status'] == 'running':
        break
    time.sleep(5)

# Get service host
service_host = orch.servers.get_service_host(service_id)
print(f"Redis running on: {service_host}:6379")

# Start benchmark client
client_recipe = orch.load_recipe('recipes/clients/redis_benchmark.yaml')
client_id = orch.clients.start_client(client_recipe, service_id, service_host)

print(f"Benchmark started: {client_id}")
```

## Configuration Options

### Service Configuration

#### Required Fields

```yaml
service:
  name: redis                    # Service name
  container_image: redis_latest.sif
  container:
    docker_source: "docker://redis:7-alpine"
    image_path: "$HOME/containers/redis_latest.sif"
```

#### Resource Configuration

```yaml
resources:
  time: "01:00:00"              # Job time limit
  partition: cpu                 # SLURM partition
  nodes: 1                       # Number of nodes
  mem: "4GB"                     # Memory allocation
```

**Guidelines:**
- **Memory**: Allocate based on dataset size (2-8GB typical)
- **Time**: 1 hour sufficient for most benchmarks
- **Partition**: Use `cpu` (Redis doesn't need GPU)

#### Persistence Configuration

```yaml
environment:
  REDIS_PERSISTENCE: "both"     # Options: none, aof, rdb, both
  # REDIS_PASSWORD: "password"  # Optional authentication
```

**Persistence Mode Selection:**

| Mode | Use Case | Durability | Performance | Disk Usage |
|------|----------|------------|-------------|------------|
| `none` | Cache, temporary data | None | Fastest | None |
| `aof` | High durability needs | Excellent | Good | High |
| `rdb` | Point-in-time backups | Good | Excellent | Low |
| `both` | Critical data | Maximum | Good | High |

### Client Configuration

#### Required Fields

```yaml
client:
  name: redis_benchmark
  target_service:
    name: redis
    port: 6379
  script:
    name: "redis_benchmark.py"
    local_path: "benchmark_scripts/"
    remote_path: "$HOME/benchmark_scripts/"
```

#### Benchmark Parameters

```yaml
parameters:
  num_operations: 10000          # Operations per test
  key_size: 10                   # Key size in bytes
  value_size: 100                # Value size in bytes
  test_persistence: true         # Test BGSAVE/AOF
  output_file: "/tmp/redis_benchmark_results.json"
  wait_for_service: 60           # Connection timeout
  # password: "password"         # If Redis has auth
```

**Parameter Guidelines:**

- **num_operations**: 
  - Small test: 1,000-5,000
  - Standard: 10,000-50,000
  - Stress test: 100,000+

- **value_size**:
  - Small values: 10-100 bytes (typical cache)
  - Medium values: 1-10 KB (session data)
  - Large values: 10-100 KB (documents)

- **test_persistence**:
  - `true`: Test BGSAVE and AOF rewrite performance
  - `false`: Skip persistence tests for faster benchmarks

## Benchmark Metrics

### Understanding the Results

#### Operations Per Second (OPS)

Measures throughput for each operation type:

```json
{
  "set_ops_per_second": 15234.5,  // Write throughput
  "get_ops_per_second": 23456.7,  // Read throughput
  "del_ops_per_second": 18345.2   // Delete throughput
}
```

**Interpretation:**
- GET is typically 1.5-2x faster than SET
- DEL performance between GET and SET
- Higher is better

**Typical Performance on MeluXina:**
- Small values (100 bytes): 15,000-25,000 SET ops/sec
- Medium values (1 KB): 10,000-15,000 SET ops/sec
- Large values (10 KB): 3,000-5,000 SET ops/sec

#### Latency Statistics

Measures response time distribution:

```json
{
  "latency_stats": {
    "mean": 0.000065,      // Average: 0.065 ms
    "median": 0.000062,    // 50th percentile
    "p95": 0.000098,       // 95th percentile: 0.098 ms
    "p99": 0.000145,       // 99th percentile: 0.145 ms
    "min": 0.000042,       // Best case
    "max": 0.002134        // Worst case
  }
}
```

**Interpretation:**
- **Mean**: Average latency (all requests)
- **Median**: Middle value (less affected by outliers)
- **P95**: 95% of requests faster than this
- **P99**: 99% of requests faster than this
- Lower is better

**Acceptable Latencies:**
- Excellent: < 0.1 ms (P99)
- Good: 0.1-1 ms (P99)
- Acceptable: 1-10 ms (P99)
- Poor: > 10 ms (P99)

#### Memory Usage

Tracks Redis memory consumption:

```json
{
  "initial_memory": {
    "used_memory_human": "1.2MB",
    "used_memory_peak_human": "1.5MB",
    "mem_fragmentation_ratio": 1.12
  }
}
```

**Interpretation:**
- **used_memory**: Current memory usage
- **used_memory_peak**: Maximum memory used
- **mem_fragmentation_ratio**:
  - < 1.0: Memory swapping (bad)
  - 1.0-1.5: Normal (good)
  - > 1.5: High fragmentation (consider restart)

#### Cache Hit Rate

For GET operations:

```json
{
  "cache_hits": 9950,
  "cache_hit_rate": 99.5
}
```

**Interpretation:**
- 100%: All keys found (perfect)
- 90-99%: Good cache performance
- < 90%: Consider cache warming or TTL tuning

#### Persistence Performance

If `test_persistence: true`:

```json
{
  "bgsave_time": 0.234,         // RDB snapshot time in seconds
  "aof_rewrite_time": 0.456     // AOF compaction time in seconds
}
```

**Interpretation:**
- **BGSAVE**: Time to create RDB snapshot
- **AOF Rewrite**: Time to compact AOF file
- Depends on dataset size and disk speed
- Longer times indicate more data or slower I/O

### Performance Comparison

**Example Results Comparison:**

| Configuration | SET ops/s | GET ops/s | P99 Latency |
|---------------|-----------|-----------|-------------|
| No persistence | 25,000 | 35,000 | 0.08 ms |
| AOF only | 18,000 | 33,000 | 0.12 ms |
| RDB only | 24,000 | 34,000 | 0.09 ms |
| Both | 17,000 | 32,000 | 0.13 ms |

## Troubleshooting

### Common Issues

#### Issue 1: Connection Refused

**Symptoms:**
```
Error: Connection refused to mel2073:6379
```

**Causes:**
- Service not yet running
- Wrong hostname or port
- Network connectivity issue

**Solutions:**
```bash
# 1. Check service status
python main.py --status

# 2. Verify service is RUNNING, not PENDING
# 3. Wait 30-60 seconds for Redis to start
# 4. Check SLURM logs for errors
squeue -u $USER
```

#### Issue 2: Container Build Failed

**Symptoms:**
```
Error: Container build failed at $(date)
```

**Causes:**
- Network issues pulling Docker image
- Insufficient disk space
- Apptainer module not loaded

**Solutions:**
```bash
# 1. Check available disk space
df -h $HOME/containers

# 2. Manually build container
ssh meluxina
module add Apptainer
apptainer build $HOME/containers/redis_latest.sif docker://redis:7-alpine

# 3. Update recipe to use existing container
# Set force_rebuild: false in config.yaml
```

#### Issue 3: Authentication Required

**Symptoms:**
```
Error: NOAUTH Authentication required
```

**Causes:**
- Service configured with password
- Client not providing password

**Solutions:**
```yaml
# Update client recipe to include password
parameters:
  password: "your_password_here"
```

#### Issue 4: Out of Memory

**Symptoms:**
```
Error: OOM command not allowed when used memory > 'maxmemory'
```

**Causes:**
- Redis maxmemory limit reached
- Too much data for allocated memory

**Solutions:**
```yaml
# Increase memory allocation in service recipe
resources:
  mem: "8GB"  # Increase from 4GB

# Or reduce test size in client recipe
parameters:
  num_operations: 5000  # Reduce from 10000
  value_size: 50        # Reduce from 100
```

#### Issue 5: Slow Performance

**Symptoms:**
- Very low ops/second
- High P99 latency (> 10 ms)

**Causes:**
- Network latency between nodes
- Disk I/O bottleneck (with persistence)
- CPU contention on shared node

**Solutions:**
```bash
# 1. Check if service and client on same node
python main.py --status  # Note node names

# 2. Disable persistence for faster performance
# In service recipe:
environment:
  REDIS_PERSISTENCE: "none"

# 3. Request dedicated node resources
resources:
  partition: cpu
  exclusive: true  # If supported
```

#### Issue 6: Benchmark Script Not Found

**Symptoms:**
```
ERROR: Benchmark script not found at $HOME/benchmark_scripts/redis_benchmark.py
```

**Causes:**
- Script not uploaded to cluster
- Wrong remote path
- File permissions

**Solutions:**
```bash
# 1. Manually upload script
ssh meluxina
mkdir -p $HOME/benchmark_scripts
exit

scp benchmark_scripts/redis_benchmark.py meluxina:~/benchmark_scripts/

# 2. Verify script exists
ssh meluxina "ls -la ~/benchmark_scripts/redis_benchmark.py"

# 3. Make executable
ssh meluxina "chmod +x ~/benchmark_scripts/redis_benchmark.py"
```

### Debugging Steps

#### 1. Check SLURM Logs (Most Important!)

**Service Logs** (Redis server output):
```bash
# Find job ID
python main.py --status

# View service SLURM output
ssh meluxina
tail -f slurm-<SERVICE_JOB_ID>.out
```

**Client Logs** (Benchmark results and errors):
```bash
# View client/benchmark SLURM output (CONTAINS RESULTS!)
tail -f slurm-<CLIENT_JOB_ID>.out

# Or view completed benchmark
cat slurm-<CLIENT_JOB_ID>.out
```

**💡 Pro Tip**: The client SLURM log contains all benchmark results formatted nicely!

#### 2. Test Manual Connection

```bash
# SSH to service node
ssh mel2073  # Use actual node from: python main.py --status

# Test Redis
redis-cli -h localhost -p 6379 ping
# Expected: PONG

# Check Redis info
redis-cli -h localhost -p 6379 INFO server

# Test SET/GET
redis-cli -h localhost -p 6379 SET testkey "hello"
redis-cli -h localhost -p 6379 GET testkey
# Expected: "hello"
```

#### 3. Check Script Upload

```bash
ssh meluxina
ls -la ~/benchmark_scripts/redis_benchmark.py

# Verify script content
head -20 ~/benchmark_scripts/redis_benchmark.py
```

**Note**: The script is auto-uploaded by the orchestrator. If it exists but fails, delete it and re-run:
```bash
rm ~/benchmark_scripts/redis_benchmark.py
# Then run client again - new version will be uploaded
```

#### 4. Enable Verbose Logging

```bash
python main.py --verbose --recipe recipes/services/redis.yaml
```

#### 5. Check Container

```bash
ssh meluxina
apptainer exec $HOME/containers/redis_latest.sif redis-server --version

# Test container manually
apptainer exec $HOME/containers/redis_latest.sif redis-cli --version
```

#### 6. Common Debugging Workflow

```bash
# 1. Check if jobs are running
python main.py --status

# 2. If service shows RUNNING, check service logs
ssh meluxina
tail -50 slurm-<SERVICE_JOB_ID>.out

# 3. If client completed, check client logs for results
tail -100 slurm-<CLIENT_JOB_ID>.out

# 4. If errors in logs, look for:
#    - "Connection refused" → Service not ready yet (wait 30s)
#    - "Script not found" → Delete old script, re-run
#    - "Authentication required" → Add password parameter
#    - "Out of memory" → Increase mem in recipe or reduce operations
```

## Performance Tuning

### Optimizing for Throughput

**Service Configuration:**
```yaml
environment:
  REDIS_PERSISTENCE: "none"  # Disable persistence
  
resources:
  mem: "8GB"                 # More memory
```

**Client Configuration:**
```yaml
parameters:
  num_operations: 100000     # More operations
  value_size: 100            # Moderate value size
  test_persistence: false    # Skip persistence tests
```

**Expected Improvement:** 1.5-2x throughput increase

### Optimizing for Latency

**Service Configuration:**
```yaml
environment:
  REDIS_PERSISTENCE: "rdb"   # Async snapshots only

resources:
  partition: cpu
  nodes: 1
  cpus_per_task: 4           # More CPU if available
```

**Client Configuration:**
```yaml
parameters:
  num_operations: 10000
  value_size: 50             # Smaller values
```

**Expected Improvement:** 20-40% lower P99 latency

### Optimizing for Durability

**Service Configuration:**
```yaml
environment:
  REDIS_PERSISTENCE: "both"  # AOF + RDB
  
resources:
  mem: "8GB"                 # Extra memory for AOF buffer
```

**Expected Trade-off:** 15-25% throughput reduction, maximum data safety

### Hardware Considerations

**MeluXina CPU Nodes:**
- Fast NVMe storage for persistence
- Low-latency networking
- Shared CPU resources

**Recommendations:**
1. Use `cpu` partition for Redis (no GPU needed)
2. Request sufficient memory (4-8GB typical)
3. Consider dedicated nodes for critical benchmarks
4. Monitor disk I/O if using persistence

### Benchmark Best Practices

1. **Run Multiple Iterations**
   ```bash
   for i in {1..5}; do
     python main.py --recipe recipes/clients/redis_benchmark.yaml --target-service <ID>
   done
   ```

2. **Test Different Value Sizes**
   - Small (10-100 bytes): Cache scenarios
   - Medium (1-10 KB): Session data
   - Large (10-100 KB): Document storage

3. **Baseline Without Persistence**
   - First test with `REDIS_PERSISTENCE: "none"`
   - Then compare with AOF, RDB, both

4. **Monitor System Resources**
   ```bash
   ssh meluxina
   top              # CPU usage
   free -h          # Memory usage
   iostat -x 5      # Disk I/O
   ```

---

## 📚 Summary

You now have everything you need to benchmark Redis on MeluXina:

### ✅ What Works
- **Automatic deployment**: Redis service spins up in containers automatically
- **Automatic endpoint resolution**: No need to manually specify hostnames
- **Formatted output**: Results printed to SLURM logs in readable format
- **Flexible configuration**: 4 persistence modes, configurable parameters
- **Comprehensive metrics**: Throughput, latency distribution, memory usage

### 🎯 Key Takeaways

1. **Results are in SLURM logs** - Always check `slurm-<CLIENT_JOB_ID>.out`
2. **Scripts auto-upload** - Delete old script if updating: `rm ~/benchmark_scripts/redis_benchmark.py`
3. **Boolean flags work naturally** - Use `test_persistence: true` in YAML
4. **Multiple persistence modes** - Test none, AOF, RDB, or both
5. **Fast benchmarks** - ~2-3 minutes for 30K operations

### 📖 Additional Resources

- **Quick Reference**: [REDIS_QUICK_REFERENCE.md](REDIS_QUICK_REFERENCE.md) - Common commands and cheat sheets
- **Main README**: [README.md](../README.md) - General orchestrator usage
- **Other Services**: Ollama (LLM), Chroma (Vector DB), Prometheus (Monitoring)

### 🤝 Getting Help

- Check SLURM logs first (`tail -f slurm-<JOB_ID>.out`)
- Review [Troubleshooting](#troubleshooting) section above
- Check [Common Issues](#common-issues) for quick fixes

**Happy Benchmarking!** 🚀

