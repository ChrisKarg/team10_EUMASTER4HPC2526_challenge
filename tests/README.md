# SSH Client Tests

This directory contains a simple test script for the SSH client functionality.

## Files

- `simple_ssh_test.py` - Main test script for SSH client functionality

## Quick Setup and Usage

### 1. Configure Main Config File

The test uses the main `config.yaml` file from the orchestrator root directory.

Edit `../config.yaml` with your SSH connection details:

```yaml
# config.yaml
hpc:
  hostname: "login.lxp.lu"  # Your HPC hostname
  username: "your_username" # Your username
  port: 22                  # SSH port
  
  # Use either password or key_filename (not both)
  password: null            # "your_password"
  key_filename: "~/.ssh/id_rsa"  # Path to SSH private key
```

### 2. Install Dependencies

```bash
pip install paramiko scp pyyaml
```

### 3. Run Test

```bash
cd tests
python simple_ssh_test.py
```

## What the Test Does

The test script performs these operations:

1. **SSH Connection** - Tests basic connectivity and authentication
2. **Basic Commands** - Runs simple Unix commands:
   - `whoami` - Check current user
   - `pwd` - Show current directory
   - `hostname` - Show hostname
   - `date` - Show current date
   - `which sbatch` - Check if SLURM is available
   - `which apptainer` - Check if Apptainer is available
   - `ls -la` - List files in home directory

3. **File Operations** - Tests file upload/download:
   - Upload a test script
   - Execute the script on remote host
   - Download results
   - Clean up files

4. **SLURM Job Submission** - Tests job management:
   - Submit a simple test job
   - Check job status
   - Cancel the job

## Example Output

```
==================================================
SSH Client Simple Test
==================================================
Testing connection to: user@login.lxp.lu:22

🔌 Connecting to SSH server...
✅ SSH connection successful!

� Running basic commands:

  Command: whoami (Check current user)
    ✅ Success: user

  Command: pwd (Show current directory)
    ✅ Success: /home/users/user

📁 Testing file operations...
  Uploading test script...
    ✅ Upload successful
    ✅ Script execution successful:
      Test script executed successfully at Mon Oct  7 10:30:15 2025
      Running on: mel2001
      Current user: user

🚀 Testing SLURM job submission...
    ✅ Job submitted: 1234567
    📊 Job status: PENDING
    ✅ Job cancelled successfully

🔌 Disconnecting...

==================================================
TEST RESULTS
==================================================
Tests completed: 9/9
Success rate: 100%
🎉 SSH client is working correctly!
```

## Prerequisites

- Python 3.6+
- paramiko and scp packages: `pip install paramiko scp`
- SSH access to HPC cluster
- Valid SSH credentials (password or key file)

## Troubleshooting

### Common Issues

1. **Configuration file not found**:
   ```
   ❌ Configuration file not found: config.yaml
   ```
   Make sure you're running from the tests directory and that `../config.yaml` exists.

2. **Import errors**:
   ```bash
   pip install paramiko scp pyyaml
   ```

3. **SSH connection failed**:
   - Check hostname, username, and credentials in config.yaml
   - Verify SSH key permissions: `chmod 600 ~/.ssh/id_rsa`
   - Test manual SSH: `ssh username@hostname`

4. **SLURM tests fail**:
   - This is normal if SLURM is not available
   - The test will continue with other operations

### Your Current Configuration

Based on your config.yaml, the test will connect to:
- **Hostname**: login.lxp.lu
- **Username**: u103235  
- **Port**: 8822
- **Key**: ~/.ssh/id_ed25519_mlux

### SSH Key Setup

If you don't have an SSH key:

```bash
# Generate SSH key pair
ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa

# Copy public key to remote host
ssh-copy-id username@hostname
```

## Simple Test Only

If you just want to test basic connectivity without the full test suite, you can modify the script or run:

```python
# Quick connectivity test
python -c "
import socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
result = sock.connect_ex(('login.lxp.lu', 22))
print('✅ SSH port accessible' if result == 0 else '❌ SSH port not accessible')
"
```