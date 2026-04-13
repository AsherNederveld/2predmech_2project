import os
import csv
import re
import subprocess
import statistics
import matplotlib.pyplot as plt
import numpy as np

BENCHMARK_ORDER = [
    "astar_163B", "astar_23B", "astar_313B",
    "bfs__amazon-2008-mtx__17000000000", "bfs__amazon-2008-mtx__19000000000",
    "bfs__amazon-2008-mtx__23000000000", "bfs__citationCiteseer-mtx__1000000000",
    "bfs__citationCiteseer-mtx__4000000000", "bfs__citationCiteseer-mtx__7000000000",
    "bfs__com-Youtube-mtx__11000000000", "bfs__com-Youtube-mtx__14000000000",
    "bfs__com-Youtube-mtx__5000000000", "bfs__dblp-2010-mtx__1000000000",
    "bfs__dblp-2010-mtx__4000000000", "bfs__luxembourg_osm-mtx__0",
    "bfs__netherlands_osm-mtx__37000000000", "bfs__netherlands_osm-mtx__4000000000",
    "bwaves_1609B", "bwaves_1861B", "bwaves_98B",
    "calculix_2655B", "calculix_2670B", "calculix_3812B",
    "cc__amazon-2008-mtx__17000000000", "cc__amazon-2008-mtx__19000000000",
    "cc__amazon-2008-mtx__25000000000", "cc__citationCiteseer-mtx__1000000000",
    "cc__citationCiteseer-mtx__5000000000", "cc__com-Youtube-mtx__11000000000",
    "cc__com-Youtube-mtx__13000000000", "cc__com-Youtube-mtx__4000000000",
    "cc__dblp-2010-mtx__1000000000", "cc__dblp-2010-mtx__3000000000",
    "cc__dblp-2010-mtx__6000000000", "cc__luxembourg_osm-mtx__0",
    "cc__netherlands_osm-mtx__11000000000", "cc__netherlands_osm-mtx__2000000000",
    "gcc_13B", "gcc_39B", "gcc_56B",
    "mcf_158B", "mcf_250B", "mcf_46B",
    "omnetpp_17B", "omnetpp_340B", "omnetpp_4B",
    "perlbench_105B", "perlbench_135B", "perlbench_53B",
    "bfs__kron-18__269000000000", "bfs__urand-17__39000000000",
    "bfs__urand-17__699000000000", "bfs__urand-18__1342000000000",
    "bfs__urand-18__2050000000000", "cc__kron-18__366000000000",
    "cc__urand-17__1304000000000", "cc__urand-17__550000000000",
    "cc__urand-18__2669000000000", "soplex_205B",
    "soplex_217B", "soplex_66B", "sphinx3_1339B",
    "sphinx3_2520B", "sphinx3_883B", "xalancbmk_748B",
    "xalancbmk_768B", "xalancbmk_99B"
]

def normalize(name):
    return name.replace('-', '_').replace('.', '_').lower()

def extract_stats(filepath):
    stats = {"ipc": None, "hits": None, "inserts": None}
    if not filepath or not os.path.exists(filepath):
        return stats
    try:
        cmd = f"grep -E 'cumulative IPC|Total Hits in buffer|Total Inserted into buffer' '{filepath}'"
        out = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL)
        ipc_matches = re.findall(r"cumulative IPC:\s*([\d.]+)", out)
        hits_matches = re.findall(r"(\d+)\s*Total Hits in buffer", out)
        ins_matches = re.findall(r"(\d+)\s*Total Inserted into buffer", out)
        if ipc_matches: stats["ipc"] = float(ipc_matches[-1])
        if hits_matches: stats["hits"] = int(hits_matches[-1])
        if ins_matches: stats["inserts"] = int(ins_matches[-1])
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

def plot_results(benchmarks, speedup_dict, output_path):
    """Generates a bar chart for speedup comparisons."""
    plt.figure(figsize=(20, 8))
    
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
    base_prefix = "champsim_drrip_base"
    exp_prefixes = ["champsim_drrip_bypass", "champsim_drrip_aggressive"] # Add more as needed
    # ---------------------

    # Generate dynamic filename based on inputs
    exp_tag = "_vs_".join(exp_prefixes)
    output_filename = f"./new_res/results_{base_prefix}_vs_{exp_tag}.csv"
    
    os.makedirs("./new_res", exist_ok=True)

    if not os.path.exists(dump_dir):
        print(f"Error: Directory {dump_dir} does not exist.")
        return

    all_files = os.listdir(dump_dir)
    all_files.sort()

    # Dynamic headers
    headers = ["Benchmark", "Baseline_IPC"]
    for exp in exp_prefixes:
        headers += [f"{exp}_IPC", f"{exp}_Speedup", f"{exp}_HitRate"]

    # Storage for graphing
    graph_benchmarks = []
    # Dict mapping exp_prefix -> list of ratios per benchmark
    graph_speedups = {exp: [] for exp in exp_prefixes}

    with open(output_filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()

        for bench in BENCHMARK_ORDER:
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
                
                # Hit Rate calculation
                if e_stats["hits"] is not None and e_stats["inserts"] is not None:
                    total = e_stats["hits"] + e_stats["inserts"]
                    row[f"{exp}_HitRate"] = f"{(e_stats['hits'] / total * 100):.2f}%" if total > 0 else "0.00%"
                else:
                    row[f"{exp}_HitRate"] = "N/A"
                
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