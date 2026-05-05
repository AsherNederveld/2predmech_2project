import os
import glob
import re
import matplotlib.pyplot as plt
import numpy as np

# Set the experiment directories and the exact output image path
BASELINE_DIR = "/projects/coursework/2026-spring/cs395t-lin/asher/take2/2predmech_2project/new_multi_exp"
EXP_DIR = "/projects/coursework/2026-spring/cs395t-lin/asher/take2/2predmech_2project/new_multi_exp"
OUTPUT_IMG = "/projects/coursework/2026-spring/cs395t-lin/asher/take2/2predmech_2project/multi_useful_pf.png"

# Define the exact file prefixes
PREFIX_BASELINE = "champsim_mockingjay.orig_triage_17_nlpc_llc_filtNone_256_32_prom_lru"
PREFIX_EXP = "champsim_mockingjay.orig_triage_16_lpc_llc_filtAll_256_32_nprom_lru"

# --- VISUALIZATION SETTINGS ---
MIN_BASELINE_DENOMINATOR = 100.0

def get_useful_prefetches(filepath):
    """
    Scans a ChampSim trace output file and extracts the USEFUL prefetch count across all 4 cores.
    """
    re_pref = re.compile(r"cpu(\d)->LLC\s+PREFETCH\s+REQUESTED:\s+(\d+)\s+ISSUED:\s+(\d+)\s+USEFUL:\s+(\d+)\s+USELESS:\s+(\d+)")
    
    total_useful = 0.0
    found_any = False
    
    try:
        with open(filepath, 'r') as f:
            for line in f:
                m_pref = re_pref.search(line)
                if m_pref:
                    core = int(m_pref.group(1))
                    if 0 <= core < 4:
                        total_useful += float(m_pref.group(4)) 
                        found_any = True
                    
    except FileNotFoundError:
        print(f"Warning: File not found {filepath}")
        return None
        
    if found_any:
        return total_useful
    return None

def extract_trace_name(filename, prefix):
    trace_name = filename.replace(prefix + ".", "")
    trace_name = trace_name.replace(".trace.gz.out", "")
    trace_name = trace_name.replace(".out", "")
    return trace_name

def calculate_geomean(ratios):
    """
    Calculates the geometric mean of a list of ratios.
    Handles 0s by returning 0 (if any ratio is 0, the geomean is 0).
    """
    arr = np.array(ratios)
    if (arr == 0).any():
        return 0.0
    return np.exp(np.mean(np.log(arr)))

def main():
    baseline_useful = {}
    exp_useful = {}

    # 1. Parse Files
    for filepath in glob.glob(os.path.join(BASELINE_DIR, f"{PREFIX_BASELINE}*")):
        filename = os.path.basename(filepath)
        trace_name = extract_trace_name(filename, PREFIX_BASELINE)
        useful_count = get_useful_prefetches(filepath)
        if useful_count is not None:
            baseline_useful[trace_name] = useful_count

    for filepath in glob.glob(os.path.join(EXP_DIR, f"{PREFIX_EXP}*")):
        filename = os.path.basename(filepath)
        trace_name = extract_trace_name(filename, PREFIX_EXP)
        useful_count = get_useful_prefetches(filepath)
        if useful_count is not None:
            exp_useful[trace_name] = useful_count

    common_traces = sorted(list(set(baseline_useful.keys()) & set(exp_useful.keys())))

    if not common_traces:
        print("Error: No matching traces found.")
        return

    # 2. Group by Trace Family and Calculate Ratios
    trace_groups = {} 
    
    for trace in common_traces:
        base_val = baseline_useful[trace]
        exp_val = exp_useful[trace]
        
        if base_val < MIN_BASELINE_DENOMINATOR:
            continue
            
        family = re.split(r'[_.]', trace)[0]
        ratio = exp_val / base_val
        
        if family not in trace_groups:
            trace_groups[family] = []
        trace_groups[family].append(ratio)

    if not trace_groups:
        print(f"Error: No traces had a baseline useful count >= {MIN_BASELINE_DENOMINATOR}.")
        return

    # 3. Calculate Geomean per Family
    families = []
    geomean_pcts = []
    all_ratios = [] 
    
    for family in sorted(trace_groups.keys()):
        ratios = trace_groups[family]
        g_mean_ratio = calculate_geomean(ratios)
        
        pct_increase = (g_mean_ratio - 1.0) * 100.0
        
        families.append(family)
        geomean_pcts.append(pct_increase)
        all_ratios.extend(ratios) 

    # Add the 'avg' bar at the very end
    if all_ratios:
        overall_g_mean = calculate_geomean(all_ratios)
        overall_pct_increase = (overall_g_mean - 1.0) * 100.0
        families.append("avg")
        geomean_pcts.append(overall_pct_increase)

    # 4. Plotting
    os.makedirs(os.path.dirname(OUTPUT_IMG), exist_ok=True)

    fig, ax = plt.subplots(figsize=(12, 7))
    
    # Keeping the color logic: Indigo for avg, Blue for positive, Red for negative
    colors = []
    for i, val in enumerate(geomean_pcts):
        if families[i] == "avg":
            colors.append('#005f86') 
        else:
            colors.append('#005f86' if val >= 0 else '#005f86')

    # Plot raw geomean_pcts without capping them
    bars = ax.bar(families, geomean_pcts, color=colors, edgecolor='black', alpha=0.8)

    ax.set_ylabel('Percent Increase in Useful Prefetches (%) across 4 Cores')
    ax.set_xticks(range(len(families)))
    ax.set_xticklabels(families, rotation=45, ha="right")
    
    ax.axhline(0, color='black', linewidth=1.2) 
    ax.grid(axis='y', linestyle='--', alpha=0.7)

    # Scale to match the image you uploaded (~ -90 to 225)
    min_val = min(geomean_pcts) if geomean_pcts else -90
    max_val = max(geomean_pcts) if geomean_pcts else 225
    
    y_lower_bound = min(-90, min_val * 1.1) 
    y_upper_bound = max(225, max_val * 1.1)
    
    ax.set_ylim(bottom=y_lower_bound, top=y_upper_bound) 

    # Text annotations removed to leave the bars blank

    fig.tight_layout()
    
    plt.savefig(OUTPUT_IMG, dpi=300)
    print(f"Graph successfully saved as PNG at: {OUTPUT_IMG}")

if __name__ == "__main__":
    main()
