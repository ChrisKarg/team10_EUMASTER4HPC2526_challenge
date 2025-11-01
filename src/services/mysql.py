"""
MySQL Service and Client implementations
"""

import logging
from typing import Dict, Any, List, Optional
from .base import Service, Client, JobFactory


class MySQLService(Service):
    """MySQL database service implementation"""
    
    @classmethod
    def from_recipe(cls, recipe: Dict[str, Any], config: Dict[str, Any]) -> 'MySQLService':
        """Create MySQLService from recipe dictionary"""
        service_def = recipe.get('service', {})
        
        instance = cls(
            name=service_def.get('name', 'mysql'),
            container_image=service_def.get('container_image', 'mysql_latest.sif'),
            resources=service_def.get('resources', {}),
            environment=service_def.get('environment', {}),
            config=config,
            ports=service_def.get('ports', [3306]),  # Default MySQL port
            command=service_def.get('command', 'mysqld'),
            args=service_def.get('args', []),
            container=service_def.get('container', {})
        )
        instance.service_def = service_def  # Store for access to init_script
        return instance
    
    def get_service_setup_commands(self) -> List[str]:
        """Custom setup commands for MySQL service"""
        data_dir = self.environment.get('MYSQL_DATA_DIR', '/mysql/data')
        container_path = self.container.get('image_path', '/mnt/tier2/users/u103300/mysql_latest.sif')
        init_script = self.service_def.get('init_script', '')
        
        # Save initialization SQL to a file
        if init_script:
            init_commands = [
                "# Save MySQL initialization script",
                "mkdir -p /mnt/tier2/users/u103300/mysql/init",
                "cat > /mnt/tier2/users/u103300/mysql/init/init.sql << 'EOF'",
                init_script,
                "EOF",
            ]
        else:
            init_commands = []
        
        return [
            "# MySQL service setup",
            "echo 'Setting up MySQL service...'",
            "# Ensure container directory exists",
            "mkdir -p /mnt/tier2/users/u103300/containers",
            "",
            "# Create and prepare MySQL data directory structure",
            "rm -rf /mnt/tier2/users/u103300/mysql/data/*",  # Clean existing data
            "mkdir -p /mnt/tier2/users/u103300/mysql/data",
            "mkdir -p /mnt/tier2/users/u103300/mysql/tmp",
            "mkdir -p /mnt/tier2/users/u103300/mysql/run",
            "",
            "# Set proper permissions",
            "chmod -R 777 /mnt/tier2/users/u103300/mysql",
            "",
            *init_commands,  # Add initialization script commands if present
            "",
            "# Initialize MySQL data directory",
            "echo 'Initializing MySQL data directory...'",
            f"if [ -f {container_path} ]; then",
            "    # Create MySQL files directory with proper ownership",
            f"    apptainer exec --bind /mnt/tier2/users/u103300/mysql:/mysql {container_path} /bin/bash -c '",
            "        mysqld --initialize-insecure --datadir=/mysql/data",
            "    '",
            "    if [ $? -eq 0 ]; then",
            "        echo 'MySQL data directory initialized successfully'",
            "        # Apply initialization script if it exists",
            "        if [ -f /mnt/tier2/users/u103300/mysql/init/init.sql ]; then",
            f"            apptainer exec --bind /mnt/tier2/users/u103300/mysql:/mysql {container_path} /bin/bash -c '",
            "                mysqld --datadir=/mysql/data --socket=/mysql/run/mysqld.sock &",
            "                sleep 10",  # Wait for MySQL to start
            "                mysql -u root --socket=/mysql/run/mysqld.sock < /mysql/init/init.sql",
            "                pkill mysqld",
            "                sleep 5",  # Wait for MySQL to stop
            "            '",
            "        fi",
            "    else",
            "        echo 'Error: Failed to initialize MySQL data directory'",
            "        exit 1",
            "    fi",
            "else",
            "    echo 'Error: MySQL container image not found'",
            "    exit 1",
            "fi",
            ""
        ]
    
    def get_container_command(self) -> str:
        """Enhanced container command with bind mounts for MySQL"""
        cmd_parts = ["apptainer exec"]
        
        # Add bind mounts if specified in container configuration
        if self.container and 'bind_mounts' in self.container:
            for bind_mount in self.container['bind_mounts']:
                # Expand $HOME in bind mount paths
                expanded_mount = bind_mount.replace('$HOME', '${HOME}')
                cmd_parts.append(f"--bind {expanded_mount}")
        
        # Add environment variables
        for key, value in self.environment.items():
            cmd_parts.append(f"--env {key}={value}")
        
        # Add container image with base path
        container_base_path = self.config.get('containers', {}).get('base_path', '')
        if container_base_path and not self.container_image.startswith('/'):
            container_path = f"{container_base_path}/{self.container_image}"
        else:
            container_path = self.container_image
        cmd_parts.append(container_path)
        
        # Add command and args
        if self.command:
            cmd_parts.append(self.command)
            if self.args:
                cmd_parts.extend(self.args)
        
        # Run in background for services
        cmd_parts.append("&")
        
        return " ".join(cmd_parts)
    
    def get_health_check_commands(self) -> List[str]:
        """Enhanced health check for MySQL service"""
        return [
            "",
            "# Health check and monitoring for MySQL",
            "sleep 30  # Allow MySQL to initialize",
            "",
            "# Monitor MySQL process and log status",
            "echo 'MySQL service started, monitoring...'",
            "while kill -0 $! 2>/dev/null; do",
            "    echo \"$(date): MySQL service is running\"",
            "    sleep 60",
            "done",
            "",
            "echo 'MySQL service stopped'"
        ]


class MySQLClient(Client):
    """MySQL benchmark client implementation"""
    
    @classmethod
    def from_recipe(cls, recipe: Dict[str, Any], config: Dict[str, Any]) -> 'MySQLClient':
        """Create MySQLClient from recipe dictionary"""
        client_def = recipe.get('client', {})
        
        # Parse script configuration
        script_config = client_def.get('script', {})
        script_name = script_config.get('name', 'mysql_benchmark.py')
        script_local_path = script_config.get('local_path', 'benchmark_scripts/')
        script_remote_path = script_config.get('remote_path', '$HOME/benchmark_scripts/')
        
        return cls(
            name=client_def.get('name', 'mysql_benchmark'),
            container_image=client_def.get('container_image', 'mysql_client.sif'),
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
                               default_port: int = 3306, protocol: str = None) -> str:
        """MySQL-specific service endpoint resolution"""
        # Check if endpoint is explicitly set in parameters
        endpoint_from_params = self.parameters.get('endpoint')
        if endpoint_from_params:
            return endpoint_from_params
        
        # Use TARGET_SERVICE_HOST environment variable
        host = target_service_host or "${TARGET_SERVICE_HOST}"
        
        # Get port from target service config or use MySQL default (3306)
        if self.target_service and isinstance(self.target_service, dict):
            port = self.target_service.get('port', 3306)
        else:
            port = 3306
        
        # Return MySQL connection string format (no protocol)
        return f"{host}:{port}"


# Register the MySQL implementations with the factory
JobFactory.register_service('mysql', MySQLService)
JobFactory.register_client('mysql', MySQLClient)