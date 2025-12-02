# HPC AI Benchmarking Orchestrator

A modular Python orchestrator for running containerized AI benchmarking workloads on HPC clusters via SLURM. This system enables automated deployment and benchmarking of AI services like LLM inference servers, databases, and vector stores.

## 🏗️ Architecture

The orchestrator follows a modular design with five main components:

```
[CLI Interface] → [Orchestrator] → [SSH] → [SLURM] → [Containers]
     ↓               ↓              ↓        ↓          ↓
[YAML Recipes]  [Servers &      [HPC]  [Job Queue] [Services &
                 Clients]              [Scheduler]  Benchmarks]
```

### Core Modules

- **Servers Module**: Manages deployment and lifecycle of services (Ollama, PostgreSQL, Vector DBs)
- **Clients Module**: Launches benchmark workloads against target services
- **Interface Module**: Central orchestration and user-facing management
- **Script Generator**: Creates SLURM batch scripts from YAML recipes
- **SSH Client**: Handles remote HPC operations and job submission

## 🚀 Quick Start

### 1. Setup

```bash
# Clone the repository
git clone https://github.com/ChrisKarg/team10_EUMASTER4HPC2526_challenge.git
cd team10_EUMASTER4HPC2526_challenge

# Install dependencies
pip install -r requirements.txt

# Configure for your HPC cluster
cp config.yaml.example config.yaml
# Edit config.yaml with your cluster details
```

### 2. Configure HPC Connection

Edit `config.yaml`:

```yaml
hpc:
  hostname: "login.lxp.lu"  # Your HPC login node
  username: "your_username"
  key_filename: "~/.ssh/id_rsa"  # SSH key path

slurm:
  account: "p200981"  # Your SLURM account
  partition: "gpu"    # Default partition
```

### 3. Run Your First Benchmark

```bash
# List available services and clients
python main.py --list-services
python main.py --list-clients

# Run a complete Ollama benchmark
python main.py --recipe recipes/ollama_complete.yaml

# Check system status
python main.py --status

# Download results from cluster to local machine
python main.py --download-results
```

## 📋 Usage Examples

### Command Line Interface

```bash
# List available services and clients
python main.py --list-services
python main.py --list-clients

# Check status of running jobs
python main.py --status

# Run a specific recipe
python main.py --recipe recipes/ollama_complete.yaml

# Run client against a service
python main.py --recipe recipes/clients/ollama_benchmark.yaml --target-service <SERVICE_JOB_ID>

# Complete automated session (service + client + monitoring + tunnel)
python main.py --start-session \
    recipes/services/ollama_with_cadvisor.yaml \
    recipes/clients/ollama_benchmark.yaml \
    recipes/services/prometheus_with_cadvisor.yaml

# Monitoring-only setup (without client)
python main.py --start-monitoring \
    recipes/services/ollama_with_cadvisor.yaml \
    recipes/services/prometheus_with_cadvisor.yaml

# Query metrics
python main.py --query-metrics <prometheus_id> "container_memory_usage_bytes"
python main.py --create-tunnel <prometheus_id> 9090 9090

# Download benchmark results from cluster to local machine
python main.py --download-results

# Stop a running service
python main.py --stop-service <JOB_ID>
python main.py --stop-all-services

# Interactive mode
python main.py

# Verbose logging
python main.py --verbose --recipe recipes/services/ollama.yaml
```

### Programmatic Usage

```python
from src.orchestrator import BenchmarkOrchestrator

# Initialize orchestrator
interface = BenchmarkOrchestrator('config.yaml')

# Load and run a recipe
recipe = interface.load_recipe('recipes/ollama_complete.yaml')
session_id = interface.start_benchmark_session(recipe)

status = interface.show_servers_status()
print(f"Running services: {status}")

# Generate report
interface.generate_report(session_id, 'results/report.yaml')
```

## 🎯 Complete Working Example

Here's a step-by-step example to run an Ollama benchmark with separate service and client recipes:

### Step 1: Start the Ollama Service

```bash
# Start the Ollama LLM service
python main.py --recipe recipes/services/ollama.yaml
```

**Expected output:**
```
Service started: abc12345
Monitor the job status through SLURM or check logs.
```

### Step 2: Check Service Status and Get Node IP

```bash
# Check the service status to get the node where it's running
python main.py --status
```

**Expected output:**
```
SLURM Job Status:
  Total Jobs: 1
  Services: 1
  Clients: 0
  Other: 0

Services:
    98765 |    ollama_abc12 |    RUNNING |  0:05:23 | node-01
```

Note the node name (`node-01` in this example) where your service is running.

### Step 3: Run the Benchmark Client

```bash
# Run the benchmark client against the service by using the target endpoint
python main.py --recipe recipes/clients/ollama_benchmark.yaml --target-endpoint http://node-01:11434

# or the service id

python main.py --recipe recipes/clients/ollama_benchmark.yaml --target-service 98765
```

