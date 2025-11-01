# Monitor Module Documentation

## Overview

The Monitor module provides Prometheus-based monitoring capabilities for HPC services and clients, with integrated cAdvisor support for container metrics. Prometheus services can be deployed on HPC nodes to monitor containerized services across different nodes, with metrics accessible via SSH tunneling.

## Features

- **cAdvisor Integration**: Automatic installation and configuration of cAdvisor for container monitoring
- **Multi-Node Monitoring**: Monitor services running on different HPC nodes from a central Prometheus instance
- **Container Metrics**: Collect CPU, memory, network, and filesystem metrics from containerized services
- **SSH Tunneling**: Access Prometheus web UI at localhost:9090 via SSH tunnel
- **Automatic Service Discovery**: Prometheus automatically finds service hosts via SLURM
- **PromQL Queries**: Execute queries via CLI or web interface

## Quick Start - cAdvisor Monitoring with SSH Tunnel

### Step 1: Start Services with cAdvisor

Start one or more services with cAdvisor monitoring enabled:

```bash
# Start Ollama with cAdvisor
python main.py --recipe recipes/services/ollama_with_cadvisor.yaml
```

Check the service ID:
```bash
python main.py --status
```

Output:
```
Services:
   3653331 | ollama_abc123 |    RUNNING |     1:23 | mel2073
```

Note the service ID: `ollama_abc123` and the node: `mel2073`

**What happens**: The service script will:
1. Check if cAdvisor is downloaded at `$HOME/.local/bin/cadvisor`
2. Download cAdvisor if not present (one-time download)
3. Start cAdvisor in the background on port 8080
4. Start your service (Ollama) in the container
5. cAdvisor exposes container metrics at `http://mel2073:8080/metrics`

### Step 2: Configure Prometheus to Monitor cAdvisor

Edit `recipes/services/prometheus_with_cadvisor.yaml` and add your service ID:

```yaml
service:
  name: prometheus
  
  monitoring_targets:
    - service_id: "ollama_abc123"    # Your service ID from step 1
      job_name: "ollama-cadvisor"    # Name in Prometheus
      port: 8080                     # cAdvisor metrics port
```

### Step 3: Start Prometheus

```bash
python main.py --recipe recipes/services/prometheus_with_cadvisor.yaml
```

Output:
```
Service started: session_1
```

Check Prometheus status:
```bash
python main.py --status
```

Output:
```
Services:
   3653331 | ollama_abc123       |    RUNNING |     5:23 | mel2073
   3653332 | prometheus_6355d49f |    RUNNING |     0:35 | mel2074
```

Note the Prometheus service ID: `prometheus_6355d49f` and node: `mel2074`

**What happens**: Prometheus will:
1. Start on node `mel2074` (could be different from service nodes)
2. Configure scraping targets based on your recipe
3. Resolve service IDs to actual hostnames (e.g., `ollama_abc123` → `mel2073`)
4. Start scraping cAdvisor metrics from `http://mel2073:8080/metrics`
5. Make metrics available via its API on port 9090

### Step 4: Create SSH Tunnel to Access Prometheus UI

```bash
python main.py --create-tunnel prometheus_6355d49f 9090 9090
```

Output:
```
======================================================================
SSH TUNNEL SETUP
======================================================================
To access mel2074:9090 at localhost:9090,
run the following command in a separate terminal:

  ssh -i ~/.ssh/id_ed25519_mlux -L 9090:mel2074:9090 -N u103227@login.lxp.lu -p 8822

Then access the service at: http://localhost:9090
======================================================================
```

**Copy and run the SSH command** in a separate terminal. Keep that terminal open.

### Step 5: Access Prometheus Web UI

Open your browser and go to:
```
http://localhost:9090
```

You should see the Prometheus web interface!

### Step 6: Query Container Metrics

#### Via Web UI (Recommended for Exploration)

1. Go to http://localhost:9090/graph
2. In the query box, try these queries:

```promql
# Check if cAdvisor is up
up{job="ollama-cadvisor"}

# Memory usage of containers
container_memory_usage_bytes

# CPU usage rate (last 5 minutes)
rate(container_cpu_usage_seconds_total[5m])

# Network receive rate
rate(container_network_receive_bytes_total[5m])

# Find containers by name
container_memory_usage_bytes{name=~".*ollama.*"}
```

#### Via Command Line

```bash
# Query via CLI (executes on cluster)
python main.py --query-metrics prometheus_6355d49f "container_memory_usage_bytes"

# List all available metrics
python main.py --list-available-metrics prometheus_6355d49f

# Query specific container
python main.py --query-metrics prometheus_6355d49f 'container_cpu_usage_seconds_total{name=~".*apptainer.*"}'
```

### Step 7: Monitor Multiple Services

To monitor multiple services on different nodes:

1. Start multiple services with cAdvisor:
```bash
python main.py --recipe recipes/services/ollama_with_cadvisor.yaml
python main.py --recipe recipes/services/redis_with_cadvisor.yaml
```

2. Get their service IDs:
```bash
python main.py --status
# ollama_abc123 on mel2073
# redis_def456 on mel2075
```

