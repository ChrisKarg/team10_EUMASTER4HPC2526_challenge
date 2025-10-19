# Monitor Module Documentation

## Overview

The Monitor module provides Prometheus-based monitoring capabilities for HPC services and clients. Prometheus services are deployed on HPC nodes and can be configured to monitor specific services by specifying them in the recipe configuration.

## Features

- **Monitor Specific Services**: Configure Prometheus to track metrics from your services (Ollama, etc.)
- **Automatic Service Discovery**: Prometheus automatically finds service hosts via SLURM
- **Start/Stop Prometheus**: Deploy Prometheus instances on HPC nodes as services
- **Query Metrics via SSH**: Execute PromQL queries through SSH (queries run on the cluster)
- **Status Checking**: Monitor the health of Prometheus instances

## Architecture

The monitoring system consists of:

1. **PrometheusService** (`src/services/prometheus.py`): Prometheus service implementation with target configuration
2. **Recipe** (`recipes/services/prometheus.yaml`): Prometheus deployment and monitoring targets configuration
3. **ServersModule** (`src/servers.py`): Manages Prometheus as a service
4. **MonitorsModule** (`src/monitors.py`): Provides monitoring-specific utilities
5. **SSH Query Mechanism**: Queries execute on cluster via SSH to avoid DNS issues

### Key Design Points

- Prometheus runs as a **service** (tracked by ServersModule)
- **Monitoring targets** are specified in the recipe YAML file
- Prometheus **automatically discovers service hosts** from SLURM using service IDs
- Queries execute **via SSH on the cluster** (not from local machine)
- Service discovery works even if the service isn't in local tracking

## Quick Start (Command Line)

### 1. Start a Service to Monitor

First, start the service you want to monitor (e.g., Ollama):

```bash
python main.py --recipe recipes/services/ollama.yaml
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

### 2. Configure Prometheus to Monitor the Service

Edit `recipes/services/prometheus.yaml` and add the monitoring target:

```yaml
service:
  name: prometheus
  
  monitoring_targets:
    - service_id: "ollama_abc123"    # Your service ID from step 1
      job_name: "ollama-service"     # Name in Prometheus
      port: 11434                    # Service port
```

Or use the example recipe:
```bash
# Edit prometheus_with_ollama.yaml and replace service_id
cp recipes/services/prometheus_with_ollama.yaml my_prometheus.yaml
# Edit my_prometheus.yaml to use your actual service_id
```

### 3. Start Prometheus

```bash
python main.py --recipe my_prometheus.yaml
```

Output:
```
Benchmark session started: session_1
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

Note the Prometheus service ID: `6355d49f`

### 5. Get Service Endpoint

```bash
python main.py --service-endpoint 6355d49f
```

Output:
```
Prometheus endpoint for service 6355d49f:
  Host: mel2074
  API: http://mel2074:9090
  UI: http://mel2074:9090/graph
```

### 6. Query Metrics

Now you can query metrics from **both** Prometheus itself AND the Ollama service:

```bash
# Check what services are being monitored
python main.py --query-service-metrics 6355d49f "up"

# This will show:
# - prometheus (Prometheus itself)
# - ollama-service (your Ollama instance)

# Query specific metrics by job name
python main.py --query-service-metrics 6355d49f "up{job='ollama-service'}"
```

**What Metrics Can You Query?**

Prometheus can scrape metrics from services that expose a `/metrics` endpoint in Prometheus format. By default:

- **Ollama and most services**: May not expose Prometheus metrics natively. You'll see if they're `up` or `down`, but detailed metrics depend on the service.
- **Prometheus itself**: Always exposes detailed metrics about its own operation.

**Note**: Many services don't expose Prometheus metrics by default. If your queries return empty results for a service, it means that service doesn't have a `/metrics` endpoint. This is normal.

### 7. Stop Prometheus

```bash
python main.py --stop-service 6355d49f
```

## Configuration Examples

### Monitor a Single Ollama Service

```yaml
service:
  name: prometheus
  
  monitoring_targets:
    - service_id: "ollama_abc123"
      job_name: "ollama"
      port: 11434
  
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

### Monitor Multiple Services

```yaml
service:
  name: prometheus
  
  monitoring_targets:
    - service_id: "ollama_abc123"
      job_name: "ollama-1"
      port: 11434
    
    - service_id: "ollama_xyz789"
      job_name: "ollama-2"
      port: 11434
    
    # Can also monitor by direct host if you know it
    - host: "mel2073"
      job_name: "specific-node"
      port: 9100  # e.g., node_exporter
  
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

### 7. Stop Services

```bash
# Stop Prometheus
python main.py --stop-service 6355d49f

# Stop Ollama
python main.py --stop-service ollama_abc123
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

## Best Practices

1. **Start monitors before services**: Launch Prometheus before starting services to capture all metrics

2. **Use appropriate retention**: Set `PROMETHEUS_RETENTION_TIME` based on your needs (default: 15 days)

3. **Clean up monitors**: Always stop monitors when done to free resources

4. **Check endpoint availability**: Wait for monitor to fully start before querying

5. **Save metrics periodically**: Use `collect_metrics_to_file()` to preserve important metrics

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