**Expected output:**
```
Client started: def67890
Monitor the job status through SLURM or check logs.
```

### Step 4: Monitor Progress

```bash
# Check both service and client status
python main.py --status
```

**Expected output:**
```
SLURM Job Status:
  Total Jobs: 2
  Services: 1
  Clients: 1
  Other: 0

Services:
    98765 |    ollama_abc12 |    RUNNING |  0:08:15 | node-01

Clients:
    98766 | ollama_bench_def |    RUNNING |  0:02:30 | node-02
```

### Step 5: View Results

Once the client job completes, you have multiple options for viewing results:

**Option A: Download to Local Machine (Recommended)**
```bash
# Download all benchmark results from cluster (from $HOME/results/)
python main.py --download-results

# Results are saved to ./results/ directory locally
ls -lh results/
cat results/redis_benchmark_*.json
```

**Option B: View Remotely via SSH**
```bash
# SSH to the HPC cluster
ssh meluxina

# View the benchmark results (formatted output in SLURM logs)
cat slurm-<CLIENT_JOB_ID>.out

# Or view detailed JSON results (if saved to $SCRATCH)
cat $SCRATCH/redis_benchmark_*.json
```

The SLURM log file contains formatted output with all benchmark results, making it easy to review performance metrics.

### Alternative: Using Service ID

If you prefer to use the service ID instead of manually specifying the endpoint:

```bash
# Step 1: Start service (same as above)
python main.py --recipe recipes/services/ollama.yaml

# Step 2: List running services to get the service ID
python main.py --list-running-services

# Step 3: Use the service ID to automatically resolve the endpoint
python main.py --recipe recipes/clients/ollama_benchmark.yaml --target-service abc12345
```

This approach automatically resolves the node IP and builds the endpoint for you.

### Debugging

For detailed debugging information, add `--verbose` to any command:

```bash
python main.py --verbose --recipe recipes/clients/ollama_benchmark.yaml --target-endpoint http://node-01:11434
```

This will show:
- Service host resolution details
- Generated SLURM script content
- Container command with endpoint arguments
- Detailed logging throughout the process

### Stopping Services

To stop a running service:

```bash
# Stop a specific service by job ID
python main.py --stop-service <JOB_ID>

# Stop all running services
python main.py --stop-all-services

# Example: Stop service with job ID 98765
python main.py --stop-service 98765
```

**Expected output:**
```
Successfully cancelled SLURM job: 98765
Service 98765 stopped.
```

**Note**: Stopping a service will cancel its SLURM job and free up the allocated resources. Any clients connected to that service will lose connectivity.

## 📁 Project Structure

```
team10_EUMASTER4HPC2526_challenge/
├── main.py                      # CLI entry point
├── config.yaml                  # Configuration file
├── requirements.txt             # Python dependencies
├── src/                         # Core modules
│   ├── orchestrator.py          # Main orchestrator engine
│   ├── servers.py               # Services management
│   ├── clients.py               # Benchmark clients
│   ├── ssh_client.py            # HPC SSH operations
│   ├── base.py                  # Base classes and enums
│   └── services/                # Service implementations
│       ├── __init__.py          # Service registry
│       ├── ollama.py            # Ollama service/client
│       ├── chroma.py            # Chroma service/client
│       ├── redis.py             # Redis service/client
│       └── prometheus.py        # Prometheus monitoring
├── recipes/                     # YAML recipe definitions
│   ├── services/                # Service templates
│   │   ├── ollama.yaml          # Ollama LLM service
│   │   ├── chroma.yaml          # Chroma vector DB
│   │   ├── redis.yaml           # Redis in-memory DB
│   │   └── prometheus_with_ollama.yaml
│   └── clients/                 # Client templates
│       ├── ollama_benchmark.yaml
│       ├── chroma_benchmark.yaml
│       └── redis_benchmark.yaml
├── benchmark_scripts/           # Benchmark implementation scripts
│   ├── ollama_benchmark.py      # Ollama benchmark client
│   ├── chroma_benchmark.py      # Chroma benchmark client
│   └── redis_benchmark.py       # Redis benchmark client
├── tests/                       # Test suite
├── docs/                        # Documentation
│   ├── API_DOCUMENTATION.md
│   ├── ARCHITECTURE_DOCUMENTATION.md
│   ├── CHROMA_INTEGRATION_GUIDE.md
│   ├── REDIS_INTEGRATION_GUIDE.md    # Redis detailed guide
│   └── REDIS_QUICK_REFERENCE.md      # Redis quick reference
└── examples/                    # Usage examples
```

## 🔧 Configuration

### HPC Connection

Configure your HPC cluster connection in `config.yaml`:

