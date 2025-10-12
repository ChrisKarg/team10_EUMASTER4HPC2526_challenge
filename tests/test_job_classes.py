#!/usr/bin/env python3
"""
Comprehensive tests for Job, Service, and Client classes.

This test suite covers:
- Job abstract base class functionality
- Service and Client concrete implementations
- Container configuration and path resolution
- SLURM script generation
- Factory pattern creation from recipes
- Real YAML recipe parsing
- Custom recipe dictionaries

Usage:
    python -m pytest tests/test_job_classes.py -v
    python tests/test_job_classes.py
"""

import pytest
import os
import sys
import yaml
from pathlib import Path
from unittest.mock import Mock, patch

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from services.base import Job, Service, Client, JobFactory
from services.ollama import OllamaService, OllamaClient


class TestJobFactory:
    """Test the JobFactory pattern for creating services and clients."""
    
    def setup_method(self):
        """Setup test configuration."""
        self.test_config = {
            'slurm': {
                'account': 'test_account',
                'partition': 'test_partition',
                'qos': 'default',
                'time': '01:00:00'
            },
            'services_dir': 'recipes/services',
            'clients_dir': 'recipes/clients'
        }
    
    def test_create_service_from_dict_recipe(self):
        """Test creating a service from a dictionary recipe."""
        service_recipe = {
            'service': {
                'name': 'ollama',
                'container_image': 'ollama.sif',
                'command': 'ollama',
                'args': ['serve'],
                'resources': {
                    'time': '00:30:00',
                    'partition': 'gpu',
                    'mem': '8GB'
                },
                'environment': {
                    'OLLAMA_HOST': '0.0.0.0:11434'
                },
                'ports': [11434],
                'container': {
                    'docker_source': 'docker://ollama/ollama:latest',
                    'image_path': '$HOME/containers/ollama.sif'
                }
            }
        }
        
        service = JobFactory.create_service(service_recipe, self.test_config)
        
        assert isinstance(service, OllamaService)
        assert service.name == 'ollama'
        assert service.container_image == 'ollama.sif'
        assert service.command == 'ollama'
        assert service.args == ['serve']
        assert service.resources['time'] == '00:30:00'
        assert service.environment['OLLAMA_HOST'] == '0.0.0.0:11434'
        assert service.ports == [11434]
        assert service.container['docker_source'] == 'docker://ollama/ollama:latest'
        assert service.container['image_path'] == '$HOME/containers/ollama.sif'
        assert service.config == self.test_config

    def test_create_client_from_dict_recipe(self):
        """Test creating a client from a dictionary recipe."""
        client_recipe = {
            'client': {
                'name': 'ollama_benchmark',
                'container_image': 'benchmark.sif',
                'duration': 600,
                'target_service': {
                    'name': 'ollama',
                    'port': 11434
                },
                'parameters': {
                    'endpoint': 'http://localhost:11434',
                    'num_requests': 100
                },
                'resources': {
                    'mem': '4GB',
                    'time': '00:15:00'
                },
                'container': {
                    'docker_source': 'docker://python:3.11-slim',
                    'image_path': '$HOME/containers/benchmark.sif'
                },
                'script': {
                    'name': 'ollama_benchmark.py',
                    'local_path': 'benchmark_scripts/',
                    'remote_path': '$HOME/benchmark_scripts/'
                }
            }
        }
        
        client = JobFactory.create_client(client_recipe, self.test_config)
        
        assert isinstance(client, OllamaClient)
        assert client.name == 'ollama_benchmark'
        assert client.duration == 600
        assert client.target_service['name'] == 'ollama'
        assert client.parameters['num_requests'] == 100
        assert client.container['docker_source'] == 'docker://python:3.11-slim'
        assert client.script_name == 'ollama_benchmark.py'
        assert client.script_local_path == 'benchmark_scripts/'

    def test_create_ollama_service_from_dict(self):
        """Test creating OllamaService from a dictionary recipe."""
        ollama_recipe = {
            'service': {
                'name': 'ollama',
                'container_image': 'ollama_latest.sif',
                'command': 'ollama',
                'args': ['serve'],
                'ports': [11434],
                'container': {
                    'docker_source': 'docker://ollama/ollama:latest',
                    'image_path': '$HOME/containers/ollama_latest.sif'
                }
            }
        }
        
        service = JobFactory.create_service(ollama_recipe, self.test_config)
        
        assert isinstance(service, OllamaService)
        assert service.name == 'ollama'
        assert service.ports == [11434]
        assert service.container['docker_source'] == 'docker://ollama/ollama:latest'

    def test_create_ollama_client_from_dict(self):
        """Test creating OllamaClient from a dictionary recipe."""
        client_recipe = {
            'client': {
                'name': 'ollama_benchmark',
                'target_service': {'name': 'ollama'},
                'container': {
                    'docker_source': 'docker://python:3.11-slim',
                    'image_path': '$HOME/containers/benchmark_client.sif'
                }
            }
        }
        
        client = JobFactory.create_client(client_recipe, self.test_config)
        
        assert isinstance(client, OllamaClient)
        assert client.get_target_service_name() == 'ollama'