3. Update Prometheus recipe:
```yaml
monitoring_targets:
  - service_id: "ollama_abc123"
    job_name: "ollama-cadvisor"
    port: 8080
  
  - service_id: "redis_def456"
    job_name: "redis-cadvisor"
    port: 8080
```

4. Start Prometheus and create tunnel as before

5. Query metrics from all services:
```promql
# Memory usage across all monitored containers
container_memory_usage_bytes{job=~".*cadvisor"}

# Compare CPU usage between services
rate(container_cpu_usage_seconds_total{job="ollama-cadvisor"}[5m])
rate(container_cpu_usage_seconds_total{job="redis-cadvisor"}[5m])
```

### Step 8: Cleanup

```bash
# Stop Prometheus (closes SSH tunnel automatically if managed)
python main.py --stop-service prometheus_6355d49f

# Stop monitored services
python main.py --stop-service ollama_abc123
python main.py --stop-service redis_def456

# Or stop all services at once
python main.py --stop-all-services
```

## Architecture

The monitoring system consists of:

1. **cAdvisor**: Container metrics exporter that runs on service nodes
   - Automatically downloaded and installed when `enable_cadvisor: true` in service recipe
   - Exposes container metrics on port 8080 by default
   - Monitors CPU, memory, network, filesystem usage of Apptainer containers
   - Lightweight and runs in the background alongside services

2. **PrometheusService** (`src/services/prometheus.py`): Prometheus service implementation
   - Can run on a different node than monitored services
   - Scrapes metrics from cAdvisor instances across multiple nodes
   - Stores time-series data for querying and analysis
   - Provides HTTP API and web UI on port 9090

3. **Service Recipes**: YAML configurations for services and monitoring
   - Services with `enable_cadvisor: true` automatically install and run cAdvisor
   - Prometheus recipe specifies which services to monitor via `monitoring_targets`
   - Automatic hostname resolution from service IDs

4. **SSH Tunneling**: Secure access to Prometheus UI
   - Create tunnel via `--create-tunnel` command
   - Access Prometheus at `http://localhost:9090` from your local machine
   - Works even when compute nodes are not directly accessible

5. **ServersModule** (`src/servers.py`): Manages all services including Prometheus

6. **SSH Query Mechanism**: Execute PromQL queries via CLI without browser

### How It Works

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│   Service Node  │         │ Prometheus Node │         │  Local Machine  │
│    (mel2073)    │         │    (mel2074)    │         │                 │
├─────────────────┤         ├─────────────────┤         ├─────────────────┤
│                 │         │                 │         │                 │
│  Ollama Service │         │   Prometheus    │◄────────┤  SSH Tunnel     │
│  (port 11434)   │         │   (port 9090)   │         │  localhost:9090 │
│                 │         │        │        │         │                 │
│  cAdvisor       │◄────────┤  Scrapes every  │         │  Browser/CLI    │
│  (port 8080)    │         │    15 seconds   │         │  queries        │
│  exposes metrics│         │                 │         │                 │
└─────────────────┘         └─────────────────┘         └─────────────────┘
```

### Key Design Points

- **Decentralized cAdvisor**: Each service node runs its own cAdvisor instance
- **Centralized Prometheus**: Single Prometheus instance can monitor multiple nodes
- **Automatic Installation**: cAdvisor downloaded once per user, reused across jobs
- **Cross-Node Monitoring**: Prometheus on node A can scrape cAdvisor on nodes B, C, D
- **Service Discovery**: Service IDs automatically resolved to hostnames
- **Persistent Metrics**: Prometheus stores data for the duration specified (default: 15 days)

## cAdvisor Integration

### What is cAdvisor?

cAdvisor (Container Advisor) is Google's open-source container resource usage and performance analyzer. It:
- Monitors Apptainer/Singularity containers
- Collects CPU, memory, network, and filesystem metrics
- Exposes metrics in Prometheus format at `/metrics` endpoint
- Requires no container modifications

### Enabling cAdvisor in Services

Add to any service recipe:

```yaml
service:
  name: your_service
  
  # Enable cAdvisor monitoring
  enable_cadvisor: true
  cadvisor_port: 8080  # Optional, default is 8080
  
  # ... rest of your service configuration
```

### How cAdvisor Installation Works

When a service with `enable_cadvisor: true` starts:

1. **Check**: Script checks if cAdvisor exists at `$HOME/.local/bin/cadvisor`

2. **Download** (if not found):
   ```bash
   wget https://github.com/google/cadvisor/releases/download/v0.47.2/cadvisor-v0.47.2-linux-amd64
   chmod +x cadvisor
   ```

3. **Start**: cAdvisor runs in background
   ```bash
   cadvisor -port=8080 -housekeeping_interval=10s &
   ```

4. **Verify**: Script checks if metrics endpoint responds
   ```bash
   curl http://localhost:8080/metrics
   ```

5. **Continue**: Your service starts normally

**Benefits**:
- **One-time download**: cAdvisor binary reused across all jobs
- **Fast startup**: If already downloaded, just starts immediately
- **No manual intervention**: Completely automated in SLURM script

### cAdvisor Metrics Reference

Common cAdvisor metrics you can query:

#### Memory Metrics
```promql
# Current memory usage
container_memory_usage_bytes

