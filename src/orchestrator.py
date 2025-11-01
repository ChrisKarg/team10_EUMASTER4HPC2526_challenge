"""
Orchestrator Module - Central orchestration and benchmark management engine
"""

import logging
import yaml
import os
from typing import Dict, List, Optional, Any
from pathlib import Path

from ssh_client import SSHClient
from servers import ServersModule
from clients import ClientsModule
from monitors import MonitorsModule

class BenchmarkOrchestrator:
    """Central orchestration engine for benchmark experiments"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Initialize SSH client if HPC config provided
        self.ssh_client = None
        if 'hpc' in self.config:
            hpc_config = self.config['hpc']
            self.ssh_client = SSHClient(
                hostname=hpc_config.get('hostname'),
                username=hpc_config.get('username'),
                password=hpc_config.get('password'),
                key_filename=hpc_config.get('key_filename'),
                port=hpc_config.get('port', 8822)
            )
            
            # Try to connect
            if not self.ssh_client.connect():
                self.logger.warning("Failed to connect to HPC cluster. Running in local mode.")
                self.ssh_client = None
        
        # Initialize modules
        self.servers = ServersModule(self.config, self.ssh_client)
        self.clients = ClientsModule(self.config, self.ssh_client)
        self.monitors = MonitorsModule(self.config, self.ssh_client)
        
        # Track active sessions
        self._active_sessions: Dict[str, Dict[str, Any]] = {}
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    self.logger.info(f"Loaded configuration from {config_path}")
                    return config
            except Exception as e:
                self.logger.error(f"Failed to load config {config_path}: {e}")
        
        # Return default configuration
        self.logger.warning("Using default configuration")
        return {
            'services_dir': 'recipes/services',
            'clients_dir': 'recipes/clients',
            'slurm': {
                'account': 'p200981',
                'partition': 'gpu',
                'qos': 'default',
                'time': '01:00:00',
                'nodes': 1,
                'ntasks': 1,
                'ntasks_per_node': 1
            }
        }
    
    def load_recipe(self, file_path: str) -> dict:
        """Load and validate a benchmark recipe"""
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Recipe file not found: {file_path}")
        
        try:
            with open(file_path, 'r') as f:
                recipe = yaml.safe_load(f)
            
            # Basic validation
            if not isinstance(recipe, dict):
                raise ValueError("Recipe must be a dictionary")
            
            # Validate required sections
            if 'service' not in recipe and 'client' not in recipe:
                raise ValueError("Recipe must contain at least 'service' or 'client' section")
            
            # Log what type of recipe this is
            if 'service' in recipe and 'client' in recipe:
                self.logger.info("Loaded combined service+client recipe")
            elif 'service' in recipe:
                self.logger.info("Loaded service-only recipe")
            elif 'client' in recipe:
                self.logger.info("Loaded client-only recipe")
            
            self.logger.info(f"Loaded recipe from {file_path}")
            return recipe
            
        except Exception as e:
            self.logger.error(f"Failed to load recipe {file_path}: {e}")
            raise
    
    def start_benchmark_session(self, recipe: dict, target_service_id: str = None) -> str:
        """Launch an end-to-end benchmark session"""
        
        session_id = f"session_{len(self._active_sessions) + 1}"
        self.logger.info(f"Starting benchmark session {session_id}")
        
        session_info = {
            'session_id': session_id,
            'recipe': recipe,
            'services': [],
            'clients': [],
            'status': 'starting',
            'started_at': self.servers.get_current_time()
        }
        
        try:
            # Start services first
            if 'service' in recipe:
                self.logger.info("Starting service...")
                service_id = self.servers.start_service(recipe, target_service_id)
                session_info['services'].append(service_id)
                self.logger.info(f"Service started: {service_id}")
            
            # Start clients (can target the service)
            if 'client' in recipe:
                target_service = session_info['services'][0] if session_info['services'] else None
                target_service_host = None
                
                # Resolve service host if we have a target service
                if target_service:
                    self.logger.info(f"Attempting to resolve host for service: {target_service}")
                    
                    # Wait a bit for the service to get assigned to a node
                    import time
                    for attempt in range(6):  # Try for up to 30 seconds
                        target_service_host = self.servers.get_service_host(target_service)
                        if target_service_host:
                            self.logger.info(f"✅ Resolved service {target_service} to host: {target_service_host}")
                            break
                        else:
                            self.logger.info(f"🔄 Attempt {attempt + 1}/6: Service host not yet available, waiting 5s...")
                            time.sleep(5)
                    
                    if not target_service_host:
                        self.logger.warning(f"❌ Could not resolve host for service {target_service} after 30 seconds")
                else:
                    self.logger.info("No target service specified")
                
                self.logger.info(f"Starting client targeting service: {target_service}")
                client_id = self.clients.start_client(recipe, target_service, target_service_host)
                session_info['clients'].append(client_id)
                self.logger.info(f"Client started: {client_id}")
            
            session_info['status'] = 'running'
            self._active_sessions[session_id] = session_info
            
            self.logger.info(f"Benchmark session {session_id} started successfully")
            return session_id
            
        except Exception as e:
            session_info['status'] = 'failed'
            session_info['error'] = str(e)
            self._active_sessions[session_id] = session_info
            self.logger.error(f"Failed to start benchmark session {session_id}: {e}")
            raise
    
    def stop_benchmark_session(self, session_id: str) -> bool:
        """Stop an ongoing benchmark session"""
        
        if session_id not in self._active_sessions:
            self.logger.error(f"Session {session_id} not found")
            return False
        
        session_info = self._active_sessions[session_id]
        self.logger.info(f"Stopping benchmark session {session_id}")
        
        success = True
        
        try:
            # Stop clients first
            for client_id in session_info['clients']:
                if not self.clients.stop_client(client_id):
                    success = False
            
            # Stop services
            for service_id in session_info['services']:
                if not self.servers.stop_service(service_id):
                    success = False
            
            session_info['status'] = 'stopped' if success else 'partially_stopped'
            session_info['stopped_at'] = self.servers.get_current_time()
            
            self.logger.info(f"Benchmark session {session_id} stopped")
            return success
            
        except Exception as e:
            session_info['status'] = 'error'
            session_info['error'] = str(e)
            self.logger.error(f"Error stopping session {session_id}: {e}")
            return False
    
    def stop_service(self, service_id: str) -> bool:
        """Stop a specific service by ID"""
        try:
            return self.servers.stop_service(service_id)
        except Exception as e:
            self.logger.error(f"Error stopping service {service_id}: {e}")
            return False
    
    def stop_all_services(self) -> dict:
        """Stop all running services"""
        try:
            # Get comprehensive list of all services
            all_services = self.servers.list_all_services()
            
            results = {
                'total_services': len(all_services['all_services']),
                'stopped_services': 0,
                'failed_services': 0,
                'results': {}
            }
            
            for service_info in all_services['all_services']:
                service_id = service_info['service_id']
                try:
                    # Use the enhanced stop_service method
                    if self.servers.stop_service(service_id):
                        results['stopped_services'] += 1
                        results['results'][service_id] = 'stopped'
                    else:
                        # Try using job_id if service_id failed
                        job_id = service_info.get('job_id')
                        if job_id and self.servers.stop_service(job_id):
                            results['stopped_services'] += 1
                            results['results'][service_id] = f'stopped (via job_id {job_id})'
                        else:
                            results['failed_services'] += 1
                            results['results'][service_id] = 'failed'
                except Exception as e:
                    results['failed_services'] += 1
                    results['results'][service_id] = f'error: {str(e)}'
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error stopping all services: {e}")
            return {'error': str(e)}
    
    def debug_services(self) -> dict:
        """Debug information about all services for troubleshooting"""
        try:
            debug_info = {
                'tracked_services': {},
                'slurm_jobs': [],
                'service_mapping': {}
            }
            
            # Get tracked services
            for service_id, job_info in self.servers._running_instances.items():
                debug_info['tracked_services'][service_id] = {
                    'job_id': job_info.job_id,
                    'status': job_info.status.value if hasattr(job_info.status, 'value') else str(job_info.status),
                    'submitted_at': job_info.submitted_at,
                    'started_at': getattr(job_info, 'started_at', None),
                    'completed_at': getattr(job_info, 'completed_at', None)
                }
                
                if job_info.job_id:
                    debug_info['service_mapping'][job_info.job_id] = service_id
            
            # Get all SLURM jobs
            if self.ssh_client:
                cmd = "squeue -u $USER --format='%i,%j,%T,%M,%N,%P' --noheader"
                exit_code, stdout, stderr = self.ssh_client.execute_command(cmd)
                
                if exit_code == 0 and stdout.strip():
                    for line in stdout.strip().split('\n'):
                        if line.strip():
                            fields = line.split(',')
                            if len(fields) >= 6:
                                job_info = {
                                    'job_id': fields[0].strip(),
                                    'name': fields[1].strip(),
                                    'state': fields[2].strip(),
                                    'time': fields[3].strip(),
                                    'nodes': fields[4].strip(),
                                    'partition': fields[5].strip(),
                                    'is_tracked': fields[0].strip() in debug_info['service_mapping']
                                }
                                debug_info['slurm_jobs'].append(job_info)
            
            # Get comprehensive service list
            debug_info['all_services'] = self.servers.list_all_services()
            
            return debug_info
            
        except Exception as e:
            self.logger.error(f"Error getting debug info: {e}")
            return {'error': str(e)}
    
    def show_servers_status(self) -> dict:
        """Query all server statuses"""
        # First cleanup any completed services
        self.servers.cleanup_completed_services()
        
        servers_status = {}
        
        for service_id in self.servers.list_running_services():
            servers_status[service_id] = self.servers.check_service_status(service_id)
        
        return {
            'total_services': len(servers_status),
            'services': servers_status
        }
    
    def get_slurm_status(self) -> dict:
        """Get status directly from SLURM (all user jobs)"""
        if not self.ssh_client:
            return {'error': 'SSH not connected'}
        
        try:
            # Get running/pending jobs from squeue
            exit_code, stdout, stderr = self.ssh_client.execute_command(
                "squeue -u $USER --format='%i,%j,%T,%M,%N,%P' --noheader"
            )
            
            jobs = []
            if exit_code == 0 and stdout.strip():
                for line in stdout.strip().split('\n'):
                    if line.strip():
                        fields = line.split(',')
                        if len(fields) >= 6:
                            jobs.append({
                                'job_id': fields[0].strip(),
                                'name': fields[1].strip(),
                                'state': fields[2].strip(),
                                'time': fields[3].strip(),
                                'nodes': fields[4].strip(),
                                'partition': fields[5].strip()
                            })
            
            # Categorize jobs by name patterns
            services = []
            clients = []
            other = []
            
            for job in jobs:
                name = job['name'].lower()
                if 'service' in name or 'ollama' in name or 'server' in name:
                    services.append(job)
                elif 'client' in name or 'benchmark' in name:
                    clients.append(job)
                else:
                    other.append(job)
            
            return {
                'total_jobs': len(jobs),
                'services': {'count': len(services), 'jobs': services},
                'clients': {'count': len(clients), 'jobs': clients},
                'other': {'count': len(other), 'jobs': other},
                'all_jobs': jobs
            }
        
        except Exception as e:
            self.logger.error(f"Error getting SLURM status: {e}")
            return {'error': str(e)}
    
    def show_clients_status(self) -> dict:
        """Query all client statuses"""
        # First cleanup any completed clients
        self.clients.cleanup_completed_clients()
        
        clients_status = {}
        
        for client_id in self.clients.list_running_clients():
            clients_status[client_id] = self.clients.check_client_status(client_id)
        
        return {
            'total_clients': len(clients_status),
            'clients': clients_status
        }
    
    def show_monitors_status(self) -> dict:
        """Query active monitoring instances"""
        self.monitors.cleanup_completed_monitors()
        
        monitors_status = {}
        
        for monitor_id in self.monitors.list_running_monitors():
            monitors_status[monitor_id] = self.monitors.check_monitor_status(monitor_id)
        
        return {
            'total_monitors': len(monitors_status),
            'monitors': monitors_status
        }
    
    def show_logs_status(self) -> dict:
        """Query available logs (placeholder)"""
        # TODO: Implement when logs module is added
        return {
            'total_logs': 0,
            'logs': {},
            'note': 'Logs module not yet implemented'
        }
    
    def get_system_status(self) -> dict:
        """Get overall system status"""
        return {
            'ssh_connected': self.ssh_client is not None,
            'active_sessions': len(self._active_sessions),
            'services': self.show_servers_status(),
            'clients': self.show_clients_status(),
            'sessions': {sid: {'status': info['status'], 'services': len(info['services']), 
                              'clients': len(info['clients'])} 
                        for sid, info in self._active_sessions.items()}
        }
    
    def generate_report(self, session_id: str, output_path: str):
        """Consolidate metrics, logs, and status into a final report (placeholder)"""
        
        if session_id not in self._active_sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session_info = self._active_sessions[session_id]
        
        # Create basic report
        report = {
            'session_id': session_id,
            'status': session_info['status'],
            'started_at': session_info['started_at'],
            'services': [],
            'clients': [],
            'summary': {}
        }
        
        # Add service information
        for service_id in session_info['services']:
            service_status = self.servers.check_service_status(service_id)
            report['services'].append(service_status)
        
        # Add client information
        for client_id in session_info['clients']:
            client_status = self.clients.check_client_status(client_id)
            report['clients'].append(client_status)
        
        # Save report
        with open(output_path, 'w') as f:
            yaml.dump(report, f, default_flow_style=False)
        
        self.logger.info(f"Report generated: {output_path}")
    
    def clear_all_state(self):
        """Clear all tracked services and clients"""
        cleared_services = len(self.servers._running_instances)
        cleared_clients = len(self.clients._running_instances)
        
        self.servers._running_instances.clear()
        self.clients._running_instances.clear()
        
        self.logger.info(f"Cleared {cleared_services} services and {cleared_clients} clients from tracking")
        return cleared_services, cleared_clients
    
    def cleanup(self):
        """Cleanup resources"""
        if self.ssh_client:
            self.ssh_client.disconnect()
    
    def create_ssh_tunnel(self, service_id: str, local_port: int = 9090, 
                         remote_port: int = 9090) -> bool:
        """
        Create an SSH tunnel to access a service (typically Prometheus).
        
        Args:
            service_id: Service ID to tunnel to (e.g., prometheus service)
            local_port: Local port to bind (default: 9090)
            remote_port: Remote port to forward (default: 9090)
        
        Returns:
            True if tunnel instructions were provided successfully
        """
        if not self.ssh_client:
            self.logger.error("SSH client not available")
            return False
        
        # Get the service host
        service_host = self.servers.get_service_host(service_id)
        
        if not service_host:
            self.logger.error(f"Could not resolve host for service {service_id}")
            return False
        
        # Create the tunnel (this will print instructions for the user)
        return self.ssh_client.create_tunnel_simple(
            remote_host=service_host,
            remote_port=remote_port,
            local_port=local_port
        )
    
    def list_ssh_tunnels(self) -> list:
        """List all active SSH tunnels"""
        if not self.ssh_client:
            return []
        return self.ssh_client.list_tunnels()
    
    def close_ssh_tunnel(self, tunnel_id: str) -> bool:
        """Close a specific SSH tunnel"""
        if not self.ssh_client:
            return False
        return self.ssh_client.close_tunnel(tunnel_id)


# Maintain backward compatibility with the old class name
BenchmarkInterface = BenchmarkOrchestrator