"""
Ollama Service and Client implementations
"""

import logging
from typing import Dict, Any, List, Optional
from .base import Service, Client, JobFactory


class OllamaService(Service):
    """Ollama LLM inference service implementation - simplified with defaults"""
    
    @classmethod
    def from_recipe(cls, recipe: Dict[str, Any], config: Dict[str, Any]) -> 'OllamaService':
        """Create OllamaService from recipe dictionary"""
        service_def = recipe.get('service', {})
        
        return cls(
            name=service_def.get('name', 'ollama'),
            container_image=service_def.get('container_image', 'ollama_latest.sif'),
            resources=service_def.get('resources', {}),
            environment=service_def.get('environment', {}),
            config=config,
            ports=service_def.get('ports', [11434]),
            command=service_def.get('command', 'ollama'),
            args=service_def.get('args', ['serve']),
            container=service_def.get('container', {}),
            enable_cadvisor=service_def.get('enable_cadvisor', False),
            cadvisor_port=service_def.get('cadvisor_port', 8080)
        )
    
    # All other methods use the default implementations from Service base class
    # No need to override unless specific behavior is required


class OllamaClient(Client):
    """Ollama benchmark client implementation - simplified with defaults"""
    
    @classmethod
    def from_recipe(cls, recipe: Dict[str, Any], config: Dict[str, Any]) -> 'OllamaClient':
        """Create OllamaClient from recipe dictionary"""
        client_def = recipe.get('client', {})
        
        # Parse script configuration
        script_config = client_def.get('script', {})
        script_name = script_config.get('name')
        script_local_path = script_config.get('local_path')
        script_remote_path = script_config.get('remote_path')
        
        return cls(
            name=client_def.get('name', 'ollama_benchmark'),
            container_image=client_def.get('container_image', 'benchmark_client.sif'),
            resources=client_def.get('resources', {}),
            environment=client_def.get('environment', {}),
            config=config,
            command=client_def.get('command'),
            args=client_def.get('args', []),
            target_service=client_def.get('target_service', {}),
            duration=client_def.get('duration', 300),
            parameters=client_def.get('parameters', {}),
            script_name=script_name,
            script_local_path=script_local_path,
            script_remote_path=script_remote_path,
            container=client_def.get('container', {})
        )
    
    def resolve_service_endpoint(self, target_service_host: str = None, 
                               default_port: int = 11434, protocol: str = "http") -> str:
        """Resolve Ollama service endpoint - override for Ollama-specific defaults"""
        # Check if endpoint is explicitly set in parameters
        endpoint_from_params = self.parameters.get('endpoint')
        if endpoint_from_params:
            return endpoint_from_params
        
        # Use TARGET_SERVICE_HOST environment variable
        host = target_service_host or "${TARGET_SERVICE_HOST}"
        
        # Get port from target service config or use Ollama default (11434)
        if self.target_service and isinstance(self.target_service, dict):
            port = self.target_service.get('port', 11434)
        else:
            port = 11434
        
        # Return Ollama-specific endpoint
        return f"{protocol}://{host}:{port}"
    
    # All other methods use the default implementations from Client base class
    # The script management is now simplified and predictable


# Register the Ollama implementations with the factory
JobFactory.register_service('ollama', OllamaService)
JobFactory.register_client('ollama', OllamaClient)