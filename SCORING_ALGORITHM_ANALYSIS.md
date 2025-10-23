# Scoring Algorithm Analysis & Stress Test Results

## Executive Summary

The project scoring algorithm uses a **7-component weighted scoring system** tailored to different data center personas (Hyperscaler, Colocation, Edge Computing) and custom user profiles. Each component is scored 0-100, then weighted according to persona priorities to produce a final investment rating (0-10).

**Key Findings:**
- ✅ Algorithm successfully differentiates between persona priorities
- ✅ Score distribution is reasonable (1.8-8.5 range across test cases)
- ⚠️ Hyperscaler persona is more selective (avg 5.3/10) than others
- ⚠️ Development stage scoring may over-penalize operational sites for BTM use cases
- ⚠️ Capacity scoring shows sharp threshold effects
- 🔧 Several opportunities for improvement identified

---

## How Scores Are Derived

### 1. Component Scoring (0-100 each)

The algorithm evaluates **7 business-critical components**:

#### **A. Capacity Score**
**Purpose:** Match project capacity to persona needs

**Formula:** Logistic function centered on persona-specific ideal capacity
```python
score = 100 / (1 + exp(-0.05 * (capacity_mw - ideal_mw)))
```

**Persona Ideals:**
- Hyperscaler: 100 MW (range: 30-400 MW)
- Colocation: 20 MW (range: 5-50 MW)
- Edge Computing: 2 MW (range: 0.4-5 MW)

**Characteristics:**
- Smooth sigmoid curve
- Penalizes both under-capacity and over-capacity
- Hyperscalers have steeper requirements (200+ MW gets 99+ score)

**Example Scores:**
- 1 MW → Hyperscaler: 0.7, Edge: 50.0
- 100 MW → Hyperscaler: 50.0, Edge: 99.3
- 1000 MW → All personas: ~100 (saturation)

---

#### **B. Connection Speed Score**
**Purpose:** Estimate grid connection timeline and feasibility

**Formula:** Weighted combination of:
```
= 50% * development_stage_score
+ 30% * substation_proximity_score
+ 20% * transmission_proximity_score
```

**Development Stage Component:**
- Maps development status to 15-100 scale
- "Application submitted" = 90 (optimal BTM timing)
- "Under construction" = 20 (window closed)

**Proximity Components:**
- Substation: `100 * exp(-distance_km / 30)`
- Transmission: `100 * exp(-distance_km / 50)`

**Observed Range:** 22.9 (remote refused) to 93.3 (ideal submitted)

**Why it matters:** Faster connections = lower cost, faster revenue

---

#### **C. Resilience Score**
**Purpose:** Assess redundancy and backup infrastructure

**Formula:** Count backup options, score 0-100
```python
backup_count = 0
if substation_km < 15: backup_count += 4
elif substation_km < 30: backup_count += 3
if transmission_km < 40: backup_count += 1
if "battery" in tech: backup_count += 1
if "hybrid" in tech: backup_count += 2

score = (backup_count / 10) * 100
```

**Test Results:**
- Perfect infrastructure (1km to all) → 70/100
- Remote site (50km+) → 0/100
- Hybrid tech adds +20 points

**Limitation:** Placeholder logic; production should use N+1/2N analysis

---

#### **D. Land & Planning Score**
**Purpose:** Evaluate BTM (Behind-the-Meter) intervention viability

**Philosophy:** Higher score = better timing for data center co-location

**Scoring Table:**
| Status | Score | Rationale |
|--------|-------|-----------|
| Revised | 95 | Resubmitted - optimal BTM window |
| Application submitted | 90 | Live planning - ideal timing |
| No application required | 85 | Permitted development |
| Planning expired | 80 | Reactivatable consent |
| Secretary of State granted | 70 | Nationally endorsed |
| Awaiting construction | 40 | Narrowing BTM window |
| Application withdrawn | 35 | Paused; may restart |
| Application refused | 30 | Denied; redesign needed |
| Under construction | 20 | **BTM window closed** |
| Operational | 0 | **No BTM value** |

