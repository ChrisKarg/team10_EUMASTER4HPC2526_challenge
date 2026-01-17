# Grafana Dashboards

The orchestrator provides three pre-configured Grafana dashboards for monitoring services and benchmarks.

## Accessing Grafana

### 1. Create SSH Tunnel

```bash
# Find Grafana node from status or script output
python main.py --status
# Example: grafana_xxx | RUNNING | mel0164

# Create tunnel
ssh -i ~/.ssh/id_ed25519_mlux -L 3000:mel0164:3000 -N u103227@login.lxp.lu -p 8822
```

### 2. Open Browser

Navigate to [http://localhost:3000](http://localhost:3000)

**Default credentials:** `admin` / `admin`

## Overview Dashboard

**URL:** `/d/overview/overview`

System-wide view of all monitored containers.

### Panels

| Panel | Description | Query |
|-------|-------------|-------|
| **Active Targets** | Count of UP scrape targets | `count(up == 1)` |
| **Running Containers** | Number of containers | `count(container_last_seen{name=~".+"})` |
| **Avg CPU %** | Average CPU usage | `avg(rate(container_cpu_usage_seconds_total[1m])) * 100` |
| **Total Memory** | Sum of memory usage | `sum(container_memory_usage_bytes)` |
| **Network RX** | Receive rate | `sum(rate(container_network_receive_bytes_total[1m]))` |
| **Network TX** | Transmit rate | `sum(rate(container_network_transmit_bytes_total[1m]))` |
| **CPU Timeline** | CPU usage over time | `rate(container_cpu_usage_seconds_total{name=~".+"}[1m])` |
| **Memory Timeline** | Memory usage over time | `container_memory_usage_bytes{name=~".+"}` |
| **Network Traffic** | Bidirectional traffic | RX and TX combined |
| **Target Status** | Table of scrape targets | `up` |

## Service Monitoring Dashboard

**URL:** `/d/service-monitoring/service-monitoring`

Detailed metrics for selected containers.

### Variables

| Variable | Description |
|----------|-------------|
| `$container` | Multi-select container filter |
| `$job` | Multi-select job filter |

### Panels

| Panel | Description |
|-------|-------------|
| **CPU Bar Gauge** | Current CPU usage by container |
| **Memory Bar Gauge** | Current memory by container |
| **Network RX Bar** | Receive rate by container |
| **Network TX Bar** | Transmit rate by container |
| **CPU Timeline** | CPU over time with legend |
| **Memory Total** | Total memory timeline |
| **Memory Breakdown** | Working set + cache |
| **Network Throughput** | Bidirectional view |
| **Cumulative I/O** | Total bytes transferred |
| **Filesystem Usage** | Disk usage bars |
| **Memory Limit %** | Gauge showing % of limit |

### Using the Dashboard

1. Use the **Container** dropdown to filter by specific containers
2. Use the **Job** dropdown to filter by Prometheus job
3. Adjust time range in the top-right
4. Click on legend items to show/hide series

## Benchmark Dashboard

**URL:** `/d/benchmarks/benchmarks`

Performance-focused view during benchmark runs.

### Panels

| Panel | Description |
|-------|-------------|
| **Summary Stats** | Avg/Peak CPU and Memory |
| **Live CPU Timeline** | 30-second window for responsiveness |
| **Live Memory Timeline** | Current memory state |
| **Network RX Rate** | Receive throughput |
| **Network TX Rate** | Transmit throughput |
| **CPU Heatmap** | Visual CPU distribution |
| **Avg CPU Bar** | Average over benchmark period |
| **Avg Memory Bar** | Average over benchmark period |
| **Target Health** | Scrape target status |

### Best for

- Watching benchmark progress in real-time
- Comparing resource usage between containers
- Identifying performance bottlenecks

## Customizing Dashboards

### Add a Panel

1. Click **Add panel** button
2. Choose visualization type
3. Enter PromQL query
4. Configure display options
5. Save dashboard

### Example Custom Panel

CPU usage gauge:

```promql
rate(container_cpu_usage_seconds_total{name="ollama"}[1m]) * 100
```

Memory percentage:

```promql
container_memory_usage_bytes{name="ollama"} / 
container_spec_memory_limit_bytes{name="ollama"} * 100
```

### Save Custom Dashboards

1. Make changes
2. Click **Save** (disk icon)
3. Optionally export as JSON

## Useful PromQL Queries

### Per-Container CPU

```promql
rate(container_cpu_usage_seconds_total{name=~".+"}[1m])
```

### Memory Working Set

```promql
container_memory_working_set_bytes{name=~".+"}
```

### Network by Container

```promql
# Receive rate
rate(container_network_receive_bytes_total{name=~".+"}[1m])

# Transmit rate (negative for bidirectional view)
-rate(container_network_transmit_bytes_total{name=~".+"}[1m])
```

### Container Count

```promql
count(container_last_seen{name=~".+"})
```

## Troubleshooting

### No Data Displayed

1. Check Prometheus is running and accessible
2. Verify datasource configuration
3. Ensure cAdvisor targets are being scraped
4. Check time range includes recent data

### Connection Refused

1. Verify SSH tunnel is active
2. Check Grafana is running (`python main.py --status`)
3. Confirm correct node in tunnel command

### Datasource Error

1. Go to **Configuration** → **Data Sources**
2. Click on Prometheus datasource
3. Verify URL matches Prometheus node
4. Click **Test** to verify connection

---

See also: [Monitoring Overview](overview.md) | [Prometheus Metrics](prometheus.md)
