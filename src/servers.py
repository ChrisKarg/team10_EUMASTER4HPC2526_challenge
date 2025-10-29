"""
Servers Module - Manages deployment and lifecycle of services
"""

import logging
import yaml
from typing import Dict, List, Optional, Any
from pathlib import Path

from base import BaseModule, JobInfo, ServiceStatus
from services import JobFactory, Service

class ServersModule(BaseModule):
    """Manages server services on HPC cluster"""
    
    def __init__(self, config: Dict[str, Any], ssh_client=None):
        super().__init__(config, ssh_client)
        self.services_dir = Path(config.get('services_dir', 'recipes/services'))
    
    def list_available_services(self) -> List[str]:
        """Return a list of all available service types from factory"""
        return JobFactory.list_available_services()
    
    def list_running_services(self) -> List[str]:
        """Return a list of all currently running service IDs"""
        # First update statuses from SLURM to get accurate state
        if self.ssh_client:
            for service_id in list(self._running_instances.keys()):
                try:
                    # Update status for each service
                    self.check_service_status(service_id)
                except Exception as e:
                    self.logger.error(f"Error updating status for service {service_id}: {e}")
        
        # Return services that are active (pending or running)
        return [sid for sid, job_info in self._running_instances.items() 
                if job_info.status in [ServiceStatus.PENDING, ServiceStatus.RUNNING]]
    
    def list_all_services(self) -> dict:
        """Return comprehensive list of all services (tracked + SLURM-only)"""
        result = {
            'tracked_services': [],
            'slurm_services': [],
            'all_services': []
        }
        
        # Get tracked services
        for service_id, job_info in self._running_instances.items():
            service_info = {
                'service_id': service_id,
                'job_id': job_info.job_id,
                'status': job_info.status.value if hasattr(job_info.status, 'value') else str(job_info.status),
                'type': 'tracked'
            }
            result['tracked_services'].append(service_info)
            result['all_services'].append(service_info)
        
        # Get SLURM services
        if self.ssh_client:
            try:
                cmd = "squeue -u $USER --format='%i,%j,%T' --noheader"
                exit_code, stdout, stderr = self.ssh_client.execute_command(cmd)
                
                if exit_code == 0 and stdout.strip():
                    for line in stdout.strip().split('\n'):
                        if line.strip():
                            fields = line.split(',')
                            if len(fields) >= 3:
                                job_id = fields[0].strip()
                                job_name = fields[1].strip()
                                job_state = fields[2].strip()
                                
                                # Check if this is a service-related job
                                if any(keyword in job_name.lower() for keyword in ['service', 'ollama', 'server', 'postgres', 'chroma']):
                                    # Check if already tracked
                                    is_tracked = any(info['job_id'] == job_id for info in result['tracked_services'])
                                    
                                    if not is_tracked:
                                        service_info = {
                                            'service_id': job_name,
                                            'job_id': job_id,
                                            'status': job_state,
                                            'type': 'slurm_only'
                                        }
                                        result['slurm_services'].append(service_info)
                                        result['all_services'].append(service_info)
            except Exception as e:
                self.logger.error(f"Error getting SLURM services: {e}")
        
        return result
    
    def start_service(self, recipe: dict, target_service_id: Optional[str] = None) -> str:
        """Launch a service defined in the recipe on one or multiple nodes"""
        
        service_id = self.generate_id()
        self.logger.info(f"Starting service {service_id} with recipe: {recipe}")
        
        try:
            # Create service using new factory pattern
            service = JobFactory.create_service(recipe, self.config)
            
            # If this is a Prometheus service with monitoring targets, resolve hosts
            if hasattr(service, 'monitoring_targets') and service.monitoring_targets:
                self.logger.info("Resolving monitoring targets for Prometheus service")
                
                # If target_service_id is provided via CLI, use it to override recipe targets
                if target_service_id:
                    self.logger.info(f"Using target service from CLI: {target_service_id}")
                    # Find the host for this service
                    host = self.get_service_host(target_service_id)
                    if host:
                        self.logger.info(f"Resolved target service {target_service_id} to host: {host}")
                        # Update the first monitoring target with the resolved host
                        if service.monitoring_targets:
                            service.monitoring_targets[0]['service_id'] = target_service_id
                            service.monitoring_targets[0]['host'] = host
                    else:
                        self.logger.warning(f"Could not resolve host for target service: {target_service_id}")
                        self.logger.warning("Prometheus will attempt to monitor an unknown host")
                else:
                    # Resolve hosts for all monitoring targets from recipe
                    for target in service.monitoring_targets:
                        target_id = target.get('service_id')
                        if target_id and 'host' not in target:
                            self.logger.info(f"Resolving host for monitoring target: {target_id}")
                            host = self.get_service_host(target_id)
                            if host:
                                self.logger.info(f"Resolved {target_id} to host: {host}")
                                target['host'] = host
                            else:
                                self.logger.warning(f"Could not resolve host for monitoring target: {target_id}")
            
            # Generate SLURM script using job's own method
            script_content = service.generate_slurm_script(service_id)

            # DEBUG: Log the generated script content
            self.logger.debug(f"Generated SLURM script for service {service_id}:\n{script_content}")
            
            # Submit job via SSH
            if self.ssh_client:
                job_id = self.ssh_client.submit_slurm_job(
                    script_content, f"service_{service_id}.sh"
                )
                
                if job_id:
                    # Track the job
                    job_info = JobInfo(
                        job_id=job_id,
                        service_id=service_id,
                        status=ServiceStatus.PENDING,
                        submitted_at=self.get_current_time()
                    )
                    self._running_instances[service_id] = job_info
                    
                    self.logger.info(f"Service {service_id} submitted as job {job_id}")
                    return service_id
                else:
                    raise Exception("Failed to submit SLURM job")
            else:
                # Local mode - just save the script
                script_path = Path(f"scripts/service_{service_id}.sh")
                script_path.parent.mkdir(exist_ok=True)
                with open(script_path, 'w') as f:
                    f.write(script_content)
                
                self.logger.info(f"Service script saved to {script_path}")
                return service_id
                
        except Exception as e:
            self.logger.error(f"Failed to start service {service_id}: {e}")
            raise
    
    def stop_service(self, service_id: str) -> bool:
        """Stop a running service by ID, Job ID, or Job Name"""
        
        # First try direct service ID lookup
        if service_id in self._running_instances:
            return self._stop_service_by_service_id(service_id)
        
        # If not found, try to find by job ID or job name
        return self._stop_service_by_slurm_reference(service_id)
    
    def get_service_host(self, service_id: str) -> Optional[str]:
        """Get the host/node where a service is running"""
        self.logger.debug(f"Getting host for service: {service_id}")
        self.logger.debug(f"Running instances: {list(self._running_instances.keys())}")
        
        if service_id not in self._running_instances:
            self.logger.warning(f"Service {service_id} not found in running instances")
            
            # Try to find in SLURM directly
            if self.ssh_client:
                self.logger.info(f"Attempting to find service {service_id} in SLURM")
                try:
                    # Search for jobs that match the service_id pattern
                    # Service names are typically: servicename_serviceid
                    cmd = f"squeue -u $USER --format='%i,%j,%N' --noheader | grep '{service_id}'"
                    self.logger.debug(f"Running SLURM search command: {cmd}")
                    exit_code, stdout, stderr = self.ssh_client.execute_command(cmd)
                    
                    if exit_code == 0 and stdout.strip():
                        # Parse the output: job_id,job_name,nodes
                        line = stdout.strip().split('\n')[0]  # Get first match
                        parts = line.split(',')
                        if len(parts) >= 3:
                            job_id = parts[0].strip()
                            job_name = parts[1].strip()
                            nodes = parts[2].strip()
                            
                            if nodes and nodes != '(null)':
                                self.logger.info(f"Found service {service_id} in SLURM: job {job_id} on {nodes}")
                                return nodes
                            else:
                                self.logger.warning(f"Service {service_id} found but not yet assigned to a node")
                                return None
                except Exception as e:
                    self.logger.error(f"Error searching SLURM for service {service_id}: {e}")
            
            return None
        
        job_info = self._running_instances[service_id]
        self.logger.debug(f"Job info for {service_id}: job_id={job_info.job_id}, status={job_info.status}, nodes={job_info.nodes}")
        
        # If we have node information, return the first node
        if job_info.nodes and len(job_info.nodes) > 0:
            host = job_info.nodes[0]
            self.logger.info(f"Found cached node for service {service_id}: {host}")
            return host
        
        # If no node info, try to get it from SLURM
        if self.ssh_client and job_info.job_id:
            try:
                # Query SLURM for node information
                cmd = f"squeue -j {job_info.job_id} -h -o '%N'"
                self.logger.debug(f"Running SLURM command: {cmd}")
                result = self.ssh_client.run_command(cmd)
                self.logger.debug(f"SLURM result: '{result}'")
                
                if result and result.strip():
                    node = result.strip()
                    # Update job_info with node information
                    job_info.nodes = [node]
                    self.logger.info(f"Found node for service {service_id} via SLURM: {node}")
                    return node
                else:
                    self.logger.warning(f"No node information returned from SLURM for job {job_info.job_id}")
            except Exception as e:
                self.logger.error(f"Error getting node info for job {job_info.job_id}: {e}")
        else:
            self.logger.warning(f"Cannot query SLURM: ssh_client={self.ssh_client is not None}, job_id={job_info.job_id}")
        
        return None
    
    def _stop_service_by_service_id(self, service_id: str) -> bool:
        """Stop service using internal service ID"""
        job_info = self._running_instances[service_id]
        
        try:
            if self.ssh_client and job_info.job_id:
                success = self.ssh_client.cancel_job(job_info.job_id)
                if success:
                    job_info.status = ServiceStatus.CANCELLED
                    job_info.completed_at = self.get_current_time()
                    self.logger.info(f"Service {service_id} stopped")
                    return True
                else:
                    self.logger.error(f"Failed to cancel job {job_info.job_id}")
                    return False
            else:
                # Local mode - just mark as stopped
                job_info.status = ServiceStatus.CANCELLED
                job_info.completed_at = self.get_current_time()
                self.logger.info(f"Service {service_id} marked as stopped (local mode)")
                return True
                
        except Exception as e:
            self.logger.error(f"Error stopping service {service_id}: {e}")
            return False
    
    def _stop_service_by_slurm_reference(self, reference: str) -> bool:
        """Stop service by SLURM job ID or job name"""
        try:
            if not self.ssh_client:
                self.logger.error("SSH client not available for SLURM operations")
                return False
            
            # Try to find the job by ID or name
            job_id = None
            service_id = None
            
            # Check if it's a numeric job ID
            if reference.isdigit():
                job_id = reference
                # Find corresponding service ID
                for sid, job_info in self._running_instances.items():
                    if job_info.job_id == job_id:
                        service_id = sid
                        break
            else:
                # Try to find by job name or service name pattern
                for sid, job_info in self._running_instances.items():
                    job_name = f"{job_info.service_id}"
                    if (reference in job_name or 
                        reference in sid or 
                        sid.startswith(reference)):
                        job_id = job_info.job_id
                        service_id = sid
                        break
            
            # If still not found, try to get current SLURM jobs and find by name
            if not job_id:
                slurm_status = self._get_slurm_jobs_by_pattern(reference)
                if slurm_status:
                    job_id = slurm_status.get('job_id')
            
            if job_id:
                # Cancel the job
                success = self.ssh_client.cancel_job(job_id)
                if success:
                    self.logger.info(f"Successfully cancelled SLURM job {job_id}")
                    
                    # Update internal tracking if we found the service
                    if service_id and service_id in self._running_instances:
                        job_info = self._running_instances[service_id]
                        job_info.status = ServiceStatus.CANCELLED
                        job_info.completed_at = self.get_current_time()
                    
                    return True
                else:
                    self.logger.error(f"Failed to cancel SLURM job {job_id}")
                    return False
            else:
                self.logger.error(f"Could not find job for reference: {reference}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error stopping service by reference {reference}: {e}")
            return False
    
    def _get_slurm_jobs_by_pattern(self, pattern: str) -> dict:
        """Get SLURM job info by name pattern"""
        try:
            if not self.ssh_client:
                return None
            
            # Use squeue to find jobs by name pattern
            cmd = f"squeue -u $USER --format='%i,%j,%T' --noheader | grep -i '{pattern}' | head -1"
            exit_code, stdout, stderr = self.ssh_client.execute_command(cmd)
            
            if exit_code == 0 and stdout.strip():
                fields = stdout.strip().split(',')
                if len(fields) >= 3:
                    return {
                        'job_id': fields[0].strip(),
                        'name': fields[1].strip(),
                        'state': fields[2].strip()
                    }
            return None
            
        except Exception as e:
            self.logger.error(f"Error searching SLURM jobs: {e}")
            return None
    
    def check_service_status(self, service_id: str) -> dict:
        """Return health and resource usage of a specific service"""
        
        if service_id not in self._running_instances:
            return {"error": f"Service {service_id} not found"}
        
        job_info = self._running_instances[service_id]
        
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
                        "service_id": service_id,
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
                self.logger.error(f"Error checking status for service {service_id}: {e}")
        
        # Return basic status
        return {
            "service_id": service_id,
            "status": job_info.status.value,
            "job_id": job_info.job_id,
            "submitted_at": job_info.submitted_at,
            "started_at": job_info.started_at,
            "completed_at": job_info.completed_at
        }
    
    def cleanup_completed_services(self):
        """Remove completed/failed services from tracking"""
        completed_services = []
        for service_id, job_info in self._running_instances.items():
            if job_info.status in [ServiceStatus.COMPLETED, ServiceStatus.FAILED, ServiceStatus.CANCELLED]:
                completed_services.append(service_id)
        
        for service_id in completed_services:
            self.logger.info(f"Cleaning up completed service {service_id}")
            del self._running_instances[service_id]