import os
import csv
import re
import argparse
import math
from pathlib import Path
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np

def calculate_average(iterable):
    """Calculates the arithmetic mean (average) of a list of numbers."""
    if not iterable:
        return 0
    return sum(iterable) / len(iterable)

def calculate_geomean(iterable):
    """Calculates the geometric mean of a list of numbers."""
    valid_vals = [x for x in iterable if x > 0]
    if not valid_vals:
        return 0
    return math.exp(sum(math.log(x) for x in valid_vals) / len(valid_vals))

def main():
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description="Parse ChampSim logs and compare two configurations.")
    parser.add_argument("base_config", help="The baseline configuration name (e.g., 'base')")
    parser.add_argument("comp_config", help="The configuration to compare against the baseline (e.g., 'lru')")
    args = parser.parse_args()

    results_dir = Path("dump")
    # Nested dict: data[config][benchmark] = ipc
    data = defaultdict(dict)
    all_benchmarks = set()

    # Regex to find the IPC line and capture the float
    ipc_pattern = re.compile(r"CPU 0 cumulative IPC:\s+([0-9.]+)")

    # 1. Parse files
    if not results_dir.exists():
        print(f"Error: Directory '{results_dir}' not found.")
        return

    for file_path in results_dir.glob("*.out"):
        filename = file_path.name
        base = filename[:-4] if filename.endswith(".out") else filename
        parts = base.split('.', 1)
        if len(parts) == 2:
            config = parts[0].replace("champsim_", "")
            benchmark = parts[1]
            if benchmark.endswith(".trace.gz"):
                benchmark = benchmark[:-9]
            elif benchmark.endswith(".xz"):
                benchmark = benchmark[:-3]
        else:
            config = base.replace("champsim_", "")
            benchmark = "unknown"
            
        all_benchmarks.add(benchmark)

        try:
            with open(file_path, 'r') as f:
                for line in f:
                    match = ipc_pattern.search(line)
                    if match:
                        data[config][benchmark] = float(match.group(1))
                        break
        except Exception as e:
            print(f"Could not read {file_path}: {e}")

    if not data:
        print("No IPC data was found. Exiting.")
        return

    # 2. Prepare CSV writing (includes arithmetic average of absolute IPCs)
    benchmarks_sorted = sorted(list(all_benchmarks))
    header = ["Config"] + benchmarks_sorted + ["Average IPC"]
    
    output_file = "ipc_results.csv"
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)

        for config in sorted(data.keys()):
            row = [config]
            row_ipcs = []
            
            for bench in benchmarks_sorted:
                ipc = data[config].get(bench, "")
                row.append(ipc)
                if isinstance(ipc, float):
                    row_ipcs.append(ipc)
            
            # Calculate and append Arithmetic Average
            avg_ipc = calculate_average(row_ipcs) if row_ipcs else "N/A"
            row.append(avg_ipc)
            
            writer.writerow(row)

    print(f"Successfully generated {output_file}")

    # 3. Create the specific speedup graph based on CLI arguments
    print(f"Generating speedup plot for '{args.comp_config}' over '{args.base_config}'...")
    
    if args.base_config not in data:
        print(f"Error: Baseline configuration '{args.base_config}' not found in parsed data.")
        print(f"Available configs: {', '.join(data.keys())}")
        return
        
    if args.comp_config not in data:
        print(f"Error: Comparison configuration '{args.comp_config}' not found in parsed data.")
        print(f"Available configs: {', '.join(data.keys())}")
        return

    # Calculate filtered speedups for the chosen comparison
    current_benchmarks = []
    current_speedups = []
    for bench in benchmarks_sorted:
         base_ipc = data[args.base_config].get(bench, 0)
         comp_ipc = data[args.comp_config].get(bench, 0)
         if base_ipc > 0: # Only compare if base IPC is positive
             current_benchmarks.append(bench)
             current_speedups.append(comp_ipc / base_ipc)
    
    if not current_speedups:
        print("No valid benchmarks with positive base IPC found for these configs. Exiting.")
        return

    # Calculate the geometric mean of the speedups
    geomean_speedup = calculate_geomean(current_speedups)
    
    # Append the GeoMean to our lists for plotting
    current_benchmarks.append("GeoMean")
    current_speedups.append(geomean_speedup)

    # Set up colors (blue for normal benchmarks, orange for GeoMean)
    bar_colors = ['#1f77b4'] * (len(current_benchmarks) - 1) + ['#ff7f0e']

    # Create the individual speedup plot
    plt.figure(figsize=(12, 6)) # Slightly wider figure to accommodate the extra bar
    x_indices = np.arange(len(current_benchmarks))
    
    # Capture the bars so we can iterate over them to add labels
    bars = plt.bar(x_indices, current_speedups, width=0.6, color=bar_colors)
    
    # Add numerical labels on top of each bar
    for bar in bars:
        yval = bar.get_height()
        # Format to 3 decimal places. Change '.3f' if you want more/fewer digits
        plt.text(bar.get_x() + bar.get_width()/2, yval + 0.01, f'{yval:.3f}', 
                 ha='center', va='bottom', fontsize=9, fontweight='medium')

    # Extend Y-axis slightly so the top labels don't get cut off
    max_y = max(current_speedups)
    plt.ylim(0, max_y * 1.15) 

    # Customize aesthetics
    plt.xlabel('Benchmarks', fontsize=12, fontweight='bold')
    plt.ylabel(f'Speedup over {args.base_config}', fontsize=12, fontweight='bold')
    plt.title(f'Speedup of {args.comp_config} over {args.base_config}', fontsize=14)
    
    # X-axis ticks
    plt.xticks(x_indices, current_benchmarks, rotation=45, ha='right')
    
    # Y-axis grid
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Reference line at speedup=1
    plt.axhline(y=1, color='gray', linestyle='-', linewidth=1)
    
    # Adjust layout to prevent label overlap
    plt.tight_layout()
    
    # Save the plot
    plot_file = f"speedup_{args.comp_config}_vs_{args.base_config}.png"
    plt.savefig(plot_file, dpi=300, bbox_inches="tight")
    plt.close() 
    
    print(f"Successfully generated {plot_file}")
    print(f"Geometric Mean Speedup: {geomean_speedup:.4f}")

if __name__ == "__main__":
    # main()