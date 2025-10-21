#!/usr/bin/env python3
"""
Redis Benchmark Script

This script benchmarks a Redis service with basic operations:
- SET operations (write performance)
- GET operations (read performance)  
- DEL operations (delete performance)
- Memory usage tracking
- Optional persistence performance testing

The script measures latency, throughput, and memory consumption.
Results are printed to stdout (captured in SLURM logs) and optionally saved to JSON.
"""

import os
import sys
import time
import json
import argparse
import logging
import statistics
import subprocess
from typing import List, Dict, Any, Optional
from datetime import datetime

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
redis = install_and_import("redis")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RedisBenchmark:
    """Benchmark suite for Redis in-memory database"""
    
    def __init__(self, endpoint: str, password: Optional[str] = None):
        """
        Initialize Redis benchmark
        
        Args:
            endpoint: Redis server endpoint (host:port format)
            password: Optional Redis password for authentication
        """
        self.endpoint = endpoint
        self.password = password
        self.client = None
        
    def connect(self, max_retries: int = 12, retry_delay: int = 5) -> bool:
        """
        Connect to Redis server with retries
        
        Args:
            max_retries: Maximum number of connection attempts
            retry_delay: Delay between retries in seconds
            
        Returns:
            True if connection successful, False otherwise
        """
        logger.info(f"Connecting to Redis at {self.endpoint}")
        
        for attempt in range(max_retries):
            try:
                # Parse endpoint
                if ':' in self.endpoint:
                    host, port = self.endpoint.split(':')
                    port = int(port)
                else:
                    host = self.endpoint
                    port = 6379
                
                # Create Redis client
                self.client = redis.Redis(
                    host=host,
                    port=port,
                    password=self.password,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                
                # Test connection
                self.client.ping()
                logger.info(f"✓ Connected to Redis successfully at {host}:{port}")
                
                # Get server info
                info = self.client.info('server')
                logger.info(f"✓ Redis version: {info.get('redis_version', 'unknown')}")
                
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
    
    def get_memory_info(self) -> Dict[str, Any]:
        """Get current memory usage from Redis INFO"""
        try:
            info = self.client.info('memory')
            return {
                'used_memory': info.get('used_memory', 0),
                'used_memory_human': info.get('used_memory_human', '0B'),
                'used_memory_peak': info.get('used_memory_peak', 0),
                'used_memory_peak_human': info.get('used_memory_peak_human', '0B'),
                'mem_fragmentation_ratio': info.get('mem_fragmentation_ratio', 0)
            }
        except Exception as e:
            logger.error(f"Error getting memory info: {e}")
            return {}
    
    def benchmark_set_operations(self, num_operations: int, key_size: int, 
                                 value_size: int) -> Dict[str, Any]:
        """
        Benchmark SET operations
        
        Args:
            num_operations: Number of SET operations to perform
            key_size: Size of keys in bytes
            value_size: Size of values in bytes
            
        Returns:
            Dictionary with benchmark results
        """
        logger.info(f"Benchmarking SET operations: {num_operations} operations")
        
        # Generate test data
        key_prefix = "benchmark_key_"
        value = "x" * value_size
        
        # Warmup
        for i in range(min(100, num_operations)):
            self.client.set(f"{key_prefix}warmup_{i}", value)
        
        # Start benchmark
        start_time = time.time()
        latencies = []
        
        for i in range(num_operations):
            op_start = time.time()
            self.client.set(f"{key_prefix}{i}", value)
            latency = time.time() - op_start
            latencies.append(latency)
            
            if (i + 1) % 1000 == 0:
                logger.info(f"  Completed {i + 1}/{num_operations} SET operations")
        
        total_time = time.time() - start_time
        ops_per_sec = num_operations / total_time
        
        results = {
            'operation': 'SET',
            'num_operations': num_operations,
            'total_time': total_time,
            'operations_per_second': ops_per_sec,
            'latency_mean_ms': statistics.mean(latencies) * 1000,
            'latency_median_ms': statistics.median(latencies) * 1000,
            'latency_p95_ms': (statistics.quantiles(latencies, n=20)[18] if len(latencies) > 20 else max(latencies)) * 1000,
            'latency_p99_ms': (statistics.quantiles(latencies, n=100)[98] if len(latencies) > 100 else max(latencies)) * 1000,
        }
        
        logger.info(f"✓ SET: {ops_per_sec:.2f} ops/sec, avg latency: {results['latency_mean_ms']:.3f} ms")
        return results
    
    def benchmark_get_operations(self, num_operations: int, key_prefix: str = "benchmark_key_") -> Dict[str, Any]:
        """
        Benchmark GET operations
        
        Args:
            num_operations: Number of GET operations to perform
            key_prefix: Prefix for keys to retrieve
            
        Returns:
            Dictionary with benchmark results
        """
        logger.info(f"Benchmarking GET operations: {num_operations} operations")
        
        # Warmup
        for i in range(min(100, num_operations)):
            self.client.get(f"{key_prefix}{i}")
        
        # Start benchmark
        start_time = time.time()
        latencies = []
        cache_hits = 0
        
        for i in range(num_operations):
            op_start = time.time()
            value = self.client.get(f"{key_prefix}{i}")
            latency = time.time() - op_start
            latencies.append(latency)
            
            if value is not None:
                cache_hits += 1
            
            if (i + 1) % 1000 == 0:
                logger.info(f"  Completed {i + 1}/{num_operations} GET operations")
        
        total_time = time.time() - start_time
        ops_per_sec = num_operations / total_time
        cache_hit_rate = (cache_hits / num_operations) * 100
        
        results = {
            'operation': 'GET',
            'num_operations': num_operations,
            'total_time': total_time,
            'operations_per_second': ops_per_sec,
            'cache_hit_rate': cache_hit_rate,
            'latency_mean_ms': statistics.mean(latencies) * 1000,
            'latency_median_ms': statistics.median(latencies) * 1000,
            'latency_p95_ms': (statistics.quantiles(latencies, n=20)[18] if len(latencies) > 20 else max(latencies)) * 1000,
            'latency_p99_ms': (statistics.quantiles(latencies, n=100)[98] if len(latencies) > 100 else max(latencies)) * 1000,
        }
        
        logger.info(f"✓ GET: {ops_per_sec:.2f} ops/sec, cache hit rate: {cache_hit_rate:.1f}%")
        return results
    
    def benchmark_del_operations(self, num_operations: int, key_prefix: str = "benchmark_key_") -> Dict[str, Any]:
        """
        Benchmark DEL operations
        
        Args:
            num_operations: Number of DEL operations to perform
            key_prefix: Prefix for keys to delete
            
        Returns:
            Dictionary with benchmark results
        """
        logger.info(f"Benchmarking DEL operations: {num_operations} operations")
        
        # Start benchmark
        start_time = time.time()
        latencies = []
        
        for i in range(num_operations):
            op_start = time.time()
            self.client.delete(f"{key_prefix}{i}")
            latency = time.time() - op_start
            latencies.append(latency)
            
            if (i + 1) % 1000 == 0:
                logger.info(f"  Completed {i + 1}/{num_operations} DEL operations")
        
        total_time = time.time() - start_time
        ops_per_sec = num_operations / total_time
        
        results = {
            'operation': 'DEL',
            'num_operations': num_operations,
            'total_time': total_time,
            'operations_per_second': ops_per_sec,
            'latency_mean_ms': statistics.mean(latencies) * 1000,
            'latency_median_ms': statistics.median(latencies) * 1000,
            'latency_p95_ms': (statistics.quantiles(latencies, n=20)[18] if len(latencies) > 20 else max(latencies)) * 1000,
            'latency_p99_ms': (statistics.quantiles(latencies, n=100)[98] if len(latencies) > 100 else max(latencies)) * 1000,
        }
        
        logger.info(f"✓ DEL: {ops_per_sec:.2f} ops/sec, avg latency: {results['latency_mean_ms']:.3f} ms")
        return results
    
    def benchmark_persistence(self) -> Dict[str, Any]:
        """
        Benchmark persistence operations (BGSAVE and AOF rewrite if enabled)
        
        Returns:
            Dictionary with benchmark results
        """
        logger.info("Benchmarking persistence operations...")
        
        results = {'operation': 'PERSISTENCE'}
        
        try:
            # Test BGSAVE
            logger.info("  Testing BGSAVE...")
            start_time = time.time()
            self.client.bgsave()
            
            # Wait for BGSAVE to complete
            while True:
                info = self.client.info('persistence')
                if info.get('rdb_bgsave_in_progress', 0) == 0:
                    break
                time.sleep(0.1)
            
            bgsave_time = time.time() - start_time
            results['bgsave_time_sec'] = bgsave_time
            logger.info(f"  ✓ BGSAVE completed in {bgsave_time:.2f} seconds")
            
            # Test AOF rewrite if AOF is enabled
            info = self.client.info('persistence')
            if info.get('aof_enabled', 0) == 1:
                logger.info("  Testing AOF REWRITE...")
                start_time = time.time()
                self.client.bgrewriteaof()
                
                # Wait for AOF rewrite to complete
                while True:
                    info = self.client.info('persistence')
                    if info.get('aof_rewrite_in_progress', 0) == 0:
                        break
                    time.sleep(0.1)
                
                aof_rewrite_time = time.time() - start_time
                results['aof_rewrite_time_sec'] = aof_rewrite_time
                logger.info(f"  ✓ AOF REWRITE completed in {aof_rewrite_time:.2f} seconds")
            else:
                logger.info("  AOF is disabled, skipping AOF rewrite test")
            
        except Exception as e:
            logger.error(f"Persistence benchmark failed: {e}")
            results['error'] = str(e)
        
        return results


def main():
    """Main benchmark execution"""
    parser = argparse.ArgumentParser(description='Redis Benchmark Client')
    parser.add_argument('--endpoint', required=True, help='Redis service endpoint (host:port)')
    parser.add_argument('--password', default=None, help='Redis password (if authentication enabled)')
    parser.add_argument('--num-operations', type=int, default=10000,
                       help='Number of operations for each test')
    parser.add_argument('--key-size', type=int, default=10,
                       help='Size of keys in bytes')
    parser.add_argument('--value-size', type=int, default=100,
                       help='Size of values in bytes')
    parser.add_argument('--test-persistence', action='store_true',
                       help='Test persistence operations (BGSAVE, AOF)')
    parser.add_argument('--output-file', default='/tmp/redis_benchmark_results.json',
                       help='Output file for results (optional)')
    parser.add_argument('--wait-for-service', type=int, default=60,
                       help='Wait time for service to be ready (seconds)')
    
    args = parser.parse_args()
    
    # Print configuration
    print("=" * 80)
    print("REDIS BENCHMARK - Configuration")
    print("=" * 80)
    print(f"Endpoint: {args.endpoint}")
    print(f"Operations per test: {args.num_operations}")
    print(f"Key size: {args.key_size} bytes")
    print(f"Value size: {args.value_size} bytes")
    print(f"Test persistence: {args.test_persistence}")
    print("=" * 80)
    print()
    
    # Initialize benchmark
    benchmark = RedisBenchmark(args.endpoint, args.password)
    
    # Connect to service
    if not benchmark.connect(max_retries=args.wait_for_service // 5, retry_delay=5):
        logger.error("Failed to connect to Redis service")
        return 1
    
    print()
    print("=" * 80)
    print("STARTING BENCHMARK")
    print("=" * 80)
    print()
    
    # Get initial memory info
    initial_memory = benchmark.get_memory_info()
    logger.info(f"Initial memory: {initial_memory.get('used_memory_human', '0B')}")
    
    # Run SET benchmark
    set_results = benchmark.benchmark_set_operations(
        args.num_operations, args.key_size, args.value_size
    )
    
    # Get memory after SET
    after_set_memory = benchmark.get_memory_info()
    logger.info(f"Memory after SET: {after_set_memory.get('used_memory_human', '0B')}")
    
    # Run GET benchmark
    get_results = benchmark.benchmark_get_operations(args.num_operations)
    
    # Run DEL benchmark
    del_results = benchmark.benchmark_del_operations(args.num_operations)
    
    # Get final memory
    final_memory = benchmark.get_memory_info()
    logger.info(f"Final memory: {final_memory.get('used_memory_human', '0B')}")
    
    # Test persistence if requested
    persistence_results = None
    if args.test_persistence:
        print()
        persistence_results = benchmark.benchmark_persistence()
    
    # Print comprehensive summary
    print()
    print("=" * 80)
    print("BENCHMARK RESULTS SUMMARY")
    print("=" * 80)
    print()
    print(f"Total Operations: {args.num_operations * 3} (SET + GET + DEL)")
    print()
    print("SET Operations:")
    print(f"  Throughput:    {set_results['operations_per_second']:>10.2f} ops/sec")
    print(f"  Avg Latency:   {set_results['latency_mean_ms']:>10.3f} ms")
    print(f"  P95 Latency:   {set_results['latency_p95_ms']:>10.3f} ms")
    print(f"  P99 Latency:   {set_results['latency_p99_ms']:>10.3f} ms")
    print()
    print("GET Operations:")
    print(f"  Throughput:    {get_results['operations_per_second']:>10.2f} ops/sec")
    print(f"  Cache Hit Rate:{get_results['cache_hit_rate']:>10.1f}%")
    print(f"  Avg Latency:   {get_results['latency_mean_ms']:>10.3f} ms")
    print(f"  P95 Latency:   {get_results['latency_p95_ms']:>10.3f} ms")
    print(f"  P99 Latency:   {get_results['latency_p99_ms']:>10.3f} ms")
    print()
    print("DEL Operations:")
    print(f"  Throughput:    {del_results['operations_per_second']:>10.2f} ops/sec")
    print(f"  Avg Latency:   {del_results['latency_mean_ms']:>10.3f} ms")
    print(f"  P95 Latency:   {del_results['latency_p95_ms']:>10.3f} ms")
    print(f"  P99 Latency:   {del_results['latency_p99_ms']:>10.3f} ms")
    print()
    print("Memory Usage:")
    print(f"  Initial:       {initial_memory.get('used_memory_human', '0B'):>10}")
    print(f"  After SET:     {after_set_memory.get('used_memory_human', '0B'):>10}")
    print(f"  Final:         {final_memory.get('used_memory_human', '0B'):>10}")
    print(f"  Peak:          {final_memory.get('used_memory_peak_human', '0B'):>10}")
    
    if persistence_results and 'bgsave_time_sec' in persistence_results:
        print()
        print("Persistence Performance:")
        print(f"  BGSAVE Time:   {persistence_results['bgsave_time_sec']:>10.2f} sec")
        if 'aof_rewrite_time_sec' in persistence_results:
            print(f"  AOF Rewrite:   {persistence_results['aof_rewrite_time_sec']:>10.2f} sec")
    
    print("=" * 80)
    
    # Save detailed results to JSON (optional)
    try:
        results_data = {
            'endpoint': args.endpoint,
            'timestamp': datetime.now().isoformat(),
            'configuration': {
                'num_operations': args.num_operations,
                'key_size': args.key_size,
                'value_size': args.value_size,
                'test_persistence': args.test_persistence
            },
            'results': {
                'set': set_results,
                'get': get_results,
                'del': del_results,
                'persistence': persistence_results
            },
            'memory': {
                'initial': initial_memory,
                'after_set': after_set_memory,
                'final': final_memory
            }
        }
        
        with open(args.output_file, 'w') as f:
            json.dump(results_data, f, indent=2)
        print(f"\nDetailed results saved to: {args.output_file}")
    except Exception as e:
        logger.warning(f"Could not save results to file: {e}")
        print("\n(Results not saved to file, but captured in SLURM logs above)")
    
    print("\n✓ Benchmark completed successfully!")
    return 0


if __name__ == '__main__':
    sys.exit(main())
