# System Architecture

## Overview

The HPC AI Benchmarking Orchestrator uses a **modular architecture** designed for flexibility, extensibility, and seamless HPC integration. The system orchestrates containerized AI workloads through SLURM, providing automated deployment, monitoring, and benchmarking capabilities.

## High-Level Architecture

```mermaid
flowchart TB
    subgraph Local["Local Machine"]
        direction LR
        CLI[main.py] ~~~ Config[config.yaml] ~~~ Recipes[Recipes]
    end
    
    subgraph Framework["Core Framework"]
        direction TB
        Orch[Orchestrator]
        subgraph Modules["Modules"]
            direction LR
            Srv[Servers] ~~~ Cli[Clients] ~~~ Mon[Monitors]
        end
        Orch --> Modules
        Modules --> Factory[Factory]
        Factory --> SSH[SSH]
    end
    
    subgraph HPC["MeluXina HPC"]
        direction LR
        SLURM[SLURM] --> Compute[Compute] --> Containers[Apptainer]
    end
    
    subgraph Services["Deployed Services"]
        direction LR
        Ollama[Ollama] ~~~ Redis[Redis] ~~~ Chroma[Chroma] ~~~ MySQL[MySQL]
    end
    
    subgraph Monitoring["Monitoring Stack"]
        direction LR
        cAdvisor[cAdvisor] --> Prometheus[Prometheus] --> Grafana[Grafana]
    end
    
    Local --> Framework
    Framework --> HPC
    HPC --> Services
    HPC --> Monitoring
    
    style CLI fill:#1976D2,color:#fff
    style Config fill:#1976D2,color:#fff
    style Recipes fill:#1976D2,color:#fff
    style Orch fill:#388E3C,color:#fff
    style Srv fill:#388E3C,color:#fff
    style Cli fill:#388E3C,color:#fff
    style Mon fill:#388E3C,color:#fff
    style Factory fill:#F57C00,color:#fff
    style SSH fill:#455A64,color:#fff
    style SLURM fill:#7B1FA2,color:#fff
    style Compute fill:#7B1FA2,color:#fff
    style Containers fill:#7B1FA2,color:#fff
    style Ollama fill:#0288D1,color:#fff
    style Redis fill:#D32F2F,color:#fff
    style Chroma fill:#689F38,color:#fff
    style MySQL fill:#1565C0,color:#fff
    style cAdvisor fill:#7B1FA2,color:#fff
    style Prometheus fill:#E64A19,color:#fff
    style Grafana fill:#F57C00,color:#fff
```

## Core Components

### 1. CLI Interface (`main.py`)

The command-line interface provides the primary user interaction point.

**Responsibilities:**

- Parse command-line arguments
- Load and validate configuration
- Route commands to appropriate modules
- Display status and results

### 2. BenchmarkOrchestrator

The central coordination hub managing all operations.

```mermaid
classDiagram
    class BenchmarkOrchestrator {
        +config: dict
        +ssh_client: SSHClient
        +servers: ServersModule
        +clients: ClientsModule
        +monitors: MonitorsModule
        +load_recipe(path) Recipe
        +start_service(recipe) str
        +start_client(recipe, target) str
        +stop_service(service_id) bool
        +show_status() dict
    }
    
    class ServersModule {
        +start_service(recipe) ServiceInfo
        +stop_service(service_id) bool
        +list_services() list
        +get_service_host(service_id) str
    }
    
    class ClientsModule {
        +start_client(recipe, target) ClientInfo
        +list_clients() list
    }
    
    class MonitorsModule {
        +start_monitor(recipe) MonitorInfo
        +query_metrics(query) dict
    }
    
    BenchmarkOrchestrator --> ServersModule
    BenchmarkOrchestrator --> ClientsModule
    BenchmarkOrchestrator --> MonitorsModule
```

### 3. Job Factory & Service Classes

The Factory pattern enables extensible service/client creation.

