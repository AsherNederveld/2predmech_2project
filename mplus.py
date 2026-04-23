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
        "ipc": None,
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

        # Extract IPC
        ipc_matches = re.findall(r"cumulative IPC:\s*([\d.]+)", content)
        if ipc_matches: stats["ipc"] = float(ipc_matches[-1])

        # Extract LLC TOTAL (Access, Hit, Miss, MSHR_Merge)
        llc_tot = re.findall(r"cpu0->LLC TOTAL\s+ACCESS:\s+(\d+)\s+HIT:\s+(\d+)\s+MISS:\s+(\d+)\s+MSHR_MERGE:\s+(\d+)", content)
        if llc_tot:
            stats["llc_total_access"] = int(llc_tot[-1][0])
            stats["llc_total_hit"] = int(llc_tot[-1][1])
            stats["llc_total_miss"] = int(llc_tot[-1][2])
            stats["llc_mshr_merge"] = int(llc_tot[-1][3])

        # Helper function to extract MISS and MSHR_MERGE for specific request types
        def get_req_stats(req_type):
            pattern = rf"cpu0->LLC {req_type}\s+ACCESS:\s+\d+\s+HIT:\s+\d+\s+MISS:\s+(\d+)\s+MSHR_MERGE:\s+(\d+)"
            matches = re.findall(pattern, content)
            if matches:
                return int(matches[-1][0]), int(matches[-1][1])
            return None, None

        load_miss, load_mshr = get_req_stats("LOAD")
        rfo_miss, rfo_mshr = get_req_stats("RFO")
        write_miss, write_mshr = get_req_stats("WRITE")
        pf_miss, pf_mshr = get_req_stats("PREFETCH")

        # Extract LLC PREFETCH (Requested, Issued, Useful, Useless)
        llc_pf = re.findall(r"cpu0->LLC PREFETCH REQUESTED:\s+(\d+)\s+ISSUED:\s+(\d+)\s+USEFUL:\s+(\d+)\s+USELESS:\s+(\d+)", content)
        if llc_pf:
            stats["llc_pf_req"] = int(llc_pf[-1][0])
            stats["llc_pf_issued"] = int(llc_pf[-1][1])
            stats["llc_pf_useful"] = int(llc_pf[-1][2])
            stats["llc_pf_useless"] = int(llc_pf[-1][3])

        # Extract LPC HITS and MISSES
        lpc_hm = re.findall(r"cpu0->LLC LPC_HITS:\s+(\d+)\s+LPC_MISSES:\s+(\d+)", content)
        if lpc_hm:
            stats["lpc_hits"] = int(lpc_hm[-1][0])
            stats["lpc_misses"] = int(lpc_hm[-1][1])

        # Extract LPC INSERTIONS and EVICTIONS
        lpc_ie = re.findall(r"cpu0->LLC LPC_INSERTIONS:\s+(\d+)\s+LPC_EVICTIONS:\s+(\d+)", content)
        if lpc_ie:
            stats["lpc_insertions"] = int(lpc_ie[-1][0])
            stats["lpc_evictions"] = int(lpc_ie[-1][1])

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
    fig_width = max(20, len(benchmarks) * 0.3)
    plt.figure(figsize=(fig_width, 8))
    
    x = np.arange(len(benchmarks))
    width = 0.8 / len(speedup_dict)
    
    for i, (exp_label, ratios) in enumerate(speedup_dict.items()):
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
    plt.ylabel('Geometric Mean Speedup (%)')
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
    dump_dir = os.path.join(script_dir, "google_experiments")
    
    # --- CONFIGURATION ---
    base_prefix = "champsim_lru_no_17_nlpc_llc_filtNone_256_32_prom_lru"
    exp_prefixes = [
    # "champsim_mockingjay.orig_no_17_nlpc_llc_filtNone_256_32_prom_lru",
    # "champsim_pacman_no_17_nlpc_llc_filtNone_256_32_prom_lru",
    # "champsim_drrip_no_17_nlpc_llc_filtNone_256_32_prom_lru",
    # "champsim_ship_no_17_nlpc_llc_filtNone_256_32_prom_lru",
    # "champsim_srrip_no_17_nlpc_llc_filtNone_256_32_prom_lru",
    # "champsim_random_no_17_nlpc_llc_filtNone_256_32_prom_lru",
    # "champsim_lru_no_17_nlpc_llc_filtNone_256_32_prom_lru",
    # No pref_filter
    # "champsim_mockingjay.orig_no_17_nlpc_llc_filtAll_256_32_prom_lru",
    # "champsim_pacman_no_17_nlpc_llc_filtAll_256_32_prom_lru",
    # "champsim_drrip_no_17_nlpc_llc_filtAll_256_32_prom_lru",
    # "champsim_ship_no_17_nlpc_llc_filtAll_256_32_prom_lru",
    # "champsim_srrip_no_17_nlpc_llc_filtAll_256_32_prom_lru",
    # "champsim_random_no_17_nlpc_llc_filtAll_256_32_prom_lru",
    # "champsim_lru_no_17_nlpc_llc_filtAll_256_32_prom_lru",

    # pythia pref_base
    # "champsim_mockingjay.orig_pythia_17_nlpc_llc_filtNone_256_32_prom_lru",
    # "champsim_pacman_pythia_17_nlpc_llc_filtNone_256_32_prom_lru",
    # "champsim_drrip_pythia_17_nlpc_llc_filtNone_256_32_prom_lru",
    # "champsim_ship_pythia_17_nlpc_llc_filtNone_256_32_prom_lru",
    # "champsim_srrip_pythia_17_nlpc_llc_filtNone_256_32_prom_lru",
    # "champsim_random_pythia_17_nlpc_llc_filtNone_256_32_prom_lru",
    # "champsim_lru_pythia_17_nlpc_llc_filtNone_256_32_prom_lru",

    # triage pref_base
    # "champsim_mockingjay.orig_triage_17_nlpc_llc_filtNone_256_32_prom_lru",
    # "champsim_pacman_triage_17_nlpc_llc_filtNone_256_32_prom_lru",
    # "champsim_drrip_triage_17_nlpc_llc_filtNone_256_32_prom_lru",
    # "champsim_ship_triage_17_nlpc_llc_filtNone_256_32_prom_lru",
    # "champsim_srrip_triage_17_nlpc_llc_filtNone_256_32_prom_lru",
    # "champsim_random_triage_17_nlpc_llc_filtNone_256_32_prom_lru",
    # "champsim_lru_triage_17_nlpc_llc_filtNone_256_32_prom_lru",

    # sms pref_base
    # "champsim_mockingjay.orig_sms_17_nlpc_llc_filtNone_256_32_prom_lru",
    # "champsim_pacman_sms_17_nlpc_llc_filtNone_256_32_prom_lru",
    # "champsim_drrip_sms_17_nlpc_llc_filtNone_256_32_prom_lru",
    # "champsim_ship_sms_17_nlpc_llc_filtNone_256_32_prom_lru",
    # "champsim_srrip_sms_17_nlpc_llc_filtNone_256_32_prom_lru",
    # "champsim_random_sms_17_nlpc_llc_filtNone_256_32_prom_lru",
    # "champsim_lru_sms_17_nlpc_llc_filtNone_256_32_prom_lru",

    # pythia pref_bp
    # "champsim_mockingjay.orig_pythia_17_nlpc_llc_filtNonLLC_256_32_prom_lru",
    # "champsim_pacman_pythia_17_nlpc_llc_filtNonLLC_256_32_prom_lru",
    # "champsim_drrip_pythia_17_nlpc_llc_filtNonLLC_256_32_prom_lru",
    # "champsim_ship_pythia_17_nlpc_llc_filtNonLLC_256_32_prom_lru",
    # "champsim_srrip_pythia_17_nlpc_llc_filtNonLLC_256_32_prom_lru",
    # "champsim_random_pythia_17_nlpc_llc_filtNonLLC_256_32_prom_lru",
    # "champsim_lru_pythia_17_nlpc_llc_filtNonLLC_256_32_prom_lru",

    # triage pref_bp
    # "champsim_mockingjay.orig_triage_17_nlpc_llc_filtNonLLC_256_32_prom_lru",
    # "champsim_pacman_triage_17_nlpc_llc_filtNonLLC_256_32_prom_lru",
    # "champsim_drrip_triage_17_nlpc_llc_filtNonLLC_256_32_prom_lru",
    # "champsim_ship_triage_17_nlpc_llc_filtNonLLC_256_32_prom_lru",
    # "champsim_srrip_triage_17_nlpc_llc_filtNonLLC_256_32_prom_lru",
    # "champsim_random_triage_17_nlpc_llc_filtNonLLC_256_32_prom_lru",
    # "champsim_lru_triage_17_nlpc_llc_filtNonLLC_256_32_prom_lru",

    # sms pref_bp
    # "champsim_mockingjay.orig_sms_17_nlpc_llc_filtNonLLC_256_32_prom_lru",
    # "champsim_pacman_sms_17_nlpc_llc_filtNonLLC_256_32_prom_lru",
    # "champsim_drrip_sms_17_nlpc_llc_filtNonLLC_256_32_prom_lru",
    # "champsim_ship_sms_17_nlpc_llc_filtNonLLC_256_32_prom_lru",
    # "champsim_srrip_sms_17_nlpc_llc_filtNonLLC_256_32_prom_lru",
    # "champsim_random_sms_17_nlpc_llc_filtNonLLC_256_32_prom_lru",
    # "champsim_lru_sms_17_nlpc_llc_filtNonLLC_256_32_prom_lru",

    # pythia pref_lpc
    # "champsim_mockingjay.orig_pythia_16_lpc_llc_filtAll_256_32_nprom_lru",
    # "champsim_pacman_pythia_16_lpc_llc_filtAll_256_32_nprom_lru",
    # "champsim_drrip_pythia_16_lpc_llc_filtAll_256_32_nprom_lru",
    # "champsim_ship_pythia_16_lpc_llc_filtAll_256_32_nprom_lru",
    # "champsim_srrip_pythia_16_lpc_llc_filtAll_256_32_nprom_lru",
    # "champsim_random_pythia_16_lpc_llc_filtAll_256_32_nprom_lru",
    # "champsim_lru_pythia_16_lpc_llc_filtAll_256_32_nprom_lru",

    # triage pref_lpc
    # "champsim_mockingjay.orig_triage_16_lpc_llc_filtAll_256_32_nprom_lru",
    # "champsim_pacman_triage_16_lpc_llc_filtAll_256_32_nprom_lru",
    # "champsim_drrip_triage_16_lpc_llc_filtAll_256_32_nprom_lru",
    # "champsim_ship_triage_16_lpc_llc_filtAll_256_32_nprom_lru",
    # "champsim_srrip_triage_16_lpc_llc_filtAll_256_32_nprom_lru",
    # "champsim_random_triage_16_lpc_llc_filtAll_256_32_nprom_lru",
    # "champsim_lru_triage_16_lpc_llc_filtAll_256_32_nprom_lru",
    
    # sms pref_lpc
    # "champsim_mockingjay.orig_sms_16_lpc_llc_filtAll_256_32_nprom_lru",
    # "champsim_pacman_sms_16_lpc_llc_filtAll_256_32_nprom_lru",
    # "champsim_drrip_sms_16_lpc_llc_filtAll_256_32_nprom_lru",
    # "champsim_ship_sms_16_lpc_llc_filtAll_256_32_nprom_lru",
    # "champsim_srrip_sms_16_lpc_llc_filtAll_256_32_nprom_lru",
    # "champsim_random_sms_16_lpc_llc_filtAll_256_32_nprom_lru",
    # "champsim_lru_sms_16_lpc_llc_filtAll_256_32_nprom_lru",
    
    # triage pref_lpc_wayset
    # "champsim_mockingjay.orig_triage_16_lpc_llc_filtAll_8192_1_nprom_lru",
    # "champsim_mockingjay.orig_triage_16_lpc_llc_filtAll_4096_2_nprom_lru",
    # "champsim_mockingjay.orig_triage_16_lpc_llc_filtAll_2048_4_nprom_lru",
    # "champsim_mockingjay.orig_triage_16_lpc_llc_filtAll_1024_8_nprom_lru",
    # "champsim_mockingjay.orig_triage_16_lpc_llc_filtAll_512_16_nprom_lru",
    # #champsim_mockingjay.orig_triage_16_lpc_llc_filtAll_256_32_nprom_lru",
    # "champsim_mockingjay.orig_triage_16_lpc_llc_filtAll_128_64_nprom_lru",
    # "champsim_mockingjay.orig_triage_16_lpc_llc_filtAll_64_128_nprom_lru",
    # "champsim_mockingjay.orig_triage_16_lpc_llc_filtAll_32_256_nprom_lru",
    # "champsim_mockingjay.orig_triage_16_lpc_llc_filtAll_16_512_nprom_lru",

    # triage pref_lpc_repl
    "champsim_mockingjay.orig_triage_16_lpc_llc_filtAll_256_32_nprom_lru",
    "champsim_mockingjay.orig_triage_16_lpc_llc_filtAll_256_32_nprom_srrip",
    "champsim_mockingjay.orig_triage_16_lpc_llc_filtAll_256_32_nprom_random"

    # triage pref_lpc_size
    #champsim_mockingjay.orig_triage_16_lpc_llc_filtAll_256_32_nprom_lru",
    # "champsim_mockingjay.orig_triage_16_lpc_all_filtAll_256_32_nprom_lru",

    # "champsim_mockingjay.orig_triage_15_lpc_llc_filtAll_256_64_nprom_lru",
    # "champsim_mockingjay.orig_triage_15_lpc_all_filtAll_256_64_nprom_lru",

    # "champsim_mockingjay.orig_triage_14_lpc_llc_filtAll_256_96_nprom_lru",
    # "champsim_mockingjay.orig_triage_14_lpc_all_filtAll_256_96_nprom_lru",
    
    # "champsim_mockingjay.orig_triage_13_lpc_llc_filtAll_256_128_nprom_lru",
    # "champsim_mockingjay.orig_triage_13_lpc_all_filtAll_256_128_nprom_lru",

    # "champsim_mockingjay.orig_triage_12_lpc_llc_filtAll_256_160_nprom_lru",
    # "champsim_mockingjay.orig_triage_12_lpc_all_filtAll_256_160_nprom_lru",

    # "champsim_mockingjay.orig_triage_11_lpc_llc_filtAll_256_192_nprom_lru",
    # "champsim_mockingjay.orig_triage_11_lpc_all_filtAll_256_192_nprom_lru"
 ]

    output_filename = f"./new_res/results_{base_prefix}_vs_{exp_prefixes[0]}.csv"
    os.makedirs("./new_res", exist_ok=True)

    if not os.path.exists(dump_dir):
        print(f"Error: Directory {dump_dir} does not exist.")
        return

    all_files = os.listdir(dump_dir)
    
    all_prefixes = [base_prefix] + exp_prefixes
    dynamic_benchmarks = get_dynamic_benchmarks(all_prefixes, all_files)
    
    if not dynamic_benchmarks:
        print("No benchmarks found matching the given prefixes in the dump directory.")
        return

    print(f"Found {len(dynamic_benchmarks)} benchmarks dynamically.")

    # Define the statistics keys and header titles
    stat_mappings = {
        "IPC": "ipc",
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
    graph_speedups = {exp: [] for exp in exp_prefixes}

    with open(output_filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()

        for bench in dynamic_benchmarks:
            if "deg" in bench:
                continue
            
            row = {"Benchmark": bench}
            
            # --- BASELINE EXTRACTION ---
            baseline_file = find_file(base_prefix, bench, all_files)
            b_path = os.path.join(dump_dir, baseline_file) if baseline_file else None
            b_stats = extract_stats(b_path)
            
            # Fill Baseline row data
            for header_k, dict_k in stat_mappings.items():
                val = b_stats[dict_k]
                if dict_k == "ipc" and val is None:
                    val = 0.3576000 # Your hardcoded fallback
                row[f"Baseline_{header_k}"] = val if val is not None else "N/A"
            
            baseline_ipc = row["Baseline_IPC"]
            graph_benchmarks.append(bench)

            # --- EXPERIMENT EXTRACTION ---
            for exp in exp_prefixes:
                exp_file = find_file(exp, bench, all_files)
                e_path = os.path.join(dump_dir, exp_file) if exp_file else None
                e_stats = extract_stats(e_path)
                
                # Fill Exp row data
                for header_k, dict_k in stat_mappings.items():
                    val = e_stats[dict_k]
                    row[f"{exp}_{header_k}"] = val if val is not None else "N/A"
                
                exp_ipc = e_stats["ipc"]
                
                # Speedup calculation
                if isinstance(baseline_ipc, float) and isinstance(exp_ipc, float) and baseline_ipc > 0:
                    ratio = exp_ipc / baseline_ipc
                    graph_speedups[exp].append(ratio)
                    row[f"{exp}_Speedup"] = f"{((ratio - 1) * 100):.2f}%"
                else:
                    graph_speedups[exp].append(None)
                    row[f"{exp}_Speedup"] = "N/A"
                
            writer.writerow(row)
            
    print(f"Data successfully output to {output_filename}")

    # Geometric Mean Summary and Storage
    print("\n--- Summary (Geometric Mean Speedup) ---")
    geomean_data = {}
    for exp in exp_prefixes:
        valid_ratios = [r for r in graph_speedups[exp] if r is not None]
        if valid_ratios:
            gmean = statistics.geometric_mean(valid_ratios)
            speedup_pct = (gmean - 1) * 100
            geomean_data[exp] = speedup_pct
            print(f"{exp}: {speedup_pct:.2f}%")
        else:
            print(f"{exp}: No data")

    # Generate Graphs
    plot_results(graph_benchmarks, graph_speedups, output_filename)
    plot_geomean_results(geomean_data, output_filename)

if __name__ == "__main__":
    main()