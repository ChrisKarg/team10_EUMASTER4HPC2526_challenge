# Student Challenge 2025-2026 (Benchmarking AI Factories on MeluXina supercomputer)

The objective of this challenge is to prepare students for the upcoming AI Factories in the European Union. These AI Factories will harness the power of next-generation HPC and AI systems to revolutionise data processing, analytics, and model deployment. Through this challenge, students will gain practical skills in AI benchmarking, system monitoring, and real-world deployment scenarios—equipping them to design and operate future AI Factory workflows at scale.




# High-Level Architecture Design

## Overview
The **Unified Benchmarking Framework for AI Workflows** is a modular system to orchestrate, benchmark, monitor, and log AI workflows in a reproducible and scalable HPC or Kubernetes environment.  

The framework consists of five main modules: **Servers**, **Clients**, **Monitors**, **Logs**, and **Interface**. Each module exposes a well-defined set of functions for orchestration. All services and clients run in **Apptainer containers** with all dependencies pre-installed.

---

## Modules and Functional Design

### 1. Servers Module
**Purpose:** Manage deployment and lifecycle of services to benchmark.  

**Key Methods / Functions:**
- `start_service(recipe: dict) -> str`  
  Launch a service defined in the recipe on one or multiple nodes. Returns a unique service ID.
- `stop_service(service_id: str) -> bool`  
  Stop a running service by ID.
- `list_available_services() -> List[str]`  
  Return a list of all supported service recipes.
- `list_running_services() -> List[str]`  
  Return a list of all currently running service IDs.
- `check_service_status(service_id: str) -> dict`  
  Return health and resource usage of a specific service.

**Examples of Services:**
- Storage: PostgreSQL, S3  
- Inference: Triton, vLLM  
- Vector DBs: Faiss, Milvus, Weaviate, Chroma

---

### 2. Clients Module
**Purpose:** Launch workloads to benchmark servers.  

**Key Methods / Functions:**
- `start_client(recipe: dict, target_service_id: str) -> str`  
  Launch a client workload against a target service. Returns a client ID.
- `stop_client(client_id: str) -> bool`  
  Stop a running client by ID.
- `list_available_clients() -> List[str]`  
  Return all client workload recipes.
- `list_running_clients() -> List[str]`  
  Return currently running client IDs.
- `check_client_status(client_id: str) -> dict`  
  Return workload progress and resource usage.

**Examples of Client Workloads:**
- Storage: Read/write stress tests for PostgreSQL/S3  
- Inference: Batch requests to Triton/vLLM  
- Vector DB: Query benchmarks for Faiss, Milvus, Weaviate, Chroma

---

### 3. Monitors Module
**Purpose:** Collect and report metrics for servers and clients.  

**Key Methods / Functions:**
- `start_monitor(target_ids: List[str], metrics: List[str]) -> str`  
  Start a monitoring instance for servers or clients. Returns a monitor ID.
- `stop_monitor(monitor_id: str) -> bool`  
  Stop the monitoring instance.
- `list_monitors() -> List[str]`  
  List all defined monitor configurations.
- `list_running_monitors() -> List[str]`  
  List currently active monitors.
- `collect_metrics(monitor_id: str) -> dict`  
  Return metrics collected (CPU, GPU, RAM, I/O, throughput, latency).
- `show_metrics(monitor_id: str)`  
  Display metrics visually (integration with Grafana dashboards).

---

### 4. Logs Module
**Purpose:** Aggregate and manage logs from servers and clients.  

**Key Methods / Functions:**
- `start_log_collection(target_ids: List[str]) -> str`  
  Start collecting logs from specific services/clients. Returns a log collection ID.
- `stop_log_collection(log_id: str) -> bool`  
  Stop log collection.
- `list_logs() -> List[str]`  
  List all log collections.
- `get_logs(log_id: str) -> dict`  
  Retrieve collected logs in structured format (JSON/CSV).
- `show_logs(log_id: str)`  
  Display logs in console or web UI.
- `save_logs(log_id: str, path: str)`  
  Persist logs to central repository for analysis.

---

### 5. Interface Module
**Purpose:** Central orchestration and user-facing management of benchmark experiments.  

**Key Methods / Functions:**
- `load_recipe(file_path: str) -> dict`  
  Load and validate a benchmark recipe.
- `start_benchmark_session(recipe: dict) -> str`  
  Launch an end-to-end benchmark session. Returns a session ID.
- `stop_benchmark_session(session_id: str) -> bool`  
  Stop an ongoing benchmark session.
- `show_servers_status() -> dict`  
  Query all server statuses.
- `show_clients_status() -> dict`  
  Query all client statuses.
- `show_monitors_status() -> dict`  
  Query active monitoring instances.
