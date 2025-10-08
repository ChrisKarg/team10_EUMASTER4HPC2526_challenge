#!/usr/bin/env python3
"""
Ollama Benchmark Script
This script would be included in the benchmark_client.sif container
"""

import requests
import json
import time
import argparse
import logging
import statistics
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

class OllamaBenchmark:
    """Benchmark client for Ollama LLM service"""
    
    def __init__(self, endpoint: str, model: str = "llama2"):
        self.endpoint = endpoint.rstrip('/')
        self.model = model
        self.logger = logging.getLogger(__name__)
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # Debug information
        self.logger.info(f"=== OLLAMA BENCHMARK DEBUG INFO ===")
        self.logger.info(f"Target endpoint: {self.endpoint}")
        self.logger.info(f"Target model: {self.model}")
        self.logger.info(f"====================================")
    
    def test_connection(self) -> bool:
        """Test if Ollama service is accessible"""
        self.logger.info(f"Testing connection to: {self.endpoint}/api/tags")
        try:
            response = requests.get(f"{self.endpoint}/api/tags", timeout=10)
            self.logger.info(f"Connection test response: {response.status_code}")
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False
    
    def ensure_model_loaded(self) -> bool:
        """Ensure the model is loaded on the server"""
        try:
            # Try to load the model
            response = requests.post(
                f"{self.endpoint}/api/pull",
                json={"name": self.model},
                timeout=300  # 5 minutes timeout for model download
            )
            
            if response.status_code == 200:
                self.logger.info(f"Model {self.model} loaded successfully")
                return True
            else:
                self.logger.error(f"Failed to load model {self.model}: {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error loading model {self.model}: {e}")
            return False
    
    def single_inference_request(self, prompt: str, max_tokens: int = 200) -> Dict[str, Any]:
        """Make a single inference request and measure performance"""
        
        request_data = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": 0.7,
                "top_p": 0.9
            }
        }
        
        start_time = time.time()
        
        try:
            response = requests.post(
                f"{self.endpoint}/api/generate",
                json=request_data,
                timeout=120  # 2 minutes timeout
            )
            
            end_time = time.time()
            
            if response.status_code == 200:
                result = response.json()
                
                return {
                    "success": True,
                    "latency": end_time - start_time,
                    "prompt_tokens": len(prompt.split()),
                    "completion_tokens": len(result.get("response", "").split()),
                    "total_tokens": len(prompt.split()) + len(result.get("response", "").split()),
                    "response": result.get("response", "")
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "latency": end_time - start_time
                }
                
        except Exception as e:
            end_time = time.time()
            return {
                "success": False,
                "error": str(e),
                "latency": end_time - start_time
            }
    
    def run_benchmark(self, num_requests: int = 50, concurrent_requests: int = 5, 
                     prompt_length: int = 100, max_tokens: int = 200) -> Dict[str, Any]:
        """Run the benchmark with specified parameters"""
        
        self.logger.info(f"Starting Ollama benchmark: {num_requests} requests, "
                        f"{concurrent_requests} concurrent, {prompt_length} prompt tokens")
        
        # Generate test prompts
        base_prompt = "Explain the concept of artificial intelligence and its applications in modern technology. "
        prompts = [base_prompt * (prompt_length // len(base_prompt.split())) for _ in range(num_requests)]
        
        results = []
        start_time = time.time()
        
        # Run requests with thread pool for concurrency
        with ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
            future_to_prompt = {
                executor.submit(self.single_inference_request, prompt, max_tokens): i 
                for i, prompt in enumerate(prompts)
            }
            
            for future in as_completed(future_to_prompt):
                request_id = future_to_prompt[future]
                try:
                    result = future.result()
                    result['request_id'] = request_id
                    results.append(result)
                    
                    if result['success']:
                        self.logger.info(f"Request {request_id} completed in {result['latency']:.2f}s")
                    else:
                        self.logger.error(f"Request {request_id} failed: {result['error']}")
                        
                except Exception as e:
                    self.logger.error(f"Request {request_id} exception: {e}")
                    results.append({
                        "request_id": request_id,
                        "success": False,
                        "error": str(e),
                        "latency": 0
                    })
        
        end_time = time.time()
        
        # Calculate statistics
        successful_results = [r for r in results if r['success']]
        
        if successful_results:
            latencies = [r['latency'] for r in successful_results]
            total_tokens = [r['total_tokens'] for r in successful_results]
            
            stats = {
                "total_requests": num_requests,
                "successful_requests": len(successful_results),
                "failed_requests": num_requests - len(successful_results),
                "success_rate": len(successful_results) / num_requests * 100,
                "total_time": end_time - start_time,
                "requests_per_second": num_requests / (end_time - start_time),
                "latency_stats": {
                    "mean": statistics.mean(latencies),
                    "median": statistics.median(latencies),
                    "min": min(latencies),
                    "max": max(latencies),
                    "p95": sorted(latencies)[int(0.95 * len(latencies))] if len(latencies) > 0 else 0,
                    "p99": sorted(latencies)[int(0.99 * len(latencies))] if len(latencies) > 0 else 0
                },
                "throughput": {
                    "tokens_per_second": sum(total_tokens) / (end_time - start_time),
                    "average_tokens_per_request": statistics.mean(total_tokens)
                }
            }
        else:
            stats = {
                "total_requests": num_requests,
                "successful_requests": 0,
                "failed_requests": num_requests,
                "success_rate": 0,
                "total_time": end_time - start_time,
                "error": "All requests failed"
            }
        
        return {
            "benchmark_config": {
                "model": self.model,
                "endpoint": self.endpoint,
                "num_requests": num_requests,
                "concurrent_requests": concurrent_requests,
                "prompt_length": prompt_length,
                "max_tokens": max_tokens
            },
            "results": stats,
            "raw_results": results,
            "timestamp": time.time()
        }

def main():
    """Main function for command-line usage"""
    parser = argparse.ArgumentParser(description='Ollama Benchmark Client')
    parser.add_argument('--endpoint', default='http://localhost:11434', 
                       help='Ollama service endpoint')
    parser.add_argument('--model', default='llama2', 
                       help='Model to benchmark')
    parser.add_argument('--num-requests', type=int, default=50, 
                       help='Number of requests to make')
    parser.add_argument('--concurrent-requests', type=int, default=5, 
                       help='Number of concurrent requests')
    parser.add_argument('--prompt-length', type=int, default=100, 
                       help='Approximate prompt length in tokens')
    parser.add_argument('--max-tokens', type=int, default=200, 
                       help='Maximum tokens to generate')
    parser.add_argument('--output-file', default='ollama_benchmark_results.json', 
                       help='Output file for results')
    parser.add_argument('--wait-for-service', type=int, default=60, 
                       help='Wait time for service to be ready (seconds)')
    
    args = parser.parse_args()
    
    # Debug: Print all environment variables and arguments
    import os
    print("=== DEBUGGING INFORMATION ===")
    print(f"Command line arguments:")
    for arg, value in vars(args).items():
        print(f"  --{arg.replace('_', '-')}: {value}")
    
    print(f"\nEnvironment variables:")
    for key in sorted(os.environ.keys()):
        if any(keyword in key.upper() for keyword in ['OLLAMA', 'TARGET', 'SERVICE', 'HOST', 'ENDPOINT']):
            print(f"  {key}: {os.environ[key]}")
    
    print(f"\nNetwork debugging:")
    print(f"  Hostname: {os.uname().nodename if hasattr(os, 'uname') else 'unknown'}")
    print("==============================\n")
    
    # Initialize benchmark
    benchmark = OllamaBenchmark(args.endpoint, args.model)
    
    # Wait for service to be ready
    print(f"Waiting for Ollama service at {args.endpoint}...")
    max_wait = args.wait_for_service
    wait_time = 0
    
    while wait_time < max_wait:
        if benchmark.test_connection():
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
    if not benchmark.ensure_model_loaded():
        print("Failed to load model. Exiting.")
        return 1
    
    # Run benchmark
    print("Starting benchmark...")
    results = benchmark.run_benchmark(
        num_requests=args.num_requests,
        concurrent_requests=args.concurrent_requests,
        prompt_length=args.prompt_length,
        max_tokens=args.max_tokens
    )
    
    # Save results
    with open(args.output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print("\n" + "="*50)
    print("BENCHMARK RESULTS")
    print("="*50)
    
    stats = results['results']
    print(f"Total requests: {stats['total_requests']}")
    print(f"Successful requests: {stats['successful_requests']}")
    print(f"Success rate: {stats['success_rate']:.1f}%")
    print(f"Total time: {stats['total_time']:.2f}s")
    print(f"Requests/second: {stats['requests_per_second']:.2f}")
    
    if 'latency_stats' in stats:
        print(f"\nLatency Statistics:")
        print(f"  Mean: {stats['latency_stats']['mean']:.2f}s")
        print(f"  Median: {stats['latency_stats']['median']:.2f}s")
        print(f"  95th percentile: {stats['latency_stats']['p95']:.2f}s")
        print(f"  99th percentile: {stats['latency_stats']['p99']:.2f}s")
        
        print(f"\nThroughput:")
        print(f"  Tokens/second: {stats['throughput']['tokens_per_second']:.2f}")
        print(f"  Avg tokens/request: {stats['throughput']['average_tokens_per_request']:.1f}")
    
    print(f"\nResults saved to: {args.output_file}")
    return 0

if __name__ == "__main__":
    exit(main())