# Memory working set (active memory)
container_memory_working_set_bytes

# Memory limit
container_spec_memory_limit_bytes

# Memory usage percentage
(container_memory_usage_bytes / container_spec_memory_limit_bytes) * 100
```

#### CPU Metrics
```promql
# Total CPU time consumed
container_cpu_usage_seconds_total

# CPU usage rate (last 5 minutes)
rate(container_cpu_usage_seconds_total[5m])

# CPU usage by container
rate(container_cpu_usage_seconds_total{name=~".*ollama.*"}[5m])
```

#### Network Metrics
```promql
# Bytes received
container_network_receive_bytes_total

# Bytes transmitted
container_network_transmit_bytes_total

# Receive rate (last 5 minutes)
rate(container_network_receive_bytes_total[5m])

# Transmit rate (last 5 minutes)
rate(container_network_transmit_bytes_total[5m])
```

#### Filesystem Metrics
```promql
# Filesystem usage
container_fs_usage_bytes

# Filesystem limit
container_fs_limit_bytes

# Disk usage percentage
(container_fs_usage_bytes / container_fs_limit_bytes) * 100
```

#### Container Info
```promql
# Container last seen (uptime indicator)
container_last_seen

# Container start time
container_start_time_seconds

# Check if container is running
up{job="your-cadvisor-job"}
```

### Filtering by Container

Use label matchers to filter metrics:

```promql
# By container name (regex)
container_memory_usage_bytes{name=~".*ollama.*"}

# By job (from Prometheus config)
container_cpu_usage_seconds_total{job="ollama-cadvisor"}

# By instance (node hostname)
container_memory_usage_bytes{instance="mel2073"}

# Multiple filters
rate(container_cpu_usage_seconds_total{job="ollama-cadvisor",name=~".*apptainer.*"}[5m])
```

## SSH Tunneling

### Why SSH Tunneling?

HPC compute nodes (e.g., `mel2073`, `mel2074`) are typically not directly accessible from outside the cluster. SSH tunneling allows you to:
- Access Prometheus web UI at `http://localhost:9090`
- Securely forward traffic through the login node
- Use your local browser to explore metrics
- No need for VPN or direct node access

### Creating a Tunnel

#### Method 1: Using CLI (Recommended)

```bash
# Basic usage (defaults to port 9090:9090)
python main.py --create-tunnel prometheus_6355d49f

# Custom ports
python main.py --create-tunnel prometheus_6355d49f 8080 9090
# This maps local port 8080 to remote port 9090
```

#### Method 2: Manual SSH Command

If you prefer manual control:

```bash
ssh -i ~/.ssh/id_ed25519_mlux \
    -L 9090:mel2074:9090 \
    -N u103227@login.lxp.lu \
    -p 8822
```

Where:
- `-i ~/.ssh/id_ed25519_mlux`: Your SSH key
- `-L 9090:mel2074:9090`: Forward local 9090 to mel2074:9090
- `-N`: Don't execute remote commands (just tunnel)
- `u103227@login.lxp.lu -p 8822`: Login node connection

### Using the Tunnel

1. **Start the tunnel** (keep terminal open):
   ```bash
   # Run the SSH command from --create-tunnel output
   ssh -i ~/.ssh/id_ed25519_mlux -L 9090:mel2074:9090 -N u103227@login.lxp.lu -p 8822
   ```

2. **Access Prometheus** in your browser:
   - Main UI: http://localhost:9090
   - Graph page: http://localhost:9090/graph
   - Targets: http://localhost:9090/targets
   - Metrics explorer: http://localhost:9090/metrics

3. **Query metrics** in the web UI:
   ```promql
   container_memory_usage_bytes
   ```

4. **Stop the tunnel**: Press `Ctrl+C` in the SSH terminal

### Troubleshooting Tunnels

**"Connection refused"**:
- Check if Prometheus is actually running: `python main.py --status`
- Verify the node hostname is correct
- Wait a moment for Prometheus to fully start

**"Port already in use"**:
- Another process is using port 9090 locally
- Use a different local port: `--create-tunnel service_id 9091 9090`
- Or kill the process using the port

**"Permission denied"**:
- Check your SSH key path and permissions
- Verify your SSH credentials are correct

**Tunnel disconnects**:
- Some firewalls timeout idle connections
- Add `-o ServerAliveInterval=60` to SSH command to send keepalive packets

## Quick Start (Command Line)

### 1. Start a Service with cAdvisor

First, start a service with cAdvisor monitoring enabled:

```bash
python main.py --recipe recipes/services/ollama_with_cadvisor.yaml
```

Check the service ID:
```bash
python main.py --status
```

Output:
```
Services:
   3653331 | ollama_abc123 |    RUNNING |     1:23 | mel2073
```

Note the service ID: `ollama_abc123`

### 2. Configure Prometheus to Monitor the Service via cAdvisor

Edit `recipes/services/prometheus_with_cadvisor.yaml` and update the monitoring target:

```yaml
service:
  name: prometheus
  
  monitoring_targets:
    - service_id: "ollama_abc123"    # Your service ID from step 1
      job_name: "ollama-cadvisor"    # Name in Prometheus
      port: 8080                     # cAdvisor metrics port
```