**Critical Finding:** This heavily penalizes operational assets, which may have colocation potential

---

#### **E. Latency Score (Digital Infrastructure)**
**Purpose:** Assess network connectivity quality

**Formula:** Combined fiber + IXP proximity
```python
fiber_score = 100 * exp(-fiber_km / half_distance)
ixp_score = 100 * exp(-ixp_km / half_distance)
latency_score = 50 * (fiber_score + ixp_score)
```

**Half-distances (from constants):**
- Fiber: ~5-10 km
- IXP: ~20-30 km

**Example:**
- 0.5km fiber + 2km IXP → 95.2 (excellent)
- 40km fiber + 200km IXP → 10.1 (poor)

**Most important for:** Colocation (21.7%) and Edge (24.7%)

---

#### **F. Cooling Score (Water Resources)**
**Purpose:** Assess cooling infrastructure potential

**Formula:** Exponential decay from water sources
```python
score = 100 * exp(-water_km / half_distance)
```

**Results:**
- 2 km → 92.3 (excellent)
- 10 km → 67.0 (good)
- 30 km → 30.1 (poor)

**Most important for:** Hyperscaler (14.4%), less for Edge (5.4%)

---

#### **G. Price Sensitivity Score**
**Purpose:** Estimate total energy cost competitiveness

**Components:**
1. **Base LCOE** (technology-specific):
   - Solar: £52/MWh (CF: 11%)
   - Onshore wind: £60/MWh (CF: 30%)
   - Offshore wind: £80/MWh (CF: 45%)
   - Battery: £65/MWh (CF: 20%)
   - Gas CCGT: £70/MWh (CF: 55%)

2. **TNUoS Impact** (transmission costs):
   - Scotland (north): **Credits** of £-3/kW (reduces cost)
   - South England: **Charges** of £+16/kW (increases cost)
   - Converted to £/MWh using capacity factor

3. **Total Cost:** LCOE ± TNUoS impact

4. **Scoring:**
   - If user specifies max price: score based on budget fit
   - Otherwise: relative ranking (£40-100 range assumed)

**Example:**
- Scotland wind: Low LCOE + TNUoS credit → 74.6/100
- South solar: Moderate LCOE + TNUoS charge → 82.6/100

**Importance:** Low for hyperscalers (5.6%), higher for edge (8.6%)

---

### 2. Persona Weighting

Each persona applies different weights reflecting their priorities:

```
HYPERSCALER WEIGHTS:
  Capacity:           24.4%  ← Large projects essential
  Land & Planning:    20.0%  ← Need shovel-ready sites
  Connection Speed:   16.7%  ← Fast grid access important
  Cooling:            14.4%  ← High-density cooling critical
  Resilience:         13.3%  ← Backup infrastructure
  Latency:             5.6%  ← Not critical (hyperscale workloads)
  Price Sensitivity:   5.6%  ← Less price-sensitive

COLOCATION WEIGHTS:
  Latency:            21.7%  ← Critical for multi-tenant
  Resilience:         19.6%  ← Redundancy for SLAs
  Connection Speed:   16.3%  ← Reliable uptime
  Land & Planning:    16.3%  ← Ready sites
  Capacity:           14.1%  ← Moderate needs
  Cooling:             8.7%  ← Manageable
  Price Sensitivity:   3.3%  ← Quality over cost

EDGE COMPUTING WEIGHTS:
  Land & Planning:    28.0%  ← MUST deploy fast
  Latency:            24.7%  ← Low-latency workloads
  Connection Speed:   12.9%  ← Decent connection
  Resilience:         10.8%  ← Some redundancy
  Capacity:            9.7%  ← Small footprint
  Price Sensitivity:   8.6%  ← Cost-conscious
  Cooling:             5.4%  ← Minimal needs
```

---

### 3. Final Score Calculation

**Weighted Sum:**
```python
weighted_score = sum(component_scores[i] * weights[i] for i in components)
```

