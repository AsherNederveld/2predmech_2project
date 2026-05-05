import os
import glob
import re
import matplotlib.pyplot as plt
import numpy as np

# --- PATH CONFIGURATION ---
DIRS_TO_SEARCH = [
    "/projects/coursework/2026-spring/cs395t-lin/asher/take2/2predmech_2project/new_google_experiments"
]
OUTPUT_IMG = "/projects/coursework/2026-spring/cs395t-lin/asher/take2/2predmech_2project/replacement_geomean_tall.png"

# --- EXPERIMENT CONFIGURATION ---
PREFIX_ABS_BASELINE = "champsim_lru_no_17_nlpc_llc_filtNone_256_32_prom_lru"

# Explicit order as requested: Mockingjay, PACMAN, LRU, SHiP
POLICY_ORDER = ["Mockingjay", "PACMAN", "LRU", "SHiP"]

POLICIES = {
    "Mockingjay": {
        "with": "champsim_mockingjay.orig_pythia_16_lpc_llc_filtAll_256_32_nprom_lru",
        "without": "champsim_mockingjay.orig_pythia_17_nlpc_llc_filtNone_256_32_prom_lru"
    },
    "PACMAN": {
        "with": "champsim_pacman_pythia_16_lpc_llc_filtAll_256_32_nprom_lru",
        "without": "champsim_pacman_pythia_17_nlpc_llc_filtNone_256_32_prom_lru"
    },
    "SHiP": {
        "with": "champsim_ship_pythia_16_lpc_llc_filtAll_256_32_nprom_lru",
        "without": "champsim_ship_pythia_17_nlpc_llc_filtNone_256_32_prom_lru"
    },
    "LRU": {
        "with": "champsim_lru_pythia_16_lpc_llc_filtAll_256_32_nprom_lru",
        "without": "champsim_lru_pythia_17_nlpc_llc_filtNone_256_32_prom_lru"
    }
}
    # "champsim_lru_no_17_nlpc_llc_filtNone_256_32_prom_lru",
# "champsim_mockingjay.orig_no_17_nlpc_llc_filtNone_256_32_prom_lru",
    # "champsim_pacman_no_17_nlpc_llc_filtNone_256_32_prom_lru",
        # "champsim_ship_no_17_nlpc_llc_filtNone_256_32_prom_lru",

    # "champsim_ship_no_17_nlpc_llc_filtAll_256_32_prom_lru",
# "champsim_mockingjay.orig_no_17_nlpc_llc_filtAll_256_32_prom_lru",
    # "champsim_pacman_no_17_nlpc_llc_filtAll_256_32_prom_lru",
            # "champsim_lru_no_17_nlpc_llc_filtAll_256_32_prom_lru",


COLORS = {
    "Mockingjay": "#005f86", 
    "PACMAN": "#f8971f",     
    "SHiP": "#00a9b7",       
    "LRU": "#579d42"         
}

def get_ipc(filepath):
    """Parses ChampSim IPC."""
    regex = re.compile(r"CPU 0 cumulative IPC:\s+([0-9.]+)")
    try:
        with open(filepath, 'r') as f:
            for line in f:
                match = regex.search(line)
                if match: return float(match.group(1))
    except Exception:
        pass
    return None

def extract_trace_name(filename, prefix):
    trace_name = filename.replace(prefix + ".", "")
    return trace_name.replace(".trace.gz.out", "").replace(".out", "")

def calculate_geomean(ratios):
    """Geometric mean calculation for speedup metrics."""
    arr = np.array(ratios)
    if len(arr) == 0: return 1.0
    return np.exp(np.mean(np.log(arr)))

def main():
    baseline_ipcs = {}
    policy_results = {p: {"with": {}, "without": {}} for p in POLICIES}

    printed_first = False
    # 1. Gather Data
    for d in DIRS_TO_SEARCH:
        for filepath in glob.glob(os.path.join(d, f"{PREFIX_ABS_BASELINE}*")):
            trace = extract_trace_name(os.path.basename(filepath), PREFIX_ABS_BASELINE)
            ipc = get_ipc(filepath)
            if ipc:
                baseline_ipcs[trace] = ipc
                if not printed_first:
                    print(f"First IPC recorded: {ipc} from file: {filepath}")
                    printed_first = True
        for name, configs in POLICIES.items():
            for cfg_type, prefix in configs.items():
                for filepath in glob.glob(os.path.join(d, f"{prefix}*")):
                    trace = extract_trace_name(os.path.basename(filepath), prefix)
                    ipc = get_ipc(filepath)
                    if ipc:
                        policy_results[name][cfg_type][trace] = ipc
                        if not printed_first:
                            print(f"First IPC recorded: {ipc} from file: {filepath}")
                            printed_first = True

    # 2. Intersection logic
    common_traces = set(baseline_ipcs.keys())
    for p in POLICIES:
        for cfg in ["with", "without"]:
            common_traces &= set(policy_results[p][cfg].keys())
    common_traces = sorted(list(common_traces))

    if not common_traces:
        print("Error: No common traces found across configurations.")
        return

    # 3. Calculate Speedups
    geomean_data = {p: {"with": 0.0, "without": 0.0} for p in POLICIES}
    all_speedup_values = []
    for p in POLICY_ORDER:
        for cfg in ["with", "without"]:
            ratios = [policy_results[p][cfg][t] / baseline_ipcs[t] for t in common_traces]
            speedup = (calculate_geomean(ratios) - 1.0) * 100.0
            geomean_data[p][cfg] = speedup
            all_speedup_values.append(speedup)

    # 4. Plotting
    fig, ax = plt.subplots(figsize=(12, 7))
    x = np.arange(len(POLICY_ORDER))
    width = 0.35

    for i, p in enumerate(POLICY_ORDER):
        color = COLORS[p]
        # WITH LPC = Hatched
        ax.bar(i - width/2, geomean_data[p]["with"], width, 
               color=color, edgecolor='black', hatch='////', alpha=0.9)
        # WITHOUT LPC = Solid
        ax.bar(i + width/2, geomean_data[p]["without"], width, 
               color=color, edgecolor='black', alpha=0.7)

    # Formatting
    ax.set_ylabel('Geomean Speedup over Baseline (%)', fontsize=14)
    ax.set_xticks(x)
    ax.set_xticklabels(POLICY_ORDER, fontsize=14)
    ax.axhline(0, color='black', linewidth=1.2)
    ax.grid(axis='y', linestyle='--', alpha=0.7)

    # --- ADJUST Y-AXIS FOR LEGEND HEADROOM ---
    if all_speedup_values:
        max_val = max(all_speedup_values)
        ax.set_ylim(top=max_val * 1.4) 

    # --- CLEAN LEGEND ---
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='white', edgecolor='black', hatch='////', label='With LPC'),
        Patch(facecolor='white', edgecolor='black', label='Without LPC, 1 Extra Way')
    ]
    ax.legend(handles=legend_elements, fontsize=16, frameon=True, shadow=True, loc='upper right')

    fig.tight_layout()
    os.makedirs(os.path.dirname(OUTPUT_IMG), exist_ok=True)
    plt.savefig(OUTPUT_IMG, dpi=300)
    print(f"Graph successfully saved at: {OUTPUT_IMG}")

if __name__ == "__main__":
    main()