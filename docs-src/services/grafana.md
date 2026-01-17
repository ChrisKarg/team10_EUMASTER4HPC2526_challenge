# Grafana Service

Grafana provides visualization dashboards for monitoring metrics.

## Overview

| Property | Value |
|----------|-------|
| **Type** | Visualization |
| **Default Port** | 3000 |
| **GPU Required** | No |
| **Container** | `docker://grafana/grafana:latest` |

## Quick Start

```bash
# Start full monitoring stack
./scripts/start_all_services.sh

# Create tunnel
ssh -L 3000:mel0164:3000 -N u103227@login.lxp.lu -p 8822

# Access Grafana
open http://localhost:3000
# Default: admin / admin
```

## Recipe Configuration

```yaml
# recipes/services/grafana.yaml
service:
  name: grafana
  description: "Grafana visualization"
  
  container:
    docker_source: docker://grafana/grafana:latest
    image_path: $HOME/containers/grafana.sif
  
  resources:
    nodes: 1
    cpus_per_task: 1
    mem: "1G"
    time: "02:00:00"
    partition: cpu
  
  environment:
    GF_SECURITY_ADMIN_USER: "admin"
    GF_SECURITY_ADMIN_PASSWORD: "admin"
    GF_AUTH_ANONYMOUS_ENABLED: "true"
    GF_AUTH_ANONYMOUS_ORG_ROLE: "Viewer"
  
  ports:
    - 3000
```

## Pre-Built Dashboards

The orchestrator provides three pre-configured dashboards:

### 1. Overview Dashboard

**Path:** `/d/overview/overview`

Displays system-wide metrics:

- Active targets count
- Running containers
- Total CPU/Memory usage
- CPU usage by container (time series)
- Memory usage by container (time series)
- Network traffic (RX/TX)
- Scrape target status table

### 2. Service Monitoring Dashboard

**Path:** `/d/service-monitoring/service-monitoring`

Detailed per-service metrics with container selector:

- Resource overview (CPU, Memory, Network bars)
- CPU usage timeline
- Memory breakdown (total, working set, cache)
- Network throughput
- Filesystem usage
- Memory limit gauge

### 3. Benchmark Dashboard

**Path:** `/d/benchmarks/benchmarks`

Performance-focused view during benchmark runs:

- Summary statistics (Avg/Peak CPU, Memory)
- Live CPU timeline (30s window)
- Live memory timeline
- Network performance
- CPU heatmap
- Resource comparison bars

## Accessing Dashboards

After creating SSH tunnel:

1. Open [http://localhost:3000](http://localhost:3000)
2. Login: `admin` / `admin`
3. Navigate to dashboards via left menu

## Prometheus Datasource

Grafana is automatically configured to connect to Prometheus:

```yaml
# Auto-configured datasource
apiVersion: 1
datasources:
  - name: Prometheus
    uid: prometheus
    type: prometheus
    access: proxy
    url: http://mel0210:9090
    isDefault: true
```

## Custom Dashboards

Create custom dashboards via the Grafana UI:

1. Click **+** → **Create Dashboard**
2. Add panels with PromQL queries
3. Save dashboard

### Useful Queries for Panels

```promql
# CPU gauge
rate(container_cpu_usage_seconds_total{name=~".+"}[1m]) * 100

# Memory time series
container_memory_usage_bytes{name=~".+"}

# Network bidirectional
rate(container_network_receive_bytes_total[1m])
-rate(container_network_transmit_bytes_total[1m])
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GF_SECURITY_ADMIN_USER` | Admin username | `admin` |
| `GF_SECURITY_ADMIN_PASSWORD` | Admin password | `admin` |
| `GF_AUTH_ANONYMOUS_ENABLED` | Allow anonymous access | `false` |
| `GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH` | Home dashboard | Overview |

## Troubleshooting

### Can't Connect to Prometheus

Check that:

1. Prometheus is running (`python main.py --status`)
2. Grafana's datasource URL points to correct node
3. Both services are on same network

### Dashboards Not Loading

1. Check Grafana logs: `cat slurm-*.out`
2. Verify provisioning directory exists
3. Restart Grafana service

---

See also: [Monitoring Overview](../monitoring/overview.md) | [Prometheus](prometheus.md)
