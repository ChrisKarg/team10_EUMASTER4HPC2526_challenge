#!/usr/bin/env python3
"""
Chroma Vector Database Benchmark Script

This script benchmarks a Chroma vector database service with various operations:
- Collection creation
- Document insertion (with embeddings)
- Similarity search queries
- Metadata filtering
- Performance metrics collection

The script measures latency, throughput, and success rates for vector operations.
"""

import os
import sys
import time
import json
import argparse
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import traceback
import subprocess

# Try to install required packages if not available
def install_and_import(package_name: str, import_name: str = None):
    """Install package if not available and import it"""
    if import_name is None:
        import_name = package_name
    
    try:
        return __import__(import_name)
    except ImportError:
        print(f"Installing {package_name}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", package_name])
        return __import__(import_name)

# Install required packages
requests = install_and_import("requests")
numpy = install_and_import("numpy")

# Try to import chromadb client
try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    print("Installing chromadb...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "chromadb-client"])
    import chromadb
    from chromadb.config import Settings


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ChromaBenchmark:
    """Benchmark suite for Chroma vector database"""
    
    def __init__(self, endpoint: str, collection_name: str = "benchmark_collection"):
        """
        Initialize Chroma benchmark
        
        Args:
            endpoint: Chroma server endpoint (e.g., http://hostname:8000)
            collection_name: Name of the collection to use for benchmarking
        """
        self.endpoint = endpoint.rstrip('/')
        self.collection_name = collection_name
        self.client = None
        self.collection = None
        self.results = {
            'endpoint': endpoint,
            'collection_name': collection_name,
            'start_time': datetime.now().isoformat(),
            'operations': [],
            'summary': {}
        }
        
    def connect(self, max_retries: int = 5, retry_delay: int = 10) -> bool:
        """
        Connect to Chroma server with retries
        
        Args:
            max_retries: Maximum number of connection attempts
            retry_delay: Delay between retries in seconds
            
        Returns:
            True if connection successful, False otherwise
        """
        logger.info(f"Connecting to Chroma at {self.endpoint}")
        
        for attempt in range(max_retries):
            try:
                # Parse endpoint
                # Handle both http://hostname:port and http://hostname formats
                endpoint_parts = self.endpoint.split('://')
                if len(endpoint_parts) > 1:
                    host_port = endpoint_parts[1]
                else:
                    host_port = endpoint_parts[0]
                
                # Split host and port
                if ':' in host_port:
                    host = host_port.split(':')[0]
                    port = int(host_port.split(':')[1])
                else:
                    host = host_port
                    port = 8000  # Default Chroma port
                
                self.client = chromadb.HttpClient(host=host, port=port)
                
                # Test connection with heartbeat
                heartbeat = self.client.heartbeat()
                logger.info(f"Connected to Chroma successfully at {host}:{port}. Heartbeat: {heartbeat}")
                return True
                
            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"Failed to connect after {max_retries} attempts")
                    return False
        
        return False
    
    def setup_collection(self, embedding_dimension: int = 384) -> bool:
        """
        Create or get benchmark collection
        
        Args:
            embedding_dimension: Dimension of embedding vectors
            
        Returns:
            True if setup successful
        """
        try:
            logger.info(f"Setting up collection: {self.collection_name}")
            
            # Try to delete existing collection (for fresh benchmark)
            try:
                self.client.delete_collection(name=self.collection_name)
                logger.info(f"Deleted existing collection: {self.collection_name}")
            except Exception:
                pass  # Collection might not exist
            
            # Create new collection
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"benchmark": "true", "dimension": embedding_dimension}
            )
            
            logger.info(f"Created collection: {self.collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup collection: {e}")
            traceback.print_exc()
            return False
    
    def generate_embeddings(self, num_docs: int, dimension: int = 384) -> List[List[float]]:
        """
        Generate random embeddings for benchmark
        
        Args:
            num_docs: Number of embeddings to generate
            dimension: Dimension of each embedding
            
        Returns:
            List of embedding vectors
        """
        logger.info(f"Generating {num_docs} random embeddings of dimension {dimension}")
        
        # Generate random normalized embeddings
        embeddings = numpy.random.randn(num_docs, dimension).astype('float32')
        # Normalize to unit length
        norms = numpy.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings = embeddings / norms
        
        return embeddings.tolist()
    
    def benchmark_insertion(self, num_documents: int, batch_size: int, 
                          embedding_dimension: int) -> Dict[str, Any]:
        """
        Benchmark document insertion operations
        
        Args:
            num_documents: Total number of documents to insert
            batch_size: Number of documents per batch
            embedding_dimension: Dimension of embeddings
            
        Returns:
            Dictionary with benchmark results
        """
        logger.info(f"Benchmarking insertion: {num_documents} documents in batches of {batch_size}")
        
        results = {
            'operation': 'insertion',
            'total_documents': num_documents,
            'batch_size': batch_size,
            'batches': [],
            'total_time': 0,
            'documents_per_second': 0,
            'success': False
        }
        
        try:
            # Generate all embeddings upfront
            embeddings = self.generate_embeddings(num_documents, embedding_dimension)
            
            start_time = time.time()
            
            # Insert in batches
            for batch_idx in range(0, num_documents, batch_size):
                batch_start = time.time()
                
                end_idx = min(batch_idx + batch_size, num_documents)
                batch_embeddings = embeddings[batch_idx:end_idx]
                batch_ids = [f"doc_{i}" for i in range(batch_idx, end_idx)]
                batch_documents = [f"Document {i} content" for i in range(batch_idx, end_idx)]
                batch_metadatas = [{"index": i, "batch": batch_idx // batch_size} 
                                 for i in range(batch_idx, end_idx)]
                
                # Insert batch
                self.collection.add(
                    embeddings=batch_embeddings,
                    documents=batch_documents,
                    metadatas=batch_metadatas,
                    ids=batch_ids
                )
                
                batch_time = time.time() - batch_start
                results['batches'].append({
                    'batch_index': batch_idx // batch_size,
                    'size': len(batch_embeddings),
                    'time': batch_time,
                    'docs_per_second': len(batch_embeddings) / batch_time
                })
                
                logger.info(f"Inserted batch {batch_idx // batch_size + 1}: "
                          f"{len(batch_embeddings)} docs in {batch_time:.2f}s "
                          f"({len(batch_embeddings) / batch_time:.2f} docs/s)")
            
            total_time = time.time() - start_time
            results['total_time'] = total_time
            results['documents_per_second'] = num_documents / total_time
            results['success'] = True
            
            logger.info(f"Insertion completed: {num_documents} documents in {total_time:.2f}s "
                       f"({results['documents_per_second']:.2f} docs/s)")
            
        except Exception as e:
            logger.error(f"Insertion benchmark failed: {e}")
            traceback.print_exc()
            results['error'] = str(e)
        
        return results
    
    def benchmark_queries(self, num_queries: int, top_k: int, 
                        embedding_dimension: int) -> Dict[str, Any]:
        """
        Benchmark similarity search queries
        
        Args:
            num_queries: Number of queries to perform
            top_k: Number of results to retrieve per query
            embedding_dimension: Dimension of query embeddings
            
        Returns:
            Dictionary with benchmark results
        """
        logger.info(f"Benchmarking queries: {num_queries} queries with top_k={top_k}")
        
        results = {
            'operation': 'query',
            'num_queries': num_queries,
            'top_k': top_k,
            'queries': [],
            'total_time': 0,
            'queries_per_second': 0,
            'avg_latency': 0,
            'success': False
        }
        
        try:
            # Generate query embeddings
            query_embeddings = self.generate_embeddings(num_queries, embedding_dimension)
            
            start_time = time.time()
            latencies = []
            
            # Perform queries
            for i, query_embedding in enumerate(query_embeddings):
                query_start = time.time()
                
                query_results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=top_k
                )
                
                query_time = time.time() - query_start
                latencies.append(query_time)
                
                results['queries'].append({
                    'query_index': i,
                    'latency': query_time,
                    'results_count': len(query_results['ids'][0]) if query_results['ids'] else 0
                })
                
                if (i + 1) % 10 == 0:
                    logger.info(f"Completed {i + 1}/{num_queries} queries")
            
            total_time = time.time() - start_time
            results['total_time'] = total_time
            results['queries_per_second'] = num_queries / total_time
            results['avg_latency'] = sum(latencies) / len(latencies)
            results['min_latency'] = min(latencies)
            results['max_latency'] = max(latencies)
            results['p95_latency'] = numpy.percentile(latencies, 95)
            results['p99_latency'] = numpy.percentile(latencies, 99)
            results['success'] = True
            
            logger.info(f"Query benchmark completed: {num_queries} queries in {total_time:.2f}s "
                       f"({results['queries_per_second']:.2f} queries/s, "
                       f"avg latency: {results['avg_latency']*1000:.2f}ms)")
            
        except Exception as e:
            logger.error(f"Query benchmark failed: {e}")
            traceback.print_exc()
            results['error'] = str(e)
        
        return results
    
    def run_benchmark(self, num_documents: int, embedding_dimension: int,
                     batch_size: int, num_queries: int, top_k: int) -> Dict[str, Any]:
        """
        Run complete benchmark suite
        
        Args:
            num_documents: Number of documents to insert
            embedding_dimension: Dimension of embeddings
            batch_size: Batch size for insertions
            num_queries: Number of queries to perform
            top_k: Number of results per query
            
        Returns:
            Complete benchmark results
        """
        logger.info("Starting Chroma benchmark suite")
        
        # Setup collection
        if not self.setup_collection(embedding_dimension):
            self.results['error'] = "Failed to setup collection"
            return self.results
        
        # Run insertion benchmark
        insertion_results = self.benchmark_insertion(
            num_documents, batch_size, embedding_dimension
        )
        self.results['operations'].append(insertion_results)
        
        # Run query benchmark
        query_results = self.benchmark_queries(
            num_queries, top_k, embedding_dimension
        )
        self.results['operations'].append(query_results)
        
        # Generate summary
        self.results['summary'] = {
            'total_documents_inserted': num_documents if insertion_results['success'] else 0,
            'insertion_throughput': insertion_results.get('documents_per_second', 0),
            'total_queries_executed': num_queries if query_results['success'] else 0,
            'query_throughput': query_results.get('queries_per_second', 0),
            'avg_query_latency_ms': query_results.get('avg_latency', 0) * 1000,
            'p95_query_latency_ms': query_results.get('p95_latency', 0) * 1000,
            'p99_query_latency_ms': query_results.get('p99_latency', 0) * 1000,
        }
        
        self.results['end_time'] = datetime.now().isoformat()
        
        logger.info("Benchmark suite completed")
        logger.info(f"Summary: {json.dumps(self.results['summary'], indent=2)}")
        
        return self.results
    
    def save_results(self, output_file: str):
        """Save benchmark results to JSON file"""
        try:
            with open(output_file, 'w') as f:
                json.dump(self.results, f, indent=2)
            logger.info(f"Results saved to {output_file}")
        except Exception as e:
            logger.error(f"Failed to save results: {e}")


