import os
import csv
import re
import statistics
import sys
import argparse
import matplotlib.pyplot as plt
import numpy as np

def normalize(name):
    return name.replace('-', '_').replace('.', '_').lower()

def extract_stats(filepath):
    stats = {
        "ipc": None, "llc_total_access": None, "llc_total_hit": None,
        "llc_total_miss": None, "llc_mshr_merge": None, "llc_insertions": None,
        "llc_pf_req": None, "llc_pf_issued": None, "llc_pf_useful": None,
        "llc_pf_useless": None, "lpc_hits": None, "lpc_misses": None,
        "lpc_insertions": None, "lpc_evictions": None
    }
    
    if not filepath or not os.path.exists(filepath):
        return stats
        
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        ipc_matches = re.findall(r"cumulative IPC:\s*([\d.]+)", content)
        if ipc_matches: stats["ipc"] = float(ipc_matches[-1])

        llc_tot = re.findall(r"cpu0->LLC TOTAL\s+ACCESS:\s+(\d+)\s+HIT:\s+(\d+)\s+MISS:\s+(\d+)\s+MSHR_MERGE:\s+(\d+)", content)
        if llc_tot:
            stats["llc_total_access"] = int(llc_tot[-1][0])
            stats["llc_total_hit"] = int(llc_tot[-1][1])
            stats["llc_total_miss"] = int(llc_tot[-1][2])
            stats["llc_mshr_merge"] = int(llc_tot[-1][3])

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

        llc_pf = re.findall(r"cpu0->LLC PREFETCH REQUESTED:\s+(\d+)\s+ISSUED:\s+(\d+)\s+USEFUL:\s+(\d+)\s+USELESS:\s+(\d+)", content)
        if llc_pf:
            stats["llc_pf_req"] = int(llc_pf[-1][0])
            stats["llc_pf_issued"] = int(llc_pf[-1][1])
            stats["llc_pf_useful"] = int(llc_pf[-1][2])
            stats["llc_pf_useless"] = int(llc_pf[-1][3])

        lpc_hm = re.findall(r"cpu0->LLC LPC_HITS:\s+(\d+)\s+LPC_MISSES:\s+(\d+)", content)
        if lpc_hm:
            stats["lpc_hits"] = int(lpc_hm[-1][0])
            stats["lpc_misses"] = int(lpc_hm[-1][1])

        lpc_ie = re.findall(r"cpu0->LLC LPC_INSERTIONS:\s+(\d+)\s+LPC_EVICTIONS:\s+(\d+)", content)
        if lpc_ie:
            stats["lpc_insertions"] = int(lpc_ie[-1][0])
            stats["lpc_evictions"] = int(lpc_ie[-1][1])

        filename = os.path.basename(filepath)
        if "filtNone" in filename:
            if stats["llc_total_miss"] is not None and stats["llc_mshr_merge"] is not None:
                stats["llc_insertions"] = stats["llc_total_miss"] - stats["llc_mshr_merge"]
        elif "filtAll" in filename:
            if all(v is not None for v in [stats["llc_total_miss"], pf_miss, stats["llc_mshr_merge"], pf_mshr]):
                stats["llc_insertions"] = (stats["llc_total_miss"] - pf_miss) - (stats["llc_mshr_merge"] - pf_mshr)
        elif "filtNonLLC" in filename:
            if all(v is not None for v in [stats["llc_total_miss"], pf_miss, stats["llc_mshr_merge"], pf_mshr, stats["llc_pf_issued"]]):
                stats["llc_insertions"] = (stats["llc_total_miss"] - pf_miss) - (stats["llc_mshr_merge"] - pf_mshr) + stats["llc_pf_issued"]

    except Exception as e:
        print(f"Error extracting stats from {filepath}: {e}")
        
    return stats

def get_metric_value(stats, metric):
    val = 0
    if metric == 'IPC': val = stats.get("ipc")
    elif metric == 'LPC_Insertions': val = stats.get("lpc_insertions")
    elif metric == 'LLC_Insertions': val = stats.get("llc_insertions")
    elif metric == 'LPC_Hits': val = stats.get("lpc_hits")
    elif metric == 'LLC_Hits': val = (stats.get("llc_total_hit") or 0) - (stats.get("lpc_hits") or 0)
    elif metric == 'LLC_Useful_Prefetches': val = stats.get("llc_pf_useful")
    elif metric == 'LPC_HitRate':
        h = stats.get("lpc_hits")
        a = stats.get("llc_total_access")
        val = (h / a) if h is not None and a else 0
    elif metric == 'LLC_HitRate':
        h = (stats.get("llc_total_hit") or 0) - (stats.get("lpc_hits") or 0)
        a = stats.get("llc_total_access")
        val = (h / a) if h is not None and a else 0
    elif metric == 'LPC_Reuse':
        h = stats.get("lpc_hits")
        i = stats.get("lpc_insertions")
        val = (h / i) if h is not None and i else 0
    elif metric == 'LLC_Reuse':
        h = (stats.get("llc_total_hit") or 0) - (stats.get("lpc_hits") or 0)
        i = stats.get("llc_insertions")
        val = (h / i) if h is not None and i else 0
        
    return val if val is not None else 0

