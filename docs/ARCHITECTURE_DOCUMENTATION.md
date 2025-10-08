# HPC Benchmarking Orchestrator - Architecture Documentation

## Overview

The HPC Benchmarking Orchestrator is a sophisticated system designed to manage containerized services and benchmark workloads on High-Performance Computing (HPC) clusters using SLURM. The system provides automated deployment, monitoring, and lifecycle management of distributed benchmarking experiments.

TODO: Monitor and Logs are not taken into account for now, and CLI interface is though as a minimal interface to run tests

## System Architecture

### High-Level Architecture

```mermaid
graph TB
    CLI[CLI Interface] --> BO[BenchmarkOrchestrator]
    BO --> SM[ServersModule]
    BO --> CM[ClientsModule]
    BO --> SSH[SSHClient]
    
    SM --> SG[ScriptGenerator]
    CM --> SG
    SSH --> HPC[HPC Cluster/SLURM]
    
    SM --> YAML1[Service Recipes]
    CM --> YAML2[Client Recipes]
    
    HPC --> CONT[Container Runtime]
    HPC --> JOBS[SLURM Jobs]
```

### Core Components

1. **BenchmarkOrchestrator**: Central orchestration engine
2. **ServersModule**: Manages service deployments
3. **ClientsModule**: Manages benchmark client workloads
4. **SSHClient**: Handles remote HPC communication
5. **ScriptGenerator**: Generates SLURM batch scripts
6. **BaseModule**: Abstract base class for modules

## Class Diagram

### Core System Classes

