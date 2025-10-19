# Chroma Vector Database - Quick Reference

## What Was Created?

### 1. Service Implementation
- **File**: `src/services/chroma.py`
- **Classes**: `ChromaService`, `ChromaClient`
- **Registered**: In `src/services/__init__.py`

### 2. Recipes
- **Service**: `recipes/services/chroma.yaml`
- **Client**: `recipes/clients/chroma_benchmark.yaml`

### 3. Benchmark Script
- **File**: `benchmark_scripts/chroma_benchmark.py`
- **Features**: Insertion, Queries, Metrics

### 4. Documentation
- **File**: `docs/CHROMA_INTEGRATION_GUIDE.md`
- **Content**: Complete Workflow, Configuration, Troubleshooting

## Workflow in 5 Steps

```bash
# 1. Start service
python main.py --recipe recipes/services/chroma.yaml

# 2. Check status (note the hostname!)
python main.py --status
# Output: mel2198 | RUNNING

# 3. Start client (with hostname from step 2 + port)
python main.py --recipe recipes/clients/chroma_benchmark.yaml \
  --target-endpoint http://mel2198:8000

# 4. Monitor status
python main.py --status

# 5. Retrieve results (IMPORTANT: From SLURM logs!)
ssh login.lxp.lu
# First, find your job ID
sacct -u $USER --format=JobID,JobName,State -S today | grep chroma_be+
# Then view the results with the job ID
sacct -j <job_id> --format=JobID,JobName,State,ExitCode,Elapsed && echo '---LOGS---' && tail -80 slurm-<job_id>.out
```

## Key Parameters

### Service (`chroma.yaml`)
```yaml
resources:
  mem: "8GB"          # Increase for larger datasets
  time: "01:00:00"    # Adjust runtime
  partition: cpu      # No GPU needed
  
ports:
  - 8000              # Standard Chroma port
```

### Client (`chroma_benchmark.yaml`)
```yaml
parameters:
  num_documents: 1000           # Number of documents
  embedding_dimension: 384      # Embedding size
  batch_size: 100               # Batch size
  num_queries: 100              # Number of queries
  top_k: 10                     # Results per query
  output_file: "/tmp/chroma_benchmark_results.json"
```

## Customization Examples

### Large-Scale Benchmark
```yaml
parameters:
  num_documents: 100000
  batch_size: 500
  num_queries: 1000
```

### More Memory
```yaml
resources:
  mem: "32GB"
```

### Longer Runtime
```yaml
resources:
  time: "04:00:00"
```

## Next Steps

1. ✅ Test service: `python main.py --recipe recipes/services/chroma.yaml`
2. ✅ Test client: After service start with `--target-endpoint http://<hostname>:8000`
3. 📊 Retrieve results from SLURM logs: `sacct -j <job_id> --format=JobID,State,ExitCode && tail -80 slurm-<job_id>.out`
4. 🔧 Adjust parameters for your use case
5. 📈 Scale benchmark

## ⚠️ Important Note About Results

**Benchmark results are printed in the SLURM job log, not in a separate file on the login node!**

How to retrieve them:
```bash
ssh login.lxp.lu

# Step 1: Find your job ID
sacct -u $USER --format=JobID,JobName,State -S today | grep chroma

# Step 2: View job status and logs (replace <job_id> with actual ID)
sacct -j <job_id> --format=JobID,JobName,State,ExitCode,Elapsed && echo '---LOGS---' && tail -80 slurm-<job_id>.out
```

Example:
```bash
# If your job ID is 3649933:
sacct -j 3649933 --format=JobID,JobName,State,ExitCode,Elapsed && echo '---LOGS---' && tail -80 slurm-3649933.out
```

The JSON file (`/tmp/chroma_benchmark_results.json`) is created on the compute node but is not directly accessible from the login node.

## Comparison with Ollama

| Aspect | Ollama | Chroma |
|--------|--------|--------|
| **Type** | LLM Service | Vector DB |
| **Port** | 11434 | 8000 |
| **GPU** | Yes | No |
| **Memory** | 16GB | 8GB |
| **Partition** | gpu | cpu |
| **Use Case** | Text Generation | Vector Search |

## Troubleshooting

### Service Not Starting
```bash
ssh login.lxp.lu
cat slurm-<job_id>.err
ls -lh ~/containers/chroma_latest.sif
```

### Client Cannot Connect
```bash
# Check hostname
python main.py --status

# Don't forget the port!
--target-endpoint http://mel2198:8000  # ✅ Correct
--target-endpoint http://mel2198       # ❌ Wrong (missing port)

# Test health check
ssh login.lxp.lu
curl http://mel2198:8000/api/v1/heartbeat
```

### Results Not Found
```bash
# Results are in SLURM log, not in /tmp on login node!
ssh login.lxp.lu

# Correct method (2 steps):
# 1. Find job ID
sacct -u $USER --format=JobID,JobName,State -S today | grep chroma

# 2. View results with job ID
sacct -j <job_id> --format=JobID,State,ExitCode,Elapsed && echo '---LOGS---' && tail -80 slurm-<job_id>.out

# The JSON file is on the compute node:
# /tmp/chroma_benchmark_results.json (not accessible from login node)
```

### Out of Memory
```yaml
# Increase in chroma.yaml:
resources:
  mem: "16GB"  # or more
```

## Further Information

- **Complete Guide**: `docs/CHROMA_INTEGRATION_GUIDE.md`
- **Service Code**: `src/services/chroma.py`
- **Benchmark Code**: `benchmark_scripts/chroma_benchmark.py`
- **Chroma Docs**: https://docs.trychroma.com/

---

**Good luck with Chroma! 🚀**
