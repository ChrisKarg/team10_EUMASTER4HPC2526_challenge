#!/usr/bin/env python3
"""
Simple test runner for Job, Service, and Client classes.
Can run without pytest - uses built-in unittest and manual test execution.
"""

import unittest
import os
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from services.base import Job, Service, Client, JobFactory
    from services.ollama import OllamaService, OllamaClient
    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import modules: {e}")
    IMPORTS_AVAILABLE = False


class TestJobClasses(unittest.TestCase):
    """Test Job, Service, and Client classes."""
    
    def setUp(self):
        """Setup test configuration."""
        if not IMPORTS_AVAILABLE:
            self.skipTest("Required modules not available")
            
        self.test_config = {
            'slurm': {
                'account': 'test_account',
                'partition': 'gpu',
                'qos': 'default',
                'time': '01:00:00'
            },
            'services_dir': 'recipes/services',
            'clients_dir': 'recipes/clients'
        }

    def test_service_creation_from_dict(self):
        """Test creating a service from dictionary recipe."""
        service_recipe = {
            'service': {
                'name': 'ollama',
                'container_image': 'ollama.sif',
                'command': 'ollama',
                'args': ['serve'],
                'resources': {
                    'time': '00:30:00',
                    'partition': 'gpu',
                    'mem': '8GB',
                    'gres': 'gpu:1'
                },
                'environment': {
                    'OLLAMA_HOST': '0.0.0.0:11434',
                    'OLLAMA_TLS_SKIP_VERIFY': '1'
                },
                'ports': [11434],
                'container': {
                    'docker_source': 'docker://ollama/ollama:latest',
                    'image_path': '$HOME/containers/ollama.sif'
                }
            }
        }
        
        service = JobFactory.create_service(service_recipe, self.test_config)
        
        # Test basic properties
        self.assertIsInstance(service, OllamaService)
        self.assertEqual(service.name, 'ollama')
        self.assertEqual(service.container_image, 'ollama.sif')
        self.assertEqual(service.command, 'ollama')
        self.assertEqual(service.args, ['serve'])
        
        # Test resources
        self.assertEqual(service.resources['time'], '00:30:00')
        self.assertEqual(service.resources['mem'], '8GB')
        self.assertEqual(service.resources['gres'], 'gpu:1')
        
        # Test environment
        self.assertEqual(service.environment['OLLAMA_HOST'], '0.0.0.0:11434')
        
        # Test ports
        self.assertEqual(service.ports, [11434])
        
        # Test container configuration
        self.assertEqual(service.container['docker_source'], 'docker://ollama/ollama:latest')
        self.assertEqual(service.container['image_path'], '$HOME/containers/ollama.sif')
        
        # Test config
        self.assertEqual(service.config, self.test_config)

    def test_client_creation_from_dict(self):
        """Test creating a client from dictionary recipe."""
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
                    'num_requests': 100,
                    'model': 'llama2'
                },
                'resources': {
                    'mem': '4GB',
                    'time': '00:15:00',
                    'partition': 'gpu'
                },
                'environment': {
                    'OLLAMA_TLS_SKIP_VERIFY': '1'
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
        
        # Test basic properties
        self.assertIsInstance(client, OllamaClient)
        self.assertEqual(client.name, 'ollama_benchmark')
        self.assertEqual(client.duration, 600)
        
        # Test target service
        self.assertEqual(client.target_service['name'], 'ollama')
        self.assertEqual(client.target_service['port'], 11434)
        self.assertEqual(client.get_target_service_name(), 'ollama')
        
        # Test parameters
        self.assertEqual(client.parameters['num_requests'], 100)
        
        # Test container configuration
        self.assertEqual(client.container['docker_source'], 'docker://python:3.11-slim')
        self.assertEqual(client.container['image_path'], '$HOME/containers/benchmark.sif')
        
        # Test script configuration
        self.assertEqual(client.script_name, 'ollama_benchmark.py')
        self.assertEqual(client.script_local_path, 'benchmark_scripts/')
        self.assertEqual(client.script_remote_path, '$HOME/benchmark_scripts/')

    def test_ollama_service_creation(self):
        """Test creating OllamaService."""
        ollama_recipe = {
            'service': {
                'name': 'ollama',
                'container_image': 'ollama_latest.sif',
                'command': 'ollama',
                'args': ['serve'],
                'ports': [11434],
                'environment': {
                    'OLLAMA_HOST': '0.0.0.0:11434',
                    'OLLAMA_TLS_SKIP_VERIFY': '1'
                },
                'resources': {
                    'gres': 'gpu:1',
                    'mem': '16GB'
                },
                'container': {
                    'docker_source': 'docker://ollama/ollama:latest',
                    'image_path': '$HOME/containers/ollama_latest.sif'
                }
            }
        }
        
        service = JobFactory.create_service(ollama_recipe, self.test_config)
        
        self.assertIsInstance(service, OllamaService)
        self.assertEqual(service.name, 'ollama')
        self.assertEqual(service.command, 'ollama')
        self.assertEqual(service.args, ['serve'])
        self.assertEqual(service.ports, [11434])
        self.assertIn('docker_source', service.container)

    def test_ollama_client_creation(self):
        """Test creating OllamaClient."""
        client_recipe = {
            'client': {
                'name': 'ollama_benchmark',
                'target_service': {'name': 'ollama', 'port': 11434},
                'duration': 300,
                'parameters': {
                    'model': 'llama2',
                    'num_requests': 10
                },
                'container': {
                    'docker_source': 'docker://python:3.11-slim',
                    'image_path': '$HOME/containers/benchmark_client.sif'
                },
                'script': {
                    'name': 'ollama_benchmark.py',
                    'local_path': 'benchmark_scripts/',
                    'remote_path': '$HOME/benchmark_scripts/'
                }
            }
        }
        
        client = JobFactory.create_client(client_recipe, self.test_config)
        
        self.assertIsInstance(client, OllamaClient)
        self.assertEqual(client.name, 'ollama_benchmark')
        self.assertEqual(client.get_target_service_name(), 'ollama')

    def test_service_container_path_resolution(self):
        """Test service container path resolution."""
        service_recipe = {
            'service': {
                'name': 'ollama',
                'container_image': 'ollama.sif',
                'container': {
                    'image_path': '$HOME/containers/ollama.sif'
                }
            }
        }
        
        service = JobFactory.create_service(service_recipe, self.test_config)
        
        # Test with image_path in container config
        path = service._resolve_container_path()
        self.assertEqual(path, '$HOME/containers/ollama.sif')
        
        # Test fallback behavior with Ollama service
        fallback_recipe = {
            'service': {
                'name': 'ollama',
                'container_image': 'test.sif',
                'container': {}
            }
        }
        fallback_config = {'containers': {'base_path': '/mnt/containers'}, 'slurm': {'account': 'test'}}
        service_fallback = JobFactory.create_service(fallback_recipe, fallback_config)
        path_fallback = service_fallback._resolve_container_path()
        self.assertEqual(path_fallback, '/mnt/containers/test.sif')

    def test_client_container_path_resolution(self):
        """Test client container path resolution."""
        client_recipe = {
            'client': {
                'name': 'ollama_benchmark',
                'container_image': 'benchmark.sif',
                'target_service': {'name': 'ollama'},
                'container': {
                    'image_path': '$HOME/containers/benchmark.sif'
                }
            }
        }
        
        client = JobFactory.create_client(client_recipe, self.test_config)
        
        path = client._resolve_container_path()
        self.assertEqual(path, '$HOME/containers/benchmark.sif')

    def test_docker_source_resolution(self):
        """Test Docker source resolution for services and clients."""
        # Test service docker source
        service_recipe = {
            'service': {
                'name': 'ollama',
                'container_image': 'ollama.sif',
                'container': {
                    'docker_source': 'docker://ollama/ollama:latest'
                }
            }
        }
        
        service = JobFactory.create_service(service_recipe, self.test_config)
        self.assertEqual(service._get_docker_source(), 'docker://ollama/ollama:latest')
        
        # Test client docker source
        client_recipe = {
            'client': {
                'name': 'ollama_benchmark',
                'container_image': 'benchmark.sif',
                'target_service': {'name': 'ollama'},
                'container': {
                    'docker_source': 'docker://python:3.11-slim'
                }
            }
        }
        
        client = JobFactory.create_client(client_recipe, self.test_config)
        self.assertEqual(client._get_docker_source(), 'docker://python:3.11-slim')

    def test_container_build_commands(self):
        """Test container build commands generation."""
        service_recipe = {
            'service': {
                'name': 'ollama',
                'container_image': 'ollama.sif',
                'container': {
                    'docker_source': 'docker://ollama/ollama:latest',
                    'image_path': '$HOME/containers/ollama.sif'
                }
            }
        }
        
        service = JobFactory.create_service(service_recipe, self.test_config)
        
        commands = service._generate_container_build_commands()
        
        # Check that essential commands are present
        commands_str = ' '.join(commands)
        self.assertIn('mkdir -p', commands_str)
        self.assertIn('docker://ollama/ollama:latest', commands_str)
        self.assertIn('apptainer build', commands_str)
        self.assertIn('$HOME/containers/ollama.sif', commands_str)

    def test_slurm_script_generation(self):
        """Test SLURM script generation."""
        service_recipe = {
            'service': {
                'name': 'ollama',
                'container_image': 'ollama.sif',
                'resources': {
                    'time': '01:00:00',
                    'partition': 'gpu',
                    'mem': '8GB',
                    'gres': 'gpu:1'
                },
                'environment': {
                    'OLLAMA_HOST': '0.0.0.0:11434'
                },
                'container': {
                    'docker_source': 'docker://ollama/ollama:latest',
                    'image_path': '$HOME/containers/ollama.sif'
                }
            }
        }
        
        service = JobFactory.create_service(service_recipe, self.test_config)
        
        script = service.generate_slurm_script('test_job_123')
        
        # Test SLURM headers
        self.assertIn('#!/bin/bash', script)
        self.assertIn('#SBATCH --job-name=ollama_test_job_123', script)
        self.assertIn('#SBATCH --account=test_account', script)
        self.assertIn('#SBATCH --time=01:00:00', script)
        self.assertIn('#SBATCH --partition=gpu', script)
        self.assertIn('#SBATCH --mem=8GB', script)
        self.assertIn('#SBATCH --gres=gpu:1', script)
        
        # Test container management
        self.assertIn('apptainer build', script)
        self.assertIn('docker://ollama/ollama:latest', script)
        
        # Test container execution
        self.assertIn('apptainer exec', script)
        self.assertIn('--env OLLAMA_HOST=0.0.0.0:11434', script)

    def test_client_slurm_script_generation(self):
        """Test client SLURM script generation."""
        client_recipe = {
            'client': {
                'name': 'ollama_benchmark',
                'container_image': 'benchmark.sif',
                'target_service': {'name': 'ollama'},
                'duration': 300,
                'container': {
                    'docker_source': 'docker://python:3.11-slim',
                    'image_path': '$HOME/containers/benchmark.sif'
                }
            }
        }
        
        client = JobFactory.create_client(client_recipe, self.test_config)
        
        script = client.generate_slurm_script('client_123', 'target-host')
        
        # Test basic structure
        self.assertIn('#!/bin/bash', script)
        self.assertIn('TARGET_SERVICE_HOST=target-host', script)
        
        # Test container build commands for client
        self.assertIn('Client container management', script)
        self.assertIn('docker://python:3.11-slim', script)
        
        # Test container execution
        self.assertIn('apptainer exec', script)

    def test_container_command_generation(self):
        """Test container command generation."""
        # Test service container command
        service_recipe = {
            'service': {
                'name': 'ollama',
                'container_image': 'ollama.sif',
                'resources': {'gres': 'gpu:1'},
                'environment': {'OLLAMA_HOST': '0.0.0.0:11434'},
                'container': {'image_path': '$HOME/containers/ollama.sif'}
            }
        }
        
        service = JobFactory.create_service(service_recipe, self.test_config)
        
        cmd = service.get_container_command()
        self.assertIn('apptainer exec', cmd)
        self.assertIn('--nv', cmd)  # GPU support
        self.assertIn('--env OLLAMA_HOST=0.0.0.0:11434', cmd)
        self.assertIn('&', cmd)  # Background execution
        
        # Test client container command
        client_recipe = {
            'client': {
                'name': 'ollama_benchmark',
                'container_image': 'benchmark.sif',
                'target_service': {'name': 'ollama'},
                'environment': {'PYTHONPATH': '/benchmark'},
                'container': {'image_path': '$HOME/containers/benchmark.sif'}
            }
        }
        
        client = JobFactory.create_client(client_recipe, self.test_config)
        
        cmd = client.get_container_command()
        self.assertIn('apptainer exec', cmd)
        self.assertIn('--env PYTHONPATH=/benchmark', cmd)
        self.assertIn('--bind', cmd)  # Script mounting

    def test_edge_cases(self):
        """Test edge cases and error handling."""
        # Test empty container config
        service_recipe = {
            'service': {
                'name': 'ollama',
                'container_image': 'ollama.sif',
                'container': {}
            }
        }
        empty_config = {}
        
        service = JobFactory.create_service(service_recipe, empty_config)
        
        # Should not crash
        self.assertIsNone(service._get_docker_source())
        path = service._resolve_container_path()
        self.assertEqual(path, 'ollama.sif')
        
        # Test client with missing target service details
        client_recipe = {
            'client': {
                'name': 'ollama_benchmark',
                'container_image': 'benchmark.sif',
                'target_service': {'name': 'ollama'}
            }
        }
        
        client = JobFactory.create_client(client_recipe, empty_config)
        
        self.assertEqual(client.get_target_service_name(), 'ollama')
        self.assertEqual(client.target_service, {'name': 'ollama'})


def run_manual_tests():
    """Run tests manually without unittest framework."""
    print("=== Manual Test Execution ===")
    
    if not IMPORTS_AVAILABLE:
        print("❌ Cannot run tests: Required modules not available")
        print("Make sure you're running from the correct directory and src/services modules exist")
        return 1
    
    try:
        # Create test instance
        test_instance = TestJobClasses()
        test_instance.setUp()
        
        # Get all test methods
        test_methods = [method for method in dir(test_instance) 
                       if method.startswith('test_') and callable(getattr(test_instance, method))]
        
        passed = 0
        failed = 0
        
        for test_method in test_methods:
            try:
                print(f"Running {test_method}...", end=' ')
                getattr(test_instance, test_method)()
                print("✅ PASSED")
                passed += 1
            except Exception as e:
                print(f"❌ FAILED: {e}")
                failed += 1
        
        print(f"\n=== Results ===")
        print(f"Total: {passed + failed}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        
        return 0 if failed == 0 else 1
        
    except Exception as e:
        print(f"❌ Test setup failed: {e}")
        return 1


if __name__ == '__main__':
    import sys
    
    # Try to run with unittest first
    try:
        if len(sys.argv) > 1 and sys.argv[1] == '--manual':
            exit(run_manual_tests())
        else:
            # Run with unittest
            unittest.main(verbosity=2)
    except SystemExit:
        pass
    except Exception as e:
        print(f"Unittest failed, trying manual execution: {e}")
        exit(run_manual_tests())