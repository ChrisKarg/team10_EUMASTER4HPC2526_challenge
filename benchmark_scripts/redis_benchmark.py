#!/usr/bin/env python3
"""
Redis Benchmark Script

This script is a wrapper around the native `redis-benchmark` CLI tool.
It executes the benchmark (optionally via Apptainer) and parses the CSV output into JSON.
It uses ONLY the Python Standard Library (no pip install required).
"""

import os
import sys
import json
import argparse
import subprocess
import shlex
import shutil
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

class RedisNativeBenchmark:
    """Adapter to run the native redis-benchmark CLI and parse its output."""

    def __init__(self, endpoint: str, password: Optional[str] = None):
        self.endpoint = endpoint
        self.password = password

    def _parse_endpoint(self) -> Tuple[str, int]:
        # Remove protocol if present
        clean_endpoint = self.endpoint.replace("redis://", "").replace("rediss://", "")
        
        if ':' in clean_endpoint:
            host, port_str = clean_endpoint.split(':', 1)
            return host, int(port_str)
        return clean_endpoint, 6379

    def _build_command(
        self,
        num_requests: int,
        clients: int,
        data_size: int,
        tests: Optional[List[str]] = None,
        pipeline: Optional[int] = None,
        threads: Optional[int] = None,
        extra_args: Optional[List[str]] = None,
        runner_tokens: Optional[List[str]] = None,
    ) -> List[str]:
        host, port = self._parse_endpoint()

        cmd: List[str] = []
        if runner_tokens:
            cmd.extend(runner_tokens)
        else:
            cmd.append("redis-benchmark")

        cmd.extend([
            "-h", host,
            "-p", str(port),
            "-n", str(num_requests),
            "-c", str(clients),
            "-d", str(data_size),
            "--csv",
        ])

        if self.password:
            cmd.extend(["-a", self.password])

        if tests:
            cmd.extend(["-t", ",".join(tests)])

        if pipeline and pipeline > 1:
            cmd.extend(["-P", str(pipeline)])

        if threads and threads > 0:
            cmd.extend(["--threads", str(threads)])

        if extra_args:
            cmd.extend(extra_args)

        return cmd

    @staticmethod
    def _parse_csv_output(stdout: str) -> Dict[str, Any]:
        """Parse redis-benchmark --csv output into a structured dict."""
        results: Dict[str, Any] = {"tests": {}}
        lines = [line.strip() for line in stdout.splitlines() if line.strip()]
        
        for line in lines:
            # Skip lines that don't look like CSV or are errors
            if ',' not in line:
                continue
                
            # Handle quotes if present
            if line.startswith('"') and line.endswith('"'):
                line = line.strip('"')
            
            parts = [p.strip('"') for p in line.split(',')]
            if not parts:
                continue
                
            test_name = parts[0]
            test_data: Dict[str, Any] = {}
            
            # Try to parse metrics
            metrics: List[float] = []
            for value in parts[1:]:
            try:
                    metrics.append(float(value))
            except ValueError:
                    test_data.setdefault("extra", []).append(value)
            
            if metrics:
                # First metric is requests per second
                test_data["requests_per_second"] = metrics[0]
                if len(metrics) > 1:
                    test_data["metrics"] = metrics[1:]
            
            results["tests"][test_name] = test_data
                
        return results

    def run(
        self,
        num_requests: int,
        clients: int,
        data_size: int,
        tests: Optional[List[str]] = None,
        pipeline: Optional[int] = None,
        threads: Optional[int] = None,
        extra_args: Optional[List[str]] = None,
        native_runner: Optional[str] = None,
        timeout_sec: int = 600,
    ) -> Dict[str, Any]:
        runner_tokens: Optional[List[str]] = None
        if native_runner:
            expanded = os.path.expandvars(native_runner)
            runner_tokens = shlex.split(expanded)

        cmd = self._build_command(
            num_requests=num_requests,
            clients=clients,
            data_size=data_size,
            tests=tests,
            pipeline=pipeline,
            threads=threads,
            extra_args=extra_args,
            runner_tokens=runner_tokens,
        )

        print(f"Executing: {' '.join(cmd)}")
        
        completed = None
        timed_out = False
        try:
            completed = subprocess.run(
                cmd,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,  # Same as text=True for Python 3.6+
                timeout=timeout_sec,
            )
        except subprocess.TimeoutExpired:
            timed_out = True

        stdout = (completed.stdout if completed else "") or ""
        stderr = (completed.stderr if completed else "") or ""
        returncode = completed.returncode if completed else 124

        parsed = self._parse_csv_output(stdout) if stdout else {"tests": {}}
        parsed["raw_output"] = stdout
        parsed["stderr"] = stderr
        parsed["returncode"] = returncode
        parsed["timed_out"] = timed_out
        parsed["command"] = cmd
        
        return parsed


