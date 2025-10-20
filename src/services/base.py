"""
Base Job Classes and Factory
============================

This module provides the foundational abstractions for the HPC job orchestration system.
It implements a self-contained job architecture where each job type is responsible for
generating its own SLURM batch scripts, eliminating external dependencies and coupling.

Examples:
--------

Creating and using a service:
    service_recipe = {
        'service': {
            'name': 'ollama',
            'container_image': 'ollama.sif',
            'resources': {'mem': '16G'},
            'environment': {'MODEL': 'llama2'}
        }
    }
    service = JobFactory.create_service(service_recipe)
    script = service.generate_slurm_script(config, 'svc_001')

Creating and using a client:
    client_recipe = {
        'client': {
            'container_image': 'benchmark.sif',
            'target_service': {'name': 'ollama'},
            'duration': 600
        }
    }
    client = JobFactory.create_client(client_recipe)
    script = client.generate_slurm_script(config, 'client_001', 'node-123')
"""

import abc
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

@dataclass
class Job(abc.ABC):
    """
    Abstract base class for all HPC jobs (services and clients).
    
    This class implements the core job abstraction with self-contained SLURM script
    generation capabilities. Each job is responsible for generating its own deployment
    scripts, eliminating external dependencies and following object-oriented principles.
    
    Attributes:
        name (str): Unique identifier for the job type (e.g., 'ollama', 'benchmark')
        container_image (str): Path or name of the container image to execute
        resources (Dict[str, Any]): SLURM resource requirements (mem, cpus, gres, etc.)
        environment (Dict[str, str]): Environment variables to set in the job
        command (Optional[str]): Override command to execute in container
        args (Optional[List[str]]): Command line arguments for the container command
    
    Design Pattern:
        Implements the Template Method pattern where generate_slurm_script() provides
        the algorithm structure, and subclasses implement specific details through
        abstract methods.
    """
    
    name: str
    container_image: str
    resources: Dict[str, Any]
    environment: Dict[str, str]
    config: Dict[str, Any]
    command: Optional[str] = None
    args: Optional[List[str]] = None
    
    def generate_slurm_script(self, job_id: str, target_service_host: str = None) -> str:
        """
        This is the main template method that orchestrates the creation of a complete
        SLURM batch script. It combines configuration (from self.config), resource 
        requirements, container management, and job-specific commands into a single 
        executable script.
        
        Template Method Pattern:
            This method implements the invariant parts of script generation while
            delegating job-specific details to abstract methods implemented by subclasses:
            - generate_script_commands(): Job-specific execution logic
            - get_container_command(): Container runtime command construction
            - _get_docker_source(): Container source resolution (overridable)
        
        Args:
            job_id (str): Unique identifier for this job instance, used in:
                - SLURM job naming (#SBATCH --job-name)
                - Log file naming and identification
                - Resource tracking and monitoring
            target_service_host (str, optional): For client jobs, specifies the hostname
                where the target service is running. Sets TARGET_SERVICE_HOST environment
                variable for service discovery.
        
        Returns:
            str: Complete SLURM batch script content ready for submission via sbatch.
                The script includes SLURM directives, module loading, environment setup,
                container management, and job-specific execution commands.
        
        Raises:
            ValueError: If required configuration is missing (e.g., SLURM account)
            
        Configuration Requirements:
            Required:
                - config['slurm']['account']: SLURM account for job charging
            Optional with defaults:
                - config['slurm']['partition']: 'cpu'
                - config['slurm']['qos']: 'default' 
                - config['slurm']['time']: '00:15:00'
                - config['slurm']['nodes']: 1
                - config['slurm']['ntasks']: 1
                - config['slurm']['ntasks_per_node']: 1
        """
        # Get default SLURM configuration
        slurm_config = self.config.get('slurm', {})
        if 'account' not in slurm_config or slurm_config['account'] is None:
            raise ValueError("SLURM account must be specified in slurm configuration")
        
        default_slurm_config = {
            'account': slurm_config['account'],
            'partition': slurm_config.get('partition', 'cpu'),
            'qos': slurm_config.get('qos', 'default'),
            'time': slurm_config.get('time', '00:15:00'),
            'nodes': slurm_config.get('nodes', 1),
            'ntasks': slurm_config.get('ntasks', 1),
            'ntasks_per_node': slurm_config.get('ntasks_per_node', 1)
        }
        
        # Merge with job-specific resources
        final_slurm_config = {**default_slurm_config, **self.resources}
        
        # Generate basic SLURM directives
        script_lines = [
            "#!/bin/bash -l",
            f"#SBATCH --job-name={self.name}_{job_id}",
            f"#SBATCH --time={final_slurm_config['time']}",
            f"#SBATCH --qos={final_slurm_config['qos']}",
            f"#SBATCH --partition={final_slurm_config['partition']}",
            f"#SBATCH --account={final_slurm_config['account']}",
            f"#SBATCH --nodes={final_slurm_config['nodes']}",
            f"#SBATCH --ntasks={final_slurm_config['ntasks']}",
            f"#SBATCH --ntasks-per-node={final_slurm_config['ntasks_per_node']}",
        ]
        
        # Add optional SLURM directives
        if final_slurm_config.get('gres'):
            script_lines.insert(-2, f"#SBATCH --gres={final_slurm_config['gres']}")
        
        if final_slurm_config.get('mem'):
            script_lines.insert(-2, f"#SBATCH --mem={final_slurm_config['mem']}")
        
        if final_slurm_config.get('cpus_per_task'):
            script_lines.insert(-2, f"#SBATCH --cpus-per-task={final_slurm_config['cpus_per_task']}")

        # Load Apptainer
        script_lines.extend([
            "",
            "# Load required modules",
            "module add Apptainer",
            ""
        ])
        
        # Add environment variables
        if self.environment:
            script_lines.append("# Set environment variables")
            for key, value in self.environment.items():
                script_lines.append(f"export {key}={value}")
            script_lines.append("")
        
        # Add container build commands
        container_build_commands = self._generate_container_build_commands()
        if container_build_commands:
            script_lines.extend(container_build_commands)
        
        # Add target service host for clients (if applicable)
        if target_service_host:
            script_lines.append(f"export TARGET_SERVICE_HOST={target_service_host}")
            script_lines.append("")
        
        # Add job-specific commands (delegated to the concrete implementation)
        job_commands = self.generate_script_commands()
        script_lines.extend(job_commands)
        
        return "\n".join(script_lines)
    
    @classmethod
    @abc.abstractmethod
    def from_recipe(cls, recipe: Dict[str, Any], config: Dict[str, Any]) -> 'Job':
        """
        This abstract method must be implemented by concrete subclasses to handle
        the parsing and validation of recipe dictionaries into job instances.
        
        Args:
            recipe (Dict[str, Any]): Recipe configuration dictionary containing
                job parameters, resources, environment variables, and other settings.
                Expected structure varies by job type but typically includes:
                - service/client: Job-specific configuration block
                - container_image: Container image specification
                - resources: SLURM resource requirements
                - environment: Environment variables
            config (Dict[str, Any]): Global configuration dictionary containing
                system-wide settings that will be stored as self.config for use
                by other job methods.
        
        Returns:
            Job: Concrete job instance initialized with recipe parameters and config
        
        Raises:
            ValueError: If recipe is malformed or missing required fields
            KeyError: If expected configuration keys are not present
        """
        pass
    
    @abc.abstractmethod
    def generate_script_commands(self) -> List[str]:
        """
        This abstract method is called by generate_slurm_script() to obtain the
        job-specific commands that will be executed in the SLURM batch script.
        It represents the core execution logic for each job type.
        
        The method can access the global configuration through self.config,
        which contains system-wide settings including SLURM configuration,
        container settings, and job-type specific configuration sections.
        
        Note: Default implementations are provided in Service and Client classes.
        Override only if you need custom behavior.
        
        Returns:
            List[str]: List of bash commands to be included in the SLURM script.
                Commands should be valid bash syntax and include any necessary
                setup, execution, and cleanup operations.
        """
        pass
    
    @abc.abstractmethod
    def get_container_command(self) -> str:
        """
        This abstract method constructs the complete command line that will be used
        to execute the container in the SLURM environment. It handles container
        runtime selection, bind mounts, environment passing, and command specification.
        
        Note: Default implementations are provided in Service and Client classes.
        Override only if you need custom behavior.
        
        Returns:
            str: Complete container execution command ready for bash execution.
                Typically uses Apptainer/Singularity syntax but may vary by implementation.
        """
        pass

    def _generate_container_build_commands(self) -> List[str]:
        """Generate container build commands for this job"""
        commands = []
        
        container_base_path = self.config.get('containers', {}).get('base_path', '')
        if container_base_path and not self.container_image.startswith('/'):
            container_path = f"{container_base_path}/{self.container_image}"
        else:
            container_path = self.container_image
        
        # Get docker source - subclasses can override this logic
        docker_source = self._get_docker_source()
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
    
    def _get_docker_source(self) -> Optional[str]:
        """Get docker source for this job type - can be overridden by subclasses"""
        docker_sources = self.config.get('containers', {}).get('docker_sources', {})
        return docker_sources.get(self.name)


