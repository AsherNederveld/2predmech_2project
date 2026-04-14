import os
import csv
import re
import subprocess
import statistics
import matplotlib.pyplot as plt
import numpy as np

def normalize(name):
    return name.replace('-', '_').replace('.', '_').lower()

def extract_stats(filepath):
    stats = {"ipc": None}
    if not filepath or not os.path.exists(filepath):
        return stats
    try:
        cmd = f"grep -E 'cumulative IPC' '{filepath}'"
        out = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL)
        ipc_matches = re.findall(r"cumulative IPC:\s*([\d.]+)", out)
        if ipc_matches: stats["ipc"] = float(ipc_matches[-1])
    except Exception:
        pass
    return stats

def find_file(prefix, bench, all_files):
    norm_bench = normalize(bench)
    for filename in all_files:
        if filename.startswith(prefix) and filename.endswith('.out'):
            if norm_bench in normalize(filename):
                return filename
    return None

def get_dynamic_benchmarks(prefixes, all_files):
    """Dynamically extracts unique benchmark names from filenames based on the provided prefixes."""
    benchmarks = set()
    for filename in all_files:
        if not filename.endswith('.out'):
            continue
        for prefix in prefixes:
            if filename.startswith(prefix):
                # Strip prefix and .out extension
                bench_name = filename[len(prefix):-4]
                # Remove any leading connecting characters like underscores or dashes
                bench_name = bench_name.lstrip('_').lstrip('-')
                if bench_name:
                    benchmarks.add(bench_name)
    return sorted(list(benchmarks))

def plot_results(benchmarks, speedup_dict, output_path):
    """Generates a bar chart for speedup comparisons."""
    # If there are a lot of dynamic benchmarks, we might need a wider figure
    fig_width = max(20, len(benchmarks) * 0.3)
    plt.figure(figsize=(fig_width, 8))
    
    x = np.arange(len(benchmarks))
    width = 0.8 / len(speedup_dict)  # Adjust bar width based on number of experiments
    
    for i, (exp_label, ratios) in enumerate(speedup_dict.items()):
        # Convert ratios to speedup percentage: (ratio - 1) * 100
        pct_values = [(r - 1) * 100 if r is not None else 0 for r in ratios]
        offset = i * width
        plt.bar(x + offset, pct_values, width, label=exp_label)

    plt.axhline(0, color='black', linewidth=0.8)
    plt.ylabel('Speedup (%)')
    plt.title('Performance Speedup by Experiment')
    plt.xticks(x + width / 2, benchmarks, rotation=90, fontsize=8)
    plt.legend()
    plt.tight_layout()
    
    graph_filename = output_path.replace('.csv', '.png')
    plt.savefig(graph_filename)
    print(f"Graph saved to {graph_filename}")

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dump_dir = os.path.join(script_dir, "dump")
    
    # --- CONFIGURATION ---
    # base_prefix = "champsim_mockingjay_nlpc_all_triage"
    # exp_prefixes = ["champsim_mockingjay_nlpc_llc_triage", "champsim_mockingjay_lpc_all_triage", "champsim_mockingjay_lpc_llc_triage"]
   
    # base_prefix = "champsim_mockingjay_base"
    # exp_prefixes = ["champsim_mockingjay_bypass", "champsim_mockingjay_nlpc_all_triage", "champsim_mockingjay_nlpc_llc_triage", "champsim_mockingjay_lpc_all_triage", "champsim_mockingjay_lpc_llc_triage"]    
    
    # base_prefix = "champsim_drrip_base"
    # exp_prefixes = ["champsim_drrip_bypass"]

    base_prefix = "champsim_mockingjay.orig_triage_17_nlpc_llc_filtNone"
    exp_prefixes = ["champsim_mockingjay.orig_triage_17_nlpc_all_filtNonLLC", "champsim_mockingjay.orig_triage_16_lpc_all_filtAll", "champsim_mockingjay.orig_triage_16_lpc_llc_filtAll"]

    # Generate dynamic filename based on inputs
    exp_tag = "_vs_".join(exp_prefixes)
    output_filename = f"./new_res/results_{base_prefix}_vs_{exp_tag}.csv"
    
    os.makedirs("./new_res", exist_ok=True)

    if not os.path.exists(dump_dir):
        print(f"Error: Directory {dump_dir} does not exist.")
        return

    all_files = os.listdir(dump_dir)
    
    # Dynamically grab benchmarks
    all_prefixes = [base_prefix] + exp_prefixes
    dynamic_benchmarks = get_dynamic_benchmarks(all_prefixes, all_files)
    
    if not dynamic_benchmarks:
        print("No benchmarks found matching the given prefixes in the dump directory.")
        return

    print(f"Found {len(dynamic_benchmarks)} benchmarks dynamically.")

    # Dynamic headers
    headers = ["Benchmark", "Baseline_IPC"]
    for exp in exp_prefixes:
        headers += [f"{exp}_IPC", f"{exp}_Speedup"]

    # Storage for graphing
    graph_benchmarks = []
    # Dict mapping exp_prefix -> list of ratios per benchmark
    graph_speedups = {exp: [] for exp in exp_prefixes}

    with open(output_filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()

        for bench in dynamic_benchmarks:
            baseline_file = find_file(base_prefix, bench, all_files)
            b_path = os.path.join(dump_dir, baseline_file) if baseline_file else None
            b_stats = extract_stats(b_path)
            
            row = {"Benchmark": bench, "Baseline_IPC": b_stats["ipc"] if b_stats["ipc"] is not None else "N/A"}
            graph_benchmarks.append(bench)

            for exp in exp_prefixes:
                exp_file = find_file(exp, bench, all_files)
                e_path = os.path.join(dump_dir, exp_file) if exp_file else None
                e_stats = extract_stats(e_path)
                
                ipc = e_stats["ipc"]
                row[f"{exp}_IPC"] = ipc if ipc is not None else "N/A"
                
                # Speedup calculation
                if isinstance(row["Baseline_IPC"], float) and isinstance(ipc, float) and row["Baseline_IPC"] > 0:
                    ratio = ipc / row["Baseline_IPC"]
                    graph_speedups[exp].append(ratio)
                    row[f"{exp}_Speedup"] = f"{((ratio - 1) * 100):.2f}%"
                else:
                    graph_speedups[exp].append(None)
                    row[f"{exp}_Speedup"] = "N/A"
                
            writer.writerow(row)
            
    print(f"Data successfully output to {output_filename}")

    # Geometric Mean Summary
    print("\n--- Summary (Geometric Mean Speedup) ---")
    for exp in exp_prefixes:
        valid_ratios = [r for r in graph_speedups[exp] if r is not None]
        if valid_ratios:
            gmean = statistics.geometric_mean(valid_ratios)
            print(f"{exp}: {((gmean - 1) * 100):.2f}%")
        else:
            print(f"{exp}: No data")

    # Generate Graph
    plot_results(graph_benchmarks, graph_speedups, output_filename)

if __name__ == "__main__":
    main()