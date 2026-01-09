#!/usr/bin/env python3
"""
Redis Parametric Benchmark Script

This script runs comprehensive parameter sweeps for Redis benchmarking.
It varies clients, data sizes, and pipeline depths to collect performance data
for multiple operations across different configurations.

Uses ONLY the Python Standard Library (no pip install required).
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
# We'll reuse its logic for running individual benchmarks
sys.path.insert(0, os.path.dirname(__file__))
from redis_benchmark import RedisNativeBenchmark


class ParametricBenchmarkSuite:
    """Runs parametric sweeps of Redis benchmarks across multiple configurations."""
    
    def __init__(self, endpoint: str, native_runner: Optional[str] = None, password: Optional[str] = None):
        self.endpoint = endpoint
        self.native_runner = native_runner
        self.password = password
        self.benchmark = RedisNativeBenchmark(endpoint, password)
        
    def run_sweep(
        self,
        client_counts: List[int],
        data_sizes: List[int],
        pipeline_depths: List[int],
        operations_per_test: int = 100000,
        tests: List[str] = None
    ) -> Dict[str, Any]:
        """
        Run a full parametric sweep across all parameter combinations.
        
        Args:
            client_counts: List of concurrent client counts to test
            data_sizes: List of data payload sizes (bytes) to test
            pipeline_depths: List of pipeline depths to test
            operations_per_test: Number of operations per benchmark run
            tests: List of Redis operations to test
            
        Returns:
            Dictionary containing all results organized by parameters
        """
        if tests is None:
            tests = ['set', 'get', 'lpush', 'lpop', 'sadd', 'hset', 'spop', 'zadd', 'zpopmin']
        
        results = {
            'metadata': {
                'endpoint': self.endpoint,
                'start_time': datetime.now().isoformat(),
                'operations_per_test': operations_per_test,
                'tests': tests
            },
            'parameter_ranges': {
                'clients': client_counts,
                'data_sizes': data_sizes,
                'pipeline_depths': pipeline_depths
            },
            'results': []
        }
        
        total_combinations = len(client_counts) * len(data_sizes) * len(pipeline_depths)
        current = 0
        
        print("=" * 80)
        print("REDIS PARAMETRIC BENCHMARK SUITE")
        print("=" * 80)
        print(f"Endpoint:     {self.endpoint}")
        print(f"Tests:        {', '.join(tests)}")
        print(f"Clients:      {client_counts}")
        print(f"Data Sizes:   {data_sizes} bytes")
        print(f"Pipelines:    {pipeline_depths}")
        print(f"Total Runs:   {total_combinations}")
        print("=" * 80)
        print()
        
        for clients in client_counts:
            for data_size in data_sizes:
                for pipeline in pipeline_depths:
                    current += 1
                    print(f"\n[{current}/{total_combinations}] Running: clients={clients}, "
                          f"data_size={data_size}B, pipeline={pipeline}")
                    print("-" * 60)
                    
                    run_start = time.time()
                    
                    try:
                        # Run the benchmark for this parameter combination
                        run_results = self.benchmark.run(
                            num_requests=operations_per_test,
                            clients=clients,
                            data_size=data_size,
                            tests=tests,
                            pipeline=pipeline,
                            native_runner=self.native_runner
                        )
                        
                        run_duration = time.time() - run_start
                        
                        # Extract key metrics
                        test_results = {}
                        tests_data = run_results.get('tests', {})
                        
                        for test_name, test_data in tests_data.items():
                            if test_name == 'test':  # Skip header row
                                continue
                            
                            rps = test_data.get('requests_per_second', 0)
                            metrics = test_data.get('metrics', [])
                            
                            test_results[test_name] = {
                                'requests_per_second': rps,
                                'latency_avg_ms': metrics[0] if len(metrics) > 0 else None,
                                'latency_min_ms': metrics[1] if len(metrics) > 1 else None,
                                'latency_p50_ms': metrics[2] if len(metrics) > 2 else None,
                                'latency_p95_ms': metrics[3] if len(metrics) > 3 else None,
                                'latency_p99_ms': metrics[4] if len(metrics) > 4 else None,
                                'latency_max_ms': metrics[5] if len(metrics) > 5 else None,
                            }
                        
                        # Store this run's results
                        results['results'].append({
                            'parameters': {
                                'clients': clients,
                                'data_size_bytes': data_size,
                                'pipeline': pipeline
                            },
                            'tests': test_results,
                            'run_duration_seconds': round(run_duration, 2),
                            'timestamp': datetime.now().isoformat(),
                            'success': True
                        })
                        
                        # Print summary for this run
                        print(f"  Completed in {run_duration:.1f}s")
                        for test_name, test_metrics in test_results.items():
                            rps = test_metrics['requests_per_second']
                            if rps > 0:
                                print(f"    {test_name:12s}: {rps:12,.0f} req/s")
                        
                    except Exception as e:
                        print(f"  ERROR: {e}")
                        results['results'].append({
                            'parameters': {
                                'clients': clients,
                                'data_size_bytes': data_size,
                                'pipeline': pipeline
                            },
                            'error': str(e),
                            'timestamp': datetime.now().isoformat(),
                            'success': False
                        })
                    
                    # Small delay between runs to let Redis stabilize
                    time.sleep(2)
        
        results['metadata']['end_time'] = datetime.now().isoformat()
        results['metadata']['total_runs'] = total_combinations
        results['metadata']['successful_runs'] = sum(1 for r in results['results'] if r.get('success', False))
        
        return results


def main():
    """Main benchmark execution"""
    parser = argparse.ArgumentParser(description='Redis Parametric Benchmark Suite')
    parser.add_argument('--endpoint', required=True, help='Redis service endpoint (host:port)')
    parser.add_argument('--password', default=None, help='Redis password')
    
    # Parameter ranges (comma-separated lists)
    parser.add_argument('--clients', default='1,10,50,100,200,500',
                       help='Comma-separated list of client counts (default: 1,10,50,100,200,500)')
    parser.add_argument('--data-sizes', default='64,256,1024,4096,16384,65536',
                       help='Comma-separated list of data sizes in bytes (default: 64,256,1024,4096,16384,65536)')
    parser.add_argument('--pipelines', default='1,4,16,64,256',
                       help='Comma-separated list of pipeline depths (default: 1,4,16,64,256)')
    
    # Test configuration
    parser.add_argument('--operations', type=int, default=100000,
                       help='Operations per test (default: 100000)')
    parser.add_argument('--tests', default='set,get,lpush,lpop,sadd,hset,spop,zadd,zpopmin',
                       help='Comma-separated list of tests (default: set,get,lpush,lpop,sadd,hset,spop,zadd,zpopmin)')
    
    # Wrapper configuration
    parser.add_argument('--native-runner', default=None,
                       help='Command to wrap redis-benchmark (e.g. "apptainer exec image.sif")')
    parser.add_argument('--output-file', default='/tmp/redis_parametric_results.json',
                       help='Output file for results JSON')
    parser.add_argument('--copy-to-shared', action='store_true', help='Copy to shared directory')
    parser.add_argument('--shared-dir', default=None, help='Target shared directory')
    
    args = parser.parse_args()
    
    # Parse parameter ranges
    try:
        client_counts = [int(x.strip()) for x in args.clients.split(',')]
        data_sizes = [int(x.strip()) for x in args.data_sizes.split(',')]
        pipeline_depths = [int(x.strip()) for x in args.pipelines.split(',')]
        tests = [x.strip().lower() for x in args.tests.split(',')]
    except ValueError as e:
        print(f"Error parsing parameter ranges: {e}")
        return 1
    
    # Create benchmark suite
    suite = ParametricBenchmarkSuite(args.endpoint, args.native_runner, args.password)
    
    # Run the full sweep
    overall_start = time.time()
    results = suite.run_sweep(
        client_counts=client_counts,
        data_sizes=data_sizes,
        pipeline_depths=pipeline_depths,
        operations_per_test=args.operations,
        tests=tests
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
    
    # Optional: Copy to shared directory
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
            filename = f"redis_parametric_{job_id}.json"
            dest_path = os.path.join(dest_dir, filename)
            
            shutil.copy(args.output_file, dest_path)
            print(f"✓ Results copied to: {dest_path}")
        except Exception as e:
            print(f"✗ Failed to copy to shared directory: {e}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

