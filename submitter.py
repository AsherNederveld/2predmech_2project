import os
import subprocess

# Configuration
executables = ["champsim_bp", "champsim_bpb", "champsim_bpt"]  # List of executables to run

# Each entry: (trace_list_file, input_path_prefix, output_suffix)
# Updated to use absolute paths to avoid relative pathing issues
jobs = [
    ("traces_list.txt", "/scratch/cluster/akanksha/CRCRealTraces/", ""),
    ("real.txt", "/scratch/cluster/qduong/actual_graphs_1B/traces/", ""),
    ("synthetic.txt", "/scratch/cluster/qduong/synthetic_graphs_1B/traces/", "s"),
]

condor_dir = "./condor_jobs"  # Where job files will be written
os.makedirs(condor_dir, exist_ok=True)

# Base job file template
job_template = """\
executable            = /projects/coursework/2026-spring/cs395t-lin/mbd2325/ChampSim/bin/{exe}
arguments             = --warmup-instructions 200000000 --simulation-instructions 200000000 $(trace)

+Group                = "GUEST"
+Project              = "ARCHITECTURE"
+ProjectDescription   = "ChampSim run"

environment           = "LD_LIBRARY_PATH=/scratch/cluster/speedway/opt/gcc/14.2.0/lib64:$LD_LIBRARY_PATH"

should_transfer_files     = YES
when_to_transfer_output   = ON_EXIT
transfer_input_files      = bin/{exe}, {input_path}$(trace)

output                = /scratch/cluster/mbd2325/{exe}.$(trace).out

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