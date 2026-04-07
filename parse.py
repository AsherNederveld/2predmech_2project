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
            
            # Calculate and append GeoMean
            gmean = calculate_geomean(row_ipcs) if row_ipcs else "N/A"
            row.append(gmean)
            
            writer.writerow(row)

    print(f"Successfully generated {output_file}")

if __name__ == "__main__":
    main()