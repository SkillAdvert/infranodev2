# Dynamic Persona Weights Strategy

## Executive Summary

This document outlines a comprehensive strategy to make persona weights dynamic and responsive to user inputs, transforming the static weight system into an intelligent, adaptive scoring framework.

---

## 1. CURRENT STATE ANALYSIS

### Existing Weight System

**Static Weights** (main.py:69-97):
```python
PERSONA_WEIGHTS = {
    "hyperscaler": {
        "capacity": 0.244,
        "connection_speed": 0.167,
        "resilience": 0.133,
        "land_planning": 0.2,
        "latency": 0.056,
        "cooling": 0.144,
        "price_sensitivity": 0.056,
    },
    # ... more personas
}
```

**Current User Inputs**:
1. `persona`: Select predefined persona (hyperscaler/colocation/edge_computing)
2. `custom_weights`: JSON string with manual 7-weight specification
3. `user_ideal_mw`: Override capacity ideal
4. `user_max_price_mwh`: Set price budget constraint
5. `dc_demand_mw`: Facility demand for capacity filtering

### Limitations

1. **No Intuitive Customization**: Users must understand all 7 criteria and manually balance weights to sum to 1.0
2. **Binary Choice**: Either use preset persona OR fully custom weights (no hybrid)
3. **No Constraint-Based Optimization**: User constraints don't automatically adjust weights
4. **No Priority Expression**: Can't say "I care about X more than Y" without doing math
5. **No Learning**: System doesn't adapt based on user selections or feedback

---

## 2. STRATEGIC APPROACH: MULTI-TIER WEIGHT GENERATION

### Tier 1: Priority-Based Adjustment (Simple)
**User Experience**: "I care more about cost and speed"

Users specify importance levels (1-5) for each criterion. System converts to weights.

**Example Input**:
```json
{
  "priorities": {
    "capacity": 4,
    "connection_speed": 5,
    "price_sensitivity": 5,
    "resilience": 3,
    "land_planning": 3,
    "latency": 2,
    "cooling": 2
  }
}
```

**Algorithm**:
```python
total = sum(priorities)
weights = {k: v / total for k, v in priorities.items()}
```

### Tier 2: Constraint-Based Optimization (Moderate)
**User Experience**: "I need 50MW, budget £65/MWh, deployment in 18 months"

System analyzes constraints and adjusts weights to emphasize relevant criteria.

**Example Input**:
```json
{
  "capacity_required_mw": 50,
  "max_price_mwh": 65,
  "deployment_timeline_months": 18,
  "must_have_redundancy": true,
  "location_flexibility": "low"
}
```

**Weight Adjustments**:
- `max_price_mwh` < market average → ↑ price_sensitivity weight
- `deployment_timeline_months` < 24 → ↑ land_planning weight (shovel-ready)
- `must_have_redundancy` = true → ↑ resilience weight
- `location_flexibility` = low → ↑ latency/cooling (pick best site)

### Tier 3: Persona Blending (Advanced)
**User Experience**: "Mix hyperscaler + colocation characteristics"

Blend multiple persona weights with user-specified ratios.

**Example Input**:
```json
{
  "persona_blend": {
    "hyperscaler": 0.6,
    "colocation": 0.4
  }
}
```

### Tier 4: Goal-Oriented Optimization (Expert)
**User Experience**: "Optimize for fastest deployment + lowest TCO"

Multi-objective optimization with user-defined goals and trade-offs.

**Example Input**:
```json
{
  "goals": [
    {"objective": "minimize_deployment_time", "importance": 0.6},
    {"objective": "minimize_total_cost", "importance": 0.4}
  ]
}
```

---

## 3. IMPLEMENTATION ARCHITECTURE

### 3.1 Weight Generation Pipeline

```
User Input → Tier Detection → Weight Generator → Validation → Normalization → Scoring
```

### 3.2 Core Components

#### A. Priority-to-Weight Converter
```python
def priorities_to_weights(
    priorities: Dict[str, int],
    base_persona: Optional[str] = None,
    blend_factor: float = 0.5
) -> Dict[str, float]:
    """
    Convert user priority ratings (1-5) to normalized weights.

    Args:
        priorities: Criteria importance (1=low, 5=critical)
        base_persona: Optional persona to blend with
        blend_factor: How much to blend with base (0=full custom, 1=full persona)
    """
```

