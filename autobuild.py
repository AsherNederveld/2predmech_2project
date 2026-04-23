import json
import subprocess
import os

# List of configuration names based on your naming convention:
# champsim_<LLC Replacement Policy>_<LLC Prefetcher>_<LLC Ways>_<LPC Enable>_<Allow L1/L2 in LPC>_<enable_llc_filter>_<LPC Ways>_<LPC Sets>_<LPC Allow Promotion> where LPC Allow Promotion is _prom for true
configs = [
     # No pref_base
    # "champsim_mockingjay.orig_no_17_nlpc_llc_filtNone_256_32_prom_lru",
    # "champsim_pacman_no_17_nlpc_llc_filtNone_256_32_prom_lru",
    # "champsim_drrip_no_17_nlpc_llc_filtNone_256_32_prom_lru",
    # "champsim_ship_no_17_nlpc_llc_filtNone_256_32_prom_lru",
    # "champsim_srrip_no_17_nlpc_llc_filtNone_256_32_prom_lru",
    # "champsim_random_no_17_nlpc_llc_filtNone_256_32_prom_lru",
    "champsim_lru_no_17_nlpc_llc_filtNone_256_32_prom_lru",
    # No pref_filter
    # "champsim_mockingjay.orig_no_17_nlpc_llc_filtAll_256_32_prom_lru",
    # "champsim_pacman_no_17_nlpc_llc_filtAll_256_32_prom_lru",
    # "champsim_drrip_no_17_nlpc_llc_filtAll_256_32_prom_lru",
    # "champsim_ship_no_17_nlpc_llc_filtAll_256_32_prom_lru",
    # "champsim_srrip_no_17_nlpc_llc_filtAll_256_32_prom_lru",
    # "champsim_random_no_17_nlpc_llc_filtAll_256_32_prom_lru",
    "champsim_lru_no_17_nlpc_llc_filtAll_256_32_prom_lru",

    # pythia pref_base
    # "champsim_mockingjay.orig_pythia_17_nlpc_llc_filtNone_256_32_prom_lru",
    # "champsim_pacman_pythia_17_nlpc_llc_filtNone_256_32_prom_lru",
    # "champsim_drrip_pythia_17_nlpc_llc_filtNone_256_32_prom_lru",
    # "champsim_ship_pythia_17_nlpc_llc_filtNone_256_32_prom_lru",
    # "champsim_srrip_pythia_17_nlpc_llc_filtNone_256_32_prom_lru",
    # "champsim_random_pythia_17_nlpc_llc_filtNone_256_32_prom_lru",
    "champsim_lru_pythia_17_nlpc_llc_filtNone_256_32_prom_lru",

    # triage pref_base
    # "champsim_mockingjay.orig_triage_17_nlpc_llc_filtNone_256_32_prom_lru",
    # "champsim_pacman_triage_17_nlpc_llc_filtNone_256_32_prom_lru",
    # "champsim_drrip_triage_17_nlpc_llc_filtNone_256_32_prom_lru",
    # "champsim_ship_triage_17_nlpc_llc_filtNone_256_32_prom_lru",
    # "champsim_srrip_triage_17_nlpc_llc_filtNone_256_32_prom_lru",
    # "champsim_random_triage_17_nlpc_llc_filtNone_256_32_prom_lru",
    "champsim_lru_triage_17_nlpc_llc_filtNone_256_32_prom_lru",

    # sms pref_base
    # "champsim_mockingjay.orig_sms_17_nlpc_llc_filtNone_256_32_prom_lru",
    # "champsim_pacman_sms_17_nlpc_llc_filtNone_256_32_prom_lru",
    # "champsim_drrip_sms_17_nlpc_llc_filtNone_256_32_prom_lru",
    # "champsim_ship_sms_17_nlpc_llc_filtNone_256_32_prom_lru",
    # "champsim_srrip_sms_17_nlpc_llc_filtNone_256_32_prom_lru",
    # "champsim_random_sms_17_nlpc_llc_filtNone_256_32_prom_lru",
    "champsim_lru_sms_17_nlpc_llc_filtNone_256_32_prom_lru",

    # pythia pref_bp
    # "champsim_mockingjay.orig_pythia_17_nlpc_llc_filtNonLLC_256_32_prom_lru",
    # "champsim_pacman_pythia_17_nlpc_llc_filtNonLLC_256_32_prom_lru",
    # "champsim_drrip_pythia_17_nlpc_llc_filtNonLLC_256_32_prom_lru",
    # "champsim_ship_pythia_17_nlpc_llc_filtNonLLC_256_32_prom_lru",
    # "champsim_srrip_pythia_17_nlpc_llc_filtNonLLC_256_32_prom_lru",
    # "champsim_random_pythia_17_nlpc_llc_filtNonLLC_256_32_prom_lru",
    "champsim_lru_pythia_17_nlpc_llc_filtNonLLC_256_32_prom_lru",

    # triage pref_bp
    # "champsim_mockingjay.orig_triage_17_nlpc_llc_filtNonLLC_256_32_prom_lru",
    # "champsim_pacman_triage_17_nlpc_llc_filtNonLLC_256_32_prom_lru",
    # "champsim_drrip_triage_17_nlpc_llc_filtNonLLC_256_32_prom_lru",
    # "champsim_ship_triage_17_nlpc_llc_filtNonLLC_256_32_prom_lru",
    # "champsim_srrip_triage_17_nlpc_llc_filtNonLLC_256_32_prom_lru",
    # "champsim_random_triage_17_nlpc_llc_filtNonLLC_256_32_prom_lru",
    "champsim_lru_triage_17_nlpc_llc_filtNonLLC_256_32_prom_lru",

    # sms pref_bp
    # "champsim_mockingjay.orig_sms_17_nlpc_llc_filtNonLLC_256_32_prom_lru",
    # "champsim_pacman_sms_17_nlpc_llc_filtNonLLC_256_32_prom_lru",
    # "champsim_drrip_sms_17_nlpc_llc_filtNonLLC_256_32_prom_lru",
    # "champsim_ship_sms_17_nlpc_llc_filtNonLLC_256_32_prom_lru",
    # "champsim_srrip_sms_17_nlpc_llc_filtNonLLC_256_32_prom_lru",
    # "champsim_random_sms_17_nlpc_llc_filtNonLLC_256_32_prom_lru",
    "champsim_lru_sms_17_nlpc_llc_filtNonLLC_256_32_prom_lru",

    # pythia pref_lpc
    # "champsim_mockingjay.orig_pythia_16_lpc_llc_filtAll_256_32_nprom_lru",
    # "champsim_pacman_pythia_16_lpc_llc_filtAll_256_32_nprom_lru",
    # "champsim_drrip_pythia_16_lpc_llc_filtAll_256_32_nprom_lru",
    # "champsim_ship_pythia_16_lpc_llc_filtAll_256_32_nprom_lru",
    # "champsim_srrip_pythia_16_lpc_llc_filtAll_256_32_nprom_lru",
    # "champsim_random_pythia_16_lpc_llc_filtAll_256_32_nprom_lru",
    "champsim_lru_pythia_16_lpc_llc_filtAll_256_32_nprom_lru",

    # triage pref_lpc
    # "champsim_mockingjay.orig_triage_16_lpc_llc_filtAll_256_32_nprom_lru",
    # "champsim_pacman_triage_16_lpc_llc_filtAll_256_32_nprom_lru",
    # "champsim_drrip_triage_16_lpc_llc_filtAll_256_32_nprom_lru",
    # "champsim_ship_triage_16_lpc_llc_filtAll_256_32_nprom_lru",
    # "champsim_srrip_triage_16_lpc_llc_filtAll_256_32_nprom_lru",
    # "champsim_random_triage_16_lpc_llc_filtAll_256_32_nprom_lru",
    "champsim_lru_triage_16_lpc_llc_filtAll_256_32_nprom_lru",
    
    # sms pref_lpc
    # "champsim_mockingjay.orig_sms_16_lpc_llc_filtAll_256_32_nprom_lru",
    # "champsim_pacman_sms_16_lpc_llc_filtAll_256_32_nprom_lru",
    # "champsim_drrip_sms_16_lpc_llc_filtAll_256_32_nprom_lru",
    # "champsim_ship_sms_16_lpc_llc_filtAll_256_32_nprom_lru",
    # "champsim_srrip_sms_16_lpc_llc_filtAll_256_32_nprom_lru",
    # "champsim_random_sms_16_lpc_llc_filtAll_256_32_nprom_lru",
    "champsim_lru_sms_16_lpc_llc_filtAll_256_32_nprom_lru",
    
    # triage pref_lpc_wayset
    # "champsim_mockingjay.orig_triage_16_lpc_llc_filtAll_8192_1_nprom_lru",
    # "champsim_mockingjay.orig_triage_16_lpc_llc_filtAll_4096_2_nprom_lru",
    # "champsim_mockingjay.orig_triage_16_lpc_llc_filtAll_2048_4_nprom_lru",
    # "champsim_mockingjay.orig_triage_16_lpc_llc_filtAll_1024_8_nprom_lru",
    # "champsim_mockingjay.orig_triage_16_lpc_llc_filtAll_512_16_nprom_lru",
    # #champsim_mockingjay.orig_triage_16_lpc_llc_filtAll_256_32_nprom_lru",
    # "champsim_mockingjay.orig_triage_16_lpc_llc_filtAll_128_64_nprom_lru",
    # "champsim_mockingjay.orig_triage_16_lpc_llc_filtAll_64_128_nprom_lru",
    # "champsim_mockingjay.orig_triage_16_lpc_llc_filtAll_32_256_nprom_lru",
    # "champsim_mockingjay.orig_triage_16_lpc_llc_filtAll_16_512_nprom_lru",

    # triage pref_lpc_repl
    #champsim_mockingjay.orig_triage_16_lpc_llc_filtAll_256_32_nprom_lru",
    # "champsim_mockingjay.orig_triage_16_lpc_llc_filtAll_256_32_nprom_srrip",
    # "champsim_mockingjay.orig_triage_16_lpc_llc_filtAll_256_32_nprom_random",

    # triage pref_lpc_size
    #champsim_mockingjay.orig_triage_16_lpc_llc_filtAll_256_32_nprom_lru",
    # "champsim_mockingjay.orig_triage_16_lpc_all_filtAll_256_32_nprom_lru",

    # "champsim_mockingjay.orig_triage_15_lpc_llc_filtAll_256_64_nprom_lru",
    # "champsim_mockingjay.orig_triage_15_lpc_all_filtAll_256_64_nprom_lru",

    # "champsim_mockingjay.orig_triage_14_lpc_llc_filtAll_256_96_nprom_lru",
    # "champsim_mockingjay.orig_triage_14_lpc_all_filtAll_256_96_nprom_lru",
    
    # "champsim_mockingjay.orig_triage_13_lpc_llc_filtAll_256_128_nprom_lru",
    # "champsim_mockingjay.orig_triage_13_lpc_all_filtAll_256_128_nprom_lru",

    # "champsim_mockingjay.orig_triage_12_lpc_llc_filtAll_256_160_nprom_lru",
    # "champsim_mockingjay.orig_triage_12_lpc_all_filtAll_256_160_nprom_lru",

    # "champsim_mockingjay.orig_triage_11_lpc_llc_filtAll_256_192_nprom_lru",
    # "champsim_mockingjay.orig_triage_11_lpc_all_filtAll_256_192_nprom_lru"
]