```mermaid
classDiagram
    %% Core Orchestration Layer
    class BenchmarkOrchestrator {
        <<Orchestrator>>
        -config: Dict
        -ssh_client: SSHClient
        -servers: ServersModule
        -clients: ClientsModule
        -_active_sessions: Dict
        +load_recipe(file_path: str) dict
        +start_benchmark_session(recipe: dict) str
        +stop_benchmark_session(session_id: str) bool
        +stop_service(service_id: str) bool
        +stop_all_services() dict
        +show_servers_status() dict
        +show_clients_status() dict
        +get_system_status() dict
        +generate_report(session_id: str, output_path: str)
        +cleanup()
    }
    
    %% Abstract Base Module
    class BaseModule {
        <<abstract>>
        #config: Dict
        #ssh_client: SSHClient
        #logger: Logger
        #_running_instances: Dict[str, JobInfo]
        +generate_id() str
        +get_current_time() float
        +list_available_services()* List[str]
        +list_running_services()* List[str]
    }
    
    %% Service Management
    class ServersModule {
        <<Module>>
        -script_generator: ScriptGenerator
        -services_dir: Path
        -service_definitions: Dict
        +_load_service_definitions()
        +list_available_services() List[str]
        +list_running_services() List[str]
        +list_all_services() dict
        +start_service(recipe: dict) str
        +stop_service(service_id: str) bool
        +check_service_status(service_id: str) dict
        +cleanup_completed_services()
    }
    
    %% Client Management
    class ClientsModule {
        <<Module>>
        -script_generator: ScriptGenerator
        -clients_dir: Path
        -client_definitions: Dict
        +_load_client_definitions()
        +list_available_clients() List[str]
        +list_running_clients() List[str]
        +start_client(recipe: dict, target_service_id: str) str
        +stop_client(client_id: str) bool
        +check_client_status(client_id: str) dict
        +cleanup_completed_clients()
    }
    
    %% Infrastructure Layer
    class SSHClient {
        <<Infrastructure>>
        -hostname: str
        -username: str
        -password: str
        -key_filename: str
        -port: int
        -client: paramiko.SSHClient
        +connect() bool
        +disconnect()
        +execute_command(command: str) Tuple[int, str, str]
        +upload_file(local_path: str, remote_path: str) bool
        +download_file(remote_path: str, local_path: str) bool
        +submit_slurm_job(script_content: str) str
        +cancel_slurm_job(job_id: str) bool
        +get_job_status(job_id: str) dict
    }
    
    class ScriptGenerator {
        <<Utility>>
        -config: Dict
        -default_slurm_config: Dict
        +generate_service_script(service_config: ServiceConfig, service_id: str) str
        +generate_client_script(client_config: ClientConfig, client_id: str) str
        +_build_container_commands(image: str) List[str]
        +_get_singularity_run_command(config: ServiceConfig|ClientConfig) str
    }
    
    %% Configuration Data Classes
    class ServiceConfig {
        <<DataClass>>
        +name: str
        +container_image: str
        +resources: Dict
        +environment: Dict
        +ports: List[int]
        +command: str
        +args: List[str]
    }
    
    class ClientConfig {
        <<DataClass>>
        +name: str
        +container_image: str
        +target_service: Dict
        +workload_type: str
        +duration: int
        +resources: Dict
        +environment: Dict
        +parameters: Dict
    }
    
    %% Runtime Data Classes
    class JobInfo {
        <<DataClass>>
        +job_id: str
        +service_id: str
        +status: ServiceStatus
        +submitted_at: float
        +started_at: float
        +completed_at: float
        +nodes: List[str]
        +logs_path: str
    }
    
    class ServiceStatus {
        <<enumeration>>
        PENDING
        RUNNING
        COMPLETED
        FAILED
        CANCELLED
    }
    
    %% Inheritance Relationships
    BaseModule <|-- ServersModule : inherits
    BaseModule <|-- ClientsModule : inherits
    
    %% Composition Relationships
    BenchmarkOrchestrator *-- ServersModule : contains
    BenchmarkOrchestrator *-- ClientsModule : contains
    BenchmarkOrchestrator *-- SSHClient : contains
    
    %% Dependency Relationships
    ServersModule ..> ScriptGenerator : uses
    ClientsModule ..> ScriptGenerator : uses
    ServersModule ..> ServiceConfig : creates
    ClientsModule ..> ClientConfig : creates
    BaseModule ..> JobInfo : manages
    JobInfo ..> ServiceStatus : has status
```
```

### Simplified Component View

```mermaid
graph TD
    %% Main Components
    BO[🎯 BenchmarkOrchestrator<br/>Central Orchestration Engine]
    SM[🖥️ ServersModule<br/>Service Management]
    CM[📊 ClientsModule<br/>Benchmark Client Management]
    SSH[🔐 SSHClient<br/>HPC Communication]
    SG[📝 ScriptGenerator<br/>SLURM Script Generation]
    
    %% Data Components
    SC[⚙️ ServiceConfig<br/>Service Configuration]
    CC[⚙️ ClientConfig<br/>Client Configuration]
    JI[📋 JobInfo<br/>Job Tracking]
    
    %% Relationships
    BO --> SM
    BO --> CM
    BO --> SSH
    SM --> SG
    CM --> SG
    SM --> SC
    CM --> CC
    SM --> JI
    CM --> JI
    
    %% External Systems
    SSH --> HPC[🏢 HPC Cluster<br/>SLURM Workload Manager]
    
    %% Styling
    classDef orchestrator fill:#e1f5fe,stroke:#01579b,stroke-width:3px
    classDef module fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef infrastructure fill:#e8f5e8,stroke:#1b5e20,stroke-width:2px
    classDef config fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef external fill:#ffebee,stroke:#c62828,stroke-width:2px
    
    class BO orchestrator
    class SM,CM module
    class SSH,SG infrastructure
    class SC,CC,JI config
    class HPC external