#### B. Constraint-to-Weight Adjuster
```python
def constraints_to_weight_adjustments(
    constraints: Dict[str, Any],
    base_weights: Dict[str, float]
) -> Dict[str, float]:
    """
    Adjust weights based on user constraints.

    Constraints analyzed:
    - Budget → price_sensitivity
    - Timeline → land_planning
    - Capacity → capacity
    - Redundancy → resilience
    - Digital requirements → latency
    - Cooling needs → cooling
    - Grid access → connection_speed
    """
```

#### C. Persona Blender
```python
def blend_persona_weights(
    persona_mix: Dict[str, float],
    personas_dict: Dict[str, Dict[str, float]]
) -> Dict[str, float]:
    """
    Blend multiple persona weights.

    Formula: weights = Σ(persona_i × ratio_i)
    """
```

#### D. Goal Optimizer
```python
def optimize_weights_for_goals(
    goals: List[Dict[str, Any]],
    component_mappings: Dict[str, List[str]]
) -> Dict[str, float]:
    """
    Generate weights that optimize for multiple objectives.

    Goals mapped to criteria:
    - minimize_deployment_time → land_planning, connection_speed
    - minimize_total_cost → price_sensitivity
    - maximize_reliability → resilience, cooling
    - minimize_latency → latency, connection_speed
    """
```

### 3.3 API Design

#### Endpoint 1: Generate Weights from Priorities
```
POST /api/weights/from-priorities
{
  "priorities": {
    "capacity": 4,
    "connection_speed": 5,
    ...
  },
  "base_persona": "hyperscaler",  // optional
  "blend_factor": 0.3  // optional, 0-1
}

Response:
{
  "weights": {...},
  "methodology": "priority-based with 30% hyperscaler blend",
  "normalized": true
}
```

#### Endpoint 2: Generate Weights from Constraints
```
POST /api/weights/from-constraints
{
  "capacity_required_mw": 50,
  "max_price_mwh": 65,
  "deployment_timeline_months": 18,
  "must_have_redundancy": true,
  "location_flexibility": "low",
  "base_persona": "hyperscaler"  // optional starting point
}

Response:
{
  "weights": {...},
  "adjustments_applied": [
    {
      "criterion": "price_sensitivity",
      "original": 0.056,
      "adjusted": 0.15,
      "reason": "Budget £65/MWh below market avg (£70)"
    },
    ...
  ],
  "methodology": "constraint-based optimization"
}
```

#### Endpoint 3: Blend Personas
```
POST /api/weights/blend-personas
{
  "persona_blend": {
    "hyperscaler": 0.6,
    "colocation": 0.3,
    "edge_computing": 0.1
  }
}
```

#### Endpoint 4: Optimize for Goals
```
POST /api/weights/optimize-for-goals
{
  "goals": [
    {"objective": "minimize_deployment_time", "importance": 0.5},
    {"objective": "minimize_total_cost", "importance": 0.3},
    {"objective": "maximize_reliability", "importance": 0.2}
  ]
}
```

#### Enhanced Main Endpoint
```
GET /api/projects/enhanced
  ?persona=hyperscaler  // traditional
  &weight_generation_mode=priority  // NEW
  &priorities={"capacity":4,"price_sensitivity":5,...}  // NEW
  &constraints={"max_price_mwh":65,...}  // NEW
  &custom_weights={...}  // existing fallback
```

---

## 4. WEIGHT ADJUSTMENT RULES

### Rule-Based Adjustments

#### Budget Constraints
```python
if user_max_price_mwh:
    market_avg = 70.0  # £/MWh
    if user_max_price_mwh < market_avg * 0.9:
        # Budget-sensitive → boost price_sensitivity
        adjustment_factor = 1 + (market_avg - user_max_price_mwh) / market_avg
        weights["price_sensitivity"] *= adjustment_factor
```

#### Timeline Constraints
```python
if deployment_timeline_months < 24:
    # Fast deployment → boost land_planning (shovel-ready sites)
    urgency_factor = (24 - deployment_timeline_months) / 24
    weights["land_planning"] *= (1 + urgency_factor)
    weights["connection_speed"] *= (1 + urgency_factor * 0.5)
```

#### Capacity Constraints
```python
if capacity_required_mw > 100:
    # Large capacity → boost capacity weight
    weights["capacity"] *= 1.3
elif capacity_required_mw < 10:
    # Small capacity → reduce capacity importance
    weights["capacity"] *= 0.7
```