@dataclass  
class Service(Job):
    """
    Abstract base class for long-running service jobs.
    
    Services represent persistent, long-running applications that provide functionality
    to other components in the system. Examples include databases, API servers, 
    machine learning inference services, and compute engines.
    
    Attributes:
        ports (List[int]): Network ports that the service exposes for client connections.
            These ports are used for service discovery and health checking.
            Default: Empty list (no exposed ports)
        container (Dict[str, Any]): Container configuration including docker_source
            and image_path. When image exists at image_path, it's used; when not found,
            it's downloaded from docker_source and placed at image_path.
            Default: Empty dictionary
    """
    ports: List[int] = None
    container: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.ports is None:
            self.ports = []
        if self.container is None:
            self.container = {}
    
    def generate_script_commands(self) -> List[str]:
        """Default service script generation - can be overridden if needed"""
        commands = []
        
        # Add service setup
        commands.extend(self.get_service_setup_commands())
        
        # Start the service
        commands.append(f"# Start the {self.name} service")
        commands.append(self.get_container_command())
        
        # Add health check and monitoring
        commands.extend(self.get_health_check_commands())
        
        return commands
    
    def get_container_command(self) -> str:
        """Default container command for services - can be overridden if needed"""
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
    
    def get_health_check_commands(self) -> List[str]:
        """Default health check and monitoring - can be overridden if needed"""
        return [
            "",
            f"# Keep the job alive and monitor {self.name} service",
            "sleep 30  # Allow service to start",
            "",
            "# Simple monitoring loop",
            f"echo '{self.name} service started, monitoring...'",
            "while kill -0 $! 2>/dev/null; do",
            "    sleep 60",
            "done",
            "",
            f"echo '{self.name} service finished'"
        ]
    
    def get_service_setup_commands(self) -> List[str]:
        """Default service setup - can be overridden if needed"""
        return []
    
    def _get_docker_source(self) -> Optional[str]:
        """Override to use container config from service YAML instead of global config"""
        # First check if docker_source is specified in service container config
        if self.container and 'docker_source' in self.container:
            return self.container['docker_source']
        
        # Fallback to global config for backward compatibility
        docker_sources = self.config.get('containers', {}).get('docker_sources', {})
        return docker_sources.get(self.name)
    
    def get_container_command(self) -> str:
        """Default container command for services - enhanced with local container paths"""
        cmd_parts = ["apptainer exec"]
        
        # Add GPU support if gres indicates GPU usage
        if self.resources.get('gres', '').startswith('gpu:'):
            cmd_parts.append("--nv")
        
        # Add environment variables
        for key, value in self.environment.items():
            cmd_parts.append(f"--env {key}={value}")
        
        # Resolve container path using service-specific logic
        container_path = self._resolve_container_path()
        cmd_parts.append(container_path)
        
        # Add command and args
        if self.command:
            cmd_parts.append(self.command)
            if self.args:
                cmd_parts.extend(self.args)
        
        # Run in background for services
        cmd_parts.append("&")
        
        return " ".join(cmd_parts)
    
    def _resolve_container_path(self) -> str:
        """Resolve the actual container path using service-specific configuration"""
        # Use image_path from service container config
        if self.container and 'image_path' in self.container:
            return self.container['image_path']
        
        # Fallback to global config logic for backward compatibility
        container_base_path = self.config.get('containers', {}).get('base_path', '')
        if container_base_path and not self.container_image.startswith('/'):
            return f"{container_base_path}/{self.container_image}"
        else:
            return self.container_image
    
    def _generate_container_build_commands(self) -> List[str]:
        """Generate container build commands using simplified logic"""
        commands = []
        
        # Get container path and docker source from service config
        container_path = self._resolve_container_path()
        docker_source = self._get_docker_source()
        
        if docker_source:
            # Ensure directory exists (extract directory from container_path)
            container_dir = '/'.join(container_path.split('/')[:-1])
            if container_dir:
                commands.append(f"mkdir -p {container_dir}")
            
            commands.extend([
                "# Container management",
                f"if [ ! -f \"{container_path}\" ]; then",
                f"    echo \"Container {container_path} not found, building from {docker_source}...\"",
                f"    echo \"Starting container build at $(date)\"",
                f"    apptainer build {container_path} {docker_source}",
                f"    if [ $? -eq 0 ]; then",
                f"        echo \"Container built successfully at $(date)\"",
                f"    else",
                f"        echo \"Container build failed at $(date)\"",
                f"        exit 1",
                f"    fi",
                "else",
                f"    echo \"Container {container_path} already exists\"",
                "fi",
                ""
            ])
        
        return commands


