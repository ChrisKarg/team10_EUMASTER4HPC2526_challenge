"""
This package provides the core job abstraction layer and factory for creating 
service and client instances in the HPC orchestration system.

The package follows an object-oriented design where jobs are self-contained entities
responsible for their own SLURM script generation, eliminating the need for external
script generators and avoiding isinstance() checks.

Key Design Principles:
- Self-contained objects: Each job generates its own SLURM scripts
- Template method pattern: Base class provides script structure, subclasses fill details
- Polymorphic behavior: Method overriding instead of type checking
- Factory registration: Automatic registration when concrete classes are imported

Notice: to add a new service or client, create a new class in this package inheriting
from Service or Client, and implement the required abstract methods.
You must also ensure the new class is imported here to trigger registration. Add it to
the __all__ list below and use methods register_service or register_client of JobFactory in that module.

Usage Example:
--------------
    from services import JobFactory
    
    # Create service from recipe
    service_recipe = {'service': {'name': 'ollama', ...}}
    service = JobFactory.create_service(service_recipe, config)
    
    # Generate SLURM script
    script = service.generate_slurm_script('service_id')
    
    # Create client from recipe  
    client_recipe = {'client': {'target_service': {'name': 'ollama'}, ...}}
    client = JobFactory.create_client(client_recipe, config)
    
    script = client.generate_slurm_script('client_id', 'target_host')
"""

# Import base classes
from .base import Job, Service, Client, JobFactory

# Import specific implementations (this triggers registration)
from .ollama import OllamaService, OllamaClient

# Make key classes available at package level
__all__ = [
    'Job',
    'Service', 
    'Client',
    'JobFactory',
    'OllamaService',
    'OllamaClient'
]

# Verify registrations happened
import logging
logger = logging.getLogger(__name__)
logger.debug(f"Available services: {JobFactory.list_available_services()}")
logger.debug(f"Available clients: {JobFactory.list_available_clients()}")