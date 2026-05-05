import csv

with open('new_res/parse_results.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        print(row['champsim_mockingjay.orig_triage_16_lpc_llc_filtAll_256_32_nprom_lru_LPC_Hits'], 
              row['champsim_mockingjay.orig_triage_16_lpc_llc_filtAll_256_32_nprom_lru_LPC_Insertions'])
        break
