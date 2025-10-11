"""
Ollama Service and Client implementations
"""

import logging
from typing import Dict, Any, List, Optional
from .base import Service, Client, JobFactory


class OllamaService(Service):
    """Ollama LLM inference service implementation"""
    
    @classmethod
    def from_recipe(cls, recipe: Dict[str, Any], config: Dict[str, Any]) -> 'OllamaService':
        """Create OllamaService from recipe dictionary"""
        service_def = recipe.get('service', {})
        
        return cls(
            name=service_def.get('name', 'ollama'),
            container_image=service_def.get('container_image', 'ollama_latest.sif'),
            resources=service_def.get('resources', {}),
            environment=service_def.get('environment', {}),
            config=config,
            ports=service_def.get('ports', [11434]),
            command=service_def.get('command', 'ollama'),
            args=service_def.get('args', ['serve'])
        )
    
    def generate_script_commands(self) -> List[str]:
        """Generate Ollama service-specific script commands"""
        commands = []
        
        # Add container execution command
        commands.append("# Start the Ollama service")
        commands.append(self.get_container_command())
        
        # Add health check and monitoring
        commands.extend(self.get_health_check_commands())
        
        return commands
    
    def get_container_command(self) -> str:
        """Build the Apptainer command for Ollama service"""
        cmd_parts = ["apptainer exec"]
        
        # Add GPU support if gres indicates GPU usage
        if self.resources.get('gres', '').startswith('gpu:'):
            cmd_parts.append("--nv")
        
        # Add environment variables
        for key, value in self.environment.items():
            cmd_parts.append(f"--env {key}={value}")
        
        # Add container image with base path
        container_base_path = self.config.get('containers', {}).get('base_path', '')
        if container_base_path and not self.container_image.startswith('/'):
            container_path = f"{container_base_path}/{self.container_image}"
        else:
            container_path = self.container_image
        cmd_parts.append(container_path)
        
        # Add command and args
        if self.command:
            cmd_parts.append(self.command)
            if self.args:
                cmd_parts.extend(self.args)
        
        # Run in background for services
        cmd_parts.append("&")
        
        return " ".join(cmd_parts)
    
    def get_service_setup_commands(self) -> List[str]:
        return []

    def get_health_check_commands(self) -> List[str]:
        """Get Ollama service health check and monitoring commands"""
        return [
            "",
            "# Keep the job alive and monitor Ollama service",
            "sleep 30  # Allow service to start",
            "",
            "# Simple health check loop",
            "echo 'Ollama service started, monitoring...'",
            "while kill -0 $! 2>/dev/null; do",
            "    sleep 60",
            "done",
            "",
            "echo 'Ollama service finished'"
        ]