### 3. Start Prometheus

```bash
python main.py --recipe recipes/services/prometheus_with_cadvisor.yaml
```

Output:
```
Service started: session_1
```

### 4. Check What's Running

```bash
python main.py --status
```

Output:
```
Services:
   3653331 | ollama_abc123       |    RUNNING |     5:23 | mel2073
   3653332 | prometheus_6355d49f |    RUNNING |     4:35 | mel2074
```

Note the Prometheus service ID: `prometheus_6355d49f`

### 5. Create SSH Tunnel

```bash
python main.py --create-tunnel prometheus_6355d49f
```

This will display an SSH command. Run it in a separate terminal and keep it open.

### 6. Access Prometheus Web UI

Open your browser and visit:
```
http://localhost:9090
```

### 7. Query Container Metrics

In the Prometheus web UI, try these queries:

```promql
# Check if cAdvisor is up
up{job="ollama-cadvisor"}

# Container memory usage
container_memory_usage_bytes

# Container CPU rate
rate(container_cpu_usage_seconds_total[5m])
```

Or query via CLI:

```bash
# Query via CLI
python main.py --query-metrics prometheus_6355d49f "container_memory_usage_bytes"

# List available metrics
python main.py --list-available-metrics prometheus_6355d49f
```

### 8. Stop Services

```bash
# Stop Prometheus
python main.py --stop-service prometheus_6355d49f

# Stop Ollama
python main.py --stop-service ollama_abc123

# Or stop all
python main.py --stop-all-services
```

## Configuration Examples

### Service with cAdvisor Enabled

Enable cAdvisor monitoring for any service:

```yaml
# recipes/services/your_service_with_cadvisor.yaml
service:
  name: your_service
  container_image: your_service.sif
  
  # Enable cAdvisor for container monitoring
  enable_cadvisor: true
  cadvisor_port: 8080  # Optional, default is 8080
  
  container:
    docker_source: docker://your/image:latest
    image_path: $HOME/containers/your_service.sif
  
  resources:
    mem: 16G
    cpus_per_task: 4
    time: "01:00:00"
  
  environment:
    YOUR_VAR: "value"
  
  ports:
    - 8000  # Your service port
```

### Monitor a Single Service via cAdvisor

```yaml
# recipes/services/prometheus_with_cadvisor.yaml
service:
  name: prometheus
  
  monitoring_targets:
    - service_id: "ollama_abc123"     # Replace with your service ID
      job_name: "ollama-cadvisor"
      port: 8080                      # cAdvisor metrics port
  
  container:
    docker_source: docker://prom/prometheus:latest
    image_path: $HOME/containers/prometheus.sif
  
  resources:
    mem: 4G
    cpus_per_task: 2
    time: "02:00:00"
  
  ports:
    - 9090
  
  # Optional: Enable cAdvisor for Prometheus itself
  enable_cadvisor: false
```

### Monitor Multiple Services Across Nodes

Monitor services running on different HPC nodes:

```yaml
service:
  name: prometheus
  
  monitoring_targets:
    # Ollama on node mel2073
    - service_id: "ollama_abc123"
      job_name: "ollama-gpu-node"
      port: 8080
    
    # Redis on node mel2075
    - service_id: "redis_def456"
      job_name: "redis-cpu-node"
      port: 8080
    
    # Chroma on node mel2076
    - service_id: "chroma_ghi789"
      job_name: "chroma-vector-db"
      port: 8080
    
    # You can also monitor by direct hostname if you know it
    - host: "mel2074"
      job_name: "specific-node"
      port: 8080
  
  container:
    docker_source: docker://prom/prometheus:latest
    image_path: $HOME/containers/prometheus.sif
  
  resources:
    mem: 8G
    cpus_per_task: 4
    time: "04:00:00"
    partition: cpu
  
  environment:
    PROMETHEUS_RETENTION_TIME: "30d"  # Keep metrics for 30 days
  
  ports:
    - 9090
```

### Complete Example: Ollama with Monitoring

**Step 1**: Service recipe with cAdvisor (`ollama_monitored.yaml`)

```yaml
service:
  name: ollama
  container_image: ollama_latest.sif
  command: ollama
  args: ["serve"]
  
  # Enable cAdvisor
  enable_cadvisor: true
  cadvisor_port: 8080
  
  container:
    docker_source: "docker://ollama/ollama:latest"
    image_path: "$HOME/containers/ollama_latest.sif"
  
  resources:
    time: "02:00:00"
    partition: gpu
    gres: "gpu:1"
    mem: "16GB"
  
  environment:
    OLLAMA_HOST: "0.0.0.0:11434"
  
  ports:
    - 11434
```

**Step 2**: Start the service
```bash
python main.py --recipe ollama_monitored.yaml
# Note the service ID: ollama_abc123
```

**Step 3**: Prometheus recipe (`prometheus_monitor.yaml`)

