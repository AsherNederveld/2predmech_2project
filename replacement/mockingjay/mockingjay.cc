#include "mockingjay.h"
#include <algorithm>
#include <cassert>

mockingjay::mockingjay(CACHE* cache) : champsim::modules::replacement(cache), cache(cache),
    NUM_SET(cache->NUM_SET), NUM_WAY(cache->NUM_WAY), LOG2_BLOCK_SIZE(6)
{
    LOG2_LLC_SET = std::log2(NUM_SET);
    LOG2_LLC_SIZE = LOG2_LLC_SET + std::log2(NUM_WAY) + LOG2_BLOCK_SIZE;
    LOG2_SAMPLED_SETS = std::max(0L, LOG2_LLC_SIZE - 16);
   
    INF_RD = NUM_WAY * HISTORY - 1;
    INF_ETR = (NUM_WAY * HISTORY / GRANULARITY) - 1;
    MAX_RD = INF_RD - 22;

    SAMPLED_CACHE_TAG_BITS = 31 - LOG2_LLC_SIZE;
    PC_SIGNATURE_BITS = LOG2_LLC_SIZE - 10;
}

bool mockingjay::is_sampled_set(int set) {
    int mask_length = LOG2_LLC_SET-LOG2_SAMPLED_SETS;
    int mask = (1 << mask_length) - 1;
    return (set & mask) == ((set >> (LOG2_LLC_SET - mask_length)) & mask);
}

uint64_t mockingjay::CRC_HASH(uint64_t _blockAddress) {
    static const unsigned long long crcPolynomial = 3988292384ULL;
    unsigned long long _returnVal = _blockAddress;
    for (unsigned int i = 0; i < 3; i++)
        _returnVal = ((_returnVal & 1) == 1) ? ((_returnVal >> 1) ^ crcPolynomial) : (_returnVal >> 1);
    return _returnVal;
}

uint64_t mockingjay::get_pc_signature(uint64_t pc, bool hit, bool prefetch, uint32_t core) {
    pc = pc << 1;
    if (hit) pc = pc | 1;
    pc = pc << 1;
    if (prefetch) pc = pc | 1;                            
    pc = CRC_HASH(pc);
    if (64 > PC_SIGNATURE_BITS) {
        pc = (pc << (64 - PC_SIGNATURE_BITS)) >> (64 - PC_SIGNATURE_BITS);
    }
    return pc;
}

uint32_t mockingjay::get_sampled_cache_index(uint64_t full_addr) {
    full_addr = full_addr >> LOG2_BLOCK_SIZE;
    if (64 > (LOG2_SAMPLED_CACHE_SETS + LOG2_LLC_SET)) {
        full_addr = (full_addr << (64 - (LOG2_SAMPLED_CACHE_SETS + LOG2_LLC_SET))) >> (64 - (LOG2_SAMPLED_CACHE_SETS + LOG2_LLC_SET));
    }
    return full_addr;
}

uint64_t mockingjay::get_sampled_cache_tag(uint64_t x) {
    x >>= LOG2_LLC_SET + LOG2_BLOCK_SIZE + LOG2_SAMPLED_CACHE_SETS;
    if (64 > SAMPLED_CACHE_TAG_BITS) {
        x = (x << (64 - SAMPLED_CACHE_TAG_BITS)) >> (64 - SAMPLED_CACHE_TAG_BITS);
    }
    return x;
}

int mockingjay::search_sampled_cache(uint64_t blockAddress, uint32_t set) {
    auto& sampled_set = sampled_cache[set];
    for (int way = 0; way < SAMPLED_CACHE_WAYS; way++) {
        if (sampled_set[way].valid && (sampled_set[way].tag == blockAddress)) {
            return way;
        }
    }
    return -1;
}

void mockingjay::detrain(uint32_t set, int way) {
    SampledCacheLine temp = sampled_cache[set][way];
    if (!temp.valid) {
        return;
    }

    if (rdp.count(temp.signature)) {
        rdp[temp.signature] = std::min(rdp[temp.signature] + 1, INF_RD);
    } else {
        rdp[temp.signature] = INF_RD;
    }
    sampled_cache[set][way].valid = false;
}

int mockingjay::temporal_difference(int init, int sample) {
    if (sample > init) {
        int diff = sample - init;
        diff = diff * TEMP_DIFFERENCE;
        diff = std::min(1, diff);
        return std::min(init + diff, INF_RD);
    } else if (sample < init) {
        int diff = init - sample;
        diff = diff * TEMP_DIFFERENCE;
        diff = std::min(1, diff);
        return std::max(init - diff, 0);
    } else {
        return init;
    }
}

int mockingjay::increment_timestamp(int input) {
    input++;
    input = input % (1 << TIMESTAMP_BITS);
    return input;
}

int mockingjay::time_elapsed(int global, int local) {
    if (global >= local) {
        return global - local;
    }
    global = global + (1 << TIMESTAMP_BITS);
    return global - local;
}