class OllamaClient(Client):
    """Ollama benchmark client implementation"""
    
    @classmethod
    def from_recipe(cls, recipe: Dict[str, Any], config: Dict[str, Any]) -> 'OllamaClient':
        """Create OllamaClient from recipe dictionary"""
        client_def = recipe.get('client', {})
        
        return cls(
            name=client_def.get('name', 'ollama_benchmark'),
            container_image=client_def.get('container_image', 'benchmark_client.sif'),
            resources=client_def.get('resources', {}),
            environment=client_def.get('environment', {}),
            config=config,
            command=client_def.get('command'),
            args=client_def.get('args', []),
            target_service=client_def.get('target_service', {}),
            duration=client_def.get('duration', 300),
            parameters=client_def.get('parameters', {})
        )
    
    def generate_script_commands(self) -> List[str]:
        """Generate Ollama client-specific script commands"""
        commands = []
        
        # Add client-specific setup
        commands.extend(self.get_client_setup_commands())
        
        # Add container execution command
        commands.extend([
            "# Start the Ollama benchmark workload",
            "echo '=== OLLAMA BENCHMARK EXECUTION ==='",
            f"echo 'Container command: {self.get_container_command()}'",
            "echo '===================================='",
            "",
            self.get_container_command(),
            "",
            "echo 'Ollama benchmark execution completed'"
        ])
        
        # Add result collection
        commands.extend(self._get_result_collection_commands())
        
        return commands
    
    def get_container_command(self) -> str:
        """Build the Apptainer command for Ollama benchmark client"""
        cmd_parts = ["apptainer exec"]
        
        # Add GPU support if gres indicates GPU usage
        if self.resources.get('gres', '').startswith('gpu:'):
            cmd_parts.append("--nv")
        
        # Add environment variables
        for key, value in self.environment.items():
            cmd_parts.append(f"--env {key}={value}")
        
        # Mount benchmark scripts directory
        cmd_parts.append("--bind $HOME/benchmark_scripts:/app")
        
        # Add container image with base path
        container_base_path = self.config.get('containers', {}).get('base_path', '')
        if container_base_path and not self.container_image.startswith('/'):
            container_path = f"{container_base_path}/{self.container_image}"
        else:
            container_path = self.container_image
        cmd_parts.append(container_path)
        
        # Build the Python command for Ollama benchmark
        python_cmd = "python /app/ollama_benchmark.py"
        
        # Add endpoint parameter
        endpoint = self.resolve_service_endpoint(default_port=11434)
        if endpoint:
            python_cmd += f" --endpoint={endpoint}"
        
        # Add other parameters
        for key, value in self.parameters.items():
            if key == 'endpoint':  # Skip endpoint as it's handled above
                continue
            cli_key = key.replace('_', '-')
            python_cmd += f" --{cli_key}={value}"
        
        # Run inside container with dependency installation
        cmd_parts.extend(["bash", "-c", f'"pip install requests && {python_cmd}"'])
        
        return " ".join(cmd_parts)
    
    def get_client_setup_commands(self) -> List[str]:
        """Get Ollama client-specific setup commands"""
        return [
            "# Network debugging information",
            "echo '=== OLLAMA BENCHMARK DEBUG INFO ==='",
            "echo \"Client node: $(hostname)\"",
            "echo \"Client IP: $(hostname -I | awk '{print $1}')\"",
            "echo \"Target service host: ${TARGET_SERVICE_HOST:-'not set'}\"",
            "echo \"Environment variables:\"",
            "printenv | grep -E '(OLLAMA|TARGET|SERVICE)' || echo 'No relevant environment variables'",
            "echo '===================================='",
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
    
    def resolve_service_endpoint(self, target_service_host: str = None, 
                               default_port: int = 11434, protocol: str = "http") -> str:
        """Resolve Ollama service endpoint"""
        logger = logging.getLogger(__name__)
        
        logger.info(f"Resolving Ollama endpoint - target_service_host: {target_service_host}, default_port: {default_port}")
        
        # Check if endpoint is explicitly set in parameters
        endpoint_from_params = self.parameters.get('endpoint')
        
        if endpoint_from_params:
            logger.info(f"Using endpoint from recipe: {endpoint_from_params}")
            return endpoint_from_params
        elif target_service_host:
            # Auto-discover service endpoint
            port = default_port
            if self.target_service and isinstance(self.target_service, dict):
                port = self.target_service.get('port', default_port)
                logger.info(f"Got port from target_service config: {port}")
            
            if protocol:
                endpoint = f"{protocol}://{target_service_host}:{port}"
            else:
                endpoint = f"{target_service_host}:{port}"
                
            logger.info(f"Using auto-discovered Ollama service at: {endpoint}")
            return endpoint
        else:
            logger.warning("No endpoint specified for Ollama client")
            return None
    
    def _get_result_collection_commands(self) -> List[str]:
        """Get result collection commands for Ollama benchmark"""
        output_file = self.parameters.get('output_file', '/tmp/ollama_benchmark_results.json')
        return [
            "",
            "# Copy Ollama benchmark results back to submit directory",
            "mkdir -p $SLURM_SUBMIT_DIR/results",
            f"cp {output_file} $SLURM_SUBMIT_DIR/results/ 2>/dev/null || echo 'Warning: Could not copy Ollama results file'",
            "echo 'Ollama results collection completed'",
            "",
            "echo 'Ollama client workload completed'"
        ]


# Register the Ollama implementations with the factory
JobFactory.register_service('ollama', OllamaService)
JobFactory.register_client('ollama', OllamaClient)