```yaml
service:
  name: prometheus
  
  monitoring_targets:
    - service_id: "ollama_abc123"  # From step 2
      job_name: "ollama-gpu"
      port: 8080
  
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

**Step 4**: Start Prometheus
```bash
python main.py --recipe prometheus_monitor.yaml
# Note the service ID: prometheus_xyz789
```

**Step 5**: Create tunnel and access
```bash
python main.py --create-tunnel prometheus_xyz789
# Run the SSH command shown
# Open http://localhost:9090 in browser
```

## Quick Start (Python API)

### Using as a Service

```python
from orchestrator import BenchmarkOrchestrator

orchestrator = BenchmarkOrchestrator('config.yaml')

# Load Prometheus recipe
recipe = orchestrator.load_recipe('recipes/services/prometheus.yaml')

# Start as a service
session_id = orchestrator.start_benchmark_session(recipe)

# Get services
services = orchestrator.servers.list_running_services()
# Find prometheus service ID from the list

# Get service host
host = orchestrator.servers.get_service_host(service_id)
print(f"Prometheus on: {host}")
```

### Query via SSH

For programmatic querying, you can use the SSH client directly:

```python
service_id = "6355d49f"
host = orchestrator.servers.get_service_host(service_id)

if host:
    endpoint = f"http://{host}:9090"
    query = "up"
    curl_cmd = f"curl -s '{endpoint}/api/v1/query?query={query}'"
    
    exit_code, stdout, stderr = orchestrator.ssh_client.execute_command(curl_cmd)
    
    if exit_code == 0:
        import json
        result = json.loads(stdout)
        print(result)
```

## Command Line Reference

### MonitorsModule Class

#### Methods

##### `start_monitor(recipe: dict) -> str`
Start a Prometheus monitoring instance.

**Parameters:**
- `recipe`: Dictionary containing Prometheus configuration

**Returns:**
- Monitor ID (string)

**Example:**
```python
recipe = orchestrator.load_recipe('recipes/services/prometheus.yaml')
monitor_id = orchestrator.monitors.start_monitor(recipe)
```

---

##### `stop_monitor(monitor_id: str) -> bool`
Stop a running monitor.

**Parameters:**
- `monitor_id`: Monitor identifier

**Returns:**
- `True` if successful, `False` otherwise

---

##### `check_monitor_status(monitor_id: str) -> dict`
Get current status of a monitor.

**Returns:**
```python
{
    'monitor_id': 'abc123',
    'status': 'running',
    'job_id': '12345',
    'nodes': ['mel2345'],
    'submitted_at': 1234567890.0,
    'started_at': 1234567900.0
}
```

---

##### `get_monitor_endpoint(monitor_id: str) -> Optional[str]`
Get the Prometheus HTTP endpoint URL.

**Returns:**
- Endpoint URL (e.g., `http://mel2345:9090`) or `None`

---

##### `query_metrics(monitor_id: str, query: str) -> dict`
Execute a PromQL query against Prometheus.

**Parameters:**
- `monitor_id`: Monitor identifier
- `query`: PromQL query string

**Returns:**
- Prometheus API response (JSON)

**Example:**
```python
# Query service availability
metrics = orchestrator.monitors.query_metrics(monitor_id, "up")

# Query CPU usage
cpu = orchestrator.monitors.query_metrics(
    monitor_id,
    "rate(process_cpu_seconds_total[5m])"
)
```

---

##### `collect_metrics_to_file(monitor_id: str, query: str, output_file: str) -> bool`
Query metrics and save to a file.

**Parameters:**
- `monitor_id`: Monitor identifier
- `query`: PromQL query
- `output_file`: Output filename (saved in `metrics/` directory)

**Returns:**
- `True` if successful

---

##### `show_metrics(monitor_id: str, query: str = None) -> dict`
Display current metrics (defaults to "up" query).

---

##### `construct_report(monitor_id: str, output_file: str) -> bool`
Generate a comprehensive monitoring report with multiple metrics.

**Report includes:**
- Monitor status
- Service availability (`up`)
- CPU usage
- Memory usage
- Scrape duration

---

##### `list_running_monitors() -> List[str]`
Get list of all running monitor IDs.

---

##### `list_available_monitors() -> List[str]`
Get list of available monitor types (currently: `['prometheus']`).

---

## Prometheus Configuration

### Recipe File Structure

```yaml
# recipes/services/prometheus.yaml

service:
  name: prometheus
  
  container:
    docker_source: docker://prom/prometheus:latest
    image_path: $HOME/containers/prometheus.sif
  
  resources:
    mem: 4G
    cpus_per_task: 2
    time: "02:00:00"
  
  environment:
    PROMETHEUS_RETENTION_TIME: "15d"
  
  ports:
    - 9090
```

### Prometheus Configuration File

The module automatically creates a basic `prometheus.yml` configuration:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
  
  - job_name: 'node'
    static_configs:
      - targets: ['localhost:9100']
```

You can customize this by modifying `$HOME/prometheus/config/prometheus.yml` on the HPC cluster.

## Common Use Cases

### 1. Monitor a Running Service

```python
# Start your service
service_id = orchestrator.servers.start_service(service_recipe)

# Start Prometheus monitor
monitor_recipe = orchestrator.load_recipe('recipes/services/prometheus.yaml')
monitor_id = orchestrator.monitors.start_monitor(monitor_recipe)

# Wait for both to start
time.sleep(30)

