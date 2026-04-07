import os
import csv
import re
import math
from pathlib import Path
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np

def calculate_geomean(iterable):
    """Calculates the geometric mean of a list of numbers safely."""
    if not iterable:
        return 0
    # Prevent math domain error if an IPC is exactly 0
    if any(x == 0 for x in iterable):
        return 0
    return math.exp(sum(math.log(x) for x in iterable) / len(iterable))

def main():
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

    # 2. Prepare CSV writing (includes geomean of absolute IPCs)
    benchmarks_sorted = sorted(list(all_benchmarks))
    header = ["Config"] + benchmarks_sorted + ["Geometric Mean"]
    
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
            
            # Calculate and append GeoMean (on absolute values)
            gmean = calculate_geomean(row_ipcs) if row_ipcs else "N/A"
            row.append(gmean)
            
            writer.writerow(row)

    print(f"Successfully generated {output_file}")

    # 3. Create individual speedup graphs (One graph per comparison, speedup over base IPC)
    print("Generating individual speedup plots...")
    configs_sorted = sorted(data.keys())
    
    # Check if base configuration exists (assuming processed name 'base')
    if 'base' not in data:
        print("Error: 'base' configuration not found. Cannot calculate speedups/generate speedup plots.")
    else:
        for config in configs_sorted:
            if config == 'base': continue # Skip plotting base speedup vs itself

            # 1. Calculate filtered speedups for this config
            current_benchmarks = []
            current_speedups = []
            for bench in benchmarks_sorted:
                 base_ipc = data['base'].get(bench, 0)
                 config_ipc = data[config].get(bench, 0)
                 if base_ipc > 0: # Only compare if base IPC is positive
                     current_benchmarks.append(bench)
                     current_speedups.append(config_ipc / base_ipc)
            
            if not current_speedups: # No valid comparisons possible for this config
                print(f"No valid benchmarks with positive base IPC found for {config}. Skipping plot.")
                continue

            # 2. Create the individual speedup plot
            plt.figure(figsize=(10, 6)) # Adjust figure size
            x_indices = np.arange(len(current_benchmarks))
            # Single bar chart, no multiple configs side-by-side on one chart
            plt.bar(x_indices, current_speedups, width=0.6) # Standard width
            
            # 3. Customize aesthetics
            plt.xlabel('Benchmarks', fontsize=12, fontweight='bold')
            plt.ylabel('Speedup over base', fontsize=12, fontweight='bold')
            plt.title(f'Speedup of {config} over base IPC', fontsize=14)
            
            # X-axis ticks
            plt.xticks(x_indices, current_benchmarks, rotation=45, ha='right')
            
            # Y-axis grid, no horizontal legends needed as only one config plotted
            plt.grid(axis='y', linestyle='--', alpha=0.7)
            
            # Reference line at speedup=1
            plt.axhline(y=1, color='gray', linestyle='-', linewidth=1)
            
            # Adjust layout to prevent label overlap
            plt.tight_layout()
            
            # 4. Save the plot
            plot_file = f"speedup_{config}_vs_base.png"
            plt.savefig(plot_file, dpi=300, bbox_inches="tight")
            plt.close() # Close figure immediately to prevent memory issues
            print(f"Successfully generated {plot_file}")
        print("Successfully generated all speedup plots.")

if __name__ == "__main__":
    main()