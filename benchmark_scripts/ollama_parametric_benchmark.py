#!/usr/bin/env python3
"""
Ollama Parametric Benchmark Script

This script runs comprehensive parameter sweeps for Ollama LLM benchmarking.
It varies concurrent requests, prompt lengths, and max token outputs to collect 
performance data across different configurations.

Uses standard libraries + requests for HTTP.
"""

import os
import sys
import json
import argparse
import time
from typing import List, Dict, Any, Optional
from datetime import datetime

# Import the base benchmark class
# Add both the script directory and current directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir:
    sys.path.insert(0, script_dir)
sys.path.insert(0, os.getcwd())

# Debug: Print search paths
print(f"DEBUG: Script location: {os.path.abspath(__file__)}")
print(f"DEBUG: Script directory: {script_dir}")
print(f"DEBUG: Current working directory: {os.getcwd()}")
print(f"DEBUG: Python path: {sys.path[:3]}")

try:
    from ollama_benchmark import OllamaBenchmark
    print("DEBUG: Successfully imported ollama_benchmark")
except ImportError as e:
    print(f"DEBUG: Initial import failed: {e}")
    # If import fails, try to find and import from the benchmark_scripts directory
    import importlib.util
    benchmark_script = None
    search_dirs = [script_dir, os.getcwd(), '/app', os.path.expanduser('~/benchmark_scripts')]
    
    print(f"DEBUG: Searching for ollama_benchmark.py in: {search_dirs}")
    for possible_dir in search_dirs:
        possible_path = os.path.join(possible_dir, 'ollama_benchmark.py')
        print(f"DEBUG: Checking {possible_path}... ", end='')
        if os.path.exists(possible_path):
            print("FOUND!")
            benchmark_script = possible_path
            break
        else:
            print("not found")
    
    # Also list files in /app to debug
    if os.path.exists('/app'):
        print(f"DEBUG: Files in /app: {os.listdir('/app')}")
    
    if benchmark_script:
        print(f"DEBUG: Loading from {benchmark_script}")
        spec = importlib.util.spec_from_file_location("ollama_benchmark", benchmark_script)
        ollama_benchmark = importlib.util.module_from_spec(spec)
        sys.modules["ollama_benchmark"] = ollama_benchmark
        spec.loader.exec_module(ollama_benchmark)
        OllamaBenchmark = ollama_benchmark.OllamaBenchmark
        print("DEBUG: Successfully loaded ollama_benchmark")
    else:
        print(f"ERROR: Could not find ollama_benchmark.py in any of the search directories")
        print(f"ERROR: Please ensure ollama_benchmark.py is in the same directory as this script")
        sys.exit(1)