def main():
    """Main benchmark execution"""
    parser = argparse.ArgumentParser(description='Chroma Vector Database Benchmark')
    parser.add_argument('--endpoint', required=True, help='Chroma service endpoint')
    parser.add_argument('--collection-name', default='benchmark_collection',
                       help='Collection name for benchmark')
    parser.add_argument('--num-documents', type=int, default=1000,
                       help='Number of documents to insert')
    parser.add_argument('--embedding-dimension', type=int, default=384,
                       help='Dimension of embeddings')
    parser.add_argument('--batch-size', type=int, default=100,
                       help='Batch size for insertions')
    parser.add_argument('--num-queries', type=int, default=100,
                       help='Number of queries to perform')
    parser.add_argument('--top-k', type=int, default=10,
                       help='Number of results per query')
    parser.add_argument('--concurrent-operations', type=int, default=1,
                       help='Number of concurrent operations (currently not used)')
    parser.add_argument('--output-file', default='/tmp/chroma_benchmark_results.json',
                       help='Output file for results')
    parser.add_argument('--wait-for-service', type=int, default=120,
                       help='Maximum seconds to wait for service')
    
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info("Chroma Vector Database Benchmark")
    logger.info("=" * 80)
    logger.info(f"Endpoint: {args.endpoint}")
    logger.info(f"Collection: {args.collection_name}")
    logger.info(f"Documents: {args.num_documents}")
    logger.info(f"Embedding dimension: {args.embedding_dimension}")
    logger.info(f"Batch size: {args.batch_size}")
    logger.info(f"Queries: {args.num_queries}")
    logger.info(f"Top-k: {args.top_k}")
    logger.info("=" * 80)
    
    # Initialize benchmark
    benchmark = ChromaBenchmark(args.endpoint, args.collection_name)
    
    # Connect to service
    if not benchmark.connect(max_retries=args.wait_for_service // 10, retry_delay=10):
        logger.error("Failed to connect to Chroma service")
        sys.exit(1)
    
    # Run benchmark
    results = benchmark.run_benchmark(
        num_documents=args.num_documents,
        embedding_dimension=args.embedding_dimension,
        batch_size=args.batch_size,
        num_queries=args.num_queries,
        top_k=args.top_k
    )
    
    # Save results
    benchmark.save_results(args.output_file)
    
    # Print summary
    print("\n" + "=" * 80)
    print("BENCHMARK SUMMARY")
    print("=" * 80)
    print(json.dumps(results['summary'], indent=2))
    print("=" * 80)
    
    logger.info("Benchmark completed successfully")


if __name__ == '__main__':
    main()
