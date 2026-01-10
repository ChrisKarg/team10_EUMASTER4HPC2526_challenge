#!/usr/bin/env python3
"""
Ollama Parametric Benchmark Analysis and Plotting Script

This script analyzes Ollama LLM benchmark results and generates performance plots.
It loads parametric benchmark data and creates visualizations for:
- Throughput (requests/sec) vs. concurrent requests
- Throughput (tokens/sec) vs. concurrent requests
- Latency vs. concurrent requests
- Throughput vs. prompt length
- Throughput vs. max tokens
- Performance heatmaps
- Latency distribution comparisons

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


class OllamaResultsAnalyzer:
    """Analyzer for Ollama parametric benchmark results."""
    
    def __init__(self, results_dir: str = "results"):
        self.results_dir = Path(results_dir)
        self.data = []
        self.plots_dir = Path("analysis/plotsOllama")
        self.plots_dir.mkdir(parents=True, exist_ok=True)
        
    def load_results(self, pattern: str = "ollama_parametric_*.json"):
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
                metrics = result['metrics']
                
                all_results.append({
                    'concurrent_requests': params['concurrent_requests'],
                    'prompt_length': params['prompt_length'],
                    'max_tokens': params['max_tokens'],
                    'requests_per_second': metrics.get('requests_per_second', 0),
                    'tokens_per_second': metrics.get('tokens_per_second', 0),
                    'avg_tokens_per_request': metrics.get('avg_tokens_per_request', 0),
                    'latency_mean': metrics.get('latency_mean', 0),
                    'latency_median': metrics.get('latency_median', 0),
                    'latency_min': metrics.get('latency_min', 0),
                    'latency_max': metrics.get('latency_max', 0),
                    'latency_p95': metrics.get('latency_p95', 0),
                    'latency_p99': metrics.get('latency_p99', 0),
                    'success_rate': metrics.get('success_rate', 0),
                    'successful_requests': metrics.get('successful_requests', 0),
                    'total_time': metrics.get('total_time', 0)
                })
        
        return all_results
    
    def plot_throughput_vs_concurrent(self, metrics):
        """Plot 1: Request and Token Throughput vs Concurrent Requests."""
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        
        # Filter for prompt_length=100, max_tokens=100
        filtered_data = [m for m in metrics if m['prompt_length'] == 100 and m['max_tokens'] == 100]
        
        if not filtered_data:
            print("  ⚠ Insufficient data for plot_throughput_vs_concurrent")
            return
        
        filtered_data.sort(key=lambda x: x['concurrent_requests'])
        
        concurrent = [m['concurrent_requests'] for m in filtered_data]
        req_per_sec = [m['requests_per_second'] for m in filtered_data]
        tok_per_sec = [m['tokens_per_second'] for m in filtered_data]
        
        # Plot 1a: Requests per second
        axes[0].plot(concurrent, req_per_sec, marker='o', linewidth=2, color='steelblue')
        axes[0].set_xlabel('Concurrent Requests', fontsize=12)
        axes[0].set_ylabel('Requests/sec', fontsize=12)
        axes[0].set_title('Request Throughput vs Concurrency\n(prompt=100, max_tokens=100)', 
                         fontsize=14, fontweight='bold')
        axes[0].grid(True, alpha=0.3)
        
        # Plot 1b: Tokens per second
        axes[1].plot(concurrent, tok_per_sec, marker='o', linewidth=2, color='darkorange')
        axes[1].set_xlabel('Concurrent Requests', fontsize=12)
        axes[1].set_ylabel('Tokens/sec', fontsize=12)
        axes[1].set_title('Token Throughput vs Concurrency\n(prompt=100, max_tokens=100)', 
                         fontsize=14, fontweight='bold')
        axes[1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        output_path = self.plots_dir / "1_throughput_vs_concurrent.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"  ✓ Saved: {output_path}")
        plt.close()
    
    def plot_latency_vs_concurrent(self, metrics):
        """Plot 2: Latency Percentiles vs Concurrent Requests."""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Filter for prompt_length=100, max_tokens=100
        filtered_data = [m for m in metrics if m['prompt_length'] == 100 and m['max_tokens'] == 100]
        
        if not filtered_data:
            print("  ⚠ Insufficient data for plot_latency_vs_concurrent")
            return
        
        filtered_data.sort(key=lambda x: x['concurrent_requests'])
        
        concurrent = [m['concurrent_requests'] for m in filtered_data]
        lat_mean = [m['latency_mean'] for m in filtered_data]
        lat_p95 = [m['latency_p95'] for m in filtered_data]
        lat_p99 = [m['latency_p99'] for m in filtered_data]
        
        ax.plot(concurrent, lat_mean, marker='o', label='Mean', linewidth=2)
        ax.plot(concurrent, lat_p95, marker='s', label='P95', linewidth=2)
        ax.plot(concurrent, lat_p99, marker='^', label='P99', linewidth=2)
        
        ax.set_xlabel('Concurrent Requests', fontsize=12)
        ax.set_ylabel('Latency (seconds)', fontsize=12)
        ax.set_title('Latency vs Concurrency (prompt=100, max_tokens=100)', 
                    fontsize=14, fontweight='bold')
        ax.legend(fontsize=11)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        output_path = self.plots_dir / "2_latency_vs_concurrent.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"  ✓ Saved: {output_path}")
        plt.close()
    
    def plot_throughput_vs_prompt_length(self, metrics):
        """Plot 3: Throughput vs Prompt Length (separate lines for concurrency)."""
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        
        # Filter for max_tokens=100
        filtered_data = [m for m in metrics if m['max_tokens'] == 100]
        
        if not filtered_data:
            print("  ⚠ Insufficient data for plot_throughput_vs_prompt_length")
            return
        
        # Get unique concurrent request values
        concurrent_values = sorted(set(m['concurrent_requests'] for m in filtered_data))
        
        for concurrent in concurrent_values:
            conc_data = [m for m in filtered_data if m['concurrent_requests'] == concurrent]
            conc_data.sort(key=lambda x: x['prompt_length'])
            
            prompt_lens = [m['prompt_length'] for m in conc_data]
            req_per_sec = [m['requests_per_second'] for m in conc_data]
            tok_per_sec = [m['tokens_per_second'] for m in conc_data]
            
            if prompt_lens:
                axes[0].plot(prompt_lens, req_per_sec, marker='o', 
                           label=f"{concurrent} concurrent", linewidth=2)
                axes[1].plot(prompt_lens, tok_per_sec, marker='o', 
                           label=f"{concurrent} concurrent", linewidth=2)
        
        axes[0].set_xlabel('Prompt Length (tokens)', fontsize=12)
        axes[0].set_ylabel('Requests/sec', fontsize=12)
        axes[0].set_title('Request Throughput vs Prompt Length', fontsize=14, fontweight='bold')
        axes[0].legend(fontsize=10)
        axes[0].grid(True, alpha=0.3)
        
        axes[1].set_xlabel('Prompt Length (tokens)', fontsize=12)
        axes[1].set_ylabel('Tokens/sec', fontsize=12)
        axes[1].set_title('Token Throughput vs Prompt Length', fontsize=14, fontweight='bold')
        axes[1].legend(fontsize=10)
        axes[1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        output_path = self.plots_dir / "3_throughput_vs_prompt_length.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"  ✓ Saved: {output_path}")
        plt.close()
    
    def plot_throughput_vs_max_tokens(self, metrics):
        """Plot 4: Throughput vs Max Output Tokens (separate lines for concurrency)."""
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        
        # Filter for prompt_length=100
        filtered_data = [m for m in metrics if m['prompt_length'] == 100]
        
        if not filtered_data:
            print("  ⚠ Insufficient data for plot_throughput_vs_max_tokens")
            return
        
        # Get unique concurrent request values
        concurrent_values = sorted(set(m['concurrent_requests'] for m in filtered_data))
        
        for concurrent in concurrent_values:
            conc_data = [m for m in filtered_data if m['concurrent_requests'] == concurrent]
            conc_data.sort(key=lambda x: x['max_tokens'])
            
            max_toks = [m['max_tokens'] for m in conc_data]
            req_per_sec = [m['requests_per_second'] for m in conc_data]
            tok_per_sec = [m['tokens_per_second'] for m in conc_data]
            
            if max_toks:
                axes[0].plot(max_toks, req_per_sec, marker='o', 
                           label=f"{concurrent} concurrent", linewidth=2)
                axes[1].plot(max_toks, tok_per_sec, marker='o', 
                           label=f"{concurrent} concurrent", linewidth=2)
        
        axes[0].set_xlabel('Max Output Tokens', fontsize=12)
        axes[0].set_ylabel('Requests/sec', fontsize=12)
        axes[0].set_title('Request Throughput vs Max Tokens', fontsize=14, fontweight='bold')
        axes[0].legend(fontsize=10)
        axes[0].grid(True, alpha=0.3)
        
        axes[1].set_xlabel('Max Output Tokens', fontsize=12)
        axes[1].set_ylabel('Tokens/sec', fontsize=12)
        axes[1].set_title('Token Throughput vs Max Tokens', fontsize=14, fontweight='bold')
        axes[1].legend(fontsize=10)
        axes[1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        output_path = self.plots_dir / "4_throughput_vs_max_tokens.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"  ✓ Saved: {output_path}")
        plt.close()
    
    def plot_heatmap_request_throughput(self, metrics):
        """Plot 5: Heatmap of Request Throughput (concurrent x prompt_length)."""
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Filter for max_tokens=100
        filtered_data = [m for m in metrics if m['max_tokens'] == 100]
        
        if not filtered_data:
            print("  ⚠ Insufficient data for plot_heatmap_request_throughput")
            return
        
        # Get unique values
        concurrent_list = sorted(set(m['concurrent_requests'] for m in filtered_data))
        prompt_list = sorted(set(m['prompt_length'] for m in filtered_data))
        
        # Create matrix
        matrix = np.zeros((len(prompt_list), len(concurrent_list)))
        
        for m in filtered_data:
            i = prompt_list.index(m['prompt_length'])
            j = concurrent_list.index(m['concurrent_requests'])
            matrix[i, j] = m['requests_per_second']
        
        # Create heatmap
        im = ax.imshow(matrix, cmap='YlOrRd', aspect='auto')
        
        # Set ticks
        ax.set_xticks(range(len(concurrent_list)))
        ax.set_yticks(range(len(prompt_list)))
        ax.set_xticklabels(concurrent_list)
        ax.set_yticklabels(prompt_list)
        
        ax.set_xlabel('Concurrent Requests', fontsize=12)
        ax.set_ylabel('Prompt Length (tokens)', fontsize=12)
        ax.set_title('Request Throughput Heatmap (max_tokens=100)', fontsize=14, fontweight='bold')
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('Requests/sec', fontsize=11)
        
        # Add text annotations
        for i in range(len(prompt_list)):
            for j in range(len(concurrent_list)):
                if matrix[i, j] > 0:
                    text = ax.text(j, i, f'{matrix[i, j]:.1f}',
                                 ha="center", va="center", color="black", fontsize=9)
        
        plt.tight_layout()
        output_path = self.plots_dir / "5_heatmap_request_throughput.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"  ✓ Saved: {output_path}")
        plt.close()
    
    def plot_heatmap_token_throughput(self, metrics):
        """Plot 6: Heatmap of Token Throughput (concurrent x max_tokens)."""
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Filter for prompt_length=100
        filtered_data = [m for m in metrics if m['prompt_length'] == 100]
        
        if not filtered_data:
            print("  ⚠ Insufficient data for plot_heatmap_token_throughput")
            return
        
        # Get unique values
        concurrent_list = sorted(set(m['concurrent_requests'] for m in filtered_data))
        max_tokens_list = sorted(set(m['max_tokens'] for m in filtered_data))
        
        # Create matrix
        matrix = np.zeros((len(max_tokens_list), len(concurrent_list)))
        
        for m in filtered_data:
            i = max_tokens_list.index(m['max_tokens'])
            j = concurrent_list.index(m['concurrent_requests'])
            matrix[i, j] = m['tokens_per_second']
        
        # Create heatmap
        im = ax.imshow(matrix, cmap='YlGnBu', aspect='auto')
        
        # Set ticks
        ax.set_xticks(range(len(concurrent_list)))
        ax.set_yticks(range(len(max_tokens_list)))
        ax.set_xticklabels(concurrent_list)
        ax.set_yticklabels(max_tokens_list)
        
        ax.set_xlabel('Concurrent Requests', fontsize=12)
        ax.set_ylabel('Max Output Tokens', fontsize=12)
        ax.set_title('Token Throughput Heatmap (prompt_length=100)', fontsize=14, fontweight='bold')
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('Tokens/sec', fontsize=11)
        
        # Add text annotations
        for i in range(len(max_tokens_list)):
            for j in range(len(concurrent_list)):
                if matrix[i, j] > 0:
                    text = ax.text(j, i, f'{int(matrix[i, j])}',
                                 ha="center", va="center", color="white", fontsize=9)
        
        plt.tight_layout()
        output_path = self.plots_dir / "6_heatmap_token_throughput.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"  ✓ Saved: {output_path}")
        plt.close()
    
    def plot_efficiency_analysis(self, metrics):
        """Plot 7: Token Efficiency (tokens/request) analysis."""
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        
        # Plot 7a: Tokens per request vs prompt length
        filtered_data = [m for m in metrics if m['max_tokens'] == 100 and m['concurrent_requests'] == 5]
        
        if filtered_data:
            filtered_data.sort(key=lambda x: x['prompt_length'])
            prompt_lens = [m['prompt_length'] for m in filtered_data]
            tokens_per_req = [m['avg_tokens_per_request'] for m in filtered_data]
            
            axes[0].plot(prompt_lens, tokens_per_req, marker='o', linewidth=2, color='green')
            axes[0].set_xlabel('Prompt Length (tokens)', fontsize=12)
            axes[0].set_ylabel('Avg Tokens/Request', fontsize=12)
            axes[0].set_title('Token Efficiency vs Prompt Length\n(concurrent=5, max_tokens=100)', 
                            fontsize=14, fontweight='bold')
            axes[0].grid(True, alpha=0.3)
        
        # Plot 7b: Tokens per request vs max_tokens
        filtered_data = [m for m in metrics if m['prompt_length'] == 100 and m['concurrent_requests'] == 5]
        
        if filtered_data:
            filtered_data.sort(key=lambda x: x['max_tokens'])
            max_toks = [m['max_tokens'] for m in filtered_data]
            tokens_per_req = [m['avg_tokens_per_request'] for m in filtered_data]
            
            axes[1].plot(max_toks, tokens_per_req, marker='o', linewidth=2, color='purple')
            axes[1].set_xlabel('Max Output Tokens', fontsize=12)
            axes[1].set_ylabel('Avg Tokens/Request', fontsize=12)
            axes[1].set_title('Token Efficiency vs Max Tokens\n(concurrent=5, prompt_length=100)', 
                            fontsize=14, fontweight='bold')
            axes[1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        output_path = self.plots_dir / "7_efficiency_analysis.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"  ✓ Saved: {output_path}")
        plt.close()
    
    def print_summary_statistics(self, metrics):
        """Print summary statistics to console."""
        print("\n" + "=" * 80)
        print("SUMMARY STATISTICS")
        print("=" * 80)
        
        if not metrics:
            print("No valid metrics found.")
            return
        
        # Peak throughput
        print("\nPeak Throughput:")
        print("-" * 60)
        max_req = max(metrics, key=lambda x: x['requests_per_second'])
        max_tok = max(metrics, key=lambda x: x['tokens_per_second'])
        
        print(f"  Requests/sec:  {max_req['requests_per_second']:.2f} req/s")
        print(f"    Config: concurrent={max_req['concurrent_requests']}, "
              f"prompt={max_req['prompt_length']}, max_tokens={max_req['max_tokens']}")
        print(f"  Tokens/sec:    {max_tok['tokens_per_second']:.2f} tok/s")
        print(f"    Config: concurrent={max_tok['concurrent_requests']}, "
              f"prompt={max_tok['prompt_length']}, max_tokens={max_tok['max_tokens']}")
        
        # Best latency
        print("\nBest Latency:")
        print("-" * 60)
        min_lat = min(metrics, key=lambda x: x['latency_mean'])
        print(f"  Mean latency:  {min_lat['latency_mean']:.2f}s")
        print(f"    Config: concurrent={min_lat['concurrent_requests']}, "
              f"prompt={min_lat['prompt_length']}, max_tokens={min_lat['max_tokens']}")
        
        # Optimal configuration (balanced)
        print("\nOptimal Configuration (concurrent=5, prompt=100, max_tokens=100):")
        print("-" * 60)
        optimal = [m for m in metrics if m['concurrent_requests'] == 5 
                  and m['prompt_length'] == 100 and m['max_tokens'] == 100]
        if optimal:
            opt = optimal[0]
            print(f"  Requests/sec:      {opt['requests_per_second']:.2f}")
            print(f"  Tokens/sec:        {opt['tokens_per_second']:.2f}")
            print(f"  Mean latency:      {opt['latency_mean']:.2f}s")
            print(f"  P95 latency:       {opt['latency_p95']:.2f}s")
            print(f"  Tokens/request:    {opt['avg_tokens_per_request']:.1f}")
        
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
        
        self.plot_throughput_vs_concurrent(metrics)
        self.plot_latency_vs_concurrent(metrics)
        self.plot_throughput_vs_prompt_length(metrics)
        self.plot_throughput_vs_max_tokens(metrics)
        self.plot_heatmap_request_throughput(metrics)
        self.plot_heatmap_token_throughput(metrics)
        self.plot_efficiency_analysis(metrics)
        
        self.print_summary_statistics(metrics)
        
        print(f"\n✓ All plots saved to: {self.plots_dir}/")
        return True


def main():
    parser = argparse.ArgumentParser(description='Ollama Benchmark Results Analysis and Plotting')
    parser.add_argument('--results-dir', default='results',
                       help='Directory containing result JSON files (default: results)')
    parser.add_argument('--pattern', default='ollama_parametric_*.json',
                       help='File pattern to match (default: ollama_parametric_*.json)')
    parser.add_argument('--output-dir', default='analysis/plotsOllama',
                       help='Directory to save plots (default: analysis/plotsOllama)')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("OLLAMA BENCHMARK ANALYSIS")
    print("=" * 80)
    
    analyzer = OllamaResultsAnalyzer(args.results_dir)
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
