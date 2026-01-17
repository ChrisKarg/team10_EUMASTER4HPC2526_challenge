# Prometheus Metrics

Prometheus collects and stores metrics from cAdvisor sidecars running alongside services.

## Accessing Prometheus

```bash
# Create SSH tunnel
ssh -i ~/.ssh/id_ed25519_mlux -L 9090:mel0210:9090 -N u103227@login.lxp.lu -p 8822

# Open Prometheus UI
open http://localhost:9090
```

## Configuration

Prometheus is automatically configured to scrape cAdvisor endpoints:

```yaml
# Auto-generated: $HOME/prometheus/config/prometheus.yml
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

## PromQL Query Reference

### CPU Queries

```promql
# Instant CPU usage rate (per container)
rate(container_cpu_usage_seconds_total{name=~".+"}[5m])

# Average CPU across all containers
avg(rate(container_cpu_usage_seconds_total{name=~".+"}[5m]))

# Max CPU usage
max(rate(container_cpu_usage_seconds_total{name=~".+"}[5m]))

# CPU for specific container
rate(container_cpu_usage_seconds_total{name="ollama"}[5m])

# CPU percentage (assuming 1 core = 100%)
rate(container_cpu_usage_seconds_total{name=~".+"}[5m]) * 100
```

### Memory Queries

```promql
# Current memory usage
container_memory_usage_bytes{name=~".+"}

# Memory working set (more accurate for actual usage)
container_memory_working_set_bytes{name=~".+"}

# Memory cache (page cache)
container_memory_cache{name=~".+"}

# Memory as percentage of limit
container_memory_usage_bytes{name=~".+"} / 
container_spec_memory_limit_bytes{name=~".+"} * 100

# Total memory across all containers
sum(container_memory_usage_bytes{name=~".+"})

# Memory growth rate
rate(container_memory_usage_bytes{name=~".+"}[5m])
```

### Network Queries

```promql
# Receive rate (bytes/sec)
rate(container_network_receive_bytes_total{name=~".+"}[5m])

# Transmit rate (bytes/sec)
rate(container_network_transmit_bytes_total{name=~".+"}[5m])

# Total bandwidth (RX + TX)
rate(container_network_receive_bytes_total{name=~".+"}[5m]) +
rate(container_network_transmit_bytes_total{name=~".+"}[5m])

# Packet rate
rate(container_network_receive_packets_total{name=~".+"}[5m])
```

### Filesystem Queries

```promql
# Filesystem usage
container_fs_usage_bytes{name=~".+"}

# Filesystem usage percentage
container_fs_usage_bytes{name=~".+"} / 
container_fs_limit_bytes{name=~".+"} * 100
```

### Target Status

```promql
# All targets up/down
up

# Only up targets
up == 1

# Count of up targets
count(up == 1)
```

## Query via CLI

```bash
# Simple query
python main.py --query-metrics prometheus_xxx "up"

# Container memory
python main.py --query-metrics prometheus_xxx "container_memory_usage_bytes"

# With label filter
python main.py --query-metrics prometheus_xxx 'container_cpu_usage_seconds_total{name="ollama"}'

# Rate query
python main.py --query-metrics prometheus_xxx 'rate(container_cpu_usage_seconds_total[5m])'
```

## Metric Labels

### Common Labels

| Label | Description | Example |
|-------|-------------|---------|
| `name` | Container name | `ollama`, `redis` |
| `instance` | Node hostname | `mel2073:8080` |
| `job` | Prometheus job name | `ollama-cadvisor` |
| `service` | Service identifier | `ollama` |

### Filtering by Label

```promql
# Specific container
container_memory_usage_bytes{name="ollama"}

# Multiple containers
container_memory_usage_bytes{name=~"ollama|redis"}

# By job
container_cpu_usage_seconds_total{job="ollama-cadvisor"}

# Exclude pattern
container_memory_usage_bytes{name!~"cadvisor"}
```

## Aggregation Functions

### Sum

```promql
# Total memory
sum(container_memory_usage_bytes{name=~".+"})

# Sum by label
sum by (name) (container_memory_usage_bytes{name=~".+"})
```

### Average

```promql
# Average CPU
avg(rate(container_cpu_usage_seconds_total{name=~".+"}[5m]))
```

### Max/Min

```promql
# Peak memory
max(container_memory_usage_bytes{name=~".+"})

# Min CPU
min(rate(container_cpu_usage_seconds_total{name=~".+"}[5m]))
```

### Count

```promql
# Number of containers
count(container_last_seen{name=~".+"})
```

## Time Functions

### Rate

```promql
# Per-second rate over 5 minutes
rate(container_cpu_usage_seconds_total[5m])

# Use $__rate_interval in Grafana for auto-adjustment
rate(container_cpu_usage_seconds_total[$__rate_interval])
```

### Increase

```promql
# Total increase over 1 hour
increase(container_network_receive_bytes_total[1h])
```

### Delta

```promql
# Change over 5 minutes
delta(container_memory_usage_bytes[5m])
```

## Data Retention

Configure retention in Prometheus recipe:

```yaml
environment:
  PROMETHEUS_RETENTION_TIME: "15d"  # Keep 15 days
  PROMETHEUS_STORAGE_PATH: "/prometheus"
```

---

See also: [Monitoring Overview](overview.md) | [Grafana Dashboards](grafana.md)