CONFIG_FILE = "start_config.json"

def run_experiment(config_name):
    # 1. Parse the naming convention
    # Splitting by underscores
    parts = config_name.split('_')
    
    # Expected format: [champsim, replacement, prefetcher, ways, lpc, allow, filter]
    if len(parts) < 7:
        print(f"Skipping {config_name}: Name does not match convention")
        return

    replacement_policy = "mockingjay_orig" if parts[1] == "mockingjay.orig" else parts[1]
    prefetcher_name = parts[2]
    llc_ways = int(parts[3])
    lpc_enable_str = parts[4]
    allow_str = parts[5]
    filter_str = parts[6]
    
    # New LPC structural parameters
    lpc_ways = int(parts[7]) if len(parts) > 7 else 16
    lpc_sets = int(parts[8]) if len(parts) > 8 else 512
    lpc_allow_promotion = True if len(parts) > 9 and parts[9] == "prom" else False
    lpc_replacement_policy = parts[10] if len(parts) > 10 else "lru"

    # 2. Map string codes to Boolean values
    lpc_enable = True if lpc_enable_str == "lpc" and "n" not in lpc_enable_str else False
    allow_l1l2 = True if allow_str == "all" and lpc_enable == True else False

    # Filter Logic:
    # filtAll: both True | filtnonLLC: all=False, partial=True | filtNone: both False
    if filter_str == "filtAll":
        f_all, f_partial = True, True
    elif filter_str == "filtNonLLC":
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
    data["LLC"]["lpc_ways"] = lpc_ways
    data["LLC"]["lpc_sets"] = lpc_sets
    data["LLC"]["lpc_allow_promotion"] = lpc_allow_promotion
    data["LLC"]["lpc_replacement_policy"] = lpc_replacement_policy

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