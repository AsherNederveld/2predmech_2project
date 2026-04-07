#ifndef REPLACEMENT_MOCKINGJAY_H
#define REPLACEMENT_MOCKINGJAY_H
#include <unordered_set> // Add this at the top

#include <vector>
#include <unordered_map>
#include <cmath>
#include <cstdint>
#include <iostream>


#include "cache.h"
#include "modules.h"


class mockingjay : public champsim::modules::replacement
{
  long NUM_SET;
  long NUM_WAY;
  long LOG2_BLOCK_SIZE;
  long LOG2_LLC_SET;
  long LOG2_LLC_SIZE;


  long LOG2_SAMPLED_SETS;


  // Constants
  int HISTORY = 8;
  int GRANULARITY = 8;
  int INF_RD;
  int INF_ETR;
  int MAX_RD;


  int SAMPLED_CACHE_WAYS = 5;
  int LOG2_SAMPLED_CACHE_SETS = 4;
  int SAMPLED_CACHE_TAG_BITS;
  int PC_SIGNATURE_BITS;
  int TIMESTAMP_BITS = 8;

  //int MAX_PREFETCH_CANDIDATES = 10000000000000;  // 5x the VPB size (VPB is 16)

  double TEMP_DIFFERENCE = 1.0/16.0;
  double FLEXMIN_PENALTY = 2.0;


  // Data
  std::vector<std::vector<int>> etr;
  std::vector<int> etr_clock;
  std::unordered_map<uint64_t, int> rdp;
  std::vector<int> current_timestamp;


  struct SampledCacheLine {
    bool valid;
    uint64_t tag;
    uint64_t signature;
    int timestamp;
  };
  std::unordered_map<uint32_t, std::vector<SampledCacheLine>> sampled_cache;


  // Tracking structure for evictions
  struct EvictRecord {
      uint64_t cycle_evicted;
      long set;
      std::vector<int> ways_etr;
      int incoming_etr;
  };
  std::unordered_map<uint64_t, EvictRecord> eviction_history;

  struct PrefetchCandidate {
      uint64_t block_addr;
      long set;
      int etr;
  };
  std::unordered_map<uint64_t, PrefetchCandidate> prefetch_candidates;

  // Helpers
  bool is_sampled_set(int set);
  uint64_t CRC_HASH(uint64_t _blockAddress);
  uint64_t get_pc_signature(uint64_t pc, bool hit, bool prefetch, uint32_t core);
  uint32_t get_sampled_cache_index(uint64_t full_addr);
  uint64_t get_sampled_cache_tag(uint64_t x);
  int search_sampled_cache(uint64_t blockAddress, uint32_t set);
  void detrain(uint32_t set, int way);
  int temporal_difference(int init, int sample);
  int increment_timestamp(int input);
  int time_elapsed(int global, int local);


public:
  CACHE* cache;
  explicit mockingjay(CACHE* cache);


  void initialize_replacement();
  long find_victim(uint32_t triggering_cpu, uint64_t instr_id, long set, const champsim::cache_block* current_set, champsim::address ip,
                   champsim::address full_addr, access_type type);
  void update_replacement_state(uint32_t triggering_cpu, long set, long way, champsim::address full_addr, champsim::address ip, champsim::address victim_addr,
                                access_type type, uint8_t hit);
  void replacement_cache_fill(uint32_t triggering_cpu, long set, long way, champsim::address full_addr, champsim::address ip, champsim::address victim_addr,
                              access_type type);
  void replacement_final_stats();
};


#endif
