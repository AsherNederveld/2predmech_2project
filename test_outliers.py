import nmplus
base_prefix, exp_prefixes = nmplus.load_prefixes_from_file("runconfigs/7_mj_sweep.txt")
args_stat = 'REUSE'
active_metrics = ['LPC_Reuse', 'LLC_Reuse']
all_prefixes = [base_prefix] + exp_prefixes

import os
dump_dir = "experiments"
all_files = os.listdir(dump_dir)
dynamic_benchmarks = nmplus.get_dynamic_benchmarks(all_prefixes, all_files)

plot_data = {metric: {config: [] for config in all_prefixes} for metric in active_metrics}

for bench in dynamic_benchmarks:
    if "deg" in bench: continue
    
    b_file = nmplus.find_file(base_prefix, bench, all_files)
    b_path = os.path.join(dump_dir, b_file) if b_file else None
    b_stats = nmplus.extract_stats(b_path)
    
    for metric in active_metrics:
        plot_data[metric][base_prefix].append(nmplus.get_metric_value(b_stats, metric))
        
    for exp in exp_prefixes:
        e_file = nmplus.find_file(exp, bench, all_files)
        e_path = os.path.join(dump_dir, e_file) if e_file else None
        e_stats = nmplus.extract_stats(e_path)
        
        for metric in active_metrics:
            plot_data[metric][exp].append(nmplus.get_metric_value(e_stats, metric))

for metric in active_metrics:
    print("Metric:", metric)
    for config in all_prefixes:
        vals = [v for v in plot_data[metric][config] if v is not None]
        if vals:
            print(f"  {config}: max={max(vals)}, min={min(vals)}")
