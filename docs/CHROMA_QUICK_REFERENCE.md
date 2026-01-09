# Chroma Vector Database - Quick Reference

## What Was Created?

### 1. Service Implementation
- **File**: `src/services/chroma.py`
- **Classes**: `ChromaService`, `ChromaClient`
- **Registered**: In `src/services/__init__.py`

### 2. Recipes
- **Service**: `recipes/services/chroma.yaml`
- **Client**: `recipes/clients/chroma_benchmark.yaml`
- **Parametric**: `recipes/clients/chroma_parametric.yaml`

### 3. Benchmark Scripts
- **Single-run**: `benchmark_scripts/chroma_benchmark.py`
- **Parametric**: `benchmark_scripts/chroma_parametric_benchmark.py`
- **Analysis**: `analysis/plot_chroma_results.py`

### 4. Automation Scripts
- **Parametric helper**: `scripts/run_chroma_parametric.sh`

### 5. Documentation
- **File**: `docs/CHROMA_INTEGRATION_GUIDE.md`
- **Content**: Complete Workflow, Configuration, Troubleshooting, Parametric Benchmarking

## Workflow in 5 Steps (Single Benchmark)

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

# 5. Retrieve results
ssh login.lxp.lu
# Results are in the results directory
ls -lh ~/results/
# View benchmark results JSON
cat ~/results/chroma_benchmark_results.json
```

## Parametric Benchmark Workflow (5-Step Automated)

```bash
# Fully automated - does everything for you!
./scripts/run_chroma_parametric.sh
```

**This script automatically:**
1. ✅ Starts Chroma service (or uses existing one)
2. ✅ Submits parametric benchmark job
3. ✅ Waits for completion (1-4 hours)
4. ✅ Downloads results from cluster
5. ✅ Generates all 7 analysis plots
6. ✅ Opens plots directory

**Manual alternative (if needed):**

```bash
# 1. Start service
python main.py --recipe recipes/services/chroma.yaml

# 2. Get service ID
python main.py --list-running-services

# 3. Submit parametric benchmark
python main.py --recipe recipes/clients/chroma_parametric.yaml --target-service <SERVICE_ID>

# 4. Wait for completion
python main.py --status

# 5. Download results
python main.py --download-results

# 6. Generate plots
python analysis/plot_chroma_results.py
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

### Single Benchmark Client (`chroma_benchmark.yaml`)
```yaml
parameters:
  num_documents: 1000           # Number of documents
  embedding_dimension: 384      # Embedding size
  batch_size: 100               # Batch size
  num_queries: 100              # Number of queries
  top_k: 10                     # Results per query
  output_file: "/tmp/chroma_benchmark_results.json"
```

### Parametric Benchmark Client (`chroma_parametric.yaml`)
```yaml
parameters:
  num_documents: "500,1000,2000,5000"        # Document sweep
  embedding_dimensions: "192,384,768,1536"   # Dimension sweep
  batch_sizes: "50,100,200,500"              # Batch size sweep
  num_queries: 1000                          # Fixed queries
  top_k: 10                                  # Fixed top-k
```

## Customization Examples

### Faster Parametric Run (Quick Testing)
```yaml
parameters:
  num_documents: "500,1000"           # Fewer points
  embedding_dimensions: "384,768"     # Fewer dimensions
  batch_sizes: "100,200"              # Fewer batch sizes
```

