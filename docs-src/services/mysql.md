# MySQL Service

MySQL is a popular open-source relational database management system.

## Overview

| Property | Value |
|----------|-------|
| **Type** | Relational Database |
| **Default Port** | 3306 |
| **GPU Required** | No |
| **Container** | `docker://mysql:8.0` |

## Quick Start

```bash
# Start MySQL service
python main.py --recipe recipes/services/mysql.yaml

# Run benchmark
python main.py --recipe recipes/clients/mysql_benchmark.yaml --target-service mysql_xxx
```

## Recipe Configuration

```yaml
# recipes/services/mysql.yaml
service:
  name: mysql
  description: "MySQL relational database"
  
  container:
    docker_source: docker://mysql:8.0
    image_path: $HOME/containers/mysql_latest.sif
  
  resources:
    nodes: 1
    ntasks: 1
    cpus_per_task: 4
    mem: "8G"
    time: "02:00:00"
    partition: cpu
    qos: default
  
  environment:
    MYSQL_ROOT_PASSWORD: "benchmark_root_password"
    MYSQL_DATABASE: "benchmark"
    MYSQL_USER: "benchmark"
    MYSQL_PASSWORD: "benchmark_password"
  
  ports:
    - 3306
```

### With Monitoring

```yaml
# recipes/services/mysql_with_cadvisor.yaml
service:
  name: mysql
  enable_cadvisor: true
  cadvisor_port: 8080
  # ... rest of config
```

## Benchmark Client

```yaml
# recipes/clients/mysql_benchmark.yaml
client:
  name: mysql_benchmark
  type: mysql_benchmark
  
  parameters:
    database: "benchmark"
    num_threads: 10
    num_transactions: 10000
    table_size: 100000
    operations: "read,write,update,delete"
    output_file: "$HOME/results/mysql_benchmark.json"
```

### Benchmark Metrics

| Metric | Description |
|--------|-------------|
| `transactions_per_second` | TPS |
| `queries_per_second` | QPS |
| `read_latency_avg` | Average read time |
| `write_latency_avg` | Average write time |
| `connection_time` | Connection establishment time |

## CLI Access

```bash
# Create SSH tunnel
ssh -L 3306:mel0222:3306 -N u103227@login.lxp.lu -p 8822

# Connect with mysql client
mysql -h 127.0.0.1 -u benchmark -p benchmark
```

## Performance Tuning

```yaml
environment:
  MYSQL_INNODB_BUFFER_POOL_SIZE: "4G"
  MYSQL_MAX_CONNECTIONS: "200"
  MYSQL_INNODB_LOG_FILE_SIZE: "256M"
```

---

See also: [Services Overview](overview.md)