- `show_logs_status() -> dict`  
  Query available logs.
- `generate_report(session_id: str, output_path: str)`  
  Consolidate metrics, logs, and status into a final report.

---

## Containerization
- **Framework:** Apptainer containers for reproducible execution.  
- **Inclusions:** Python, database clients, SDKs, monitoring agents.  
- **Isolation:** Containers ensure consistent runtime environments across all nodes and GPUs.

---

## Orchestration
- **Scheduler:** Slurm batch scripts or K8S deployments manage jobs.  
- **Reproducibility:** Jobs are designed to run consistently across nodes, GPUs, and clusters.

---

## Benchmarks
- **Target Services:** PostgreSQL, S3, Triton, vLLM, Faiss, Milvus, Weaviate, Chroma  
- **Execution:** Scripts inside containers perform workload benchmarks.  
- **Scalability:** Supports single-node or multi-node execution.

---

## Monitoring & Reporting
- **Metrics:** Collected via Prometheus exporters for CPU, GPU, RAM, I/O, throughput, latency.  
- **Visualization:** Grafana dashboards for live comparison.  
- **Logs & Reports:** Structured logs and CSV/JSON metrics are saved and consolidated into final reports for analysis.







# Global plan of the challenge

The challenge will span 4 months, with students organised into teams. It follows these steps:

## Phase 1 :

### Onboarding

- Introduction to MeluXina and best practices for research and commercial HPC use.
- Familiarisation with Slurm, storage systems, and monitoring tools.
- Exploration & Adoption: In-depth exploration of the assigned topic.
- Define objectives, identify tools and methodologies, and clarify performance metrics.

### What to do:

- Create your own project github (public) and configure it with milestones
- Comment on the issue 1 (https://github.com/LuxProvide/EUMASTER4HPC2526/issues/1 ) to mention your github URL
- Do the onboaring and the examples on meluxina
- Load the example's result/log files on your github
- Schedule meetings (within the group and brainstorm the project)
- Define clear design, identify the tech stacks, create issues on your gitLab

### What I need to look to at the end of the phase:

- Your github
- The logs of the example (per user)
- The design (README file)
- The issues & tasks


## Phase 2 :

-Prototyping: Development of applications, monitoring dashboards, or benchmarking scripts.
-Iterative testing and validation.

## Phase 3:

- Evaluation & Testing: Deployment on MeluXina at realistic scales.
- Performance measurements, resource usage profiling, and scalability testing.
- Report Building: Documentation of methodologies, results, and recommended best practices.
- Creation of comprehensive final reports.

## Phase 4:

-Defense: Each team will present their results and defend their findings in a final session.
Q&A and feedback for improvement.

# Challenge topics: Developing a global benchmarking framework for AI Factory workloads

## Objectives

Design and implement a unified benchmarking framework to evaluate end-to-end performance for critical AI Factory components.
Include benchmarks for:

- File storage, relational databases (e.g., PostgreSQL), and object storage (e.g., S3)
- Inference servers (vLLM, Triton, etc.)
- Vector databases (Chroma, Faiss, Milvus, Weaviate)
- Enable reproducible, modular benchmarking scenarios using Slurm orchestration.
- Provide comparative insights, performance guidelines, and scalability assessments.

## Timeline

- Month 1: Analyse MeluXina’s architecture; survey APIs and services for storage, inference, and retrieval; design benchmark framework architecture.
- Month 2: Develop modular benchmark components:
    - Generic services deployment : Storage, Inference, Vector DB
    - Load generators based on Dask/Spark/Slurm for inference and retrieval tasks
    - Common data schema and metrics collection interface
- Month 3: Execute benchmarks using Slurm; collect throughput, latency, resource usage, and scaling metrics across all components.
- Month 4: Integrate results; generate dashboards and comparisons; finalise documentation and present findings.

## Tools & stacks :

- Modular framework using Python, and Slurm
- Python DB drivers (e.g., psycopg2), S3 SDK for storage benchmarks
- GPU-accelerated inference servers in containerised environments
- Dockerised vector DB deployments for scalable search testing
- Prometheus & Grafana for unified monitoring
- Slurm for orchestrated, synchronised benchmark execution
- Supervision & Mentoring

## Supervision by Dr. Farouk Mansouri:

- Dr. Mansouri Farouk will oversee the challenge, providing strategic and technical supervision with a load of 4 hours per month.
Responsibilities:
- Overall coordination and alignment with AI Factory vision.
Weekly progress reviews.
- Technical deep-dives on HPC practices and system optimisation.


## Mentoring:

- Dedicated mentoring sessions will take place one per week for:
- Technical support and best practices.
-Guidance on tool selection, deployment, and optimisation.
-Assistance with debugging, benchmarking analysis, and report writing.
Preparation for the final defense.