```

## Sequence Diagrams

### 1. Benchmark Session Lifecycle

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant BO as BenchmarkOrchestrator
    participant SM as ServersModule
    participant CM as ClientsModule
    participant SSH as SSHClient
    participant HPC as HPC Cluster
    
    User->>CLI: Execute benchmark recipe
    CLI->>BO: load_recipe(recipe_path)
    BO->>BO: Validate recipe structure
    
    User->>CLI: Start benchmark session
    CLI->>BO: start_benchmark_session(recipe)
    
    Note over BO,HPC: Service Deployment Phase
    BO->>SM: start_service(service_recipe)
    SM->>SM: Generate unique service_id
    SM->>ScriptGenerator: generate_service_script(config, id)
    ScriptGenerator-->>SM: SLURM script content
    SM->>SSH: submit_slurm_job(script)
    SSH->>HPC: sbatch script.sh
    HPC-->>SSH: job_id
    SSH-->>SM: job_id
    SM->>SM: Track service in _running_instances
    SM-->>BO: service_id
    
    Note over BO,HPC: Service Readiness Check
    BO->>SM: check_service_status(service_id)
    SM->>SSH: get_job_status(job_id)
    SSH->>HPC: squeue -j job_id
    HPC-->>SSH: job status
    SSH-->>SM: status info
    SM-->>BO: service status
    
    Note over BO,HPC: Client Deployment Phase
    BO->>CM: start_client(client_recipe, service_id)
    CM->>CM: Generate unique client_id
    CM->>ScriptGenerator: generate_client_script(config, id)
    ScriptGenerator-->>CM: SLURM script content
    CM->>SSH: submit_slurm_job(script)
    SSH->>HPC: sbatch script.sh
    HPC-->>SSH: job_id
    SSH-->>CM: job_id
    CM->>CM: Track client in _running_instances
    CM-->>BO: client_id
    
    BO-->>CLI: session_id
    CLI-->>User: Session started: session_id
```

### 2. Service Deployment Flow

```mermaid
sequenceDiagram
    participant BO as BenchmarkOrchestrator
    participant SM as ServersModule
    participant SG as ScriptGenerator
    participant SSH as SSHClient
    participant HPC as HPC Cluster
    
    BO->>SM: start_service(recipe)
    SM->>SM: _parse_service_recipe(recipe)
    SM->>SM: generate_id()
    
    Note over SM,SG: Script Generation
    SM->>SG: generate_service_script(config, service_id)
    SG->>SG: Extract resource requirements
    SG->>SG: Build SLURM directives
    SG->>SG: Generate container commands
    SG->>SG: Add environment variables
    SG->>SG: Add networking setup
    SG-->>SM: Complete SLURM script
    
    Note over SM,HPC: Job Submission
    SM->>SSH: submit_slurm_job(script_content)
    SSH->>SSH: Create temporary script file
    SSH->>HPC: Upload script to HPC
    SSH->>HPC: sbatch script.sh
    HPC-->>SSH: SLURM job_id
    SSH-->>SM: job_id
    
    Note over SM: State Tracking
    SM->>SM: Create JobInfo(job_id, service_id, PENDING)
    SM->>SM: Add to _running_instances
    SM-->>BO: service_id
```

### 3. Status Monitoring Flow

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant BO as BenchmarkOrchestrator
    participant SM as ServersModule
    participant SSH as SSHClient
    participant HPC as HPC Cluster
    
    User->>CLI: Check system status
    CLI->>BO: get_system_status()
    
    BO->>SM: show_servers_status()
    
    loop For each running service
        SM->>SM: check_service_status(service_id)
        SM->>SSH: get_job_status(job_id)
        SSH->>HPC: squeue -j job_id
        HPC-->>SSH: Job state, nodes, etc.
        SSH-->>SM: Job information
        SM->>SM: Update JobInfo status
        SM->>SM: Parse node assignments
    end
    
    SM->>SM: cleanup_completed_services()
    SM-->>BO: Services status summary
    
    BO->>CM: show_clients_status()
    CM-->>BO: Clients status summary
    
    BO->>BO: Compile system overview
    BO-->>CLI: Complete system status
    CLI-->>User: Status report