# Get endpoints
service_host = orchestrator.servers.get_service_host(service_id)
prometheus_url = orchestrator.monitors.get_monitor_endpoint(monitor_id)

print(f"Service running on: {service_host}")
print(f"Prometheus at: {prometheus_url}")
```

### 2. Continuous Metric Collection

```python
import time

# Start monitor
monitor_id = orchestrator.monitors.start_monitor(prometheus_recipe)
time.sleep(30)

# Collect metrics every 5 minutes
for i in range(12):  # Run for 1 hour
    timestamp = int(time.time())
    
    orchestrator.monitors.collect_metrics_to_file(
        monitor_id,
        "up",
        f"metrics_{timestamp}.json"
    )
    
    print(f"Metrics collected at {timestamp}")
    time.sleep(300)  # 5 minutes
```

### 3. Generate End-of-Session Report

```python
# After benchmark session completes
orchestrator.monitors.construct_report(
    monitor_id,
    f"session_{session_id}_report.json"
)

# Stop monitor
orchestrator.monitors.stop_monitor(monitor_id)
```

## PromQL Query Examples

Common queries you can use:

```python
# Service availability
orchestrator.monitors.query_metrics(monitor_id, "up")

# CPU usage rate (5-minute average)
orchestrator.monitors.query_metrics(
    monitor_id,
    "rate(process_cpu_seconds_total[5m])"
)

# Memory usage
orchestrator.monitors.query_metrics(
    monitor_id,
    "process_resident_memory_bytes"
)

# Scrape duration
orchestrator.monitors.query_metrics(
    monitor_id,
    "scrape_duration_seconds"
)

# HTTP request rate
orchestrator.monitors.query_metrics(
    monitor_id,
    "rate(http_requests_total[5m])"
)
```

## Troubleshooting

### Monitor Won't Start

1. Check SLURM job status:
```python
status = orchestrator.monitors.check_monitor_status(monitor_id)
print(status)
```

2. Check SLURM logs:
```bash
cat slurm-<job_id>.out
```

### Cannot Query Metrics

1. Ensure monitor is running:
```python
status = orchestrator.monitors.check_monitor_status(monitor_id)
assert status['status'] == 'running'
```

2. Wait for Prometheus to fully start (usually 10-30 seconds)

3. Check if endpoint is reachable:
```python
endpoint = orchestrator.monitors.get_monitor_endpoint(monitor_id)
print(f"Try accessing: {endpoint}")
```

### Metrics Not Appearing

1. Check Prometheus configuration:
```bash
cat $HOME/prometheus/config/prometheus.yml
```

2. Verify scrape targets are configured correctly

3. Check Prometheus UI at `http://<node>:9090/targets`

## Integration with Orchestrator

The monitor module is integrated into the main orchestrator:

```python
# Access via orchestrator
orchestrator = BenchmarkOrchestrator('config.yaml')

# Monitor operations
orchestrator.monitors.start_monitor(recipe)
orchestrator.monitors.check_monitor_status(monitor_id)
orchestrator.show_monitors_status()  # All monitors

# System-wide status
system_status = orchestrator.get_system_status()
print(system_status['monitors'])
```

## Architecture Diagrams

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                            HPC CLUSTER                              │
│                                                                     │
│  ┌──────────────────────┐      ┌───────────────────────┐            │
│  │  GPU Node (mel2073)  │      │   CPU Node (mel2074)  │            │
│  ├──────────────────────┤      ├───────────────────────┤            │
│  │                      │      │                       │            │
│  │  ┌─────────────────┐ │      │  ┌─────────────────┐  │            │
│  │  │ Ollama Service  │ │      │  │   Prometheus    │  │            │
│  │  │  Port: 11434    │ │      │  │   Port: 9090    │  │            │
│  │  └─────────────────┘ │      │  └────────┬────────┘  │            │
│  │          │           │      │           │           │            │
│  │  ┌───────▼─────────┐ │      │     Scrapes every     │            │
│  │  │    cAdvisor     │◄├──────┼─────15 seconds        │            │
│  │  │  Port: 8080     │ │      │           │           │            │
│  │  │  /metrics       │ │      │  Stores time-series   │            │
│  │  └─────────────────┘ │      │       metrics         │            │
│  │    Monitors: CPU,    │      │                       │            │
│  │    Memory, Network,  │      │                       │            │
│  │    Disk              │      │                       │            │
│  └──────────────────────┘      └──────────┬────────────┘            │
│                                           │                         │
│  ┌───────────────────────┐                │                         │
│  │   GPU Node (mel2075)  │                │                         │
│  ├───────────────────────┤                │                         │
│  │                       │                │                         │
│  │  ┌─────────────────┐  │                │                         │
│  │  │ Redis Service   │  │                │                         │
│  │  │  Port: 6379     │  │                │                         │
│  │  └─────────────────┘  │                │                         │
│  │          │            │                │                         │
│  │  ┌───────▼─────────┐  │                │                         │
│  │  │    cAdvisor     │◄-├────────────────┘                         │
│  │  │  Port: 8080     │  │                                          │
│  │  │  /metrics       │  │                                          │
│  │  └─────────────────┘  │                                          │
│  └───────────────────────┘                                          │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────┐      │
│  │               Login Node (login.lxp.lu:8822)              │      │
│  │                    SSH Gateway                            │      │
│  └─────────────────────────────┬─────────────────────────────┘      │
└────────────────────────────────┼────────────────────────────────────┘
                                 │
                                 │ SSH Tunnel
                                 │ Port Forwarding
                                 │
                       ┌─────────▼─────────┐
                       │                   │
                       │  Local Machine    │
                       │                   │
                       │  localhost:9090   │◄────┐
                       │                   │     │
                       └───────────────────┘     │
                                                 │
                       ┌─────────────────────────┴─────┐
                       │                               │
                       │   Web Browser / CLI           │
                       │                               │
                       │   Prometheus UI               │
                       │   Query Metrics               │
                       │   View Dashboards             │
                       │                               │
                       └───────────────────────────────┘