### Comprehensive Parametric Sweep
```yaml
parameters:
  num_documents: "100,500,1000,2000,5000,10000"
  embedding_dimensions: "128,192,384,768,1536"
  batch_sizes: "25,50,100,200,500"
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

1. ✅ Test single benchmark: `python main.py --recipe recipes/services/chroma.yaml`
2. ✅ Test parametric: `./scripts/run_chroma_parametric.sh`
3. 📊 View plots: `analysis/plots/*.png`
4. 🔧 Adjust parameters for your use case
5. 📈 Scale benchmark

## ⚠️ Important Notes

### About Results Location

**Single Benchmark:**
- Automatic copy to `~/results/` on HPC cluster
- Access via: `ssh login.lxp.lu && ls ~/results/`

**Parametric Benchmark:**
- Results in `./results/` locally after `--download-results`
- Plots in `./analysis/plots/` after running `plot_chroma_results.py`

### About Parametric Benchmarks

- **Duration**: 1-4 hours depending on parameter ranges
- **Memory**: 8GB service + 8GB client per run
- **Parallelization**: Runs sequentially; no concurrent benchmarks
- **Results**: One JSON file per parametric run

### About Plots

- Plots use dark background for readability
- Heatmaps are normalized to show relative performance
- All metrics are automatically calculated from JSON results

## Comparison: Single vs Parametric

| Aspect | Single Benchmark | Parametric |
|--------|------------------|-----------|
| **Duration** | 5-10 minutes | 1-4 hours |
| **Parameters** | Fixed | Swept grid |
| **Plots** | None | 7 analysis plots |
| **Scaling Data** | No | Yes |
| **Quick Test** | ✅ Yes | ❌ No |
| **Comprehensive Analysis** | ❌ No | ✅ Yes |

## Comparison with Ollama & Redis

| Aspect | Ollama | Chroma | Redis |
|--------|--------|--------|-------|
| **Type** | LLM Service | Vector DB | Key-Value DB |
| **Port** | 11434 | 8000 | 6379 |
| **GPU** | Yes | No | No |
| **Memory** | 16GB | 8GB | 4GB |
| **Partition** | gpu | cpu | cpu |
| **Use Case** | Text Gen | Vector Search | Caching |
| **Parametric** | No | Yes ✅ | Yes ✅ |

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

### Parametric Script Fails
```bash
# Check Python packages
pip install chromadb numpy matplotlib requests

# Run with debug output
bash -x ./scripts/run_chroma_parametric.sh

# Manual parametric
python benchmark_scripts/chroma_parametric_benchmark.py \
  --endpoint http://localhost:8000 \
  --output-file results/debug.json
```

### Results Not Found
```bash
# For single benchmarks - check cluster
ssh login.lxp.lu
ls -lh ~/results/

# For parametric - check locally
ls -lh results/chroma_parametric_*.json

# Regenerate plots
python analysis/plot_chroma_results.py --results-dir results/
```

### Out of Memory
```yaml
# Increase in chroma.yaml:
resources:
  mem: "16GB"  # or more

# Or reduce workload in parametric:
parameters:
  num_documents: "500,1000"  # Fewer points
```

### Plots Not Generated
```bash
# Install dependencies
pip install matplotlib numpy

# Manually regenerate
python analysis/plot_chroma_results.py

# Check if JSON files exist
ls -lh results/chroma_parametric_*.json
```

## Further Information

- **Complete Guide**: `docs/CHROMA_INTEGRATION_GUIDE.md`
- **Service Code**: `src/services/chroma.py`
- **Benchmark Code**: `benchmark_scripts/chroma_benchmark.py`
- **Parametric Code**: `benchmark_scripts/chroma_parametric_benchmark.py`
- **Analysis Code**: `analysis/plot_chroma_results.py`
- **Chroma Docs**: https://docs.trychroma.com/
- **Redis Comparison**: `docs/REDIS_QUICK_REFERENCE.md`

## File Reference

```
benchmark_scripts/
├── chroma_benchmark.py              # Single run
├── chroma_parametric_benchmark.py   # Parametric sweep
└── requirements.txt

analysis/
├── plot_chroma_results.py           # Generate plots
└── plots/                           # Output directory
    ├── 1_insertion_throughput_vs_documents.png
    ├── 2_insertion_throughput_vs_dimension.png
    ├── 3_insertion_throughput_vs_batch_size.png
    ├── 4_query_latency_vs_documents.png
    ├── 5_query_latency_vs_dimension.png
    ├── 6_heatmap_insertion_throughput.png
    └── 7_heatmap_query_latency.png

recipes/
├── services/
│   └── chroma.yaml                  # Service config
└── clients/
    ├── chroma_benchmark.yaml        # Single benchmark
    └── chroma_parametric.yaml       # Parametric sweep

scripts/
└── run_chroma_parametric.sh         # Automation script

docs/
├── CHROMA_INTEGRATION_GUIDE.md      # Complete reference
└── CHROMA_QUICK_REFERENCE.md        # This file
```

---

**Good luck with Chroma! 🚀**

For parametric benchmarking, start with: `./scripts/run_chroma_parametric.sh`
