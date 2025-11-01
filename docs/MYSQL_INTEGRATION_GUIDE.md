# MySQL Integration Guide

This guide explains how to set up and test the MySQL service and benchmark client on the supercomputer using our job orchestration system.

## Prerequisites

- Access to the supercomputer with SLURM
- Apptainer/Singularity installed
- Python environment with required packages

## Quick Start

1. **Clone the repository (if not already done)**
   ```bash
   git clone https://github.com/ChrisKarg/team10_EUMASTER4HPC2526_challenge.git
   cd team10_EUMASTER4HPC2526_challenge
   ```

2. **Start the MySQL Service**
   ```bash
   # Using the orchestrator script
   python main.py --recipe recipes/services/mysql.yaml
   ```

   This will:
   - Create an Apptainer container from MySQL 8.0 image
   - Start MySQL server in the container
   - Initialize the database with benchmark user and database
   - Expose port 3306 for connections

3. **Run the Benchmark Client**
   ```bash
   # After the service is running and you have its node address
   python main.py --recipe recipes/clients/mysql_benchmark.yaml --target-host <service-node>
   ```

   Replace `<service-node>` with the hostname where the MySQL service is running.

## Detailed Testing Instructions

### 1. Verify Service Deployment

After starting the service, you can check its status:

```bash
# Check SLURM job status
squeue -u $USER

# Check service logs
cat slurm-<jobid>.out
```

The logs should show MySQL successfully starting and listening on port 3306.

### 2. Manual Connection Test

You can test connecting to MySQL manually using the MySQL client in the container:

```bash
# Replace <service-node> with actual hostname
apptainer exec containers/mysql_client.sif mysql -h <service-node> \
    -u benchmark_user -pbenchmark_pass benchmark_db -e "SELECT VERSION();"
```

### 3. Run Benchmark Tests

The benchmark client supports various parameters:

```bash
# Basic benchmark
python main.py --recipe recipes/clients/mysql_benchmark.yaml \
    --target-host <service-node>

# Custom benchmark parameters
python main.py --recipe recipes/clients/mysql_benchmark.yaml \
    --target-host <service-node> \
    --set client.parameters.num_connections=20 \
    --set client.parameters.transactions_per_client=2000
```

### 4. View Benchmark Results

Results are stored in JSON format:

```bash
# View latest benchmark results
cat results/mysql_benchmark_results.json
```

## Common Operations

### Check Container Status
```bash
# List running containers
apptainer instance list
```

### Access MySQL Shell
```bash
# Connect to running MySQL instance
apptainer exec containers/mysql_client.sif mysql -h <service-node> \
    -u benchmark_user -pbenchmark_pass benchmark_db
```

### Monitor Performance
```bash
# View real-time MySQL status
apptainer exec containers/mysql_client.sif mysqladmin -h <service-node> \
    -u benchmark_user -pbenchmark_pass status
```

## Troubleshooting

1. **Service Won't Start**
   - Check SLURM job output: `cat slurm-<jobid>.out`
   - Verify container exists: `ls -l $HOME/containers/mysql_latest.sif`
   - Check port availability: `netstat -tulpn | grep 3306`

2. **Client Can't Connect**
   - Verify service is running: `squeue -u $USER`
   - Check network connectivity: `ping <service-node>`
   - Verify port is open: `nc -zv <service-node> 3306`

3. **Benchmark Failures**
   - Check client logs in results directory
   - Verify database permissions
   - Check available memory and resources

## Configuration Reference

### Service Configuration
Key settings in `recipes/services/mysql.yaml`:
```yaml
service:
  environment:
    MYSQL_ROOT_PASSWORD: "mysecretpassword"
    MYSQL_DATABASE: "benchmark_db"
    MYSQL_USER: "benchmark_user"
    MYSQL_PASSWORD: "benchmark_pass"
```

### Benchmark Configuration
Key settings in `recipes/clients/mysql_benchmark.yaml`:
```yaml
client:
  parameters:
    num_connections: 10
    transactions_per_client: 1000
```

## Best Practices

1. **Resource Allocation**
   - Adjust memory based on database size
   - Use CPU partition unless specific GPU needs
   - Allow enough time for database initialization

2. **Benchmarking**
   - Start with small test runs
   - Gradually increase load
   - Monitor system resources
   - Save and compare results

3. **Production Use**
   - Change default passwords
   - Configure proper backup location
   - Adjust MySQL configuration for workload