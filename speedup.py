import os
import glob
import re
import matplotlib.pyplot as plt
import numpy as np

# Set the experiment directories and the exact output image path
BASELINE_DIR = "/projects/coursework/2026-spring/cs395t-lin/asher/take2/2predmech_2project/experiments"
EXP_DIR = "/projects/coursework/2026-spring/cs395t-lin/asher/take2/2predmech_2project/new_experiments"
OUTPUT_IMG = "/projects/coursework/2026-spring/cs395t-lin/asher/take2/2predmech_2project/speedup.png"

# Define the exact file prefixes
PREFIX_BASELINE = "champsim_mockingjay.orig_triage_16_lpc_llc_filtAll_8192_1_nprom_lru"
PREFIX_EXP = "champsim_mockingjay.orig_triage_16_lpc_llc_filtAll_1_8192_nprom_lru"


def get_ipc(filepath):
    """
    Scans a ChampSim trace output file for the final simulation IPC.
    Matches: "CPU 0 cumulative IPC: 0.9159 instructions: 500000002"
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
    if (arr <= 0).any(): # IPC ratios shouldn't be 0 or negative, but safe to check
        return 0.0
    return np.exp(np.mean(np.log(arr)))

def main():
    baseline_ipcs = {}
    exp_ipcs = {}

    # 1. Parse Baseline Files
    for filepath in glob.glob(os.path.join(BASELINE_DIR, f"{PREFIX_BASELINE}*")):
        filename = os.path.basename(filepath)
        trace_name = extract_trace_name(filename, PREFIX_BASELINE)
        
        ipc = get_ipc(filepath)
        if ipc is not None:
            baseline_ipcs[trace_name] = ipc

    # 2. Parse Experimental Files
    for filepath in glob.glob(os.path.join(EXP_DIR, f"{PREFIX_EXP}*")):
        filename = os.path.basename(filepath)
        trace_name = extract_trace_name(filename, PREFIX_EXP)
        
        ipc = get_ipc(filepath)
        if ipc is not None:
            exp_ipcs[trace_name] = ipc

    # 3. Find traces that successfully completed in BOTH configurations
    common_traces = sorted(list(set(baseline_ipcs.keys()) & set(exp_ipcs.keys())))

    if not common_traces:
        print("Error: No matching traces found between the baseline and experimental configurations.")
        return

    # 4. Group by Trace Family and Calculate IPC Ratios
    trace_groups = {}
    
    for trace in common_traces:
        base_ipc = baseline_ipcs[trace]
        exp_ipc = exp_ipcs[trace]
        
        if base_ipc <= 0:
            continue
            
        # Extract the family name (everything before the first '_' or '.')
        family = re.split(r'[_.]', trace)[0]
        
        # Calculate the raw ratio for this simpoint
        ratio = exp_ipc / base_ipc
        
        if family not in trace_groups:
            trace_groups[family] = []
        trace_groups[family].append(ratio)

    if not trace_groups:
        print("Error: No valid traces found.")
        return

    # 5. Calculate Geomean per Family
    families = []
    geomean_speedups = []
    all_ratios = [] # Track all ratios for the overall avg
    
    for family in sorted(trace_groups.keys()):
        ratios = trace_groups[family]
        g_mean_ratio = calculate_geomean(ratios)
        
        # Convert the geomean ratio back to a percentage increase/decrease
        pct_speedup = (g_mean_ratio - 1.0) * 100.0
        
        families.append(family)
        geomean_speedups.append(pct_speedup)
        all_ratios.extend(ratios) # Keep a flat list of all trace ratios

    # Add the 'avg' bar at the end
    if all_ratios:
        overall_g_mean = calculate_geomean(all_ratios)
        overall_pct_speedup = (overall_g_mean - 1.0) * 100.0
        families.append("avg")
        geomean_speedups.append(overall_pct_speedup)

    # Ensure output directory exists
    os.makedirs(os.path.dirname(OUTPUT_IMG), exist_ok=True)

    # 6. Generate the Single Bar Chart
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # Color bars based on whether the speedup is positive (blue), negative (red), or avg (indigo)
    colors = []
    for i, val in enumerate(geomean_speedups):
        if families[i] == "avg":
            colors.append('#005f86') # Indigo/Purple for avg
        else:
            colors.append('#005f86' if val >= 0 else '#005f86')
            
    bars = ax.bar(families, geomean_speedups, color=colors, edgecolor='black', alpha=0.8)

    ax.set_ylabel('Speedup (%)')
    ax.set_xticks(range(len(families)))
    ax.set_xticklabels(families, rotation=45, ha="right")
    
    # Draw a distinct line at 0 for clarity
    ax.axhline(0, color='black', linewidth=1.2) 
    ax.grid(axis='y', linestyle='--', alpha=0.7)

    # Dynamically scale Y-Axis 
    min_val = min(geomean_speedups) if geomean_speedups else 0
    max_val = max(geomean_speedups) if geomean_speedups else 0
    
    y_lower = min(0, min_val * 1.1)
    y_upper = max(0, max_val * 1.15) if max_val > 0 else 1.0
    
    ax.set_ylim(bottom=y_lower, top=y_upper)

    fig.tight_layout()

    # 7. Save Image
    plt.savefig(OUTPUT_IMG, dpi=300)
    print(f"Graph successfully saved as PNG at: {OUTPUT_IMG}")

if __name__ == "__main__":
    main()