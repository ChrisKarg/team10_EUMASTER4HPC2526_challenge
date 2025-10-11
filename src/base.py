"""
Base classes for the HPC Orchestrator
"""

import abc
import uuid
import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

class ServiceStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class JobInfo:
    """Information about a SLURM job"""
    job_id: str
    service_id: str
    status: ServiceStatus
    submitted_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    nodes: Optional[List[str]] = None
    logs_path: Optional[str] = None

class BaseModule(abc.ABC):
    """Base class for all orchestrator modules"""
    
    def __init__(self, config: Dict[str, Any], ssh_client=None):
        self.config = config
        self.ssh_client = ssh_client
        self.logger = logging.getLogger(self.__class__.__name__)
        self._running_instances: Dict[str, JobInfo] = {}
    
    def generate_id(self) -> str:
        """Generate a unique ID for services/clients"""
        return str(uuid.uuid4())[:8]
    
    def get_current_time(self) -> float:
        """Get current timestamp"""
        return time.time()
    
    @abc.abstractmethod
    def list_available_services(self) -> List[str]:
        """List all available service types"""
        pass
    
    @abc.abstractmethod
    def list_running_services(self) -> List[str]:
        """List currently running service IDs"""
        pass