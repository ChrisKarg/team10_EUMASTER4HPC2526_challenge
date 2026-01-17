# Quick Start

Run your first benchmark in 5 minutes! This guide walks through a complete end-to-end workflow.

## Prerequisites

- [Installation completed](installation.md)
- SSH connection working
- Container images available on MeluXina

## Option 1: Automated Full Stack (Recommended)

Use the automation scripts to start everything at once:

```bash
# Start all services (Ollama, Redis, Chroma, MySQL, Prometheus, Grafana)
./scripts/start_all_services.sh

# Wait for services to be ready, then start benchmark clients
./scripts/start_all_clients.sh
```

Then create SSH tunnels to access the dashboards:

```bash
# Tunnel for Grafana (replace mel0XXX with actual node from script output)
ssh -i ~/.ssh/id_ed25519_mlux -L 3000:mel0XXX:3000 -N u103227@login.lxp.lu -p 8822

# Tunnel for Prometheus
ssh -i ~/.ssh/id_ed25519_mlux -L 9090:mel0YYY:9090 -N u103227@login.lxp.lu -p 8822
```

Open [http://localhost:3000](http://localhost:3000) in your browser to see Grafana dashboards.

---

## Option 2: Step-by-Step Manual Workflow

### Step 1: Start a Service

Start an Ollama LLM service:

```bash
python main.py --recipe recipes/services/ollama.yaml
```

**Expected output:**

```
Service started: ollama_a1b2c3d4
Monitor the job status through SLURM or check logs.

  To check status:
    python main.py --status
  
  To stop:
    python main.py --stop-service ollama_a1b2c3d4
```

### Step 2: Check Status

Wait for the service to start running:

```bash
python main.py --status
```

**Expected output:**

```
SLURM Job Status:
  Total Jobs: 1
  Services: 1
  Clients: 0

Services:
  JOB_ID  | SERVICE_ID        | STATUS  | RUNTIME  | NODE
  3656789 | ollama_a1b2c3d4   | RUNNING | 0:02:15  | mel2073
```

!!! tip "Note the Node"
    Remember the node name (`mel2073` in this example) - you'll need it for client connections and SSH tunnels.

### Step 3: Run a Benchmark Client

Run a benchmark against the service:

```bash
# Using service ID (recommended)
python main.py --recipe recipes/clients/ollama_benchmark.yaml --target-service ollama_a1b2c3d4

# Or using direct endpoint
python main.py --recipe recipes/clients/ollama_benchmark.yaml --target-endpoint http://mel2073:11434
```

**Expected output:**

```
Client started: ollama_bench_e5f6g7h8
Benchmark running against: http://mel2073:11434
```

### Step 4: Monitor Progress

Check both service and client status:

```bash
python main.py --status
```

**Expected output:**

```
SLURM Job Status:
  Total Jobs: 2
  Services: 1
  Clients: 1

Services:
  JOB_ID  | SERVICE_ID        | STATUS  | RUNTIME  | NODE
  3656789 | ollama_a1b2c3d4   | RUNNING | 0:05:30  | mel2073

Clients:
  JOB_ID  | CLIENT_ID              | STATUS  | RUNTIME  | NODE
  3656790 | ollama_bench_e5f6g7h8  | RUNNING | 0:02:45  | mel2074
```

### Step 5: View Results

#### Option A: Download Results Locally

```bash
# Download all results from cluster
python main.py --download-results

# View results
ls -la results/
cat results/ollama_benchmark_*.json
```

#### Option B: View in Grafana

Create an SSH tunnel to access Grafana:

```bash
# Start tunnel (replace mel0XXX with Grafana node)
ssh -i ~/.ssh/id_ed25519_mlux -L 3000:mel0XXX:3000 -N u103227@login.lxp.lu -p 8822
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

**Default credentials:** `admin` / `admin`

### Step 6: Clean Up

Stop services when done:

```bash
# Stop a specific service
python main.py --stop-service ollama_a1b2c3d4

# Or stop all services
python main.py --stop-all-services
```

**Expected output:**

```
✅ Stopped 2/2 services
```

---

## Quick Command Reference

| Action | Command |
|--------|---------|
| Start service | `python main.py --recipe recipes/services/ollama.yaml` |
| Check status | `python main.py --status` |
| Run client | `python main.py --recipe recipes/clients/ollama_benchmark.yaml --target-service <ID>` |
| Stop service | `python main.py --stop-service <ID>` |
| Stop all | `python main.py --stop-all-services` |
| Download results | `python main.py --download-results` |
| List services | `python main.py --list-services` |
| List clients | `python main.py --list-clients` |
| Verbose mode | `python main.py --verbose --status` |

---

## Example: Redis Benchmark

```bash
# 1. Start Redis service
python main.py --recipe recipes/services/redis.yaml

# 2. Check it's running
python main.py --status

# 3. Run benchmark
python main.py --recipe recipes/clients/redis_benchmark.yaml --target-service redis_XXXX

# 4. Download results
python main.py --download-results
```

## Example: Full Monitoring Session

```bash
# Start service with cAdvisor monitoring
python main.py --start-monitoring \
    recipes/services/ollama_with_cadvisor.yaml \
    recipes/services/prometheus_with_cadvisor.yaml

# This starts:
# - Ollama service with cAdvisor sidecar
# - Prometheus scraping cAdvisor metrics
# - Provides tunnel command for Prometheus UI
```

---

## Next Steps

- [CLI Reference](../cli/commands.md) - All available commands
- [Services Guide](../services/overview.md) - Configure different services
- [Monitoring Guide](../monitoring/overview.md) - Set up Grafana dashboards
- [Recipes Guide](../recipes/overview.md) - Write custom configurations
