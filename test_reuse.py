import nmplus

stats = nmplus.extract_stats("experiments/champsim_mockingjay.orig_triage_16_lpc_llc_filtAll_256_32_nprom_lru.astar_23B.trace.gz.out")
print("LPC_Hits:", stats.get("lpc_hits"))
print("LPC_Insertions:", stats.get("lpc_insertions"))
val = nmplus.get_metric_value(stats, "LPC_Reuse")
print("LPC_Reuse:", val)

