"""
SSH Client for remote HPC operations
"""

import paramiko
import scp
import logging
import os
import time
import tempfile
import threading
from typing import Optional, Tuple, Dict, Any, List
from pathlib import Path
import subprocess
import shlex

class SSHClient:
    """SSH client for remote HPC operations"""
    
    def __init__(self, hostname: str, username: str, password: Optional[str] = None, 
                 key_filename: Optional[str] = None, port: int = 22):
        self.hostname = hostname
        self.username = username
        self.password = password
        self.key_filename = str(Path(key_filename).expanduser())

        self.port = port
        self.client = None
        self.logger = logging.getLogger(__name__)
        
        # Track active SSH tunnels
        self._tunnels: Dict[str, Dict[str, Any]] = {}
        self._tunnel_lock = threading.Lock()
    
    def connect(self) -> bool:
        """Establish SSH connection"""
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            if self.key_filename:
                self.client.connect(
                    hostname=self.hostname,
                    username=self.username,
                    key_filename=self.key_filename,
                    port=self.port
                )
            else:
                self.client.connect(
                    hostname=self.hostname,
                    username=self.username,
                    password=self.password,
                    port=self.port
                )
            
            self.logger.info(f"Connected to {self.hostname}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to {self.hostname}: {e}")
            return False
    
    def disconnect(self):
        """Close SSH connection and all active tunnels"""
        # Close all tunnels first
        self.close_all_tunnels()
        
        if self.client:
            self.client.close()
            self.logger.info(f"Disconnected from {self.hostname}")
    
    def execute_command(self, command: str) -> Tuple[int, str, str]:
        """Execute command on remote host"""
        if not self.client:
            raise ConnectionError("Not connected to remote host")
        
        try:
            stdin, stdout, stderr = self.client.exec_command(command)
            exit_code = stdout.channel.recv_exit_status()
            stdout_str = stdout.read().decode('utf-8')
            stderr_str = stderr.read().decode('utf-8')
            
            self.logger.debug(f"Command: {command}")
            self.logger.debug(f"Exit code: {exit_code}")
            
            return exit_code, stdout_str, stderr_str
            
        except Exception as e:
            self.logger.error(f"Failed to execute command '{command}': {e}")
            raise
    
    def upload_file(self, local_path: str, remote_path: str) -> bool:
        """Upload file to remote host"""
        if not self.client:
            raise ConnectionError("Not connected to remote host")
        
        try:
            # Check if local file exists
            if not os.path.exists(local_path):
                self.logger.error(f"Local file does not exist: {local_path}")
                return False
            
            # Get file size for logging
            file_size = os.path.getsize(local_path)
            self.logger.info(f"Uploading {local_path} ({file_size} bytes) to {remote_path}")
            
            scp_client = scp.SCPClient(self.client.get_transport())
            scp_client.put(local_path, remote_path)
            scp_client.close()
            
            self.logger.info(f"Successfully uploaded {local_path} to {remote_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to upload {local_path} to {remote_path}: {e}")
            return False
    
    def ensure_benchmark_script(self, script_name: str = "ollama_benchmark.py") -> bool:
        """Ensure benchmark script is available on remote host"""
        local_script = f"benchmark_scripts/{script_name}"
        remote_script = f"benchmark_scripts/{script_name}"
        
        try:
            # Create remote benchmark_scripts directory
            self.execute_command("mkdir -p benchmark_scripts")
            
            # Check if script exists locally
            if not os.path.exists(local_script):
                self.logger.error(f"Local benchmark script not found: {local_script}")
                return False
            
            # Upload the script
            if self.upload_file(local_script, remote_script):
                # Make it executable
                self.execute_command(f"chmod +x {remote_script}")
                self.logger.info(f"Benchmark script {script_name} is now available on remote host")
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to ensure benchmark script availability: {e}")
            return False
    
    def download_file(self, remote_path: str, local_path: str) -> bool:
        """Download file from remote host"""
        if not self.client:
            raise ConnectionError("Not connected to remote host")
        
        try:
            scp_client = scp.SCPClient(self.client.get_transport())
            scp_client.get(remote_path, local_path)
            scp_client.close()
            
            self.logger.info(f"Downloaded {remote_path} to {local_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to download {remote_path} to {local_path}: {e}")
            return False
    
    def submit_slurm_job(self, script_content: str, script_name: str = None) -> Optional[str]:
        """Submit SLURM job and return job ID"""
        if not script_name:
            script_name = f"job_{int(time.time())}.sh"
        
        remote_script_path = f"/tmp/{script_name}"

        try:
            # Create temporary local file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
                f.write(script_content)
                temp_path = f.name
            
            # Upload script
            if not self.upload_file(temp_path, remote_script_path):
                return None
            
            # Make script executable
            exit_code, _, _ = self.execute_command(f"chmod +x {remote_script_path}")
            if exit_code != 0:
                self.logger.error("Failed to make script executable")
                return None
            
            # Submit job
            exit_code, stdout, stderr = self.execute_command(f"sbatch {remote_script_path}")
            
            # Clean up
            os.unlink(temp_path)
            self.execute_command(f"rm {remote_script_path}")
            
            if exit_code == 0:
                # Extract job ID from sbatch output
                # Format: "Submitted batch job 12345"
                for line in stdout.strip().split('\n'):
                    if 'Submitted batch job' in line:
                        job_id = line.split()[-1]
                        self.logger.info(f"Submitted SLURM job: {job_id}")
                        return job_id
            else:
                self.logger.error(f"Failed to submit job: {stderr}")
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error submitting SLURM job: {e}")
            return None
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get SLURM job status"""
        try:
            # Use squeue to get job status
            exit_code, stdout, stderr = self.execute_command(
                f"squeue -j {job_id} --format='%i,%T,%M,%N' --noheader"
            )
            
            if exit_code == 0 and stdout.strip():
                fields = stdout.strip().split(',')
                if len(fields) >= 4:
                    return {
                        'job_id': fields[0].strip(),
                        'state': fields[1].strip(),
                        'time': fields[2].strip(),
                        'nodes': fields[3].strip()
                    }
            
            # If job not in queue, check sacct for completed jobs
            exit_code, stdout, stderr = self.execute_command(
                f"sacct -j {job_id} --format='JobID,State,ExitCode,NodeList' --noheader --parsable2"
            )
            
            if exit_code == 0 and stdout.strip():
                for line in stdout.strip().split('\n'):
                    if line.startswith(job_id + '|'):
                        fields = line.split('|')
                        if len(fields) >= 4:
                            return {
                                'job_id': fields[0],
                                'state': fields[1],
                                'exit_code': fields[2],
                                'nodes': fields[3]
                            }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting job status for {job_id}: {e}")
            return None
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel SLURM job"""
        try:
            exit_code, stdout, stderr = self.execute_command(f"scancel {job_id}")
            if exit_code == 0:
                self.logger.info(f"Cancelled job {job_id}")
                return True
            else:
                self.logger.error(f"Failed to cancel job {job_id}: {stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error cancelling job {job_id}: {e}")
            return False
    
    def create_tunnel(self, remote_host: str, remote_port: int, 
                     local_port: int = None, tunnel_id: str = None) -> Optional[Dict[str, Any]]:
        """
        Create an SSH tunnel for port forwarding.
        
        Args:
            remote_host: The remote host to tunnel to (e.g., compute node hostname)
            remote_port: The remote port to forward (e.g., 9090 for Prometheus)
            local_port: Local port to bind to (default: same as remote_port)
            tunnel_id: Optional identifier for the tunnel
        
        Returns:
            Dictionary with tunnel information or None on failure
        """
        if not self.client:
            raise ConnectionError("Not connected to remote host")
        
        if local_port is None:
            local_port = remote_port
        
        if tunnel_id is None:
            tunnel_id = f"{remote_host}_{remote_port}"
        
        try:
            with self._tunnel_lock:
                # Check if tunnel already exists
                if tunnel_id in self._tunnels:
                    self.logger.warning(f"Tunnel {tunnel_id} already exists")
                    return self._tunnels[tunnel_id]
                
                # Create transport for the tunnel
                transport = self.client.get_transport()
                
                # Start local port forwarding
                # This creates a tunnel: localhost:local_port -> remote_host:remote_port
                self.logger.info(f"Creating SSH tunnel: localhost:{local_port} -> {remote_host}:{remote_port}")
                
                # Use paramiko's port forwarding
                # Note: We need to run this in a separate thread to keep the tunnel alive
                def tunnel_handler():
                    try:
                        # Open direct TCP/IP channel through SSH
                        local_server = transport.open_channel(
                            "direct-tcpip",
                            (remote_host, remote_port),
                            ("localhost", local_port)
                        )
                        
                        while True:
                            time.sleep(1)
                            if not transport.is_active():
                                self.logger.warning(f"Tunnel {tunnel_id} transport closed")
                                break
                    except Exception as e:
                        self.logger.error(f"Tunnel handler error for {tunnel_id}: {e}")
                
                # Store tunnel information
                tunnel_info = {
                    'tunnel_id': tunnel_id,
                    'remote_host': remote_host,
                    'remote_port': remote_port,
                    'local_port': local_port,
                    'transport': transport,
                    'created_at': time.time(),
                    'status': 'active'
                }
                
                self._tunnels[tunnel_id] = tunnel_info
                
                self.logger.info(f"SSH tunnel created: {tunnel_id}")
                self.logger.info(f"  Access via: http://localhost:{local_port}")
                
                return tunnel_info
                
        except Exception as e:
            self.logger.error(f"Failed to create SSH tunnel: {e}")
            return None
    
    def create_tunnel_simple(self, remote_host: str, remote_port: int = 9090, 
                           local_port: int = 9090) -> bool:
        """
        Create a simple SSH tunnel using SSH command (more reliable for long-running tunnels).
        This method uses subprocess to run ssh command with port forwarding.
        
        Args:
            remote_host: The remote host to tunnel to
            remote_port: The remote port to forward (default: 9090)
            local_port: Local port to bind to (default: 9090)
        
        Returns:
            True if tunnel creation command succeeded
        
        Note:
            This will print instructions for the user to run the SSH command manually
            as keeping tunnels alive programmatically can be complex.
        """
        # Generate SSH tunnel command
        ssh_key = f"-i {self.key_filename}" if self.key_filename else ""
        # Build argument list for subprocess (safer than passing a single shell string)
        args = ["ssh"]
        if self.key_filename:
            args += ["-i", self.key_filename]
        args += [
            "-L", f"{local_port}:{remote_host}:{remote_port}",
            "-N", "-f",
            f"{self.username}@{self.hostname}",
            "-p", str(self.port),
            "-o", "ExitOnForwardFailure=yes",
            "-o", "ServerAliveInterval=60",
            "-o", "ServerAliveCountMax=3",
        ]

        # Human-readable command for logging/printing
        tunnel_cmd = " ".join(shlex.quote(a) for a in args)

        try:
            self.logger.info(f"Running SSH tunnel command: {tunnel_cmd}")
            # Run the ssh command (will background because of -f)
            subprocess.run(args, check=True)
            self.logger.info("SSH tunnel started successfully")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"SSH tunnel command failed: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Failed to start SSH tunnel: {e}")
            return False
        
        # self.logger.info(f"=" * 70)
        # self.logger.info("SSH TUNNEL SETUP")
        # self.logger.info(f"=" * 70)
        # self.logger.info(f"To access {remote_host}:{remote_port} at localhost:{local_port},")
        # self.logger.info("run the following command in a separate terminal:")
        # self.logger.info("")
        # self.logger.info(f"  {tunnel_cmd}")
        # self.logger.info("")
        # self.logger.info(f"Then access the service at: http://localhost:{local_port}")
        # self.logger.info(f"=" * 70)

        print(f"Command used to create the SSH tunnel:")
        print(f"  {tunnel_cmd}")
        print(f"You can access the service at: http://localhost:{local_port}")

        return True
    
    def close_tunnel(self, tunnel_id: str) -> bool:
        """
        Close an SSH tunnel.
        
        Args:
            tunnel_id: Identifier of the tunnel to close
        
        Returns:
            True if tunnel was closed successfully
        """
        with self._tunnel_lock:
            if tunnel_id not in self._tunnels:
                self.logger.warning(f"Tunnel {tunnel_id} not found")
                return False
            
            try:
                tunnel_info = self._tunnels[tunnel_id]
                transport = tunnel_info.get('transport')
                
                if transport:
                    transport.close()
                
                tunnel_info['status'] = 'closed'
                del self._tunnels[tunnel_id]
                
                self.logger.info(f"Tunnel {tunnel_id} closed")
                return True
                
            except Exception as e:
                self.logger.error(f"Error closing tunnel {tunnel_id}: {e}")
                return False
    
    def list_tunnels(self) -> List[Dict[str, Any]]:
        """List all active SSH tunnels"""
        with self._tunnel_lock:
            return [
                {
                    'tunnel_id': info['tunnel_id'],
                    'remote_host': info['remote_host'],
                    'remote_port': info['remote_port'],
                    'local_port': info['local_port'],
                    'status': info['status'],
                    'created_at': info['created_at']
                }
                for info in self._tunnels.values()
            ]
    
    def close_all_tunnels(self):
        """Close all active SSH tunnels"""
        with self._tunnel_lock:
            tunnel_ids = list(self._tunnels.keys())
        
        for tunnel_id in tunnel_ids:
            self.close_tunnel(tunnel_id)