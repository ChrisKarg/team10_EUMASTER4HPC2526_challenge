# Complete Automated Benchmarking & Monitoring Guide

This guide demonstrates both the complete benchmarking session and monitoring-only workflows.

## Table of Contents
- [Complete Benchmarking Session](#complete-benchmarking-session-start-session)
- [Monitoring Only](#monitoring-only-start-monitoring)
- [Comparison: Manual vs Automated](#comparison-manual-vs-automated)
- [Advanced Usage](#advanced-usage)
- [Troubleshooting](#troubleshooting)

---

# Complete Benchmarking Session (`--start-session`)

## Overview

The `--start-session` command automates the entire end-to-end benchmarking workflow:
1. ✅ Starts service with cAdvisor monitoring
2. ✅ Waits for service to be assigned to a node
3. ✅ Configures Prometheus with the detected service and correct node
4. ✅ Starts Prometheus monitoring with proper targets
5. ✅ Starts client benchmark targeting the service
6. ✅ Creates SSH tunnel for Prometheus UI

**This replaces 10+ manual steps with a single command!**

## Quick Start

### Single Command

```bash
python main.py --start-session \
    recipes/services/ollama_with_cadvisor.yaml \
    recipes/clients/ollama_benchmark.yaml \
    recipes/services/prometheus_with_cadvisor.yaml
```

That's it! The system will:
- Start Ollama service with cAdvisor
- Wait for service to be assigned to node
- Configure Prometheus with the correct target node
- Start Prometheus monitoring
- Start benchmark client targeting Ollama
- Create SSH tunnel for you

## Complete Benchmarking Examples

### Example 1: Ollama LLM Benchmarking

```bash
python main.py --start-session \
    recipes/services/ollama_with_cadvisor.yaml \
    recipes/clients/ollama_benchmark.yaml \
    recipes/services/prometheus_with_cadvisor.yaml
```

**Expected Output**:
```
======================================================================
AUTOMATED BENCHMARKING SESSION
======================================================================
Service recipe:    recipes/services/ollama_with_cadvisor.yaml
Client recipe:     recipes/clients/ollama_benchmark.yaml
Prometheus recipe: recipes/services/prometheus_with_cadvisor.yaml
======================================================================

[1/5] Starting service with cAdvisor...
✅ Service started: session_1

[2/5] Waiting for service to be assigned to a node...
   Attempt 1/18: Service found but waiting for node assignment...
   Attempt 2/18: Service found but waiting for node assignment...
✅ Service ready: ollama_abc123 on mel2073

[3/5] Configuring Prometheus to monitor ollama_abc123 on mel2073...
✅ Prometheus configured to monitor ollama_abc123 at mel2073:8080
   Starting Prometheus with configured targets...
✅ Prometheus started: session_2

[4/5] Waiting for Prometheus to be assigned to a node...
   Attempt 1/12: Prometheus waiting for node assignment...
   Attempt 2/12: Prometheus waiting for node assignment...
✅ Prometheus ready: prometheus_6355d49f on mel2074

[5/5] Starting client benchmark targeting ollama_abc123...
   Service endpoint: http://mel2073:11434
✅ Client started: client_def456

Creating SSH tunnel to Prometheus...
======================================================================
SSH TUNNEL SETUP
======================================================================
To access mel2074:9090 at localhost:9090,
run the following command in a separate terminal:

  ssh -i ~/.ssh/id_ed25519_mlux -L 9090:mel2074:9090 -N u103227@login.lxp.lu -p 8822

Then access the service at: http://localhost:9090
======================================================================

======================================================================
BENCHMARKING SESSION COMPLETE
======================================================================
Service ID:    ollama_abc123
Service Host:  mel2073:11434
Client ID:     client_def456
Prometheus ID: prometheus_6355d49f
Prometheus UI: http://localhost:9090 (after tunnel setup)

Session Components:
  1. Service 'ollama' with cAdvisor monitoring
  2. Prometheus collecting metrics from cAdvisor at mel2073:8080
  3. Client benchmark running against service

To access Prometheus UI:
  1. Run the SSH command shown above in a separate terminal
  2. Open http://localhost:9090 in your browser

To query metrics:
  python main.py --query-metrics prometheus_6355d49f "up"
  python main.py --query-metrics prometheus_6355d49f "container_memory_usage_bytes"

To check client status:
  python main.py --status

To stop everything:
  python main.py --stop-all-services
======================================================================
```

### Example 2: Redis Benchmarking

```bash
python main.py --start-session \
    recipes/services/redis_with_cadvisor.yaml \
    recipes/clients/redis_benchmark.yaml \
    recipes/services/prometheus_with_cadvisor.yaml
```

### Example 3: Chroma Vector Database Benchmarking

```bash
python main.py --start-session \
    recipes/services/chroma_with_cadvisor.yaml \
    recipes/clients/chroma_benchmark.yaml \
    recipes/services/prometheus_with_cadvisor.yaml
```

---

# Monitoring Only (`--start-monitoring`)

## Overview

The `--start-monitoring` command automates just the monitoring setup (without client benchmarking):
1. Starts your service with cAdvisor enabled
2. Waits for service to be assigned to a node
3. Configures Prometheus with the detected service and correct node
4. Starts Prometheus monitoring with proper targets
5. Creates SSH tunnel for web UI access

## Quick Start

### Single Command Setup

```bash
python main.py --start-monitoring \
    recipes/services/ollama_with_cadvisor.yaml \
    recipes/services/prometheus_with_cadvisor.yaml
```

This single command replaces these manual steps:
- Start service: `python main.py --recipe recipes/services/ollama_with_cadvisor.yaml`
- Check status: `python main.py --status` (to get service ID)
- Edit Prometheus recipe to add service ID (manual file editing)
- Start Prometheus: `python main.py --recipe recipes/services/prometheus_with_cadvisor.yaml`
- Check status again: `python main.py --status` (to get Prometheus ID)
- Create tunnel: `python main.py --create-tunnel prometheus_xyz 9090 9090`

## Recipe Requirements

### 1. Prepare Your Recipes

Ensure your service recipe has cAdvisor enabled:

**recipes/services/ollama_with_cadvisor.yaml**:
```yaml
service:
  name: ollama
  container_image: ollama_latest.sif
  
  # Enable cAdvisor for monitoring
  enable_cadvisor: true
  cadvisor_port: 8080
  
  container:
    docker_source: "docker://ollama/ollama:latest"
    image_path: "$HOME/containers/ollama_latest.sif"
  
  resources:
    mem: 16G
    cpus_per_task: 4
    time: "02:00:00"
    partition: gpu
    gres: "gpu:1"
  
  environment:
    OLLAMA_HOST: "0.0.0.0:11434"
  
  ports:
    - 11434
```

**recipes/services/prometheus_with_cadvisor.yaml**:
```yaml
service:
  name: prometheus
  
  # Monitoring targets will be automatically updated by --start-monitoring
  monitoring_targets: []
  
  container:
    docker_source: docker://prom/prometheus:latest
    image_path: $HOME/containers/prometheus.sif
  
  resources:
    mem: 4G
    cpus_per_task: 2
    time: "02:00:00"
  
  ports:
    - 9090
```

### 2. Run Monitoring Setup

```bash
python main.py --start-monitoring \
    recipes/services/ollama_with_cadvisor.yaml \
    recipes/services/prometheus_with_cadvisor.yaml
```

### 3. Expected Output

```
======================================================================
AUTOMATED MONITORING SETUP
======================================================================
Service recipe: recipes/services/ollama_with_cadvisor.yaml
Prometheus recipe: recipes/services/prometheus_with_cadvisor.yaml
======================================================================

[1/5] Starting service with cAdvisor...
✅ Service started: session_1

[2/5] Waiting for service to be assigned to a node...
   Attempt 1/12: Service not yet assigned to node...
   Attempt 2/12: Service not yet assigned to node...
✅ Service assigned: ollama_abc123 on mel2073

[3/5] Configuring Prometheus to monitor ollama_abc123...
✅ Added ollama_abc123 to monitoring targets

[4/5] Starting Prometheus...
✅ Prometheus started: session_2
   Waiting for Prometheus to be assigned to a node...
✅ Prometheus assigned: prometheus_6355d49f on mel2074

[5/5] Creating SSH tunnel to Prometheus...
======================================================================
SSH TUNNEL SETUP
======================================================================
To access mel2074:9090 at localhost:9090,
run the following command in a separate terminal:

  ssh -i ~/.ssh/id_ed25519_mlux -L 9090:mel2074:9090 -N u103227@login.lxp.lu -p 8822

Then access the service at: http://localhost:9090
======================================================================

======================================================================
MONITORING SETUP COMPLETE
======================================================================
Service ID: ollama_abc123
Prometheus ID: prometheus_6355d49f

To access Prometheus UI:
  1. Run the SSH command shown above in a separate terminal
  2. Open http://localhost:9090 in your browser

To query metrics:
  python main.py --query-metrics prometheus_6355d49f "up"
  python main.py --query-metrics prometheus_6355d49f "container_memory_usage_bytes"

To stop everything:
  python main.py --stop-service prometheus_6355d49f
  python main.py --stop-service ollama_abc123
======================================================================
```

---

# Monitoring the Session

## Check Status

```bash
python main.py --status
```

Output shows all components:
```
Services:
   3653331 | ollama_abc123       |    RUNNING |     5:23 | mel2073
   3653332 | prometheus_6355d49f |    RUNNING |     4:35 | mel2074

Clients:
   3653333 | client_def456       |    RUNNING |     3:10 | mel2076
```

## Access Prometheus UI

1. Run the SSH tunnel command in a separate terminal
2. Open http://localhost:9090 in your browser
3. Query metrics:

```promql
# Check all components are up
up

# Service container metrics
container_memory_usage_bytes{job="ollama-cadvisor"}
rate(container_cpu_usage_seconds_total{job="ollama-cadvisor"}[5m])

# Network I/O
rate(container_network_receive_bytes_total[5m])
```

## Query Metrics via CLI

```bash
# Check service availability
python main.py --query-metrics prometheus_6355d49f "up"

# Memory usage
python main.py --query-metrics prometheus_6355d49f "container_memory_usage_bytes"

# CPU rate
python main.py --query-metrics prometheus_6355d49f 'rate(container_cpu_usage_seconds_total[5m])'

# List all available metrics
python main.py --list-available-metrics prometheus_6355d49f
```

## Session Cleanup

### Stop Specific Components

```bash
# Stop Prometheus (optional, keeps service and client running)
python main.py --stop-service prometheus_6355d49f

# Stop client (stops benchmark, keeps service running)
python main.py --stop-service client_def456

# Stop service
python main.py --stop-service ollama_abc123
```

### Stop Everything at Once

```bash
python main.py --stop-all-services
```

This stops all running services, clients, and monitoring in one command.

---

# Comparison: Manual vs Automated

## Manual Process (Before)
```bash
# Step 1: Start service
python main.py --recipe recipes/services/ollama_with_cadvisor.yaml

# Step 2: Check status and copy service ID
python main.py --status
# Output: ollama_abc123 on mel2073 (manually copy this)

# Step 3: Edit Prometheus recipe file
# vim recipes/services/prometheus_with_cadvisor.yaml
# Add: 
#   monitoring_targets:
#     - service_id: "ollama_abc123"
#       host: "mel2073"
#       port: 8080

# Step 4: Start Prometheus
python main.py --recipe recipes/services/prometheus_with_cadvisor.yaml

# Step 5: Check status again and copy Prometheus ID
python main.py --status
# Output: prometheus_xyz789 (manually copy this)

# Step 6: Start client with copied service ID
python main.py --recipe recipes/clients/ollama_benchmark.yaml --target-service ollama_abc123

# Step 7: Create SSH tunnel
python main.py --create-tunnel prometheus_xyz789 9090 9090

# Total: 7 commands + 2 manual edits + 3 copy/paste operations
```

## Automated Process (Now)
```bash
python main.py --start-session \
    recipes/services/ollama_with_cadvisor.yaml \
    recipes/clients/ollama_benchmark.yaml \
    recipes/services/prometheus_with_cadvisor.yaml

# Total: 1 command + 0 manual operations
```

**Time savings**: ~5-7 minutes → ~90 seconds  
**Error potential**: 5 error points → 0 error points  
**User actions**: 12 → 1

---

# Advanced Usage

## What Gets Automated

### Service Endpoint Detection

The system automatically detects service endpoints based on service type:
- **Ollama**: `http://node:11434`
- **Redis**: `http://node:6379`
- **Chroma**: `http://node:8000`
- **Custom**: Uses first port from recipe

### Client Configuration

The client is automatically configured with:
- **Target Service ID**: Detected service ID
- **Target Endpoint**: Detected service host and port
- No manual editing required!

### Prometheus Targets

Prometheus monitoring targets are automatically configured:
- **Service ID**: Auto-detected
- **Host**: Actual node where service is running (e.g., mel2073)
- **Job Name**: Based on service name + "-cadvisor"
- **Port**: 8080 (cAdvisor default)

## Custom Service Ports

If your service uses a custom port, the system will try to detect it from the recipe:

```yaml
# In your service recipe
service:
  ports:
    - 9999  # Custom port
```

The client will automatically use `http://node:9999` as the endpoint.

## Multiple Clients

To run multiple benchmarks against the same service:

```bash
# Start first session
python main.py --start-session \
    recipes/services/ollama_with_cadvisor.yaml \
    recipes/clients/ollama_benchmark.yaml \
    recipes/services/prometheus_with_cadvisor.yaml

# Note the service ID from output: ollama_abc123

# Start another client manually
python main.py --recipe recipes/clients/ollama_benchmark_2.yaml --target-service ollama_abc123
```

## Monitoring Multiple Services

To monitor multiple services simultaneously, start each service+monitoring pair separately, or use a single Prometheus instance for all:

```bash
# Option 1: Separate monitoring for each service
python main.py --start-session service1.yaml client1.yaml prometheus.yaml
python main.py --start-session service2.yaml client2.yaml prometheus.yaml

# Option 2: One Prometheus for all services (start services first)
python main.py --recipe service1.yaml
python main.py --recipe service2.yaml
# Wait for both to be running, then:
python main.py --start-monitoring service1_id prometheus.yaml
python main.py --add-monitoring-target prometheus_id service2_id
python main.py --reload-prometheus prometheus_id
```

---

# How It Works

## Workflow Steps (Under the Hood)

The automated workflow executes these steps:

### 1. Start Service
- Launches service with cAdvisor sidecar
- Service submitted to SLURM scheduler

### 2. Wait for Service Node Assignment
- Polls SLURM every 5 seconds
- Waits up to 90 seconds for node assignment
- Captures actual node where service is running (e.g., mel2073)

### 3. Configure and Start Prometheus
- **Key Innovation**: Prometheus configured AFTER service location is known
- Creates prometheus.yml with correct target:
  ```yaml
  monitoring_targets:
    - service_id: "ollama_abc123"
      host: "mel2073"  # Actual node from step 2
      job_name: "ollama-cadvisor"
      port: 8080
  ```
- Starts Prometheus with auto-configured targets
- No "Could not resolve host" warnings!

### 4. Wait for Prometheus
- Polls SLURM every 5 seconds
- Waits up to 60 seconds for Prometheus to be running
- Creates SSH tunnel command for UI access

### 5. Start Client
- Launches benchmark/client targeting the service
- Uses auto-detected service endpoint

## Key Features

- **Sequential Configuration**: Service location detected before Prometheus starts
- **Automatic Node Detection**: Uses SLURM job info (`squeue %N`) for actual node assignments
- **Smart Timeouts**: 90 seconds for service, 60 seconds for Prometheus
- **Error Prevention**: Prometheus always gets correct service target
- **SSH Tunnel Setup**: Generates ready-to-use tunnel commands
- **Cleanup Ready**: All components tracked for easy shutdown

## Service Endpoint Detection

The system automatically detects service endpoints based on service type:
- **Ollama**: `http://node:11434`
- **Redis**: `http://node:6379`
- **Chroma**: `http://node:8000`
- **Custom**: Uses first port from recipe

## Status Tracking

All components tracked with:
- **job_name**: Original name from recipe
- **service_id**: Unique identifier (e.g., ollama_abc123)
- **status**: Real-time status from SLURM (RUNNING/PENDING/etc.)
- **nodes**: Actual node assignment when running

---

# Benefits Summary

1. **No Manual Configuration**: System detects service nodes automatically
2. **Immediate Monitoring**: Prometheus configured and started automatically with correct targets
3. **Error Prevention**: No chance of wrong node names, IDs, or "Could not resolve host" issues
4. **Time Savings**: Complete setup in ~90 seconds instead of 5+ minutes
5. **Reproducibility**: Same command works every time
6. **Easy Cleanup**: Single command stops all components
7. **Zero Copy-Paste**: No need to manually copy service IDs or node names

---

# Troubleshooting

## Service ID Not Detected

If the automated setup fails to detect service ID:

```bash
# Check manually
python main.py --status

# Use the service ID with manual setup
python main.py --recipe recipes/services/prometheus_with_cadvisor.yaml
```

## Client Fails to Start

If client fails to start:

1. Verify service is running: `python main.py --status`
2. Check service endpoint is correct
3. Look at client SLURM logs: `cat slurm-<job_id>.out`
4. Verify client recipe is compatible with service

## Prometheus Not Accessible

If you can't access Prometheus after creating the tunnel:

1. Verify Prometheus is running:
   ```bash
   python main.py --status
   ```

2. Check the tunnel command is correct

3. Wait 30-60 seconds for Prometheus to fully start

4. Try accessing: http://localhost:9090/targets to see if targets are configured

## No Metrics Available

If Prometheus shows no metrics:

1. Verify cAdvisor is running in the service container (check SLURM logs)

2. Check Prometheus targets page: http://localhost:9090/targets
   - Targets should show as "UP"
   - If "DOWN", check network connectivity

3. Wait 15-30 seconds for first scrape cycle

4. Verify service ID was correctly added to Prometheus config

---

# Best Practices

1. **Use `--start-session` by default**: It's the easiest and most reliable way
2. **Wait for completion**: Let the command finish before accessing Prometheus
3. **Keep SSH tunnel open**: The tunnel terminal must stay active
4. **Check status regularly**: Monitor all components with `--status`
5. **Clean up after**: Always stop services when done to free resources
6. **Use appropriate resources**: Ensure service has enough memory/CPU for both service and benchmark load

---  

## See Also

- [Monitor Documentation](../docs/MONITOR_DOCUMENTATION.md) - Complete monitoring reference
- [cAdvisor Integration](../docs/MONITOR_DOCUMENTATION.md#cadvisor-integration) - How cAdvisor works
- [Prometheus Configuration](../docs/MONITOR_DOCUMENTATION.md#prometheus-configuration) - Advanced config
- [Troubleshooting Guide](../docs/MONITOR_DOCUMENTATION.md#troubleshooting-guide) - Common issues
