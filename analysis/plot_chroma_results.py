#!/usr/bin/env python3
"""
Chroma Parametric Benchmark Analysis and Plotting Script

This script analyzes Chroma benchmark results and generates performance plots.
It loads parametric benchmark data and creates visualizations for:
- Insertion throughput vs. number of documents
- Insertion throughput vs. embedding dimension
- Insertion throughput vs. batch size
- Query latency analysis
- Operation comparisons
- Performance heatmaps

Dependencies: matplotlib, numpy
Install: pip install matplotlib numpy
"""

import sys
import os
import json
import argparse
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend

try:
    import matplotlib.pyplot as plt
    import numpy as np
except ImportError:
    print("ERROR: This script requires matplotlib and numpy")
    print("Install with: pip install matplotlib numpy")
    sys.exit(1)

from pathlib import Path
from typing import List, Dict, Any


class ChromaResultsAnalyzer:
    """Analyzer for Chroma parametric benchmark results."""
    
    def __init__(self, results_dir: str = "results"):
        self.results_dir = Path(results_dir)
        self.data = []
        self.plots_dir = Path("analysis/plotsChroma")
        self.plots_dir.mkdir(parents=True, exist_ok=True)
        
    def load_results(self, pattern: str = "chroma_parametric_*.json"):
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
                    self.data.append({'filename': result_file.name, 'data': data})
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
                insertion = result.get('insertion', {})
                query = result.get('query', {})
                
                all_results.append({
                    'num_documents': params['num_documents'],
                    'embedding_dimension': params['embedding_dimension'],
                    'batch_size': params['batch_size'],
                    'num_queries': params['num_queries'],
                    'top_k': params['top_k'],
                    'insertion_throughput': insertion.get('throughput_docs_per_sec', 0),
                    'insertion_time': insertion.get('total_time_seconds', 0),
                    'query_throughput': query.get('throughput_queries_per_sec', 0),
                    'query_latency_avg': query.get('avg_latency_ms', 0),
                    'query_latency_p95': query.get('p95_latency_ms', 0),
                    'query_latency_p99': query.get('p99_latency_ms', 0),
                    'query_latency_min': query.get('min_latency_ms', 0),
                    'query_latency_max': query.get('max_latency_ms', 0),
                    'query_time': query.get('total_time_seconds', 0),
                })
        
        return all_results
    
    def plot_insertion_throughput_vs_documents(self, metrics):
        """Plot 1: Insertion Throughput vs Number of Documents (separate lines for batch sizes)."""
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        
        # Group by embedding dimension and batch size
        dims = sorted(set(m['embedding_dimension'] for m in metrics))
        
        for idx, dim in enumerate(dims[:2]):  # Show first 2 dimensions
            ax = axes[idx]
            
            # Filter for this dimension and pipeline=1
            dim_data = [m for m in metrics if m['embedding_dimension'] == dim]
            
            # Group by batch size
            batch_sizes = sorted(set(m['batch_size'] for m in dim_data))
            
            for batch_size in batch_sizes:
                size_data = [m for m in dim_data if m['batch_size'] == batch_size]
                size_data.sort(key=lambda x: x['num_documents'])
                
                docs = [m['num_documents'] for m in size_data]
                throughput = [m['insertion_throughput'] for m in size_data]
                
                if docs:
                    ax.plot(docs, throughput, marker='o', label=f"Batch {batch_size}", linewidth=2)
            
            ax.set_xlabel('Number of Documents', fontsize=12)
            ax.set_ylabel('Throughput (docs/s)', fontsize=12)
            ax.set_title(f'Insertion Throughput vs Documents (Dim={dim})', fontsize=14, fontweight='bold')
            ax.legend(title='Batch Size', fontsize=10)
            ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        output_path = self.plots_dir / "1_insertion_throughput_vs_documents.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"  ✓ Saved: {output_path}")
        plt.close()
    
    def plot_insertion_throughput_vs_dimension(self, metrics):
        """Plot 2: Insertion Throughput vs Embedding Dimension (separate lines for document counts)."""
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Filter for batch_size=100
        filtered_data = [m for m in metrics if m['batch_size'] == 100]
        
        # Group by num_documents (select representative values)
        doc_counts = [500, 1000, 2000, 5000]
        
        for docs in doc_counts:
            doc_data = [m for m in filtered_data if m['num_documents'] == docs]
            doc_data.sort(key=lambda x: x['embedding_dimension'])
            
            dims = [m['embedding_dimension'] for m in doc_data]
            throughput = [m['insertion_throughput'] for m in doc_data]
            
            if dims:
                ax.plot(dims, throughput, marker='s', label=f"{docs} docs", linewidth=2)
        
        ax.set_xlabel('Embedding Dimension', fontsize=12)
        ax.set_ylabel('Throughput (docs/s)', fontsize=12)
        ax.set_title('Insertion Throughput vs Embedding Dimension (Batch=100)', fontsize=14, fontweight='bold')
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        output_path = self.plots_dir / "2_insertion_throughput_vs_dimension.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"  ✓ Saved: {output_path}")
        plt.close()
    
    def plot_insertion_throughput_vs_batch_size(self, metrics):
        """Plot 3: Insertion Throughput vs Batch Size."""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Filter for embedding_dimension=384
        filtered_data = [m for m in metrics if m['embedding_dimension'] == 384]
        
        # Group by num_documents
        doc_counts = sorted(set(m['num_documents'] for m in filtered_data))
        
        for docs in doc_counts:
            doc_data = [m for m in filtered_data if m['num_documents'] == docs]
            doc_data.sort(key=lambda x: x['batch_size'])
            
            batch_sizes = [m['batch_size'] for m in doc_data]
            throughput = [m['insertion_throughput'] for m in doc_data]
            
            if batch_sizes:
                ax.plot(batch_sizes, throughput, marker='D', label=f"{docs} docs", linewidth=2)
        
        ax.set_xlabel('Batch Size', fontsize=12)
        ax.set_ylabel('Throughput (docs/s)', fontsize=12)
        ax.set_title('Insertion Throughput vs Batch Size (Dimension=384)', fontsize=14, fontweight='bold')
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        output_path = self.plots_dir / "3_insertion_throughput_vs_batch_size.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"  ✓ Saved: {output_path}")
        plt.close()
    
    def plot_query_latency_vs_documents(self, metrics):
        """Plot 4: Query P99 Latency vs Number of Documents."""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Filter for embedding_dimension=384, batch_size=100
        filtered_data = [m for m in metrics 
                        if m['embedding_dimension'] == 384 and m['batch_size'] == 100
                        and m['query_latency_p99'] > 0]
        filtered_data.sort(key=lambda x: x['num_documents'])
        
        docs = [m['num_documents'] for m in filtered_data]
        latency_p99 = [m['query_latency_p99'] for m in filtered_data]
        latency_p95 = [m['query_latency_p95'] for m in filtered_data]
        latency_avg = [m['query_latency_avg'] for m in filtered_data]
        
        ax.plot(docs, latency_p99, marker='o', linewidth=2, label='P99', color='red')
        ax.plot(docs, latency_p95, marker='s', linewidth=2, label='P95', color='orange')
        ax.plot(docs, latency_avg, marker='^', linewidth=2, label='Average', color='blue')
        
        ax.set_xlabel('Number of Documents', fontsize=12)
        ax.set_ylabel('Query Latency (ms)', fontsize=12)
        ax.set_title('Query Latency vs Number of Documents (Dim=384, Batch=100)', fontsize=14, fontweight='bold')
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        output_path = self.plots_dir / "4_query_latency_vs_documents.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"  ✓ Saved: {output_path}")
        plt.close()
    
    def plot_query_latency_vs_dimension(self, metrics):
        """Plot 5: Query Latency vs Embedding Dimension."""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Filter for num_documents=1000, batch_size=100
        filtered_data = [m for m in metrics 
                        if m['num_documents'] == 1000 and m['batch_size'] == 100
                        and m['query_latency_p99'] > 0]
        filtered_data.sort(key=lambda x: x['embedding_dimension'])
        
        dims = [m['embedding_dimension'] for m in filtered_data]
        latency_p99 = [m['query_latency_p99'] for m in filtered_data]
        latency_avg = [m['query_latency_avg'] for m in filtered_data]
        
        ax.plot(dims, latency_p99, marker='o', linewidth=2, label='P99', color='red')
        ax.plot(dims, latency_avg, marker='^', linewidth=2, label='Average', color='blue')
        
        ax.set_xlabel('Embedding Dimension', fontsize=12)
        ax.set_ylabel('Query Latency (ms)', fontsize=12)
        ax.set_title('Query Latency vs Embedding Dimension (1000 docs, Batch=100)', fontsize=14, fontweight='bold')
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        output_path = self.plots_dir / "5_query_latency_vs_dimension.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"  ✓ Saved: {output_path}")
        plt.close()
    
    def plot_heatmap_insertion_throughput(self, metrics):
        """Plot 6: Heatmap of Insertion Throughput (documents x batch_size)."""
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Filter for embedding_dimension=384
        filtered_data = [m for m in metrics if m['embedding_dimension'] == 384]
        
        # Get unique documents and batch sizes
        docs_list = sorted(set(m['num_documents'] for m in filtered_data))
        batch_sizes_list = sorted(set(m['batch_size'] for m in filtered_data))
        
        # Create matrix
        matrix = np.zeros((len(docs_list), len(batch_sizes_list)))
        
        for m in filtered_data:
            i = docs_list.index(m['num_documents'])
            j = batch_sizes_list.index(m['batch_size'])
            matrix[i, j] = m['insertion_throughput']
        
        # Create heatmap
        im = ax.imshow(matrix, cmap='YlOrRd', aspect='auto')
        
        # Set ticks
        ax.set_xticks(range(len(batch_sizes_list)))
        ax.set_yticks(range(len(docs_list)))
        ax.set_xticklabels(batch_sizes_list)
        ax.set_yticklabels(docs_list)
        
        ax.set_xlabel('Batch Size', fontsize=12)
        ax.set_ylabel('Number of Documents', fontsize=12)
        ax.set_title('Insertion Throughput Heatmap (docs/s, Dim=384)', fontsize=14, fontweight='bold')
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('Docs/sec', fontsize=11)
        
        # Add text annotations
        for i in range(len(docs_list)):
            for j in range(len(batch_sizes_list)):
                if matrix[i, j] > 0:
                    text = ax.text(j, i, f'{int(matrix[i, j])}',
                                  ha="center", va="center", color="black", fontsize=9)
        
        plt.tight_layout()
        output_path = self.plots_dir / "6_heatmap_insertion_throughput.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"  ✓ Saved: {output_path}")
        plt.close()
    
    def plot_heatmap_query_latency(self, metrics):
        """Plot 7: Heatmap of Query Latency P99 (documents x dimension)."""
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Filter for batch_size=100
        filtered_data = [m for m in metrics 
                        if m['batch_size'] == 100 and m['query_latency_p99'] > 0]
        
        # Get unique documents and dimensions
        docs_list = sorted(set(m['num_documents'] for m in filtered_data))
        dims_list = sorted(set(m['embedding_dimension'] for m in filtered_data))
        
        # Create matrix
        matrix = np.zeros((len(docs_list), len(dims_list)))
        
        for m in filtered_data:
            i = docs_list.index(m['num_documents'])
            j = dims_list.index(m['embedding_dimension'])
            matrix[i, j] = m['query_latency_p99']
        
        # Create heatmap
        im = ax.imshow(matrix, cmap='RdYlGn_r', aspect='auto')
        
        # Set ticks
        ax.set_xticks(range(len(dims_list)))
        ax.set_yticks(range(len(docs_list)))
        ax.set_xticklabels(dims_list)
        ax.set_yticklabels(docs_list)
        
        ax.set_xlabel('Embedding Dimension', fontsize=12)
        ax.set_ylabel('Number of Documents', fontsize=12)
        ax.set_title('Query Latency P99 Heatmap (ms, Batch=100)', fontsize=14, fontweight='bold')
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('Latency (ms)', fontsize=11)
        
        # Add text annotations
        for i in range(len(docs_list)):
            for j in range(len(dims_list)):
                if matrix[i, j] > 0:
                    text = ax.text(j, i, f'{matrix[i, j]:.1f}',
                                  ha="center", va="center", color="black", fontsize=8)
        
        plt.tight_layout()
        output_path = self.plots_dir / "7_heatmap_query_latency.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"  ✓ Saved: {output_path}")
        plt.close()
    
    def print_summary_statistics(self, metrics):
        """Print summary statistics to console."""
        print("\n" + "=" * 80)
        print("SUMMARY STATISTICS")
        print("=" * 80)
        
        # Peak insertion throughput
        print("\nPeak Insertion Throughput by Configuration:")
        print("-" * 60)
        if metrics:
            max_insertion = max(metrics, key=lambda m: m['insertion_throughput'])
            print(f"  Max Throughput:     {max_insertion['insertion_throughput']:10,.0f} docs/s")
            print(f"    Documents:       {max_insertion['num_documents']}")
            print(f"    Dimension:       {max_insertion['embedding_dimension']}")
            print(f"    Batch Size:      {max_insertion['batch_size']}")
        
        # Best query latency
        print("\nBest Query Latency (lowest P99):")
        print("-" * 60)
        valid_queries = [m for m in metrics if m['query_latency_p99'] > 0]
        if valid_queries:
            min_latency = min(valid_queries, key=lambda m: m['query_latency_p99'])
            print(f"  P99 Latency:        {min_latency['query_latency_p99']:10.2f} ms")
            print(f"    Documents:       {min_latency['num_documents']}")
            print(f"    Dimension:       {min_latency['embedding_dimension']}")
            print(f"    Batch Size:      {min_latency['batch_size']}")
        
        # Average statistics
        print("\nAverage Performance:")
        print("-" * 60)
        if metrics:
            avg_insertion = np.mean([m['insertion_throughput'] for m in metrics if m['insertion_throughput'] > 0])
            print(f"  Avg Insertion:      {avg_insertion:10,.0f} docs/s")
        
        if valid_queries:
            avg_latency = np.mean([m['query_latency_p99'] for m in valid_queries])
            print(f"  Avg Query P99:      {avg_latency:10.2f} ms")
        
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
        
        self.plot_insertion_throughput_vs_documents(metrics)
        self.plot_insertion_throughput_vs_dimension(metrics)
        self.plot_insertion_throughput_vs_batch_size(metrics)
        self.plot_query_latency_vs_documents(metrics)
        self.plot_query_latency_vs_dimension(metrics)
        self.plot_heatmap_insertion_throughput(metrics)
        self.plot_heatmap_query_latency(metrics)
        
        self.print_summary_statistics(metrics)
        
        print(f"\n✓ All plots saved to: {self.plots_dir}/")
        return True


def main():
    parser = argparse.ArgumentParser(description='Chroma Benchmark Results Analysis and Plotting')
    parser.add_argument('--results-dir', default='results',
                       help='Directory containing result JSON files (default: results)')
    parser.add_argument('--pattern', default='chroma_parametric_*.json',
                       help='File pattern to match (default: chroma_parametric_*.json)')
    parser.add_argument('--output-dir', default='analysis/plotsChroma',
                       help='Directory to save plots (default: analysis/plotsChroma)')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("CHROMA BENCHMARK ANALYSIS")
    print("=" * 80)
    
    analyzer = ChromaResultsAnalyzer(args.results_dir)
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
