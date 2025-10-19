# HPC Benchmarking Orchestrator - API Documentation

## Table of Contents
1. [Core Classes](#core-classes)
2. [API Reference](#api-reference)
3. [Configuration Schema](#configuration-schema)
4. [Recipe Formats](#recipe-formats)
5. [Usage Examples](#usage-examples)
6. [Error Codes](#error-codes)

## Core Classes

### BenchmarkOrchestrator

The central orchestration engine that coordinates all benchmarking operations.

#### Constructor
```python
BenchmarkOrchestrator(config_path: str = "config.yaml")
```

#### Key Methods

##### Recipe Management
- `load_recipe(file_path: str) -> dict`
  - Loads and validates a benchmark recipe from YAML file
  - **Parameters**: `file_path` - Path to the recipe YAML file
  - **Returns**: Parsed recipe dictionary
  - **Raises**: `FileNotFoundError`, `ValueError`

##### Session Management
- `start_benchmark_session(recipe: dict) -> str`
  - Launches a complete benchmark session with services and clients
  - **Parameters**: `recipe` - Recipe dictionary containing service and client definitions
  - **Returns**: Unique session ID
  - **Raises**: `RuntimeError` if service deployment fails

- `stop_benchmark_session(session_id: str) -> bool`
  - Stops all components of a benchmark session
  - **Parameters**: `session_id` - Session identifier
  - **Returns**: True if successful

##### Service Management
- `stop_service(service_id: str) -> bool`
  - Stops a specific service by ID
  - **Parameters**: `service_id` - Service identifier
  - **Returns**: True if successfully stopped

- `stop_all_services() -> dict`
  - Stops all running services
  - **Returns**: Dictionary with stop results and statistics

##### Status and Monitoring
- `show_servers_status() -> dict`
  - Returns status of all running services
  - **Returns**: Dictionary with service statuses

- `show_clients_status() -> dict`
  - Returns status of all running clients
  - **Returns**: Dictionary with client statuses

- `get_system_status() -> dict`
  - Returns comprehensive system status
  - **Returns**: Dictionary with overall system state

- `get_slurm_status() -> dict`
  - Returns raw SLURM job status for all user jobs
  - **Returns**: Dictionary with SLURM job information

##### Debugging and Utilities
- `debug_services() -> dict`
  - Returns detailed debug information about all services
  - **Returns**: Dictionary with debug information

- `clear_all_state()`
  - Clears all tracked services and clients from memory
  - **Returns**: Tuple of (cleared_services_count, cleared_clients_count)

- `generate_report(session_id: str, output_path: str)`
  - Generates a comprehensive benchmark report
  - **Parameters**: 
    - `session_id` - Session to generate report for
    - `output_path` - Output file path

### ServersModule

Manages the lifecycle of services on the HPC cluster.

#### Key Methods

- `list_available_services() -> List[str]`
  - Returns list of all available service types from recipes
  - **Returns**: List of service names

- `list_running_services() -> List[str]`
  - Returns list of currently active service IDs
  - **Returns**: List of running service IDs

- `start_service(recipe: dict) -> str`
  - Deploys a new service instance
  - **Parameters**: `recipe` - Service configuration dictionary
  - **Returns**: Unique service ID
  - **Raises**: `RuntimeError` if deployment fails

- `stop_service(service_id: str) -> bool`
  - Stops a running service
  - **Parameters**: `service_id` - Service identifier
  - **Returns**: True if successful

- `check_service_status(service_id: str) -> dict`
  - Returns detailed status of a specific service
  - **Parameters**: `service_id` - Service identifier
  - **Returns**: Dictionary with service status details

### ClientsModule

Manages benchmark client workloads that target services.

#### Key Methods

- `list_available_clients() -> List[str]`
  - Returns list of all available client types from recipes
  - **Returns**: List of client names

- `list_running_clients() -> List[str]`
  - Returns list of currently active client IDs
  - **Returns**: List of running client IDs

- `start_client(recipe: dict, target_service_id: str, target_service_host: str = None) -> str`
  - Launches a benchmark client against a target service
  - **Parameters**: 
    - `recipe` - Client configuration dictionary
    - `target_service_id` - ID of the target service
    - `target_service_host` - Optional host override
  - **Returns**: Unique client ID

- `stop_client(client_id: str) -> bool`
  - Stops a running client
  - **Parameters**: `client_id` - Client identifier
  - **Returns**: True if successful

- `check_client_status(client_id: str) -> dict`
  - Returns detailed status of a specific client
  - **Parameters**: `client_id` - Client identifier
  - **Returns**: Dictionary with client status details

### MonitorsModule

Manages Prometheus monitoring instances for metrics collection.

**Note**: Prometheus runs as a **service** (tracked by ServersModule). MonitorsModule provides monitoring-specific utilities and delegates to ServersModule for service operations.

#### Key Methods

- `list_available_services() -> List[str]`
  - Returns list of available monitoring service types
  - **Returns**: List with `['prometheus']`

- `list_running_services() -> List[str]`
  - Returns list of running monitor service IDs
  - **Returns**: List of service IDs

- `start_monitor(recipe: dict) -> str`
  - Starts a new Prometheus monitoring instance
  - **Parameters**: `recipe` - Prometheus recipe configuration
  - **Returns**: Service ID of the started monitor

- `stop_monitor(service_id: str) -> bool`
  - Stops a running monitor
  - **Parameters**: `service_id` - Monitor service identifier
  - **Returns**: True if successful

- `get_monitor_status(service_id: str) -> dict`
  - Gets detailed status of a monitor
  - **Parameters**: `service_id` - Monitor service identifier
  - **Returns**: Dictionary with status details (job_id, status, nodes, etc.)

- `get_monitor_endpoint(service_id: str) -> str`
  - Gets the Prometheus HTTP endpoint URL
  - **Parameters**: `service_id` - Monitor service identifier
  - **Returns**: Endpoint URL (e.g., `http://mel2073:9090`) or None

- `list_running_monitors() -> List[dict]`
  - Lists all running Prometheus monitors with details
  - **Returns**: List of dictionaries with monitor information

#### Querying Metrics

To query metrics from Prometheus, use SSH to execute curl commands on the cluster:

```python
# Get service host
host = orchestrator.servers.get_service_host(service_id)

if host:
    # Build curl command
    endpoint = f"http://{host}:9090"
    query = "up"
    curl_cmd = f"curl -s '{endpoint}/api/v1/query?query={query}'"
    
    # Execute via SSH
    exit_code, stdout, stderr = orchestrator.ssh_client.execute_command(curl_cmd)
    
    if exit_code == 0:
        import json
        result = json.loads(stdout)
        print(result)
```

**Note**: Queries must execute via SSH on the cluster due to internal DNS resolution.

### SSHClient

Handles secure communication with the HPC cluster.

#### Key Methods

- `connect() -> bool`
  - Establishes SSH connection to HPC cluster
  - **Returns**: True if connection successful

- `execute_command(command: str) -> Tuple[int, str, str]`
  - Executes a command on the remote cluster
  - **Parameters**: `command` - Shell command to execute
  - **Returns**: Tuple of (exit_code, stdout, stderr)

- `submit_slurm_job(script_content: str) -> str`
  - Submits a SLURM job to the cluster
  - **Parameters**: `script_content` - Complete SLURM script
  - **Returns**: SLURM job ID

- `cancel_slurm_job(job_id: str) -> bool`
  - Cancels a SLURM job
  - **Parameters**: `job_id` - SLURM job identifier
  - **Returns**: True if successful

## Configuration Schema

### Main Configuration (config.yaml)

```yaml
# HPC Connection Settings
hpc:
  hostname: "meluxina.lxp.lu"
  username: "your_username"
  key_filename: "~/.ssh/id_rsa"
  port: 8822

# SLURM Default Settings
slurm:
  account: "p200981"
  partition: "gpu"
  qos: "default"
  time: "01:00:00"
  nodes: 1
  ntasks: 1
  ntasks_per_node: 1

# Directory Paths
services_dir: "recipes/services"
clients_dir: "recipes/clients"

# Container Settings
containers:
  auto_build: true
  build_timeout: "30:00"
  registry: "docker://registry.example.com"
```

### Service Recipe Schema

```yaml
# Service Definition
name: "ollama"
description: "Ollama LLM inference service"
container_image: "ollama_latest.sif"
command: "ollama"
args: ["serve"]

# Resource Requirements
resources:
  gpu: 1
  memory: "16GB"
  slurm:
    partition: "gpu"
    time: "02:00:00"
    gres: "gpu:1"

# Environment Variables
environment:
  OLLAMA_HOST: "0.0.0.0:11434"
  OLLAMA_KEEP_ALIVE: "5m"
  CUDA_VISIBLE_DEVICES: "0"

# Network Ports
ports:
  - 11434

# Health Check (Optional)
health_check:
  endpoint: "/api/health"
  interval: 30
  timeout: 10
  retries: 3
```

### Client Recipe Schema

```yaml
# Client Definition
name: "ollama_benchmark"
description: "Ollama performance benchmark"
container_image: "benchmark_tools.sif"
workload_type: "llm_inference"
duration: 300  # seconds

# Target Service Configuration
target_service:
  type: "ollama"
  port: 11434
  endpoint: "/api/generate"

# Resource Requirements
resources:
  memory: "8GB"
  slurm:
    partition: "cpu"
    time: "00:30:00"

# Environment Variables
environment:
  BENCHMARK_MODE: "performance"
  LOG_LEVEL: "INFO"

# Benchmark Parameters
parameters:
  model: "llama2:7b"
  requests_per_second: 10
  concurrent_users: 5
  prompt_length: 100
  max_tokens: 256
```

### Complete Recipe Schema

```yaml
# Complete Benchmark Recipe (services + clients)
service:
  name: "ollama"
  # ... service configuration

---

client:
  name: "ollama_benchmark"
  # ... client configuration
```

## Usage Examples

### Basic Service Deployment

```python
from orchestrator import BenchmarkOrchestrator

# Initialize orchestrator
orch = BenchmarkOrchestrator("config.yaml")

# Load and deploy a service
recipe = orch.load_recipe("recipes/ollama_simple.yaml")
session_id = orch.start_benchmark_session(recipe)

print(f"Started session: {session_id}")

# Monitor status
status = orch.get_system_status()
print(f"Services running: {status['services']['total_services']}")
```

### Manual Service and Client Management

```python
# Start service only
service_recipe = {
    'name': 'ollama',
    'container_image': 'ollama_latest.sif',
    'resources': {'gpu': 1, 'memory': '16GB'},
    'environment': {'OLLAMA_HOST': '0.0.0.0:11434'},
    'ports': [11434]
}

service_id = orch.servers.start_service(service_recipe)

# Wait for service to be ready
import time
while True:
    status = orch.servers.check_service_status(service_id)
    if status['status'] == 'running':
        break
    time.sleep(10)

# Start client
client_recipe = {
    'name': 'benchmark_client',
    'container_image': 'benchmark_tools.sif',
    'target_service': {'type': 'ollama', 'port': 11434},
    'workload_type': 'inference',
    'duration': 300
}

client_id = orch.clients.start_client(client_recipe, service_id)
```

### Status Monitoring

```python
# Get comprehensive status
system_status = orch.get_system_status()

# Get SLURM job details
slurm_status = orch.get_slurm_status()

# Debug service issues
debug_info = orch.debug_services()

# Generate report
orch.generate_report(session_id, "benchmark_report.yaml")
```

### Cleanup Operations

```python
# Stop specific service
orch.stop_service(service_id)

# Stop all services
orch.stop_all_services()

# Stop benchmark session
orch.stop_benchmark_session(session_id)

# Clear tracking state
orch.clear_all_state()
```

## Error Codes

### Common Error Scenarios

#### Configuration Errors
- **FileNotFoundError**: Configuration or recipe file not found
- **ValueError**: Invalid YAML format or missing required fields
- **KeyError**: Missing required configuration keys

#### Connection Errors
- **ConnectionError**: Failed to connect to HPC cluster
- **TimeoutError**: SSH operation timeout
- **AuthenticationError**: SSH authentication failed

#### SLURM Errors
- **JobSubmissionError**: SLURM job submission failed
- **JobNotFoundError**: SLURM job ID not found
- **InsufficientResourcesError**: Requested resources not available

#### Service Errors
- **ServiceStartupError**: Service failed to start
- **ServiceNotFoundError**: Service ID not found
- **ServiceHealthCheckError**: Service health check failed

### Error Handling Patterns

```python
try:
    session_id = orch.start_benchmark_session(recipe)
except FileNotFoundError as e:
    print(f"Recipe file not found: {e}")
except ValueError as e:
    print(f"Invalid recipe format: {e}")
except RuntimeError as e:
    print(f"Service deployment failed: {e}")
```

## CLI Interface

### Command Line Usage

```bash
# Start benchmark from recipe
python main.py --recipe recipes/ollama_complete.yaml

# Check system status
python main.py --status

# List available services
python main.py --list-services

# Stop specific service
python main.py --stop-service <SERVICE_ID>

# Stop all services
python main.py --stop-all-services

# Get service endpoint
python main.py --service-endpoint <SERVICE_ID>

# Debug services
python main.py --debug-services

# Clear state
python main.py --clear-state
```

### Monitoring Commands

```bash
# Start Prometheus monitor
python main.py --recipe recipes/services/prometheus.yaml

# List available monitors
python main.py --list-monitors

# Check monitor status
python main.py --monitor-status <SERVICE_ID>

# Query metrics from a service (executed via SSH on cluster)
python main.py --query-service-metrics <SERVICE_ID> "<PROMQL_QUERY>"

# Examples:
python main.py --query-service-metrics 6355d49f "up"
python main.py --query-service-metrics 6355d49f "rate(process_cpu_seconds_total[5m])"
python main.py --query-service-metrics 6355d49f "process_resident_memory_bytes"
```

### Environment Variables

- `ORCHESTRATOR_CONFIG`: Path to configuration file
- `ORCHESTRATOR_LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `SSH_KEY_PATH`: Override SSH key path
- `SLURM_ACCOUNT`: Override SLURM account

## Best Practices

### Recipe Design
1. **Resource Specification**: Always specify appropriate resource requirements
2. **Health Checks**: Include health check endpoints for services
3. **Environment Variables**: Use environment variables for configuration
4. **Timeouts**: Set appropriate SLURM time limits

### Error Handling
1. **Graceful Degradation**: Handle partial failures gracefully
2. **Retry Logic**: Implement retry logic for transient failures
3. **Cleanup**: Always clean up resources after use
4. **Logging**: Use appropriate logging levels

### Performance
1. **Resource Optimization**: Right-size resource allocations
2. **Batch Operations**: Use batch operations where possible
3. **Status Caching**: Cache status information to reduce SLURM queries
4. **Connection Reuse**: Reuse SSH connections

### Security
1. **Key Management**: Use SSH keys instead of passwords
2. **Permission Control**: Set appropriate file permissions
3. **Network Security**: Configure secure container networking
4. **Audit Logging**: Enable audit logging for compliance