#### Redundancy Requirements
```python
if must_have_redundancy:
    weights["resilience"] *= 1.5
    weights["connection_speed"] *= 1.2  # multiple connection options
```

#### Latency Requirements
```python
if latency_sensitive_workloads:
    weights["latency"] *= 2.0
    weights["cooling"] *= 1.2  # better cooling = better performance
```

---

## 5. USER INTERFACE DESIGN

### Option A: Slider-Based Priority Setting
```
Capacity:          ●----       (3/5) Moderate
Connection Speed:  ●●●●●       (5/5) Critical
Resilience:        ●●--        (2/5) Low
Land Planning:     ●●●●-       (4/5) Important
Latency:           ●----       (1/5) Not Important
Cooling:           ●●●--       (3/5) Moderate
Price Sensitivity: ●●●●●       (5/5) Critical

[Generate Custom Weights]
```

### Option B: Constraint-Based Wizard
```
Step 1: What's your budget?
  ○ Flexible (price not a primary concern)
  ○ Market rate (~£70/MWh)
  ● Below market (£___/MWh)

Step 2: When do you need to deploy?
  ○ No rush (36+ months)
  ● Fast (12-24 months)
  ○ Urgent (<12 months)

Step 3: Capacity requirements?
  [50] MW

Step 4: Redundancy needs?
  ● Must have N+1 redundancy
  ○ Some redundancy preferred
  ○ Not critical

[Generate Optimized Weights]
```

### Option C: Template-Based Selection
```
Choose a scenario that matches your needs:

● Cost-Optimized Deployment
  Focus: Lowest TCO, flexible on location/timing
  Weights: price_sensitivity (35%), capacity (20%), ...

○ Speed-to-Market
  Focus: Fastest deployment, shovel-ready sites
  Weights: land_planning (35%), connection_speed (25%), ...

○ High-Performance Computing
  Focus: Maximum reliability and low latency
  Weights: latency (30%), resilience (25%), cooling (20%), ...

○ Balanced Approach
  Focus: Equal consideration of all factors
  Weights: All criteria weighted equally (14.3% each)

[Customize Further] [Use Template]
```

---

## 6. VALIDATION AND SAFEGUARDS

### Weight Validation Rules

```python
def validate_weights(weights: Dict[str, float]) -> Tuple[bool, Optional[str]]:
    """
    Ensure generated weights are valid.

    Rules:
    1. All 7 criteria must be present
    2. All weights must be non-negative
    3. Weights must sum to 1.0 (±0.001 tolerance)
    4. No single weight > 0.5 (prevent over-concentration)
    5. At least 3 weights must be > 0.05 (force diversity)
    """

    # Check sum
    total = sum(weights.values())
    if not math.isclose(total, 1.0, abs_tol=0.001):
        return False, f"Weights sum to {total}, not 1.0"

    # Check concentration
    max_weight = max(weights.values())
    if max_weight > 0.5:
        return False, f"Single weight {max_weight} exceeds 50% limit"

    # Check diversity
    significant = [w for w in weights.values() if w > 0.05]
    if len(significant) < 3:
        return False, "At least 3 criteria must have >5% weight"

    return True, None
```

### Normalization

```python
def normalize_weights(weights: Dict[str, float]) -> Dict[str, float]:
    """Ensure weights sum to exactly 1.0"""
    total = sum(weights.values())
    if total == 0:
        # All zeros → equal distribution
        return {k: 1.0 / len(weights) for k in weights}
    return {k: v / total for k, v in weights.items()}
```

---

## 7. IMPLEMENTATION PHASES

### Phase 1: Foundation (Week 1)
- [ ] Implement priority-to-weight converter
- [ ] Add weight validation functions
- [ ] Create `/api/weights/from-priorities` endpoint
- [ ] Add `weight_generation_mode` parameter to main endpoint
- [ ] Unit tests for weight generation

### Phase 2: Constraint-Based (Week 2)
- [ ] Implement constraint analysis engine
- [ ] Build adjustment rule system
- [ ] Create `/api/weights/from-constraints` endpoint
- [ ] Integration tests with scoring pipeline

### Phase 3: Advanced Features (Week 3)
- [ ] Implement persona blending
- [ ] Build goal-oriented optimizer
- [ ] Create remaining API endpoints
- [ ] Performance optimization

### Phase 4: UI/UX (Week 4)
- [ ] Frontend weight generation wizard
- [ ] Slider-based priority interface
- [ ] Template-based selection
- [ ] Weight visualization (radar chart)
- [ ] A/B testing framework

