#!/usr/bin/env python3
"""
Simple SSH Client Test
Basic test script to verify SSH connectivity and run simple commands
"""

import sys
import os
import time
import logging
from pathlib import Path

# Add parent directory to path to import ssh_client
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

def test_ssh_connection():
    """Simple SSH connection test with basic commands"""
    
    # Load configuration from main config.yaml
    config_file = Path(__file__).parent.parent / 'config.yaml'
    if not config_file.exists():
        print("❌ Configuration file not found: config.yaml")
        print("Make sure you're running from the orchestrator directory")
        print("Expected config file at: ../config.yaml")
        return False
    
    # Import YAML parser
    try:
        import yaml
    except ImportError:
        print("❌ PyYAML not available. Install with: pip install pyyaml")
        return False
    
    # Load YAML configuration
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"❌ Failed to load config file: {e}")
        return False
    
    # Extract HPC connection settings
    hpc_config = config.get('hpc', {})
    if not hpc_config:
        print("❌ No 'hpc' section found in config.yaml")
        return False
    
    hostname = hpc_config.get('hostname')
    username = hpc_config.get('username') 
    password = hpc_config.get('password')
    key_filename = hpc_config.get('key_filename')
    port = hpc_config.get('port', 22)
    
    if not hostname or not username:
        print("❌ hostname and username are required in config.yaml hpc section")
        return False
    
    # Import SSH client
    try:
        from ssh_client import SSHClient
    except ImportError as e:
        print(f"❌ Could not import ssh_client: {e}")
        print("Make sure you have paramiko and scp installed: pip install paramiko scp")
        return False
    
    print("="*50)
    print("SSH Client Simple Test")
    print("="*50)
    print(f"Testing connection to: {username}@{hostname}:{port}")
    print()
    
    # Create SSH client
    ssh_client = SSHClient(
        hostname=hostname,
        username=username,
        password=password,
        key_filename=key_filename,
        port=port
    )
    
    # Test connection
    print("🔌 Connecting to SSH server...")
    if not ssh_client.connect():
        print("❌ SSH connection failed")
        return False
    
    print("✅ SSH connection successful!")
    
    # Test basic commands
    commands = [
        ("whoami", "Check current user"),
        ("pwd", "Show current directory"), 
        ("hostname", "Show hostname"),
        ("date", "Show current date"),
        ("which sbatch", "Check if SLURM is available"),
        ("which apptainer", "Check if Apptainer is available"),
        ("ls -la", "List files in home directory")
    ]
    
    print("\n📋 Running basic commands:")
    success_count = 0
    
    for cmd, description in commands:
        print(f"\n  Command: {cmd} ({description})")
        try:
            exit_code, stdout, stderr = ssh_client.execute_command(cmd)
            if exit_code == 0:
                output = stdout.strip()
                if len(output) > 100:
                    output = output[:100] + "..."
                print(f"    ✅ Success: {output}")
                success_count += 1
            else:
                print(f"    ⚠️  Exit code {exit_code}: {stderr.strip()}")
        except Exception as e:
            print(f"    ❌ Error: {e}")
    
    # Test file upload
    print(f"\n📁 Testing file operations...")
    test_content = f"""#!/bin/bash
echo "Test script executed successfully at $(date)"
echo "Running on: $(hostname)"
echo "Current user: $(whoami)"
"""
    
    local_file = Path("test_script.sh")
    remote_file = "/tmp/ssh_test_script.sh"
    
    try:
        # Create local test file
        with open(local_file, 'w') as f:
            f.write(test_content)
        
        # Upload file
        print("  Uploading test script...")
        if ssh_client.upload_file(str(local_file), remote_file):
            print("    ✅ Upload successful")
            
            # Make executable and run
            ssh_client.execute_command(f"chmod +x {remote_file}")
            exit_code, stdout, stderr = ssh_client.execute_command(f"bash {remote_file}")
            
            if exit_code == 0:
                print("    ✅ Script execution successful:")
                for line in stdout.strip().split('\n'):
                    print(f"      {line}")
                success_count += 1
            else:
                print(f"    ⚠️  Script execution failed: {stderr.strip()}")
            
            # Cleanup
            ssh_client.execute_command(f"rm -f {remote_file}")
        else:
            print("    ❌ Upload failed")
    
    except Exception as e:
        print(f"    ❌ File operation error: {e}")
    
    finally:
        # Cleanup local file
        if local_file.exists():
            local_file.unlink()
    
    # Test SLURM job submission (if available)
    print(f"\n🚀 Testing SLURM job submission...")
    job_script = """#!/bin/bash -l
#SBATCH --job-name=ssh_test
#SBATCH --time=00:01:00
#SBATCH --account=p200981
#SBATCH --qos=default
#SBATCH --partition=cpu
#SBATCH --nodes=1
#SBATCH --ntasks=1

echo "SLURM test job started at $(date)"
sleep 5
echo "SLURM test job completed at $(date)"
"""
    
    try:
        job_id = ssh_client.submit_slurm_job(job_script, "ssh_test_job.sh")
        if job_id:
            print(f"    ✅ Job submitted: {job_id}")
            
            # Wait a moment then check status
            time.sleep(3)
            status = ssh_client.get_job_status(job_id)
            if status:
                print(f"    📊 Job status: {status.get('state', 'UNKNOWN')}")
            
            # Cancel the job
            if ssh_client.cancel_job(job_id):
                print(f"    ✅ Job cancelled successfully")
            success_count += 1
        else:
            print("    ⚠️  Job submission failed (SLURM may not be available)")
    
    except Exception as e:
        print(f"    ❌ SLURM test error: {e}")
    
    # Disconnect
    print(f"\n🔌 Disconnecting...")
    ssh_client.disconnect()
    
    # Summary
    total_tests = len(commands) + 2  # commands + file ops + slurm
    print(f"\n" + "="*50)
    print("TEST RESULTS")
    print("="*50)
    print(f"Tests completed: {success_count}/{total_tests}")
    print(f"Success rate: {success_count/total_tests*100:.0f}%")
    
    if success_count >= total_tests - 1:  # Allow 1 failure
        print("🎉 SSH client is working correctly!")
        return True
    else:
        print("⚠️  Some tests failed - check your SSH configuration")
        return False

def main():
    """Main function"""
    # Setup basic logging
    logging.basicConfig(level=logging.WARNING)
    
    try:
        success = test_ssh_connection()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        return 130
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    print(__doc__)
    print("\nConfiguration:")
    print("This test uses the main config.yaml file from the orchestrator.")
    print("Make sure config.yaml exists in the parent directory with HPC settings:")
    print("""
# config.yaml
hpc:
  hostname: "login.lxp.lu"
  username: "your_username"
  port: 22
  # Use either password or key_filename
  password: null  # "your_password"
  key_filename: "~/.ssh/id_rsa"  # Path to SSH private key
""")
    print("Then run: python simple_ssh_test.py")
    print("="*50)
    
    sys.exit(main())