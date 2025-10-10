"""
Script Generator for SLURM jobs
"""

import os
import logging
from typing import Dict, Any, List, Optional
from base import ServiceConfig, ClientConfig

class ScriptGenerator:
    """Generates SLURM batch scripts for services and clients"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Default SLURM configuration
        self.default_slurm_config = {
            'account': config.get('slurm', {}).get('account', 'p200981'),
            'partition': config.get('slurm', {}).get('partition', 'gpu'),
            'qos': config.get('slurm', {}).get('qos', 'default'),
            'time': config.get('slurm', {}).get('time', '01:00:00'),
            'nodes': config.get('slurm', {}).get('nodes', 1),
            'ntasks': config.get('slurm', {}).get('ntasks', 1),
            'ntasks_per_node': config.get('slurm', {}).get('ntasks_per_node', 1)
        }
    
    def generate_service_script(self, service_config: ServiceConfig, service_id: str) -> str:
        """Generate SLURM script for a service"""
        
        # Extract resource requirements
        resources = service_config.resources
        slurm_config = {**self.default_slurm_config, **resources.get('slurm', {})}
        
        # Adjust time allocation if auto-building is enabled
        if self.config.get('containers', {}).get('auto_build', False):
            build_timeout = self.config.get('containers', {}).get('build_timeout', '30:00')
            original_time = slurm_config.get('time', '01:00:00')
            # Use the longer of build timeout or original time
            if self._compare_time_strings(build_timeout, original_time) > 0:
                slurm_config['time'] = build_timeout
                self.logger.info(f"Extended SLURM time to {build_timeout} for container auto-build")
        
        script_lines = [
            "#!/bin/bash -l",
            f"#SBATCH --job-name={service_config.name}_{service_id}",
            f"#SBATCH --time={slurm_config['time']}",
            f"#SBATCH --qos={slurm_config['qos']}",
            f"#SBATCH --partition={slurm_config['partition']}",
            f"#SBATCH --account={slurm_config['account']}",
            f"#SBATCH --nodes={slurm_config['nodes']}",
            f"#SBATCH --ntasks={slurm_config['ntasks']}",
            f"#SBATCH --ntasks-per-node={slurm_config['ntasks_per_node']}",
            "",
            "# Load required modules",
            "module add Apptainer",
            ""
        ]
        
        # Add GPU requirements if needed
        if resources.get('gpu', 0) > 0:
            script_lines.insert(-2, f"#SBATCH --gres=gpu:{resources['gpu']}")
        
        # Add memory requirements if specified
        if resources.get('memory'):
            script_lines.insert(-2, f"#SBATCH --mem={resources['memory']}")
        
        # Add environment variables
        if service_config.environment:
            script_lines.append("# Set environment variables")
            for key, value in service_config.environment.items():
                script_lines.append(f"export {key}={value}")
            script_lines.append("")
        
        # Add container build commands (if auto_build is enabled)
        container_build_commands = self._generate_container_build_commands(service_config)
        if container_build_commands:
            script_lines.extend(container_build_commands)
        
        # Add service-specific setup
        if service_config.name == "ollama":
            script_lines.extend(self._generate_ollama_setup())
        
        # Add container execution command
        container_cmd = self._build_container_command(service_config)
        script_lines.append("# Start the service")
        script_lines.append(container_cmd)
        
        # Add health check and keep-alive
        script_lines.extend([
            "",
            "# Keep the job alive and monitor service",
            "sleep 30  # Allow service to start",
            "",
            "# Simple health check loop",
            "echo 'Service started, monitoring...'",
            "while kill -0 $! 2>/dev/null; do",
            "    sleep 60",
            "done",
            "",
            "echo 'Service finished'"
        ])
        
        return "\n".join(script_lines)
    
    def generate_client_script(self, client_config: ClientConfig, client_id: str, 
                             target_service_host: str = None) -> str:
        """Generate SLURM script for a client"""
        
        # Extract resource requirements
        resources = client_config.resources
        slurm_config = {**self.default_slurm_config, **resources.get('slurm', {})}
        
        script_lines = [
            "#!/bin/bash -l",
            f"#SBATCH --job-name={client_config.name}_{client_id}",
            f"#SBATCH --time={slurm_config['time']}",
            f"#SBATCH --qos={slurm_config['qos']}",
            f"#SBATCH --partition={slurm_config['partition']}",
            f"#SBATCH --account={slurm_config['account']}",
            f"#SBATCH --nodes={slurm_config['nodes']}",
            f"#SBATCH --ntasks={slurm_config['ntasks']}",
            f"#SBATCH --ntasks-per-node={slurm_config['ntasks_per_node']}",
            "",
            "# Load required modules",
            "module add Apptainer",
            ""
        ]
        
        # Add GPU requirements if needed
        if resources.get('gpu', 0) > 0:
            script_lines.insert(-2, f"#SBATCH --gres=gpu:{resources['gpu']}")
        
        # Add memory requirements if specified
        if resources.get('memory'):
            script_lines.insert(-2, f"#SBATCH --mem={resources['memory']}")
        
        # Add environment variables
        if client_config.environment:
            script_lines.append("# Set environment variables")
            for key, value in client_config.environment.items():
                script_lines.append(f"export {key}={value}")
            script_lines.append("")
        
        # Add target service information
        if target_service_host:
            script_lines.append(f"export TARGET_SERVICE_HOST={target_service_host}")
            script_lines.append("")
            self.logger.info(f"Added TARGET_SERVICE_HOST environment variable: {target_service_host}")
        else:
            self.logger.warning("No target_service_host provided - TARGET_SERVICE_HOST will not be set")
        
        # Add client container build commands (if auto_build is enabled)
        client_container_build_commands = self._generate_client_container_build_commands(client_config)
        if client_container_build_commands:
            script_lines.extend(client_container_build_commands)
        
        # Add client-specific setup
        if client_config.workload_type == "ollama_benchmark":
            script_lines.extend(self._generate_ollama_client_setup())
        
        # Add container execution command
        container_cmd = self._build_client_container_command(client_config, target_service_host)
        script_lines.extend([
            "# Start the client workload",
            "echo '=== CONTAINER EXECUTION DEBUG ==='",
            f"echo 'Container command: {container_cmd}'",
            "echo '=================================='",
            "",
            container_cmd,
            "",
            "echo 'Container execution completed'"
        ])
        
        # Add result collection commands
        if client_config.workload_type == "ollama_benchmark":
            output_file = client_config.parameters.get('output_file', '/tmp/ollama_benchmark_results.json')
            script_lines.extend([
                "",
                "# Copy results back to submit directory",
                "mkdir -p $SLURM_SUBMIT_DIR/results",
                f"cp {output_file} $SLURM_SUBMIT_DIR/results/ 2>/dev/null || echo 'Warning: Could not copy results file'",
                "echo 'Results collection completed'"
            ])
        
        script_lines.append("")
        script_lines.append("echo 'Client workload completed'")
        
        return "\n".join(script_lines)
    
    def _build_container_command(self, service_config: ServiceConfig) -> str:
        """Build the apptainer exec command for a service"""
        
        cmd_parts = ["apptainer exec"]
        
        # Add GPU support if needed
        if service_config.resources.get('gpu', 0) > 0:
            cmd_parts.append("--nv")
        
        # Add environment variables
        for key, value in service_config.environment.items():
            cmd_parts.append(f"--env {key}={value}")
        
        # Add container image with base path
        container_base_path = self.config.get('containers', {}).get('base_path', '')
        if container_base_path and not service_config.container_image.startswith('/'):
            container_path = f"{container_base_path}/{service_config.container_image}"
        else:
            container_path = service_config.container_image
        cmd_parts.append(container_path)
        
        # Add command
        if service_config.command:
            cmd_parts.append(service_config.command)
            if service_config.args:
                cmd_parts.extend(service_config.args)
        
        # Run in background for services
        cmd_parts.append("&")
        
        return " ".join(cmd_parts)
    
    def _generate_container_build_commands(self, service_config: ServiceConfig) -> List[str]:
        """Generate commands to build container if it doesn't exist"""
        commands = []
        
        # Check if auto_build is enabled
        if not self.config.get('containers', {}).get('auto_build', False):
            return commands
        
        container_base_path = self.config.get('containers', {}).get('base_path', '')
        if container_base_path and not service_config.container_image.startswith('/'):
            container_path = f"{container_base_path}/{service_config.container_image}"
        else:
            container_path = service_config.container_image
        
        # Get docker source for this service
        docker_sources = self.config.get('containers', {}).get('docker_sources', {})
        docker_source = docker_sources.get(service_config.name)
        force_rebuild = self.config.get('containers', {}).get('force_rebuild', False)
        
        if docker_source:
            commands.append("# Container management")
            commands.append(f"mkdir -p {container_base_path}")
            
            if force_rebuild:
                commands.extend([
                    f"echo \"Force rebuild enabled, building container from {docker_source}...\"",
                    f"echo \"Starting container build at $(date)\"",
                    f"apptainer build --force {container_path} {docker_source}",
                ])
            else:
                commands.extend([
                    f"if [ ! -f \"{container_path}\" ]; then",
                    f"    echo \"Container {container_path} not found, building from {docker_source}...\"",
                    f"    echo \"Starting container build at $(date)\"",
                    f"    apptainer build {container_path} {docker_source}",
                ])
            
            commands.extend([
                f"if [ $? -eq 0 ]; then",
                f"    echo \"Container built successfully at $(date)\"",
                f"else",
                f"    echo \"Container build failed at $(date)\"",
                f"    exit 1",
                f"fi",
            ])
            
            if not force_rebuild:
                commands.extend([
                    "else",
                    f"    echo \"Container {container_path} already exists\"",
                    "fi",
                ])
            
            commands.append("")
        
        return commands
    
    def _build_client_container_command(self, client_config: ClientConfig, target_service_host: str = None) -> str:
        """Build the apptainer exec command for a client"""
        
        cmd_parts = ["apptainer exec"]
        
        # Add GPU support if needed
        if client_config.resources.get('gpu', 0) > 0:
            cmd_parts.append("--nv")
        
        # Add environment variables
        for key, value in client_config.environment.items():
            cmd_parts.append(f"--env {key}={value}")
        
        # Mount benchmark scripts directory
        cmd_parts.append("--bind $HOME/benchmark_scripts:/app")
        
        # Add container image with base path
        container_base_path = self.config.get('containers', {}).get('base_path', '')
        if container_base_path and not client_config.container_image.startswith('/'):
            container_path = f"{container_base_path}/{client_config.container_image}"
        else:
            container_path = client_config.container_image
        cmd_parts.append(container_path)
        
        # Add workload-specific command
        if client_config.workload_type == "ollama_benchmark":
            python_cmd = "python /app/ollama_benchmark.py"
            endpoint = self._resolve_service_endpoint(client_config, target_service_host, default_port=11434)
            self.logger.info(f"Resolved endpoint for ollama_benchmark: {endpoint}")
            if endpoint:
                python_cmd += f" --endpoint={endpoint}"
                self.logger.info(f"Python command with endpoint: {python_cmd}")
            else:
                self.logger.warning("No endpoint resolved for ollama_benchmark - missing --endpoint argument!")
            
            # Add other parameters
            for key, value in client_config.parameters.items():
                if key == 'endpoint':  # Skip endpoint as it's handled above
                    continue
                cli_key = key.replace('_', '-')
                python_cmd += f" --{cli_key}={value}"
            
            self.logger.info(f"Final ollama_benchmark command: {python_cmd}")
            # Run inside container with dependency installation first
            cmd_parts.extend(["bash", "-c", f'"pip install requests && {python_cmd}"'])
            
        elif client_config.workload_type == "postgresql_benchmark":
            python_cmd = "python /app/postgresql_benchmark.py"
            endpoint = self._resolve_service_endpoint(client_config, target_service_host, default_port=5432, protocol="")
            if endpoint:
                python_cmd += f" --host={target_service_host} --port={client_config.target_service.get('port', 5432)}"
            
            # Add other parameters
            for key, value in client_config.parameters.items():
                cli_key = key.replace('_', '-')
                python_cmd += f" --{cli_key}={value}"
            
            cmd_parts.extend(["bash", "-c", f'"pip install psycopg2-binary && {python_cmd}"'])
            
        elif client_config.workload_type == "vector_benchmark":
            python_cmd = "python /app/vector_benchmark.py"
            endpoint = self._resolve_service_endpoint(client_config, target_service_host, default_port=8000)
            if endpoint:
                python_cmd += f" --endpoint={endpoint}"
            
            # Add other parameters
            for key, value in client_config.parameters.items():
                if key == 'endpoint':  # Skip endpoint as it's handled above
                    continue
                cli_key = key.replace('_', '-')
                python_cmd += f" --{cli_key}={value}"
            
            cmd_parts.extend(["bash", "-c", f'"pip install chromadb requests && {python_cmd}"'])
            
        else:
            # Generic workload
            cmd_parts.extend(["echo", f"'Running generic workload: {client_config.workload_type}'"])
        
        return " ".join(cmd_parts)
    
    def _resolve_service_endpoint(self, client_config: ClientConfig, target_service_host: str = None, 
                                default_port: int = 8080, protocol: str = "http") -> str:
        """Resolve service endpoint from configuration and discovered host"""
        self.logger.info(f"Resolving endpoint - target_service_host: {target_service_host}, default_port: {default_port}, protocol: {protocol}")
        self.logger.info(f"Client config target_service: {client_config.target_service}")
        self.logger.info(f"Client config parameters: {client_config.parameters}")
        
        # Check if endpoint is explicitly set in parameters
        endpoint_from_params = client_config.parameters.get('endpoint')
        
        if endpoint_from_params:
            # Use endpoint from recipe parameters (highest priority)
            self.logger.info(f"Using endpoint from recipe: {endpoint_from_params}")
            return endpoint_from_params
        elif target_service_host:
            # Auto-discover service endpoint using target_service config and discovered host
            port = default_port
            if client_config.target_service and isinstance(client_config.target_service, dict):
                port = client_config.target_service.get('port', default_port)
                self.logger.info(f"Got port from target_service config: {port}")
            
            if protocol:
                endpoint = f"{protocol}://{target_service_host}:{port}"
            else:
                endpoint = f"{target_service_host}:{port}"
                
            self.logger.info(f"Using auto-discovered service at: {endpoint}")
            service_type = client_config.target_service.get('type', 'unknown') if client_config.target_service else 'unknown'
            self.logger.info(f"Service type: {service_type} on port {port}")
            return endpoint
        else:
            # No endpoint available
            self.logger.warning("No endpoint specified, make sure target_service configuration is correct")
            self.logger.warning(f"target_service_host was: {target_service_host}")
            return None
    
    def _generate_client_container_build_commands(self, client_config: ClientConfig) -> List[str]:
        """Generate commands to build client container if it doesn't exist"""
        commands = []
        
        # Check if auto_build is enabled
        if not self.config.get('containers', {}).get('auto_build', False):
            return commands
        
        container_base_path = self.config.get('containers', {}).get('base_path', '')
        if container_base_path and not client_config.container_image.startswith('/'):
            container_path = f"{container_base_path}/{client_config.container_image}"
        else:
            container_path = client_config.container_image
        
        # Get docker source for benchmark client
        docker_sources = self.config.get('containers', {}).get('docker_sources', {})
        docker_source = docker_sources.get('benchmark_client')  # Default for client containers
        
        if docker_source:
            commands.extend([
                "# Check if client container exists, build if not",
                f"if [ ! -f \"{container_path}\" ]; then",
                f"    echo \"Container {container_path} not found, building from {docker_source}...\"",
                f"    mkdir -p {container_base_path}",
                f"    apptainer build {container_path} {docker_source}",
                f"    echo \"Container built successfully\"",
                "else",
                f"    echo \"Container {container_path} already exists\"",
                "fi",
                ""
            ])
        
        return commands
    
    def _generate_ollama_setup(self) -> List[str]:
        """Generate Ollama-specific setup commands"""
        return [
            "# Ollama-specific setup",
            "export OLLAMA_TLS_SKIP_VERIFY=1",
            "export OLLAMA_HOST=0.0.0.0:11434",
            ""
        ]
    
    def _generate_ollama_client_setup(self) -> List[str]:
        """Generate Ollama client-specific setup commands"""
        return [
            "# Ollama client setup",
            "export OLLAMA_TLS_SKIP_VERIFY=1",
            "",
            "# Network debugging information",
            "echo '=== NETWORK DEBUG INFO ==='",
            "echo \"Client node: $(hostname)\"",
            "echo \"Client IP: $(hostname -I | awk '{print $1}')\"",
            "echo \"Target service host: ${TARGET_SERVICE_HOST:-'not set'}\"",
            "echo \"Environment variables:\"",
            "printenv | grep -E '(OLLAMA|TARGET|SERVICE)' || echo 'No relevant environment variables'",
            "echo '=========================='",
            "",
            "# Copy benchmark script to compute node",
            "mkdir -p $HOME/benchmark_scripts",
            "",
            "# Look for the benchmark script in multiple locations",
            "SCRIPT_FOUND=0",
            "",
            "# First try uploaded script in /tmp/",
            "for script in /tmp/ollama_benchmark_*.py; do",
            "    if [ -f \"$script\" ]; then",
            "        cp \"$script\" $HOME/benchmark_scripts/ollama_benchmark.py",
            "        echo \"Found and copied benchmark script from: $script\"",
            "        SCRIPT_FOUND=1",
            "        break",
            "    fi",
            "done",
            "",
            "# If not found in /tmp/, try other locations",
            "if [ $SCRIPT_FOUND -eq 0 ]; then",
            "    for location in \"$SLURM_SUBMIT_DIR/benchmark_scripts/ollama_benchmark.py\" \"$SLURM_SUBMIT_DIR/../benchmark_scripts/ollama_benchmark.py\" \"$HOME/benchmark_scripts/ollama_benchmark.py\"; do",
            "        if [ -f \"$location\" ]; then",
            "            cp \"$location\" $HOME/benchmark_scripts/ollama_benchmark.py",
            "            echo \"Found and copied benchmark script from: $location\"",
            "            SCRIPT_FOUND=1",
            "            break",
            "        fi",
            "    done",
            "fi",
            "",
            "# Final check and error handling",
            "if [ $SCRIPT_FOUND -eq 0 ]; then",
            "    echo \"ERROR: ollama_benchmark.py not found in any location!\"",
            "    echo \"Debugging information:\"",
            "    echo \"  Current working directory: $(pwd)\"",
            "    echo \"  SLURM_SUBMIT_DIR: $SLURM_SUBMIT_DIR\"",
            "    echo \"  HOME: $HOME\"",
            "    echo \"\"",
            "    echo \"Checked locations:\"",
            "    echo \"  - /tmp/ollama_benchmark_*.py\"",
            "    echo \"  - $SLURM_SUBMIT_DIR/benchmark_scripts/ollama_benchmark.py\"",
            "    echo \"  - $SLURM_SUBMIT_DIR/../benchmark_scripts/ollama_benchmark.py\"",
            "    echo \"  - $HOME/benchmark_scripts/ollama_benchmark.py\"",
            "    echo \"\"",
            "    echo \"Files in /tmp/:\"",
            "    ls -la /tmp/ollama_benchmark* 2>/dev/null || echo \"  No ollama_benchmark files in /tmp/\"",
            "    echo \"\"",
            "    echo \"Files in SLURM_SUBMIT_DIR:\"",
            "    ls -la \"$SLURM_SUBMIT_DIR/\" 2>/dev/null || echo \"  Cannot access SLURM_SUBMIT_DIR\"",
            "    exit 1",
            "fi",
            "",
            "chmod +x $HOME/benchmark_scripts/ollama_benchmark.py",
            "echo \"Benchmark script ready at: $HOME/benchmark_scripts/ollama_benchmark.py\"",
            "",
            "# Wait for service to be ready",
            "sleep 60",
            ""
        ]
    
    def _compare_time_strings(self, time1: str, time2: str) -> int:
        """Compare two SLURM time strings (HH:MM:SS format). Returns 1 if time1 > time2, -1 if time1 < time2, 0 if equal"""
        def time_to_seconds(time_str):
            parts = time_str.split(':')
            if len(parts) == 2:  # MM:SS format
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:  # HH:MM:SS format
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            else:
                return 0
        
        seconds1 = time_to_seconds(time1)
        seconds2 = time_to_seconds(time2)
        
        if seconds1 > seconds2:
            return 1
        elif seconds1 < seconds2:
            return -1
        else:
            return 0