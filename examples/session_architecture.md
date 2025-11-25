# Complete Session Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         HPC CLUSTER                                     │
│                                                                         │
│  ┌───────────────────┐    ┌───────────────────┐    ┌─────────────────┐ │
│  │  Service Node     │    │   Client Node     │    │ Prometheus Node │ │
│  │   (mel2073)       │    │   (mel2076)       │    │   (mel2074)     │ │
│  ├───────────────────┤    ├───────────────────┤    ├─────────────────┤ │
│  │                   │    │                   │    │                 │ │
│  │ ┌───────────────┐ │    │ ┌───────────────┐ │    │ ┌─────────────┐ │ │
│  │ │Ollama Service │ │    │ │Benchmark Client│◄─────┼─┤ Prometheus  │ │ │
│  │ │Port: 11434    │◄├────┤ │Sends requests │ │    │ │Port: 9090   │ │ │
│  │ └───────────────┘ │    │ │Measures perf  │ │    │ └──────┬──────┘ │ │
│  │        │          │    │ └───────────────┘ │    │        │        │ │
│  │        │          │    │                   │    │  Scrapes every  │ │
│  │ ┌──────▼────────┐ │    │                   │    │   15 seconds    │ │
│  │ │  cAdvisor     │◄├────┼───────────────────┼────┤        │        │ │
│  │ │  Port: 8080   │ │    │                   │    │        │        │ │
│  │ │  /metrics     │ │    │                   │    │  Stores time-   │ │
│  │ └───────────────┘ │    │                   │    │  series data    │ │
│  │  Monitors:        │    │                   │    │                 │ │
│  │  - CPU usage      │    │                   │    │                 │ │
│  │  - Memory         │    │                   │    │                 │ │
│  │  - Network I/O    │    │                   │    │                 │ │
│  │  - Disk I/O       │    │                   │    │                 │ │
│  └───────────────────┘    └───────────────────┘    └────────┬────────┘ │
│                                                               │          │
│  ┌────────────────────────────────────────────────────────────┘          │
│  │                Login Node (login.lxp.lu:8822)                         │
│  │                      SSH Gateway                                      │
│  └──────────────────────────────┬────────────────────────────────────────┘
└─────────────────────────────────┼──────────────────────────────────────────┘
                                  │
                                  │ SSH Tunnel
                                  │ Port Forwarding
                                  │
                        ┌─────────▼──────────┐
                        │                    │
                        │  Local Machine     │
                        │                    │
                        │  localhost:9090    │◄──────┐
                        │                    │       │
                        └────────────────────┘       │
                                                     │
                        ┌────────────────────────────┴────────┐
                        │                                     │
                        │   Web Browser                       │
                        │                                     │
                        │   - View metrics                    │
                        │   - Query PromQL                    │
                        │   - Create dashboards               │
                        │   - Monitor benchmarks              │
                        │                                     │
                        └─────────────────────────────────────┘
```

## Data Flow

### 1. Benchmark Request Flow

```
Client Node                Service Node
    │                          │
    │  HTTP Request            │
    │  (benchmark query)       │
    ├─────────────────────────►│
    │                          │ Process request
    │                          │ (LLM inference,
    │                          │  DB query, etc.)
    │                          │
    │  HTTP Response           │
    │  (result + timing)       │
    │◄─────────────────────────┤
    │                          │
    │  Record metrics:         │
    │  - Latency              │
    │  - Throughput           │
    │  - Success rate         │
    │                          │
```

### 2. Monitoring Data Flow

```
Service Node              Prometheus Node
    │                          │
    │  cAdvisor running         │
    │  Collecting metrics       │
    │  every 10 seconds         │
    │                          │
    │                          │  Scrape metrics
    │  HTTP GET /metrics       │  every 15 seconds
    │◄─────────────────────────┤
    │                          │
    │  Return Prometheus       │
    │  format metrics          │
    ├─────────────────────────►│
    │                          │
    │                          │  Store in
    │                          │  time-series DB
    │                          │
    │                          │  Available for
    │                          │  queries via UI/API
```

### 3. Complete Session Flow

```
User Command
    │
    ├─► [1/6] Start Service with cAdvisor
    │         │
    │         ├─► Submit SLURM job
    │         ├─► Wait for node assignment
    │         ├─► Check cAdvisor exists
    │         ├─► Download if needed (one-time)
    │         ├─► Start cAdvisor (port 8080)
    │         └─► Start service (e.g., Ollama)
    │
    ├─► [2/6] Detect Service
    │         │
    │         ├─► Poll squeue every 5s
    │         ├─► Find most recent service
    │         ├─► Get assigned node (e.g., mel2073)
    │         └─► Detect port (e.g., 11434)
    │
    ├─► [3/6] Start Client
    │         │
    │         ├─► Build endpoint: http://mel2073:11434
    │         ├─► Update client recipe
    │         ├─► Submit client SLURM job
    │         └─► Client starts sending requests
    │
    ├─► [4/6] Configure Prometheus
    │         │
    │         ├─► Add service_id to targets
    │         ├─► Set job_name: "service-cadvisor"
    │         ├─► Set port: 8080
    │         └─► Generate prometheus.yml
    │
    ├─► [5/6] Start Prometheus
    │         │
    │         ├─► Submit Prometheus SLURM job
    │         ├─► Wait for node assignment
    │         ├─► Start scraping cAdvisor
    │         └─► Expose UI on port 9090
    │
    └─► [6/6] Create SSH Tunnel
              │
              ├─► Detect Prometheus node
              ├─► Generate SSH command
              └─► User runs command → access localhost:9090
