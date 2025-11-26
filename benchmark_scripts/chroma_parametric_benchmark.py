#!/usr/bin/env python3
"""
Chroma Parametric Benchmark Script

This script runs comprehensive parameter sweeps for Chroma vector database benchmarking.
It varies collection configurations, document counts, embedding dimensions, and batch sizes
to collect performance data for multiple scenarios across different configurations.

Uses the chromadb client library for vector operations.
"""

import os
import sys
import json
import argparse
import subprocess
import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

# Import the base benchmark class from the single-run script
sys.path.insert(0, os.path.dirname(__file__))
from chroma_benchmark import ChromaBenchmark


class ParametricBenchmarkSuite:
    """Runs parametric sweeps of Chroma benchmarks across multiple configurations."""
    
    def __init__(self, endpoint: str):
        self.endpoint = endpoint
        self.benchmark = ChromaBenchmark(endpoint)
        
    def run_sweep(
        self,
        num_documents_list: List[int],
        embedding_dimensions: List[int],
        batch_sizes: List[int],
        num_queries: int = 1000,
        top_k: int = 10,
        collection_prefix: str = "bench",
        wait_for_service: int = 60
    ) -> Dict[str, Any]:
        """
        Run a full parametric sweep across all parameter combinations.
        
        Args:
            num_documents_list: List of document counts to test
            embedding_dimensions: List of embedding dimensions to test
            batch_sizes: List of batch sizes to test
            num_queries: Number of queries per test
            top_k: Number of results per query
            collection_prefix: Prefix for collection names
            
        Returns:
            Dictionary containing all results organized by parameters
        """
        
        results = {
            'metadata': {
                'endpoint': self.endpoint,
                'start_time': datetime.now().isoformat(),
                'num_queries': num_queries,
                'top_k': top_k,
                'collection_prefix': collection_prefix
            },
            'parameter_ranges': {
                'num_documents': num_documents_list,
                'embedding_dimensions': embedding_dimensions,
                'batch_sizes': batch_sizes
            },
            'results': []
        }
        
        total_combinations = len(num_documents_list) * len(embedding_dimensions) * len(batch_sizes)
        current = 0
        
        print("=" * 80)
        print("CHROMA PARAMETRIC BENCHMARK SUITE")
        print("=" * 80)
        print(f"Endpoint:              {self.endpoint}")
        print(f"Document Counts:       {num_documents_list}")
        print(f"Embedding Dimensions:  {embedding_dimensions}")
        print(f"Batch Sizes:           {batch_sizes}")
        print(f"Queries per Test:      {num_queries}")
        print(f"Top-K:                 {top_k}")
        print(f"Total Runs:            {total_combinations}")
        print("=" * 80)
        print()
        
        for num_docs in num_documents_list:
            for embedding_dim in embedding_dimensions:
                for batch_size in batch_sizes:
                    current += 1
                    collection_name = f"{collection_prefix}_{num_docs}_{embedding_dim}_{batch_size}_{int(time.time())}"
                    
                    print(f"\n[{current}/{total_combinations}] Running: docs={num_docs}, "
                          f"dim={embedding_dim}, batch={batch_size}")
                    print("-" * 60)
                    
                    run_start = time.time()
                    
                    try:
                        # Connect to service (retry for this benchmark instance)
                        benchmark = ChromaBenchmark(self.endpoint, collection_name)
                        max_retries = max(3, wait_for_service // 10)  # Scale retries based on wait time
                        if not benchmark.connect(max_retries=max_retries, retry_delay=5):
                            raise Exception("Failed to connect to Chroma service")
                        
                        # Run the benchmark for this parameter combination
                        run_results = benchmark.run_benchmark(
                            num_documents=num_docs,
                            embedding_dimension=embedding_dim,
                            batch_size=batch_size,
                            num_queries=num_queries,
                            top_k=top_k
                        )
                        
                        run_duration = time.time() - run_start
                        
                        # Extract key metrics
                        summary = run_results.get('summary', {})
                        operations = run_results.get('operations', [])
                        
                        # Parse insertion and query results
                        insertion_data = None
                        query_data = None
                        
                        for op in operations:
                            if op.get('operation') == 'insertion':
                                insertion_data = op
                            elif op.get('operation') == 'query':
                                query_data = op
                        
                        # Store this run's results
                        results['results'].append({
                            'parameters': {
                                'num_documents': num_docs,
                                'embedding_dimension': embedding_dim,
                                'batch_size': batch_size,
                                'num_queries': num_queries,
                                'top_k': top_k
                            },
                            'insertion': {
                                'throughput_docs_per_sec': insertion_data.get('documents_per_second', 0) if insertion_data else 0,
                                'total_time_seconds': insertion_data.get('total_time', 0) if insertion_data else 0,
                                'success': insertion_data.get('success', False) if insertion_data else False
                            },
                            'query': {
                                'throughput_queries_per_sec': query_data.get('queries_per_second', 0) if query_data else 0,
                                'avg_latency_ms': query_data.get('avg_latency', 0) * 1000 if query_data else 0,
                                'p95_latency_ms': query_data.get('p95_latency', 0) * 1000 if query_data else 0,
                                'p99_latency_ms': query_data.get('p99_latency', 0) * 1000 if query_data else 0,
                                'min_latency_ms': query_data.get('min_latency', 0) * 1000 if query_data else 0,
                                'max_latency_ms': query_data.get('max_latency', 0) * 1000 if query_data else 0,
                                'total_time_seconds': query_data.get('total_time', 0) if query_data else 0,
                                'success': query_data.get('success', False) if query_data else False
                            },
                            'run_duration_seconds': round(run_duration, 2),
                            'timestamp': datetime.now().isoformat(),
                            'success': all([
                                insertion_data.get('success', False) if insertion_data else False,
                                query_data.get('success', False) if query_data else False
                            ])
                        })
                        
                        # Print summary for this run
                        print(f"  Completed in {run_duration:.1f}s")
                        if insertion_data:
                            print(f"    Insertion: {insertion_data.get('documents_per_second', 0):10,.0f} docs/s")
                        if query_data:
                            print(f"    Query:     {query_data.get('queries_per_second', 0):10,.1f} queries/s "
                                  f"(P99: {query_data.get('p99_latency', 0) * 1000:6.1f}ms)")
                        
                    except Exception as e:
                        print(f"  ERROR: {e}")
                        results['results'].append({
                            'parameters': {
                                'num_documents': num_docs,
                                'embedding_dimension': embedding_dim,
                                'batch_size': batch_size,
                                'num_queries': num_queries,
                                'top_k': top_k
                            },
                            'error': str(e),
                            'timestamp': datetime.now().isoformat(),
                            'success': False
                        })
                    
                    # Small delay between runs to let Chroma stabilize
                    time.sleep(2)
        
        results['metadata']['end_time'] = datetime.now().isoformat()
        results['metadata']['total_runs'] = total_combinations
        results['metadata']['successful_runs'] = sum(1 for r in results['results'] if r.get('success', False))
        
        return results


def main():
    """Main benchmark execution"""
    parser = argparse.ArgumentParser(description='Chroma Parametric Benchmark Suite')
    parser.add_argument('--endpoint', required=True, help='Chroma service endpoint (host:port)')
    
    # Parameter ranges (comma-separated lists)
    parser.add_argument('--num-documents', default='500,1000,2000,5000',
                       help='Comma-separated list of document counts (default: 500,1000,2000,5000)')
    parser.add_argument('--embedding-dimensions', default='192,384,768,1536',
                       help='Comma-separated list of embedding dimensions (default: 192,384,768,1536)')
    parser.add_argument('--batch-sizes', default='50,100,200,500',
                       help='Comma-separated list of batch sizes (default: 50,100,200,500)')
    
    # Test configuration
    parser.add_argument('--num-queries', type=int, default=1000,
                       help='Number of queries per test (default: 1000)')
    parser.add_argument('--top-k', type=int, default=10,
                       help='Number of results per query (default: 10)')
    
    # Output and utility options
    parser.add_argument('--output-file', default=None,
                       help='Output file for results JSON (default: ~/results/chroma_parametric_<JOB_ID>.json)')
    parser.add_argument('--collection-prefix', default='bench',
                       help='Prefix for collection names')
    parser.add_argument('--copy-to-shared', action='store_true', help='Copy to shared directory')
    parser.add_argument('--shared-dir', default=None, help='Target shared directory')
    
    # Orchestrator-specific options (for compatibility)
    parser.add_argument('--wait-for-service', type=int, default=60,
                       help='Wait time for service readiness (default: 60)')
    parser.add_argument('--parametric-mode', type=lambda x: x.lower() in ('true', '1', 'yes'),
                       default=True, help='Enable parametric mode (default: True)')
    
    args = parser.parse_args()
    
    # Set default output file if not specified
    if args.output_file is None:
        results_dir = os.path.expanduser("~/results")
        os.makedirs(results_dir, exist_ok=True)
        job_id = os.environ.get('SLURM_JOB_ID', 'unknown')
        args.output_file = os.path.join(results_dir, f"chroma_parametric_{job_id}.json")
    
    # Parse parameter ranges
    try:
        # Handle both comma-separated strings and lists
        if isinstance(args.num_documents, str):
            num_documents_list = [int(x.strip()) for x in args.num_documents.split(',')]
        else:
            num_documents_list = [int(x.strip()) for x in str(args.num_documents).split(',')]
            
        if isinstance(args.embedding_dimensions, str):
            embedding_dimensions = [int(x.strip()) for x in args.embedding_dimensions.split(',')]
        else:
            embedding_dimensions = [int(x.strip()) for x in str(args.embedding_dimensions).split(',')]
            
        if isinstance(args.batch_sizes, str):
            batch_sizes = [int(x.strip()) for x in args.batch_sizes.split(',')]
        else:
            batch_sizes = [int(x.strip()) for x in str(args.batch_sizes).split(',')]
    except ValueError as e:
        print(f"Error parsing parameter ranges: {e}")
        return 1
    
    # Create benchmark suite
    suite = ParametricBenchmarkSuite(args.endpoint)
    
    # Run the full sweep
    overall_start = time.time()
    results = suite.run_sweep(
        num_documents_list=num_documents_list,
        embedding_dimensions=embedding_dimensions,
        batch_sizes=batch_sizes,
        num_queries=args.num_queries,
        top_k=args.top_k,
        collection_prefix=args.collection_prefix,
        wait_for_service=args.wait_for_service
    )
    overall_duration = time.time() - overall_start
    
    # Add total duration
    results['metadata']['total_duration_seconds'] = round(overall_duration, 2)
    
    # Print final summary
    print("\n" + "=" * 80)
    print("BENCHMARK SUITE COMPLETED")
    print("=" * 80)
    print(f"Total Duration:    {overall_duration/60:.1f} minutes")
    print(f"Total Runs:        {results['metadata']['total_runs']}")
    print(f"Successful Runs:   {results['metadata']['successful_runs']}")
    print(f"Failed Runs:       {results['metadata']['total_runs'] - results['metadata']['successful_runs']}")
    print("=" * 80)
    
    # Save results to JSON
    try:
        with open(args.output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n✓ Results saved to: {args.output_file}")
    except Exception as e:
        print(f"\n✗ Failed to save results: {e}")
        return 1
    
    # ALWAYS copy to ~/results/ directory (for orchestrator discovery)
    try:
        import shutil
        
        results_dir = os.path.expanduser("~/results")
        if not os.path.exists(results_dir):
            os.makedirs(results_dir, exist_ok=True)
        
        # If output file is not already in ~/results/, copy it there
        if not args.output_file.startswith(results_dir):
            job_id = os.environ.get('SLURM_JOB_ID', 'unknown')
            filename = f"chroma_parametric_{job_id}.json"
            dest_path = os.path.join(results_dir, filename)
            
            shutil.copy(args.output_file, dest_path)
            print(f"✓ Results copied to: {dest_path}")
        else:
            print(f"✓ Results already in: {args.output_file}")
    except Exception as e:
        print(f"⚠️  Could not copy to ~/results/: {e}")
        # Don't return 1 here - still successful even if copy fails
    
    # Optional: Copy to additional shared directory
    if args.copy_to_shared:
        try:
            import shutil
            
            if args.shared_dir:
                dest_dir = os.path.expandvars(args.shared_dir)
            else:
                dest_dir = os.environ.get('SCRATCH') or os.path.expanduser('~')
            
            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir)
            
            job_id = os.environ.get('SLURM_JOB_ID', 'unknown')
            filename = f"chroma_parametric_{job_id}_shared.json"
            dest_path = os.path.join(dest_dir, filename)
            
            shutil.copy(args.output_file, dest_path)
            print(f"✓ Results also copied to: {dest_path}")
        except Exception as e:
            print(f"⚠️  Could not copy to additional shared directory: {e}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
