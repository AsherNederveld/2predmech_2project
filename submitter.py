import os
import subprocess

# Configuration
executables = [
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
    # "champsim_mockingjay.orig_triage_16_lpc_llc_filtAll_256_32_nprom_lru",
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
# Each entry: (trace_list_file, input_path_prefix, output_suffix)
# Updated to use absolute paths to avoid relative pathing issues
jobs = [
    ("traces_list.txt", "/scratch/cluster/akanksha/CRCRealTraces/", ""),
    ("real.txt", "/scratch/cluster/qduong/actual_graphs_1B/traces/", ""),
    ("synthetic.txt", "/scratch/cluster/mbd2325/predmech_traces/", "s"),
    # ("google.txt", "/scratch/cluster/mbd2325/googletraces/", ""),
]

condor_dir = "./condor_jobs"  # Where job files will be written
os.makedirs(condor_dir, exist_ok=True)

# bypass job file template
job_template = """\
executable            = /projects/coursework/2026-spring/cs395t-lin/asher/take2/2predmech_2project/bin/{exe}
arguments             = --warmup-instructions 200000000 --simulation-instructions 500000000 $(trace)

+Group                = "GUEST"
+Project              = "ARCHITECTURE"
+ProjectDescription   = "ChampSim run"

environment           = "LD_LIBRARY_PATH=/scratch/cluster/speedway/opt/gcc/14.2.0/lib64:$LD_LIBRARY_PATH"

should_transfer_files     = YES
when_to_transfer_output   = ON_EXIT
transfer_input_files      = bin/{exe}, {input_path}$(trace)

output                = /projects/coursework/2026-spring/cs395t-lin/asher/take2/2predmech_2project/experiments/{exe}.$(trace).out

request_memory = 256MB
request_disk = 1500000

queue trace from {trace_file}
"""

def create_and_submit_jobs():
    for exe in executables:
        for trace_file, input_path, suffix in jobs:
            job_filename = f"{condor_dir}/{exe}_{trace_file}.condor"
            with open(job_filename, "w") as f:
                f.write(job_template.format(exe=exe, trace_file=trace_file, input_path=input_path, suffix=suffix))
            print(f"Submitting job file: {job_filename}")
            subprocess.run(["condor_submit", job_filename], check=True)

if __name__ == "__main__":
    create_and_submit_jobs()