```

### 4. Error Handling and Cleanup

```mermaid
sequenceDiagram
    participant BO as BenchmarkOrchestrator
    participant SM as ServersModule
    participant SSH as SSHClient
    participant HPC as HPC Cluster
    
    Note over BO,HPC: Error Detection
    BO->>SM: check_service_status(service_id)
    SM->>SSH: get_job_status(job_id)
    SSH->>HPC: squeue -j job_id
    HPC-->>SSH: Job FAILED status
    SSH-->>SM: FAILED status
    SM->>SM: Update JobInfo.status = FAILED
    SM-->>BO: Service failed
    
    Note over BO,HPC: Cleanup Process
    BO->>SM: stop_all_services()
    
    loop For each service
        SM->>SSH: cancel_slurm_job(job_id)
        SSH->>HPC: scancel job_id
        HPC-->>SSH: Job cancelled
        SSH-->>SM: Success
        SM->>SM: Update JobInfo.status = CANCELLED
    end
    
    SM->>SM: cleanup_completed_services()
    SM-->>BO: Cleanup summary
```

## Key Design Patterns

### 1. **Abstract Factory Pattern**
- `BaseModule` serves as an abstract base for `ServersModule` and `ClientsModule`
- Provides common interface for service management across different module types

### 2. **Strategy Pattern**
- `ScriptGenerator` implements different script generation strategies
- Configurable SLURM parameters based on resource requirements

### 3. **Observer Pattern**
- Status monitoring through periodic SLURM queries
- Event-driven updates to service and client states

### 4. **Command Pattern**
- SSH operations encapsulated as commands
- SLURM job operations abstracted through SSH interface

## Data Flow Architecture

### Configuration Flow
1. **Config Loading**: YAML configuration files loaded at startup
2. **Recipe Processing**: Service and client recipes parsed from YAML
3. **Script Generation**: Dynamic SLURM script creation based on configurations
4. **Resource Allocation**: SLURM directives generated based on resource requirements

### Job Lifecycle Flow
1. **Submission**: SLURM jobs submitted via SSH
2. **Tracking**: Job IDs stored in internal state
3. **Monitoring**: Periodic status updates via SLURM queries
4. **Cleanup**: Completed/failed jobs removed from tracking

### Communication Flow
1. **CLI → Orchestrator**: User commands processed
2. **Orchestrator → Modules**: Delegated operations
3. **Modules → SSH**: Remote execution
4. **SSH → HPC**: SLURM operations

## Error Handling Strategy

### Hierarchical Error Management
- **Connection Errors**: SSH connectivity issues handled at client level
- **Job Errors**: SLURM job failures tracked in JobInfo status
- **Configuration Errors**: Recipe validation before execution
- **Resource Errors**: Graceful handling of resource allocation failures

### Recovery Mechanisms
- **Automatic Retry**: Failed SSH operations retried with backoff
- **State Cleanup**: Orphaned jobs detected and cleaned up
- **Graceful Degradation**: System continues operation with partial failures

## Performance Considerations

### Scalability
- **Concurrent Operations**: Multiple services/clients managed simultaneously
- **Resource Optimization**: Dynamic resource allocation based on requirements
- **State Management**: Efficient tracking of large numbers of jobs

### Monitoring Overhead
- **Lazy Evaluation**: Status updates only when requested
- **Batch Operations**: Multiple SLURM queries combined where possible
- **Caching**: Service definitions cached in memory

## Security Model

### Authentication
- **SSH Key-based**: Secure key-based authentication to HPC clusters
- **User Isolation**: Jobs run under authenticated user context
- **Network Security**: Container networking configured for secure communication

### Authorization
- **SLURM ACLs**: Resource access controlled by SLURM policies
- **Container Isolation**: Services isolated through container boundaries
- **File Permissions**: Proper permissions for scripts and data files

## Deployment Architecture

### Container Management
- **Singularity Integration**: Native support for Singularity containers
- **Image Building**: Automatic container building on HPC nodes
- **Registry Support**: Support for container registries and local images

### Resource Management
- **GPU Allocation**: Automatic GPU resource allocation for workloads
- **Memory Management**: Dynamic memory allocation based on service requirements
- **Network Configuration**: Automatic port allocation and networking setup

This architecture provides a robust, scalable, and maintainable foundation for managing complex benchmarking experiments on HPC infrastructure.