class OllamaParametricBenchmarkSuite:
    """Runs parametric sweeps of Ollama benchmarks across multiple configurations."""
    
    def __init__(self, endpoint: str, model: str = "llama2"):
        self.endpoint = endpoint
        self.model = model
        self.benchmark = OllamaBenchmark(endpoint, model)
        
    def run_sweep(
        self,
        concurrent_requests_list: List[int],
        prompt_lengths: List[int],
        max_tokens_list: List[int],
        operations_per_test: int = 20
    ) -> Dict[str, Any]:
        """
        Run a full parametric sweep across all parameter combinations.
        
        Args:
            concurrent_requests_list: List of concurrent request counts to test
            prompt_lengths: List of prompt lengths (in tokens) to test
            max_tokens_list: List of max output tokens to test
            operations_per_test: Number of operations per benchmark run
            
        Returns:
            Dictionary containing all results organized by parameters
        """
        results = {
            'metadata': {
                'endpoint': self.endpoint,
                'model': self.model,
                'start_time': datetime.now().isoformat(),
                'operations_per_test': operations_per_test
            },
            'parameter_ranges': {
                'concurrent_requests': concurrent_requests_list,
                'prompt_lengths': prompt_lengths,
                'max_tokens': max_tokens_list
            },
            'results': []
        }
        
        total_combinations = (len(concurrent_requests_list) * 
                            len(prompt_lengths) * 
                            len(max_tokens_list))
        current = 0
        
        print("=" * 80)
        print("OLLAMA PARAMETRIC BENCHMARK SUITE")
        print("=" * 80)
        print(f"Endpoint:           {self.endpoint}")
        print(f"Model:              {self.model}")
        print(f"Concurrent Reqs:    {concurrent_requests_list}")
        print(f"Prompt Lengths:     {prompt_lengths}")
        print(f"Max Tokens:         {max_tokens_list}")
        print(f"Total Runs:         {total_combinations}")
        print("=" * 80)
        print()
        
        for concurrent in concurrent_requests_list:
            for prompt_len in prompt_lengths:
                for max_tokens in max_tokens_list:
                    current += 1
                    print(f"\n[{current}/{total_combinations}] Running: "
                          f"concurrent={concurrent}, prompt={prompt_len}, max_tokens={max_tokens}")
                    print("-" * 60)
                    
                    run_start = time.time()
                    
                    try:
                        # Run the benchmark for this parameter combination
                        run_results = self.benchmark.run_benchmark(
                            num_requests=operations_per_test,
                            concurrent_requests=concurrent,
                            prompt_length=prompt_len,
                            max_tokens=max_tokens
                        )
                        
                        run_duration = time.time() - run_start
                        
                        # Extract key metrics
                        stats = run_results.get('results', {})
                        
                        result_entry = {
                            'parameters': {
                                'concurrent_requests': concurrent,
                                'prompt_length': prompt_len,
                                'max_tokens': max_tokens
                            },
                            'metrics': {
                                'total_requests': stats.get('total_requests', 0),
                                'successful_requests': stats.get('successful_requests', 0),
                                'failed_requests': stats.get('failed_requests', 0),
                                'success_rate': stats.get('success_rate', 0),
                                'total_time': stats.get('total_time', 0),
                                'requests_per_second': stats.get('requests_per_second', 0),
                                'latency_mean': stats.get('latency_stats', {}).get('mean', 0),
                                'latency_median': stats.get('latency_stats', {}).get('median', 0),
                                'latency_min': stats.get('latency_stats', {}).get('min', 0),
                                'latency_max': stats.get('latency_stats', {}).get('max', 0),
                                'latency_p95': stats.get('latency_stats', {}).get('p95', 0),
                                'latency_p99': stats.get('latency_stats', {}).get('p99', 0),
                                'tokens_per_second': stats.get('throughput', {}).get('tokens_per_second', 0),
                                'avg_tokens_per_request': stats.get('throughput', {}).get('average_tokens_per_request', 0)
                            },
                            'run_duration_seconds': round(run_duration, 2),
                            'timestamp': datetime.now().isoformat(),
                            'success': stats.get('successful_requests', 0) > 0
                        }
                        
                        results['results'].append(result_entry)
                        
                        # Print summary for this run
                        print(f"  Completed in {run_duration:.1f}s")
                        print(f"    Requests/sec:       {result_entry['metrics']['requests_per_second']:.2f}")
                        print(f"    Tokens/sec:         {result_entry['metrics']['tokens_per_second']:.2f}")
                        print(f"    Latency (mean):     {result_entry['metrics']['latency_mean']:.2f}s")
                        print(f"    Latency (p95):      {result_entry['metrics']['latency_p95']:.2f}s")
                        print(f"    Success rate:       {result_entry['metrics']['success_rate']:.1f}%")
                        
                    except Exception as e:
                        print(f"  ERROR: {e}")
                        results['results'].append({
                            'parameters': {
                                'concurrent_requests': concurrent,
                                'prompt_length': prompt_len,
                                'max_tokens': max_tokens
                            },
                            'error': str(e),
                            'timestamp': datetime.now().isoformat(),
                            'success': False
                        })
                    
                    # Small delay between runs to let service stabilize
                    time.sleep(3)
        
        results['metadata']['end_time'] = datetime.now().isoformat()
        results['metadata']['total_runs'] = total_combinations
        results['metadata']['successful_runs'] = sum(1 for r in results['results'] if r.get('success', False))
        
        return results


