import os
import glob
import re
import matplotlib.pyplot as plt
import numpy as np

# Set the experiment directories and the exact output image path
BASELINE_DIR = "/projects/coursework/2026-spring/cs395t-lin/asher/take2/2predmech_2project/new_multi_exp"
EXP_DIR = "/projects/coursework/2026-spring/cs395t-lin/asher/take2/2predmech_2project/new_multi_exp"
OUTPUT_IMG = "/projects/coursework/2026-spring/cs395t-lin/asher/take2/2predmech_2project/multi_speedup.png"

# Define the exact file prefixes
PREFIX_BASELINE = "champsim_mockingjay.orig_triage_17_nlpc_llc_filtNone_256_32_prom_lru"
PREFIX_EXP = "champsim_mockingjay.orig_triage_16_lpc_llc_filtAll_256_32_nprom_lru"

def get_ipcs(filepath):
    """
    Scans a ChampSim trace output file for the final simulation IPCs of all 4 cores.
    Matches: "CPU X cumulative IPC: 0.9159 instructions: 500000002"
    """
    regex = re.compile(r"CPU (\d) cumulative IPC:\s+([0-9.]+)\s+instructions")
    ipcs = {}
    try:
        with open(filepath, 'r') as f:
            for line in f:
                match = regex.search(line)
                if match:
                    core = int(match.group(1))
                    if 0 <= core < 4:
                        ipcs[core] = float(match.group(2))
    except FileNotFoundError:
        print(f"Warning: File not found {filepath}")
    
    if len(ipcs) == 4:
        return [ipcs[0], ipcs[1], ipcs[2], ipcs[3]]
    return None

def extract_trace_name(filename, prefix):
    trace_name = filename.replace(prefix + ".", "")
    trace_name = trace_name.replace(".trace.gz.out", "")
    trace_name = trace_name.replace(".out", "")
    return trace_name

def calculate_geomean(ratios):
    arr = np.array(ratios)
    if (arr <= 0).any() or len(arr) == 0:
        return 1.0
    return np.exp(np.mean(np.log(arr)))

def main():
    baseline_ipcs = {}
    exp_ipcs = {}

    for filepath in glob.glob(os.path.join(BASELINE_DIR, f"{PREFIX_BASELINE}*")):
        filename = os.path.basename(filepath)
        trace_name = extract_trace_name(filename, PREFIX_BASELINE)
        
        ipcs = get_ipcs(filepath)
        if ipcs is not None:
            baseline_ipcs[trace_name] = ipcs

    for filepath in glob.glob(os.path.join(EXP_DIR, f"{PREFIX_EXP}*")):
        filename = os.path.basename(filepath)
        trace_name = extract_trace_name(filename, PREFIX_EXP)
        
        ipcs = get_ipcs(filepath)
        if ipcs is not None:
            exp_ipcs[trace_name] = ipcs

    common_traces = sorted(list(set(baseline_ipcs.keys()) & set(exp_ipcs.keys())))

    if not common_traces:
        print("Error: No matching traces found between the baseline and experimental configurations.")
        return

    trace_groups = {}
    
    for trace in common_traces:
        b_ipcs = baseline_ipcs[trace]
        e_ipcs = exp_ipcs[trace]
        
        family = re.split(r'[_.]', trace)[0]
        
        if family not in trace_groups:
            trace_groups[family] = {c: [] for c in range(4)}
            
        for c in range(4):
            if b_ipcs[c] > 0:
                trace_groups[family][c].append(e_ipcs[c] / b_ipcs[c])

    if not trace_groups:
        print("Error: No valid traces found.")
        return

    families = []
    geomean_speedups = []
    all_ratios = {c: [] for c in range(4)}
    
    for family in sorted(trace_groups.keys()):
        core_geomeans = []
        for c in range(4):
            ratios = trace_groups[family][c]
            core_geomeans.append(calculate_geomean(ratios))
            all_ratios[c].extend(ratios)
            
        family_g_mean = calculate_geomean(core_geomeans)
        pct_speedup = (family_g_mean - 1.0) * 100.0
        
        families.append(family)
        geomean_speedups.append(pct_speedup)

    if all_ratios[0]:
        overall_core_geomeans = []
        for c in range(4):
            overall_core_geomeans.append(calculate_geomean(all_ratios[c]))
            
        overall_g_mean = calculate_geomean(overall_core_geomeans)
        overall_pct_speedup = (overall_g_mean - 1.0) * 100.0
        families.append("avg")
        geomean_speedups.append(overall_pct_speedup)

    os.makedirs(os.path.dirname(OUTPUT_IMG), exist_ok=True)

    fig, ax = plt.subplots(figsize=(12, 7))
    
    colors = []
    for i, val in enumerate(geomean_speedups):
        if families[i] == "avg":
            colors.append('#005f86') 
        else:
            colors.append('#005f86')
            
    bars = ax.bar(families, geomean_speedups, color=colors, edgecolor='black', alpha=0.8)

    ax.set_ylabel('Geomean Speedup (%) across 4 Cores')
    ax.set_xticks(range(len(families)))
    ax.set_xticklabels(families, rotation=45, ha="right")
    
    ax.axhline(0, color='black', linewidth=1.2) 
    ax.grid(axis='y', linestyle='--', alpha=0.7)

    min_val = min(geomean_speedups) if geomean_speedups else 0
    max_val = max(geomean_speedups) if geomean_speedups else 0
    
    y_lower = min(0, min_val * 1.1)
    y_upper = max(0, max_val * 1.15) if max_val > 0 else 1.0
    
    ax.set_ylim(bottom=y_lower, top=y_upper)

    fig.tight_layout()

    plt.savefig(OUTPUT_IMG, dpi=300)
    print(f"Graph successfully saved as PNG at: {OUTPUT_IMG}")

if __name__ == "__main__":
    main()
