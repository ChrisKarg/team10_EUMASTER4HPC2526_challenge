# Prometheus Service

Prometheus is a monitoring and alerting toolkit for collecting and querying metrics.

## Overview

| Property | Value |
|----------|-------|
| **Type** | Monitoring |
| **Default Port** | 9090 |
| **GPU Required** | No |
| **Container** | `docker://prom/prometheus:latest` |

## Quick Start

```bash
# Start Prometheus with service monitoring
python main.py --recipe recipes/services/prometheus_with_cadvisor.yaml

# Create tunnel
ssh -L 9090:mel0210:9090 -N u103227@login.lxp.lu -p 8822

# Access UI
open http://localhost:9090
```

## Recipe Configuration

```yaml
# recipes/services/prometheus_with_cadvisor.yaml
service:
  name: prometheus
  description: "Prometheus monitoring"
  
  container:
    docker_source: docker://prom/prometheus:latest
    image_path: $HOME/containers/prometheus.sif
  
  resources:
    nodes: 1
    cpus_per_task: 2
    mem: "4G"
    time: "02:00:00"
    partition: cpu
  
  # Services to monitor
  monitoring_targets:
    - service_id: "ollama_xxx"
      job_name: "ollama-cadvisor"
      port: 8080
    - service_id: "redis_xxx"
      job_name: "redis-cadvisor"
      port: 8080
  
  environment:
    PROMETHEUS_RETENTION_TIME: "15d"
  
  ports:
    - 9090
```

## Configuration

Prometheus is automatically configured to scrape cAdvisor endpoints from monitored services.

### Auto-Generated Config

```yaml
# $HOME/prometheus/config/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'ollama-cadvisor'
    static_configs:
      - targets: ['mel2073:8080']
        labels:
          service: 'ollama'
          instance: 'mel2073'

  - job_name: 'redis-cadvisor'
    static_configs:
      - targets: ['mel0182:8080']
        labels:
          service: 'redis'
          instance: 'mel0182'
```

## Useful PromQL Queries

### CPU Usage

```promql
# CPU usage rate by container
rate(container_cpu_usage_seconds_total{name=~".+"}[5m])

# Average CPU usage
avg(rate(container_cpu_usage_seconds_total[5m]))
```

### Memory Usage

```promql
# Memory usage by container
container_memory_usage_bytes{name=~".+"}

# Memory working set
container_memory_working_set_bytes{name=~".+"}
```

### Network Traffic

```promql
# Network receive rate
rate(container_network_receive_bytes_total[5m])

# Network transmit rate
rate(container_network_transmit_bytes_total[5m])
```

### Container Info

```promql
# Active containers
count(container_last_seen{name=~".+"})

# Scrape targets up
up
```

## Querying via CLI

```bash
# Query metrics from orchestrator
python main.py --query-metrics prometheus_xxx "container_memory_usage_bytes"

# With labels
python main.py --query-metrics prometheus_xxx 'container_memory_usage_bytes{name="ollama"}'
```

## Data Retention

Configure retention in environment:

```yaml
environment:
  PROMETHEUS_RETENTION_TIME: "7d"    # Keep 7 days
  PROMETHEUS_STORAGE_PATH: "/prometheus"
```

---

See also: [Monitoring Overview](../monitoring/overview.md) | [Grafana](grafana.md)