```yaml
hpc:
  hostname: "login.lxp.lu"
  username: "your_username"
  key_filename: "~/.ssh/id_ed25519_mlux"  # or use password
  port: 8822

slurm:
  account: "p200981"    ## id for the account (in this case, project id)
  partition: "gpu"
  qos: "default"
  time: "01:00:00"
```

### Container Images

Ensure your container images are available on the HPC cluster:

```yaml
containers:
  base_path: "/path/to/containers"
  images:
    ollama: "ollama_latest.sif"
    postgres: "postgres_latest.sif" 
    benchmark_client: "benchmark_client.sif"
```

## 📝 Recipe Format

### Complete Recipe Example

```yaml
# ollama_complete.yaml
apiVersion: v1
kind: BenchmarkRecipe
metadata:
  name: ollama-llm-benchmark
  description: End-to-end benchmark of Ollama LLM service

service:
  type: ollama
  name: ollama-server
  container_image: ollama_latest.sif
  command: ollama
  args: ["serve"]
  
  resources:
    gpu: 1
    memory: "16GB"
    slurm:
      partition: gpu
      time: "02:00:00"
  
  environment:
    OLLAMA_TLS_SKIP_VERIFY: "1"
    OLLAMA_HOST: "0.0.0.0:11434"

client:
  type: ollama_benchmark
  name: ollama-benchmark-client
  workload_type: ollama_benchmark
  duration: 300
  
  parameters:
    model: "llama2"
    num_requests: 50
    concurrent_requests: 5
    output_file: "/tmp/ollama_benchmark_results.json"
```

### Service-Only Recipe

```yaml
# service_only.yaml
service:
  type: ollama
  resources:
    gpu: 1
    memory: "16GB"
  environment:
    OLLAMA_HOST: "0.0.0.0:11434"
```

### Client-Only Recipe

```yaml
# client_only.yaml
client:
  type: ollama_benchmark
  duration: 300
  parameters:
    model: "llama2"
    num_requests: 100
```

## 🎯 Supported Services

### Ollama (LLM Inference)
- **Container**: `ollama_latest.sif`
- **Ports**: 11434
- **GPU**: Required
- **Models**: llama2, codellama, mistral, etc.

### MySQL (Database)
- **Container**: `mysql_latest.sif` 
- **Ports**: 3306
- **Resources**: CPU-focused
- **Features**: CRUD benchmarks, connection pooling, multi-threaded benchmarking

### PostgreSQL (Database)
- **Container**: `postgres_latest.sif` 
- **Ports**: 5432
- **Resources**: CPU-focused
- **Features**: CRUD benchmarks, connection pooling

### Chroma (Vector Database)
- **Container**: `chroma_latest.sif`
- **Ports**: 8000
- **Features**: Vector similarity search, embeddings

### Redis (In-Memory Database)
- **Container**: `redis_latest.sif`
- **Ports**: 6379
- **Resources**: CPU-focused
- **Features**: Key-value storage, caching, persistence (AOF/RDB)
- **Benchmarking**: Single-run and parametric sweep modes
- **Analysis**: Automated plot generation for performance visualization
- **Documentation**: [Redis Integration Guide](docs/REDIS_INTEGRATION_GUIDE.md), [Quick Reference](docs/REDIS_QUICK_REFERENCE.md)

## 🧪 Benchmark Clients

### Ollama Benchmark
- **Metrics**: Latency, throughput, tokens/sec
- **Parameters**: Model, requests, concurrency
- **Output**: JSON results with statistics

### MySQL Benchmark
- **Metrics**: CRUD performance, transaction throughput, latency
- **Parameters**: Concurrent connections, transactions per client
- **Workloads**: Mixed read/write operations, multi-threaded clients

### PostgreSQL Benchmark
- **Metrics**: CRUD performance, connection handling
- **Parameters**: Connections, transactions, table size
- **Workloads**: Read/write patterns, stress tests

### Vector Database Benchmark
- **Metrics**: Search latency, indexing performance
- **Parameters**: Vector dimensions, collection size
- **Workloads**: Similarity search, bulk operations

### Redis Benchmark
- **Modes**: Single-run (quick tests) and Parametric (comprehensive sweeps)
- **Metrics**: Operations per second (SET/GET/LPUSH/SADD/etc.), latency distribution (P50/P95/P99)
- **Parameters**: Client counts (1-500), data sizes (64B-64KB), pipeline depths (1-256)
- **Parametric Sweep**: Automatically tests all parameter combinations
- **Analysis**: Generates 6 performance plots (throughput, latency, heatmaps, comparisons)
- **Automation**: One-command workflow via `scripts/run_redis_parametric.sh`
- **Output**: JSON results with comprehensive performance data

## 🎛️ Service Management

### Starting Services

```bash
# Start a service using a recipe
python main.py --recipe recipes/services/ollama.yaml
python main.py --recipe recipes/services/redis.yaml
python main.py --recipe recipes/services/chroma.yaml

# Expected output: Service started: <SERVICE_ID>
```

