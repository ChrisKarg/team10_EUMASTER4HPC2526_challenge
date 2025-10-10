"""
Clients Module - Launch workloads to benchmark servers
"""

import logging
import os
import yaml
from typing import Dict, List, Optional, Any
from pathlib import Path

from base import BaseModule, ClientConfig, JobInfo, ServiceStatus
from script_generator import ScriptGenerator

class ClientsModule(BaseModule):
    """Manages client workloads on HPC cluster"""
    
    def __init__(self, config: Dict[str, Any], ssh_client=None):
        super().__init__(config, ssh_client)
        self.script_generator = ScriptGenerator(config)
        self.clients_dir = Path(config.get('clients_dir', 'recipes/clients'))
        self._load_client_definitions()
    
    def _load_client_definitions(self):
        """Load client definitions from YAML files"""
        self.client_definitions = {}
        
        if not self.clients_dir.exists():
            self.logger.warning(f"Clients directory not found: {self.clients_dir}")
            return
        
        for yaml_file in self.clients_dir.glob("*.yaml"):
            try:
                with open(yaml_file, 'r') as f:
                    client_def = yaml.safe_load(f)
                    client_name = client_def.get('name', yaml_file.stem)
                    self.client_definitions[client_name] = client_def
                    self.logger.debug(f"Loaded client definition: {client_name}")
            except Exception as e:
                self.logger.error(f"Failed to load client definition {yaml_file}: {e}")
    
    def list_available_services(self) -> List[str]:
        """Return a list of all supported client recipes (implementing BaseModule interface)"""
        return self.list_available_clients()
    
    def list_available_clients(self) -> List[str]:
        """Return all client workload recipes"""
        return list(self.client_definitions.keys())
    
    def list_running_services(self) -> List[str]:
        """Return currently running client IDs (implementing BaseModule interface)"""
        return self.list_running_clients()
    
    def list_running_clients(self) -> List[str]:
        """Return currently running client IDs"""
        # First update statuses from SLURM to get accurate state
        if self.ssh_client:
            for client_id in list(self._running_instances.keys()):
                try:
                    # Update status for each client
                    self.check_client_status(client_id)
                except Exception as e:
                    self.logger.error(f"Error updating status for client {client_id}: {e}")
        
        # Return clients that are active (pending or running)
        return [cid for cid, job_info in self._running_instances.items() 
                if job_info.status in [ServiceStatus.PENDING, ServiceStatus.RUNNING]]
    
    def start_client(self, recipe: dict, target_service_id: str, target_service_host: str = None) -> str:
        """Launch a client workload against a target service"""
        
        client_id = self.generate_id()
        self.logger.info(f"Starting client {client_id} with recipe: {recipe}")
        self.logger.info(f"Target service ID: {target_service_id}")
        self.logger.info(f"Target service host: {target_service_host}")
        
        try:
            # Parse recipe to create client config
            client_config = self._parse_client_recipe(recipe)
            self.logger.info(f"Client config workload type: {client_config.workload_type}")
            self.logger.info(f"Client config target_service: {client_config.target_service}")
            
            # Generate SLURM script
            script_content = self.script_generator.generate_client_script(
                client_config, client_id, target_service_host
            )
            
            # Submit job via SSH
            if self.ssh_client:
                # Upload benchmark script if this is an ollama_benchmark client
                if client_config.workload_type == "ollama_benchmark":
                    # Try the new ensure_benchmark_script method first
                    if hasattr(self.ssh_client, 'ensure_benchmark_script'):
                        if self.ssh_client.ensure_benchmark_script("ollama_benchmark.py"):
                            self.logger.info("Benchmark script uploaded to remote home directory")
                        else:
                            self.logger.warning("Failed to upload benchmark script to home directory")
                    
                    # Also try the /tmp/ upload as fallback
                    possible_paths = [
                        "benchmark_scripts/ollama_benchmark.py",
                        "../benchmark_scripts/ollama_benchmark.py"
                    ]
                    
                    benchmark_script_path = None
                    for path in possible_paths:
                        if os.path.exists(path):
                            benchmark_script_path = path
                            break
                    
                    if benchmark_script_path:
                        remote_script_path = f"/tmp/ollama_benchmark_{client_id}.py"
                        self.logger.info(f"Attempting to upload {benchmark_script_path} to {remote_script_path}")
                        if self.ssh_client.upload_file(benchmark_script_path, remote_script_path):
                            self.logger.info(f"Successfully uploaded benchmark script to {remote_script_path}")
                        else:
                            self.logger.error("Failed to upload benchmark script to /tmp/")
                    else:
                        self.logger.error(f"Benchmark script not found in any of these locations: {possible_paths}")
                        self.logger.error(f"Current working directory: {os.getcwd()}")
                
                # DEBUG: Log the generated script content
                self.logger.debug(f"Generated SLURM script for client {client_id}:\n{script_content}")

                job_id = self.ssh_client.submit_slurm_job(
                    script_content, f"client_{client_id}.sh"
                )
                
                if job_id:
                    # Track the job
                    job_info = JobInfo(
                        job_id=job_id,
                        service_id=client_id,
                        status=ServiceStatus.PENDING,
                        submitted_at=self.get_current_time()
                    )
                    self._running_instances[client_id] = job_info
                    
                    self.logger.info(f"Client {client_id} submitted as job {job_id}")
                    return client_id
                else:
                    raise Exception("Failed to submit SLURM job")
            else:
                # Local mode - just save the script
                script_path = Path(f"scripts/client_{client_id}.sh")
                script_path.parent.mkdir(exist_ok=True)
                with open(script_path, 'w') as f:
                    f.write(script_content)
                
                self.logger.info(f"Client script saved to {script_path}")
                return client_id
                
        except Exception as e:
            self.logger.error(f"Failed to start client {client_id}: {e}")
            raise
    
    def stop_client(self, client_id: str) -> bool:
        """Stop a running client by ID"""
        
        if client_id not in self._running_instances:
            self.logger.error(f"Client {client_id} not found")
            return False
        
        job_info = self._running_instances[client_id]
        
        try:
            if self.ssh_client and job_info.job_id:
                success = self.ssh_client.cancel_job(job_info.job_id)
                if success:
                    job_info.status = ServiceStatus.CANCELLED
                    job_info.completed_at = self.get_current_time()
                    self.logger.info(f"Client {client_id} stopped")
                    return True
                else:
                    self.logger.error(f"Failed to cancel job {job_info.job_id}")
                    return False
            else:
                # Local mode - just mark as stopped
                job_info.status = ServiceStatus.CANCELLED
                job_info.completed_at = self.get_current_time()
                self.logger.info(f"Client {client_id} marked as stopped (local mode)")
                return True
                
        except Exception as e:
            self.logger.error(f"Error stopping client {client_id}: {e}")
            return False
    
    def check_client_status(self, client_id: str) -> dict:
        """Return workload progress and resource usage"""
        
        if client_id not in self._running_instances:
            return {"error": f"Client {client_id} not found"}
        
        job_info = self._running_instances[client_id]
        
        # Update status from SLURM if connected
        if self.ssh_client and job_info.job_id:
            try:
                slurm_status = self.ssh_client.get_job_status(job_info.job_id)
                if slurm_status:
                    # Map SLURM states to our status enum
                    state_mapping = {
                        'PENDING': ServiceStatus.PENDING,
                        'RUNNING': ServiceStatus.RUNNING,
                        'COMPLETED': ServiceStatus.COMPLETED,
                        'FAILED': ServiceStatus.FAILED,
                        'CANCELLED': ServiceStatus.CANCELLED,
                        'TIMEOUT': ServiceStatus.FAILED
                    }
                    
                    slurm_state = slurm_status.get('state', 'UNKNOWN')
                    if slurm_state in state_mapping:
                        job_info.status = state_mapping[slurm_state]
                        
                        # Update timing info
                        if job_info.status == ServiceStatus.RUNNING and not job_info.started_at:
                            job_info.started_at = self.get_current_time()
                        elif job_info.status in [ServiceStatus.COMPLETED, ServiceStatus.FAILED, ServiceStatus.CANCELLED]:
                            if not job_info.completed_at:
                                job_info.completed_at = self.get_current_time()
                    
                    return {
                        "client_id": client_id,
                        "status": job_info.status.value,
                        "job_id": job_info.job_id,
                        "slurm_state": slurm_state,
                        "nodes": slurm_status.get('nodes'),
                        "submitted_at": job_info.submitted_at,
                        "started_at": job_info.started_at,
                        "completed_at": job_info.completed_at
                    }
                else:
                    # Job not found in SLURM - might have completed very quickly
                    # Only mark as completed if it was previously pending/running
                    if job_info.status in [ServiceStatus.PENDING, ServiceStatus.RUNNING]:
                        self.logger.warning(f"Job {job_info.job_id} not found in SLURM, marking as completed")
                        job_info.status = ServiceStatus.COMPLETED
                        if not job_info.completed_at:
                            job_info.completed_at = self.get_current_time()
            except Exception as e:
                self.logger.error(f"Error checking status for client {client_id}: {e}")
        
        # Return basic status
        return {
            "client_id": client_id,
            "status": job_info.status.value,
            "job_id": job_info.job_id,
            "submitted_at": job_info.submitted_at,
            "started_at": job_info.started_at,
            "completed_at": job_info.completed_at
        }
    
    def _parse_client_recipe(self, recipe: dict) -> ClientConfig:
        """Parse recipe dictionary into ClientConfig"""
        
        client_def = recipe.get('client', {})
        
        # Get client template if specified
        client_type = client_def.get('type')
        if client_type and client_type in self.client_definitions:
            template = self.client_definitions[client_type]
            # Merge template with recipe overrides
            merged_def = {**template, **client_def}
        else:
            merged_def = client_def
        
        return ClientConfig(
            name=merged_def.get('name', 'unknown'),
            container_image=merged_def.get('container_image', 'unknown'),
            target_service=merged_def.get('target_service', {}),  # Store as dict to preserve port info
            workload_type=merged_def.get('workload_type', 'generic'),
            duration=merged_def.get('duration', 300),
            resources=merged_def.get('resources', {}),
            environment=merged_def.get('environment', {}),
            parameters=merged_def.get('parameters', {})
        )
    
    def cleanup_completed_clients(self):
        """Remove completed/failed clients from tracking"""
        completed_clients = []
        for client_id, job_info in self._running_instances.items():
            if job_info.status in [ServiceStatus.COMPLETED, ServiceStatus.FAILED, ServiceStatus.CANCELLED]:
                completed_clients.append(client_id)
        
        for client_id in completed_clients:
            self.logger.info(f"Cleaning up completed client {client_id}")
            del self._running_instances[client_id]