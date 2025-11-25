# Redis Quick Reference

## Recipes

- **Service**: `recipes/services/redis.yaml`
- **Benchmark**: `recipes/clients/redis_benchmark.yaml`

## Common Commands

### Start Service
```bash
python main.py --recipe recipes/services/redis.yaml
```

### Run Benchmark
```bash
# Auto-discovery of service endpoint
python main.py --recipe recipes/clients/redis_benchmark.yaml --target-service <SERVICE_JOB_ID>
```

## Benchmark Parameters

Modify `recipes/clients/redis_benchmark.yaml` to tune the load:

```yaml
parameters:
  num_operations: 1000000  # 1 Million requests
  clients: 100             # 100 Parallel clients
  value_size: 1024         # 1KB payloads
  pipeline: 16             # Pipeline 16 commands (High Throughput)
  native_tests: "set,get"  # Only test SET and GET
```

## Download Results

After benchmarks complete, download the JSON results to your local machine:

```bash
# Download all JSON results from $HOME/results (default)
python main.py --download-results

# Download from a custom remote path
python main.py --download-results "$SCRATCH/*.json"
```

Results are saved to `./results/` locally as `redis_benchmark_{JOB_ID}.json`.

## Troubleshooting

**"Connection Refused"**
- Ensure the Redis Service job is `RUNNING`.
- Check `slurm-*.out` logs for binding errors.
- Ensure Client and Service are on the same network (or use Infiniband IP if configured).

**"Permission Denied"**
- Check that `benchmark_scripts/redis_benchmark.py` is executable or invoked via `python3`.