class TestServiceClass:
    """Test Service class functionality."""
    
    def setup_method(self):
        """Setup test configuration and service instance."""
        self.test_config = {
            'slurm': {
                'account': 'test_account',
                'partition': 'gpu'
            }
        }
        
        service_recipe = {
            'service': {
                'name': 'ollama',
                'container_image': 'ollama.sif',
                'resources': {'mem': '8GB', 'gres': 'gpu:1'},
                'environment': {'OLLAMA_HOST': '0.0.0.0:11434'},
                'ports': [11434],
                'container': {
                    'docker_source': 'docker://ollama/ollama:latest',
                    'image_path': '$HOME/containers/ollama.sif'
                }
            }
        }
        
        self.service = JobFactory.create_service(service_recipe, self.test_config)

    def test_service_initialization(self):
        """Test service initialization and post_init."""
        assert self.service.name == 'ollama'
        assert self.service.ports == [11434]
        assert self.service.container['docker_source'] == 'docker://ollama/ollama:latest'
        assert isinstance(self.service.container, dict)

    def test_resolve_container_path(self):
        """Test container path resolution."""
        # Test with image_path in container config
        assert self.service._resolve_container_path() == '$HOME/containers/ollama.sif'
        
        # Test without image_path (fallback)
        fallback_recipe = {
            'service': {
                'name': 'ollama',
                'container_image': 'ollama.sif',
                'container': {}
            }
        }
        fallback_config = {'containers': {'base_path': '/mnt/containers'}, 'slurm': {'account': 'test'}}
        service_no_path = JobFactory.create_service(fallback_recipe, fallback_config)
        assert service_no_path._resolve_container_path() == '/mnt/containers/ollama.sif'

    def test_get_docker_source(self):
        """Test Docker source resolution."""
        assert self.service._get_docker_source() == 'docker://ollama/ollama:latest'
        
        # Test fallback to global config
        fallback_service_recipe = {
            'service': {
                'name': 'ollama',
                'container_image': 'ollama.sif',
                'container': {}
            }
        }
        fallback_config = {
            'containers': {
                'docker_sources': {'ollama': 'docker://global/ollama:latest'}
            }
        }
        service_no_source = JobFactory.create_service(fallback_service_recipe, fallback_config)
        assert service_no_source._get_docker_source() == 'docker://global/ollama:latest'

    def test_container_build_commands(self):
        """Test container build commands generation."""
        commands = self.service._generate_container_build_commands()
        
        assert any('mkdir -p' in cmd for cmd in commands)
        assert any('docker://ollama/ollama:latest' in cmd for cmd in commands)
        assert any('apptainer build' in cmd for cmd in commands)
        assert any('$HOME/containers/ollama.sif' in cmd for cmd in commands)

    def test_get_container_command(self):
        """Test container command generation."""
        cmd = self.service.get_container_command()
        
        assert 'apptainer exec' in cmd
        assert '--nv' in cmd  # GPU support
        assert '--env OLLAMA_HOST=0.0.0.0:11434' in cmd
        assert '$HOME/containers/ollama.sif' in cmd
        assert '&' in cmd  # Background execution

    def test_slurm_script_generation(self):
        """Test SLURM script generation."""
        script = self.service.generate_slurm_script('test_job_123')
        
        assert '#!/bin/bash' in script
        assert '#SBATCH --job-name=ollama_test_job_123' in script
        assert '#SBATCH --mem=8GB' in script
        assert '#SBATCH --gres=gpu:1' in script
        assert 'apptainer build' in script
        assert 'apptainer exec' in script


