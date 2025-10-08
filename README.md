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
```

## 📋 Usage Examples

### Command Line Interface

```bash
# List available services
python main.py --list-services

# Run a specific recipe
python main.py --recipe recipes/ollama_complete.yaml

# Interactive mode
python main.py

# Verbose logging
python main.py --verbose --recipe recipes/postgresql_complete.yaml
```

### Programmatic Usage

```python
from src.orchestrator import BenchmarkOrchestrator

# Initialize orchestrator
interface = BenchmarkOrchestrator('config.yaml')

# Load and run a recipe
recipe = interface.load_recipe('recipes/ollama_complete.yaml')
session_id = interface.start_benchmark_session(recipe)

# Monitor status
status = interface.show_servers_status()
print(f"Running services: {status}")

# Generate report
interface.generate_report(session_id, 'results/report.yaml')
```

## 📁 Project Structure

```
team10_EUMASTER4HPC2526_challenge/
├── main.py                 # CLI entry point
├── config.yaml            # Configuration file
├── requirements.txt        # Python dependencies
├── src/                    # Core modules
│   ├── orchestrator.py     # Main orchestrator engine
│   ├── servers.py          # Services management
│   ├── clients.py          # Benchmark clients
│   ├── ssh_client.py       # HPC SSH operations
│   ├── script_generator.py # SLURM script generation
│   └── base.py             # Base classes and enums
├── recipes/                # YAML recipe definitions
│   ├── services/           # Service templates
│   │   └── ollama.yaml     # Ollama LLM service
│   └── clients/            # Client templates
│       └── ollama_benchmark.yaml
├── benchmark_scripts/      # Benchmark implementation scripts
│   └── ollama_benchmark.py # Ollama benchmark client
├── tests/                  # Test suite
├── docs/                   # Documentation
└── examples/              # Usage examples
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

### PostgreSQL (Database)
- **Container**: `postgres_latest.sif` 
- **Ports**: 5432
- **Resources**: CPU-focused
- **Features**: CRUD benchmarks, connection pooling

### Chroma (Vector Database)
- **Container**: `chroma_latest.sif`
- **Ports**: 8000
- **Features**: Vector similarity search, embeddings

## 🧪 Benchmark Clients

### Ollama Benchmark
- **Metrics**: Latency, throughput, tokens/sec
- **Parameters**: Model, requests, concurrency
- **Output**: JSON results with statistics

### PostgreSQL Benchmark
- **Metrics**: CRUD performance, connection handling
- **Parameters**: Connections, transactions, table size
- **Workloads**: Read/write patterns, stress tests

### Vector Database Benchmark
- **Metrics**: Search latency, indexing performance
- **Parameters**: Vector dimensions, collection size
- **Workloads**: Similarity search, bulk operations

## 📊 Monitoring & Results

### Status Monitoring

```python
# Check running services
status = interface.show_servers_status()

# Check benchmark clients
clients = interface.show_clients_status()

# System overview
system = interface.get_system_status()
```

### Results Collection

Results are automatically collected in JSON format:

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