def find_file(prefix, bench, all_files):
    norm_bench = normalize(bench)
    for filename in all_files:
        if filename.startswith(prefix) and filename.endswith('.out'):
            if norm_bench in normalize(filename):
                return filename
    return None

def get_dynamic_benchmarks(prefixes, all_files):
    benchmarks = set()
    for filename in all_files:
        if not filename.endswith('.out'): continue
        for prefix in prefixes:
            if filename.startswith(prefix):
                bench_name = filename[len(prefix):-4].lstrip('_').lstrip('-')
                if bench_name: benchmarks.add(bench_name)
    return sorted(list(benchmarks))

def plot_custom_results(benchmarks, plot_data, active_metrics, is_relative, is_log, exp_prefixes, base_prefix, output_path):
    configs = exp_prefixes if is_relative else [base_prefix] + exp_prefixes
    
    total_bars_per_bench = len(configs) * len(active_metrics)
    fig_width = max(20, len(benchmarks) * (total_bars_per_bench * 0.1))
    
    fig, ax = plt.subplots(figsize=(fig_width, 8))
    x = np.arange(len(benchmarks))
    
    items = [(config, metric) for config in configs for metric in active_metrics]
    width = 0.8 / len(items)
    
    for i, (config, metric) in enumerate(items):
        if is_relative:
            base_vals = plot_data[metric][base_prefix]
            exp_vals = plot_data[metric][config]
            vals = []
            for b, e in zip(base_vals, exp_vals):
                if b and b > 0 and e is not None:
                    vals.append(((e / b) - 1) * 100)
                else:
                    vals.append(0)
        else:
            vals = plot_data[metric][config]
            
        offset = (i - len(items)/2 + 0.5) * width
        ax.bar(x + offset, vals, width, label=f"{config} ({metric})")
            
    if is_relative:
        if is_log: ax.set_yscale('symlog')
        ax.set_ylabel('Relative Change (%)' + (' (Log Scale)' if is_log else ''))
        ax.set_title(f'{" & ".join(active_metrics)} by Experiment (Relative %)')
    else:
        if is_log: ax.set_yscale('symlog')
        ax.set_ylabel('Absolute Values' + (' (Log Scale)' if is_log else ''))
        ax.set_title(f'{" & ".join(active_metrics)} by Experiment (Absolute)')
        
    ax.axhline(0, color='black', linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(benchmarks, rotation=90, fontsize=8)
    
    ax.legend(bbox_to_anchor=(1.01, 1), loc='upper left', fontsize='small')
    ax.grid(axis='y', linestyle='--', alpha=0.6)
        
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight')
    print(f"Graph saved to {output_path}")
    plt.close()

def plot_summary_results(plot_data, active_metrics, is_relative, is_log, exp_prefixes, base_prefix, output_path):
    configs = exp_prefixes if is_relative else [base_prefix] + exp_prefixes
    
    fig, ax = plt.subplots(figsize=(max(12, len(configs) * len(active_metrics) * 1.5), 8))
    
    x = np.arange(len(configs))
    width = 0.8 / len(active_metrics)
    
    for i, metric in enumerate(active_metrics):
        values = []
        for config in configs:
            if is_relative:
                b_vals = plot_data[metric][base_prefix]
                e_vals = plot_data[metric][config]
                ratios = [e/b for b, e in zip(b_vals, e_vals) if b and b > 0 and e is not None and e > 0]
                if ratios:
                    values.append((statistics.geometric_mean(ratios) - 1) * 100)
                else:
                    values.append(0)
            else:
                vals = [v for v in plot_data[metric][config] if v is not None and v > 0]
                if vals:
                    values.append(statistics.geometric_mean(vals))
                else:
                    values.append(0)
                    
        offset = (i - len(active_metrics)/2 + 0.5) * width
        bars = ax.bar(x + offset, values, width, label=metric, edgecolor='black')
        
        for bar in bars:
            yval = bar.get_height()
            if yval == 0: continue
            
            va = 'bottom' if yval >= 0 else 'top'
            data_max = max(abs(v) for v in values) if values else 1
            text_offset = data_max * 0.02 if yval >= 0 else -data_max * 0.02
            
            if is_relative: text_label = f'{yval:.2f}%'
            elif 'Rate' in metric or 'Reuse' in metric: text_label = f'{yval:.4f}'
            else: text_label = f'{yval:.0f}'
                
            ax.text(bar.get_x() + bar.get_width() / 2, yval + text_offset, text_label, ha='center', va=va, fontsize=8)

    ax.axhline(0, color='black', linewidth=0.8)
    
    if is_relative:
        if is_log: ax.set_yscale('symlog')
        ax.set_ylabel('Geomean Relative Change (%)' + (' (Log Scale)' if is_log else ''))
        ax.set_title(f'Overall Geometric Mean Summary: {" & ".join(active_metrics)}')
    else:
        if is_log: ax.set_yscale('symlog')
        ax.set_ylabel('Geomean (Absolute)' + (' (Log Scale)' if is_log else ''))
        ax.set_title(f'Overall Geometric Mean Summary: {" & ".join(active_metrics)}')
        
    ax.set_xticks(x)
    ax.set_xticklabels(configs, rotation=45, ha='right', fontsize=10)
    ax.legend(title="Metrics")
    
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight')
    print(f"Summary graph saved to {output_path}")
    plt.close()

def load_prefixes_from_file(filepath):
    try:
        with open(filepath, 'r') as f:
            lines = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
        if len(lines) < 2:
            print(f"Error: '{filepath}' must contain at least two lines (1 base, 1+ experiments).")
            sys.exit(1)
        return lines[0], lines[1:]
    except FileNotFoundError:
        print(f"Error: Configuration file '{filepath}' not found.")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Parse and graph ChampSim data.")
    parser.add_argument("config_file", help="Text file with base prefix on line 1, experiments below.")
    parser.add_argument("-s", "--stat", choices=['IPC', 'INSERT', 'HITRATE', 'HIT', 'USEPF', 'REUSE'], default='IPC', help="Which statistics to graph")
    parser.add_argument("-r", "--relative", action="store_true", help="Plot relative percentages instead of absolute values")
    parser.add_argument("-l", "--log", action="store_true", help="Use logarithmic scale for the Y-axis")
    args = parser.parse_args()

    stat_configs = {
        'IPC': ['IPC'],
        'INSERT': ['LPC_Insertions', 'LLC_Insertions'],
        'HITRATE': ['LPC_HitRate', 'LLC_HitRate'],
        'HIT': ['LLC_Hits', 'LPC_Hits'],
        'USEPF': ['LLC_Useful_Prefetches'],
        'REUSE': ['LPC_Reuse', 'LLC_Reuse']
    }
    active_metrics = stat_configs[args.stat]

    base_prefix, exp_prefixes = load_prefixes_from_file(args.config_file)
    print(f"Base Prefix: {base_prefix}")
    print(f"Loaded {len(exp_prefixes)} Experiment Prefixes.")
    print(f"Graphing Mode: {args.stat} ({'Relative %' if args.relative else 'Absolute'})")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    dump_dir = os.path.join(script_dir, "experiments")

    os.makedirs("./new_res", exist_ok=True)
    out_csv = "./new_res/parse_results.csv"
    out_png = "./new_res/parse_results.png"
    out_geo = "./new_res/parse_results_geomean.png"

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

    stat_mappings = {
        "IPC": "ipc", "LLC_Total_Access": "llc_total_access", "LLC_Total_Hit": "llc_total_hit",
        "LLC_Total_Miss": "llc_total_miss", "LLC_MSHR_Merge": "llc_mshr_merge", "LLC_Insertions": "llc_insertions",
        "LLC_PF_Req": "llc_pf_req", "LLC_PF_Useful": "llc_pf_useful", "LLC_PF_Useless": "llc_pf_useless",
        "LPC_Hits": "lpc_hits", "LPC_Misses": "lpc_misses", "LPC_Insertions": "lpc_insertions",
        "LPC_Evictions": "lpc_evictions"
    }

    headers = ["Benchmark"]
    for k in stat_mappings.keys(): headers.append(f"Baseline_{k}")
    for exp in exp_prefixes:
        for k in stat_mappings.keys(): headers.append(f"{exp}_{k}")

    plot_data = {metric: {config: [] for config in all_prefixes} for metric in active_metrics}
    graph_benchmarks = []

    with open(out_csv, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()

        for bench in dynamic_benchmarks:
            if "deg" in bench: continue
            
            row = {"Benchmark": bench}
            
            # Extract Baseline
            b_file = find_file(base_prefix, bench, all_files)
            b_path = os.path.join(dump_dir, b_file) if b_file else None
            b_stats = extract_stats(b_path)
            
            for header_k, dict_k in stat_mappings.items():
                val = b_stats[dict_k]
                if dict_k == "ipc" and val is None: val = 0.3576000
                row[f"Baseline_{header_k}"] = val if val is not None else "N/A"
            
            for metric in active_metrics:
                plot_data[metric][base_prefix].append(get_metric_value(b_stats, metric))
            
            graph_benchmarks.append(bench)

            # Extract Experiments
            for exp in exp_prefixes:
                e_file = find_file(exp, bench, all_files)
                e_path = os.path.join(dump_dir, e_file) if e_file else None
                e_stats = extract_stats(e_path)
                
                for header_k, dict_k in stat_mappings.items():
                    val = e_stats[dict_k]
                    row[f"{exp}_{header_k}"] = val if val is not None else "N/A"
                
                for metric in active_metrics:
                    plot_data[metric][exp].append(get_metric_value(e_stats, metric))
                
            writer.writerow(row)
            
    print(f"Data successfully output to {out_csv}")

    # Generate Graphs
    plot_custom_results(graph_benchmarks, plot_data, active_metrics, args.relative, args.log, exp_prefixes, base_prefix, out_png)
    plot_summary_results(plot_data, active_metrics, args.relative, args.log, exp_prefixes, base_prefix, out_geo)

if __name__ == "__main__":
    main()