void mockingjay::initialize_replacement() {
    etr.resize(NUM_SET, std::vector<int>(NUM_WAY, 0));
    etr_clock.resize(NUM_SET, GRANULARITY);
    current_timestamp.resize(NUM_SET, 0);

    for (int i = 0; i < NUM_SET; i++) {
        etr_clock[i] = GRANULARITY;
        current_timestamp[i] = 0;
    }
    for (uint32_t set = 0; set < NUM_SET; set++) {
        if (is_sampled_set(set)) {
            int modifier = 1 << LOG2_LLC_SET;
            int limit = 1 << LOG2_SAMPLED_CACHE_SETS;
            for (int i = 0; i < limit; i++) {
                sampled_cache[set + modifier*i].resize(SAMPLED_CACHE_WAYS);
                for (int w=0; w<SAMPLED_CACHE_WAYS; w++) {
                    sampled_cache[set + modifier*i][w].valid = false;
                }
            }
        }
    }
}

long mockingjay::find_victim(uint32_t triggering_cpu, uint64_t instr_id, long set, const champsim::cache_block* current_set, champsim::address ip,
                             champsim::address full_addr, access_type type) {
    uint64_t pc_signature = get_pc_signature(ip.to<uint64_t>(), false, type == access_type::PREFETCH, triggering_cpu);
    int incoming_etr = 0;
    if (rdp.count(pc_signature)) {
        incoming_etr = (rdp[pc_signature] > MAX_RD) ? INF_ETR : (rdp[pc_signature] / GRANULARITY);
    }

    //asher
    if (type == access_type::PREFETCH && incoming_etr >= 1) {
        return NUM_WAY; // Bypass the LLC. handle_fill will put it in the Victim Prefetch Buffer!
    }

    for (long way = 0; way < NUM_WAY; way++) {
        if (current_set[way].valid == false) {
            return way;
        }
    }

    int max_etr = 0;
    int victim_way = 0;
    for (long way = 0; way < NUM_WAY; way++) {
        if (std::abs(etr[set][way]) > max_etr ||
                (std::abs(etr[set][way]) == max_etr &&
                        etr[set][way] < 0)) {
            max_etr = std::abs(etr[set][way]);
            victim_way = way;
        }
    }
   
    if (type != access_type::WRITE && rdp.count(pc_signature) &&
            (rdp[pc_signature] > MAX_RD || incoming_etr > max_etr)) {
        return NUM_WAY;
    }
   
    return victim_way;
}

void mockingjay::update_replacement_state(uint32_t triggering_cpu, long set, long way, champsim::address full_addr, champsim::address ip,
                                          champsim::address victim_addr, access_type type, uint8_t hit) {
    if (type == access_type::WRITE) {
        if (!hit) {
            etr[set][way] = -INF_ETR;
        }
        return;
    }

    uint64_t full_addr_val = full_addr.to<uint64_t>();
    uint64_t pc_val = ip.to<uint64_t>();
    uint64_t pc = get_pc_signature(pc_val, hit, type == access_type::PREFETCH, triggering_cpu);

    if (is_sampled_set(set)) {
        uint32_t sampled_cache_index = get_sampled_cache_index(full_addr_val);
        uint64_t sampled_cache_tag = get_sampled_cache_tag(full_addr_val);
        int sampled_cache_way = search_sampled_cache(sampled_cache_tag, sampled_cache_index);

        if (sampled_cache_way > -1) {
            uint64_t last_signature = sampled_cache[sampled_cache_index][sampled_cache_way].signature;
            uint64_t last_timestamp = sampled_cache[sampled_cache_index][sampled_cache_way].timestamp;
            int sample = time_elapsed(current_timestamp[set], last_timestamp);

            if (sample <= INF_RD) {
                if (type == access_type::PREFETCH) {
                    sample = sample * FLEXMIN_PENALTY;
                }
                if (rdp.count(last_signature)) {
                    int init = rdp[last_signature];
                    rdp[last_signature] = temporal_difference(init, sample);
                } else {
                    rdp[last_signature] = sample;
                }

                sampled_cache[sampled_cache_index][sampled_cache_way].valid = false;
            }
        }

        int lru_way = -1;
        int lru_rd = -1;
        for (int w = 0; w < SAMPLED_CACHE_WAYS; w++) {
            if (sampled_cache[sampled_cache_index][w].valid == false) {
                lru_way = w;
                lru_rd = INF_RD + 1;
                continue;
            }

            uint64_t last_timestamp = sampled_cache[sampled_cache_index][w].timestamp;
            int sample = time_elapsed(current_timestamp[set], last_timestamp);
            if (sample > INF_RD) {
                lru_way = w;
                lru_rd = INF_RD + 1;
                detrain(sampled_cache_index, w);
            } else if (sample > lru_rd) {
                lru_way = w;
                lru_rd = sample;
            }
        }
        detrain(sampled_cache_index, lru_way);

        for (int w = 0; w < SAMPLED_CACHE_WAYS; w++) {
            if (sampled_cache[sampled_cache_index][w].valid == false) {
                sampled_cache[sampled_cache_index][w].valid = true;
                sampled_cache[sampled_cache_index][w].signature = pc;
                sampled_cache[sampled_cache_index][w].tag = sampled_cache_tag;
                sampled_cache[sampled_cache_index][w].timestamp = current_timestamp[set];
                break;
            }
        }
        current_timestamp[set] = increment_timestamp(current_timestamp[set]);
    }

    if (etr_clock[set] == GRANULARITY) {
        for (long w = 0; w < NUM_WAY; w++) {
            if (w != way && std::abs(etr[set][w]) < INF_ETR) {
                etr[set][w]--;
            }
        }
        etr_clock[set] = 0;
        std::vector<uint64_t> to_remove;
        for (auto& pair : prefetch_candidates) {
            PrefetchCandidate& cand = pair.second;
            if (cand.set == set) {
                cand.etr--;
                if (cand.etr <= 1) { // Safer to use <= 1
                    // Issue prefetch directly to Victim Prefetch Buffer
                    champsim::address pf_addr(cand.block_addr << LOG2_BLOCK_SIZE);
                    //Asher
                    cache->prefetch_to_vpb(pf_addr);
                    to_remove.push_back(pair.first);
                }
            }
        }
        // Clean up prefetch candidates that were prefetched
        for (uint64_t block_addr : to_remove) {
            prefetch_candidates.erase(block_addr);
        }
    }
    etr_clock[set]++;
   
    if (way < NUM_WAY) {
        if (!rdp.count(pc)) {
            etr[set][way] = 0;
        } else {
            if (rdp[pc] > MAX_RD) {
                etr[set][way] = INF_ETR;
            } else {
                etr[set][way] = rdp[pc] / GRANULARITY;
            }
        }
    }
}