```

### Data Flow: Service Startup with cAdvisor

```
User Command → python main.py --recipe ollama_with_cadvisor.yaml
    │
    ▼
SLURM Job Submission
    │
    ├─→ Service starts on GPU node (mel2073)
    │
    ▼
cAdvisor Installation Check
    │
    ├─→ Check: $HOME/.local/bin/cadvisor exists?
    │   │
    │   ├─→ YES: Skip download
    │   │
    │   └─→ NO:  Download from GitHub
    │           wget https://github.com/google/cadvisor/...
    │           chmod +x cadvisor
    │
    ▼
cAdvisor Startup
    │
    ├─→ cadvisor -port=8080 -housekeeping_interval=10s &
    │
    ▼
Health Check
    │
    ├─→ curl http://localhost:8080/metrics
    │
    ▼
Service Starts
    │
    └─→ ollama serve
```

### Metric Collection Flow

```
Container → cAdvisor → Prometheus → Query → User
    │           │            │          │        │
    │           │            │          │        │
 Running    Monitors      Stores     PromQL   Browser/CLI
 Service    Resources   Time-series  Query    Dashboard
            
            Every 10s    Every 15s    On-demand
            
            Metrics:     Retention:   Format:
            • CPU        • 15 days    • JSON
            • Memory     • ~1TB       • Graph
            • Network    • Queryable  • Table
            • Disk
```

### Storage Layout

```
$HOME/
├── .local/
│   └── bin/
│       └── cadvisor                    # One-time download
│
├── containers/
│   ├── ollama_latest.sif              # Service container
│   ├── prometheus.sif                  # Prometheus container
│   └── redis_latest.sif               # Another service
│
├── prometheus/
│   ├── config/
│   │   └── prometheus.yml             # Generated by script
│   └── data/
│       └── [time-series database]     # Prometheus storage
│
├── cadvisor.log                       # cAdvisor logs
└── slurm-<job_id>.out                # SLURM job output
```

## Quick Reference

### Common Commands

#### Service Management
```bash
# List running services
python main.py --status

# Stop a service
python main.py --stop-service <service_id>

# Stop all services
python main.py --stop-all-services
```

#### Prometheus Queries (CLI)
```bash
# Query container memory
python main.py --query-metrics <prometheus_id> "container_memory_usage_bytes"

# Query CPU rate
python main.py --query-metrics <prometheus_id> "rate(container_cpu_usage_seconds_total[5m])"

# List all metrics
python main.py --list-available-metrics <prometheus_id>

# Filter by container name
python main.py --query-metrics <prometheus_id> 'container_memory_usage_bytes{name=~".*ollama.*"}'
```

#### SSH Tunnel
```bash
# Create tunnel (default ports 9090:9090)
python main.py --create-tunnel <prometheus_id>

# Custom ports (local:remote)
python main.py --create-tunnel <prometheus_id> 8080 9090

# Access after tunnel is established
# Browser: http://localhost:9090
```

### Useful PromQL Queries

#### Memory Metrics
```promql
# Current memory usage
container_memory_usage_bytes

# Working set memory
container_memory_working_set_bytes

# Memory usage by container
container_memory_usage_bytes{name=~".*ollama.*"}

# Memory percentage
(container_memory_usage_bytes / container_spec_memory_limit_bytes) * 100
```

#### CPU Metrics
```promql
# CPU usage rate (5 min avg)
rate(container_cpu_usage_seconds_total[5m])

# CPU by container
rate(container_cpu_usage_seconds_total{name=~".*ollama.*"}[5m])
```

#### Network Metrics
```promql
# Network receive rate
rate(container_network_receive_bytes_total[5m])

# Network transmit rate
rate(container_network_transmit_bytes_total[5m])

# Total network I/O
rate(container_network_receive_bytes_total[5m]) + rate(container_network_transmit_bytes_total[5m])
```

#### Filesystem Metrics
```promql
# Disk usage
container_fs_usage_bytes

# Disk usage percentage
(container_fs_usage_bytes / container_fs_limit_bytes) * 100
```

#### Status Checks
```promql
# Check if cAdvisor is up
up{job=~".*cadvisor"}

# Container uptime
time() - container_start_time_seconds