class TestClientClass:
    """Test Client class functionality."""
    
    def setup_method(self):
        """Setup test configuration and client instance."""
        self.test_config = {
            'slurm': {
                'account': 'test_account'
            }
        }
        
        client_recipe = {
            'client': {
                'name': 'ollama_benchmark',
                'container_image': 'benchmark.sif',
                'target_service': {'name': 'ollama', 'port': 11434},
                'duration': 300,
                # 'parameters': {'endpoint': 'http://localhost:11434'},
                'container': {
                    'docker_source': 'docker://python:3.11-slim',
                    'image_path': '$HOME/containers/benchmark.sif'
                },
                'script': {
                    'name': 'ollama_benchmark.py',
                    'local_path': 'benchmark_scripts/',
                    'remote_path': '$HOME/benchmark_scripts/'
                }
            }
        }
        
        self.client = JobFactory.create_client(client_recipe, self.test_config)

    def test_client_initialization(self):
        """Test client initialization."""
        assert self.client.name == 'ollama_benchmark'
        assert self.client.duration == 300
        assert self.client.get_target_service_name() == 'ollama'
        assert self.client.script_name == 'ollama_benchmark.py'

    def test_target_service_methods(self):
        """Test target service access methods."""
        assert self.client.get_target_service_name() == 'ollama'
        assert self.client.target_service['name'] == 'ollama'
        assert self.client.target_service['port'] == 11434

    def test_resolve_service_endpoint(self):
        """Test service endpoint resolution."""
        endpoint = self.client.resolve_service_endpoint('test-host', 11434, 'http')
        assert endpoint == 'http://test-host:11434'
        
        # Test with default TARGET_SERVICE_HOST variable
        endpoint_default = self.client.resolve_service_endpoint()
        assert endpoint_default == 'http://${TARGET_SERVICE_HOST}:11434'

    def test_client_container_build_commands(self):
        """Test client container build commands."""
        commands = self.client._generate_container_build_commands()
        assert any('Client container management' in cmd for cmd in commands)
        assert any('docker://python:3.11-slim' in cmd for cmd in commands)
        assert any('$HOME/containers/benchmark.sif' in cmd for cmd in commands)

    def test_client_script_generation(self):
        """Test client SLURM script generation."""
        script = self.client.generate_slurm_script('client_123', 'target-host')
        
        assert '#!/bin/bash' in script
        assert 'TARGET_SERVICE_HOST=target-host' in script
        assert 'Client container management' in script
        assert 'apptainer build' in script
        assert 'apptainer exec' in script


class TestRealYAMLRecipes:
    """Test with real YAML recipe files."""
    
    def setup_method(self):
        """Setup paths and config."""
        self.base_path = Path(__file__).parent.parent
        self.test_config = {
            'slurm': {
                'account': 'test_account',
                'partition': 'gpu'
            }
        }

    def test_load_ollama_service_yaml(self):
        """Test loading and creating service from real ollama.yaml."""
        ollama_yaml_path = self.base_path / 'recipes' / 'services' / 'ollama.yaml'
        
        if ollama_yaml_path.exists():
            with open(ollama_yaml_path, 'r') as f:
                recipe = yaml.safe_load(f)
            
            service = JobFactory.create_service(recipe, self.test_config)
            
            assert isinstance(service, OllamaService)
            assert service.name == 'ollama'
            assert service.command == 'ollama'
            assert service.args == ['serve']
            assert 11434 in service.ports
            assert 'docker_source' in service.container
            assert 'image_path' in service.container

    def test_load_ollama_client_yaml(self):
        """Test loading and creating client from real ollama_benchmark.yaml."""
        client_yaml_path = self.base_path / 'recipes' / 'clients' / 'ollama_benchmark.yaml'
        
        if client_yaml_path.exists():
            with open(client_yaml_path, 'r') as f:
                recipe = yaml.safe_load(f)
            
            client = JobFactory.create_client(recipe, self.test_config)
            
            assert isinstance(client, OllamaClient)
            assert client.name == 'ollama_benchmark'
            assert client.get_target_service_name() == 'ollama'
            assert 'docker_source' in client.container
            assert 'image_path' in client.container

    def test_yaml_container_configuration(self):
        """Test that YAML recipes have proper container configuration."""
        recipes_to_test = [
            ('recipes/services/ollama.yaml', 'service'),
            ('recipes/clients/ollama_benchmark.yaml', 'client')
        ]
        
        for recipe_path, recipe_type in recipes_to_test:
            full_path = self.base_path / recipe_path
            if full_path.exists():
                with open(full_path, 'r') as f:
                    recipe = yaml.safe_load(f)
                
                config = recipe.get(recipe_type, {})
                container_config = config.get('container', {})
                
                # Verify required container fields
                assert 'docker_source' in container_config, f"Missing docker_source in {recipe_path}"
                assert 'image_path' in container_config, f"Missing image_path in {recipe_path}"
                assert container_config['docker_source'].startswith('docker://'), f"Invalid docker_source format in {recipe_path}"
                assert '$HOME/containers' in container_config['image_path'], f"image_path should use $HOME/containers in {recipe_path}"


