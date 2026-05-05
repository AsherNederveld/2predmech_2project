import os
import glob
import re
import matplotlib.pyplot as plt
import numpy as np

# Set the experiment directory and output image path
DATA_DIR = "/projects/coursework/2026-spring/cs395t-lin/asher/take2/2predmech_2project/new_experiments"
OUTPUT_IMG = "/projects/coursework/2026-spring/cs395t-lin/mbd2325/ipc_speedup_comparison_grouped.png"

# Define the exact file prefixes for the baseline and all 4 experimentals
PREFIX_BASELINE = "champsim_lru_no_17_nlpc_llc_filtAll_256_32_prom_lru"

PREFIXES_EXP = {
    "Mockingjay": "champsim_mockingjay.orig_sms_16_lpc_llc_filtAll_256_32_nprom_lru",
    "PACMAN": "champsim_pacman_sms_16_lpc_llc_filtAll_256_32_nprom_lru",
    "LRU": "champsim_lru_sms_16_lpc_llc_filtAll_256_32_nprom_lru",
    "SHiP": "champsim_ship_sms_16_lpc_llc_filtAll_256_32_nprom_lru"
}

def get_ipc(filepath):
    """
    Scans a ChampSim trace output file for the final simulation IPC.
    """
    regex = re.compile(r"CPU 0 cumulative IPC:\s+([0-9.]+)\s+instructions")
    final_ipc = None
    try:
        with open(filepath, 'r') as f:
            for line in f:
                match = regex.search(line)
                if match:
                    final_ipc = float(match.group(1))
    except FileNotFoundError:
        print(f"Warning: File not found {filepath}")
    
    return final_ipc

def extract_trace_name(filename, prefix):
    """
    Strips the prefix and standard ChampSim output extensions to get a clean trace name.
    """
    trace_name = filename.replace(prefix + ".", "")
    trace_name = trace_name.replace(".trace.gz.out", "")
    trace_name = trace_name.replace(".out", "")
    return trace_name

def calculate_geomean(ratios):
    """
    Calculates the geometric mean of a list of ratios.
    """
    arr = np.array(ratios)
    if len(arr) == 0:
        return 1.0 
    if (arr <= 0).any():
        return 1.0 
    return np.exp(np.mean(np.log(arr)))

def main():
    baseline_ipcs = {}
    exp_ipcs = {name: {} for name in PREFIXES_EXP.keys()}

    # 1. Parse Baseline Files
    for filepath in glob.glob(os.path.join(DATA_DIR, f"{PREFIX_BASELINE}*")):
        filename = os.path.basename(filepath)
        trace_name = extract_trace_name(filename, PREFIX_BASELINE)
        ipc = get_ipc(filepath)
        if ipc is not None:
            baseline_ipcs[trace_name] = ipc

    # 2. Parse All Experimental Files
    for exp_name, exp_prefix in PREFIXES_EXP.items():
        for filepath in glob.glob(os.path.join(DATA_DIR, f"{exp_prefix}*")):
            filename = os.path.basename(filepath)
            trace_name = extract_trace_name(filename, exp_prefix)
            ipc = get_ipc(filepath)
            if ipc is not None:
                exp_ipcs[exp_name][trace_name] = ipc

    # 3. Find traces that successfully completed in common
    common_traces = set(baseline_ipcs.keys())
    for exp_dict in exp_ipcs.values():
        common_traces = common_traces.intersection(set(exp_dict.keys()))
    common_traces = sorted(list(common_traces))

    if not common_traces:
        print("Error: No common traces found.")
        return

    # 4. Group by Trace Family and Calculate Ratios
    trace_groups = {}
    for trace in common_traces:
        base_ipc = baseline_ipcs[trace]
        if base_ipc <= 0: continue
        family = re.split(r'[_.]', trace)[0]
        if family not in trace_groups:
            trace_groups[family] = {exp_name: [] for exp_name in PREFIXES_EXP.keys()}
        for exp_name in PREFIXES_EXP.keys():
            exp_ipc = exp_ipcs[exp_name][trace]
            trace_groups[family][exp_name].append(exp_ipc / base_ipc)

    # 5. Calculate Geomean Speedup
    families = sorted(trace_groups.keys())
    geomean_speedups = {exp_name: [] for exp_name in PREFIXES_EXP.keys()}
    all_ratios = {exp_name: [] for exp_name in PREFIXES_EXP.keys()}
    
    for family in families:
        for exp_name in PREFIXES_EXP.keys():
            ratios = trace_groups[family][exp_name]
            pct_speedup = (calculate_geomean(ratios) - 1.0) * 100.0
            geomean_speedups[exp_name].append(pct_speedup)
            all_ratios[exp_name].extend(ratios)

    # Add "avg" bar
    families.append("avg")
    for exp_name in PREFIXES_EXP.keys():
        overall_pct = (calculate_geomean(all_ratios[exp_name]) - 1.0) * 100.0
        geomean_speedups[exp_name].append(overall_pct)

    # 6. Generate the Grouped Bar Chart
    fig, ax = plt.subplots(figsize=(16, 8))
    x = np.arange(len(families))
    width = 0.2
    
    colors = ['#005f86', '#f8971f', '#579d42', '#00a9b7']
    offsets = [-1.5, -0.5, 0.5, 1.5]

    for idx, (exp_name, offset) in enumerate(zip(PREFIXES_EXP.keys(), offsets)):
        vals = geomean_speedups[exp_name]
        ax.bar(x + (offset * width), vals, width, label=exp_name, 
               color=colors[idx], edgecolor='black', alpha=0.8)

    # Formatting
    ax.set_ylabel('Speedup (%)', fontsize=14)
    ax.set_xticks(x)
    ax.set_xticklabels(families, rotation=45, ha="right", fontsize=12)
    
    # --- ENLARGED LEGEND ---
    ax.legend(title='Replacement Policy', 
              loc='upper right', 
              fontsize=16,          # Size of "Mockingjay", "PACMAN", etc.
              title_fontsize=18,    # Size of "Replacement Policy" title
              frameon=True, 
              shadow=True)

    ax.axhline(0, color='black', linewidth=1.2) 
    ax.grid(axis='y', linestyle='--', alpha=0.7)

    # Scale Y-Axis
    all_vals = [val for exp_vals in geomean_speedups.values() for val in exp_vals]
    ax.set_ylim(bottom=min(0, min(all_vals) * 1.2), top=max(all_vals) * 1.25)

    fig.tight_layout()
    os.makedirs(os.path.dirname(OUTPUT_IMG), exist_ok=True)
    plt.savefig(OUTPUT_IMG, dpi=300)
    print(f"Graph successfully saved at: {OUTPUT_IMG}")

if __name__ == "__main__":
    main()