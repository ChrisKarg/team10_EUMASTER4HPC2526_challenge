import re
import sys
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# Apply a professional style
plt.style.use('ggplot')

def parse_sysbench_output(filepath):
    """
    Parses the sysbench text output to extract time-series data
    and summary statistics.
    """
    time_series_data = []
    summary_stats = {
        'read': 0, 'write': 0, 'other': 0, 'total': 0,
        'lat_min': 0, 'lat_avg': 0, 'lat_max': 0, 'lat_95': 0
    }

    ts_pattern = re.compile(
        r"\[\s+(?P<time>\d+)s\s+\] thds: \d+ tps: (?P<tps>[\d.]+) qps: (?P<qps>[\d.]+) "
        r"\(r/w/o: (?P<read>[\d.]+)/(?P<write>[\d.]+)/(?P<other>[\d.]+)\) "
        r"lat \(ms,95%\): (?P<lat>[\d.]+)"
    )

    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()
            
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            # 1. Parse Time Series Data
            match = ts_pattern.search(line)
            if match:
                data = match.groupdict()
                time_series_data.append({
                    'time': int(data['time']),
                    'tps': float(data['tps']),
                    'qps': float(data['qps']),
                    'read_qps': float(data['read']),
                    'write_qps': float(data['write']),
                    'other_qps': float(data['other']),
                    'lat_95': float(data['lat'])
                })
                continue

            # 2. Parse Summary Statistics
            if "SQL statistics:" in line:
                current_section = "sql"
            elif "Latency (ms):" in line:
                current_section = "latency"

            if current_section == "sql":
                if line.startswith("read:"):
                    summary_stats['read'] = int(line.split()[-1])
                elif line.startswith("write:"):
                    summary_stats['write'] = int(line.split()[-1])
                elif line.startswith("other:"):
                    summary_stats['other'] = int(line.split()[-1])
                elif line.startswith("total:"):
                    summary_stats['total'] = int(line.split()[-1])

            if current_section == "latency":
                if line.startswith("min:"):
                    summary_stats['lat_min'] = float(line.split()[-1])
                elif line.startswith("avg:"):
                    summary_stats['lat_avg'] = float(line.split()[-1])
                elif line.startswith("max:"):
                    summary_stats['lat_max'] = float(line.split()[-1])
                elif line.startswith("95th percentile:"):
                    summary_stats['lat_95'] = float(line.split()[-1])

        df = pd.DataFrame(time_series_data)
        return df, summary_stats

    except FileNotFoundError:
        print(f"Error: The file '{filepath}' was not found.")
        sys.exit(1)

def plot_timeline_smoothed(df):
    """Generates a dual-axis chart with Rolling Averages to show trends clearly."""
    fig, ax1 = plt.subplots(figsize=(12, 6))

    # Calculate Rolling Averages (Window = 3 measurements)
    df['tps_smooth'] = df['tps'].rolling(window=3, center=True).mean()
    df['lat_smooth'] = df['lat_95'].rolling(window=3, center=True).mean()

    # Plot TPS (Left Axis)
    color_tps = '#348ABD' # Blueish
    ax1.set_xlabel('Time (s)')
    ax1.set_ylabel('Transactions per Second (TPS)', color=color_tps, fontweight='bold')
    
    # Raw data (faint)
    ax1.plot(df['time'], df['tps'], color=color_tps, alpha=0.3, linewidth=1, label='TPS (Raw)')
    # Smooth data (bold)
    ax1.plot(df['time'], df['tps_smooth'], color=color_tps, linewidth=3, label='TPS (Trend)')
    ax1.tick_params(axis='y', labelcolor=color_tps)
    ax1.grid(True, linestyle='--', alpha=0.6)

    # Plot Latency (Right Axis)
    ax2 = ax1.twinx() 
    color_lat = '#E24A33' # Reddish
    ax2.set_ylabel('95th Percentile Latency (ms)', color=color_lat, fontweight='bold')
    
    # Raw data (faint)
    ax2.plot(df['time'], df['lat_95'], color=color_lat, alpha=0.3, linestyle='--', linewidth=1, label='Latency (Raw)')
    # Smooth data (bold)
    ax2.plot(df['time'], df['lat_smooth'], color=color_lat, linestyle='--', linewidth=3, label='Latency (Trend)')
    ax2.tick_params(axis='y', labelcolor=color_lat)
    
    # Combined Legend
    lines_1, labels_1 = ax1.get_legend_handles_labels()
    lines_2, labels_2 = ax2.get_legend_handles_labels()
    ax1.legend(lines_1 + lines_2, labels_1 + labels_2, loc='upper center', bbox_to_anchor=(0.5, 1.1), ncol=4)

    plt.title('System Stability: Throughput vs. Latency (Smoothed)', y=1.12, fontsize=14)
    fig.tight_layout()
    plt.savefig('sysbench_timeline_smoothed.png')
    print("Saved sysbench_timeline_smoothed.png")

