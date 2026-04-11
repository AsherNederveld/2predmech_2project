import os
import csv
import re
import math
from pathlib import Path
from collections import defaultdict

def calculate_geomean(iterable):
    """Calculates the geometric mean of a list of numbers."""
    if not iterable:
        return 0
    # Using log-sum to avoid overflow with large products
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

    # 2. Prepare CSV writing
    benchmarks_sorted = sorted(list(all_benchmarks))
    # Moved "Geometric Mean" to the second position in the header
    header = ["Config", "Geometric Mean"] + benchmarks_sorted
    
    output_file = "ipc_results.csv"
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)

        for config in sorted(data.keys()):
            # Collect individual IPCs for this config first
            row_ipcs = []
            bench_values = []
            
            for bench in benchmarks_sorted:
                ipc = data[config].get(bench, "")
                bench_values.append(ipc)
                if isinstance(ipc, (float, int)):
                    row_ipcs.append(ipc)
            
            # Calculate GeoMean
            gmean = calculate_geomean(row_ipcs) if row_ipcs else "N/A"
            
            # Print to console as requested: GeoMean followed by individual IPCs
            print(f"Config: {config} | GeoMean: {gmean} | IPCs: {bench_values}")

            # Construct the final row: [Config, GeoMean, Bench1, Bench2, ...]
            final_row = [config, gmean] + bench_values
            writer.writerow(final_row)

    print(f"\nSuccessfully generated {output_file}")

if __name__ == "__main__":
    main()