```mermaid
classDiagram
    class JobFactory {
        +_services: dict
        +_clients: dict
        +register_service(name, cls)
        +register_client(name, cls)
        +create_service(recipe) Service
        +create_client(recipe) Client
    }
    
    class BaseJob {
        <<abstract>>
        +name: str
        +job_id: str
        +generate_slurm_script() str
        +get_setup_commands() list
        +get_container_command() str
    }
    
    class Service {
        +ports: list
        +enable_cadvisor: bool
        +get_service_setup_commands() list
    }
    
    class Client {
        +target_endpoint: str
        +get_benchmark_commands() list
    }
    
    class OllamaService {
        +model: str
        +get_model_pull_commands() list
    }
    
    class RedisService {
        +persistence: str
        +get_redis_config() list
    }
    
    BaseJob <|-- Service
    BaseJob <|-- Client
    Service <|-- OllamaService
    Service <|-- RedisService
    Service <|-- ChromaService
    Service <|-- MySQLService
    Service <|-- PrometheusService
    Service <|-- GrafanaService
    JobFactory ..> BaseJob : creates
```

### 4. SSH Client

Handles all remote HPC operations securely.

**Operations:**

- Command execution via SSH
- File transfer (upload/download)
- Job submission (`sbatch`)
- Job management (`squeue`, `scancel`)

### 5. SLURM Integration

Jobs are submitted as SLURM batch scripts with:

- Resource allocation (CPU, GPU, memory, time)
- Module loading (Apptainer)
- Container execution
- Output logging

## Data Flow

### Service Deployment Flow

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant Orchestrator
    participant Factory
    participant SSH
    participant SLURM
    participant Container
    
    User->>CLI: --recipe service.yaml
    CLI->>Orchestrator: start_service(recipe)
    Orchestrator->>Factory: create_service(recipe)
    Factory-->>Orchestrator: ServiceInstance
    Orchestrator->>SSH: submit_job(script)
    SSH->>SLURM: sbatch script.sh
    SLURM->>Container: allocate & run
    Container-->>SLURM: running on node
    SLURM-->>SSH: job_id, node
    SSH-->>Orchestrator: ServiceInfo
    Orchestrator-->>CLI: service_id
    CLI-->>User: "Service started: abc123"
```

### Metrics Collection Flow

```mermaid
sequenceDiagram
    participant Service as Service Container
    participant cAdvisor
    participant Prometheus
    participant Grafana
    participant User
    
    loop Every 15s
        cAdvisor->>Service: Collect container metrics
        Service-->>cAdvisor: CPU, Memory, Network, Disk
        Prometheus->>cAdvisor: Scrape /metrics
        cAdvisor-->>Prometheus: Metrics data
    end
    
    User->>Grafana: Open dashboard
    Grafana->>Prometheus: PromQL query
    Prometheus-->>Grafana: Time series data
    Grafana-->>User: Visualizations
```

## Design Patterns

### Factory Pattern

Used for creating services and clients from YAML recipes:

```python
# Registration
JobFactory.register_service('ollama', OllamaService)
JobFactory.register_client('ollama_benchmark', OllamaBenchmarkClient)

# Creation
service = JobFactory.create_service(recipe)  # Returns OllamaService
client = JobFactory.create_client(recipe)    # Returns OllamaBenchmarkClient
```

### Template Method Pattern

Base classes define the structure, subclasses customize behavior:

```python
class BaseJob:
    def generate_slurm_script(self):
        script = []
        script.extend(self._generate_header())      # Template
        script.extend(self.get_setup_commands())    # Hook - override in subclass
        script.extend(self._generate_execution())   # Template
        return '\n'.join(script)
```

### Strategy Pattern

Different services implement different setup strategies:

```python
class OllamaService(Service):
    def get_setup_commands(self):
        return ["export OLLAMA_HOST=0.0.0.0:11434", ...]

class RedisService(Service):
    def get_setup_commands(self):
        return ["redis-server --bind 0.0.0.0", ...]
```

## File Organization

```
src/
├── orchestrator.py      # BenchmarkOrchestrator
├── servers.py           # ServersModule
├── clients.py           # ClientsModule
├── monitors.py          # MonitorsModule
├── ssh_client.py        # SSHClient
├── base.py              # BaseJob, enums, utilities
└── services/
    ├── __init__.py      # JobFactory registration
    ├── base.py          # Service/Client base classes
    ├── ollama.py        # OllamaService, OllamaClient
    ├── redis.py         # RedisService, RedisClient
    ├── chroma.py        # ChromaService, ChromaClient
    ├── mysql.py         # MySQLService, MySQLClient
    ├── prometheus.py    # PrometheusService
    └── grafana.py       # GrafanaService
```

---

Next: [Job Hierarchy](jobs.md) | [Services](../services/overview.md)
