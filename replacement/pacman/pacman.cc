#include "pacman.h"
#include <algorithm>
#include <cassert>
#include <random>

pacman::pacman(CACHE* cache) 
    : replacement(cache), 
      NUM_SET(cache->NUM_SET), 
      NUM_WAY(cache->NUM_WAY), 
      rrpv(static_cast<std::size_t>(NUM_SET * NUM_WAY), maxRRPV) 
{
  // Initialize SDM counters to mid-point [cite: 328]
  cnt_SRRIP_PH.resize(NUM_CPUS, champsim::msl::fwcounter<SDM_WIDTH>(1 << (SDM_WIDTH - 1)));
  cnt_SRRIP_PHM.resize(NUM_CPUS, champsim::msl::fwcounter<SDM_WIDTH>(1 << (SDM_WIDTH - 1)));
  cnt_BRRIP_PH.resize(NUM_CPUS, champsim::msl::fwcounter<SDM_WIDTH>(1 << (SDM_WIDTH - 1)));
}

unsigned& pacman::get_rrpv(long set, long way) { 
  return rrpv.at(static_cast<std::size_t>(set * NUM_WAY + way)); 
}

pacman::set_type pacman::get_set_type(long set) {
  // Use ChampSim's sampling infrastructure (e.g., 32 sets per monitor) [cite: 352]
  switch (get_set_sample_category(set)) {
    case 0: return set_type::leader_SRRIP_PH;
    case 1: return set_type::leader_SRRIP_PHM;
    case 2: return set_type::leader_BRRIP_PH;
    default: return set_type::follower;
  }
}

pacman::pacman_policy pacman::get_best_policy(uint32_t cpu) {
  // Find policy with minimum counter value [cite: 316, 330]
  unsigned v1 = cnt_SRRIP_PH[cpu].value();
  unsigned v2 = cnt_SRRIP_PHM[cpu].value();
  unsigned v3 = cnt_BRRIP_PH[cpu].value();

  if (v1 <= v2 && v1 <= v3) return pacman_policy::SRRIP_PH;
  if (v2 <= v1 && v2 <= v3) return pacman_policy::SRRIP_PHM;
  return pacman_policy::BRRIP_PH;
}

void pacman::apply_insertion(long set, long way, pacman_policy policy, access_type type) {
  bool is_prefetch = (type == access_type::PREFETCH);

  // PACMan-M logic: Prefetch misses always get RRPV=3 [cite: 243, 272]
  if (is_prefetch && (policy == pacman_policy::SRRIP_PHM)) {
    get_rrpv(set, way) = maxRRPV;
    return;
  }

  // Standard DRRIP insertion [cite: 267]
  if (policy == pacman_policy::BRRIP_PH) {
    // 95% RRPV=3, 5% RRPV=2 [cite: 239]
    static thread_local std::mt19937_64 gen(42);
    std::uniform_int_distribution<> dis(0, 99);
    get_rrpv(set, way) = (dis(gen) < 5) ? (maxRRPV - 1) : maxRRPV;
  } else {
    get_rrpv(set, way) = maxRRPV - 1; // SRRIP insertion
  }
}

void pacman::apply_promotion(long set, long way, pacman_policy policy, access_type type) {
  // PACMan-H logic: No update on prefetch hit [cite: 249, 273]
  if (type == access_type::PREFETCH) {
    return; 
  }
  // Demand hits promote to MRU (0) [cite: 267, 273]
  get_rrpv(set, way) = 0;
}

void pacman::update_replacement_state(uint32_t cpu, long set, long way, champsim::address full_addr, champsim::address ip,
                                      champsim::address victim_addr, access_type type, uint8_t hit) {
  if (type == access_type::WRITE) return; // Skip writebacks [cite: 331]

  if (hit) {
    apply_promotion(set, way, get_best_policy(cpu), type);
  }
}

void pacman::replacement_cache_fill(uint32_t cpu, long set, long way, champsim::address full_addr, champsim::address ip, 
                                   champsim::address victim_addr, access_type type) {
  if (type == access_type::WRITE) return;

  // Update SDM counters on demand misses [cite: 328, 331]
  if (type != access_type::PREFETCH) {
    switch (get_set_type(set)) {
      case set_type::leader_SRRIP_PH:
        cnt_SRRIP_PH[cpu] += 2;
        cnt_SRRIP_PHM[cpu]--;
        cnt_BRRIP_PH[cpu]--;
        break;
      case set_type::leader_SRRIP_PHM:
        cnt_SRRIP_PH[cpu]--;
        cnt_SRRIP_PHM[cpu] += 2;
        cnt_BRRIP_PH[cpu]--;
        break;
      case set_type::leader_BRRIP_PH:
        cnt_SRRIP_PH[cpu]--;
        cnt_SRRIP_PHM[cpu]--;
        cnt_BRRIP_PH[cpu] += 2;
        break;
      default: break;
    }
  }

  // Determine and apply insertion policy
  pacman_policy current_policy;
  switch (get_set_type(set)) {
    case set_type::leader_SRRIP_PH:  current_policy = pacman_policy::SRRIP_PH; break;
    case set_type::leader_SRRIP_PHM: current_policy = pacman_policy::SRRIP_PHM; break;
    case set_type::leader_BRRIP_PH:  current_policy = pacman_policy::BRRIP_PH; break;
    default:                         current_policy = get_best_policy(cpu); break;
  }

  apply_insertion(set, way, current_policy, type);
}

long pacman::find_victim(uint32_t triggering_cpu, uint64_t instr_id, long set, const champsim::cache_block* current_set, 
                         champsim::address ip, champsim::address full_addr, access_type type) {
  // Identical to DRRIP: Find block with maxRRPV [cite: 268]
  auto begin = std::next(std::begin(rrpv), set * NUM_WAY);
  auto end = std::next(begin, NUM_WAY);

  while (true) {
    auto victim = std::find(begin, end, maxRRPV);
    if (victim != end) {
      return std::distance(begin, victim);
    }
    // If no victim found, increment all RRPVs [cite: 268]
    for (auto it = begin; it != end; ++it) {
      (*it)++;
    }
  }
}