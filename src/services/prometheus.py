"""
Prometheus Service Implementation
"""

from typing import Dict, Any, List
from dataclasses import dataclass

from services.base import Service, JobFactory


@dataclass
class PrometheusService(Service):
    """Prometheus monitoring service for HPC environments"""
    
    # Store monitoring targets
    monitoring_targets: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Initialize monitoring targets"""
        if self.monitoring_targets is None:
            self.monitoring_targets = []
    
    @classmethod
    def from_recipe(cls, recipe: Dict[str, Any], config: Dict[str, Any]) -> 'PrometheusService':
        """Create Prometheus service from recipe"""
        service_config = recipe.get('service', {})
        
        # Get monitoring targets from recipe
        monitoring_targets = service_config.get('monitoring_targets', [])
        
        instance = cls(
            name=service_config.get('name', 'prometheus'),
            container_image=service_config.get('container_image', 'prometheus.sif'),
            resources=service_config.get('resources', {}),
            environment=service_config.get('environment', {}),
            command=service_config.get('command'),
            args=service_config.get('args', []),
            ports=service_config.get('ports', [9090]),
            container=service_config.get('container', {}),
            config=config,
            enable_cadvisor=service_config.get('enable_cadvisor', False),
            cadvisor_port=service_config.get('cadvisor_port', 8080)
        )
        instance.monitoring_targets = monitoring_targets
        return instance
    
    def get_service_setup_commands(self) -> List[str]:
        """Setup Prometheus configuration and data directories"""
        # First get base service setup (includes cAdvisor if enabled)
        commands = super().get_service_setup_commands()
        
        commands.extend([
            "# Prometheus setup",
            "mkdir -p $HOME/prometheus/data",
            "mkdir -p $HOME/prometheus/config",
            "",
            "# Create Prometheus configuration",
            "cat > $HOME/prometheus/config/prometheus.yml << 'EOF'",
            "global:",
            "  scrape_interval: 15s",
            "  evaluation_interval: 15s",
            "",
            "scrape_configs:",
        ])
        
        # Add monitoring targets from recipe
        if self.monitoring_targets:
            for target in self.monitoring_targets:
                service_id = target.get('service_id')
                job_name = target.get('job_name', service_id)
                
                # Check if this is a cAdvisor target (port 8080 by default) or service target
                port = target.get('port', 8080)  # Default to cAdvisor port
                
                # Host should already be resolved before script generation
                if 'host' in target:
                    host = target['host']
                    commands.extend([
                        "",
                        f"  - job_name: '{job_name}'",
                        "    static_configs:",
                        f"      - targets: ['{host}:{port}']",
                    ])
                    
                    # If monitoring cAdvisor, also add labels to identify the container host
                    if port == 8080 or 'cadvisor' in job_name.lower():
                        commands.extend([
                            "        labels:",
                            f"          instance: '{host}'",
                            "          job_type: 'cadvisor'",
                        ])
                else:
                    # If host is not provided, skip this target
                    commands.extend([
                        "",
                        f"  # Warning: Could not resolve host for service {service_id}",
                        f"  # Skipping monitoring target: {job_name}",
                    ])
        
        commands.extend([
            "EOF",
            "",
            "echo 'Prometheus configuration created:'",
            "cat $HOME/prometheus/config/prometheus.yml",
            ""
        ])
        
        return commands
    
    def get_container_command(self) -> str:
        """Generate Prometheus container execution command"""
        cmd_parts = ["apptainer exec"]
        
        # Add bind mounts for Prometheus data and config
        cmd_parts.append("--bind $HOME/prometheus/data:/prometheus")
        cmd_parts.append("--bind $HOME/prometheus/config:/etc/prometheus")
        
        # Add environment variables
        for key, value in self.environment.items():
            cmd_parts.append(f"--env {key}={value}")
        
        # Resolve container path
        container_path = self._resolve_container_path()
        cmd_parts.append(container_path)
        
        # Prometheus command
        if self.command:
            cmd_parts.append(self.command)
            if self.args:
                cmd_parts.extend(self.args)
        else:
            # Default Prometheus command
            cmd_parts.extend([
                "prometheus",
                "--config.file=/etc/prometheus/prometheus.yml",
                "--storage.tsdb.path=/prometheus",
                "--web.listen-address=0.0.0.0:9090"
            ])
        
        # Run in background
        cmd_parts.append("&")
        
        return " ".join(cmd_parts)
    
    def get_health_check_commands(self) -> List[str]:
        """Prometheus-specific health monitoring"""
        return [
            "",
            "# Wait for Prometheus to start",
            "sleep 10",
            "",
            "# Get the Prometheus process ID",
            "PROMETHEUS_PID=$!",
            "",
            "# Display Prometheus endpoint",
            "echo '========================================='",
            "echo 'Prometheus is running on:'",
            "echo \"http://$(hostname):9090\"",
            "echo '========================================='",
            "",
            "# Check if Prometheus is responding",
            "for i in {1..5}; do",
            "    if curl -s http://localhost:9090/-/ready > /dev/null 2>&1; then",
            "        echo \"Prometheus is ready!\"",
            "        break",
            "    fi",
            "    echo \"Waiting for Prometheus to be ready... ($i/5)\"",
            "    sleep 5",
            "done",
            "",
            "# Monitor Prometheus process",
            "echo 'Monitoring Prometheus... (press Ctrl+C to stop)'",
            "while kill -0 $PROMETHEUS_PID 2>/dev/null; do",
            "    sleep 60",
            "    echo \"Prometheus still running on $(hostname):9090\"",
            "done",
            "",
            "echo 'Prometheus service finished'"
        ]


# Register the Prometheus service with the factory
JobFactory.register_service('prometheus', PrometheusService)
