import os
import glob
import re
import matplotlib.pyplot as plt
import numpy as np

DIRS_TO_SEARCH = [
    "/projects/coursework/2026-spring/cs395t-lin/asher/take2/2predmech_2project/new_multi_exp"
]
OUTPUT_IMG = "/projects/coursework/2026-spring/cs395t-lin/asher/take2/2predmech_2project/multi_comparison.png"

PREFIX_ABS_BASELINE = "champsim_lru_no_17_nlpc_llc_filtNone_256_32_prom_lru"

POLICY_ORDER = ["Mockingjay", "PACMAN", "LRU", "SHiP"]

POLICIES = {
    "Mockingjay": {
        "with": "champsim_mockingjay.orig_sms_16_lpc_llc_filtAll_256_32_nprom_lru",
        "without": "champsim_mockingjay.orig_sms_17_nlpc_llc_filtNone_256_32_prom_lru"
    },
    "PACMAN": {
        "with": "champsim_pacman_sms_16_lpc_llc_filtAll_256_32_nprom_lru",
        "without": "champsim_pacman_sms_17_nlpc_llc_filtNone_256_32_prom_lru"
    },
    "SHiP": {
        "with": "champsim_ship_sms_16_lpc_llc_filtAll_256_32_nprom_lru",
        "without": "champsim_ship_sms_17_nlpc_llc_filtNone_256_32_prom_lru"
    },
    "LRU": {
        "with": "champsim_lru_sms_16_lpc_llc_filtAll_256_32_nprom_lru",
        "without": "champsim_lru_sms_17_nlpc_llc_filtNone_256_32_prom_lru"
    }
}

COLORS = {
    "Mockingjay": "#005f86", 
    "PACMAN": "#f8971f",     
    "SHiP": "#00a9b7",       
    "LRU": "#579d42"         
}

def get_ipcs(filepath):
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
    except Exception:
        pass
    
    if len(ipcs) == 4:
        return [ipcs[0], ipcs[1], ipcs[2], ipcs[3]]
    return None

def extract_trace_name(filename, prefix):
    trace_name = filename.replace(prefix + ".", "")
    return trace_name.replace(".trace.gz.out", "").replace(".out", "")

def calculate_geomean(ratios):
    arr = np.array(ratios)
    if len(arr) == 0: return 1.0
    if (arr <= 0).any(): return 1.0
    return np.exp(np.mean(np.log(arr)))

def main():
    baseline_ipcs = {}
    policy_results = {p: {"with": {}, "without": {}} for p in POLICIES}

    for d in DIRS_TO_SEARCH:
        for filepath in glob.glob(os.path.join(d, f"{PREFIX_ABS_BASELINE}*")):
            trace = extract_trace_name(os.path.basename(filepath), PREFIX_ABS_BASELINE)
            ipcs = get_ipcs(filepath)
            if ipcs: baseline_ipcs[trace] = ipcs
        for name, configs in POLICIES.items():
            for cfg_type, prefix in configs.items():
                for filepath in glob.glob(os.path.join(d, f"{prefix}*")):
                    trace = extract_trace_name(os.path.basename(filepath), prefix)
                    ipcs = get_ipcs(filepath)
                    if ipcs: policy_results[name][cfg_type][trace] = ipcs

    common_traces = set(baseline_ipcs.keys())
    for p in POLICIES:
        for cfg in ["with", "without"]:
            common_traces &= set(policy_results[p][cfg].keys())

    common_traces = sorted(list(common_traces))

    if not common_traces:
        print("Error: No common traces found across configurations.")
        return

    print(f"Number of common traces processed: {len(common_traces)}\n")

    geomean_data = {p: {"with": 0.0, "without": 0.0} for p in POLICIES}
    all_speedup_values = []
    
    for p in POLICY_ORDER:
        for cfg in ["with", "without"]:
            core_geomeans = []
            for c in range(4):
                ratios = [policy_results[p][cfg][t][c] / baseline_ipcs[t][c] for t in common_traces if baseline_ipcs[t][c] > 0]
                core_geomeans.append(calculate_geomean(ratios))
            
            speedup = (calculate_geomean(core_geomeans) - 1.0) * 100.0
            geomean_data[p][cfg] = speedup
            all_speedup_values.append(speedup)

    fig, ax = plt.subplots(figsize=(12, 7))
    x = np.arange(len(POLICY_ORDER))
    width = 0.35

    for i, p in enumerate(POLICY_ORDER):
        color = COLORS[p]
        ax.bar(i - width/2, geomean_data[p]["with"], width, 
               color=color, edgecolor='black', hatch='////', alpha=0.9)
        ax.bar(i + width/2, geomean_data[p]["without"], width, 
               color=color, edgecolor='black', alpha=0.7)

    ax.set_ylabel('Geomean Speedup over Baseline (%) across 4 Cores', fontsize=14)
    ax.set_xticks(x)
    ax.set_xticklabels(POLICY_ORDER, fontsize=14)
    ax.axhline(0, color='black', linewidth=1.2)
    ax.grid(axis='y', linestyle='--', alpha=0.7)

    if all_speedup_values:
        max_val = max(all_speedup_values)
        ax.set_ylim(bottom=min(0, min(all_speedup_values) * 1.2), top=max_val * 1.4) 

    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='white', edgecolor='black', hatch='////', label='With LPC'),
        Patch(facecolor='white', edgecolor='black', label='Without LPC')
    ]
    ax.legend(handles=legend_elements, fontsize=16, frameon=True, shadow=True, loc='upper right')

    fig.tight_layout()
    os.makedirs(os.path.dirname(OUTPUT_IMG), exist_ok=True)
    plt.savefig(OUTPUT_IMG, dpi=300)
    print(f"Graph successfully saved at: {OUTPUT_IMG}")

if __name__ == "__main__":
    main()
