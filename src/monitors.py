"""
Monitors Module - Manages monitoring instances using Prometheus
"""

import logging
import time
import json
from typing import Dict, List, Optional, Any
from pathlib import Path

from base import BaseModule, JobInfo, ServiceStatus
from services import JobFactory

class MonitorsModule(BaseModule):
    """Manages Prometheus monitoring instances on HPC cluster"""
    
    def __init__(self, config: Dict[str, Any], ssh_client=None):
        super().__init__(config, ssh_client)
        self.monitors_dir = Path(config.get('monitors_dir', 'recipes/monitors'))
        self.metrics_dir = Path(config.get('metrics_dir', 'metrics'))
    
    def list_available_services(self) -> List[str]:
        """List all available monitor types (required by BaseModule)"""
        return ['prometheus']
    
    def list_running_services(self) -> List[str]:
        """List currently running monitor IDs (required by BaseModule)"""
        if self.ssh_client:
            for monitor_id in list(self._running_instances.keys()):
                try:
                    self.check_monitor_status(monitor_id)
                except Exception as e:
                    self.logger.error(f"Error updating status for monitor {monitor_id}: {e}")
        
        return [mid for mid, job_info in self._running_instances.items() 
                if job_info.status in [ServiceStatus.PENDING, ServiceStatus.RUNNING]]
    
    def list_available_monitors(self) -> List[str]:
        """List all available monitor types (currently only Prometheus)"""
        return self.list_available_services()
    
    def list_running_monitors(self) -> List[str]:
        """List currently running monitor IDs"""
        return self.list_running_services()
    
    def start_monitor(self, recipe: dict) -> str:
        """Start a Prometheus monitor instance"""
        monitor_id = self.generate_id()
        self.logger.info(f"Starting monitor {monitor_id}")
        
        try:
            # Create monitor service (Prometheus is a service)
            monitor = JobFactory.create_service(recipe, self.config)
            
            # Generate SLURM script
            script_content = monitor.generate_slurm_script(monitor_id)
            
            # Submit job via SSH
            if self.ssh_client:
                job_id = self.ssh_client.submit_slurm_job(
                    script_content, f"monitor_{monitor_id}.sh"
                )
                
                if job_id:
                    job_info = JobInfo(
                        job_id=job_id,
                        service_id=monitor_id,
                        status=ServiceStatus.PENDING,
                        submitted_at=self.get_current_time()
                    )
                    self._running_instances[monitor_id] = job_info
                    
                    self.logger.info(f"Monitor {monitor_id} submitted as job {job_id}")
                    return monitor_id
                else:
                    raise Exception("Failed to submit SLURM job for monitor")
            else:
                # Local mode - save script
                script_path = Path(f"scripts/monitor_{monitor_id}.sh")
                script_path.parent.mkdir(exist_ok=True)
                with open(script_path, 'w') as f:
                    f.write(script_content)
                
                self.logger.info(f"Monitor script saved to {script_path}")
                return monitor_id
                
        except Exception as e:
            self.logger.error(f"Failed to start monitor {monitor_id}: {e}")
            raise
    
    def stop_monitor(self, monitor_id: str) -> bool:
        """Stop a running monitor"""
        if monitor_id not in self._running_instances:
            self.logger.error(f"Monitor {monitor_id} not found")
            return False
        
        job_info = self._running_instances[monitor_id]
        
        try:
            if self.ssh_client and job_info.job_id:
                success = self.ssh_client.cancel_job(job_info.job_id)
                if success:
                    job_info.status = ServiceStatus.CANCELLED
                    job_info.completed_at = self.get_current_time()
                    self.logger.info(f"Monitor {monitor_id} stopped")
                    return True
                else:
                    self.logger.error(f"Failed to cancel monitor job {job_info.job_id}")
                    return False
            else:
                # Local mode
                job_info.status = ServiceStatus.CANCELLED
                job_info.completed_at = self.get_current_time()
                self.logger.info(f"Monitor {monitor_id} marked as stopped (local mode)")
                return True
                
        except Exception as e:
            self.logger.error(f"Error stopping monitor {monitor_id}: {e}")
            return False
    
    def check_monitor_status(self, monitor_id: str) -> dict:
        """Check health and status of a specific monitor"""
        if monitor_id not in self._running_instances:
            return {"error": f"Monitor {monitor_id} not found"}
        
        job_info = self._running_instances[monitor_id]
        
        # Update status from SLURM if connected
        if self.ssh_client and job_info.job_id:
            try:
                slurm_status = self.ssh_client.get_job_status(job_info.job_id)
                if slurm_status:
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
                        
                        if job_info.status == ServiceStatus.RUNNING and not job_info.started_at:
                            job_info.started_at = self.get_current_time()
                        elif job_info.status in [ServiceStatus.COMPLETED, ServiceStatus.FAILED, ServiceStatus.CANCELLED]:
                            if not job_info.completed_at:
                                job_info.completed_at = self.get_current_time()
                    
                    # Get node information for Prometheus endpoint
                    nodes = slurm_status.get('nodes')
                    if nodes:
                        job_info.nodes = nodes if isinstance(nodes, list) else [nodes]
                    
                    return {
                        "monitor_id": monitor_id,
                        "status": job_info.status.value,
                        "job_id": job_info.job_id,
                        "slurm_state": slurm_state,
                        "nodes": job_info.nodes,
                        "submitted_at": job_info.submitted_at,
                        "started_at": job_info.started_at,
                        "completed_at": job_info.completed_at
                    }
            except Exception as e:
                self.logger.error(f"Error checking monitor status {monitor_id}: {e}")
        
        return {
            "monitor_id": monitor_id,
            "status": job_info.status.value,
            "job_id": job_info.job_id,
            "submitted_at": job_info.submitted_at,
            "started_at": job_info.started_at,
            "completed_at": job_info.completed_at
        }
    
    def get_monitor_endpoint(self, monitor_id: str) -> Optional[str]:
        """Get the Prometheus endpoint URL for a monitor"""
        if monitor_id not in self._running_instances:
            return None
        
        job_info = self._running_instances[monitor_id]
        
        # Get node information
        if job_info.nodes and len(job_info.nodes) > 0:
            host = job_info.nodes[0]
            port = 9090  # Default Prometheus port
            return f"http://{host}:{port}"
        
        # Try to get from SLURM
        if self.ssh_client and job_info.job_id:
            try:
                cmd = f"squeue -j {job_info.job_id} -h -o '%N'"
                result = self.ssh_client.run_command(cmd)
                
                if result and result.strip():
                    node = result.strip()
                    job_info.nodes = [node]
                    port = 9090
                    return f"http://{node}:{port}"
            except Exception as e:
                self.logger.error(f"Error getting monitor endpoint: {e}")
        
        return None
    
    def query_metrics(self, monitor_id: str, query: str) -> dict:
        """Query Prometheus for metrics"""
        endpoint = self.get_monitor_endpoint(monitor_id)
        
        if not endpoint:
            return {"error": "Monitor endpoint not available"}
        
        try:
            import requests
            
            # Build Prometheus query API URL
            query_url = f"{endpoint}/api/v1/query"
            params = {'query': query}
            
            response = requests.get(query_url, params=params, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except ImportError:
            return {"error": "requests library not available for querying"}
        except Exception as e:
            self.logger.error(f"Error querying Prometheus: {e}")
            return {"error": str(e)}
    
    def collect_metrics_to_file(self, monitor_id: str, query: str, output_file: str) -> bool:
        """Collect metrics from Prometheus and save to file"""
        try:
            metrics_data = self.query_metrics(monitor_id, query)
            
            if "error" in metrics_data:
                self.logger.error(f"Failed to collect metrics: {metrics_data['error']}")
                return False
            
            # Create metrics directory if it doesn't exist
            self.metrics_dir.mkdir(parents=True, exist_ok=True)
            
            # Save to file
            output_path = self.metrics_dir / output_file
            with open(output_path, 'w') as f:
                json.dump(metrics_data, f, indent=2)
            
            self.logger.info(f"Metrics saved to {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error collecting metrics to file: {e}")
            return False
    
    def show_metrics(self, monitor_id: str, query: str = None) -> dict:
        """Show current metrics from Prometheus"""
        if query is None:
            # Default query: show all metrics
            query = "up"
        
        return self.query_metrics(monitor_id, query)
    
    def construct_report(self, monitor_id: str, output_file: str) -> bool:
        """Construct a comprehensive monitoring report"""
        try:
            # Get monitor status
            status = self.check_monitor_status(monitor_id)
            
            # Collect various metrics
            report = {
                "monitor_id": monitor_id,
                "report_timestamp": time.time(),
                "monitor_status": status,
                "metrics": {}
            }
            
            # Common Prometheus queries
            queries = {
                "up": "up",  # Service availability
                "cpu_usage": "rate(process_cpu_seconds_total[5m])",
                "memory_usage": "process_resident_memory_bytes",
                "scrape_duration": "scrape_duration_seconds"
            }
            
            for metric_name, query in queries.items():
                try:
                    result = self.query_metrics(monitor_id, query)
                    if "error" not in result:
                        report["metrics"][metric_name] = result
                except Exception as e:
                    self.logger.warning(f"Failed to collect {metric_name}: {e}")
            
            # Save report
            self.metrics_dir.mkdir(parents=True, exist_ok=True)
            output_path = self.metrics_dir / output_file
            
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2)
            
            self.logger.info(f"Report saved to {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error constructing report: {e}")
            return False
    
    def cleanup_completed_monitors(self):
        """Remove completed/failed monitors from tracking"""
        completed_monitors = []
        for monitor_id, job_info in self._running_instances.items():
            if job_info.status in [ServiceStatus.COMPLETED, ServiceStatus.FAILED, ServiceStatus.CANCELLED]:
                completed_monitors.append(monitor_id)
        
        for monitor_id in completed_monitors:
            self.logger.info(f"Cleaning up completed monitor {monitor_id}")
            del self._running_instances[monitor_id]
