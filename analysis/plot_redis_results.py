#!/usr/bin/env python3
"""
Redis Parametric Benchmark Analysis and Plotting Script

This script analyzes Redis benchmark results and generates performance plots.
It loads parametric benchmark data and creates visualizations for:
- Throughput vs. number of clients
- Throughput vs. data size
- Throughput vs. pipeline depth
- Latency analysis
- Operation comparisons
- Performance heatmaps

Dependencies: matplotlib, numpy
Install: pip install matplotlib numpy
"""

import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any
import argparse

try:
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    import matplotlib.pyplot as plt
    import numpy as np
except ImportError:
    print("ERROR: This script requires matplotlib and numpy")
    print("Install with: pip install matplotlib numpy")
    sys.exit(1)


class RedisResultsAnalyzer:
    """Analyzer for Redis parametric benchmark results."""
    
    def __init__(self, results_dir: str = "results"):
        self.results_dir = Path(results_dir)
        self.data = []
        self.plots_dir = Path("analysis/plots")
        self.plots_dir.mkdir(parents=True, exist_ok=True)
        
    def load_results(self, pattern: str = "redis_parametric_*.json"):
        """Load all parametric benchmark result files."""
        result_files = list(self.results_dir.glob(pattern))
        
        if not result_files:
            print(f"WARNING: No result files found matching '{pattern}' in {self.results_dir}")
            return False
        
        print(f"Loading {len(result_files)} result file(s)...")
        
        for result_file in result_files:
            try:
                with open(result_file, 'r') as f:
                    data = json.load(f)
                    self.data.append({
                        'filename': result_file.name,
                        'data': data
                    })
                print(f"  ✓ Loaded {result_file.name}")
            except Exception as e:
                print(f"  ✗ Failed to load {result_file.name}: {e}")
        
        return len(self.data) > 0
    
    def extract_metrics(self):
        """Extract and organize metrics from all loaded results."""
        all_results = []
        
        for dataset in self.data:
            results = dataset['data'].get('results', [])
            for result in results:
                if not result.get('success', False):
                    continue
                
                params = result['parameters']
                tests = result['tests']
                
                for test_name, metrics in tests.items():
                    all_results.append({
                        'clients': params['clients'],
                        'data_size': params['data_size_bytes'],
                        'pipeline': params['pipeline'],
                        'test': test_name.upper(),
                        'rps': metrics['requests_per_second'],
                        'latency_avg': metrics.get('latency_avg_ms'),
                        'latency_p50': metrics.get('latency_p50_ms'),
                        'latency_p95': metrics.get('latency_p95_ms'),
                        'latency_p99': metrics.get('latency_p99_ms'),
                    })
        
        return all_results
    
    def plot_throughput_vs_clients(self, metrics, test_names=['SET', 'GET']):
        """Plot 1: Throughput vs Number of Clients (separate lines for data sizes)."""
        fig, axes = plt.subplots(1, len(test_names), figsize=(14, 6))
        if len(test_names) == 1:
            axes = [axes]
        
        for idx, test in enumerate(test_names):
            ax = axes[idx]
            
            # Filter for this test and pipeline=1
            test_data = [m for m in metrics if m['test'] == test and m['pipeline'] == 1]
            
            # Group by data size
            data_sizes = sorted(set(m['data_size'] for m in test_data))
            
            for data_size in data_sizes:
                size_data = [m for m in test_data if m['data_size'] == data_size]
                size_data.sort(key=lambda x: x['clients'])
                
                clients = [m['clients'] for m in size_data]
                rps = [m['rps'] for m in size_data]
                
                if data_size < 1024:
                    label = f"{data_size}B"
                else:
                    label = f"{data_size//1024}KB"
                
                ax.plot(clients, rps, marker='o', label=label, linewidth=2)
            
            ax.set_xlabel('Number of Clients', fontsize=12)
            ax.set_ylabel('Throughput (req/s)', fontsize=12)
            ax.set_title(f'{test} Throughput vs Clients', fontsize=14, fontweight='bold')
            ax.legend(title='Data Size', fontsize=10)
            ax.grid(True, alpha=0.3)
            ax.set_xscale('log')
        
        plt.tight_layout()
        output_path = self.plots_dir / "1_throughput_vs_clients.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"  ✓ Saved: {output_path}")
        plt.close()
    
    def plot_throughput_vs_datasize(self, metrics, test_names=['SET', 'GET']):
        """Plot 2: Throughput vs Data Size (separate lines for client counts)."""
        fig, axes = plt.subplots(1, len(test_names), figsize=(14, 6))
        if len(test_names) == 1:
            axes = [axes]
        
        for idx, test in enumerate(test_names):
            ax = axes[idx]
            
            # Filter for this test and pipeline=1
            test_data = [m for m in metrics if m['test'] == test and m['pipeline'] == 1]
            
            # Group by client count (select representative values)
            client_counts = [1, 50, 200, 500]
            
            for clients in client_counts:
                client_data = [m for m in test_data if m['clients'] == clients]
                client_data.sort(key=lambda x: x['data_size'])
                
                data_sizes = [m['data_size'] for m in client_data]
                rps = [m['rps'] for m in client_data]
                
                if data_sizes:
                    ax.plot(data_sizes, rps, marker='o', label=f"{clients} clients", linewidth=2)
            
            ax.set_xlabel('Data Size (bytes)', fontsize=12)
            ax.set_ylabel('Throughput (req/s)', fontsize=12)
            ax.set_title(f'{test} Throughput vs Data Size', fontsize=14, fontweight='bold')
            ax.legend(fontsize=10)
            ax.grid(True, alpha=0.3)
            ax.set_xscale('log')
        
        plt.tight_layout()
        output_path = self.plots_dir / "2_throughput_vs_datasize.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"  ✓ Saved: {output_path}")
        plt.close()
    
    def plot_throughput_vs_pipeline(self, metrics, test='GET'):
        """Plot 3: Throughput vs Pipeline Depth."""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Filter for this test and data_size=256
        test_data = [m for m in metrics if m['test'] == test and m['data_size'] == 256]
        
        # Group by client count
        client_counts = [10, 50, 200, 500]
        
        for clients in client_counts:
            client_data = [m for m in test_data if m['clients'] == clients]
            client_data.sort(key=lambda x: x['pipeline'])
            
            pipelines = [m['pipeline'] for m in client_data]
            rps = [m['rps'] for m in client_data]
            
            if pipelines:
                ax.plot(pipelines, rps, marker='o', label=f"{clients} clients", linewidth=2)
        
        ax.set_xlabel('Pipeline Depth', fontsize=12)
        ax.set_ylabel('Throughput (req/s)', fontsize=12)
        ax.set_title(f'{test} Throughput vs Pipeline Depth (256B)', fontsize=14, fontweight='bold')
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.set_xscale('log')
        
        plt.tight_layout()
        output_path = self.plots_dir / "3_throughput_vs_pipeline.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"  ✓ Saved: {output_path}")
        plt.close()
    
    def plot_latency_vs_clients(self, metrics, test_names=['SET', 'GET']):
        """Plot 4: P99 Latency vs Number of Clients."""
        fig, axes = plt.subplots(1, len(test_names), figsize=(14, 6))
        if len(test_names) == 1:
            axes = [axes]
        
        for idx, test in enumerate(test_names):
            ax = axes[idx]
            
            # Filter for this test, pipeline=1, data_size=256
            test_data = [m for m in metrics if m['test'] == test and m['pipeline'] == 1 
                        and m['data_size'] == 256 and m['latency_p99'] is not None]
            test_data.sort(key=lambda x: x['clients'])
            
            clients = [m['clients'] for m in test_data]
            latency_p99 = [m['latency_p99'] for m in test_data]
            
            ax.plot(clients, latency_p99, marker='o', linewidth=2, color='red')
            
            ax.set_xlabel('Number of Clients', fontsize=12)
            ax.set_ylabel('P99 Latency (ms)', fontsize=12)
            ax.set_title(f'{test} P99 Latency vs Clients (256B)', fontsize=14, fontweight='bold')
            ax.grid(True, alpha=0.3)
            ax.set_xscale('log')
        
        plt.tight_layout()
        output_path = self.plots_dir / "4_latency_vs_clients.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"  ✓ Saved: {output_path}")
        plt.close()
    
    def plot_heatmap_throughput(self, metrics, test='GET'):
        """Plot 5: Heatmap of Throughput (clients x data_size)."""
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Filter for this test and pipeline=1
        test_data = [m for m in metrics if m['test'] == test and m['pipeline'] == 1]
        
        # Get unique clients and data sizes
        clients_list = sorted(set(m['clients'] for m in test_data))
        data_sizes_list = sorted(set(m['data_size'] for m in test_data))
        
        # Create matrix
        matrix = np.zeros((len(data_sizes_list), len(clients_list)))
        
        for m in test_data:
            i = data_sizes_list.index(m['data_size'])
            j = clients_list.index(m['clients'])
            matrix[i, j] = m['rps']
        
        # Create heatmap
        im = ax.imshow(matrix, cmap='YlOrRd', aspect='auto')
        
        # Set ticks
        ax.set_xticks(range(len(clients_list)))
        ax.set_yticks(range(len(data_sizes_list)))
        ax.set_xticklabels(clients_list)
        ax.set_yticklabels([f"{s//1024}KB" if s >= 1024 else f"{s}B" for s in data_sizes_list])
        
        ax.set_xlabel('Number of Clients', fontsize=12)
        ax.set_ylabel('Data Size', fontsize=12)
        ax.set_title(f'{test} Throughput Heatmap (req/s)', fontsize=14, fontweight='bold')
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('Requests/sec', fontsize=11)
        
        # Add text annotations
        for i in range(len(data_sizes_list)):
            for j in range(len(clients_list)):
                if matrix[i, j] > 0:
                    text = ax.text(j, i, f'{int(matrix[i, j]/1000)}K',
                                 ha="center", va="center", color="black", fontsize=8)
        
        plt.tight_layout()
        output_path = self.plots_dir / "5_heatmap_throughput.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"  ✓ Saved: {output_path}")
        plt.close()
    
    def plot_operations_comparison(self, metrics):
        """Plot 6: Bar chart comparing different operations at optimal settings."""
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Use optimal settings: 100 clients, 256B, pipeline=1
        optimal_data = [m for m in metrics if m['clients'] == 100 
                       and m['data_size'] == 256 and m['pipeline'] == 1]
        
        # Group by test
        test_throughputs = {}
        for m in optimal_data:
            test = m['test']
            if test not in test_throughputs:
                test_throughputs[test] = []
            test_throughputs[test].append(m['rps'])
        
        # Calculate average throughput for each test
        tests = []
        throughputs = []
        for test in sorted(test_throughputs.keys()):
            tests.append(test)
            throughputs.append(np.mean(test_throughputs[test]))
        
        # Create bar chart
        bars = ax.bar(tests, throughputs, color='steelblue', edgecolor='black')
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(height):,}',
                   ha='center', va='bottom', fontsize=10)
        
        ax.set_xlabel('Operation', fontsize=12)
        ax.set_ylabel('Throughput (req/s)', fontsize=12)
        ax.set_title('Operation Throughput Comparison (100 clients, 256B, pipeline=1)', 
                    fontsize=14, fontweight='bold')
        ax.grid(True, axis='y', alpha=0.3)
        plt.xticks(rotation=45, ha='right')
        
        plt.tight_layout()
        output_path = self.plots_dir / "6_operations_comparison.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"  ✓ Saved: {output_path}")
        plt.close()
    
    def print_summary_statistics(self, metrics):
        """Print summary statistics to console."""
        print("\n" + "=" * 80)
        print("SUMMARY STATISTICS")
        print("=" * 80)
        
        # Peak throughput for each operation
        print("\nPeak Throughput by Operation:")
        print("-" * 60)
        test_names = sorted(set(m['test'] for m in metrics))
        for test in test_names:
            test_data = [m for m in metrics if m['test'] == test]
            if test_data:
                max_entry = max(test_data, key=lambda x: x['rps'])
                print(f"  {test:12s}: {max_entry['rps']:12,.0f} req/s "
                      f"(clients={max_entry['clients']}, size={max_entry['data_size']}B, "
                      f"pipeline={max_entry['pipeline']})")
        
        # Best configuration per operation
        print("\nOptimal Configuration (100 clients, 256B):")
        print("-" * 60)
        optimal = [m for m in metrics if m['clients'] == 100 and m['data_size'] == 256 
                  and m['pipeline'] == 1]
        for test in test_names:
            test_data = [m for m in optimal if m['test'] == test]
            if test_data:
                avg_rps = np.mean([m['rps'] for m in test_data])
                print(f"  {test:12s}: {avg_rps:12,.0f} req/s")
        
        print("=" * 80)
    
    def generate_all_plots(self):
        """Generate all analysis plots."""
        if not self.data:
            print("ERROR: No data loaded. Call load_results() first.")
            return False
        
        print("\nExtracting metrics...")
        metrics = self.extract_metrics()
        
        if not metrics:
            print("ERROR: No valid metrics found in loaded data.")
            return False
        
        print(f"Extracted {len(metrics)} metric data points.")
        
        print("\nGenerating plots...")
        
        self.plot_throughput_vs_clients(metrics, ['SET', 'GET'])
        self.plot_throughput_vs_datasize(metrics, ['SET', 'GET'])
        self.plot_throughput_vs_pipeline(metrics, 'GET')
        self.plot_latency_vs_clients(metrics, ['SET', 'GET'])
        self.plot_heatmap_throughput(metrics, 'GET')
        self.plot_operations_comparison(metrics)
        
        self.print_summary_statistics(metrics)
        
        print(f"\n✓ All plots saved to: {self.plots_dir}/")
        return True


def main():
    parser = argparse.ArgumentParser(description='Redis Benchmark Results Analysis and Plotting')
    parser.add_argument('--results-dir', default='results',
                       help='Directory containing result JSON files (default: results)')
    parser.add_argument('--pattern', default='redis_parametric_*.json',
                       help='File pattern to match (default: redis_parametric_*.json)')
    parser.add_argument('--output-dir', default='analysis/plots',
                       help='Directory to save plots (default: analysis/plots)')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("REDIS BENCHMARK ANALYSIS")
    print("=" * 80)
    
    analyzer = RedisResultsAnalyzer(args.results_dir)
    analyzer.plots_dir = Path(args.output_dir)
    analyzer.plots_dir.mkdir(parents=True, exist_ok=True)
    
    if not analyzer.load_results(args.pattern):
        print("\nERROR: No results loaded. Exiting.")
        return 1
    
    if not analyzer.generate_all_plots():
        print("\nERROR: Failed to generate plots.")
        return 1
    
    print("\n✓ Analysis complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())

