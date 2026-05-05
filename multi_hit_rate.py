import os
import glob
import re
import matplotlib.pyplot as plt
import numpy as np

# Set the experiment directories and the exact output image path
BASELINE_DIR = "/projects/coursework/2026-spring/cs395t-lin/asher/take2/2predmech_2project/new_multi_exp"
EXP_DIR = "/projects/coursework/2026-spring/cs395t-lin/asher/take2/2predmech_2project/new_multi_exp"
OUTPUT_IMG = "/projects/coursework/2026-spring/cs395t-lin/asher/take2/2predmech_2project/multi_hit_rate.png"

# Define the exact file prefixes
PREFIX_BASELINE = "champsim_mockingjay.orig_triage_17_nlpc_llc_filtNone_256_32_prom_lru"
PREFIX_EXP = "champsim_mockingjay.orig_triage_16_lpc_llc_filtAll_256_32_nprom_lru"

def get_demand_hit_rate(filepath):
    """
    Scans a ChampSim trace output file and extracts LOAD and RFO accesses and hits for all 4 cores.
    Returns: (LOAD_HIT + RFO_HIT) / (LOAD_ACCESS + RFO_ACCESS) summed across cores.
    """
    re_load = re.compile(r"cpu(\d)->LLC\s+LOAD\s+ACCESS:\s+(\d+)\s+HIT:\s+(\d+)")
    re_rfo = re.compile(r"cpu(\d)->LLC\s+RFO\s+ACCESS:\s+(\d+)\s+HIT:\s+(\d+)")
    
    core_stats = {c: {'load_acc': 0.0, 'load_hit': 0.0, 'rfo_acc': 0.0, 'rfo_hit': 0.0} for c in range(4)}
    
    try:
        with open(filepath, 'r') as f:
            for line in f:
                m_load = re_load.search(line)
                if m_load:
                    core = int(m_load.group(1))
                    if 0 <= core < 4:
                        core_stats[core]['load_acc'] = float(m_load.group(2))
                        core_stats[core]['load_hit'] = float(m_load.group(3))
                    continue
                
                m_rfo = re_rfo.search(line)
                if m_rfo:
                    core = int(m_rfo.group(1))
                    if 0 <= core < 4:
                        core_stats[core]['rfo_acc'] = float(m_rfo.group(2))
                        core_stats[core]['rfo_hit'] = float(m_rfo.group(3))
                    continue
                    
    except FileNotFoundError:
        print(f"Warning: File not found {filepath}")
        return None
        
    total_demand_acc = sum(c['load_acc'] + c['rfo_acc'] for c in core_stats.values())
    total_demand_hit = sum(c['load_hit'] + c['rfo_hit'] for c in core_stats.values())
    
    if total_demand_acc > 0:
        return total_demand_hit / total_demand_acc
    
    return None

def extract_trace_name(filename, prefix):
    trace_name = filename.replace(prefix + ".", "")
    trace_name = trace_name.replace(".trace.gz.out", "")
    trace_name = trace_name.replace(".out", "")
    return trace_name

def main():
    baseline_rates = {}
    exp_rates = {}

    # 1. Parse Baseline Files
    for filepath in glob.glob(os.path.join(BASELINE_DIR, f"{PREFIX_BASELINE}*")):
        filename = os.path.basename(filepath)
        trace_name = extract_trace_name(filename, PREFIX_BASELINE)
        
        hit_rate = get_demand_hit_rate(filepath)
        if hit_rate is not None:
            baseline_rates[trace_name] = hit_rate

    # 2. Parse Experimental Files
    for filepath in glob.glob(os.path.join(EXP_DIR, f"{PREFIX_EXP}*")):
        filename = os.path.basename(filepath)
        trace_name = extract_trace_name(filename, PREFIX_EXP)
        
        hit_rate = get_demand_hit_rate(filepath)
        if hit_rate is not None:
            exp_rates[trace_name] = hit_rate

    # 3. Find traces that successfully completed in BOTH configurations
    common_traces = sorted(list(set(baseline_rates.keys()) & set(exp_rates.keys())))

    if not common_traces:
        print("Error: No matching traces found.")
        return

    # 4. Group by Trace Family and Calculate Absolute Deltas
    trace_groups = {}
    
    for trace in common_traces:
        base_rate = baseline_rates[trace]
        exp_rate = exp_rates[trace]
            
        # Calculate the absolute difference in percentage points
        delta_pct = (exp_rate - base_rate) * 100.0
        
        # Extract the family name (everything before the first '_' or '.')
        family = re.split(r'[_.]', trace)[0]
        
        if family not in trace_groups:
            trace_groups[family] = []
        trace_groups[family].append(delta_pct)

    if not trace_groups:
        print("Error: No valid traces found.")
        return

    # 5. Calculate Arithmetic Mean per Family
    families = []
    mean_deltas = []
    all_deltas = [] # Track all deltas to calculate the overall average
    
    for family in sorted(trace_groups.keys()):
        deltas = trace_groups[family]
        avg_delta = np.mean(deltas)
        
        families.append(family)
        mean_deltas.append(avg_delta)
        all_deltas.extend(deltas) # Keep a flat list of all trace differences

    # Add the AVG bar at the very end
    if all_deltas:
        families.append("avg")
        mean_deltas.append(np.mean(all_deltas))

    # Ensure output directory exists
    os.makedirs(os.path.dirname(OUTPUT_IMG), exist_ok=True)

    # 6. Generate the Single Bar Chart
    fig, ax = plt.subplots(figsize=(12, 7))
    
    colors = []
    for i, val in enumerate(mean_deltas):
        if families[i] == "avg":
            colors.append('#005f86') # Indigo/Purple for overall avg
        else:
            colors.append('#005f86' if val >= 0 else '#005f86')

    bars = ax.bar(families, mean_deltas, color=colors, edgecolor='black', alpha=0.8)

    ax.set_ylabel('Demand Data Hit Rate Increase (%) across 4 Cores')
    ax.set_xticks(range(len(families)))
    ax.set_xticklabels(families, rotation=45, ha="right")
    
    ax.axhline(0, color='black', linewidth=1.2) 
    ax.grid(axis='y', linestyle='--', alpha=0.7)

    min_val = min(mean_deltas) if mean_deltas else 0
    max_val = max(mean_deltas) if mean_deltas else 0
    
    ax.set_ylim(bottom=min(0, min_val * 1.2), top=max_val * 1.15)

    fig.tight_layout()
    
    # 7. Save Image
    plt.savefig(OUTPUT_IMG, dpi=300)
    print(f"Graph successfully saved as PNG at: {OUTPUT_IMG}")

if __name__ == "__main__":
    main()
