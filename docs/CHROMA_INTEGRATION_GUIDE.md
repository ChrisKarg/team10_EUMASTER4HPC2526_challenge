# Chroma Vector Database Integration Guide

This guide explains how to use the Chroma vector database service and client in the HPC Orchestrator.

## Table of Contents
- [Overview](#overview)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Workflow](#workflow)
- [Configuration](#configuration)
- [Benchmark Operations](#benchmark-operations)
- [Troubleshooting](#troubleshooting)

## Overview

Chroma is an open-source vector database designed for AI applications. This integration allows you to:
- Deploy Chroma as a service on HPC nodes
- Run benchmarks to test vector database performance
- Measure insertion throughput and query latency
- Test similarity search with configurable parameters

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    HPC Orchestrator                      │
│                                                          │
│  ┌──────────────────┐         ┌─────────────────────┐  │
│  │  Chroma Service  │◄────────┤  Chroma Client      │  │
│  │  (Vector DB)     │         │  (Benchmark)        │  │
│  │  Port: 8000      │         │                     │  │
│  │  Node: mel2198   │         │  Node: mel2102      │  │
│  └──────────────────┘         └─────────────────────┘  │
│         │                              │                │
│         │ SLURM Job 1                  │ SLURM Job 2    │
│         │                              │                │
└─────────┼──────────────────────────────┼────────────────┘
          │                              │
          └──────────────────────────────┘
           HTTP Communication (port 8000)
```

## Quick Start

### 1. Start Chroma Service

```bash
# From your local machine (with venv activated)
python main.py --recipe recipes/services/chroma.yaml
```

**Expected Output:**
```
2025-10-16 10:00:00 - INFO - Starting HPC Orchestrator
2025-10-16 10:00:01 - INFO - Connected to login.lxp.lu
2025-10-16 10:00:02 - INFO - Loaded recipe from recipes/services/chroma.yaml
2025-10-16 10:00:03 - INFO - Service started: abc123def
2025-10-16 10:00:03 - INFO - Submitted SLURM job: 3646900

Benchmark session started: session_1
Monitor the job status through SLURM or check logs.
```

### 2. Check Service Status

```bash
python main.py --status
```

**Expected Output:**
```
SLURM Job Status:
  Total Jobs: 1
  Services: 1
  Clients: 0

Services:
   3646900 | chroma_abc123def | RUNNING | 0:45 | mel2198
```

**Note the hostname (mel2198)** - you'll need this for the client!

### 3. Start Benchmark Client

```bash
# Use the hostname from the status command
python main.py --recipe recipes/clients/chroma_benchmark.yaml --target-endpoint http://mel2198
```

**Expected Output:**
```
2025-10-16 10:05:00 - INFO - Starting HPC Orchestrator
2025-10-16 10:05:01 - INFO - Loaded recipe from recipes/clients/chroma_benchmark.yaml
2025-10-16 10:05:02 - INFO - Client started: xyz789abc
2025-10-16 10:05:02 - INFO - Submitted SLURM job: 3646901

Client started: xyz789abc
Monitor the job status through SLURM or check logs.
```

### 4. Monitor Progress

```bash
# Check status periodically
python main.py --status

# Or check on the HPC cluster directly
ssh login.lxp.lu
squeue -u $USER
tail -f slurm-3646901.out  # Client job output
```

### 5. Retrieve Results

Once the client job completes:

```bash
# SSH to the cluster
ssh login.lxp.lu

# Find your client job
sacct -u $USER --format=JobID,JobName,State,ExitCode -S today | grep chroma_benchmark

# View the results from the SLURM output log
tail -100 slurm-<job_id>.out
```

**Note:** Results are printed in the job log. The JSON file is saved on the compute node's `/tmp` directory and may not be directly accessible from the login node.

## Workflow

### Complete Workflow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: Deploy Chroma Service                               │
│ Command: python main.py --recipe recipes/services/chroma.yaml│
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ Orchestrator Actions:                                        │
│ 1. Read chroma.yaml recipe                                   │
│ 2. Generate SLURM batch script                               │
│ 3. Upload script to HPC cluster                              │
│ 4. Submit job to SLURM scheduler                             │
│ 5. Return job ID and service ID                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ SLURM Scheduler:                                             │
│ 1. Allocate resources (CPU node, 8GB memory)                │
│ 2. Assign compute node (e.g., mel2198)                       │
│ 3. Start Chroma container                                    │
│ 4. Chroma listens on 0.0.0.0:8000                            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 2: Check Service Status                                │
│ Command: python main.py --status                             │
│ Result: Get hostname (mel2198) and verify RUNNING           │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 3: Deploy Benchmark Client                             │
│ Command: python main.py --recipe recipes/clients/            │
│          chroma_benchmark.yaml --target-endpoint             │
│          http://mel2198                                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ Orchestrator Actions:                                        │
│ 1. Read chroma_benchmark.yaml recipe                         │
│ 2. Resolve service endpoint: http://mel2198:8000            │
│ 3. Upload benchmark script to cluster                        │
│ 4. Generate client SLURM script                              │
│ 5. Submit client job to SLURM                                │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ Client Execution:                                            │
│ 1. Wait for Chroma service (health check)                   │
│ 2. Connect to http://mel2198:8000                            │
│ 3. Create benchmark collection                               │
│ 4. Insert documents with embeddings                          │
│ 5. Perform similarity search queries                         │
│ 6. Collect performance metrics                               │
│ 7. Save results to /tmp/chroma_benchmark_results.json       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 4: Retrieve Results                                     │
│ Method 1: View SLURM logs (RECOMMENDED)                      │
│ Command: ssh login.lxp.lu                                    │
│          tail -100 slurm-<job_id>.out                        │
│                                                              │
│ Method 2: Access compute node (ADVANCED, restricted)        │
│ The JSON file is at /tmp/chroma_benchmark_results.json      │
│ on the compute node where the job ran                       │
└─────────────────────────────────────────────────────────────┘
```

### Detailed Step-by-Step

#### Step 1: Deploy Service
```bash
python main.py --recipe recipes/services/chroma.yaml
```
- Creates SLURM job with Chroma container
- Allocates resources: 1 CPU node, 8GB RAM
- Starts Chroma on port 8000
- Returns service ID and job ID

#### Step 2: Verify Service is Running
```bash
python main.py --status
```
- Lists all active SLURM jobs
- Shows service status (PENDING → RUNNING)
- Displays hostname where service is running
- **Important**: Note the hostname (e.g., mel2198)

#### Step 3: Deploy Client
```bash
python main.py --recipe recipes/clients/chroma_benchmark.yaml \
  --target-endpoint http://mel2198
```
- Uploads benchmark script to cluster
- Creates client SLURM job
- Configures endpoint to connect to service
- Starts benchmark execution

#### Step 4: Monitor Execution
```bash
# Option 1: Via orchestrator
python main.py --status

# Option 2: Direct SLURM
ssh login.lxp.lu
squeue -u $USER
sacct -j <job_id> --format=JobID,JobName,State,ExitCode

# Option 3: View logs in real-time
ssh login.lxp.lu
tail -f slurm-<job_id>.out
```

#### Step 5: Retrieve Results

**Primary Method: View SLURM Logs**

The benchmark results are printed at the end of the SLURM job output log:

```bash
ssh login.lxp.lu

# Step 1: Find your completed job ID
sacct -u $USER --format=JobID,JobName,State -S today | grep chroma_be+

# Step 2: View job status and logs (replace <job_id> with actual job ID)
sacct -j <job_id> --format=JobID,JobName,State,ExitCode,Elapsed && echo '---LOGS---' && tail -80 slurm-<job_id>.out
```

**Example with actual job ID:**
```bash
# If your job ID is 3649933:
sacct -j 3649933 --format=JobID,JobName,State,ExitCode,Elapsed && echo '---LOGS---' && tail -80 slurm-3649933.out
```

The output will show:
```json
================================================================================
BENCHMARK SUMMARY
================================================================================
{
  "total_documents_inserted": 1000,
  "insertion_throughput": 252.19,
  "total_queries_executed": 100,
  "query_throughput": 190.51,
  "avg_query_latency_ms": 5.25,
  "p95_query_latency_ms": 5.36,
  "p99_query_latency_ms": 6.13
}
================================================================================
```

**Note about JSON File:** The results are also saved to `/tmp/chroma_benchmark_results.json` on the compute node where the job runs. However, direct access to compute nodes is typically restricted for security reasons. The SLURM log method is the recommended way to retrieve results.

## Configuration

### Service Configuration (`recipes/services/chroma.yaml`)

```yaml
service:
  name: chroma
  container_image: chroma_latest.sif
  command: chroma
  args: ["run", "--host", "0.0.0.0", "--port", "8000"]
  
  container:
    docker_source: "docker://chromadb/chroma:latest"
    image_path: "$HOME/containers/chroma_latest.sif"
  
  resources:
    time: "01:00:00"      # Runtime limit
    partition: cpu         # CPU partition (no GPU needed)
    nodes: 1
    mem: "8GB"            # Memory allocation
  
  environment:
    CHROMA_HOST: "0.0.0.0"
    CHROMA_PORT: "8000"
    IS_PERSISTENT: "true"
    PERSIST_DIRECTORY: "/chroma/data"
  
  ports:
    - 8000
  
  health_check:
    endpoint: "http://localhost:8000/api/v1/heartbeat"
    timeout: 30
```

**Key Parameters:**
- `partition: cpu` - Chroma doesn't require GPU
- `mem: "8GB"` - Adjust based on dataset size
- `time` - Maximum runtime (extend for large workloads)
- `IS_PERSISTENT: "true"` - Enables data persistence

### Client Configuration (`recipes/clients/chroma_benchmark.yaml`)

```yaml
client:
  name: chroma_benchmark
  container_image: chroma_client.sif
  duration: 300  # 5 minutes
  
  parameters:
    collection_name: "benchmark_collection"
    num_documents: 1000          # Scale up for stress testing
    embedding_dimension: 384     # Standard sentence transformer size
    batch_size: 100              # Batch size for insertions
    num_queries: 100             # Number of search queries
    top_k: 10                    # Results per query
    concurrent_operations: 5     # Parallel operations
    output_file: "/tmp/chroma_benchmark_results.json"
    wait_for_service: 120        # Service readiness timeout
  
  target_service:
    name: chroma
    port: 8000
    health_check_endpoint: "/api/v1/heartbeat"
  
  script:
    name: "chroma_benchmark.py"
    local_path: "benchmark_scripts/"
    remote_path: "$HOME/benchmark_scripts/"
```

**Key Parameters:**
- `num_documents` - Scale to test throughput (1K-1M)
- `embedding_dimension` - Match your model (384, 768, 1536, etc.)
- `batch_size` - Tune for optimal insertion speed
- `num_queries` - Number of similarity searches
- `top_k` - Results per query (affects latency)

### Customization Examples

#### Large-Scale Benchmark
```yaml
parameters:
  num_documents: 100000      # 100K documents
  batch_size: 500            # Larger batches
  num_queries: 1000          # More queries
  embedding_dimension: 768   # Larger embeddings
```

#### Low-Latency Testing
```yaml
parameters:
  num_documents: 10000
  num_queries: 1000
  concurrent_operations: 20   # High concurrency
  top_k: 5                    # Fewer results
```

#### Memory-Intensive Workload
```yaml
resources:
  mem: "32GB"                # More memory
  
parameters:
  num_documents: 1000000     # 1M documents
  embedding_dimension: 1536  # Large embeddings
```

## Benchmark Operations

The benchmark script performs these operations:

### 1. Collection Setup
- Deletes existing collection (if any)
- Creates new collection with metadata
- Configures for specified embedding dimension

### 2. Document Insertion
- Generates random normalized embeddings
- Inserts documents in batches
- Measures throughput (docs/second)
- Tracks per-batch performance

### 3. Similarity Search
- Performs similarity searches
- Measures query latency
- Calculates percentiles (P95, P99)
- Tests top-k retrieval

### 4. Metrics Collected

**Insertion Metrics:**
- Total documents inserted
- Total insertion time
- Documents per second (throughput)
- Per-batch timing

**Query Metrics:**
- Total queries executed
- Queries per second
- Average latency
- Min/Max latency
- P95 latency
- P99 latency

### Example Output

```json
{
  "summary": {
    "total_documents_inserted": 1000,
    "insertion_throughput": 156.8,
    "total_queries_executed": 100,
    "query_throughput": 45.2,
    "avg_query_latency_ms": 22.1,
    "p95_query_latency_ms": 35.4,
    "p99_query_latency_ms": 42.7
  },
  "operations": [
    {
      "operation": "insertion",
      "total_documents": 1000,
      "batch_size": 100,
      "total_time": 6.38,
      "documents_per_second": 156.8,
      "success": true
    },
    {
      "operation": "query",
      "num_queries": 100,
      "top_k": 10,
      "total_time": 2.21,
      "queries_per_second": 45.2,
      "avg_latency": 0.0221,
      "success": true
    }
  ]
}
```

## Troubleshooting

### Service Not Starting

**Symptom:** Service stays in PENDING or fails to start

**Solutions:**
```bash
# Check SLURM queue
ssh login.lxp.lu
squeue -u $USER

# Check logs
cat slurm-<job_id>.out
cat slurm-<job_id>.err

# Verify container exists
ls -lh ~/containers/chroma_latest.sif

# Rebuild container if needed
apptainer pull docker://chromadb/chroma:latest
mv chroma_latest.sif ~/containers/
```

### Client Cannot Connect

**Symptom:** Client fails with connection errors

**Solutions:**
```bash
# Verify service is RUNNING
python main.py --status

# Check correct hostname
ssh login.lxp.lu
squeue -j <service_job_id> -o "%N"  # Shows node name

# Test connectivity from client node
ssh login.lxp.lu
curl http://mel2198:8000/api/v1/heartbeat

# Increase wait_for_service timeout
# Edit recipes/clients/chroma_benchmark.yaml
wait_for_service: 300  # 5 minutes
```

### Out of Memory

**Symptom:** Job fails with OOM or killed

**Solutions:**
```yaml
# Increase memory allocation
resources:
  mem: "16GB"  # or higher

# Reduce workload size
parameters:
  num_documents: 500     # Fewer documents
  batch_size: 50         # Smaller batches
```

### Slow Performance

**Symptom:** Low throughput or high latency

**Solutions:**
```yaml
# Tune batch size
parameters:
  batch_size: 200  # Experiment with values

# Reduce embedding dimension
parameters:
  embedding_dimension: 384  # Instead of 768

# Use faster partition
resources:
  partition: gpu  # If available
```

### Container Build Issues

**Symptom:** Container download/build fails

**Solutions:**
```bash
# Manual container build
ssh login.lxp.lu
cd ~/containers
apptainer pull docker://chromadb/chroma:latest
apptainer pull docker://python:3.11-slim

# Verify images
apptainer inspect chroma_latest.sif
```

## Advanced Usage

### Running Multiple Clients

Test scalability with multiple concurrent clients:

```bash
# Terminal 1
python main.py --recipe recipes/clients/chroma_benchmark.yaml \
  --target-endpoint http://mel2198

# Terminal 2
python main.py --recipe recipes/clients/chroma_benchmark.yaml \
  --target-endpoint http://mel2198

# Terminal 3
python main.py --recipe recipes/clients/chroma_benchmark.yaml \
  --target-endpoint http://mel2198
```

### Custom Benchmark Script

Modify `benchmark_scripts/chroma_benchmark.py` to add:
- Custom embedding models
- Different query patterns
- Metadata filtering tests
- Update operations
- Delete operations

### Integration with Ollama

Combine Chroma with Ollama for RAG (Retrieval-Augmented Generation):

```bash
# Start both services
python main.py --recipe recipes/services/chroma.yaml
python main.py --recipe recipes/services/ollama.yaml

# Check status
python main.py --status

# Create custom client that uses both services
# (Implementation exercise for the user)
```

## Next Steps

1. **Scale Testing**: Increase `num_documents` to test limits
2. **Custom Workloads**: Modify benchmark script for your use case
3. **Integration**: Combine with other services (Ollama, databases)
4. **Monitoring**: Add Prometheus/Grafana for metrics visualization
5. **Optimization**: Tune parameters for your specific workload

## Support

For issues or questions:
- Check SLURM logs: `slurm-<job_id>.out`
- Review orchestrator logs
- Consult Chroma documentation: https://docs.trychroma.com/
- Check HPC cluster documentation

---

*This guide is part of the HPC Orchestrator project for AI/ML workload management.*