def main():
    """Main benchmark execution"""
    parser = argparse.ArgumentParser(description='Redis Native Benchmark Wrapper')
    parser.add_argument('--endpoint', required=True, help='Redis service endpoint (host:port)')
    parser.add_argument('--password', default=None, help='Redis password')
    
    # Redis Benchmark specific arguments
    parser.add_argument('--num-operations', type=int, default=100000, help='Total number of requests (-n)')
    parser.add_argument('--clients', type=int, default=50, help='Number of parallel connections (-c)')
    parser.add_argument('--value-size', type=int, default=3, help='Data size of SET/GET value in bytes (-d)')
    parser.add_argument('--tests', default='ping,set,get,del', help='Comma separated list of tests (-t)')
    parser.add_argument('--pipeline', type=int, default=1, help='Pipeline <numreq> requests (-P)')
    parser.add_argument('--threads', type=int, default=0, help='Enable multi-thread mode (--threads)')
    
    # Wrapper configuration
    parser.add_argument('--native-runner', default=None, 
                       help='Command to wrap redis-benchmark (e.g. "apptainer exec image.sif")')
    parser.add_argument('--output-file', default='/tmp/redis_benchmark_results.json',
                       help='Output file for results JSON')
    parser.add_argument('--copy-to-shared', action='store_true', help='Copy to shared directory')
    parser.add_argument('--shared-dir', default=None, help='Target shared directory')
    
    args = parser.parse_args()

    print("=" * 80)
    print("REDIS BENCHMARK (Native Mode)")
    print("=" * 80)
    print(f"Endpoint: {args.endpoint}")
    print(f"Requests: {args.num_operations}")
    print(f"Clients:  {args.clients}")
    print(f"Payload:  {args.value_size} bytes")
    print(f"Pipeline: {args.pipeline}")
    print(f"Tests:    {args.tests}")
    print("=" * 80)

    benchmark = RedisNativeBenchmark(args.endpoint, args.password)
    
    # Run the benchmark
    results = benchmark.run(
        num_requests=args.num_operations,
        clients=args.clients,
        data_size=args.value_size,
        tests=[t.strip() for t in args.tests.split(',') if t.strip()],
        pipeline=args.pipeline,
        threads=args.threads,
        native_runner=args.native_runner
    )

    # Print Summary
    print("\nBenchmark Summary:")
    print("-" * 40)
    tests_data = results.get("tests", {})
    if tests_data:
        for test, data in tests_data.items():
            rps = data.get("requests_per_second", 0)
            print(f"{test:<10} : {rps:10.2f} req/sec")
    else:
        print("No structured results found.")
        if results.get("stderr"):
            print("\nSTDERR Output:")
            print(results["stderr"])
            
    print("-" * 40)

    # Construct final JSON payload
        payload = {
            'timestamp': datetime.now().isoformat(),
            'config': {
                'endpoint': args.endpoint,
            'requests': args.num_operations,
                'clients': args.clients,
            'payload_size': args.value_size,
            'pipeline': args.pipeline
            },
        'results': results
        }
        
    # Save to JSON
    try:
        with open(args.output_file, 'w') as f:
            json.dump(payload, f, indent=2)
        print(f"\nResults saved to: {args.output_file}")
    except Exception as e:
        print(f"Error saving results: {e}")

    # Optional Shared Copy
    if args.copy_to_shared:
        try:
            if args.shared_dir:
                dest_dir = os.path.expandvars(args.shared_dir)
            else:
                dest_dir = os.environ.get('SCRATCH') or os.path.expanduser('~')

            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir)
                
            job_id = os.environ.get('SLURM_JOB_ID', 'unknown')
            filename = f"redis_benchmark_{job_id}.json"
            dest_path = os.path.join(dest_dir, filename)
            
            shutil.copyfile(args.output_file, dest_path)
            print(f"Copy saved to: {dest_path}")
        except Exception as e:
            print(f"Error copying to shared: {e}")

    return results.get("returncode", 1)

if __name__ == '__main__':
    sys.exit(main())
