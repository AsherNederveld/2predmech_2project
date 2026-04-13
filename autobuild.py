import json
import subprocess
import os

# List of configuration names based on your naming convention:
# champsim_<LLC Replacement Policy>_<LLC Prefetcher>_<LLC Ways>_<LPC Enable>_<Allow L1/L2 in LPC>_<enable_llc_filter>
configs = [
    "champsim_mockingjay.orig_triage_16_lpc_llc_filtAll",
    "champsim_mockingjay.orig_triage_16_lpc_all_filtAll",
    "champsim_mockingjay.orig_triage_17_nlpc_llc_filtNone",
    "champsim_mockingjay.orig_triage_17_nlpc_all_filtNonLLC",
    "champsim_mockingjay.orig_no_16_nlpc_all_filtNone",
    "champsim_mockingjay.orig_no_16_nlpc_all_filtAll"
]

CONFIG_FILE = "start_config.json"

def run_experiment(config_name):
    # 1. Parse the naming convention
    # Splitting by underscores
    parts = config_name.split('_')
    
    # Expected format: [champsim, replacement, prefetcher, ways, lpc, allow, filter]
    if len(parts) < 7:
        print(f"Skipping {config_name}: Name does not match convention.")
        return

    replacement_policy = "mockingjay_orig" if parts[1] == "mockingjay.orig" else parts[1]
    prefetcher_name = parts[2]
    llc_ways = int(parts[3])
    lpc_enable_str = parts[4]
    allow_str = parts[5]
    filter_str = parts[6]

    # 2. Map string codes to Boolean values
    lpc_enable = True if lpc_enable_str == "lpc" else False
    allow_l1l2 = True if allow_str == "all" else False

    # Filter Logic:
    # filtAll: both True | filtnonLLC: all=False, partial=True | filtNone: both False
    if filter_str == "filtAll":
        f_all, f_partial = True, True
    elif filter_str == "filtnonLLC":
        f_all, f_partial = False, True
    else:  # filtNone
        f_all, f_partial = False, False

    # 3. Load, Modify, and Save JSON
    if not os.path.exists(CONFIG_FILE):
        print(f"Error: {CONFIG_FILE} not found.")
        return

    with open(CONFIG_FILE, 'r') as f:
        data = json.load(f)

    # Apply updates
    data["executable_name"] = config_name
    data["LLC"]["ways"] = llc_ways
    data["LLC"]["prefetcher"] = prefetcher_name
    data["LLC"]["replacement"] = replacement_policy
    data["LLC"]["enable_lpc"] = lpc_enable
    data["LLC"]["allow_l1l2_in_lpc"] = allow_l1l2
    data["LLC"]["enable_llc_filter_all"] = f_all
    data["LLC"]["enable_llc_filter_partial"] = f_partial

    with open(CONFIG_FILE, 'w') as f:
        json.dump(data, f, indent=4)

    print(f"\n--- Processed config for: {config_name} ---")

    # 4. Execute shell commands
    try:
        print(f"Running config.sh...")
        subprocess.run(["./config.sh", CONFIG_FILE], check=True)
        
        print(f"Running make -j 4...")
        subprocess.run(["make", "-j", "4"], check=True)
        
        print(f"Successfully built: {config_name}")
    except subprocess.CalledProcessError as e:
        print(f"Error during execution for {config_name}: {e}")

if __name__ == "__main__":
    for cfg in configs:
        run_experiment(cfg)