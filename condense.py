import os
import re
import csv

def extract_stats(filepath):
    stats = {"File": os.path.basename(filepath), "IPC": None, "LLC_MPKI": None}
    if not os.path.exists(filepath):
        return stats
    
    try:
        with open(filepath, 'r') as f:
            content = f.read()

        ipc_matches = re.findall(r"cumulative IPC:\s*([\d.]+)", content)
        if ipc_matches:
            stats["IPC"] = float(ipc_matches[-1])
        
        inst_matches = re.findall(r"instructions:\s*(\d+)", content)
        if inst_matches:
            instructions = int(inst_matches[-1])
        else:
            instructions = 0
            
        llc_misses_matches = re.findall(r"LLC TOTAL\s+ACCESS:\s+\d+\s+HIT:\s+\d+\s+MISS:\s+(\d+)", content)
        if llc_misses_matches:
            llc_misses = int(llc_misses_matches[-1])
        else:
            llc_misses = 0
            
        if instructions > 0 and llc_misses_matches:
            stats["LLC_MPKI"] = (llc_misses / float(instructions)) * 1000.0
            
    except Exception as e:
        print("Error reading {}: {}".format(filepath, e))
        
    return stats

def main():
    dump_dir = "./new_res"
    output_csv = "condensed_new_res.csv"
    
    if not os.path.exists(dump_dir):
        print("Directory {} does not exist.".format(dump_dir))
        return
        
    all_files = [f for f in os.listdir(dump_dir) if f.endswith(".out")]
    all_files.sort()
    
    results = []
    for f in all_files:
        filepath = os.path.join(dump_dir, f)
        stats = extract_stats(filepath)
        results.append(stats)
        
    with open(output_csv, 'w') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=["File", "IPC", "LLC_MPKI"])
        writer.writeheader()
        for row in results:
            writer.writerow(row)
            
    print("Processed {} files. Results saved to {}".format(len(results), output_csv))

if __name__ == "__main__":
    main()
