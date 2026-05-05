import os
import csv
import re
import statistics
import matplotlib.pyplot as plt
import numpy as np

def normalize(name):
    return name.replace('-', '_').replace('.', '_').lower()

def extract_stats(filepath):
    # Initialize all requested stats
    stats = {
        "ipc_0": None, "ipc_1": None, "ipc_2": None, "ipc_3": None,
        "llc_total_access": None,
        "llc_total_hit": None,
        "llc_total_miss": None,
        "llc_mshr_merge": None,
        "llc_insertions": None,
        "llc_pf_req": None,
        "llc_pf_issued": None,
        "llc_pf_useful": None,
        "llc_pf_useless": None,
        "lpc_hits": None,
        "lpc_misses": None,
        "lpc_insertions": None,
        "lpc_evictions": None
    }
    
    if not filepath or not os.path.exists(filepath):
        return stats
        
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Extract IPC for 4 cores
        for core in range(4):
            ipc_matches = re.findall(rf"CPU {core} cumulative IPC:\s*([\d.]+)", content)
            if ipc_matches: stats[f"ipc_{core}"] = float(ipc_matches[-1])

        def get_last_match(pattern):
            matches = re.findall(pattern, content)
            if matches: return matches[-1]
            return None

        # Helper to sum stats across all 4 cores
        def sum_stats(regex_pattern, num_groups):
            totals = [0] * num_groups
            found = False
            for core in range(4):
                pattern = regex_pattern.replace("CPU_ID", str(core))
                last_match = get_last_match(pattern)
                if last_match:
                    found = True
                    for i in range(num_groups):
                        totals[i] += int(last_match[i])
            return totals if found else [None] * num_groups

        # Extract LLC TOTAL (Access, Hit, Miss, MSHR_Merge)
        llc_tot = sum_stats(r"cpuCPU_ID->LLC TOTAL\s+ACCESS:\s+(\d+)\s+HIT:\s+(\d+)\s+MISS:\s+(\d+)\s+MSHR_MERGE:\s+(\d+)", 4)
        if llc_tot[0] is not None:
            stats["llc_total_access"] = llc_tot[0]
            stats["llc_total_hit"] = llc_tot[1]
            stats["llc_total_miss"] = llc_tot[2]
            stats["llc_mshr_merge"] = llc_tot[3]

        def get_req_stats(req_type):
            pattern = rf"cpuCPU_ID->LLC {req_type}\s+ACCESS:\s+\d+\s+HIT:\s+\d+\s+MISS:\s+(\d+)\s+MSHR_MERGE:\s+(\d+)"
            return sum_stats(pattern, 2)

        load_miss, load_mshr = get_req_stats("LOAD")
        rfo_miss, rfo_mshr = get_req_stats("RFO")
        write_miss, write_mshr = get_req_stats("WRITE")
        pf_miss, pf_mshr = get_req_stats("PREFETCH")

        # Extract LLC PREFETCH (Requested, Issued, Useful, Useless)
        llc_pf = sum_stats(r"cpuCPU_ID->LLC PREFETCH REQUESTED:\s+(\d+)\s+ISSUED:\s+(\d+)\s+USEFUL:\s+(\d+)\s+USELESS:\s+(\d+)", 4)
        if llc_pf[0] is not None:
            stats["llc_pf_req"] = llc_pf[0]
            stats["llc_pf_issued"] = llc_pf[1]
            stats["llc_pf_useful"] = llc_pf[2]
            stats["llc_pf_useless"] = llc_pf[3]

        # Extract LPC HITS and MISSES
        lpc_hm = sum_stats(r"cpuCPU_ID->LLC LPC_HITS:\s+(\d+)\s+LPC_MISSES:\s+(\d+)", 2)
        if lpc_hm[0] is not None:
            stats["lpc_hits"] = lpc_hm[0]
            stats["lpc_misses"] = lpc_hm[1]

        # Extract LPC INSERTIONS and EVICTIONS
        lpc_ie = sum_stats(r"cpuCPU_ID->LLC LPC_INSERTIONS:\s+(\d+)\s+LPC_EVICTIONS:\s+(\d+)", 2)
        if lpc_ie[0] is not None:
            stats["lpc_insertions"] = lpc_ie[0]
            stats["lpc_evictions"] = lpc_ie[1]

        # Calculate LLC Insertions dynamically based on filename
        filename = os.path.basename(filepath)
        
        if "filtNone" in filename:
            if stats["llc_total_miss"] is not None and stats["llc_mshr_merge"] is not None:
                stats["llc_insertions"] = stats["llc_total_miss"] - stats["llc_mshr_merge"]
                
        elif "filtAll" in filename:
            if all(v is not None for v in [load_miss, load_mshr, rfo_miss, rfo_mshr, write_miss, write_mshr]):
                stats["llc_insertions"] = (load_miss - load_mshr) + (rfo_miss - rfo_mshr) + (write_miss - write_mshr)
                
        elif "filtNonLLC" in filename:
            if all(v is not None for v in [stats["llc_total_miss"], pf_miss, stats["llc_mshr_merge"], pf_mshr, stats["llc_pf_issued"]]):
                stats["llc_insertions"] = (stats["llc_total_miss"] - pf_miss) - (stats["llc_mshr_merge"] - pf_mshr) + stats["llc_pf_issued"]

    except Exception as e:
        print(f"Error extracting stats from {filepath}: {e}")
        
    return stats

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
    fig_width = max(20, len(benchmarks) * 0.3)
    plt.figure(figsize=(fig_width, 8))
    
    x = np.arange(len(benchmarks))
    width = 0.8 / len(speedup_dict)
    
    for i, (exp_label, ratios) in enumerate(speedup_dict.items()):
        pct_values = [(r - 1) * 100 if r is not None else 0 for r in ratios]
        offset = i * width
        plt.bar(x + offset, pct_values, width, label=exp_label)

    plt.axhline(0, color='black', linewidth=0.8)
    plt.ylabel('Geomean Speedup (%) across Cores')
    plt.title('Performance Speedup by Experiment')
    plt.xticks(x + width / 2, benchmarks, rotation=90, fontsize=8)
    plt.legend()
    plt.tight_layout()
    
    graph_filename = output_path.replace('.csv', '.png')
    plt.savefig(graph_filename)
    print(f"Graph saved to {graph_filename}")
    plt.close()