@dataclass
class Client(Job):
    """
    Abstract base class for client jobs that interact with services.
    
    Clients represent workload generators, benchmark tools, data processors, and other
    applications that connect to services to perform computational work. Clients are
    typically short-lived and task-oriented, in contrast to long-running services.
    
    Attributes:
        target_service (Dict[str, Any]): Configuration for the service this client connects to.
            Typically includes service name, connection parameters, and discovery information.
            The 'name' field is used to determine which client implementation to use.
            Default: Empty dictionary
            
        duration (int): Maximum execution duration in seconds. Used for timeout control
            and resource planning. Default: 300 seconds (5 minutes)
            
        parameters (Dict[str, Any]): Client-specific parameters that control workload
            behavior, such as request rates, data sizes, test scenarios, etc.
            Default: Empty dictionary
    """
    target_service: Dict[str, Any] = None
    duration: int = 300
    parameters: Dict[str, Any] = None
    
    # Script configuration
    script_name: str = None  # Name of the Python script to run (e.g., "ollama_benchmark.py")
    script_local_path: str = None  # Local path to find the script (e.g., "benchmark_scripts/")
    script_remote_path: str = None  # Remote path where script should be located (e.g., "$HOME/benchmark_scripts/")
    
    # Container configuration
    container: Dict[str, Any] = None  # Container config including docker_source and image_path
    
    def __post_init__(self):
        if self.target_service is None:
            self.target_service = {}
        if self.parameters is None:
            self.parameters = {}
        if self.container is None:
            self.container = {}
        
        # Set default script configuration if not specified
        if self.script_name is None:
            if "benchmark" in self.name.lower():
                self.script_name = f"{self.name}.py"
            else:
                self.script_name = f"{self.name}_benchmark.py"
        
        if self.script_local_path is None:
            self.script_local_path = "benchmark_scripts/"
            
        if self.script_remote_path is None:
            self.script_remote_path = "$HOME/benchmark_scripts/"
    
    def get_target_service_name(self) -> str:
        """Get the name of the target service this client connects to"""
        return self.target_service.get('name', 'unknown')
    
    @classmethod
    def from_recipe(cls, recipe: Dict[str, Any], config: Dict[str, Any]) -> 'Client':
        """
        Default Client factory method that parses script configuration from YAML.
        Can be overridden by specific client implementations if needed.
        """
        # Extract client configuration
        client_config = recipe.get('client', recipe)
        
        # Parse script configuration
        script_config = client_config.get('script', {})
        script_name = script_config.get('name')
        script_local_path = script_config.get('local_path')
        script_remote_path = script_config.get('remote_path')
        
        return cls(
            name=client_config.get('name', 'client'),
            container_image=client_config.get('container_image', ''),
            resources=client_config.get('resources', {}),
            environment=client_config.get('environment', {}),
            command=client_config.get('command'),
            args=client_config.get('args', []),
            target_service=client_config.get('target_service', {}),
            duration=client_config.get('duration', 300),
            parameters=client_config.get('parameters', {}),
            script_name=script_name,
            script_local_path=script_local_path,
            script_remote_path=script_remote_path,
            config=config
        )
    
    def generate_script_commands(self) -> List[str]:
        """Default client script commands"""
        commands = []
        commands.extend(self.get_client_setup_commands())
        commands.extend(self.get_container_execution_commands())
        return commands
    
    def get_container_execution_commands(self) -> List[str]:
        """Default container execution for clients"""
        container_cmd = self.get_container_command()
        return [
            f"# Execute client workload",
            f"echo \"Starting client: {self.name}\"",
            container_cmd,
            f"echo \"Client {self.name} completed\"",
        ]
    
    def get_target_service(self) -> Dict[str, Any]:
        """Get the target service configuration"""
        return self.target_service
    
    def generate_script_commands(self) -> List[str]:
        """Default client script generation - includes container build commands"""
        commands = []
        
        # Add client setup
        commands.extend(self.get_client_setup_commands())
        
        # Add container build commands (ensure container exists before execution)
        container_build_commands = self._generate_container_build_commands()
        if container_build_commands:
            commands.extend(container_build_commands)
        
        # Add container execution command
        commands.extend([
            f"# Start the {self.name} workload",
            f"echo '=== {self.name.upper()} EXECUTION ==='",
            f"echo 'Container command: {self.get_container_command()}'",
            "echo '===================================='",
            "",
            self.get_container_command(),
            "",
            f"echo '{self.name} execution completed'"
        ])
        
        # Add result collection
        commands.extend(self.get_result_collection_commands())
        
        return commands
    
    def get_container_command(self) -> str:
        """Default container command for clients - uses client container configuration"""
        cmd_parts = ["apptainer exec"]
        
        # Add GPU support if gres indicates GPU usage
        if self.resources.get('gres', '').startswith('gpu:'):
            cmd_parts.append("--nv")
        
        # Add environment variables
        for key, value in self.environment.items():
            cmd_parts.append(f"--env {key}={value}")
        
        # Mount benchmark scripts directory - simplified path
        scripts_dir = self.config.get('benchmark', {}).get('scripts_dir', '$HOME/benchmark_scripts')
        cmd_parts.append(f"--bind {scripts_dir}:/app")
        
        # Resolve container path using client-specific logic
        container_path = self._resolve_container_path()
        cmd_parts.append(container_path)
        
        # Build the command - simplified approach
        if self.command and self.args:
            # Use explicit command and args from YAML
            python_cmd = f"{self.command} {' '.join(self.args)}"
        else:
            # Build Python command with script name - avoid double "benchmark"
            if "benchmark" in self.name.lower():
                script_name = f"{self.name}.py"
            else:
                script_name = f"{self.name}_benchmark.py"
            
            # Use configured script name if available
            if hasattr(self, 'script_name') and self.script_name:
                script_name = self.script_name
                
            python_cmd = f"python /app/{script_name}"
            
            # Add endpoint parameter
            endpoint = self.resolve_service_endpoint()
            if endpoint:
                python_cmd += f" --endpoint={endpoint}"
            
            # Add other parameters
            for key, value in self.parameters.items():
                if key == 'endpoint':  # Skip endpoint as it's handled above
                    continue
                cli_key = key.replace('_', '-')
                python_cmd += f" --{cli_key}={value}"
        
        # Run inside container - simplified without complex dependency handling
        cmd_parts.extend(["bash", "-c", f'"pip install -q requests mysql-connector-python && {python_cmd}"'])
        
        return " ".join(cmd_parts)
    
    def get_client_setup_commands(self) -> List[str]:
        """Default client setup - uses script configuration from YAML"""
        return [
            "# Client setup and debugging information",
            f"echo '=== {self.name.upper()} DEBUG INFO ==='",
            "echo \"Client node: $(hostname)\"",
            "echo \"Client IP: $(hostname -I | awk '{print $1}')\"",
            "echo \"Target service host: ${TARGET_SERVICE_HOST:-'not set'}\"",
            f"echo \"Target service: {self.get_target_service_name()}\"",
            "echo '========================='",
            "",
            f"# Ensure benchmark script directory exists",
            f"mkdir -p {self.script_remote_path.replace('$HOME/', '$HOME/')}",
            "",
            f"# Check if benchmark script exists",
            f"SCRIPT_PATH=\"{self.script_remote_path.rstrip('/')}/{self.script_name}\"",
            "if [ ! -f \"$SCRIPT_PATH\" ]; then",
            f"    echo \"ERROR: Benchmark script not found at $SCRIPT_PATH\"",
            f"    echo \"Please ensure {self.script_name} is uploaded to the scripts directory\"",
            "    exit 1",
            "fi",
            f"echo \"Using benchmark script: $SCRIPT_PATH\"",
            ""
        ]
    
    def resolve_service_endpoint(self, target_service_host: str = None, 
                               default_port: int = None, protocol: str = "http") -> str:
        """Default service endpoint resolution - can be overridden if needed"""
        # Check if endpoint is explicitly set in parameters
        endpoint_from_params = self.parameters.get('endpoint')
        if endpoint_from_params:
            return endpoint_from_params
        
        # Use TARGET_SERVICE_HOST environment variable
        host = target_service_host or "${TARGET_SERVICE_HOST}"
        
        # Get port from target service config or use default
        if self.target_service and isinstance(self.target_service, dict):
            port = self.target_service.get('port', default_port or 8080)
        else:
            port = default_port or 8080
        
        # Build endpoint
        if protocol:
            return f"{protocol}://{host}:{port}"
        else:
            return f"{host}:{port}"
    
    def get_result_collection_commands(self) -> List[str]:
        """Default result collection - can be overridden if needed"""
        output_file = self.parameters.get('output_file', f'/tmp/{self.name}_results.json')
        return [
            "",
            f"# Copy {self.name} results back to submit directory",
            "mkdir -p $SLURM_SUBMIT_DIR/results",
            f"cp {output_file} $SLURM_SUBMIT_DIR/results/ 2>/dev/null || echo 'Warning: Could not copy results file'",
            f"echo '{self.name} results collection completed'",
            "",
            f"echo '{self.name} client workload completed'"
        ]
    
    def _resolve_container_path(self) -> str:
        """Resolve the actual container path using client-specific configuration"""
        # Use image_path from client container config
        if self.container and 'image_path' in self.container:
            return self.container['image_path']
        
        # Fallback to container_image field if no container config
        return self.container_image
    
    def _generate_container_build_commands(self) -> List[str]:
        """Generate container build commands for client using client-specific configuration"""
        commands = []
        
        # Get container path and docker source from client config
        container_path = self._resolve_container_path()
        docker_source = self._get_docker_source()
        
        if docker_source:
            # Ensure directory exists (extract directory from container_path)
            container_dir = '/'.join(container_path.split('/')[:-1])
            if container_dir:
                commands.append(f"mkdir -p {container_dir}")

            # If the recipe provides explicit build_commands, create a Singularity
            # definition file on the remote host and build the SIF from it. This
            # bakes packages into the container image instead of trying to pip
            # install at runtime.
            build_cmds = self.container.get('build_commands') or []
            if build_cmds:
                # Normalize docker source (strip docker:// prefix if present)
                from_image = docker_source
                if from_image.startswith('docker://'):
                    from_image = from_image.replace('docker://', '')

                def_path = f"/tmp/singularity_{int(__import__('time').time())}.def"

                commands.append("# Client container management (Singularity definition build)")
                commands.append(f"cat > {def_path} <<'EOF'")
                commands.append(f"Bootstrap: docker")
                commands.append(f"From: {from_image}")
                commands.append("")
                commands.append("%post")
                # Add each build command under %post
                for c in build_cmds:
                    commands.append(f"    {c}")
                commands.append("")
                commands.append("%labels")
                commands.append(f"    Author {self.get_target_service_name()}_client")
                commands.append("EOF")
                commands.append(f"echo \"Starting client container build from {def_path} at $(date)\"")
                commands.append(f"apptainer build --force {container_path} {def_path}")
                commands.append("if [ $? -eq 0 ]; then")
                commands.append("    echo \"Client container built successfully\"")
                commands.append("else")
                commands.append("    echo \"Client container build failed\"")
                commands.append("    exit 1")
                commands.append("fi")
                commands.append("")
            else:
                # Fallback: simple build from docker source
                commands.extend([
                    "# Client container management",
                    f"if [ ! -f \"{container_path}\" ]; then",
                    f"    echo \"Client container {container_path} not found, building from {docker_source}...\"",
                    f"    echo \"Starting client container build at $(date)\"",
                    f"    apptainer build {container_path} {docker_source}",
                    f"    if [ $? -eq 0 ]; then",
                    f"        echo \"Client container built successfully at $(date)\"",
                    f"    else",
                    f"        echo \"Client container build failed at $(date)\"",
                    f"        exit 1",
                    f"    fi",
                    "else",
                    f"    echo \"Client container {container_path} already exists\"",
                    "fi",
                    ""
                ])
        
        return commands
    
    def _get_docker_source(self) -> Optional[str]:
        """Use docker_source from client container configuration"""
        if self.container and 'docker_source' in self.container:
            return self.container['docker_source']
        
        # No fallback - clients must specify their container configuration
        return None


