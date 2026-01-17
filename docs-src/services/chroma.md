# Chroma Service

Chroma is an open-source vector database for AI applications.

## Overview

| Property | Value |
|----------|-------|
| **Type** | Vector Database |
| **Default Port** | 8000 |
| **GPU Required** | No |
| **Container** | `docker://chromadb/chroma:latest` |

## Quick Start

```bash
# Start Chroma service
python main.py --recipe recipes/services/chroma.yaml

# Run benchmark
python main.py --recipe recipes/clients/chroma_benchmark.yaml --target-service chroma_xxx
```

## Recipe Configuration

```yaml
# recipes/services/chroma.yaml
service:
  name: chroma
  description: "Chroma vector database"
  
  container:
    docker_source: docker://chromadb/chroma:latest
    image_path: $HOME/containers/chroma_latest.sif
  
  resources:
    nodes: 1
    ntasks: 1
    cpus_per_task: 4
    mem: "16G"
    time: "02:00:00"
    partition: cpu
    qos: default
  
  environment:
    CHROMA_SERVER_HOST: "0.0.0.0"
    CHROMA_SERVER_PORT: "8000"
    PERSIST_DIRECTORY: "/data"
  
  ports:
    - 8000
```

## Benchmark Client

```yaml
# recipes/clients/chroma_benchmark.yaml
client:
  name: chroma_benchmark
  type: chroma_benchmark
  
  parameters:
    collection_name: "benchmark_collection"
    num_documents: 10000
    embedding_dimension: 384
    num_queries: 1000
    top_k: 10
    output_file: "$HOME/results/chroma_benchmark.json"
```

### Benchmark Operations

| Operation | Description |
|-----------|-------------|
| `insert` | Add documents with embeddings |
| `query` | Similarity search |
| `update` | Modify existing documents |
| `delete` | Remove documents |

### Metrics

| Metric | Description |
|--------|-------------|
| `insert_throughput` | Documents inserted per second |
| `query_latency_avg` | Average query time |
| `query_latency_p99` | 99th percentile query time |
| `recall@k` | Search accuracy |

## API Examples

```python
import chromadb

# Connect
client = chromadb.HttpClient(host="mel0058", port=8000)

# Create collection
collection = client.create_collection("my_collection")

# Add documents
collection.add(
    documents=["doc1", "doc2"],
    embeddings=[[0.1, 0.2, ...], [0.3, 0.4, ...]],
    ids=["id1", "id2"]
)

# Query
results = collection.query(
    query_embeddings=[[0.1, 0.2, ...]],
    n_results=5
)
```

---

See also: [Services Overview](overview.md)
