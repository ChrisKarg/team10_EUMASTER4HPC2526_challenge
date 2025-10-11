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
        
        Returns:
            List[str]: List of bash commands to be included in the SLURM script.
                Commands should be valid bash syntax and include any necessary
                setup, execution, and cleanup operations.
        
        Example Return Values:
            Service implementation:
                [
                    "echo 'Starting service setup'",
                    "mkdir -p /tmp/service_data", 
                    f"apptainer exec {container_path} start_service.sh",
                    "echo 'Service started successfully'"
                ]
            
            Client implementation:
                [
                    "echo 'Connecting to service at $TARGET_SERVICE_HOST'",
                    f"apptainer exec {container_path} run_benchmark.py",
                    "echo 'Benchmark completed'"
                ]
        
        Error Handling:
            - Should include validation of required configuration
            - May raise exceptions for invalid or missing configuration
            - Consider including retry logic for transient failures
        """
        pass
    
    @abc.abstractmethod
    def get_container_command(self) -> str:
        """
        This abstract method constructs the complete command line that will be used
        to execute the container in the SLURM environment. It handles container
        runtime selection, bind mounts, environment passing, and command specification.
        
        The method can access the global configuration through self.config, which may include:
        - containers.base_path: Base directory for container images
        - containers.bind_mounts: Default bind mount configurations
        - containers.runtime_options: Additional runtime parameters
        
        Returns:
            str: Complete container execution command ready for bash execution.
                Typically uses Apptainer/Singularity syntax but may vary by implementation.
        
        Example Return Values:
            Basic execution:
                "apptainer exec /containers/ollama.sif /usr/local/bin/ollama serve"
            
            With bind mounts and environment:
                "apptainer exec --bind /data:/data --env MODEL=llama2 /containers/ollama.sif ollama serve"
                
            With custom working directory:
                "apptainer exec --pwd /workspace /containers/benchmark.sif python benchmark.py"
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
    """
    ports: List[int] = None
    
    def __post_init__(self):
        if self.ports is None:
            self.ports = []
    
    @abc.abstractmethod
    def get_health_check_commands(self) -> List[str]:
        """
        Health checks are crucial for verifying that a service has started successfully
        and is ready to handle requests. These commands are typically executed after
        the service has been started but before considering the deployment complete.
        
        Returns:
            List[str]: List of bash commands that verify service health.
                Commands should:
                - Test service responsiveness (HTTP endpoints, port connectivity)
                - Validate critical functionality
                - Return non-zero exit codes on failure
                - Include appropriate timeouts and retries
        
        Example Implementations:
            [
                "sleep 5",  # Allow startup time
                "curl -f http://localhost:8080/health",
                "curl -f http://localhost:8080/api/status"
            ]
        
        Error Handling:
            - Commands should exit with code 1 on failure
            - Include meaningful error messages for debugging
            - Consider retry logic for transient failures
            - Log health check results for monitoring
        """
        pass
    
    @abc.abstractmethod
    def get_service_setup_commands(self) -> List[str]:
        """
        Get service-specific setup and initialization commands.
        Setup commands prepare the environment and resources needed for the service
        to run successfully. These commands are executed before starting the service
        and should handle all necessary initialization tasks.
        
        Returns:
            List[str]: List of bash commands for service setup and initialization.
                Commands typically handle:
                - Directory creation and permissions
                - Configuration file preparation
                - Data initialization
                - Dependency verification
                - Pre-startup validation
        
        Example Implementations:
            [
                "mkdir -p /data/postgres /logs",
                "chown postgres:postgres /data/postgres",
                "chmod 700 /data/postgres",
                "echo 'Initializing database...'",
                "initdb -D /data/postgres"
            ]
        
        Error Handling:
            - Use 'set -e' for fail-fast behavior
            - Include validation steps after setup operations
            - Provide clear error messages for troubleshooting
            - Consider idempotent operations for retry safety
        """
        pass


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
    
    def __post_init__(self):
        if self.target_service is None:
            self.target_service = {}
        if self.parameters is None:
            self.parameters = {}
    
    def get_target_service_name(self) -> str:
        """Get the name of the target service this client connects to"""
        return self.target_service.get('name', 'unknown')
    
    def get_target_service(self) -> Dict[str, Any]:
        """Get the target service configuration"""
        return self.target_service
    
    @abc.abstractmethod
    def get_client_setup_commands(self) -> List[str]:
        """
        Get client-specific setup and initialization commands.
        Setup commands prepare the client environment for executing the workload
        against the target service. These commands handle initialization tasks
        specific to the client type and workload requirements.
        
        Returns:
            List[str]: List of bash commands for client setup and preparation.
                Commands typically handle:
                - Working directory creation
                - Configuration file preparation  
                - Tool and dependency initialization
                - Target service validation
                - Result collection setup
        
        Example Implementations:
            [
                "mkdir -p /results /logs",
                "echo 'Benchmark Client Setup' > /logs/setup.log",
                "echo 'Target Service: {self.target_service}' >> /logs/setup.log",
                "date >> /logs/setup.log"
            ]
        """
        pass
    
    @abc.abstractmethod
    def resolve_service_endpoint(self, target_service_host: str = None, 
                                default_port: int = 8080, protocol: str = "http") -> str:
        """
        This method implements service discovery and endpoint resolution logic,
        combining host information, port configuration, and protocol selection
        into a complete connection URL that the client can use to reach its target service.
        
        Args:
            target_service_host (str, optional): Hostname or IP address where the target
                service is running. If None, the method should determine the host from
                self.target_service configuration or use appropriate defaults.
                
            default_port (int, optional): Default port number to use if not specified
                in service configuration. Default: 8080 (common for HTTP services)
                
            protocol (str, optional): Network protocol to use for connection
                (e.g., 'http', 'https', 'tcp', 'grpc'). Default: 'http'
        
        Returns:
            str: Complete service endpoint URL ready for client connections.
                Format depends on protocol but typically follows URL conventions:
                - HTTP/HTTPS: "http://hostname:port" or "https://hostname:port/path"
        """
        pass
    
    def _get_docker_source(self) -> Optional[str]:
        """Override to use 'benchmark_client' docker source for all clients"""
        docker_sources = self.config.get('containers', {}).get('docker_sources', {})
        return docker_sources.get('benchmark_client')


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
                    'target_service': {
                        'name': 'ollama'               # Required: maps to registry
                    },
                    'container_image': '...',          # Required: container specification
                    'duration': 300,                   # Optional: execution duration
                    'parameters': {...},               # Optional: workload parameters
                    'resources': {...},                # Optional: SLURM resources
                    # ... client-specific fields
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
        target_service = recipe.get('target_service', {})
        service_name = target_service.get('name', 'unknown')
        
        print("debug\n\n\n")
        print(cls._client_registry)
        print(recipe)

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