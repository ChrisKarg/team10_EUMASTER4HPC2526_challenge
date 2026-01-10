#!/usr/bin/env python3
"""
Redis Benchmark Analysis and Plotting Script

This script analyzes Redis benchmark results and generates visualizations.

Supports both:
- Single-run benchmark results (redis_benchmark_*.json)
- Parametric benchmark results (redis_parametric_*.json)

Dependencies: matplotlib, seaborn, numpy, pandas
Install: pip install matplotlib seaborn numpy pandas
"""

import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import argparse

try:
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    import matplotlib.pyplot as plt
    import seaborn as sns
    import numpy as np
    import pandas as pd
except ImportError as e:
    print(f"ERROR: Missing required package: {e}")
    print("Install with: pip install matplotlib seaborn numpy pandas")
    sys.exit(1)


# =============================================================================
# POSTER-QUALITY STYLE CONFIGURATION
# =============================================================================

def setup_poster_style():
    """Configure matplotlib/seaborn for plots."""
    # Use seaborn's paper context with custom scaling
    sns.set_theme(
        context='poster',  # Large elements for posters
        style='whitegrid',  # Clean white background with grid
        palette='deep',  # Professional color palette
        font_scale=1.2
    )
    
    # Additional customizations for poster quality
    plt.rcParams.update({
        # Figure
        'figure.facecolor': 'white',
        'figure.edgecolor': 'white',
        'figure.dpi': 150,
        'savefig.dpi': 300,
        'savefig.bbox': 'tight',
        'savefig.pad_inches': 0.2,
        
        # Fonts
        'font.family': 'sans-serif',
        'font.sans-serif': ['DejaVu Sans', 'Helvetica', 'Arial', 'sans-serif'],
        'font.size': 14,
        'axes.titlesize': 18,
        'axes.labelsize': 16,
        'xtick.labelsize': 14,
        'ytick.labelsize': 14,
        'legend.fontsize': 13,
        'legend.title_fontsize': 14,
        
        # Lines and markers
        'lines.linewidth': 2.5,
        'lines.markersize': 10,
        
        # Axes
        'axes.linewidth': 1.5,
        'axes.spines.top': False,
        'axes.spines.right': False,
        
        # Grid
        'grid.linewidth': 0.8,
        'grid.alpha': 0.4,
    })


# =============================================================================
# COLOR PALETTES FOR DIFFERENT PLOT TYPES
# =============================================================================

# Professional color palette for operations
OPERATION_COLORS = {
    'GET': '#2ecc71',       # Green - read operations
    'SET': '#e74c3c',       # Red - write operations
    'PING_INLINE': '#3498db',  # Blue
    'PING_MBULK': '#9b59b6',   # Purple
    'LPUSH': '#f39c12',     # Orange
    'LPOP': '#e67e22',      # Dark orange
    'SADD': '#1abc9c',      # Teal
    'SPOP': '#16a085',      # Dark teal
    'HSET': '#34495e',      # Dark gray
    'ZADD': '#8e44ad',      # Dark purple
    'ZPOPMIN': '#c0392b',   # Dark red
    'INCR': '#27ae60',      # Dark green
    'DEL': '#7f8c8d',       # Gray
}

# Latency metric colors
LATENCY_COLORS = {
    'avg': '#3498db',
    'min': '#2ecc71',
    'p50': '#f39c12',
    'p95': '#e74c3c',
    'p99': '#9b59b6',
    'max': '#e74c3c',
}

# Sequential palette for heatmaps
HEATMAP_CMAP = 'YlOrRd'


# =============================================================================
# DATA LOADING AND PROCESSING
# =============================================================================

