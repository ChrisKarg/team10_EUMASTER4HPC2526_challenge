# Installation Guide

This page provides detailed installation instructions for the HPC AI Benchmarking Orchestrator.

## Prerequisites

### Requirements

- **Python 3.9+** installed locally
- **SSH access** to MeluXina supercomputer
- **SLURM allocation** (account: `p200981` or your project account)
- **SSH key** configured for MeluXina
- **Git** for cloning the repository

## Installation Steps

### 1. Clone the Repository

```bash
cd $HOME
git clone https://github.com/ChrisKarg/team10_EUMASTER4HPC2526_challenge.git
cd team10_EUMASTER4HPC2526_challenge
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate it
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure HPC Connection

Create or edit `config.yaml` in the project root:

```yaml
# SSH Configuration for MeluXina
ssh:
  hostname: "login.lxp.lu"
  port: 8822
  username: "u103227"  # Your MeluXina username
  key_filename: "~/.ssh/id_ed25519_mlux"  # Path to your SSH key

# SLURM Configuration
slurm:
  account: "p200981"    # Your project account
  partition: "gpu"      # Default partition (gpu, cpu, fpga)
  qos: "default"        # Quality of Service
  time: "02:00:00"      # Default time limit

# Container Configuration
containers:
  base_path: "$HOME/containers"
```

!!! warning "SSH Key Setup"
    Make sure your SSH key is added to your MeluXina account. Test with:
    ```bash
    ssh -i ~/.ssh/id_ed25519_mlux -p 8822 u103227@login.lxp.lu
    ```

### 4. Verify Installation

Test the installation by checking available commands:

```bash
python main.py --help
```

Expected output:

```
usage: main.py [-h] [--recipe RECIPE] [--status] [--list-services]
               [--list-clients] [--stop-service STOP_SERVICE]
               [--stop-all-services] ...

HPC AI Benchmarking Orchestrator

optional arguments:
  -h, --help            show this help message and exit
  --recipe RECIPE       Path to YAML recipe file
  --status              Show status of all running jobs
  --list-services       List available service types
  --list-clients        List available client types
  ...
```

### 5. Test SSH Connection

Verify the orchestrator can connect to MeluXina:

```bash
python main.py --status
```

Expected output (if no jobs running):

```
SLURM Job Status:
  Total Jobs: 0
  Services: 0
  Clients: 0
```

## Container Images

The orchestrator uses Apptainer (Singularity) containers. Container images are automatically pulled on first use, but you can pre-build them:

### On MeluXina (via SSH)

```bash
# SSH to MeluXina
ssh -p 8822 u103227@login.lxp.lu

# Load Apptainer module
module load Apptainer/1.2.4-GCCcore-12.3.0

# Create containers directory
mkdir -p $HOME/containers
cd $HOME/containers

# Pull required images
apptainer pull ollama_latest.sif docker://ollama/ollama:latest
apptainer pull redis_latest.sif docker://redis:latest
apptainer pull chroma_latest.sif docker://chromadb/chroma:latest
apptainer pull mysql_latest.sif docker://mysql:8.0
apptainer pull prometheus.sif docker://prom/prometheus:latest
apptainer pull grafana.sif docker://grafana/grafana:latest
apptainer pull cadvisor.sif docker://gcr.io/cadvisor/cadvisor:latest
```

## Directory Structure

After installation, your project should look like:

```
team10_EUMASTER4HPC2526_challenge/
├── main.py                 # CLI entry point
├── config.yaml             # Your configuration
├── requirements.txt        # Python dependencies
├── src/                    # Core modules
│   ├── orchestrator.py
│   ├── servers.py
│   ├── clients.py
│   └── services/           # Service implementations
├── recipes/                # YAML recipes
│   ├── services/           # Service definitions
│   └── clients/            # Client definitions
├── benchmark_scripts/      # Benchmark implementations
├── scripts/                # Automation scripts
└── docs-src/               # Documentation
```

## Troubleshooting

### SSH Connection Issues

```bash
# Test SSH directly
ssh -v -i ~/.ssh/id_ed25519_mlux -p 8822 u103227@login.lxp.lu

# Check key permissions
chmod 600 ~/.ssh/id_ed25519_mlux
```

### SLURM Account Issues

```bash
# On MeluXina, check your accounts
sacctmgr show associations user=$USER

# Verify account in config.yaml matches
```

### Container Not Found

```bash
# On MeluXina, verify container exists
ls -la $HOME/containers/

# Check container path in recipe matches
```

## Next Steps

- [Quick Start](quickstart.md) - Run your first benchmark
- [CLI Reference](../cli/commands.md) - All available commands
- [Services](../services/overview.md) - Configure different services

---

Continue to [Quick Start](quickstart.md) →
