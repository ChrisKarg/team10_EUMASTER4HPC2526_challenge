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
    
    '''
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
    '''
        
    def get_service_setup_commands(self) -> List[str]:
        """Custom setup commands for MySQL service"""
        container_path = self.container.get('image_path', '/mnt/tier2/users/u103300/mysql_latest.sif')
        init_script = self.service_def.get('init_script', '')
        
        commands = [
            "# MySQL service setup",
            "echo '=== MYSQL SERVICE SETUP VERSION 3.0 ==='",
            "echo 'Setting up MySQL service...'",
            "mkdir -p /mnt/tier2/users/u103300/containers",
            "",
            "# Create and prepare MySQL data directory structure",
            "rm -rf /mnt/tier2/users/u103300/mysql/data/*",
            "mkdir -p /mnt/tier2/users/u103300/mysql/data",
            "mkdir -p /mnt/tier2/users/u103300/mysql/tmp",
            "mkdir -p /mnt/tier2/users/u103300/mysql/run",
            "mkdir -p /mnt/tier2/users/u103300/mysql/init",
            "chmod -R 777 /mnt/tier2/users/u103300/mysql",
            "",
            "# Initialize MySQL data directory",
            "echo 'Initializing MySQL data directory...'",
            f"apptainer exec --bind /mnt/tier2/users/u103300/mysql:/mysql {container_path} mysqld --initialize-insecure --datadir=/mysql/data",
            "",
        ]
        
        # Add init script creation - handle multi-line properly
        if init_script:
            commands.append("# Create init script")
            commands.append("cat > /mnt/tier2/users/u103300/mysql/init/init.sql << 'EOFEOF'")
            # Split the init_script by lines and add each line separately
            for line in init_script.strip().split('\n'):
                commands.append(line)
            commands.append("EOFEOF")
        else:
            commands.append("echo 'SELECT 1;' > /mnt/tier2/users/u103300/mysql/init/init.sql")
        
        commands.extend([
            "",
            "# Verify file was created",
            "echo 'Verifying init script...'",
            "ls -lah /mnt/tier2/users/u103300/mysql/init/init.sql",
            "echo 'Init script contents:'",
            "cat /mnt/tier2/users/u103300/mysql/init/init.sql",
            "",
            # Start MySQL temporarily
            "echo 'Starting MySQL temporarily to run init script...'",
            f"apptainer exec --bind /mnt/tier2/users/u103300/mysql:/mysql {container_path} mysqld --datadir=/mysql/data --socket=/mysql/run/mysqld.sock --pid-file=/mysql/run/mysqld.pid &",
            "MYSQL_PID=$!",
            "",
            # Wait for MySQL
            "echo 'Waiting for MySQL to be ready...'",
            "for i in {1..30}; do",
            f"  if apptainer exec --bind /mnt/tier2/users/u103300/mysql:/mysql {container_path} mysqladmin --socket=/mysql/run/mysqld.sock ping 2>/dev/null; then",
            "    echo 'MySQL is ready!'",
            "    break",
            "  fi",
            "  echo \"Attempt $i/30...\"",
            "  sleep 2",
            "done",
            "",
            # Run init script
            "echo 'Running init script...'",
            # FIX: Use the HOST path for the redirection, not the container path
            f"apptainer exec --bind /mnt/tier2/users/u103300/mysql:/mysql {container_path} mysql -u root --socket=/mysql/run/mysqld.sock < /mnt/tier2/users/u103300/mysql/init/init.sql",
            "",
            # Stop temporary MySQL
            "echo 'Stopping temporary MySQL...'",
            "kill $MYSQL_PID 2>/dev/null || true",
            "sleep 5",
            "",
            "echo 'MySQL initialization complete!'",
            ""
        ])
        
        return commands
    ##
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

        # Resolve container path
        container_path = self._resolve_container_path()
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
    
    def get_container_command(self) -> str:
        """Override to use sysbench directly instead of Python wrapper"""
        # Get parameters
        host = "${TARGET_SERVICE_HOST}"
        port = self.target_service.get('port', 3306)
        threads = self.parameters.get('num_connections', 16)
        duration = self.parameters.get('transactions_per_client', 300)
        tables = self.parameters.get('tables', 10)
        table_size = self.parameters.get('table_size', 100000)

        # Container path
        container_path = self._resolve_container_path()

        # Build the sysbench commands directly without bash wrapper
        commands = [
            f"sysbench oltp_read_write --mysql-host={host} --mysql-port={port} --mysql-user=${{MYSQL_USER}} --mysql-password=${{MYSQL_PASSWORD}} --mysql-db=${{MYSQL_DATABASE}} --tables={tables} --table-size={table_size} prepare",
            f"sysbench oltp_read_write --mysql-host={host} --mysql-port={port} --mysql-user=${{MYSQL_USER}} --mysql-password=${{MYSQL_PASSWORD}} --mysql-db=${{MYSQL_DATABASE}} --tables={tables} --table-size={table_size} --threads={threads} --time={duration} --report-interval=10 --percentile=95 run > /tmp/sysbench_results.txt 2>&1",
            f"sysbench oltp_read_write --mysql-host={host} --mysql-port={port} --mysql-user=${{MYSQL_USER}} --mysql-password=${{MYSQL_PASSWORD}} --mysql-db=${{MYSQL_DATABASE}} cleanup"
        ]

        # Join with && and wrap properly
        full_cmd = " && ".join(commands)

        # Build final command
        env_vars = " ".join([f"--env {k}={v}" for k, v in self.environment.items()])
    
        return f'apptainer exec {env_vars} {container_path} /bin/bash -c "{full_cmd}"'
    
    def get_client_setup_commands(self) -> List[str]:
        """Override to remove Python script checking"""
        return [
            f"echo '=== {self.name.upper()} DEBUG INFO ==='",
            "echo \"Client node: $(hostname)\"",
            f"echo \"Target service: {self.get_target_service_name()}\"",
            "echo '========================='",
            ""
        ]
    
    def get_result_collection_commands(self) -> List[str]:
        """Override to collect sysbench results"""
        return [
            "",
            "mkdir -p $SLURM_SUBMIT_DIR/results",
            "cp /tmp/sysbench_results.txt $SLURM_SUBMIT_DIR/results/ 2>/dev/null || true",
            f"echo '{self.name} completed'",
            ""
        ]
    


# Register the MySQL implementations with the factory
JobFactory.register_service('mysql', MySQLService)
JobFactory.register_client('mysql', MySQLClient)