# HPC AI Benchmarking Orchestrator

Welcome to the HPC AI Benchmarking Orchestrator documentation.

## Overview

A modular Python orchestrator for running containerized AI benchmarking workloads on HPC clusters via SLURM. This framework enables automated deployment, benchmarking, and monitoring of AI services including LLM inference servers, vector databases, in-memory stores, and relational databases on the **MeluXina supercomputer**.

## Architecture

```mermaid
flowchart TB
    subgraph Local["Local Machine"]
        direction LR
        CLI[main.py] ~~~ Config[config.yaml]
    end
    
    subgraph Framework["Orchestrator Framework"]
        direction TB
        Orch[Orchestrator]
        subgraph Modules["Modules"]
            direction LR
            Srv[Servers] ~~~ Cli[Clients] ~~~ Mon[Monitors]
        end
        Orch --> Modules
        Modules --> SSH[SSHClient]
    end
    
    subgraph HPC["MeluXina HPC"]
        direction TB
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
    style Orch fill:#388E3C,color:#fff
    style Srv fill:#388E3C,color:#fff
    style Cli fill:#388E3C,color:#fff
    style Mon fill:#388E3C,color:#fff
    style SSH fill:#455A64,color:#fff
    style SLURM fill:#F57C00,color:#fff
    style Compute fill:#F57C00,color:#fff
    style Containers fill:#F57C00,color:#fff
    style Ollama fill:#0288D1,color:#fff
    style Redis fill:#D32F2F,color:#fff
    style Chroma fill:#689F38,color:#fff
    style MySQL fill:#1565C0,color:#fff
    style cAdvisor fill:#7B1FA2,color:#fff
    style Prometheus fill:#E64A19,color:#fff
    style Grafana fill:#F57C00,color:#fff
```

## Supported Services

| Service | Type | Port | Description |
|---------|------|------|-------------|
| **Ollama** | LLM Inference | 11434 | High-performance LLM inference server |
| **Redis** | In-Memory DB | 6379 | Key-value store with persistence |
| **Chroma** | Vector DB | 8000 | Vector similarity search |
| **MySQL** | RDBMS | 3306 | Relational database |
| **Prometheus** | Monitoring | 9090 | Metrics collection |
| **Grafana** | Visualization | 3000 | Real-time dashboards |

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Start an Ollama service
python main.py --recipe recipes/services/ollama.yaml

# Check status
python main.py --status

# Run benchmark client
python main.py --recipe recipes/clients/ollama_benchmark.yaml --target-service <SERVICE_ID>

# View results in Grafana (after SSH tunnel)
open http://localhost:3000
```

## Documentation

| | |
|---|---|
| :rocket: **[Getting Started](getting-started/overview.md)** | Setup, installation, and your first benchmark |
| :building_construction: **[Architecture](architecture/overview.md)** | System design, components, and data flow |
| :gear: **[Services](services/overview.md)** | Ollama, Redis, Chroma, MySQL configuration |
| :computer: **[CLI Reference](cli/commands.md)** | Complete command-line interface documentation |
| :page_facing_up: **[Recipes](recipes/overview.md)** | YAML configuration for services and clients |
| :chart_with_upwards_trend: **[Monitoring](monitoring/overview.md)** | Grafana dashboards and Prometheus metrics |

## Key Features

- **YAML-based Configuration**: Define services and benchmarks declaratively
- **Multi-Service Support**: Ollama, Redis, Chroma, MySQL, and more
- **Automated SLURM Integration**: Seamless job submission and management
- **Real-time Monitoring**: Grafana dashboards with cAdvisor metrics
- **Parametric Benchmarking**: Sweep across multiple configurations
- **SSH Tunneling**: Secure access to HPC services

## Project Status

**Version**: 1.0.0  
**Last Updated**: January 2026  
**Project**: EUMaster4HPC Challenge 2025-2026  
**Supervisor**: Dr. Farouk Mansouri  
**Platform**: MeluXina Supercomputer

---

*Built for the Software Atelier course in collaboration with EUMASTER4HPC and LuxProvide*