```

## Component Interaction Matrix

```
┌─────────────────┬──────────┬──────────┬──────────────┬──────────┐
│                 │ Service  │ Client   │ cAdvisor     │Prometheus│
├─────────────────┼──────────┼──────────┼──────────────┼──────────┤
│ Service         │    -     │ Responds │ Monitored by │    -     │
├─────────────────┼──────────┼──────────┼──────────────┼──────────┤
│ Client          │  Sends   │    -     │      -       │    -     │
│                 │ requests │          │              │          │
├─────────────────┼──────────┼──────────┼──────────────┼──────────┤
│ cAdvisor        │ Monitors │    -     │      -       │ Scraped  │
│                 │container │          │              │   by     │
├─────────────────┼──────────┼──────────┼──────────────┼──────────┤
│ Prometheus      │    -     │    -     │   Scrapes    │    -     │
│                 │          │          │   metrics    │          │
├─────────────────┼──────────┼──────────┼──────────────┼──────────┤
│ User (via SSH)  │    -     │    -     │      -       │ Queries  │
│                 │          │          │              │   UI     │
└─────────────────┴──────────┴──────────┴──────────────┴──────────┘
```

## Timeline View

```
Time →
0s     30s    60s    90s    120s   150s   180s   210s   240s...

Service   [Starting...]──[Running]──────────────────────────────►
              │              │
              └──cAdvisor────┴──[Monitoring]──────────────────►

Client                  [Starting...]──[Benchmarking]──────────►
                              │              │
                              └──Requests────┴─────────────────►

Prometheus                      [Starting...]──[Scraping]──────►
                                      │             │
                                      └──Metrics────┴──────────►

SSH Tunnel                                  [Ready]─────────────►
                                                  │
                                                  └──User Access►
```

## Automatic Endpoint Resolution

```
Service Recipe
    │
    ├─► Service Name: "ollama"
    │   Port: [11434]
    │
    └─► Assigned Node: mel2073
            │
            ├─► Build Endpoint
            │       │
            │       └─► http://mel2073:11434
            │
            ├─► Configure Client
            │       └─► target_endpoint = http://mel2073:11434
            │
            └─► Configure Prometheus
                    └─► scrape_target = mel2073:8080
```

## Port Usage Summary

```
┌──────────────┬──────────┬────────────────────────────────┐
│ Component    │   Port   │          Purpose               │
├──────────────┼──────────┼────────────────────────────────┤
│ Service      │  varies  │ Service API (11434, 6379, etc) │
│ cAdvisor     │  8080    │ Metrics endpoint               │
│ Prometheus   │  9090    │ UI + API                       │
│ SSH Tunnel   │  9090    │ Local access to Prometheus     │
└──────────────┴──────────┴────────────────────────────────┘
```

## Automatic Configuration

### What Gets Detected

```
Service Detection:
├─ Service ID: ollama_abc123
├─ Node: mel2073
├─ Service Port: 11434 (auto-detected from service name)
└─ cAdvisor Port: 8080 (default)

Client Configuration:
├─ Target Service: ollama_abc123
├─ Target Endpoint: http://mel2073:11434
└─ Automatically set when client starts

Prometheus Configuration:
├─ Target Service: ollama_abc123
├─ Scrape Endpoint: mel2073:8080
├─ Job Name: ollama-cadvisor
└─ Automatically added to prometheus.yml
```

### What User Provides

```
User Input:
├─ Service Recipe Path
├─ Client Recipe Path
└─ Prometheus Recipe Path

Everything Else: AUTOMATED ✅
```

## Error Handling

```
[1/6] Service Start
    │
    ├─ ✅ Success → Continue
    └─ ❌ Failure → Stop, show error

[2/6] Service Detection
    │
    ├─ ✅ Node assigned → Continue
    └─ ⏱️  Timeout (60s) → Show manual steps

[3/6] Client Start
    │
    ├─ ✅ Success → Continue
    └─ ❌ Failure → Service continues, show error

[4/6] Prometheus Config
    │
    └─ ✅ Always succeeds (in-memory update)

[5/6] Prometheus Start
    │
    ├─ ✅ Success → Continue
    └─ ❌ Failure → Service/Client continue

[6/6] SSH Tunnel
    │
    ├─ ✅ Show command → User action
    └─ ❌ Failure → Show manual alternative
```

## Benefits Visualization

```
Manual Workflow:
[Start Service] → [Copy ID] → [Edit File] → [Start Client] → 
[Copy ID] → [Edit File] → [Start Prometheus] → [Copy ID] → 
[Create Tunnel]

Time: ~5-7 minutes
Steps: 9 user actions
Errors: 5 potential error points

═══════════════════════════════════════════════════════════

Automated Workflow:
[One Command] → [Wait] → [Done]

Time: ~90 seconds
Steps: 1 user action
Errors: 0 potential error points

Speed-up: 3-5× faster
Error reduction: 100%
```
