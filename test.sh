# ./config.sh test_config.json
# make -j 4
bin/champsim_mockingjay.orig_triage_16_lpc_llc_filtAll_256_32_nprom_lru --warmup-instructions 5000000 \
--simulation-instructions 10000000 \
--json stats_vibe.json /scratch/cluster/speedway/cs395t/hw1/part1/traces/bfs_small.xz