---

## 8. EXAMPLE USE CASES

### Use Case 1: Budget-Conscious Startup
```json
{
  "constraints": {
    "capacity_required_mw": 15,
    "max_price_mwh": 55,
    "deployment_timeline_months": 24,
    "must_have_redundancy": false,
    "location_flexibility": "high"
  }
}

Generated Weights:
{
  "price_sensitivity": 0.35,  // ↑ (budget tight)
  "capacity": 0.18,
  "land_planning": 0.15,
  "connection_speed": 0.12,
  "resilience": 0.08,  // ↓ (not required)
  "latency": 0.07,
  "cooling": 0.05   // ↓ (location flexible)
}
```

### Use Case 2: Enterprise HPC Deployment
```json
{
  "priorities": {
    "latency": 5,
    "cooling": 5,
    "resilience": 5,
    "connection_speed": 4,
    "capacity": 3,
    "land_planning": 3,
    "price_sensitivity": 2
  }
}

Generated Weights:
{
  "latency": 0.185,  // ↑
  "cooling": 0.185,  // ↑
  "resilience": 0.185,  // ↑
  "connection_speed": 0.148,
  "capacity": 0.111,
  "land_planning": 0.111,
  "price_sensitivity": 0.074
}
```

### Use Case 3: Hybrid Cloud Provider
```json
{
  "persona_blend": {
    "hyperscaler": 0.5,
    "colocation": 0.5
  }
}

Generated Weights:
{
  "capacity": 0.193,  // avg(0.244, 0.141)
  "connection_speed": 0.165,  // avg(0.167, 0.163)
  "resilience": 0.165,  // avg(0.133, 0.196)
  "land_planning": 0.182,  // avg(0.2, 0.163)
  "latency": 0.137,  // avg(0.056, 0.217)
  "cooling": 0.116,  // avg(0.144, 0.087)
  "price_sensitivity": 0.045   // avg(0.056, 0.033)
}
```

---

## 9. ADVANCED FEATURES (FUTURE)

### Machine Learning Weight Optimization
- Train model on user selections and feedback
- Predict optimal weights based on project characteristics
- Collaborative filtering: "Users like you prioritized..."

### Dynamic Weight Adjustment During Search
- Real-time weight refinement based on result quality
- Interactive exploration: "Show me sites with more X, less Y"
- A/B testing different weight configurations

### Contextual Recommendations
- "Based on your constraints, consider increasing resilience weight by 10%"
- "Projects in your price range typically need shovel-ready sites"
- "Warning: Current weights may exclude 80% of available sites"

### Sensitivity Analysis
- Show how weight changes affect rankings
- Identify which criteria drive score differences
- Recommend weight adjustments for better results

---

## 10. TECHNICAL CONSIDERATIONS

### Performance Impact
- Weight generation: < 10ms overhead
- No change to scoring performance (same pipeline)
- Cache common weight configurations

### Backward Compatibility
- Existing `persona` parameter continues to work
- `custom_weights` JSON still supported
- New features are additive, not breaking

### Error Handling
- Invalid priority values → default to base persona
- Impossible constraints → return warning + best effort
- Weight validation failures → fallback to persona defaults

### Logging and Analytics
- Track which weight generation methods are used
- Monitor weight distributions
- Analyze correlation between weights and user satisfaction

---

## 11. SUCCESS METRICS

### User Adoption
- % of users using dynamic weights vs. static personas
- % using priorities vs. constraints vs. custom JSON
- User satisfaction scores

### Result Quality
- Precision@K for top results
- User click-through rates
- Conversion rates (viewing → selecting projects)

### System Performance
- Weight generation latency
- API response times
- Error rates

---

## 12. CONCLUSION

This strategy transforms the static persona system into a dynamic, user-centric weight generation framework. By offering multiple tiers of customization—from simple priority sliders to advanced constraint-based optimization—we enable users of all sophistication levels to express their requirements naturally and get personalized scoring.

**Key Benefits**:
1. **Intuitive**: No need to manually balance 7 weights
2. **Flexible**: Multiple input methods for different user types
3. **Intelligent**: System understands constraints and optimizes weights
4. **Backward Compatible**: Existing API contracts preserved
5. **Extensible**: Foundation for ML-driven optimization

**Next Steps**: Implement Phase 1 (priority-based adjustment) as MVP, gather user feedback, iterate.