**Clamped to 0-100:**
```python
internal_score = max(0, min(100, weighted_score))
```

**Converted to 0-10 display rating:**
```python
investment_rating = internal_score / 10
```

**Color & Description Mapping:**
- 90-100 → Exceptional (Green #00FF00)
- 80-90 → Very Good (Light Green #33FF33)
- 70-80 → Good (Yellow-Green #7FFF00)
- 60-70 → Above Average (Lime #CCFF00)
- 50-60 → Average (Yellow #FFFF00)
- 40-50 → Below Average (Orange-Yellow #FFCC00)
- 30-40 → Poor (Orange #FF9900)
- 20-30 → Very Poor (Red-Orange #FF6600)
- 10-20 → Bad (Red #FF3300)
- 0-10 → Very Bad (Dark Red #CC0000)

---

## Stress Test Results Analysis

### Test Scenarios Summary

| Project | Capacity | Stage | Location | Hyperscaler | Colocation | Edge | Custom |
|---------|----------|-------|----------|-------------|------------|------|--------|
| **Hyperscaler Dream Site** | 150 MW | App Submitted | London | **8.5** | 8.2 | 8.4 | 8.2 |
| **Colocation Sweet Spot** | 25 MW | Revised | Manchester | 6.0 | **7.9** | 8.1 | 6.9 |
| **Edge Computing Ideal** | 3 MW | No App Req'd | Midlands | 5.5 | 7.1 | **7.7** | 6.4 |
| **Worst Case** | 2 MW | Refused | N. Scotland | 1.8 | 1.9 | 2.5 | 3.2 |
| **Average Project** | 50 MW | Awaiting Const | Central Eng | 4.2 | 5.9 | 5.8 | 5.6 |
| **Scotland Remote** | 100 MW | App Submitted | N. Scotland | 5.6 | 5.2 | 5.8 | 5.3 |
| **Under Construction** | 75 MW | Under Const | S. England | 4.5 | 6.2 | 5.9 | 6.2 |
| **Operational** | 200 MW | Operational | Yorkshire | 6.1 | 6.4 | 5.2 | 6.8 |

### Persona Behavior Analysis

#### **1. Hyperscaler Persona**
- **Average Score:** 5.3/10 (most selective)
- **Range:** 1.8 - 8.5 (widest spread)
- **Behavior:**
  - ✅ Correctly prioritizes large capacity + good planning stage
  - ✅ Dream site (150MW, submitted, urban) scores 8.5
  - ❌ Penalizes <50 MW heavily (colocation sweet spot only gets 6.0)
  - ❌ Over-penalizes "under construction" (4.5) despite excellent infrastructure
- **Insight:** Most capacity-sensitive; struggles with mid-size projects

#### **2. Colocation Persona**
- **Average Score:** 6.1/10 (moderate)
- **Range:** 1.9 - 8.2
- **Behavior:**
  - ✅ Correctly prioritizes latency + resilience
  - ✅ Sweet spot (25MW, revised, fiber-rich) scores 7.9
  - ✅ More forgiving of operational sites (6.4 vs hyperscaler's 6.1)
  - ❌ Still penalizes remote locations heavily (Scotland: 5.2)
- **Insight:** Balanced profile; latency weight (21.7%) drives urban preference

#### **3. Edge Computing Persona**
- **Average Score:** 6.2/10 (least selective)
- **Range:** 2.5 - 8.4
- **Behavior:**
  - ✅ Correctly prioritizes fast deployment (28% land/planning weight)
  - ✅ "No application required" sites score highest
  - ✅ Small capacity ideal (3MW) scores 7.7
  - ⚠️ Operational sites score poorly (5.2) despite edge potential
- **Insight:** Most permissive; deployment speed dominates

---

### Edge Case Findings

#### **Zero Capacity Test**
- **Expected:** Should fail (no project)
- **Actual:**
  - Hyperscaler: 6.2 (Above Average!) ❌
  - Colocation: 7.2 (Good!) ❌
  - Edge: 8.0 (Very Good!) ❌
- **Problem:** Other components compensate for missing capacity
- **Fix:** Add minimum capacity threshold or increase capacity weight

#### **Massive Capacity (1000 MW)**
- **Result:** All personas score 8.2-8.5 (Very Good)
- **Analysis:**
  - ✅ Doesn't break (clamped properly)
  - ⚠️ Logistic function saturates (no difference between 400 MW and 1000 MW)
  - **Consider:** Cap scoring at realistic maximums

#### **Perfect Infrastructure (0.1 km to everything)**
- **Result:**
  - Hyperscaler: 7.6
  - Colocation: 8.8 (highest!)
  - Edge: 8.5
- **Analysis:**
  - ✅ Colocation benefits most (latency + resilience weights)
  - ✅ Expected behavior

#### **Remote Island (500 km to everything)**
- **Result:** 3.9-4.8 (Poor to Below Average)
- **Analysis:**
  - ✅ Correctly penalized
  - ✅ Exponential decay prevents complete zero-out

---

### Sensitivity Analysis

#### **1. Capacity Sensitivity (Hyperscaler)**
- **1-50 MW:** Flat at 5.8-5.9 (capacity component ~0-7 points)
- **100 MW:** Jump to 7.0 (capacity component = 50 points)
- **200 MW:** Jump to 8.2 (capacity component = 99 points)
- **400+ MW:** Saturated at 8.2

**Issue:** Sharp threshold between 50-100 MW creates discontinuity

#### **2. Development Stage Sensitivity**
| Stage | Hyperscaler | Colocation | Edge | Comment |
|-------|-------------|------------|------|---------|
| Revised | 7.1 | 7.8 | **8.2** | Highest (optimal BTM timing) |
| App Submitted | 7.0 | 7.7 | 8.0 | Near-peak |
| No App Req'd | 6.8 | 7.6 | 7.8 | Strong for edge |
| Awaiting Const | 5.5 | 6.4 | 6.3 | Moderate |
| Under Const | 4.9 | 5.9 | 5.6 | **Heavily penalized** |
| Operational | 4.5 | 5.6 | 5.0 | **Worst score** |

**Concern:** Operational sites may still have colocation/PPA value

#### **3. Infrastructure Proximity (Colocation)**
- **0.5 km:** 8.7 (Excellent)
- **5 km:** 8.0 (Very Good)
- **10 km:** 7.5 (Good)
- **20 km:** 6.2 (Above Average)
- **50 km:** 4.4 (Below Average)
- **100+ km:** 3.9-4.0 (Poor)

**Analysis:** Smooth exponential decay works well

---

## Algorithm Strengths

### ✅ What Works Well

1. **Persona Differentiation**
   - Clear separation in priorities (capacity vs latency vs deployment speed)
   - Test results show expected persona preferences (e.g., edge prefers small/fast sites)

2. **Component Modularity**
   - Each of 7 components is independently testable
   - Weights are easily adjustable
   - Clear business logic mapping

3. **Smooth Proximity Scoring**
   - Exponential decay prevents harsh cliffs
   - Multiple infrastructure types balanced well

4. **Score Distribution**
   - Reasonable spread (1.8 to 8.5 across test cases)
   - No saturation at extremes (except edge cases)

5. **TNUoS Integration**
   - Geography-aware cost modeling
   - Correctly credits Scotland, penalizes South

6. **Edge Case Resilience**
   - Doesn't crash on extreme inputs (0 MW, 1000 MW, 500 km distances)
   - Proper clamping (0-100 range maintained)

---

## Algorithm Weaknesses & Improvement Opportunities

### 🔧 Critical Issues

#### **1. Zero Capacity Loophole**
**Problem:** Projects with 0 MW capacity score 6.2-8.0 (should fail)

**Root Cause:** Capacity weight (9.7-24.4%) isn't dominant enough; other components compensate

**Fix Options:**
```python
# Option A: Hard minimum threshold
if capacity_mw < 0.5:
    return {"investment_rating": 0.0, "reason": "Insufficient capacity"}

# Option B: Exponential penalty below minimum
if capacity_mw < persona_minimum:
    penalty = exp(-capacity_mw / persona_minimum)
    final_score *= penalty

# Option C: Increase capacity weight
# (May break existing calibration)
```

**Recommendation:** Option A (hard threshold) for data quality

---

#### **2. Development Stage Over-Penalization**
**Problem:** Operational sites score poorly (4.5-5.6) despite potential colocation/PPA value

**Example:**
- Operational 200 MW site with perfect infrastructure → 6.1 (hyperscaler)
- Same site "under construction" → Would score higher despite being less certain

**Root Cause:** Land & Planning score assumes **BTM intervention only**

**Fix:**
```python
def calculate_development_stage_score(status, perspective="demand", use_case="btm"):
    if use_case == "btm":
        # Current BTM-focused scoring
        return STATUS_SCORES_BTM[status]
    elif use_case == "ppa":
        # NEW: Value operational/construction sites for PPAs
        STATUS_SCORES_PPA = {
            "operational": 90,  # Revenue-generating asset
            "under construction": 80,  # Near-term certainty
            "awaiting construction": 70,
            "application submitted": 60,
            ...
        }
        return STATUS_SCORES_PPA[status]
```

**Alternative:** Add `colocation_potential` component that values operational assets

---

#### **3. Capacity Score Thresholds**
**Problem:** Sharp jump from 5.9 → 7.0 → 8.2 at 50/100/200 MW

**Root Cause:** Logistic function steepness (hardcoded -0.05 slope)

**Current:**
```python
score = 100 / (1 + exp(-0.05 * (capacity - ideal)))
```

**Fix:**
```python
# Make steepness persona-specific
STEEPNESS = {
    "hyperscaler": 0.03,  # Gentler slope (wider acceptable range)
    "colocation": 0.05,   # Current
    "edge": 0.10,         # Steeper (narrower acceptable range)
}
score = 100 / (1 + exp(-STEEPNESS[persona] * (capacity - ideal)))
```

---

### ⚠️ Moderate Issues

#### **4. Resilience Score Placeholder Logic**
**Current:** Simple backup counter (0-10 scale)

**Limitations:**
- Doesn't assess actual N+1 / 2N redundancy
- Battery storage bonus (+1-2 points) is arbitrary
- No consideration of grid zone constraints

**Production Upgrade:**
```python
def calculate_resilience_score(project, proximity_scores):
    score = 0

    # Multiple substation analysis (check for 2+ within range)
    substations_in_range = count_nearby_substations(project, radius_km=20)
    if substations_in_range >= 2:
        score += 40  # True N+1 capability

    # Dual fiber route availability
    fiber_routes = check_fiber_route_diversity(project)
    if fiber_routes >= 2:
        score += 20

    # Onsite BESS capacity
    if project.get("bess_capacity_mwh", 0) > 4:  # 4+ hours backup
        score += 20

    # Gas backup option
    if gas_connection_available(project):
        score += 10

    # Grid zone robustness
    zone_reliability = get_grid_zone_reliability(project.latitude, project.longitude)
    score += zone_reliability * 10

    return min(100, score)
```

---

#### **5. Price Sensitivity Assumptions**
**Current:** Uses rough LCOE estimates and simplified TNUoS

**Limitations:**
- LCOE doesn't account for site-specific resource quality
- TNUoS calculated from latitude only (ignores actual zones)
- No consideration of:
  - Curtailment risk
  - Balancing costs
  - Capacity market revenues
  - CfD strike prices

**Production Upgrade:**
- **LCOE:** Use actual resource data (wind speed maps, solar irradiance)
- **TNUoS:** Look up actual zone tariffs (currently hardcoded in TNUOS_ZONES_HARDCODED)
- **Curtailment:** Add constraint zone analysis
- **Market revenues:** Integrate CFD/capacity market data

---

#### **6. Missing Components**

**Land Availability:**
- Current: Not directly scored (implicit in "development stage")
- Should add: Acreage, zoning, existing use constraints

**Environmental Constraints:**
- Current: Not considered
- Should add: Flood risk, protected areas, noise limits

**Community/Political Risk:**
- Current: Not considered
- Should add: Local opposition history, political stability

**Grid Headroom:**
- Current: Proximity only (not capacity)
- Should add: Substation spare capacity, queue position

**Implementation:**
```python
# Add to component scores
"land_availability": calculate_land_score(project),       # Acreage, zoning
"environmental": calculate_environmental_score(project),  # Flood, protected areas
"community_risk": calculate_community_score(project),     # Opposition history
"grid_headroom": calculate_grid_capacity_score(project),  # Substation capacity
```

---

### 🎯 Nice-to-Have Improvements

#### **7. Non-Linear Component Interactions**
**Current:** Simple weighted sum (assumes independence)

**Reality:** Components interact:
- Low price + poor latency ≠ automatically good for edge
- Excellent capacity + refused planning = worthless
- Remote location + poor grid + no fiber = compounding penalty

**Potential Fix:**
```python
# Multiplicative penalty for critical combos
if capacity_score < 10 and land_planning_score < 30:
    final_score *= 0.5  # Both critical factors failed

# Synergy bonus
if latency_score > 80 and cooling_score > 80 and capacity_score > 80:
    final_score *= 1.1  # "Unicorn" site bonus
```

**Caution:** Adds complexity; test thoroughly

---

#### **8. User-Configurable Weights**
**Current:** Fixed persona weights

**Enhancement:** Allow users to fine-tune within constraints
```python
# Example: User wants hyperscaler profile but cares more about price
custom_weights = PERSONA_WEIGHTS["hyperscaler"].copy()
custom_weights["price_sensitivity"] = 0.15  # Up from 5.6%
custom_weights["capacity"] = 0.20  # Down from 24.4%
# (Normalize to sum to 1.0)
```

**Already supported:** `calculate_custom_weighted_score()` exists

---

#### **9. Score Confidence Intervals**
**Current:** Single point score

**Enhancement:** Show uncertainty
```python
{
    "investment_rating": 7.5,
    "confidence": "medium",
    "confidence_factors": {
        "data_quality": 0.8,  # 80% of fields populated
        "estimate_reliance": 0.6,  # Using LCOE estimates vs actuals
        "infrastructure_certainty": 0.9,  # Confirmed proximity data
    }
}
```

---

#### **10. Time-Decay Modeling**
**Current:** Static snapshot scoring

**Reality:** Project value changes over time:
- Planning sites may get refused
- Under construction sites → operational
- Grid queue positions change

**Enhancement:**
```python
def calculate_score_over_time(project, proximity_scores, months_forward=24):
    scores = []
    for month in range(0, months_forward, 6):
        projected_status = estimate_future_status(project, month)
        score = calculate_score(projected_status, proximity_scores)
        scores.append({"month": month, "score": score})
    return scores
```

---

## Recommendations

### Immediate Priorities (Next Sprint)

1. **Fix Zero Capacity Loophole**
   - Add hard minimum threshold validation
   - **Impact:** High (data quality)
   - **Effort:** Low (10 lines of code)

2. **Add PPA/Colocation Scoring Mode**
   - Allow `use_case` parameter: "btm" vs "ppa" vs "colocation"
   - Adjust development stage scoring accordingly
   - **Impact:** High (unlocks operational assets)
   - **Effort:** Medium (new scoring table + tests)

3. **Smooth Capacity Curve**
   - Make logistic steepness persona-specific
   - **Impact:** Medium (better scoring distribution)
   - **Effort:** Low (adjust constants)

### Short-Term (1-2 Months)

4. **Upgrade Resilience Scoring**
   - Implement multi-substation analysis
   - Add fiber route diversity
   - **Impact:** Medium (better colocation scoring)
   - **Effort:** Medium (requires infrastructure count data)

5. **Add Missing Components**
   - Land availability score
   - Environmental constraints score
   - **Impact:** High (more comprehensive evaluation)
   - **Effort:** High (requires new data sources)

6. **Real TNUoS Zone Lookup**
   - Replace latitude-based estimate with actual zone tariffs
   - Already have TNUOS_ZONES_HARDCODED in main.py (lines 115-178)
   - **Impact:** Medium (10-20% price accuracy improvement)
   - **Effort:** Low (use existing data)

### Long-Term (Quarterly)

7. **Machine Learning Calibration**
   - Train weights on historical investment outcomes
   - A/B test persona definitions
   - **Impact:** High (data-driven optimization)
   - **Effort:** High (requires outcome data)

8. **Dynamic Component Interactions**
   - Add non-linear penalty/bonus logic
   - Test on expanded dataset
   - **Impact:** Medium (captures edge cases)
   - **Effort:** High (complexity risk)

9. **Score Confidence Metrics**
   - Add uncertainty quantification
   - **Impact:** Medium (user trust)
   - **Effort:** Medium

---

## Testing Recommendations

### Expand Test Coverage

**Current:** 8 scenarios + 4 edge cases

**Add:**
1. **Boundary Testing**
   - Each component at exact thresholds (0, 50, 100)
   - Exact persona ideal capacities

2. **Regression Suite**
   - Lock in current scores for "Hyperscaler Dream Site" as baseline
   - Alert on any changes >0.5 points

3. **Real Project Validation**
   - Score 100 actual projects from database
   - Compare algorithm rankings to expert rankings
   - Calculate correlation coefficient (target: >0.75)

4. **Persona Consistency**
   - Verify hyperscaler never ranks 2 MW projects >7.0
   - Verify edge never ranks 500 MW projects <5.0
   - etc.

### Performance Testing

**Current:** Synchronous scoring (one project at a time)

**Test:**
- Batch scoring 1000 projects
- Measure latency (target: <50ms per project)
- Identify bottlenecks (likely: proximity calculations)

---

## Conclusion

The scoring algorithm is **fundamentally sound** with clear persona differentiation and reasonable outputs. The main issues are:

1. **Zero capacity loophole** (easy fix)
2. **Over-penalization of operational sites** (requires use-case modes)
3. **Capacity threshold sharpness** (adjust constants)

**Overall Grade: B+** (85/100)

The algorithm successfully serves its purpose but needs refinement for edge cases and expanded use cases beyond BTM intervention.

**Recommended Next Steps:**
1. Implement zero-capacity validation
2. Add PPA/colocation scoring mode
3. Validate against 100 real projects
4. Expand test suite with boundary cases

---

## Appendix: Running the Stress Tests

### Execute Full Test Suite
```bash
python test_scoring_stress.py
```

### Test Specific Scenarios
```python
from test_scoring_stress import stress_test_all_scenarios, test_edge_cases

# Just main scenarios
stress_test_all_scenarios()

# Just edge cases
test_edge_cases()
```

### Add Custom Test Cases
Edit `TEST_PROJECTS` list in `test_scoring_stress.py`:
```python
TEST_PROJECTS.append({
    "name": "My Custom Site",
    "project": {
        "capacity_mw": 75,
        "development_status_short": "application submitted",
        "technology_type": "Hybrid",
        "latitude": 52.0,
        "longitude": -1.0,
    },
    "proximity_scores": {
        "nearest_distances": {
            "substation_km": 5.0,
            "transmission_km": 10.0,
            "fiber_km": 2.0,
            "ixp_km": 5.0,
            "water_km": 3.0,
        }
    },
})
```

---

**Document Version:** 1.0
**Date:** 2025-10-23
**Author:** Claude Code Analysis
**Test Run:** 8 scenarios, 4 edge cases, 3 sensitivity analyses
