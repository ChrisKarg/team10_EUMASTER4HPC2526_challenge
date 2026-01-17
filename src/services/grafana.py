"""
Grafana Service Implementation
"""

from typing import Dict, Any, List
from dataclasses import dataclass

from .base import Service, JobFactory


@dataclass
class GrafanaService(Service):
    """Grafana monitoring dashboard service for HPC environments"""
    
    # Prometheus URL for datasource configuration
    prometheus_url: str = None
    
    def __post_init__(self):
        """Initialize defaults"""
        super().__post_init__()
        if self.prometheus_url is None:
            self.prometheus_url = "http://localhost:9090"
    
    @classmethod
    def from_recipe(cls, recipe: Dict[str, Any], config: Dict[str, Any]) -> 'GrafanaService':
        """Create Grafana service from recipe"""
        service_config = recipe.get('service', {})
        
        # Get Prometheus URL from environment or default
        env = service_config.get('environment', {})
        prometheus_url = env.get('PROMETHEUS_URL', 'http://localhost:9090')
        
        instance = cls(
            name=service_config.get('name', 'grafana'),
            container_image=service_config.get('container_image', 'grafana_latest.sif'),
            resources=service_config.get('resources', {}),
            environment=env,
            command=service_config.get('command'),
            args=service_config.get('args', []),
            ports=service_config.get('ports', [3000]),
            container=service_config.get('container', {}),
            config=config,
            enable_cadvisor=service_config.get('enable_cadvisor', False),
            cadvisor_port=service_config.get('cadvisor_port', 8080)
        )
        instance.prometheus_url = prometheus_url
        return instance
    
    def get_service_setup_commands(self) -> List[str]:
        """Setup Grafana configuration directories and provisioning"""
        # First get base service setup (includes cAdvisor if enabled)
        commands = super().get_service_setup_commands()
        
        commands.extend([
            "# Grafana setup",
            "mkdir -p $HOME/grafana/data",
            "mkdir -p $HOME/grafana/logs",
            "mkdir -p $HOME/grafana/provisioning/datasources",
            "mkdir -p $HOME/grafana/provisioning/dashboards",
            "mkdir -p $HOME/grafana/dashboards",
            "",
            "# Discover Prometheus URL",
            "echo 'Discovering Prometheus service...'",
            "",
            "# Initialize with default value",
            "PROM_URL=\"http://localhost:9090\"",
            "",
            "# Priority 1: Read from file (most reliable - written by start_all_services.sh)",
            "if [ -f \"$HOME/.prometheus_url\" ]; then",
            "    PROM_URL=$(cat $HOME/.prometheus_url | tr -d '[:space:]')",
            "    echo \"Using Prometheus URL from ~/.prometheus_url: $PROM_URL\"",
            "# Priority 2: Environment variable",
            "elif [ -n \"$PROMETHEUS_URL\" ]; then",
            "    PROM_URL=\"$PROMETHEUS_URL\"",
            "    echo \"Using Prometheus URL from environment: $PROM_URL\"",
            "# Priority 3: Try squeue (may not work on compute nodes)",
            "else",
            "    PROM_HOST=$(squeue -u $USER -n prometheus* -h -o '%N' 2>/dev/null | head -1 | tr -d ' ' || echo '')",
            "    if [ -n \"$PROM_HOST\" ]; then",
            "        PROM_URL=\"http://${PROM_HOST}:9090\"",
            "        echo \"Found Prometheus via SLURM on: $PROM_HOST\"",
            "    else",
            "        echo \"WARNING: Could not find Prometheus, using localhost:9090\"",
            "        echo \"If Grafana can't connect, set PROMETHEUS_URL or create ~/.prometheus_url\"",
            "    fi",
            "fi",
            "",
            "# Validate URL is not empty",
            "if [ -z \"$PROM_URL\" ] || [ \"$PROM_URL\" = \"http://:9090\" ]; then",
            "    PROM_URL=\"http://localhost:9090\"",
            "fi",
            "",
            "echo \"Configuring Grafana to connect to Prometheus at: $PROM_URL\"",
            "",
            "# Create Grafana datasource configuration for Prometheus",
            "cat > $HOME/grafana/provisioning/datasources/prometheus.yml << EOF",
            "apiVersion: 1",
            "",
            "datasources:",
            "  - name: Prometheus",
            "    uid: prometheus",
            "    type: prometheus",
            "    access: proxy",
            "    url: $PROM_URL",
            "    isDefault: true",
            "    editable: true",
            "    jsonData:",
            "      timeInterval: \"15s\"",
            "EOF",
            "",
            "# Create dashboard provisioning configuration",
            "cat > $HOME/grafana/provisioning/dashboards/default.yml << 'EOF'",
            "apiVersion: 1",
            "",
            "providers:",
            "  - name: HPC-Benchmarking",
            "    type: file",
            "    disableDeletion: true",
            "    updateIntervalSeconds: 10",
            "    allowUiUpdates: true",
            "    options:",
            "      path: /var/lib/grafana/dashboards",
            "EOF",
            "",
            "# Create Overview Dashboard",
            "echo 'Creating dashboards...'",
        ])

        # Add the overview dashboard
        commands.append("cat > $HOME/grafana/dashboards/overview.json << 'DASHEOF'")
        commands.append(self._get_overview_dashboard())
        commands.append("DASHEOF")

        # Add the service monitoring dashboard
        commands.append("")
        commands.append("cat > $HOME/grafana/dashboards/service.json << 'DASHEOF'")
        commands.append(self._get_service_dashboard())
        commands.append("DASHEOF")

        # Add the benchmark dashboard
        commands.append("")
        commands.append("cat > $HOME/grafana/dashboards/benchmarks.json << 'DASHEOF'")
        commands.append(self._get_benchmark_dashboard())
        commands.append("DASHEOF")

        commands.extend([
            "",
            "echo 'Grafana configuration created'",
            "echo 'Datasource: Prometheus at $PROM_URL'",
            "echo 'Dashboards: Overview, Service Monitoring, Benchmarks'",
            ""
        ])
        
        return commands

    def _get_overview_dashboard(self) -> str:
        """Return comprehensive overview dashboard JSON"""
        return '''{
  "annotations": {"list": []},
  "editable": true,
  "fiscalYearStartMonth": 0,
  "graphTooltip": 2,
  "id": null,
  "links": [
    {"title": "Service Details", "type": "link", "url": "/d/service-monitoring/service-monitoring", "icon": "dashboard"},
    {"title": "Benchmark Metrics", "type": "link", "url": "/d/benchmarks/benchmarks", "icon": "graph-bar"}
  ],
  "panels": [
    {
      "gridPos": {"h": 2, "w": 24, "x": 0, "y": 0},
      "id": 1,
      "options": {"content": "<div style=\\"text-align:center;padding:8px;background:linear-gradient(90deg,#1e3a5f,#2563eb,#1e3a5f);border-radius:8px\\"><h1 style=\\"color:#fff;font-weight:400;margin:0\\">HPC Benchmarking Dashboard</h1><p style=\\"color:#94a3b8;margin:4px 0 0\\">Real-time container metrics via cAdvisor + Prometheus</p></div>", "mode": "html"},
      "title": "",
      "transparent": true,
      "type": "text"
    },
    {
      "datasource": {"type": "prometheus", "uid": "prometheus"},
      "fieldConfig": {"defaults": {"color": {"mode": "thresholds"}, "thresholds": {"mode": "absolute", "steps": [{"color": "red", "value": null}, {"color": "green", "value": 1}]}, "mappings": []}},
      "gridPos": {"h": 4, "w": 4, "x": 0, "y": 2},
      "id": 2,
      "options": {"colorMode": "background", "graphMode": "none", "justifyMode": "center", "reduceOptions": {"calcs": ["lastNotNull"]}},
      "targets": [{"expr": "count(up == 1) or vector(0)", "refId": "A"}],
      "title": "Active Targets",
      "type": "stat"
    },
    {
      "datasource": {"type": "prometheus", "uid": "prometheus"},
      "fieldConfig": {"defaults": {"color": {"mode": "thresholds"}, "thresholds": {"mode": "absolute", "steps": [{"color": "blue", "value": null}]}, "mappings": []}},
      "gridPos": {"h": 4, "w": 4, "x": 4, "y": 2},
      "id": 3,
      "options": {"colorMode": "background", "graphMode": "none", "justifyMode": "center", "reduceOptions": {"calcs": ["lastNotNull"]}},
      "targets": [{"expr": "count(container_last_seen{name=~\\".+\\"}) or vector(0)", "refId": "A"}],
      "title": "Running Containers",
      "type": "stat"
    },
    {
      "datasource": {"type": "prometheus", "uid": "prometheus"},
      "fieldConfig": {"defaults": {"color": {"mode": "thresholds"}, "thresholds": {"mode": "absolute", "steps": [{"color": "green", "value": null}, {"color": "yellow", "value": 70}, {"color": "red", "value": 85}]}, "unit": "percent", "max": 100}},
      "gridPos": {"h": 4, "w": 4, "x": 8, "y": 2},
      "id": 4,
      "options": {"colorMode": "background", "graphMode": "area", "justifyMode": "center", "reduceOptions": {"calcs": ["lastNotNull"]}},
      "targets": [{"expr": "avg(rate(container_cpu_usage_seconds_total{name=~\\".+\\"}[1m])) * 100 or vector(0)", "refId": "A"}],
      "title": "Avg CPU %",
      "type": "stat"
    },
    {
      "datasource": {"type": "prometheus", "uid": "prometheus"},
      "fieldConfig": {"defaults": {"color": {"mode": "thresholds"}, "thresholds": {"mode": "absolute", "steps": [{"color": "green", "value": null}]}, "unit": "bytes"}},
      "gridPos": {"h": 4, "w": 4, "x": 12, "y": 2},
      "id": 5,
      "options": {"colorMode": "background", "graphMode": "area", "justifyMode": "center", "reduceOptions": {"calcs": ["lastNotNull"]}},
      "targets": [{"expr": "sum(container_memory_usage_bytes{name=~\\".+\\"}) or vector(0)", "refId": "A"}],
      "title": "Total Memory",
      "type": "stat"
    },
    {
      "datasource": {"type": "prometheus", "uid": "prometheus"},
      "fieldConfig": {"defaults": {"color": {"mode": "thresholds"}, "thresholds": {"mode": "absolute", "steps": [{"color": "purple", "value": null}]}, "unit": "Bps"}},
      "gridPos": {"h": 4, "w": 4, "x": 16, "y": 2},
      "id": 6,
      "options": {"colorMode": "background", "graphMode": "area", "justifyMode": "center", "reduceOptions": {"calcs": ["lastNotNull"]}},
      "targets": [{"expr": "sum(rate(container_network_receive_bytes_total{name=~\\".+\\"}[1m])) or vector(0)", "refId": "A"}],
      "title": "Network RX",
      "type": "stat"
    },
    {
      "datasource": {"type": "prometheus", "uid": "prometheus"},
      "fieldConfig": {"defaults": {"color": {"mode": "thresholds"}, "thresholds": {"mode": "absolute", "steps": [{"color": "orange", "value": null}]}, "unit": "Bps"}},
      "gridPos": {"h": 4, "w": 4, "x": 20, "y": 2},
      "id": 7,
      "options": {"colorMode": "background", "graphMode": "area", "justifyMode": "center", "reduceOptions": {"calcs": ["lastNotNull"]}},
      "targets": [{"expr": "sum(rate(container_network_transmit_bytes_total{name=~\\".+\\"}[1m])) or vector(0)", "refId": "A"}],
      "title": "Network TX",
      "type": "stat"
    },
    {
      "collapsed": false,
      "gridPos": {"h": 1, "w": 24, "x": 0, "y": 6},
      "id": 8,
      "title": "CPU Metrics",
      "type": "row"
    },
    {
      "datasource": {"type": "prometheus", "uid": "prometheus"},
      "fieldConfig": {"defaults": {"color": {"mode": "palette-classic"}, "unit": "percentunit", "custom": {"drawStyle": "line", "fillOpacity": 25, "lineWidth": 2, "lineInterpolation": "smooth", "spanNulls": true, "showPoints": "never"}, "min": 0}},
      "gridPos": {"h": 8, "w": 16, "x": 0, "y": 7},
      "id": 9,
      "options": {"legend": {"displayMode": "table", "placement": "right", "showLegend": true, "calcs": ["mean", "max", "lastNotNull"]}, "tooltip": {"mode": "multi", "sort": "desc"}},
      "targets": [{"expr": "rate(container_cpu_usage_seconds_total{name=~\\".+\\"}[1m])", "legendFormat": "{{name}}", "refId": "A"}],
      "title": "CPU Usage Rate by Container",
      "type": "timeseries"
    },
    {
      "datasource": {"type": "prometheus", "uid": "prometheus"},
      "fieldConfig": {"defaults": {"color": {"mode": "continuous-GrYlRd"}, "unit": "percentunit", "min": 0, "max": 1, "thresholds": {"mode": "absolute", "steps": [{"color": "green", "value": null}, {"color": "yellow", "value": 0.5}, {"color": "red", "value": 0.8}]}}},
      "gridPos": {"h": 8, "w": 8, "x": 16, "y": 7},
      "id": 10,
      "options": {"orientation": "horizontal", "displayMode": "lcd", "showUnfilled": true, "minVizWidth": 8, "minVizHeight": 10, "reduceOptions": {"calcs": ["lastNotNull"]}},
      "targets": [{"expr": "rate(container_cpu_usage_seconds_total{name=~\\".+\\"}[1m])", "legendFormat": "{{name}}", "refId": "A"}],
      "title": "CPU Usage Bar",
      "type": "bargauge"
    },
    {
      "collapsed": false,
      "gridPos": {"h": 1, "w": 24, "x": 0, "y": 15},
      "id": 11,
      "title": "Memory Metrics",
      "type": "row"
    },
    {
      "datasource": {"type": "prometheus", "uid": "prometheus"},
      "fieldConfig": {"defaults": {"color": {"mode": "palette-classic"}, "unit": "bytes", "custom": {"drawStyle": "line", "fillOpacity": 25, "lineWidth": 2, "lineInterpolation": "smooth", "spanNulls": true, "showPoints": "never", "stacking": {"mode": "none"}}, "min": 0}},
      "gridPos": {"h": 8, "w": 12, "x": 0, "y": 16},
      "id": 12,
      "options": {"legend": {"displayMode": "table", "placement": "bottom", "showLegend": true, "calcs": ["mean", "max", "lastNotNull"]}, "tooltip": {"mode": "multi", "sort": "desc"}},
      "targets": [{"expr": "container_memory_usage_bytes{name=~\\".+\\"}", "legendFormat": "{{name}}", "refId": "A"}],
      "title": "Memory Usage by Container",
      "type": "timeseries"
    },
    {
      "datasource": {"type": "prometheus", "uid": "prometheus"},
      "fieldConfig": {"defaults": {"color": {"mode": "palette-classic"}, "unit": "bytes", "custom": {"drawStyle": "line", "fillOpacity": 25, "lineWidth": 2, "lineInterpolation": "smooth", "spanNulls": true, "showPoints": "never"}, "min": 0}},
      "gridPos": {"h": 8, "w": 12, "x": 12, "y": 16},
      "id": 13,
      "options": {"legend": {"displayMode": "table", "placement": "bottom", "showLegend": true, "calcs": ["mean", "max"]}, "tooltip": {"mode": "multi", "sort": "desc"}},
      "targets": [{"expr": "container_memory_working_set_bytes{name=~\\".+\\"}", "legendFormat": "{{name}} (working set)", "refId": "A"}],
      "title": "Memory Working Set by Container",
      "type": "timeseries"
    },
    {
      "collapsed": false,
      "gridPos": {"h": 1, "w": 24, "x": 0, "y": 24},
      "id": 14,
      "title": "Network & I/O",
      "type": "row"
    },
    {
      "datasource": {"type": "prometheus", "uid": "prometheus"},
      "fieldConfig": {"defaults": {"color": {"mode": "palette-classic"}, "unit": "Bps", "custom": {"drawStyle": "line", "fillOpacity": 20, "lineWidth": 2, "lineInterpolation": "smooth", "spanNulls": true, "showPoints": "never"}}},
      "gridPos": {"h": 8, "w": 12, "x": 0, "y": 25},
      "id": 15,
      "options": {"legend": {"displayMode": "table", "placement": "bottom", "showLegend": true, "calcs": ["mean", "max"]}, "tooltip": {"mode": "multi", "sort": "desc"}},
      "targets": [
        {"expr": "rate(container_network_receive_bytes_total{name=~\\".+\\"}[1m])", "legendFormat": "RX {{name}}", "refId": "A"},
        {"expr": "-rate(container_network_transmit_bytes_total{name=~\\".+\\"}[1m])", "legendFormat": "TX {{name}}", "refId": "B"}
      ],
      "title": "Network Traffic (RX positive, TX negative)",
      "type": "timeseries"
    },
    {
      "datasource": {"type": "prometheus", "uid": "prometheus"},
      "fieldConfig": {"defaults": {"color": {"mode": "palette-classic"}, "unit": "bytes", "custom": {"drawStyle": "bars", "fillOpacity": 80, "lineWidth": 1}}},
      "gridPos": {"h": 8, "w": 12, "x": 12, "y": 25},
      "id": 16,
      "options": {"legend": {"displayMode": "table", "placement": "bottom", "showLegend": true, "calcs": ["lastNotNull"]}, "tooltip": {"mode": "multi"}},
      "targets": [{"expr": "container_fs_usage_bytes{name=~\\".+\\"}", "legendFormat": "{{name}}", "refId": "A"}],
      "title": "Filesystem Usage by Container",
      "type": "timeseries"
    },
    {
      "collapsed": false,
      "gridPos": {"h": 1, "w": 24, "x": 0, "y": 33},
      "id": 17,
      "title": "Service Status",
      "type": "row"
    },
    {
      "datasource": {"type": "prometheus", "uid": "prometheus"},
      "fieldConfig": {"defaults": {"color": {"mode": "thresholds"}, "mappings": [{"options": {"0": {"color": "red", "text": "DOWN"}, "1": {"color": "green", "text": "UP"}}, "type": "value"}], "thresholds": {"mode": "absolute", "steps": [{"color": "red", "value": null}, {"color": "green", "value": 1}]}, "custom": {"align": "center"}}},
      "gridPos": {"h": 6, "w": 24, "x": 0, "y": 34},
      "id": 18,
      "options": {"showHeader": true, "cellHeight": "sm", "footer": {"show": false}},
      "targets": [{"expr": "up", "format": "table", "instant": true, "refId": "A"}],
      "title": "Prometheus Scrape Targets",
      "transformations": [{"id": "organize", "options": {"excludeByName": {"Time": true, "__name__": true}, "renameByName": {"Value": "Status", "instance": "Instance", "job": "Job"}}}],
      "type": "table"
    }
  ],
  "refresh": "5s",
  "schemaVersion": 39,
  "tags": ["hpc", "overview", "monitoring"],
  "time": {"from": "now-15m", "to": "now"},
  "title": "Overview",
  "uid": "overview"
}'''

    def _get_service_dashboard(self) -> str:
        """Return service monitoring dashboard JSON with container selector"""
        return '''{
  "annotations": {"list": []},
  "editable": true,
  "fiscalYearStartMonth": 0,
  "graphTooltip": 2,
  "id": null,
  "links": [
    {"title": "Overview", "type": "link", "url": "/d/overview/overview", "icon": "dashboard"},
    {"title": "Benchmarks", "type": "link", "url": "/d/benchmarks/benchmarks", "icon": "graph-bar"}
  ],
  "templating": {
    "list": [
      {
        "current": {"selected": true, "text": "All", "value": "$__all"},
        "datasource": {"type": "prometheus", "uid": "prometheus"},
        "definition": "label_values(container_last_seen, name)",
        "includeAll": true,
        "label": "Container",
        "multi": true,
        "name": "container",
        "options": [],
        "query": {"query": "label_values(container_last_seen, name)", "refId": "StandardVariableQuery"},
        "refresh": 2,
        "regex": "/.+/",
        "sort": 1,
        "type": "query"
      },
      {
        "current": {"selected": true, "text": "All", "value": "$__all"},
        "datasource": {"type": "prometheus", "uid": "prometheus"},
        "definition": "label_values(up, job)",
        "includeAll": true,
        "label": "Job",
        "multi": true,
        "name": "job",
        "options": [],
        "query": {"query": "label_values(up, job)", "refId": "StandardVariableQuery"},
        "refresh": 2,
        "sort": 1,
        "type": "query"
      }
    ]
  },
  "panels": [
    {
      "gridPos": {"h": 2, "w": 24, "x": 0, "y": 0},
      "id": 1,
      "options": {"content": "<div style=\\"text-align:center;padding:8px;background:linear-gradient(90deg,#1e3a5f,#059669,#1e3a5f);border-radius:8px\\"><h1 style=\\"color:#fff;font-weight:400;margin:0\\">Service Monitoring</h1><p style=\\"color:#94a3b8;margin:4px 0 0\\">Select containers using the dropdown above</p></div>", "mode": "html"},
      "title": "",
      "transparent": true,
      "type": "text"
    },
    {
      "collapsed": false,
      "gridPos": {"h": 1, "w": 24, "x": 0, "y": 2},
      "id": 2,
      "title": "Resource Overview",
      "type": "row"
    },
    {
      "datasource": {"type": "prometheus", "uid": "prometheus"},
      "fieldConfig": {"defaults": {"color": {"mode": "continuous-GrYlRd"}, "unit": "percentunit", "min": 0, "max": 1, "thresholds": {"mode": "absolute", "steps": [{"color": "green", "value": null}]}}},
      "gridPos": {"h": 6, "w": 6, "x": 0, "y": 3},
      "id": 3,
      "options": {"orientation": "horizontal", "displayMode": "gradient", "showUnfilled": true, "minVizWidth": 8, "minVizHeight": 16, "reduceOptions": {"calcs": ["lastNotNull"]}},
      "targets": [{"expr": "rate(container_cpu_usage_seconds_total{name=~\\"$container\\"}[1m])", "legendFormat": "{{name}}", "refId": "A"}],
      "title": "CPU Usage",
      "type": "bargauge"
    },
    {
      "datasource": {"type": "prometheus", "uid": "prometheus"},
      "fieldConfig": {"defaults": {"color": {"mode": "continuous-BlYlRd"}, "unit": "bytes", "min": 0, "thresholds": {"mode": "absolute", "steps": [{"color": "green", "value": null}]}}},
      "gridPos": {"h": 6, "w": 6, "x": 6, "y": 3},
      "id": 4,
      "options": {"orientation": "horizontal", "displayMode": "gradient", "showUnfilled": true, "minVizWidth": 8, "minVizHeight": 16, "reduceOptions": {"calcs": ["lastNotNull"]}},
      "targets": [{"expr": "container_memory_usage_bytes{name=~\\"$container\\"}", "legendFormat": "{{name}}", "refId": "A"}],
      "title": "Memory Usage",
      "type": "bargauge"
    },
    {
      "datasource": {"type": "prometheus", "uid": "prometheus"},
      "fieldConfig": {"defaults": {"color": {"mode": "continuous-BlPu"}, "unit": "Bps", "min": 0, "thresholds": {"mode": "absolute", "steps": [{"color": "green", "value": null}]}}},
      "gridPos": {"h": 6, "w": 6, "x": 12, "y": 3},
      "id": 5,
      "options": {"orientation": "horizontal", "displayMode": "gradient", "showUnfilled": true, "minVizWidth": 8, "minVizHeight": 16, "reduceOptions": {"calcs": ["lastNotNull"]}},
      "targets": [{"expr": "rate(container_network_receive_bytes_total{name=~\\"$container\\"}[1m])", "legendFormat": "{{name}} RX", "refId": "A"}],
      "title": "Network Receive",
      "type": "bargauge"
    },
    {
      "datasource": {"type": "prometheus", "uid": "prometheus"},
      "fieldConfig": {"defaults": {"color": {"mode": "continuous-YlRd"}, "unit": "Bps", "min": 0, "thresholds": {"mode": "absolute", "steps": [{"color": "green", "value": null}]}}},
      "gridPos": {"h": 6, "w": 6, "x": 18, "y": 3},
      "id": 6,
      "options": {"orientation": "horizontal", "displayMode": "gradient", "showUnfilled": true, "minVizWidth": 8, "minVizHeight": 16, "reduceOptions": {"calcs": ["lastNotNull"]}},
      "targets": [{"expr": "rate(container_network_transmit_bytes_total{name=~\\"$container\\"}[1m])", "legendFormat": "{{name}} TX", "refId": "A"}],
      "title": "Network Transmit",
      "type": "bargauge"
    },
    {
      "collapsed": false,
      "gridPos": {"h": 1, "w": 24, "x": 0, "y": 9},
      "id": 7,
      "title": "CPU Metrics",
      "type": "row"
    },
    {
      "datasource": {"type": "prometheus", "uid": "prometheus"},
      "fieldConfig": {"defaults": {"color": {"mode": "palette-classic"}, "unit": "percentunit", "custom": {"drawStyle": "line", "fillOpacity": 30, "lineWidth": 2, "lineInterpolation": "smooth", "spanNulls": true, "showPoints": "never", "gradientMode": "opacity"}, "min": 0}},
      "gridPos": {"h": 8, "w": 24, "x": 0, "y": 10},
      "id": 8,
      "options": {"legend": {"displayMode": "table", "placement": "right", "showLegend": true, "calcs": ["mean", "max", "lastNotNull"]}, "tooltip": {"mode": "multi", "sort": "desc"}},
      "targets": [{"expr": "rate(container_cpu_usage_seconds_total{name=~\\"$container\\"}[1m])", "legendFormat": "{{name}}", "refId": "A"}],
      "title": "CPU Usage Over Time",
      "type": "timeseries"
    },
    {
      "collapsed": false,
      "gridPos": {"h": 1, "w": 24, "x": 0, "y": 18},
      "id": 9,
      "title": "Memory Metrics",
      "type": "row"
    },
    {
      "datasource": {"type": "prometheus", "uid": "prometheus"},
      "fieldConfig": {"defaults": {"color": {"mode": "palette-classic"}, "unit": "bytes", "custom": {"drawStyle": "line", "fillOpacity": 30, "lineWidth": 2, "lineInterpolation": "smooth", "spanNulls": true, "showPoints": "never", "gradientMode": "opacity"}, "min": 0}},
      "gridPos": {"h": 8, "w": 12, "x": 0, "y": 19},
      "id": 10,
      "options": {"legend": {"displayMode": "table", "placement": "bottom", "showLegend": true, "calcs": ["mean", "max", "lastNotNull"]}, "tooltip": {"mode": "multi", "sort": "desc"}},
      "targets": [{"expr": "container_memory_usage_bytes{name=~\\"$container\\"}", "legendFormat": "{{name}} total", "refId": "A"}],
      "title": "Total Memory Usage",
      "type": "timeseries"
    },
    {
      "datasource": {"type": "prometheus", "uid": "prometheus"},
      "fieldConfig": {"defaults": {"color": {"mode": "palette-classic"}, "unit": "bytes", "custom": {"drawStyle": "line", "fillOpacity": 30, "lineWidth": 2, "lineInterpolation": "smooth", "spanNulls": true, "showPoints": "never"}, "min": 0}},
      "gridPos": {"h": 8, "w": 12, "x": 12, "y": 19},
      "id": 11,
      "options": {"legend": {"displayMode": "table", "placement": "bottom", "showLegend": true, "calcs": ["mean", "max"]}, "tooltip": {"mode": "multi", "sort": "desc"}},
      "targets": [
        {"expr": "container_memory_working_set_bytes{name=~\\"$container\\"}", "legendFormat": "{{name}} working set", "refId": "A"},
        {"expr": "container_memory_cache{name=~\\"$container\\"}", "legendFormat": "{{name}} cache", "refId": "B"}
      ],
      "title": "Memory Breakdown",
      "type": "timeseries"
    },
    {
      "collapsed": false,
      "gridPos": {"h": 1, "w": 24, "x": 0, "y": 27},
      "id": 12,
      "title": "Network I/O",
      "type": "row"
    },
    {
      "datasource": {"type": "prometheus", "uid": "prometheus"},
      "fieldConfig": {"defaults": {"color": {"mode": "palette-classic"}, "unit": "Bps", "custom": {"drawStyle": "line", "fillOpacity": 30, "lineWidth": 2, "lineInterpolation": "smooth", "spanNulls": true, "showPoints": "never"}}},
      "gridPos": {"h": 8, "w": 12, "x": 0, "y": 28},
      "id": 13,
      "options": {"legend": {"displayMode": "table", "placement": "bottom", "showLegend": true, "calcs": ["mean", "max", "lastNotNull"]}, "tooltip": {"mode": "multi", "sort": "desc"}},
      "targets": [
        {"expr": "rate(container_network_receive_bytes_total{name=~\\"$container\\"}[1m])", "legendFormat": "{{name}} RX", "refId": "A"},
        {"expr": "-rate(container_network_transmit_bytes_total{name=~\\"$container\\"}[1m])", "legendFormat": "{{name}} TX", "refId": "B"}
      ],
      "title": "Network Throughput (RX+, TX-)",
      "type": "timeseries"
    },
    {
      "datasource": {"type": "prometheus", "uid": "prometheus"},
      "fieldConfig": {"defaults": {"color": {"mode": "palette-classic"}, "unit": "bytes", "custom": {"drawStyle": "line", "fillOpacity": 30, "lineWidth": 2, "lineInterpolation": "smooth", "spanNulls": true, "showPoints": "never"}}},
      "gridPos": {"h": 8, "w": 12, "x": 12, "y": 28},
      "id": 14,
      "options": {"legend": {"displayMode": "table", "placement": "bottom", "showLegend": true, "calcs": ["lastNotNull"]}, "tooltip": {"mode": "multi", "sort": "desc"}},
      "targets": [
        {"expr": "container_network_receive_bytes_total{name=~\\"$container\\"}", "legendFormat": "{{name}} RX total", "refId": "A"},
        {"expr": "container_network_transmit_bytes_total{name=~\\"$container\\"}", "legendFormat": "{{name}} TX total", "refId": "B"}
      ],
      "title": "Cumulative Network I/O",
      "type": "timeseries"
    },
    {
      "collapsed": false,
      "gridPos": {"h": 1, "w": 24, "x": 0, "y": 36},
      "id": 15,
      "title": "Disk I/O",
      "type": "row"
    },
    {
      "datasource": {"type": "prometheus", "uid": "prometheus"},
      "fieldConfig": {"defaults": {"color": {"mode": "palette-classic"}, "unit": "bytes", "custom": {"drawStyle": "bars", "fillOpacity": 80, "lineWidth": 1, "showPoints": "never"}}},
      "gridPos": {"h": 8, "w": 12, "x": 0, "y": 37},
      "id": 16,
      "options": {"legend": {"displayMode": "table", "placement": "bottom", "showLegend": true, "calcs": ["lastNotNull"]}, "tooltip": {"mode": "multi"}},
      "targets": [{"expr": "container_fs_usage_bytes{name=~\\"$container\\"}", "legendFormat": "{{name}}", "refId": "A"}],
      "title": "Filesystem Usage",
      "type": "timeseries"
    },
    {
      "datasource": {"type": "prometheus", "uid": "prometheus"},
      "fieldConfig": {"defaults": {"color": {"mode": "thresholds"}, "unit": "percent", "max": 100, "min": 0, "thresholds": {"mode": "absolute", "steps": [{"color": "green", "value": null}, {"color": "yellow", "value": 60}, {"color": "red", "value": 80}]}}},
      "gridPos": {"h": 8, "w": 12, "x": 12, "y": 37},
      "id": 17,
      "options": {"orientation": "auto", "showThresholdLabels": false, "showThresholdMarkers": true, "reduceOptions": {"calcs": ["lastNotNull"]}},
      "targets": [{"expr": "(container_memory_usage_bytes{name=~\\"$container\\"} / container_spec_memory_limit_bytes{name=~\\"$container\\"}) * 100", "legendFormat": "{{name}}", "refId": "A"}],
      "title": "Memory Limit Usage %",
      "type": "gauge"
    }
  ],
  "refresh": "5s",
  "schemaVersion": 39,
  "tags": ["hpc", "services", "containers", "monitoring"],
  "time": {"from": "now-15m", "to": "now"},
  "title": "Service Monitoring",
  "uid": "service-monitoring"
}'''

    def _get_benchmark_dashboard(self) -> str:
        """Return benchmark-focused dashboard JSON"""
        return '''{
  "annotations": {"list": []},
  "editable": true,
  "fiscalYearStartMonth": 0,
  "graphTooltip": 2,
  "id": null,
  "links": [
    {"title": "Overview", "type": "link", "url": "/d/overview/overview", "icon": "dashboard"},
    {"title": "Services", "type": "link", "url": "/d/service-monitoring/service-monitoring", "icon": "apps"}
  ],
  "templating": {
    "list": [
      {
        "current": {"selected": true, "text": "All", "value": "$__all"},
        "datasource": {"type": "prometheus", "uid": "prometheus"},
        "definition": "label_values(up, job)",
        "includeAll": true,
        "label": "Service",
        "multi": true,
        "name": "service",
        "options": [],
        "query": {"query": "label_values(up, job)", "refId": "StandardVariableQuery"},
        "refresh": 2,
        "regex": "/.*cadvisor.*/",
        "sort": 1,
        "type": "query"
      }
    ]
  },
  "panels": [
    {
      "gridPos": {"h": 2, "w": 24, "x": 0, "y": 0},
      "id": 1,
      "options": {"content": "<div style=\\"text-align:center;padding:8px;background:linear-gradient(90deg,#1e3a5f,#dc2626,#1e3a5f);border-radius:8px\\"><h1 style=\\"color:#fff;font-weight:400;margin:0\\">Benchmark Performance</h1><p style=\\"color:#94a3b8;margin:4px 0 0\\">Resource utilization during benchmark runs</p></div>", "mode": "html"},
      "title": "",
      "transparent": true,
      "type": "text"
    },
    {
      "collapsed": false,
      "gridPos": {"h": 1, "w": 24, "x": 0, "y": 2},
      "id": 2,
      "title": "Summary Statistics",
      "type": "row"
    },
    {
      "datasource": {"type": "prometheus", "uid": "prometheus"},
      "fieldConfig": {"defaults": {"color": {"mode": "thresholds"}, "thresholds": {"mode": "absolute", "steps": [{"color": "green", "value": null}, {"color": "yellow", "value": 0.5}, {"color": "red", "value": 0.8}]}, "unit": "percentunit", "min": 0, "max": 1}},
      "gridPos": {"h": 4, "w": 6, "x": 0, "y": 3},
      "id": 3,
      "options": {"colorMode": "background", "graphMode": "area", "justifyMode": "center", "reduceOptions": {"calcs": ["mean"]}},
      "targets": [{"expr": "avg(rate(container_cpu_usage_seconds_total{name=~\\".+\\"}[5m]))", "refId": "A"}],
      "title": "Avg CPU (5m)",
      "type": "stat"
    },
    {
      "datasource": {"type": "prometheus", "uid": "prometheus"},
      "fieldConfig": {"defaults": {"color": {"mode": "thresholds"}, "thresholds": {"mode": "absolute", "steps": [{"color": "green", "value": null}, {"color": "yellow", "value": 0.7}, {"color": "red", "value": 0.9}]}, "unit": "percentunit", "min": 0, "max": 1}},
      "gridPos": {"h": 4, "w": 6, "x": 6, "y": 3},
      "id": 4,
      "options": {"colorMode": "background", "graphMode": "area", "justifyMode": "center", "reduceOptions": {"calcs": ["max"]}},
      "targets": [{"expr": "max(rate(container_cpu_usage_seconds_total{name=~\\".+\\"}[1m]))", "refId": "A"}],
      "title": "Peak CPU (1m)",
      "type": "stat"
    },
    {
      "datasource": {"type": "prometheus", "uid": "prometheus"},
      "fieldConfig": {"defaults": {"color": {"mode": "thresholds"}, "thresholds": {"mode": "absolute", "steps": [{"color": "blue", "value": null}]}, "unit": "bytes"}},
      "gridPos": {"h": 4, "w": 6, "x": 12, "y": 3},
      "id": 5,
      "options": {"colorMode": "background", "graphMode": "area", "justifyMode": "center", "reduceOptions": {"calcs": ["mean"]}},
      "targets": [{"expr": "avg(container_memory_usage_bytes{name=~\\".+\\"})", "refId": "A"}],
      "title": "Avg Memory",
      "type": "stat"
    },
    {
      "datasource": {"type": "prometheus", "uid": "prometheus"},
      "fieldConfig": {"defaults": {"color": {"mode": "thresholds"}, "thresholds": {"mode": "absolute", "steps": [{"color": "purple", "value": null}]}, "unit": "bytes"}},
      "gridPos": {"h": 4, "w": 6, "x": 18, "y": 3},
      "id": 6,
      "options": {"colorMode": "background", "graphMode": "area", "justifyMode": "center", "reduceOptions": {"calcs": ["max"]}},
      "targets": [{"expr": "max(container_memory_usage_bytes{name=~\\".+\\"})", "refId": "A"}],
      "title": "Peak Memory",
      "type": "stat"
    },
    {
      "collapsed": false,
      "gridPos": {"h": 1, "w": 24, "x": 0, "y": 7},
      "id": 7,
      "title": "CPU Performance Timeline",
      "type": "row"
    },
    {
      "datasource": {"type": "prometheus", "uid": "prometheus"},
      "fieldConfig": {"defaults": {"color": {"mode": "palette-classic"}, "unit": "percentunit", "custom": {"drawStyle": "line", "fillOpacity": 40, "lineWidth": 2, "lineInterpolation": "smooth", "spanNulls": true, "showPoints": "never", "gradientMode": "opacity", "stacking": {"mode": "none"}}, "min": 0}},
      "gridPos": {"h": 10, "w": 24, "x": 0, "y": 8},
      "id": 8,
      "options": {"legend": {"displayMode": "table", "placement": "right", "showLegend": true, "calcs": ["mean", "max", "lastNotNull"]}, "tooltip": {"mode": "multi", "sort": "desc"}},
      "targets": [{"expr": "rate(container_cpu_usage_seconds_total{name=~\\".+\\"}[30s])", "legendFormat": "{{name}}", "refId": "A"}],
      "title": "CPU Usage Rate (30s window) - Live Benchmark View",
      "type": "timeseries"
    },
    {
      "collapsed": false,
      "gridPos": {"h": 1, "w": 24, "x": 0, "y": 18},
      "id": 9,
      "title": "Memory Performance Timeline",
      "type": "row"
    },
    {
      "datasource": {"type": "prometheus", "uid": "prometheus"},
      "fieldConfig": {"defaults": {"color": {"mode": "palette-classic"}, "unit": "bytes", "custom": {"drawStyle": "line", "fillOpacity": 40, "lineWidth": 2, "lineInterpolation": "smooth", "spanNulls": true, "showPoints": "never", "gradientMode": "opacity"}, "min": 0}},
      "gridPos": {"h": 10, "w": 24, "x": 0, "y": 19},
      "id": 10,
      "options": {"legend": {"displayMode": "table", "placement": "right", "showLegend": true, "calcs": ["mean", "max", "lastNotNull"]}, "tooltip": {"mode": "multi", "sort": "desc"}},
      "targets": [{"expr": "container_memory_usage_bytes{name=~\\".+\\"}", "legendFormat": "{{name}}", "refId": "A"}],
      "title": "Memory Usage - Live Benchmark View",
      "type": "timeseries"
    },
    {
      "collapsed": false,
      "gridPos": {"h": 1, "w": 24, "x": 0, "y": 29},
      "id": 11,
      "title": "Network Performance",
      "type": "row"
    },
    {
      "datasource": {"type": "prometheus", "uid": "prometheus"},
      "fieldConfig": {"defaults": {"color": {"mode": "palette-classic"}, "unit": "Bps", "custom": {"drawStyle": "line", "fillOpacity": 30, "lineWidth": 2, "lineInterpolation": "smooth", "spanNulls": true, "showPoints": "never"}}},
      "gridPos": {"h": 8, "w": 12, "x": 0, "y": 30},
      "id": 12,
      "options": {"legend": {"displayMode": "table", "placement": "bottom", "showLegend": true, "calcs": ["mean", "max"]}, "tooltip": {"mode": "multi", "sort": "desc"}},
      "targets": [{"expr": "rate(container_network_receive_bytes_total{name=~\\".+\\"}[30s])", "legendFormat": "{{name}} RX", "refId": "A"}],
      "title": "Network Receive Rate",
      "type": "timeseries"
    },
    {
      "datasource": {"type": "prometheus", "uid": "prometheus"},
      "fieldConfig": {"defaults": {"color": {"mode": "palette-classic"}, "unit": "Bps", "custom": {"drawStyle": "line", "fillOpacity": 30, "lineWidth": 2, "lineInterpolation": "smooth", "spanNulls": true, "showPoints": "never"}}},
      "gridPos": {"h": 8, "w": 12, "x": 12, "y": 30},
      "id": 13,
      "options": {"legend": {"displayMode": "table", "placement": "bottom", "showLegend": true, "calcs": ["mean", "max"]}, "tooltip": {"mode": "multi", "sort": "desc"}},
      "targets": [{"expr": "rate(container_network_transmit_bytes_total{name=~\\".+\\"}[30s])", "legendFormat": "{{name}} TX", "refId": "A"}],
      "title": "Network Transmit Rate",
      "type": "timeseries"
    },
    {
      "collapsed": false,
      "gridPos": {"h": 1, "w": 24, "x": 0, "y": 38},
      "id": 14,
      "title": "Resource Comparison",
      "type": "row"
    },
    {
      "datasource": {"type": "prometheus", "uid": "prometheus"},
      "fieldConfig": {"defaults": {"color": {"mode": "continuous-GrYlRd"}, "unit": "percentunit", "min": 0, "max": 1, "custom": {"hideFrom": {"legend": false, "tooltip": false, "viz": false}}}},
      "gridPos": {"h": 8, "w": 8, "x": 0, "y": 39},
      "id": 15,
      "options": {"calculate": false, "cellGap": 2, "color": {"mode": "scheme", "scheme": "RdYlGn", "reverse": true}, "yAxis": {"axisPlacement": "left"}},
      "targets": [{"expr": "rate(container_cpu_usage_seconds_total{name=~\\".+\\"}[1m])", "legendFormat": "{{name}}", "refId": "A", "format": "heatmap"}],
      "title": "CPU Heatmap",
      "type": "heatmap"
    },
    {
      "datasource": {"type": "prometheus", "uid": "prometheus"},
      "fieldConfig": {"defaults": {"color": {"mode": "continuous-GrYlRd"}, "unit": "percentunit", "min": 0, "max": 1, "thresholds": {"mode": "absolute", "steps": [{"color": "green", "value": null}, {"color": "yellow", "value": 0.5}, {"color": "red", "value": 0.8}]}}},
      "gridPos": {"h": 8, "w": 8, "x": 8, "y": 39},
      "id": 16,
      "options": {"orientation": "horizontal", "displayMode": "lcd", "showUnfilled": true, "minVizWidth": 8, "minVizHeight": 16, "reduceOptions": {"calcs": ["mean"]}},
      "targets": [{"expr": "avg_over_time(rate(container_cpu_usage_seconds_total{name=~\\".+\\"}[1m])[5m:])", "legendFormat": "{{name}}", "refId": "A"}],
      "title": "Avg CPU Over Benchmark",
      "type": "bargauge"
    },
    {
      "datasource": {"type": "prometheus", "uid": "prometheus"},
      "fieldConfig": {"defaults": {"color": {"mode": "continuous-BlYlRd"}, "unit": "bytes", "min": 0, "thresholds": {"mode": "absolute", "steps": [{"color": "green", "value": null}]}}},
      "gridPos": {"h": 8, "w": 8, "x": 16, "y": 39},
      "id": 17,
      "options": {"orientation": "horizontal", "displayMode": "lcd", "showUnfilled": true, "minVizWidth": 8, "minVizHeight": 16, "reduceOptions": {"calcs": ["mean"]}},
      "targets": [{"expr": "avg_over_time(container_memory_usage_bytes{name=~\\".+\\"}[5m])", "legendFormat": "{{name}}", "refId": "A"}],
      "title": "Avg Memory Over Benchmark",
      "type": "bargauge"
    },
    {
      "collapsed": false,
      "gridPos": {"h": 1, "w": 24, "x": 0, "y": 47},
      "id": 18,
      "title": "Service Health",
      "type": "row"
    },
    {
      "datasource": {"type": "prometheus", "uid": "prometheus"},
      "fieldConfig": {"defaults": {"color": {"mode": "thresholds"}, "mappings": [{"options": {"0": {"color": "red", "text": "DOWN"}, "1": {"color": "green", "text": "UP"}}, "type": "value"}], "thresholds": {"mode": "absolute", "steps": [{"color": "red", "value": null}, {"color": "green", "value": 1}]}}},
      "gridPos": {"h": 6, "w": 24, "x": 0, "y": 48},
      "id": 19,
      "options": {"showHeader": true, "cellHeight": "sm"},
      "targets": [{"expr": "up", "format": "table", "instant": true, "refId": "A"}],
      "title": "Scrape Target Health",
      "transformations": [{"id": "organize", "options": {"excludeByName": {"Time": true, "__name__": true}, "renameByName": {"Value": "Status", "instance": "Instance", "job": "Job"}}}],
      "type": "table"
    }
  ],
  "refresh": "5s",
  "schemaVersion": 39,
  "tags": ["hpc", "benchmarks", "performance"],
  "time": {"from": "now-15m", "to": "now"},
  "title": "Benchmarks",
  "uid": "benchmarks"
}'''

    def get_container_command(self) -> str:
        """Generate Grafana container execution command"""
        cmd_parts = ["apptainer exec"]
        
        # Add bind mounts for Grafana data, logs, provisioning, and dashboards
        cmd_parts.append("--bind $HOME/grafana/data:/var/lib/grafana")
        cmd_parts.append("--bind $HOME/grafana/logs:/var/log/grafana")
        cmd_parts.append("--bind $HOME/grafana/provisioning:/etc/grafana/provisioning")
        cmd_parts.append("--bind $HOME/grafana/dashboards:/var/lib/grafana/dashboards")
        
        # Add environment variables
        for key, value in self.environment.items():
            cmd_parts.append(f"--env {key}={value}")
        
        # Resolve container path
        container_path = self._resolve_container_path()
        cmd_parts.append(container_path)
        
        # Grafana command
        if self.command:
            cmd_parts.append(self.command)
            if self.args:
                cmd_parts.extend(self.args)
        else:
            # Default Grafana command
            cmd_parts.extend([
                "grafana-server",
                "--homepath=/usr/share/grafana",
                "--config=/etc/grafana/grafana.ini"
            ])
        
        # Run in background
        cmd_parts.append("&")
        
        return " ".join(cmd_parts)
    
    def get_health_check_commands(self) -> List[str]:
        """Grafana-specific health monitoring"""
        return [
            "",
            "# Wait for Grafana to start",
            "sleep 10",
            "",
            "# Get the Grafana process ID",
            "GRAFANA_PID=$!",
            "",
            "# Display Grafana endpoint",
            "echo '========================================='",
            "echo 'Grafana is running on:'",
            "echo \"http://$(hostname):3000\"",
            "echo 'Default credentials: admin / admin'",
            "echo '========================================='",
            "",
            "# Check if Grafana is responding",
            "for i in {1..10}; do",
            "    if curl -s http://localhost:3000/api/health | grep -q 'ok'; then",
            "        echo \"Grafana is ready!\"",
            "        break",
            "    fi",
            "    echo \"Waiting for Grafana to be ready... ($i/10)\"",
            "    sleep 5",
            "done",
            "",
            "# Monitor Grafana process",
            "echo 'Monitoring Grafana... (press Ctrl+C to stop)'",
            "while kill -0 $GRAFANA_PID 2>/dev/null; do",
            "    sleep 60",
            "    echo \"Grafana still running on $(hostname):3000\"",
            "done",
            "",
            "echo 'Grafana service finished'"
        ]


# Register the Grafana service with the factory
JobFactory.register_service('grafana', GrafanaService)