void mockingjay::replacement_cache_fill(uint32_t triggering_cpu, long set, long way, champsim::address full_addr, champsim::address ip,
                                        champsim::address victim_addr, access_type type) {
    uint64_t current_cycle = cache->current_cycle();
    uint64_t incoming_block = full_addr.to<uint64_t>() >> LOG2_BLOCK_SIZE;
    uint64_t evicted_block = victim_addr.to<uint64_t>() >> LOG2_BLOCK_SIZE;

    // Check if incoming block was previously evicted and has now returned
    auto it = eviction_history.find(incoming_block);
    if (it != eviction_history.end()) {
        EvictRecord& rec = it->second;
        uint64_t return_time = current_cycle - rec.cycle_evicted;
       
        eviction_history.erase(it);
    }

    // Check if an eviction is occurring
    if (evicted_block != 0) {
        EvictRecord rec;
        rec.cycle_evicted = current_cycle;
        rec.set = set;
       
        for (long w = 0; w < NUM_WAY; w++) {
            rec.ways_etr.push_back(etr[set][w]);
        }
       
        // Compute incoming_etr as Mockingjay would
        uint64_t pc_sig = get_pc_signature(ip.to<uint64_t>(), false, type == access_type::PREFETCH, triggering_cpu);
        if (!rdp.count(pc_sig)) {
            rec.incoming_etr = 0;
        } else {
            if (rdp[pc_sig] > MAX_RD) {
                rec.incoming_etr = INF_ETR;
            } else {
                rec.incoming_etr = rdp[pc_sig] / GRANULARITY;
            }
        }
       
        eviction_history[evicted_block] = rec;

        int evicted_etr = etr[set][way];

        // Track evicted lines with 0 < ETR < 20 for prefetching
// Track evicted lines with 0 < ETR < 20 for prefetching
//asher
if (evicted_etr > 0 && evicted_etr < 20) {
// if (false && evicted_etr > 0 && evicted_etr < 20) {

    PrefetchCandidate cand;
    cand.block_addr = evicted_block;
    cand.set = set;
    cand.etr = evicted_etr;
    
    // If table size < 256 or we are just updating an already existing candidate block
    if (prefetch_candidates.size() < 256 || prefetch_candidates.count(evicted_block)) {
        prefetch_candidates[evicted_block] = cand;
    } else {
        uint64_t max_etr_block = 0;
        int max_etr = -1;
        
        // Find the line with the largest absolute value ETR in the table
        for (const auto& pair : prefetch_candidates) {
            if (std::abs(pair.second.etr) > max_etr) {
                max_etr = std::abs(pair.second.etr);
                max_etr_block = pair.first;
            }
        }
        
        // Only insert if the new ETR has a smaller absolute value
        if (std::abs(evicted_etr) < max_etr) {
            prefetch_candidates.erase(max_etr_block);
            prefetch_candidates[evicted_block] = cand;
        }
    }
}

    }

    // Pass to update_replacement_state
    update_replacement_state(triggering_cpu, set, way, full_addr, ip, victim_addr, type, 0);
}

void mockingjay::replacement_final_stats() {
    for (const auto& pair : eviction_history) {
        uint64_t evicted_block = pair.first;
        const EvictRecord& rec = pair.second;
    }
    eviction_history.clear();
    prefetch_candidates.clear();
}