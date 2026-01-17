# Adding New Services

Step-by-step guide for integrating a new service into the orchestrator.

## Prerequisites

Before adding a new service, ensure you have:

1. A Docker image for the service
2. Understanding of the service's configuration
3. Knowledge of exposed ports and protocols

## Step-by-Step Guide

### Step 1: Prepare Container Image

```bash
# On MeluXina
module load Apptainer/1.2.4-GCCcore-12.3.0
cd $HOME/containers

# Pull from Docker Hub
apptainer pull my_service.sif docker://myorg/myservice:latest

# Or build from definition file
apptainer build my_service.sif my_service.def
```

### Step 2: Create Service Class

Create `src/services/my_service.py`:

```python
"""
MyService - Description of what this service does
"""
from typing import List
from .base import Service
from ..base import JobFactory


class MyService(Service):
    """
    MyService implementation for HPC deployment.
    
    Attributes:
        port: Service port (default: 8080)
        config_option: Custom configuration option
    """
    
    def __init__(self, config: dict):
        super().__init__(config)
        
        # Extract configuration
        service_config = config.get('service', config)
        self.port = service_config.get('ports', [8080])[0]
        self.config_option = service_config.get('config_option', 'default')
        
        # Data directories
        self.data_dir = f"$HOME/my_service/{self.job_id}/data"
        self.log_dir = f"$HOME/my_service/{self.job_id}/logs"
    
    def get_service_setup_commands(self) -> List[str]:
        """
        Setup commands executed before container starts.
        
        Returns:
            List of bash commands for setup
        """
        commands = super().get_service_setup_commands()
        commands.extend([
            "",
            "# MyService setup",
            f"export MY_SERVICE_PORT={self.port}",
            f"export MY_SERVICE_CONFIG={self.config_option}",
            "",
            "# Create directories",
            f"mkdir -p {self.data_dir}",
            f"mkdir -p {self.log_dir}",
            "",
            "# Download any required files",
            "# curl -o $HOME/my_service/config.yaml https://example.com/config.yaml",
        ])
        return commands
    
    def get_container_command(self) -> str:
        """
        Generate Apptainer execution command.
        
        Returns:
            Apptainer exec command string
        """
        container_path = self._resolve_container_path()
        
        cmd_parts = ["apptainer exec"]
        
        # GPU support
        if self._needs_gpu():
            cmd_parts.append("--nv")
        
        # Bind mounts
        cmd_parts.extend([
            f"--bind {self.data_dir}:/data",
            f"--bind {self.log_dir}:/logs",
        ])
        
        # Environment variables
        for key, value in self.environment.items():
            cmd_parts.append(f"--env {key}={value}")
        
        # Container and command
        cmd_parts.extend([
            container_path,
            f"my_service_binary --port {self.port} --config /data/config.yaml",
            "&"  # Background
        ])
        
        return " \\\n    ".join(cmd_parts)
    
    def get_health_check_commands(self) -> List[str]:
        """
        Health check commands to verify service is running.
        
        Returns:
            List of bash commands for health checking
        """
        return [
            "",
            "# Wait for MyService to initialize",
            "sleep 15",
            "",
            "# Health check loop",
            "for i in {1..10}; do",
            f"    if curl -s http://localhost:{self.port}/health | grep -q 'ok'; then",
            "        echo 'MyService is healthy!'",
            "        break",
            "    fi",
            "    echo \"Waiting for MyService... ($i/10)\"",
            "    sleep 5",
            "done",
            "",
            "# Display endpoint",
            "echo '========================================='",
            "echo 'MyService is running on:'",
            f"echo \"http://$(hostname):{self.port}\"",
            "echo '========================================='",
            "",
            "# Keep process alive",
            "wait",
        ]
    
    def _needs_gpu(self) -> bool:
        """Check if service needs GPU"""
        return 'gpu' in str(self.resources.get('gres', '')).lower()


# Register with factory
JobFactory.register_service('my_service', MyService)
```

### Step 3: Register Service

Add to `src/services/__init__.py`:

```python
from .my_service import MyService

__all__ = [
    'OllamaService',
    'RedisService',
    # ... other services
    'MyService',  # Add this
]
```

### Step 4: Create Service Recipe

Create `recipes/services/my_service.yaml`:

```yaml
service:
  name: my_service
  description: "MyService - What it does"
  
  container:
    docker_source: docker://myorg/myservice:latest
    image_path: $HOME/containers/my_service.sif
  
  # Service-specific options
  config_option: "production"
  
  # SLURM resources
  resources:
    nodes: 1
    ntasks: 1
    cpus_per_task: 4
    mem: "8G"
    time: "02:00:00"
    partition: cpu
    qos: default
  
  # Environment variables
  environment:
    MY_SERVICE_LOG_LEVEL: "info"
    MY_SERVICE_MAX_CONNECTIONS: "100"
  
  # Exposed ports
  ports:
    - 8080
```

### Step 5: Create Monitoring Recipe (Optional)

Create `recipes/services/my_service_with_cadvisor.yaml`:

```yaml
service:
  name: my_service
  description: "MyService with monitoring"
  
  container:
    docker_source: docker://myorg/myservice:latest
    image_path: $HOME/containers/my_service.sif
  
  config_option: "production"
  
  resources:
    cpus_per_task: 4
    mem: "8G"
    time: "02:00:00"
    partition: cpu
  
  environment:
    MY_SERVICE_LOG_LEVEL: "info"
  
  ports:
    - 8080
  
  # Enable monitoring
  enable_cadvisor: true
  cadvisor_port: 8081
```

### Step 6: Test the Service

```bash
# Verbose mode to see generated script
python main.py --verbose --recipe recipes/services/my_service.yaml

# Check status
python main.py --status

# View generated script
cat scripts/service_my_service_*.sh

# Stop service
python main.py --stop-service my_service_xxx
```

