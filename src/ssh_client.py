"""
SSH Client for remote HPC operations
"""

import paramiko
import scp
import logging
import os
import time
import tempfile
from typing import Optional, Tuple, Dict, Any
from pathlib import Path

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
        """Close SSH connection"""
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