### Monitoring Services

```bash
# Check status of all running jobs
python main.py --status

# List available service types
python main.py --list-services

# List available client types
python main.py --list-clients
```

### Stopping Services

```bash
# Stop a specific service by job ID
python main.py --stop-service <JOB_ID>

# Stop all running services at once
python main.py --stop-all-services
```

**Example workflow:**
```bash
# 1. Start Redis service
python main.py --recipe recipes/services/redis.yaml
# Output: Service started: 3656857

# 2. Check it's running
python main.py --status
# Output: 3656857 | redis_abc123 | RUNNING | 0:01:30 | mel0182

# 3. Stop the service when done
python main.py --stop-service 3656857
# Output: Successfully cancelled SLURM job: 3656857
```

## 📊 Monitoring & Results

### Status Monitoring (CLI)

```bash
# Check running services and clients
python main.py --status

# Verbose status with detailed information
python main.py --verbose --status
```

### Status Monitoring (Programmatic)

```python
# Check running services
status = interface.show_servers_status()

# Check benchmark clients
clients = interface.show_clients_status()

# System overview
system = interface.get_system_status()
```

### Results Collection

Results are automatically collected in JSON format in the results directory of the login node:

```json
{
  "benchmark_config": {
    "model": "llama2",
    "num_requests": 50,
    "concurrent_requests": 5
  },
  "results": {
    "success_rate": 98.0,
    "latency_stats": {
      "mean": 1.23,
      "p95": 2.45,
      "p99": 3.67
    },
    "throughput": {
      "tokens_per_second": 150.5,
      "requests_per_second": 12.3
    }
  }
}
```

## 🔌 Extending the Framework

### Adding New Services

1. Create service definition in `recipes/services/`:

```yaml
# recipes/services/my_service.yaml
name: my_service
container_image: my_service.sif
command: my_service_command
resources:
  memory: "8GB"
environment:
  SERVICE_PORT: "8080"
ports:
  - 8080
```

2. Add service-specific setup in `script_generator.py`:

```python
def _generate_my_service_setup(self) -> List[str]:
    return [
        "# My service setup",
        "export MY_SERVICE_CONFIG=production",
        ""
    ]
```

### Adding New Benchmark Clients

1. Create client definition in `recipes/clients/`:

```yaml
# recipes/clients/my_benchmark.yaml
name: my_benchmark
workload_type: my_benchmark
parameters:
  duration: 300
  connections: 10
```

2. Implement benchmark script in `benchmark_scripts/`:

```python
# benchmark_scripts/my_benchmark.py
class MyBenchmark:
    def run_benchmark(self, **params):
        # Implementation
        pass
```

## 🐛 Troubleshooting

### Common Issues

1. **SSH Connection Failed**
   - Check hostname, username, and SSH key
   - Verify HPC cluster connectivity
   - Test manual SSH connection

2. **Job Submission Failed**
   - Verify SLURM account and partition
   - Check resource requirements
   - Review cluster queue status

3. **Container Not Found**
   - Ensure container images are on HPC cluster
   - Check container paths in config
   - Verify Apptainer module is loaded

### Debug Mode

```bash
# Enable verbose logging
python main.py --verbose --recipe recipes/ollama_complete.yaml

# Check generated scripts
ls scripts/
cat scripts/service_*.sh
```

### Manual Testing

```bash
# Test recipe loading
python -c "
from src.orchestrator import BenchmarkOrchestrator
interface = BenchmarkOrchestrator()
recipe = interface.load_recipe('recipes/ollama_complete.yaml')
print(recipe)
"

# Test SSH connection
python -c "
from src.ssh_client import SSHClient
client = SSHClient('login.lxp.lu', 'username')
print(client.connect())
"
```

## 📈 Performance Considerations

### Resource Allocation

- **GPU Services**: Use `partition: gpu` with appropriate `gres`
- **Memory**: Allocate sufficient memory for models
- **Time Limits**: Set realistic job time limits
- **Concurrency**: Balance concurrent requests vs. resource limits

### Optimization Tips

- Pre-pull models to reduce startup time
- Use persistent storage for large datasets
- Monitor cluster utilization
- Batch multiple benchmarks efficiently

## 🤝 Contributing

1. **Fork** the repository
2. **Create** a feature branch
3. **Add** tests for new functionality  
4. **Submit** a pull request

### Development Setup

```bash
# Install development dependencies
pip install -r requirements.txt
pip install pytest black flake8

# Run tests
pytest

# Format code
black src/
flake8 src/
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Documentation**: Check this README and inline code comments
- **Issues**: Report bugs via GitHub issues
- **Discussions**: Use GitHub discussions for questions

---

*Built for the EU Master in HPC Challenge 2025-2026*