class JobFactory:
    """
    The JobFactory implements the Abstract Factory pattern, providing a centralized
    mechanism for creating Service and Client instances from recipe dictionaries.
    It maintains registries of available job types and handles the instantiation
    logic, ensuring type safety and proper object construction.

    Class Attributes:
        _service_registry (Dict[str, type]): Maps service names to service classes
        _client_registry (Dict[str, type]): Maps client names to client classes
    
    Error Handling:
        - Unknown service/client types raise ValueError with clear messages
        - Missing recipe sections are handled gracefully with defaults
        - Malformed recipes are caught during from_recipe() validation
        - Registry access is protected against KeyError exceptions
    """
    
    _service_registry = {}
    _client_registry = {}
    
    @classmethod
    def register_service(cls, name: str, service_class):
        """
        This method is called by concrete service implementations to make themselves
        available for creation through the factory. Registration typically occurs
        during module import when the concrete class is defined.
        
        Args:
            name (str): Unique identifier for the service type. This name must match
                the 'name' field in service recipes. Examples: 'ollama', 'postgres', 'redis'
            service_class (type): Concrete service class that inherits from Service
                and implements all required abstract methods.
        
        Raises:
            TypeError: If service_class is not a subclass of Service
            ValueError: If name is empty or None
        
        Registry Collision:
            If a service name is registered multiple times, the last registration
            overwrites previous ones. This allows for implementation replacement
            but should be used carefully to avoid unexpected behavior.
        """
        cls._service_registry[name] = service_class
    
    @classmethod
    def register_client(cls, name: str, client_class):
        """
        This method is called by concrete client implementations to make themselves
        available for creation through the factory. Registration typically occurs
        during module import when the concrete class is defined.
        
        Args:
            name (str): Target service name that this client is designed for. This name must
                match the 'name' field in the target_service section of client recipes. 
                Examples: 'ollama', 'postgres', 'redis'
            client_class (type): Concrete client class that inherits from Client
                and implements all required abstract methods.
        
        Raises:
            TypeError: If client_class is not a subclass of Client
            ValueError: If name is empty or None
        
        Registry Collision:
            If a client for the same service name is registered multiple times, the last registration
            overwrites previous ones. This allows for implementation replacement
            but should be used carefully to avoid unexpected behavior.
            but should be used carefully to avoid unexpected behavior.
        """
        cls._client_registry[name] = client_class
    
    @classmethod
    def create_service(cls, recipe: Dict[str, Any], config: Dict[str, Any]) -> Service:
        """
        This factory method creates concrete Service instances based on the service
        type specified in the recipe. It handles service discovery, class lookup,
        and delegation to the appropriate concrete implementation.
        
        Args:
            recipe (Dict[str, Any]): Recipe dictionary containing service configuration.
                Must include a 'service' section with at minimum a 'name' field.
                Expected structure:
                {
                    'service': {
                        'name': 'service_type',      # Required: maps to registry
                        'container_image': '...',     # Required: container specification
                        'resources': {...},           # Optional: SLURM resources
                        'environment': {...},         # Optional: environment variables
                        'ports': [...],              # Optional: exposed ports
                        # ... service-specific fields
                    }
                }
            config (Dict[str, Any]): Global configuration dictionary that will be
                stored in the service instance for use by other methods. Contains
                system-wide settings including SLURM configuration, container settings,
                and service-specific configuration sections.
                    }
                }
        
        Returns:
            Service: Concrete service instance initialized from the recipe.
                The returned instance is fully configured and ready for script generation
                and deployment.
        
        Raises:
            ValueError: If the service name is not found in the registry, indicating
                an unknown or unregistered service type.
            KeyError: If the recipe is missing required sections or fields.
            Exception: Any exception raised by the concrete service's from_recipe() method,
                typically due to invalid configuration or validation failures.
        """
        service_def = recipe.get('service', {})
        service_name = service_def.get('name', 'unknown')
        
        if service_name in cls._service_registry:
            service_class = cls._service_registry[service_name]
            return service_class.from_recipe(recipe, config)
        else:
            raise ValueError(f"Unknown service type: {service_name}")
    
    @classmethod
    def create_client(cls, recipe: Dict[str, Any], config: Dict[str, Any]) -> Client:
        """
        This factory method creates concrete Client instances based on the workload
        type specified in the recipe. It handles client discovery, class lookup,
        and delegation to the appropriate concrete implementation.
        
        Args:
            recipe (Dict[str, Any]): Recipe dictionary containing client configuration.
                Must include a 'client' section with 'target_service' containing a 'name' field.
                Expected structure:
                {
                    'client': {
                        'target_service': {
                            'name': 'ollama'               # Required: maps to registry
                        },
                        'container_image': '...',          # Required: container specification
                        'duration': 300,                   # Optional: execution duration
                        'parameters': {...},               # Optional: workload parameters
                        'resources': {...},                # Optional: SLURM resources
                        # ... client-specific fields
                    }
                }
            config (Dict[str, Any]): Global configuration dictionary that will be
                stored in the client instance for use by other methods. Contains
                system-wide settings including SLURM configuration, container settings,
                and client-specific configuration sections.
                        'parameters': {...},               # Optional: workload parameters
                        'resources': {...},                # Optional: SLURM resources
                        # ... client-specific fields
                    }
                }
        
        Returns:
            Client: Concrete client instance initialized from the recipe.
                The returned instance is fully configured and ready for script generation
                and workload execution.
        
        Raises:
            ValueError: If the target service name is not found in the registry, indicating
                an unknown or unregistered service type for clients.
            KeyError: If the recipe is missing required sections or fields.
            Exception: Any exception raised by the concrete client's from_recipe() method,
                typically due to invalid configuration or validation failures.
        """
        target_service = recipe.get('client', {}).get('target_service', {})
        service_name = target_service.get('name', 'unknown')

        if service_name in cls._client_registry:
            client_class = cls._client_registry[service_name]
            return client_class.from_recipe(recipe, config)
        else:
            raise ValueError(f"Unknown target service for client: {service_name}")
    
    @classmethod
    def list_available_services(cls) -> List[str]:
        """
        List all registered service types.
        """
        return list(cls._service_registry.keys())
    
    @classmethod
    def list_available_clients(cls) -> List[str]:
        """
        List all registered client target service names.
        """  
        return list(cls._client_registry.keys())