def main():
    """Main benchmark execution"""
    parser = argparse.ArgumentParser(description='Ollama Parametric Benchmark Suite')
    parser.add_argument('--endpoint', required=True, help='Ollama service endpoint')
    parser.add_argument('--model', default='llama2', help='Model to benchmark')
    
    # Parameter ranges (comma-separated lists)
    # Support both --concurrent and --concurrent-requests for compatibility
    parser.add_argument('--concurrent', '--concurrent-requests', dest='concurrent',
                       default='1,2,5,10,20',
                       help='Comma-separated list of concurrent requests (default: 1,2,5,10,20)')
    parser.add_argument('--prompt-lengths', default='50,100,200,500',
                       help='Comma-separated list of prompt lengths in tokens (default: 50,100,200,500)')
    parser.add_argument('--max-tokens', default='50,100,200,500',
                       help='Comma-separated list of max output tokens (default: 50,100,200,500)')
    
    # Test configuration
    # Support both --operations and --operations-per-test for compatibility
    parser.add_argument('--operations', '--operations-per-test', dest='operations',
                       type=int, default=20,
                       help='Operations per test (default: 20)')
    
    # Output configuration
    parser.add_argument('--output-file', default='results/ollama_parametric_results.json',
                       help='Output file for results JSON')
    parser.add_argument('--copy-to-shared', action='store_true', 
                       help='Copy to shared directory (deprecated, use --shared-dir instead)')
    parser.add_argument('--shared-dir', default=None, 
                       help='Target shared directory (if set, results will be copied here)')
    parser.add_argument('--wait-for-service', type=int, default=60,
                       help='Wait time for service to be ready (seconds)')
    
    # Ignore orchestrator-specific flags
    parser.add_argument('--parametric-mode', action='store_true', 
                       help='Parametric mode flag (ignored, for compatibility)')
    
    args = parser.parse_args()
    
    # Parse parameter ranges
    try:
        concurrent_requests = [int(x.strip()) for x in args.concurrent.split(',')]
        prompt_lengths = [int(x.strip()) for x in args.prompt_lengths.split(',')]
        max_tokens_list = [int(x.strip()) for x in args.max_tokens.split(',')]
        # concurrent_requests = [1]
        # prompt_lengths = [50,100]
        # max_tokens_list = [50]
    except ValueError as e:
        print(f"Error parsing parameter ranges: {e}")
        return 1
    
    # Create benchmark suite
    suite = OllamaParametricBenchmarkSuite(args.endpoint, args.model)
    
    # Wait for service to be ready
    print(f"Waiting for Ollama service at {args.endpoint}...")
    max_wait = args.wait_for_service
    wait_time = 0
    
    while wait_time < max_wait:
        if suite.benchmark.test_connection():
            print("Service is ready!")
            break
        time.sleep(5)
        wait_time += 5
        print(f"Waiting... ({wait_time}/{max_wait}s)")
    else:
        print(f"Service not ready after {max_wait} seconds. Exiting.")
        return 1
    
    # Ensure model is loaded
    print(f"Loading model {args.model}...")
    if not suite.benchmark.ensure_model_loaded():
        print("Failed to load model. Continuing anyway...")
    
    # Run the full sweep
    overall_start = time.time()
    results = suite.run_sweep(
        concurrent_requests_list=concurrent_requests,
        prompt_lengths=prompt_lengths,
        max_tokens_list=max_tokens_list,
        operations_per_test=args.operations
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
    if args.shared_dir:
        try:
            import shutil
            
            dest_dir = os.path.expandvars(args.shared_dir)
            
            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir)
            
            job_id = os.environ.get('SLURM_JOB_ID', 'unknown')
            filename = f"ollama_parametric_{job_id}.json"
            dest_path = os.path.join(dest_dir, filename)
            
            shutil.copy(args.output_file, dest_path)
            print(f"✓ Results copied to: {dest_path}")
        except Exception as e:
            print(f"✗ Failed to copy to shared directory: {e}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
