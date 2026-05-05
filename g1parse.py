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

        # --- MODIFICATION: Skip configs containing "new" or "llc" ---
        config_lower = config.lower()
        if "new" in config_lower or "lpc" in config_lower:
            continue
        # -----------------------------------------------------------

        try:
            with open(file_path, 'r') as f:
                for line in f:
                    match = ipc_pattern.search(line)
                    if match:
                        data[config][benchmark] = float(match.group(1))
                        all_benchmarks.add(benchmark)
                        break
        except Exception as e:
            print(f"Could not read {file_path}: {e}")

    # 1.5 FILTER: Identify and remove traces (columns) with an IPC < 1.0
    traces_to_remove = set()
    for config, benches in data.items():
        for bench, ipc in benches.items():
            if ipc < 1.0:
                traces_to_remove.add(bench)

    # Remove the disqualified traces from our master list
    all_benchmarks -= traces_to_remove

    # 2. Prepare CSV writing
    benchmarks_sorted = sorted(list(all_benchmarks))
    header = ["Config", "Geometric Mean"] + benchmarks_sorted
    
    output_file = "ipc_results.csv"
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)

        for config in sorted(data.keys()):
            row_ipcs = []
            bench_values = []
            
            for bench in benchmarks_sorted:
                # Get the IPC; since we filtered traces_to_remove, 
                # any value here is guaranteed to be >= 1.0 or missing
                ipc = data[config].get(bench, "")
                bench_values.append(ipc)
                
                if isinstance(ipc, (float, int)):
                    row_ipcs.append(ipc)
            
            # Calculate GeoMean
            gmean = calculate_geomean(row_ipcs) if row_ipcs else "N/A"
            
            # Print to console
            print(f"Config: {config} | GeoMean: {gmean} | IPCs: {bench_values}")

            # Construct the final row: [Config, GeoMean, Bench1, Bench2, ...]
            final_row = [config, gmean] + bench_values
            writer.writerow(final_row)

    print(f"\nSuccessfully generated {output_file}")
    if traces_to_remove:
        print(f"Note: Removed columns for traces (IPC < 1.0): {', '.join(traces_to_remove)}")

if __name__ == "__main__":
    main()