def plot_correlation(df):
    """Scatter plot of TPS vs Latency to show saturation curve."""
    plt.figure(figsize=(10, 6))
    
    # Scatter plot
    plt.scatter(df['tps'], df['lat_95'], color='#988ED5', alpha=0.8, edgecolors='white', s=80, label='Data Point')
    
    # Trendline (Linear fit)
    z = np.polyfit(df['tps'], df['lat_95'], 1)
    p = np.poly1d(z)
    plt.plot(df['tps'], p(df['tps']), "k--", alpha=0.5, label=f"Trend")

    plt.title('Performance Curve: Throughput vs. Latency', fontsize=14)
    plt.xlabel('Transactions per Second (TPS)', fontweight='bold')
    plt.ylabel('95th Percentile Latency (ms)', fontweight='bold')
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.6)
    
    plt.tight_layout()
    plt.savefig('sysbench_correlation.png')
    print("Saved sysbench_correlation.png")

def plot_qps_breakdown(df):
    """Stacked area chart for QPS."""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    ax.stackplot(df['time'], 
                 df['read_qps'], df['write_qps'], df['other_qps'],
                 labels=['Read', 'Write', 'Other'],
                 colors=['#348ABD', '#FBC15E', '#8EBA42'], alpha=0.9)
    
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Queries per Second (QPS)', fontweight='bold')
    ax.set_title('Workload Composition (Read/Write Mix)', fontsize=14)
    ax.legend(loc='upper left', frameon=True, facecolor='white')
    
    plt.tight_layout()
    plt.savefig('sysbench_qps_breakdown.png')
    print("Saved sysbench_qps_breakdown.png")

def plot_summary_stats(stats):
    """Bar charts for summary stats."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # 1. Total Operations
    labels = ['Read', 'Write', 'Other']
    values = [stats['read'], stats['write'], stats['other']]
    colors = ['#348ABD', '#FBC15E', '#8EBA42']
    
    bars = ax1.bar(labels, values, color=colors)
    ax1.set_title('Total Queries Performed', fontsize=12)
    ax1.set_ylabel('Count')
    
    for bar in bars:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:,}', ha='center', va='bottom', fontsize=10, fontweight='bold')

    # 2. Latency Distribution
    lat_labels = ['Min', 'Avg', '95th %', 'Max']
    lat_values = [stats['lat_min'], stats['lat_avg'], stats['lat_95'], stats['lat_max']]
    lat_colors = ['#8EBA42', '#348ABD', '#FBC15E', '#E24A33'] # Green, Blue, Orange, Red
    
    bars2 = ax2.bar(lat_labels, lat_values, color=lat_colors)
    ax2.set_title('Latency Statistics (ms)', fontsize=12)
    ax2.set_ylabel('Time (ms)')
    
    for bar in bars2:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.2f}', ha='center', va='bottom', fontsize=10, fontweight='bold')

    plt.suptitle("Sysbench Run Summary", fontsize=16)
    plt.tight_layout()
    plt.savefig('sysbench_summary.png')
    print("Saved sysbench_summary.png")

if __name__ == "__main__":
    filename = sys.argv[1] if len(sys.argv) > 1 else 'results.txt'
    
    print(f"Processing file: {filename}...")
    df, stats = parse_sysbench_output(filename)
    
    if df.empty:
        print("No time-series data found! Check file format.")
    else:
        plot_timeline_smoothed(df)
        plot_correlation(df)
        plot_qps_breakdown(df)
        plot_summary_stats(stats)
        print("Done! 4 charts generated.")