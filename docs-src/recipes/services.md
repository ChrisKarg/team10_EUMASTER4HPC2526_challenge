# Service Recipes

Service recipes define how AI and database services are deployed on the HPC cluster.

## Available Service Recipes

| Recipe | Service | GPU | Monitoring |
|--------|---------|-----|------------|
| `ollama.yaml` | Ollama LLM | Yes | No |
| `ollama_with_cadvisor.yaml` | Ollama LLM | Yes | Yes |
| `redis.yaml` | Redis | No | No |
| `redis_with_cadvisor.yaml` | Redis | No | Yes |
| `chroma.yaml` | Chroma | No | No |
| `chroma_with_cadvisor.yaml` | Chroma | No | Yes |
| `mysql.yaml` | MySQL | No | No |
| `mysql_with_cadvisor.yaml` | MySQL | No | Yes |
| `prometheus_with_cadvisor.yaml` | Prometheus | No | Yes |
| `grafana.yaml` | Grafana | No | No |

## Recipe Fields Reference

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Unique service identifier |
| `container.docker_source` | string | Docker image source |
| `container.image_path` | string | Local SIF path |

### Resource Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `resources.nodes` | int | 1 | Number of nodes |
| `resources.ntasks` | int | 1 | Number of tasks |
| `resources.cpus_per_task` | int | 1 | CPUs per task |
| `resources.mem` | string | "4G" | Memory allocation |
| `resources.time` | string | "01:00:00" | Time limit |
| `resources.partition` | string | "cpu" | SLURM partition |
| `resources.qos` | string | "default" | Quality of service |
| `resources.gres` | string | - | GPU resources |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `description` | string | Human-readable description |
| `environment` | dict | Environment variables |
| `ports` | list | Exposed ports |
| `enable_cadvisor` | bool | Enable monitoring |
| `cadvisor_port` | int | cAdvisor port (default: 8080) |
| `command` | string | Override container command |
| `args` | list | Command arguments |

## Example: Ollama Service

```yaml
# recipes/services/ollama.yaml
service:
  name: ollama
  description: "Ollama LLM inference server with GPU acceleration"
  
  container:
    docker_source: docker://ollama/ollama:latest
    image_path: $HOME/containers/ollama_latest.sif
  
  resources:
    nodes: 1
    ntasks: 1
    cpus_per_task: 4
    mem: "32G"
    time: "04:00:00"
    partition: gpu
    qos: default
    gres: "gpu:1"
  
  environment:
    OLLAMA_HOST: "0.0.0.0:11434"
    OLLAMA_MODELS: "$HOME/.ollama/models"
    OLLAMA_NUM_PARALLEL: "4"
    OLLAMA_KEEP_ALIVE: "5m"
  
  ports:
    - 11434
```

## Example: Redis with Monitoring

```yaml
# recipes/services/redis_with_cadvisor.yaml
service:
  name: redis
  description: "Redis in-memory database with cAdvisor monitoring"
  
  container:
    docker_source: docker://redis:latest
    image_path: $HOME/containers/redis_latest.sif
  
  resources:
    nodes: 1
    cpus_per_task: 4
    mem: "8G"
    time: "02:00:00"
    partition: cpu
  
  environment:
    REDIS_PORT: "6379"
    REDIS_BIND: "0.0.0.0"
  
  ports:
    - 6379
  
  # Enable cAdvisor sidecar
  enable_cadvisor: true
  cadvisor_port: 8080
```

## Example: Prometheus

```yaml
# recipes/services/prometheus_with_cadvisor.yaml
service:
  name: prometheus
  description: "Prometheus metrics collection"
  
  container:
    docker_source: docker://prom/prometheus:latest
    image_path: $HOME/containers/prometheus.sif
  
  # Services to monitor (resolved at runtime)
  monitoring_targets:
    - service_id: "ollama_abc123"
      job_name: "ollama-cadvisor"
      port: 8080
    - service_id: "redis_xyz789"
      job_name: "redis-cadvisor"
      port: 8080
  
  resources:
    cpus_per_task: 2
    mem: "4G"
    time: "02:00:00"
    partition: cpu
  
  environment:
    PROMETHEUS_RETENTION_TIME: "15d"
  
  ports:
    - 9090
```

## Using Service Recipes

```bash
# Basic usage
python main.py --recipe recipes/services/ollama.yaml

# With verbose output
python main.py --verbose --recipe recipes/services/redis.yaml

# Check what's running
python main.py --status
```

## Generated SLURM Script

A service recipe generates a SLURM script like:

```bash
#!/bin/bash
#SBATCH --job-name=ollama_a1b2c3d4
#SBATCH --account=p200981
#SBATCH --partition=gpu
#SBATCH --qos=default
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --gres=gpu:1
#SBATCH --output=slurm-%j.out
#SBATCH --error=slurm-%j.err

module purge
module load Apptainer/1.2.4-GCCcore-12.3.0

# Service setup
export OLLAMA_HOST=0.0.0.0:11434
export OLLAMA_MODELS=$HOME/.ollama/models
mkdir -p $HOME/.ollama/models

# Container execution
apptainer exec --nv \
    --bind $HOME/.ollama:/root/.ollama \
    $HOME/containers/ollama_latest.sif \
    ollama serve &

# Health check
sleep 10
curl -s http://localhost:11434/api/tags

wait
```

---

Next: [Client Recipes](clients.md) | [Writing Custom Recipes](custom.md)