def plot_geomean_results(geomean_dict, output_path):
    """Generates a bar chart specifically for the geometric mean speedups."""
    if not geomean_dict:
        return
        
    labels = list(geomean_dict.keys())
    values = list(geomean_dict.values())
    
    plt.figure(figsize=(max(8, len(labels) * 1.5), 6))
    bars = plt.bar(labels, values, color='cornflowerblue', edgecolor='black')
    
    plt.axhline(0, color='black', linewidth=0.8)
    plt.ylabel('Final Geomean Speedup (%) (Geomean of Core Geomeans)')
    plt.title('Overall Geometric Mean Speedup by Experiment vs Baseline')
    plt.xticks(rotation=45, ha='right', fontsize=10)
    
    for bar in bars:
        yval = bar.get_height()
        va = 'bottom' if yval >= 0 else 'top'
        offset = 0.2 if yval >= 0 else -0.2
        plt.text(bar.get_x() + bar.get_width() / 2, yval + offset, f'{yval:.2f}%', ha='center', va=va, fontsize=10)

    plt.tight_layout()
    
    geomean_graph_filename = output_path.replace('.csv', '_geomean.png')
    plt.savefig(geomean_graph_filename)
    print(f"Geomean graph saved to {geomean_graph_filename}")
    plt.close()

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dump_dir = os.path.join(script_dir, "new_multi_exp")
    
    if not os.path.exists(dump_dir):
        print(f"Error: Directory {dump_dir} does not exist.")
        return

    all_files = os.listdir(dump_dir)
    # Extract unique prefixes assuming format prefix.benchmark.out
    # We will use .config[X] as the benchmark part in multi_exp
    all_prefixes = sorted(list(set(f.replace(".out", "").rsplit(".", 1)[0] for f in all_files if f.endswith(".out"))))

    if not all_prefixes:
        print("No prefixes found in the directory.")
        return
        
    # Attempt to set the base prefix to the one with 'filtNone' and 'prom_lru' to be safe
    base_prefix = "champsim_lru_no_17_nlpc_llc_filtNone_256_32_prom_lru"
    if base_prefix not in all_prefixes:
        base_prefix = all_prefixes[0]
        
    # Define specific experiments to run here. If empty, runs on all prefixes.
    TARGET_EXPERIMENTS = [
        "champsim_mockingjay.orig_no_17_nlpc_llc_filtNone_256_32_prom_lru",
        "champsim_mockingjay.orig_sms_17_nlpc_llc_filtNone_256_32_prom_lru",
        "champsim_mockingjay.orig_sms_17_nlpc_llc_filtNonLLC_256_32_prom_lru",
        "champsim_mockingjay.orig_sms_16_lpc_all_filtAll_256_32_nprom_lru",
        "champsim_mockingjay.orig_sms_16_lpc_llc_filtAll_256_32_nprom_lru"
    ]
    
    if TARGET_EXPERIMENTS:
        exp_prefixes = [p for p in TARGET_EXPERIMENTS if p in all_prefixes and p != base_prefix]
    else:
        exp_prefixes = [p for p in all_prefixes if p != base_prefix]

    output_filename = f"./new_res/multi_results_{base_prefix}_vs_all.csv"
    os.makedirs("./new_res", exist_ok=True)

    print("\n--- Files Found Per Config ---")
    for prefix in [base_prefix] + exp_prefixes:
        count = sum(1 for f in all_files if f.startswith(prefix) and f.endswith('.out'))
        print(f"{prefix}: {count}")
    print("------------------------------\n")

    dynamic_benchmarks = get_dynamic_benchmarks([base_prefix] + exp_prefixes, all_files)
    
    if not dynamic_benchmarks:
        print("No benchmarks found matching the given prefixes in the dump directory.")
        return

    print(f"Found {len(dynamic_benchmarks)} total unique benchmarks dynamically across all configs.")

    # Define the statistics keys and header titles
    stat_mappings = {
        "IPC_0": "ipc_0", "IPC_1": "ipc_1", "IPC_2": "ipc_2", "IPC_3": "ipc_3",
        "LLC_Total_Access": "llc_total_access",
        "LLC_Total_Hit": "llc_total_hit",
        "LLC_Total_Miss": "llc_total_miss",
        "LLC_MSHR_Merge": "llc_mshr_merge",
        "LLC_Insertions": "llc_insertions",
        "LLC_PF_Req": "llc_pf_req",
        "LLC_PF_Useful": "llc_pf_useful",
        "LLC_PF_Useless": "llc_pf_useless",
        "LPC_Hits": "lpc_hits",
        "LPC_Misses": "lpc_misses",
        "LPC_Insertions": "lpc_insertions",
        "LPC_Evictions": "lpc_evictions"
    }

    # Build Dynamic Headers
    headers = ["Benchmark"]
    for k in stat_mappings.keys():
        headers.append(f"Baseline_{k}")
    for exp in exp_prefixes:
        for k in stat_mappings.keys():
            headers.append(f"{exp}_{k}")
        headers.append(f"{exp}_Speedup")

    # Storage for graphing
    graph_benchmarks = []
    
    # Store per-core speedups for geomean calculations
    # exp -> {core -> [speedup_ratio]}
    core_speedups = {exp: {core: [] for core in range(4)} for exp in exp_prefixes}
    
    # Geomean of 4 cores per benchmark for plotting
    graph_speedups = {exp: [] for exp in exp_prefixes}

    with open(output_filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()

        for bench in dynamic_benchmarks:
            if "deg" in bench:
                continue
            
            row = {"Benchmark": bench}
            
            # --- BASELINE EXTRACTION ---
            b_path = os.path.join(dump_dir, f"{base_prefix}.{bench}.out")
            if not os.path.exists(b_path):
                # Fallback to loose match
                for f in all_files:
                    if f.startswith(base_prefix) and bench in f:
                        b_path = os.path.join(dump_dir, f)
                        break
            
            b_stats = extract_stats(b_path)
            
            # Fill Baseline row data
            for header_k, dict_k in stat_mappings.items():
                val = b_stats.get(dict_k)
                row[f"Baseline_{header_k}"] = val if val is not None else "N/A"
            
            baseline_ipcs = [b_stats.get(f"ipc_{c}") for c in range(4)]
            graph_benchmarks.append(bench)

            # --- EXPERIMENT EXTRACTION ---
            for exp in exp_prefixes:
                e_path = os.path.join(dump_dir, f"{exp}.{bench}.out")
                if not os.path.exists(e_path):
                    for f in all_files:
                        if f.startswith(exp) and bench in f:
                            e_path = os.path.join(dump_dir, f)
                            break
                            
                e_stats = extract_stats(e_path)
                
                # Fill Exp row data
                for header_k, dict_k in stat_mappings.items():
                    val = e_stats.get(dict_k)
                    row[f"{exp}_{header_k}"] = val if val is not None else "N/A"
                
                exp_ipcs = [e_stats.get(f"ipc_{c}") for c in range(4)]
                
                bench_ratios = []
                for c in range(4):
                    if isinstance(baseline_ipcs[c], float) and isinstance(exp_ipcs[c], float) and baseline_ipcs[c] > 0:
                        ratio = exp_ipcs[c] / baseline_ipcs[c]
                        core_speedups[exp][c].append(ratio)
                        bench_ratios.append(ratio)
                    else:
                        core_speedups[exp][c].append(None)
                
                if len(bench_ratios) == 4:
                    bench_geomean = statistics.geometric_mean(bench_ratios)
                    graph_speedups[exp].append(bench_geomean)
                    row[f"{exp}_Speedup"] = f"{((bench_geomean - 1) * 100):.2f}%"
                else:
                    graph_speedups[exp].append(None)
                    row[f"{exp}_Speedup"] = "N/A"
                
            writer.writerow(row)
            
    print(f"Data successfully output to {output_filename}")

    # Geometric Mean Summary and Storage
    print("\n--- Summary (Geometric Mean Speedup) ---")
    geomean_data = {}
    for exp in exp_prefixes:
        valid_core_gmeans = []
        for c in range(4):
            valid_ratios = [r for r in core_speedups[exp][c] if r is not None]
            if valid_ratios:
                c_gmean = statistics.geometric_mean(valid_ratios)
                valid_core_gmeans.append(c_gmean)
        
        if len(valid_core_gmeans) == 4:
            final_gmean = statistics.geometric_mean(valid_core_gmeans)
            speedup_pct = (final_gmean - 1) * 100
            geomean_data[exp] = speedup_pct
            print(f"{exp}: {speedup_pct:.2f}%")
        else:
            print(f"{exp}: No complete data for all 4 cores")

    # Generate Graphs
    plot_results(graph_benchmarks, graph_speedups, output_filename)
    plot_geomean_results(geomean_data, output_filename)

if __name__ == "__main__":
    main()