class TestJobAbstractClass:
    """Test Job abstract base class functionality."""
    
    def test_job_is_abstract(self):
        """Test that Job cannot be instantiated directly."""
        with pytest.raises(TypeError):
            Job(name='test', container_image='test.sif')

    def test_slurm_header_generation(self):
        """Test SLURM header generation."""
        service_recipe = {
            'service': {
                'name': 'ollama',
                'container_image': 'ollama.sif',
                'resources': {
                    'time': '01:00:00',
                    'partition': 'gpu',
                    'mem': '8GB',
                    'nodes': 2,
                    'gres': 'gpu:1'
                }
            }
        }
        
        service = JobFactory.create_service(service_recipe, {'slurm': {'account': 'test_account'}})
        
        script = service.generate_slurm_script('job_123')
        
        assert '#SBATCH --job-name=ollama_job_123' in script
        assert '#SBATCH --account=test_account' in script
        assert '#SBATCH --time=01:00:00' in script
        assert '#SBATCH --partition=gpu' in script
        assert '#SBATCH --mem=8GB' in script
        assert '#SBATCH --nodes=2' in script
        assert '#SBATCH --gres=gpu:1' in script

    def test_environment_variable_handling(self):
        """Test environment variable processing."""
        client_recipe = {
            'client': {
                'name': 'ollama_benchmark',
                'container_image': 'benchmark.sif',
                'target_service': {'name': 'ollama'},
                'environment': {
                    'TEST_VAR1': 'value1',
                    'TEST_VAR2': 'value2'
                }
            }
        }
        
        client = JobFactory.create_client(client_recipe, {})
        
        cmd = client.get_container_command()
        assert '--env TEST_VAR1=value1' in cmd
        assert '--env TEST_VAR2=value2' in cmd


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_container_config(self):
        """Test handling of empty container configuration."""
        service_recipe = {
            'service': {
                'name': 'ollama',
                'container_image': 'ollama.sif',
                'container': {}
            }
        }
        
        service = JobFactory.create_service(service_recipe, {})
        
        # Should not crash and should have sensible defaults
        assert service._get_docker_source() is None
        path = service._resolve_container_path()
        assert path == 'ollama.sif'  # Fallback to container_image

    def test_missing_target_service(self):
        """Test client with missing target service."""
        client_recipe = {
            'client': {
                'name': 'ollama_benchmark',
                'container_image': 'benchmark.sif',
                'target_service': {}  # Empty target service
            }
        }
        
        with pytest.raises(ValueError):
            JobFactory.create_client(client_recipe, {})

    def test_invalid_recipe_structure(self):
        """Test handling of invalid recipe structures."""
        with pytest.raises((ValueError, KeyError)):
            JobFactory.create_service({}, {})  # Empty recipe

    def test_resource_merging(self):
        """Test that job resources are properly merged with SLURM defaults."""
        config = {
            'slurm': {
                'account': 'default_account',
                'time': '01:00:00',
                'partition': 'default'
            }
        }
        
        service_recipe = {
            'service': {
                'name': 'ollama',
                'container_image': 'ollama.sif',
                'resources': {
                    'time': '02:00:00',  # Override default
                    'mem': '16GB'       # Additional resource
                }
            }
        }
        
        service = JobFactory.create_service(service_recipe, config)

        script = service.generate_slurm_script('test_job')
        assert '#SBATCH --time=02:00:00' in script  # Overridden
        assert '#SBATCH --mem=16GB' in script      # Additional
        assert '#SBATCH --account=default_account' in script  # From config


def run_tests():
    """Run all tests if script is executed directly."""
    import subprocess
    import sys
    
    try:
        # Try to run with pytest
        result = subprocess.run([sys.executable, '-m', 'pytest', __file__, '-v'], 
                              capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return result.returncode
    except FileNotFoundError:
        # Fallback: run tests manually
        print("pytest not available, running tests manually...")
        
        test_classes = [
            TestJobFactory,
            TestServiceClass, 
            TestClientClass,
            TestRealYAMLRecipes,
            TestJobAbstractClass,
            TestEdgeCases
        ]
        
        total_tests = 0
        passed_tests = 0
        
        for test_class in test_classes:
            print(f"\n=== {test_class.__name__} ===")
            instance = test_class()
            
            # Get all test methods
            test_methods = [method for method in dir(instance) 
                          if method.startswith('test_') and callable(getattr(instance, method))]
            
            for test_method in test_methods:
                total_tests += 1
                try:
                    if hasattr(instance, 'setup_method'):
                        instance.setup_method()
                    
                    getattr(instance, test_method)()
                    print(f"✅ {test_method}")
                    passed_tests += 1
                except Exception as e:
                    print(f"❌ {test_method}: {e}")
        
        print(f"\n=== Results ===")
        print(f"Total tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        
        return 0 if passed_tests == total_tests else 1


if __name__ == '__main__':
    exit(run_tests())