class RedisResultsAnalyzer:
    """Analyzer for Redis benchmark results with poster-quality plotting."""
    
    def __init__(self, results_dir: str = "results"):
        self.results_dir = Path(results_dir)
        self.single_run_data = []
        self.parametric_data = []
        self.plots_dir = Path("analysis/plots")
        self.plots_dir.mkdir(parents=True, exist_ok=True)
        
        # Apply poster styling
        setup_poster_style()
    
    def load_all_results(self):
        """Load both single-run and parametric benchmark results."""
        # Load single-run results
        single_files = list(self.results_dir.glob("redis_benchmark*.json"))
        single_files = [f for f in single_files if 'parametric' not in f.name]
        
        for result_file in single_files:
            try:
                with open(result_file, 'r') as f:
                    data = json.load(f)
                    self.single_run_data.append({
                        'filename': result_file.name,
                        'data': data
                    })
                print(f"  ✓ Loaded single-run: {result_file.name}")
            except Exception as e:
                print(f"  ✗ Failed to load {result_file.name}: {e}")
        
        # Load parametric results
        parametric_files = list(self.results_dir.glob("redis_parametric_*.json"))
        
        for result_file in parametric_files:
            try:
                with open(result_file, 'r') as f:
                    data = json.load(f)
                    self.parametric_data.append({
                        'filename': result_file.name,
                        'data': data
                    })
                print(f"  ✓ Loaded parametric: {result_file.name}")
            except Exception as e:
                print(f"  ✗ Failed to load {result_file.name}: {e}")
        
        total = len(self.single_run_data) + len(self.parametric_data)
        print(f"\nTotal: {total} result file(s) loaded")
        return total > 0
    
    def get_single_run_df(self) -> pd.DataFrame:
        """Convert single-run results to a pandas DataFrame."""
        records = []
        
        for dataset in self.single_run_data:
            config = dataset['data'].get('config', {})
            results = dataset['data'].get('results', {})
            tests = results.get('tests', {})
            
            for test_name, metrics in tests.items():
                # Skip header row if accidentally included
                if test_name.lower() == 'test':
                    continue
                    
                metric_array = metrics.get('metrics', [])
                records.append({
                    'source': dataset['filename'],
                    'operation': test_name,
                    'throughput': metrics.get('requests_per_second', 0),
                    'clients': config.get('clients', 50),
                    'payload_size': config.get('payload_size', 256),
                    'pipeline': config.get('pipeline', 1),
                    'latency_avg': metric_array[0] if len(metric_array) > 0 else None,
                    'latency_min': metric_array[1] if len(metric_array) > 1 else None,
                    'latency_p50': metric_array[2] if len(metric_array) > 2 else None,
                    'latency_p95': metric_array[3] if len(metric_array) > 3 else None,
                    'latency_p99': metric_array[4] if len(metric_array) > 4 else None,
                    'latency_max': metric_array[5] if len(metric_array) > 5 else None,
                })
        
        return pd.DataFrame(records)
    
    def get_parametric_df(self) -> pd.DataFrame:
        """Convert parametric results to a pandas DataFrame."""
        records = []
        
        for dataset in self.parametric_data:
            results_list = dataset['data'].get('results', [])
            
            for result in results_list:
                if not result.get('success', False):
                    continue
                
                params = result.get('parameters', {})
                tests = result.get('tests', {})
                
                for test_name, metrics in tests.items():
                    if test_name.lower() == 'test':
                        continue
                        
                    records.append({
                        'source': dataset['filename'],
                        'operation': test_name.upper(),
                        'throughput': metrics.get('requests_per_second', 0),
                        'clients': params.get('clients', 50),
                        'data_size': params.get('data_size_bytes', 256),
                        'pipeline': params.get('pipeline', 1),
                        'latency_avg': metrics.get('latency_avg_ms'),
                        'latency_min': metrics.get('latency_min_ms'),
                        'latency_p50': metrics.get('latency_p50_ms'),
                        'latency_p95': metrics.get('latency_p95_ms'),
                        'latency_p99': metrics.get('latency_p99_ms'),
                        'latency_max': metrics.get('latency_max_ms'),
                    })
        
        return pd.DataFrame(records)

    # =========================================================================
    # SINGLE-RUN PLOTS 
    # =========================================================================
    
    def plot_throughput_comparison(self, df: pd.DataFrame):
        """Plot 1: Throughput comparison bar chart with error bars."""
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Aggregate by operation
        agg_df = df.groupby('operation')['throughput'].agg(['mean', 'std', 'count']).reset_index()
        agg_df = agg_df.sort_values('mean', ascending=True)
        
        # Get colors for each operation
        colors = [OPERATION_COLORS.get(op, '#95a5a6') for op in agg_df['operation']]
        
        # Create horizontal bar chart
        bars = ax.barh(
            agg_df['operation'], 
            agg_df['mean'] / 1000,  # Convert to thousands
            xerr=agg_df['std'] / 1000 if agg_df['std'].notna().any() else None,
            color=colors,
            edgecolor='white',
            linewidth=2,
            capsize=5,
            error_kw={'linewidth': 2, 'capthick': 2}
        )
        
        # Add value labels
        for bar, val in zip(bars, agg_df['mean']):
            ax.text(
                bar.get_width() + 1, 
                bar.get_y() + bar.get_height()/2,
                f'{val/1000:.1f}K',
                va='center', ha='left',
                fontsize=14, fontweight='bold'
            )
        
        ax.set_xlabel('Throughput (thousand req/s)', fontweight='bold')
        ax.set_ylabel('Operation', fontweight='bold')
        ax.set_title('Redis Operation Throughput Comparison', fontweight='bold', pad=20)
        
        # Add subtle grid
        ax.xaxis.grid(True, alpha=0.3)
        ax.set_axisbelow(True)
        
        plt.tight_layout()
        output_path = self.plots_dir / "1_throughput_comparison.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
        print(f"  ✓ Saved: {output_path}")
        plt.close()
    
    def plot_latency_distribution(self, df: pd.DataFrame):
        """Plot 2: Latency distribution with box/violin plot."""
        # Prepare data for latency distribution
        latency_data = []
        for _, row in df.iterrows():
            for metric in ['latency_min', 'latency_p50', 'latency_p95', 'latency_p99', 'latency_max']:
                if pd.notna(row[metric]):
                    latency_data.append({
                        'operation': row['operation'],
                        'percentile': metric.replace('latency_', '').upper(),
                        'latency_ms': row[metric]
                    })
        
        lat_df = pd.DataFrame(latency_data)
        
        if lat_df.empty:
            print("  ⚠ No latency data available for distribution plot")
            return
        
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # Create grouped bar chart for latency percentiles
        operations = df['operation'].unique()
        percentiles = ['MIN', 'P50', 'P95', 'P99', 'MAX']
        x = np.arange(len(operations))
        width = 0.15
        
        percentile_colors = ['#2ecc71', '#3498db', '#f39c12', '#e74c3c', '#9b59b6']
        
        for i, (pct, color) in enumerate(zip(percentiles, percentile_colors)):
            pct_data = lat_df[lat_df['percentile'] == pct]
            values = []
            for op in operations:
                op_data = pct_data[pct_data['operation'] == op]['latency_ms']
                values.append(op_data.mean() if len(op_data) > 0 else 0)
            
            bars = ax.bar(x + i * width, values, width, label=pct, color=color, edgecolor='white', linewidth=1.5)
        
        ax.set_xlabel('Operation', fontweight='bold')
        ax.set_ylabel('Latency (ms)', fontweight='bold')
        ax.set_title('Redis Latency Distribution by Percentile', fontweight='bold', pad=20)
        ax.set_xticks(x + width * 2)
        ax.set_xticklabels(operations, rotation=45, ha='right')
        ax.legend(title='Percentile', loc='upper left', framealpha=0.95)
        ax.yaxis.grid(True, alpha=0.3)
        ax.set_axisbelow(True)
        
        plt.tight_layout()
        output_path = self.plots_dir / "2_latency_distribution.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
        print(f"  ✓ Saved: {output_path}")
        plt.close()
    
    def plot_latency_breakdown(self, df: pd.DataFrame):
        """Plot 3: Stacked latency breakdown showing avg vs tail latency."""
        fig, ax = plt.subplots(figsize=(12, 8))
        
        operations = df['operation'].unique()
        
        # Prepare data
        avg_latencies = []
        tail_latencies = []  # p99 - avg (showing the tail)
        
        for op in operations:
            op_data = df[df['operation'] == op]
            avg = op_data['latency_avg'].mean()
            p99 = op_data['latency_p99'].mean()
            avg_latencies.append(avg if pd.notna(avg) else 0)
            tail_latencies.append((p99 - avg) if pd.notna(p99) and pd.notna(avg) else 0)
        
        x = np.arange(len(operations))
        width = 0.6
        
        # Stacked bars
        bars1 = ax.bar(x, avg_latencies, width, label='Average Latency', color='#3498db', edgecolor='white', linewidth=2)
        bars2 = ax.bar(x, tail_latencies, width, bottom=avg_latencies, label='Tail Latency (P99 - Avg)', 
                       color='#e74c3c', edgecolor='white', linewidth=2)
        
        # Add value labels
        for i, (avg, tail) in enumerate(zip(avg_latencies, tail_latencies)):
            total = avg + tail
            ax.text(i, total + 0.05, f'{total:.2f}ms', ha='center', va='bottom', fontweight='bold', fontsize=12)
        
        ax.set_xlabel('Operation', fontweight='bold')
        ax.set_ylabel('Latency (ms)', fontweight='bold')
        ax.set_title('Average vs Tail Latency Breakdown', fontweight='bold', pad=20)
        ax.set_xticks(x)
        ax.set_xticklabels(operations, rotation=45, ha='right')
        ax.legend(loc='upper right', framealpha=0.95)
        ax.yaxis.grid(True, alpha=0.3)
        ax.set_axisbelow(True)
        
        plt.tight_layout()
        output_path = self.plots_dir / "3_latency_breakdown.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
        print(f"  ✓ Saved: {output_path}")
        plt.close()
    
    def plot_throughput_vs_latency(self, df: pd.DataFrame):
        """Plot 4: Scatter plot of throughput vs latency (performance profile)."""
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Filter operations with valid data
        plot_df = df[df['latency_avg'].notna() & df['throughput'].notna()].copy()
        
        if plot_df.empty:
            print("  ⚠ No valid throughput/latency data for scatter plot")
            return
        
        # Create scatter plot with different colors per operation
        for op in plot_df['operation'].unique():
            op_data = plot_df[plot_df['operation'] == op]
            color = OPERATION_COLORS.get(op, '#95a5a6')
            ax.scatter(
                op_data['throughput'] / 1000,
                op_data['latency_avg'],
                s=200,
                c=color,
                label=op,
                alpha=0.8,
                edgecolor='white',
                linewidth=2
            )
        
        ax.set_xlabel('Throughput (thousand req/s)', fontweight='bold')
        ax.set_ylabel('Average Latency (ms)', fontweight='bold')
        ax.set_title('Throughput vs Latency Performance Profile', fontweight='bold', pad=20)
        ax.legend(title='Operation', loc='upper right', framealpha=0.95)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        output_path = self.plots_dir / "4_throughput_vs_latency.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
        print(f"  ✓ Saved: {output_path}")
        plt.close()
    
    def plot_summary_dashboard(self, df: pd.DataFrame):
        """Plot 5: Summary dashboard combining key metrics."""
        fig = plt.figure(figsize=(16, 12))
        
        # Create grid layout
        gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)
        
        # --- Subplot 1: Throughput bars ---
        ax1 = fig.add_subplot(gs[0, 0])
        agg_df = df.groupby('operation')['throughput'].mean().sort_values(ascending=True)
        colors = [OPERATION_COLORS.get(op, '#95a5a6') for op in agg_df.index]
        bars = ax1.barh(agg_df.index, agg_df.values / 1000, color=colors, edgecolor='white', linewidth=1.5)
        ax1.set_xlabel('Throughput (K req/s)', fontweight='bold')
        ax1.set_title('Throughput by Operation', fontweight='bold')
        ax1.xaxis.grid(True, alpha=0.3)
        
        # --- Subplot 2: Latency comparison ---
        ax2 = fig.add_subplot(gs[0, 1])
        operations = df['operation'].unique()
        x = np.arange(len(operations))
        width = 0.35
        
        avg_vals = [df[df['operation'] == op]['latency_avg'].mean() for op in operations]
        p99_vals = [df[df['operation'] == op]['latency_p99'].mean() for op in operations]
        
        ax2.bar(x - width/2, avg_vals, width, label='Average', color='#3498db', edgecolor='white')
        ax2.bar(x + width/2, p99_vals, width, label='P99', color='#e74c3c', edgecolor='white')
        ax2.set_ylabel('Latency (ms)', fontweight='bold')
        ax2.set_title('Average vs P99 Latency', fontweight='bold')
        ax2.set_xticks(x)
        ax2.set_xticklabels(operations, rotation=45, ha='right')
        ax2.legend(framealpha=0.95)
        ax2.yaxis.grid(True, alpha=0.3)
        
        # --- Subplot 3: Latency percentiles (radar-style bar) ---
        ax3 = fig.add_subplot(gs[1, 0])
        
        # Get one representative operation (SET or first available)
        rep_op = 'SET' if 'SET' in df['operation'].values else df['operation'].iloc[0]
        rep_data = df[df['operation'] == rep_op].iloc[0]
        
        percentiles = ['MIN', 'P50', 'P95', 'P99', 'MAX']
        values = [
            rep_data['latency_min'] if pd.notna(rep_data['latency_min']) else 0,
            rep_data['latency_p50'] if pd.notna(rep_data['latency_p50']) else 0,
            rep_data['latency_p95'] if pd.notna(rep_data['latency_p95']) else 0,
            rep_data['latency_p99'] if pd.notna(rep_data['latency_p99']) else 0,
            rep_data['latency_max'] if pd.notna(rep_data['latency_max']) else 0,
        ]
        
        pct_colors = ['#2ecc71', '#3498db', '#f39c12', '#e74c3c', '#9b59b6']
        bars = ax3.bar(percentiles, values, color=pct_colors, edgecolor='white', linewidth=1.5)
        
        for bar, val in zip(bars, values):
            ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1, 
                    f'{val:.2f}', ha='center', fontweight='bold', fontsize=11)
        
        ax3.set_ylabel('Latency (ms)', fontweight='bold')
        ax3.set_title(f'{rep_op} Latency Percentiles', fontweight='bold')
        ax3.yaxis.grid(True, alpha=0.3)
        
        # --- Subplot 4: Read vs Write comparison ---
        ax4 = fig.add_subplot(gs[1, 1])
        
        read_ops = ['GET', 'PING_INLINE', 'PING_MBULK']
        write_ops = ['SET', 'LPUSH', 'SADD', 'HSET', 'ZADD']
        
        read_throughput = df[df['operation'].isin(read_ops)]['throughput'].mean() / 1000
        write_throughput = df[df['operation'].isin(write_ops)]['throughput'].mean() / 1000
        
        categories = ['Read Operations', 'Write Operations']
        values = [read_throughput if pd.notna(read_throughput) else 0, 
                  write_throughput if pd.notna(write_throughput) else 0]
        colors = ['#2ecc71', '#e74c3c']
        
        bars = ax4.bar(categories, values, color=colors, edgecolor='white', linewidth=2, width=0.5)
        
        for bar, val in zip(bars, values):
            if val > 0:
                ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                        f'{val:.1f}K', ha='center', fontweight='bold', fontsize=14)
        
        ax4.set_ylabel('Throughput (K req/s)', fontweight='bold')
        ax4.set_title('Read vs Write Performance', fontweight='bold')
        ax4.yaxis.grid(True, alpha=0.3)
        
        # Main title
        fig.suptitle('Redis Performance Summary Dashboard', fontsize=20, fontweight='bold', y=1.02)
        
        plt.tight_layout()
        output_path = self.plots_dir / "5_summary_dashboard.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
        print(f"  ✓ Saved: {output_path}")
        plt.close()
    
    def plot_latency_heatmap_single(self, df: pd.DataFrame):
        """Plot 6: Heatmap of latency metrics across operations."""
        fig, ax = plt.subplots(figsize=(12, 8))
        
        operations = df['operation'].unique()
        metrics = ['latency_min', 'latency_avg', 'latency_p50', 'latency_p95', 'latency_p99', 'latency_max']
        metric_labels = ['MIN', 'AVG', 'P50', 'P95', 'P99', 'MAX']
        
        # Build matrix
        matrix = np.zeros((len(operations), len(metrics)))
        for i, op in enumerate(operations):
            op_data = df[df['operation'] == op]
            for j, metric in enumerate(metrics):
                val = op_data[metric].mean()
                matrix[i, j] = val if pd.notna(val) else 0
        
        # Create heatmap
        sns.heatmap(
            matrix,
            annot=True,
            fmt='.2f',
            cmap='YlOrRd',
            xticklabels=metric_labels,
            yticklabels=operations,
            ax=ax,
            cbar_kws={'label': 'Latency (ms)'},
            linewidths=0.5,
            linecolor='white'
        )
        
        ax.set_xlabel('Latency Percentile', fontweight='bold')
        ax.set_ylabel('Operation', fontweight='bold')
        ax.set_title('Latency Heatmap Across Operations', fontweight='bold', pad=20)
        
        plt.tight_layout()
        output_path = self.plots_dir / "6_latency_heatmap.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
        print(f"  ✓ Saved: {output_path}")
        plt.close()

    # =========================================================================
    # PARAMETRIC PLOTS
    # =========================================================================
    
    def plot_throughput_vs_clients(self, df: pd.DataFrame, test_names=['SET', 'GET']):
        """Plot: Throughput scaling with number of clients."""
        fig, axes = plt.subplots(1, len(test_names), figsize=(7*len(test_names), 6))
        if len(test_names) == 1:
            axes = [axes]
        
        palette = sns.color_palette("viridis", n_colors=6)
        
        for idx, test in enumerate(test_names):
            ax = axes[idx]
            test_df = df[(df['operation'] == test) & (df['pipeline'] == 1)]
            
            if test_df.empty:
                continue
            
            data_sizes = sorted(test_df['data_size'].unique())
            
            for i, data_size in enumerate(data_sizes):
                size_df = test_df[test_df['data_size'] == data_size].sort_values('clients')
                label = f"{data_size}B" if data_size < 1024 else f"{data_size//1024}KB"
                ax.plot(size_df['clients'], size_df['throughput'] / 1000, 
                       marker='o', label=label, color=palette[i % len(palette)], linewidth=2.5)
            
            ax.set_xlabel('Number of Clients', fontweight='bold')
            ax.set_ylabel('Throughput (K req/s)', fontweight='bold')
            ax.set_title(f'{test} Throughput Scaling', fontweight='bold')
            ax.set_xscale('log')
            ax.legend(title='Payload Size', framealpha=0.95)
            ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        output_path = self.plots_dir / "7_throughput_vs_clients.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
        print(f"  ✓ Saved: {output_path}")
        plt.close()
    
    def plot_throughput_vs_datasize(self, df: pd.DataFrame, test_names=['SET', 'GET']):
        """Plot: Throughput vs data size."""
        fig, axes = plt.subplots(1, len(test_names), figsize=(7*len(test_names), 6))
        if len(test_names) == 1:
            axes = [axes]
        
        palette = sns.color_palette("tab10")
        
        for idx, test in enumerate(test_names):
            ax = axes[idx]
            test_df = df[(df['operation'] == test) & (df['pipeline'] == 1)]
            
            if test_df.empty:
                continue
            
            client_counts = [1, 50, 200, 500]
            
            for i, clients in enumerate(client_counts):
                client_df = test_df[test_df['clients'] == clients].sort_values('data_size')
                if not client_df.empty:
                    ax.plot(client_df['data_size'], client_df['throughput'] / 1000,
                           marker='s', label=f"{clients} clients", color=palette[i], linewidth=2.5)
            
            ax.set_xlabel('Payload Size (bytes)', fontweight='bold')
            ax.set_ylabel('Throughput (K req/s)', fontweight='bold')
            ax.set_title(f'{test} vs Payload Size', fontweight='bold')
            ax.set_xscale('log')
            ax.legend(framealpha=0.95)
            ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        output_path = self.plots_dir / "8_throughput_vs_datasize.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
        print(f"  ✓ Saved: {output_path}")
        plt.close()
    
    def plot_throughput_vs_pipeline(self, df: pd.DataFrame, test='GET'):
        """Plot: Pipeline depth impact on throughput."""
        fig, ax = plt.subplots(figsize=(10, 7))
        
        test_df = df[(df['operation'] == test) & (df['data_size'] == 256)]
        
        if test_df.empty:
            print(f"  ⚠ No data for {test} with 256B payload")
            return
        
        palette = sns.color_palette("husl", n_colors=5)
        client_counts = [10, 50, 100, 200, 500]
        
        for i, clients in enumerate(client_counts):
            client_df = test_df[test_df['clients'] == clients].sort_values('pipeline')
            if not client_df.empty:
                ax.plot(client_df['pipeline'], client_df['throughput'] / 1000,
                       marker='o', label=f"{clients} clients", color=palette[i % len(palette)], linewidth=2.5)
        
        ax.set_xlabel('Pipeline Depth', fontweight='bold')
        ax.set_ylabel('Throughput (K req/s)', fontweight='bold')
        ax.set_title(f'{test} Throughput vs Pipeline Depth (256B payload)', fontweight='bold')
        ax.set_xscale('log')
        ax.legend(framealpha=0.95)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        output_path = self.plots_dir / "9_throughput_vs_pipeline.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
        print(f"  ✓ Saved: {output_path}")
        plt.close()
    
    def plot_heatmap_throughput(self, df: pd.DataFrame, test='GET'):
        """Plot: Heatmap of throughput (clients x data_size)."""
        fig, ax = plt.subplots(figsize=(12, 9))
        
        test_df = df[(df['operation'] == test) & (df['pipeline'] == 1)]
        
        if test_df.empty:
            print(f"  ⚠ No data for {test} heatmap")
            return
        
        clients_list = sorted(test_df['clients'].unique())
        data_sizes_list = sorted(test_df['data_size'].unique())
        
        matrix = np.zeros((len(data_sizes_list), len(clients_list)))
        
        for _, row in test_df.iterrows():
            try:
                i = data_sizes_list.index(row['data_size'])
                j = clients_list.index(row['clients'])
                matrix[i, j] = row['throughput'] / 1000
            except ValueError:
                continue
        
        # Format labels
        y_labels = [f"{s//1024}KB" if s >= 1024 else f"{s}B" for s in data_sizes_list]
        
        sns.heatmap(
            matrix,
            annot=True,
            fmt='.0f',
            cmap='YlGnBu',
            xticklabels=clients_list,
            yticklabels=y_labels,
            ax=ax,
            cbar_kws={'label': 'Throughput (K req/s)'},
            linewidths=0.5,
            linecolor='white'
        )
        
        ax.set_xlabel('Number of Clients', fontweight='bold')
        ax.set_ylabel('Payload Size', fontweight='bold')
        ax.set_title(f'{test} Throughput Heatmap (K req/s)', fontweight='bold', pad=20)
        
        plt.tight_layout()
        output_path = self.plots_dir / "10_throughput_heatmap.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
        print(f"  ✓ Saved: {output_path}")
        plt.close()
    
    def plot_operations_comparison_parametric(self, df: pd.DataFrame):
        """Plot: Operation comparison at optimal settings."""
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # Find optimal configuration
        optimal_df = df[(df['clients'] == 100) & (df['data_size'] == 256) & (df['pipeline'] == 1)]
        
        if optimal_df.empty:
            # Fallback to any available configuration
            optimal_df = df.groupby('operation')['throughput'].mean().reset_index()
            optimal_df.columns = ['operation', 'throughput']
        else:
            optimal_df = optimal_df.groupby('operation')['throughput'].mean().reset_index()
        
        optimal_df = optimal_df.sort_values('throughput', ascending=True)
        
        colors = [OPERATION_COLORS.get(op, '#95a5a6') for op in optimal_df['operation']]
        
        bars = ax.barh(optimal_df['operation'], optimal_df['throughput'] / 1000, 
                       color=colors, edgecolor='white', linewidth=2)
        
        for bar, val in zip(bars, optimal_df['throughput']):
            ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
                   f'{val/1000:.1f}K', va='center', fontweight='bold', fontsize=12)
        
        ax.set_xlabel('Throughput (K req/s)', fontweight='bold')
        ax.set_ylabel('Operation', fontweight='bold')
        ax.set_title('Redis Operations Comparison\n(100 clients, 256B, pipeline=1)', fontweight='bold')
        ax.xaxis.grid(True, alpha=0.3)
        
        plt.tight_layout()
        output_path = self.plots_dir / "11_operations_comparison.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
        print(f"  ✓ Saved: {output_path}")
        plt.close()
    
    def plot_latency_scaling(self, df: pd.DataFrame, test_names=['SET', 'GET']):
        """Plot: P99 latency scaling with clients."""
        fig, axes = plt.subplots(1, len(test_names), figsize=(7*len(test_names), 6))
        if len(test_names) == 1:
            axes = [axes]
        
        for idx, test in enumerate(test_names):
            ax = axes[idx]
            test_df = df[(df['operation'] == test) & (df['pipeline'] == 1) & (df['data_size'] == 256)]
            test_df = test_df[test_df['latency_p99'].notna()].sort_values('clients')
            
            if test_df.empty:
                continue
            
            ax.plot(test_df['clients'], test_df['latency_p99'], 
                   marker='o', color='#e74c3c', linewidth=2.5, markersize=10)
            ax.fill_between(test_df['clients'], test_df['latency_p99'], alpha=0.3, color='#e74c3c')
            
            ax.set_xlabel('Number of Clients', fontweight='bold')
            ax.set_ylabel('P99 Latency (ms)', fontweight='bold')
            ax.set_title(f'{test} P99 Latency Scaling', fontweight='bold')
            ax.set_xscale('log')
            ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        output_path = self.plots_dir / "12_latency_scaling.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
        print(f"  ✓ Saved: {output_path}")
        plt.close()

    # =========================================================================
    # SUMMARY AND STATISTICS
    # =========================================================================
    
    def print_summary_statistics(self, single_df: pd.DataFrame, parametric_df: pd.DataFrame):
        """Print comprehensive summary statistics."""
        print("\n" + "=" * 80)
        print("SUMMARY STATISTICS")
        print("=" * 80)
        
        # Single-run results
        if not single_df.empty:
            print("\n📊 Single-Run Results:")
            print("-" * 60)
            for op in single_df['operation'].unique():
                op_data = single_df[single_df['operation'] == op]
                throughput = op_data['throughput'].mean()
                latency_avg = op_data['latency_avg'].mean()
                latency_p99 = op_data['latency_p99'].mean()
                print(f"  {op:15s}: {throughput:10,.0f} req/s | "
                      f"Avg: {latency_avg:.2f}ms | P99: {latency_p99:.2f}ms")
        
        # Parametric results
        if not parametric_df.empty:
            print("\n📈 Parametric Results (Peak Performance):")
            print("-" * 60)
            for op in parametric_df['operation'].unique():
                op_data = parametric_df[parametric_df['operation'] == op]
                max_entry = op_data.loc[op_data['throughput'].idxmax()]
                print(f"  {op:12s}: {max_entry['throughput']:10,.0f} req/s "
                      f"(clients={int(max_entry['clients'])}, size={int(max_entry['data_size'])}B, "
                      f"pipeline={int(max_entry['pipeline'])})")
        
        print("=" * 80)

    # =========================================================================
    # MAIN GENERATION METHOD
    # =========================================================================
    
    def generate_all_plots(self):
        """Generate all plots."""
        single_df = self.get_single_run_df()
        parametric_df = self.get_parametric_df()
        
        if single_df.empty and parametric_df.empty:
            print("ERROR: No data available for plotting.")
            return False
        
        print("\n" + "=" * 80)
        print("GENERATING PLOTS")
        print("=" * 80)
        
        # Generate single-run plots
        if not single_df.empty:
            print(f"\n📊 Single-run data: {len(single_df)} records")
            print("-" * 40)
            self.plot_throughput_comparison(single_df)
            self.plot_latency_distribution(single_df)
            self.plot_latency_breakdown(single_df)
            self.plot_throughput_vs_latency(single_df)
            self.plot_summary_dashboard(single_df)
            self.plot_latency_heatmap_single(single_df)
        
        # Generate parametric plots
        if not parametric_df.empty:
            print(f"\n📈 Parametric data: {len(parametric_df)} records")
            print("-" * 40)
            
            available_ops = parametric_df['operation'].unique()
            test_ops = [op for op in ['SET', 'GET'] if op in available_ops]
            
            if test_ops:
                self.plot_throughput_vs_clients(parametric_df, test_ops)
                self.plot_throughput_vs_datasize(parametric_df, test_ops)
                self.plot_latency_scaling(parametric_df, test_ops)
            
            if 'GET' in available_ops:
                self.plot_throughput_vs_pipeline(parametric_df, 'GET')
                self.plot_heatmap_throughput(parametric_df, 'GET')
            
            self.plot_operations_comparison_parametric(parametric_df)
        
        # Print summary
        self.print_summary_statistics(single_df, parametric_df)
        
        print(f"\n✓ All plots saved to: {self.plots_dir}/")
        return True


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Redis Benchmark Analysis - Plots',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python plot_redis_results.py
  python plot_redis_results.py --results-dir ./my_results
  python plot_redis_results.py --output-dir ./poster_figures
        """
    )
    parser.add_argument('--results-dir', default='results',
                       help='Directory containing result JSON files (default: results)')
    parser.add_argument('--output-dir', default='analysis/plots',
                       help='Directory to save plots (default: analysis/plots)')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("REDIS BENCHMARK ANALYSIS")
    print("Plots")
    print("=" * 80)
    
    analyzer = RedisResultsAnalyzer(args.results_dir)
    analyzer.plots_dir = Path(args.output_dir)
    analyzer.plots_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\nResults directory: {args.results_dir}")
    print(f"Output directory:  {args.output_dir}")
    print("-" * 40)
    
    if not analyzer.load_all_results():
        print("\nERROR: No results loaded. Exiting.")
        return 1
    
    if not analyzer.generate_all_plots():
        print("\nERROR: Failed to generate plots.")
        return 1
    
    print("\n✓ Analysis complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
