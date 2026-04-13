import os
import csv
import re
import subprocess
import statistics

# ... (BENCHMARK_ORDER remains the same) ...
BENCHMARK_ORDER = [
    "astar_163B", "astar_23B", "astar_313B",
    "bfs__amazon-2008-mtx__17000000000", "bfs__amazon-2008-mtx__19000000000",
    "bfs__amazon-2008-mtx__23000000000", "bfs__citationCiteseer-mtx__1000000000",
    "bfs__citationCiteseer-mtx__4000000000", "bfs__citationCiteseer-mtx__7000000000",
    "bfs__com-Youtube-mtx__11000000000", "bfs__com-Youtube-mtx__14000000000",
    "bfs__com-Youtube-mtx__5000000000", "bfs__dblp-2010-mtx__1000000000",
    "bfs__dblp-2010-mtx__4000000000", "bfs__luxembourg_osm-mtx__0",
    "bfs__netherlands_osm-mtx__37000000000", "bfs__netherlands_osm-mtx__4000000000",
    "bwaves_1609B", "bwaves_1861B", "bwaves_98B",
    "calculix_2655B", "calculix_2670B", "calculix_3812B",
    "cc__amazon-2008-mtx__17000000000", "cc__amazon-2008-mtx__19000000000",
    "cc__amazon-2008-mtx__25000000000", "cc__citationCiteseer-mtx__1000000000",
    "cc__citationCiteseer-mtx__5000000000", "cc__com-Youtube-mtx__11000000000",
    "cc__com-Youtube-mtx__13000000000", "cc__com-Youtube-mtx__4000000000",
    "cc__dblp-2010-mtx__1000000000", "cc__dblp-2010-mtx__3000000000",
    "cc__dblp-2010-mtx__6000000000", "cc__luxembourg_osm-mtx__0",
    "cc__netherlands_osm-mtx__11000000000", "cc__netherlands_osm-mtx__2000000000",
    "gcc_13B", "gcc_39B", "gcc_56B",
    "mcf_158B", "mcf_250B", "mcf_46B",
    "omnetpp_17B", "omnetpp_340B", "omnetpp_4B",
    "perlbench_105B", "perlbench_135B", "perlbench_53B",
    "bfs__kron-18__269000000000", "bfs__urand-17__39000000000",
    "bfs__urand-17__699000000000", "bfs__urand-18__1342000000000",
    "bfs__urand-18__2050000000000", "cc__kron-18__366000000000",
    "cc__urand-17__1304000000000", "cc__urand-17__550000000000",
    "cc__urand-18__2669000000000", "soplex_205B",
    "soplex_217B", "soplex_66B", "sphinx3_1339B",
    "sphinx3_2520B", "sphinx3_883B", "xalancbmk_748B",
    "xalancbmk_768B", "xalancbmk_99B"
]

def normalize(name):
    return name.replace('-', '_').replace('.', '_').lower()

def extract_stats(filepath):
    stats = {"ipc": None, "hits": None, "inserts": None}
    if not filepath or not os.path.exists(filepath):
        return stats
    try:
        cmd = f"grep -E 'cumulative IPC|Total Hits in buffer|Total Inserted into buffer' '{filepath}'"
        out = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL)
        ipc_matches = re.findall(r"cumulative IPC:\s*([\d.]+)", out)
        hits_matches = re.findall(r"(\d+)\s*Total Hits in buffer", out)
        ins_matches = re.findall(r"(\d+)\s*Total Inserted into buffer", out)
        if ipc_matches: stats["ipc"] = float(ipc_matches[-1])
        if hits_matches: stats["hits"] = int(hits_matches[-1])
        if ins_matches: stats["inserts"] = int(ins_matches[-1])
    except Exception:
        pass
    return stats

def find_file(prefix, bench, all_files):
    norm_bench = normalize(bench)
    for filename in all_files:
        if filename.startswith(prefix) and filename.endswith('.out'):
            if norm_bench in normalize(filename):
                return filename
    return None

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Define the directory where result files are actually stored
    dump_dir = os.path.join(script_dir, "dump")
    
    output_filename = "./new_res/zzz_ipc_drrip_results.csv"
    headers = ["Benchmark", "Baseline_IPC", "Experimental_IPC", "Speedup", 
               "Buffer_Hits", "Buffer_Inserts", "Buffer_Hit_Rate"]

    # List files inside the dump directory
    if not os.path.exists(dump_dir):
        print(f"Error: Directory {dump_dir} does not exist.")
        return

    all_files = os.listdir(dump_dir)
    all_files.sort()

    speedup_ratios = []

    with open(output_filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()

        for bench in BENCHMARK_ORDER:
            # Removed "./dump/" from prefixes because listdir returns just the filenames
            base_prefix = "champsim_drrip_base"
            exp_prefix = "champsim_drrip_bypass"
            
            baseline_file = find_file(base_prefix, bench, all_files)
            experimental_file = find_file(exp_prefix, bench, all_files)
            
            # Use dump_dir for joining paths
            b_path = os.path.join(dump_dir, baseline_file) if baseline_file else None
            e_path = os.path.join(dump_dir, experimental_file) if experimental_file else None
            
            b_stats = extract_stats(b_path)
            e_stats = extract_stats(e_path)
            
            row = {"Benchmark": bench}
            row["Baseline_IPC"] = b_stats["ipc"] if b_stats["ipc"] is not None else "N/A"
            row["Experimental_IPC"] = e_stats["ipc"] if e_stats["ipc"] is not None else "N/A"
            
            if isinstance(row["Baseline_IPC"], float) and isinstance(row["Experimental_IPC"], float):
                ratio = row["Experimental_IPC"] / row["Baseline_IPC"]
                speedup_ratios.append(ratio)
                speedup_pct = (ratio - 1) * 100
                row["Speedup"] = f"{speedup_pct:.2f}%"
            else:
                row["Speedup"] = "N/A"
            
            row["Buffer_Hits"] = e_stats["hits"] if e_stats["hits"] is not None else "N/A"
            row["Buffer_Inserts"] = e_stats["inserts"] if e_stats["inserts"] is not None else "N/A"
            
            if e_stats["hits"] is not None and e_stats["inserts"] is not None:
                total = e_stats["hits"] + e_stats["inserts"]
                row["Buffer_Hit_Rate"] = f"{(e_stats['hits'] / total * 100):.2f}%" if total > 0 else "0.00%"
            else:
                row["Buffer_Hit_Rate"] = "N/A"
                
            writer.writerow(row)
            
    print(f"Data successfully output to {output_filename}")

    if speedup_ratios:
        gmean_ratio = statistics.geometric_mean(speedup_ratios)
        gmean_speedup_pct = (gmean_ratio - 1) * 100
        print(f"\nOverall Geometric Mean Speedup: {gmean_speedup_pct:.2f}%")
    else:
        print("\nNo valid IPC data found to calculate Geometric Mean.")

if __name__ == "__main__":
    main()