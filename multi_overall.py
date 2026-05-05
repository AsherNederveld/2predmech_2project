import os
import glob
import re
import matplotlib.pyplot as plt
import numpy as np

DATA_DIR = "/projects/coursework/2026-spring/cs395t-lin/asher/take2/2predmech_2project/new_multi_exp"
OUTPUT_IMG = "/projects/coursework/2026-spring/cs395t-lin/asher/take2/2predmech_2project/multi_overall.png"

# Guessing the baseline and exp prefixes for multicore
PREFIX_BASELINE = "champsim_lru_no_17_nlpc_llc_filtNone_256_32_prom_lru"

PREFIXES_EXP = {
    "Mockingjay": "champsim_mockingjay.orig_triage_16_lpc_llc_filtAll_256_32_nprom_lru",
    "PACMAN": "champsim_pacman_triage_16_lpc_llc_filtAll_256_32_nprom_lru",
    "LRU": "champsim_lru_triage_16_lpc_llc_filtAll_256_32_nprom_lru",
    "SHiP": "champsim_ship_triage_16_lpc_llc_filtAll_256_32_nprom_lru"
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
    except FileNotFoundError:
        pass
    
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
    if len(arr) == 0: return 1.0 
    if (arr <= 0).any(): return 1.0 
    return np.exp(np.mean(np.log(arr)))

def main():
    baseline_ipcs = {}
    exp_ipcs_dict = {name: {} for name in PREFIXES_EXP.keys()}

    for filepath in glob.glob(os.path.join(DATA_DIR, f"{PREFIX_BASELINE}*")):
        filename = os.path.basename(filepath)
        trace_name = extract_trace_name(filename, PREFIX_BASELINE)
        ipcs = get_ipcs(filepath)
        if ipcs: baseline_ipcs[trace_name] = ipcs

    for exp_name, exp_prefix in PREFIXES_EXP.items():
        for filepath in glob.glob(os.path.join(DATA_DIR, f"{exp_prefix}*")):
            filename = os.path.basename(filepath)
            trace_name = extract_trace_name(filename, exp_prefix)
            ipcs = get_ipcs(filepath)
            if ipcs: exp_ipcs_dict[exp_name][trace_name] = ipcs

    common_traces = set(baseline_ipcs.keys())
    for exp_dict in exp_ipcs_dict.values():
        common_traces = common_traces.intersection(set(exp_dict.keys()))
    common_traces = sorted(list(common_traces))

    if not common_traces:
        print("Error: No common traces found. Please check prefix names.")
        return

    trace_groups = {}
    for trace in common_traces:
        base_ipcs = baseline_ipcs[trace]
        family = re.split(r'[_.]', trace)[0]
        if family not in trace_groups:
            trace_groups[family] = {exp_name: {c: [] for c in range(4)} for exp_name in PREFIXES_EXP.keys()}
        for exp_name in PREFIXES_EXP.keys():
            e_ipcs = exp_ipcs_dict[exp_name][trace]
            for c in range(4):
                if base_ipcs[c] > 0:
                    trace_groups[family][exp_name][c].append(e_ipcs[c] / base_ipcs[c])

    families = sorted(trace_groups.keys())
    geomean_speedups = {exp_name: [] for exp_name in PREFIXES_EXP.keys()}
    all_ratios = {exp_name: {c: [] for c in range(4)} for exp_name in PREFIXES_EXP.keys()}
    
    for family in families:
        for exp_name in PREFIXES_EXP.keys():
            core_geomeans = []
            for c in range(4):
                ratios = trace_groups[family][exp_name][c]
                core_geomeans.append(calculate_geomean(ratios))
                all_ratios[exp_name][c].extend(ratios)
            
            family_gmean = calculate_geomean(core_geomeans)
            pct_speedup = (family_gmean - 1.0) * 100.0
            geomean_speedups[exp_name].append(pct_speedup)

    families.append("avg")
    for exp_name in PREFIXES_EXP.keys():
        overall_core_geomeans = []
        for c in range(4):
            overall_core_geomeans.append(calculate_geomean(all_ratios[exp_name][c]))
        overall_gmean = calculate_geomean(overall_core_geomeans)
        overall_pct = (overall_gmean - 1.0) * 100.0
        geomean_speedups[exp_name].append(overall_pct)

    fig, ax = plt.subplots(figsize=(16, 8))
    x = np.arange(len(families))
    width = 0.2
    
    colors = ['#005f86', '#f8971f', '#579d42', '#00a9b7']
    offsets = [-1.5, -0.5, 0.5, 1.5]

    for idx, (exp_name, offset) in enumerate(zip(PREFIXES_EXP.keys(), offsets)):
        vals = geomean_speedups[exp_name]
        ax.bar(x + (offset * width), vals, width, label=exp_name, 
               color=colors[idx], edgecolor='black', alpha=0.8)

    ax.set_ylabel('Geomean Speedup (%) Across 4 Cores', fontsize=14)
    ax.set_xticks(x)
    ax.set_xticklabels(families, rotation=45, ha="right", fontsize=12)
    
    ax.legend(title='Replacement Policy', 
              loc='upper right', 
              fontsize=16,
              title_fontsize=18,
              frameon=True, 
              shadow=True)

    ax.axhline(0, color='black', linewidth=1.2) 
    ax.grid(axis='y', linestyle='--', alpha=0.7)

    all_vals = [val for exp_vals in geomean_speedups.values() for val in exp_vals]
    ax.set_ylim(bottom=min(0, min(all_vals) * 1.2), top=max(all_vals) * 1.25)

    fig.tight_layout()
    os.makedirs(os.path.dirname(OUTPUT_IMG), exist_ok=True)
    plt.savefig(OUTPUT_IMG, dpi=300)
    print(f"Graph successfully saved at: {OUTPUT_IMG}")

if __name__ == "__main__":
    main()