## Adding a Benchmark Client

### Step 1: Create Client Class

Create `src/services/my_service.py` (add to existing file):

```python
class MyServiceBenchmarkClient(Client):
    """Benchmark client for MyService"""
    
    def __init__(self, config: dict):
        super().__init__(config)
        params = config.get('parameters', {})
        self.requests = params.get('requests', 1000)
        self.concurrent = params.get('concurrent', 10)
        self.duration = params.get('duration', 60)
        self.output_file = params.get('output_file', '$HOME/results/my_service_bench.json')
    
    def get_benchmark_commands(self) -> List[str]:
        return [
            "",
            "# MyService Benchmark",
            f"echo 'Benchmarking {self.target_endpoint}'",
            f"echo 'Requests: {self.requests}, Concurrent: {self.concurrent}'",
            "",
            f"python3 benchmark_scripts/my_service_benchmark.py \\",
            f"    --endpoint {self.target_endpoint} \\",
            f"    --requests {self.requests} \\",
            f"    --concurrent {self.concurrent} \\",
            f"    --duration {self.duration} \\",
            f"    --output {self.output_file}",
            "",
            f"echo 'Benchmark complete. Results: {self.output_file}'",
        ]


# Register client
JobFactory.register_client('my_service_benchmark', MyServiceBenchmarkClient)
```

### Step 2: Create Client Recipe

Create `recipes/clients/my_service_benchmark.yaml`:

```yaml
client:
  name: my_service_benchmark
  type: my_service_benchmark
  description: "Performance benchmark for MyService"
  
  parameters:
    requests: 10000
    concurrent: 50
    duration: 120
    output_file: "$HOME/results/my_service_benchmark.json"
  
  resources:
    cpus_per_task: 4
    mem: "4G"
    time: "00:30:00"
    partition: cpu
```

### Step 3: Create Benchmark Script

Create `benchmark_scripts/my_service_benchmark.py`:

```python
#!/usr/bin/env python3
"""MyService benchmark implementation"""
import argparse
import json
import time
import statistics
from concurrent.futures import ThreadPoolExecutor
import requests

def benchmark_request(endpoint):
    """Single benchmark request"""
    start = time.time()
    try:
        resp = requests.get(f"{endpoint}/api/test", timeout=30)
        return {
            'success': resp.status_code == 200,
            'latency': time.time() - start,
            'status': resp.status_code
        }
    except Exception as e:
        return {
            'success': False,
            'latency': time.time() - start,
            'error': str(e)
        }

def main():
    parser = argparse.ArgumentParser(description='MyService Benchmark')
    parser.add_argument('--endpoint', required=True)
    parser.add_argument('--requests', type=int, default=1000)
    parser.add_argument('--concurrent', type=int, default=10)
    parser.add_argument('--duration', type=int, default=60)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    
    print(f"Starting benchmark against {args.endpoint}")
    print(f"Requests: {args.requests}, Concurrent: {args.concurrent}")
    
    start_time = time.time()
    results = []
    
    with ThreadPoolExecutor(max_workers=args.concurrent) as executor:
        futures = [
            executor.submit(benchmark_request, args.endpoint)
            for _ in range(args.requests)
        ]
        results = [f.result() for f in futures]
    
    total_time = time.time() - start_time
    
    # Calculate statistics
    successful = [r for r in results if r['success']]
    latencies = [r['latency'] for r in successful]
    
    output = {
        'benchmark': 'my_service_benchmark',
        'endpoint': args.endpoint,
        'config': {
            'requests': args.requests,
            'concurrent': args.concurrent
        },
        'results': {
            'total_requests': len(results),
            'successful': len(successful),
            'failed': len(results) - len(successful),
            'success_rate': len(successful) / len(results) * 100,
            'total_duration': total_time,
            'requests_per_second': len(results) / total_time,
        },
        'latency': {
            'mean': statistics.mean(latencies) if latencies else 0,
            'median': statistics.median(latencies) if latencies else 0,
            'stdev': statistics.stdev(latencies) if len(latencies) > 1 else 0,
            'min': min(latencies) if latencies else 0,
            'max': max(latencies) if latencies else 0,
            'p95': sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0,
            'p99': sorted(latencies)[int(len(latencies) * 0.99)] if latencies else 0,
        }
    }
    
    # Save results
    with open(args.output, 'w') as f:
        json.dump(output, f, indent=2)
    
    # Print summary
    print("\n" + "="*50)
    print("BENCHMARK RESULTS")
    print("="*50)
    print(f"Success Rate: {output['results']['success_rate']:.2f}%")
    print(f"Throughput: {output['results']['requests_per_second']:.2f} req/s")
    print(f"Latency (mean): {output['latency']['mean']*1000:.2f} ms")
    print(f"Latency (p99): {output['latency']['p99']*1000:.2f} ms")
    print(f"Results saved to: {args.output}")

if __name__ == '__main__':
    main()
```

### Step 4: Test Client

```bash
# Start service
python main.py --recipe recipes/services/my_service.yaml

# Run benchmark
python main.py --recipe recipes/clients/my_service_benchmark.yaml --target-service my_service_xxx

# Download results
python main.py --download-results
```

## Checklist

- [ ] Container image available on MeluXina
- [ ] Service class created in `src/services/`
- [ ] Service registered in `__init__.py`
- [ ] Service recipe created
- [ ] Service recipe with cAdvisor created (optional)
- [ ] Client class created (optional)
- [ ] Benchmark script created (optional)
- [ ] Client recipe created (optional)
- [ ] Documentation updated

---

See also: [Extending the Framework](extending.md) | [Recipes Overview](../recipes/overview.md)