# All containers
container_last_seen
```

### Recipe Templates

#### Service with cAdvisor
```yaml
service:
  name: my_service
  container_image: my_service.sif
  
  # Enable monitoring
  enable_cadvisor: true
  cadvisor_port: 8080
  
  container:
    docker_source: "docker://my/image:latest"
    image_path: "$HOME/containers/my_service.sif"
  
  resources:
    mem: 8G
    cpus_per_task: 2
    time: "01:00:00"
  
  environment:
    MY_VAR: "value"
  
  ports:
    - 8000
```

#### Prometheus Configuration
```yaml
service:
  name: prometheus
  
  monitoring_targets:
    - service_id: "service_abc123"  # From: python main.py --status
      job_name: "my-service"
      port: 8080
  
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

## Troubleshooting Guide

### cAdvisor Issues

**cAdvisor Not Starting**
```bash
# Check SLURM log
cat slurm-<job_id>.out

# Look for download/start messages
# Expected: "cAdvisor is running on port 8080"
```

**Download Fails**
- Check network connectivity from compute node
- Verify GitHub is accessible from cluster
- Manually download and place at `$HOME/.local/bin/cadvisor`

**Port Already in Use**
- Change `cadvisor_port` in recipe to different port (e.g., 8081)
- Update Prometheus monitoring_targets accordingly

**Metrics Not Available**
- Wait ~30 seconds for cAdvisor to start collecting
- Check if container is actually running
- Verify cAdvisor process is alive: `ps aux | grep cadvisor`

### Prometheus Issues

**Targets Show as DOWN**
```bash
# Verify service is running
python main.py --status

# Check if service has cAdvisor enabled
# Look for: enable_cadvisor: true in recipe

# Test cAdvisor endpoint (via SSH on compute node)
curl http://localhost:8080/metrics
```

**No Metrics Collected**
- Wait 15-30 seconds for first scrape
- Check targets page: http://localhost:9090/targets (via tunnel)
- Verify network connectivity between Prometheus node and service nodes
- Check Prometheus logs in SLURM output

**Configuration Errors**
- Review generated prometheus.yml in SLURM output
- Verify service_id resolution worked correctly
- Check for typos in monitoring_targets section

### SSH Tunnel Issues

**Connection Refused**
```bash
# Verify Prometheus is running
python main.py --status

# Check correct node/port
python main.py --service-endpoint <prometheus_id>

# Try different local port if 9090 is busy
python main.py --create-tunnel <prometheus_id> 9091 9090
```

**Port Already in Use**
- Another process is using port 9090 locally
- Use different local port as shown above
- Or kill the process: `netstat -ano | findstr :9090` (Windows)

**Tunnel Disconnects**
- Some firewalls timeout idle connections
- Add keepalive to SSH command: `-o ServerAliveInterval=60`
- Or refresh browser to keep connection active

**Permission Denied**
- Check SSH key path and permissions
- Verify SSH credentials are correct
- Test basic SSH connection: `ssh user@login.lxp.lu -p 8822`

### Query Issues

**Empty Results**
- Wait for first scrape cycle (~15-30 seconds)
- Check if metric name is correct (use list-available-metrics)
- Verify cAdvisor is collecting data for your container
- Check label filters (job, name, instance)

**Syntax Errors**
- Use single quotes for PromQL with regex: `'container_memory_usage_bytes{name=~".*ollama.*"}'`
- Properly escape special characters
- Verify bracket matching in rate/increase functions

**Performance Issues**
- Reduce query time range for large datasets
- Use more specific label filters
- Consider aggregation functions (sum, avg, max)

## Best Practices

1. **Start services with cAdvisor enabled**: Add `enable_cadvisor: true` to service recipes for monitoring

2. **Use appropriate retention**: Set `PROMETHEUS_RETENTION_TIME` based on your needs (default: 15 days)

3. **Clean up when done**: Always stop services and Prometheus to free resources
   ```bash
   python main.py --stop-all-services
   ```

4. **Wait for metrics**: Allow 30-60 seconds after starting for full metric collection

5. **Use SSH tunnels for exploration**: The Prometheus web UI is much easier than CLI for discovering metrics

6. **Keep tunnels alive**: SSH tunnel terminal must stay open; consider using `screen` or `tmux`

7. **Monitor multiple services**: One Prometheus can monitor many services across nodes

8. **Label your targets**: Use descriptive `job_name` values in monitoring_targets for clarity

9. **Regular metric collection**: Use CLI queries for automated metric collection in scripts

10. **Check targets page**: Always verify targets are UP before querying: http://localhost:9090/targets

## Example Script

See `examples/monitor_example.py` for a complete working example.

Run it with:
```bash
python examples/monitor_example.py
```

## Limitations

1. **Single Prometheus per monitor**: Each monitor instance runs one Prometheus server
2. **Manual configuration**: Scrape targets must be configured manually in `prometheus.yml`
3. **No authentication**: Current implementation doesn't include Prometheus authentication
4. **Simple queries only**: Uses basic PromQL queries via HTTP API

## Future Enhancements

Possible extensions (KEEP IT SIMPLE, only add if really needed):
- Auto-discovery of service targets
- Alerting configuration
- Grafana integration for visualization
- Metric exporters for services
- Authentication and security
