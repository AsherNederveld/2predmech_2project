#ifndef REPLACEMENT_PACMAN_H
#define REPLACEMENT_PACMAN_H

#include <vector>
#include "cache.h"
#include "modules.h"
#include "msl/fwcounter.h"

// PACMan-DYN building on DRRIP [cite: 48, 260]
struct pacman : public champsim::modules::replacement {
private:
  unsigned& get_rrpv(long set, long way);

public:
  static constexpr unsigned maxRRPV = 3; 
  static constexpr unsigned PSEL_WIDTH = 10; 
  static constexpr unsigned SDM_WIDTH = 10; // Saturating counter for policy selection [cite: 327]

  // PACMan-DYN monitors three policy combinations [cite: 322, 323, 324]
  enum class pacman_policy {
    SRRIP_PH,   // SRRIP + PACMan-H
    SRRIP_PHM,  // SRRIP + PACMan-HM
    BRRIP_PH    // BRRIP + PACMan-H
  };

  enum class set_type {
    follower,
    leader_SRRIP_PH,
    leader_SRRIP_PHM,
    leader_BRRIP_PH
  };

  long NUM_SET, NUM_WAY;
  std::vector<unsigned> rrpv;
  
  // Per-CPU counters for DRRIP and PACMan selection [cite: 327, 328]
  std::vector<champsim::msl::fwcounter<SDM_WIDTH>> cnt_SRRIP_PH;
  std::vector<champsim::msl::fwcounter<SDM_WIDTH>> cnt_SRRIP_PHM;
  std::vector<champsim::msl::fwcounter<SDM_WIDTH>> cnt_BRRIP_PH;

  pacman(CACHE* cache);

  long find_victim(uint32_t triggering_cpu, uint64_t instr_id, long set, const champsim::cache_block* current_set, champsim::address ip,
                   champsim::address full_addr, access_type type);
  
  void replacement_cache_fill(uint32_t triggering_cpu, long set, long way, champsim::address full_addr, champsim::address ip, champsim::address victim_addr,
                              access_type type);
  
  void update_replacement_state(uint32_t triggering_cpu, long set, long way, champsim::address full_addr, champsim::address ip, champsim::address victim_addr,
                                access_type type, uint8_t hit);

  // Set Dueling logic [cite: 280, 318]
  set_type get_set_type(long set);
  pacman_policy get_best_policy(uint32_t cpu);
  
  // Internal RRPV updaters [cite: 267, 272]
  void apply_insertion(long set, long way, pacman_policy policy, access_type type);
  void apply_promotion(long set, long way, pacman_policy policy, access_type type);
};

#endif