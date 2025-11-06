# Dynamic Weight Generation - Usage Guide

## Overview

The dynamic weight generation system allows users to create custom scoring weights through intuitive, high-level inputs instead of manually specifying all 7 criteria weights. This guide provides practical examples for each method.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Method 1: Priority-Based](#method-1-priority-based)
3. [Method 2: Constraint-Based](#method-2-constraint-based)
4. [Method 3: Persona Blending](#method-3-persona-blending)
5. [Method 4: Goal-Oriented](#method-4-goal-oriented)
6. [Using Generated Weights](#using-generated-weights)
7. [API Reference](#api-reference)

---

## Quick Start

### Problem
You need to score projects but the preset personas don't match your needs.

### Solution
Use one of 4 intuitive methods to generate custom weights:

| Method | Best For | Complexity |
|--------|----------|------------|
| **Priorities** | "I care about X more than Y" | 🟢 Simple |
| **Constraints** | "I need X budget, Y timeline" | 🟡 Moderate |
| **Blending** | "Mix hyperscaler + colocation" | 🟢 Simple |
| **Goals** | "Optimize for speed + cost" | 🟠 Advanced |

---

## Method 1: Priority-Based

### When to Use
- You understand the 7 criteria
- Want to specify relative importance simply
- Don't need complex constraint analysis

### How It Works
Rate each criterion 1-5:
- **1**: Low importance
- **2**: Below average
- **3**: Moderate (default)
- **4**: Important
- **5**: Critical

### Example: Budget-Conscious Startup

**Scenario**: Small startup, price-sensitive, needs moderate capacity, not latency-critical

```bash
curl -X POST http://localhost:8000/api/weights/from-priorities \
  -H "Content-Type: application/json" \
  -d '{
    "priorities": {
      "capacity": 3,
      "connection_speed": 4,
      "resilience": 2,
      "land_planning": 4,
      "latency": 1,
      "cooling": 2,
      "price_sensitivity": 5
    }
  }'
```

**Response**:
```json
{
  "weights": {
    "capacity": 0.1429,
    "connection_speed": 0.1905,
    "resilience": 0.0952,
    "land_planning": 0.1905,
    "latency": 0.0476,
    "cooling": 0.0952,
    "price_sensitivity": 0.2381
  },
  "methodology": "priority-based",
  "validation": {"valid": true},
  "sum": 1.0
}
```

### Example: High-Performance Computing

**Scenario**: HPC workload requiring low latency, high cooling, strong resilience

```bash
curl -X POST http://localhost:8000/api/weights/from-priorities \
  -H "Content-Type: application/json" \
  -d '{
    "priorities": {
      "capacity": 3,
      "connection_speed": 4,
      "resilience": 5,
      "land_planning": 3,
      "latency": 5,
      "cooling": 5,
      "price_sensitivity": 2
    }
  }'
```

**Result**: Weights emphasize latency (18.5%), resilience (18.5%), and cooling (18.5%)

### Example: Hybrid Approach with Persona Blend

**Scenario**: Start with hyperscaler baseline, customize with your priorities

```bash
curl -X POST http://localhost:8000/api/weights/from-priorities \
  -H "Content-Type: application/json" \
  -d '{
    "priorities": {
      "price_sensitivity": 5,
      "resilience": 5
    },
    "base_persona": "hyperscaler",
    "blend_factor": 0.5
  }'
```

**Result**: 50% your priorities + 50% hyperscaler preset = balanced hybrid

---

## Method 2: Constraint-Based

### When to Use
- Have specific requirements (budget, timeline, capacity)
- Want system to intelligently adjust weights
- Need constraint-driven optimization

### How It Works
Specify constraints, system boosts relevant criteria weights automatically.

### Example: Fast Deployment on Budget

**Scenario**: Need deployment in 12 months, budget £55/MWh, 25MW capacity

```bash
curl -X POST http://localhost:8000/api/weights/from-constraints \
  -H "Content-Type: application/json" \
  -d '{
    "constraints": {
      "capacity_required_mw": 25,
      "max_price_mwh": 55,
      "deployment_timeline_months": 12,
      "must_have_redundancy": false,
      "location_flexibility": "high"
    },
    "base_persona": "hyperscaler"
  }'
```

**What Happens**:
1. `max_price_mwh: 55` (below £70 market avg) → **↑ price_sensitivity** by 1.27x
2. `deployment_timeline_months: 12` (urgent) → **↑ land_planning** by 1.25x, **↑ connection_speed** by 1.15x
3. `location_flexibility: high` → **↑ price_sensitivity** by 1.2x (can shop around)

**Console Output**:
```
🔧 Weight adjustments applied:
   • Boosted price_sensitivity by 1.27x (budget £55/MWh < market avg)
   • Boosted land_planning & connection_speed (deployment in 12 months)
   • Boosted price_sensitivity (high location flexibility)
```

**Response**:
```json
{
  "weights": {
    "capacity": 0.206,
    "connection_speed": 0.162,
    "resilience": 0.112,
    "land_planning": 0.211,
    "latency": 0.047,
    "cooling": 0.121,
    "price_sensitivity": 0.141
  },
  "methodology": "constraint-based optimization",
  "adjustments_applied": [
    {
      "criterion": "price_sensitivity",
      "reason": "Budget £55/MWh below market average",
      "direction": "increased"
    },
    {
      "criterion": "land_planning",
      "reason": "Fast deployment needed (12 months)",
      "direction": "increased"
    }
  ]
}
```

### Example: Enterprise Mission-Critical

**Scenario**: Large capacity, must have redundancy, latency-sensitive, location-constrained

```bash
curl -X POST http://localhost:8000/api/weights/from-constraints \
  -H "Content-Type: application/json" \
  -d '{
    "constraints": {
      "capacity_required_mw": 150,
      "deployment_timeline_months": 30,
      "must_have_redundancy": true,
      "latency_sensitive": true,
      "cooling_intensive": true,
      "location_flexibility": "low"
    },
    "base_persona": "hyperscaler"
  }'
```

**What Happens**:
1. `capacity: 150` (large) → **↑ capacity** by 1.3x
2. `must_have_redundancy` → **↑ resilience** by 1.5x, **↑ connection_speed** by 1.2x
3. `latency_sensitive` → **↑ latency** by 2.0x, **↑ cooling** by 1.2x
4. `cooling_intensive` → **↑ cooling** by 1.8x
5. `location_flexibility: low` → **↑ latency** by 1.3x, **↑ cooling** by 1.3x

**Result**: Heavily weighted toward operational criteria (resilience, latency, cooling)

---

## Method 3: Persona Blending

### When to Use
- Hybrid use case combining multiple personas
- Want to mix characteristics
- Need weighted average of personas

### How It Works
Specify blend ratios, system averages the persona weights.

### Example: Hybrid Cloud Provider

**Scenario**: 60% hyperscaler workloads, 40% colocation tenants

```bash
curl -X POST http://localhost:8000/api/weights/blend-personas \
  -H "Content-Type: application/json" \
  -d '{
    "persona_blend": {
      "hyperscaler": 0.6,
      "colocation": 0.4
    }
  }'
```

**Response**:
```json
{
  "weights": {
    "capacity": 0.2028,
    "connection_speed": 0.1666,
    "resilience": 0.1582,
    "land_planning": 0.1852,
    "latency": 0.1204,
    "cooling": 0.1212,
    "price_sensitivity": 0.0468
  },
  "methodology": "persona blending",
  "persona_blend": {
    "hyperscaler": 0.6,
    "colocation": 0.4
  }
}
```

### Example: Three-Way Blend

**Scenario**: Mixed edge + colocation + some hyperscale

```bash
curl -X POST http://localhost:8000/api/weights/blend-personas \
  -H "Content-Type: application/json" \
  -d '{
    "persona_blend": {
      "edge_computing": 0.5,
      "colocation": 0.3,
      "hyperscaler": 0.2
    }
  }'
```

**Result**: Balanced weights reflecting all three use cases

---

## Method 4: Goal-Oriented

### When to Use
- Multiple competing objectives
- Need to optimize trade-offs
- Have clear goals with priorities

### How It Works
Specify objectives with importance weights, system maps goals to criteria.

### Supported Objectives

| Objective | Maps To Criteria | Use Case |
|-----------|-----------------|----------|
| `minimize_deployment_time` | land_planning (50%), connection_speed (30%) | Fast time-to-market |
| `minimize_total_cost` | price_sensitivity (60%), capacity (20%) | Budget-constrained |
| `maximize_reliability` | resilience (40%), cooling (25%), connection_speed (25%) | Mission-critical |
| `minimize_latency` | latency (60%), connection_speed (30%) | Real-time workloads |
| `maximize_capacity` | capacity (70%), connection_speed (20%) | Scale-focused |
| `maximize_flexibility` | land_planning (40%), resilience (30%) | Adaptable deployment |

### Example: Speed + Cost Optimization

**Scenario**: 50% focus on fast deployment, 30% on cost, 20% on reliability

```bash
curl -X POST http://localhost:8000/api/weights/optimize-for-goals \
  -H "Content-Type: application/json" \
  -d '{
    "goals": [
      {"objective": "minimize_deployment_time", "importance": 0.5},
      {"objective": "minimize_total_cost", "importance": 0.3},
      {"objective": "maximize_reliability", "importance": 0.2}
    ]
  }'
```

**How It's Calculated**:
```
minimize_deployment_time (50%):
  → land_planning: 0.5 × 0.5 = 0.25
  → connection_speed: 0.3 × 0.5 = 0.15

minimize_total_cost (30%):
  → price_sensitivity: 0.6 × 0.3 = 0.18
  → capacity: 0.2 × 0.3 = 0.06

maximize_reliability (20%):
  → resilience: 0.4 × 0.2 = 0.08
  → cooling: 0.25 × 0.2 = 0.05
  → connection_speed: 0.25 × 0.2 = 0.05

Sum connection_speed: 0.15 + 0.05 = 0.20
Add diversity padding + normalize
```

**Response**:
```json
{
  "weights": {
    "capacity": 0.078,
    "connection_speed": 0.222,
    "resilience": 0.098,
    "land_planning": 0.272,
    "latency": 0.020,
    "cooling": 0.069,
    "price_sensitivity": 0.220
  },
  "methodology": "goal-oriented optimization",
  "goals": [
    {"objective": "minimize_deployment_time", "importance": 0.5},
    {"objective": "minimize_total_cost", "importance": 0.3},
    {"objective": "maximize_reliability", "importance": 0.2}
  ]
}
```

### Example: Latency-Focused

**Scenario**: Latency is everything (80%), some reliability (20%)

```bash
curl -X POST http://localhost:8000/api/weights/optimize-for-goals \
  -H "Content-Type: application/json" \
  -d '{
    "goals": [
      {"objective": "minimize_latency", "importance": 0.8},
      {"objective": "maximize_reliability", "importance": 0.2}
    ]
  }'
```

**Result**: Heavy emphasis on latency (48%), connection_speed (31%), with resilience (8%) and cooling (9%)

---

## Using Generated Weights

### Step 1: Generate Weights

Use any of the 4 methods above to get custom weights.

### Step 2: Use in Scoring

Pass generated weights as `custom_weights` JSON string to `/api/projects/enhanced`:

```bash
# Generate weights
WEIGHTS=$(curl -s -X POST http://localhost:8000/api/weights/from-priorities \
  -H "Content-Type: application/json" \
  -d '{"priorities": {"price_sensitivity": 5, "capacity": 4}}' \
  | jq -c '.weights')

# Use in scoring
curl -X GET "http://localhost:8000/api/projects/enhanced?limit=100&custom_weights=${WEIGHTS}"
```

### Step 3: Compare Results

Compare custom weights vs. preset personas:

```bash
curl "http://localhost:8000/api/projects/compare-scoring?persona=hyperscaler&project_ref_id=ABC123"
```

---

## API Reference

### POST /api/weights/from-priorities

**Request Body**:
```json
{
  "priorities": {
    "capacity": 1-5,
    "connection_speed": 1-5,
    "resilience": 1-5,
    "land_planning": 1-5,
    "latency": 1-5,
    "cooling": 1-5,
    "price_sensitivity": 1-5
  },
  "base_persona": "hyperscaler" | "colocation" | "edge_computing" | null,
  "blend_factor": 0.0-1.0  // 0 = full custom, 1 = full persona
}
```

**Response**:
```json
{
  "weights": {...},
  "methodology": "priority-based [with X% persona blend]",
  "validation": {"valid": true},
  "sum": 1.0
}
```

---

### POST /api/weights/from-constraints

**Request Body**:
```json
{
  "constraints": {
    "capacity_required_mw": number,
    "max_price_mwh": number,
    "deployment_timeline_months": number,
    "must_have_redundancy": boolean,
    "latency_sensitive": boolean,
    "cooling_intensive": boolean,
    "location_flexibility": "low" | "medium" | "high"
  },
  "base_persona": "hyperscaler" | "colocation" | "edge_computing" | null
}
```

**Response**:
```json
{
  "weights": {...},
  "methodology": "constraint-based optimization",
  "adjustments_applied": [
    {"criterion": "...", "reason": "...", "direction": "increased"}
  ]
}
```

---

### POST /api/weights/blend-personas

**Request Body**:
```json
{
  "persona_blend": {
    "hyperscaler": 0.0-1.0,
    "colocation": 0.0-1.0,
    "edge_computing": 0.0-1.0
  }
}
```

**Response**:
```json
{
  "weights": {...},
  "methodology": "persona blending",
  "persona_blend": {...}
}
```

---

### POST /api/weights/optimize-for-goals

**Request Body**:
```json
{
  "goals": [
    {"objective": "minimize_deployment_time", "importance": 0.0-1.0},
    {"objective": "minimize_total_cost", "importance": 0.0-1.0},
    {"objective": "maximize_reliability", "importance": 0.0-1.0},
    {"objective": "minimize_latency", "importance": 0.0-1.0},
    {"objective": "maximize_capacity", "importance": 0.0-1.0},
    {"objective": "maximize_flexibility", "importance": 0.0-1.0}
  ]
}
```

**Response**:
```json
{
  "weights": {...},
  "methodology": "goal-oriented optimization",
  "goals": [...],
  "supported_objectives": [...]
}
```

---

## Validation Rules

All generated weights must satisfy:

1. ✅ **All 7 criteria present**
2. ✅ **All weights ≥ 0**
3. ✅ **Sum = 1.0** (±0.001 tolerance)
4. ✅ **No single weight > 0.5** (prevents over-concentration)
5. ✅ **At least 3 weights > 0.05** (ensures diversity)

If validation fails, the response includes:
```json
{
  "validation": {
    "valid": false,
    "error": "Single weight 'latency' = 0.65 exceeds 50% limit"
  }
}
```

---

## Best Practices

### 1. Start Simple
Begin with **priority-based** or **persona blending**. Advance to constraints/goals as needed.

### 2. Use Base Personas
For priority-based, start with a persona base:
```json
{
  "priorities": {"price_sensitivity": 5},
  "base_persona": "hyperscaler",
  "blend_factor": 0.3
}
```
This gives 70% your priorities + 30% expert-designed hyperscaler weights.

### 3. Validate Results
Always check:
- `validation.valid` is `true`
- `sum` is `1.0`
- Weights align with your intentions

### 4. Compare Approaches
Try multiple methods, compare results:
```bash
# Priority-based
curl .../from-priorities -d '{...}'

# Constraint-based
curl .../from-constraints -d '{...}'

# Compare which gives better results
```

### 5. Iterate
Adjust priorities/constraints, regenerate, test with actual scoring.

---

## Troubleshooting

### "Weight sum is not 1.0"
**Cause**: Internal math issue (shouldn't happen)
**Solution**: Weights are auto-normalized; if this appears, report bug

### "Single weight exceeds 50% limit"
**Cause**: Too extreme priority or constraint
**Solution**: Reduce priority value or use blend with base persona

### "At least 3 criteria must have >5% weight"
**Cause**: Too concentrated on 1-2 criteria
**Solution**: Spread importance across more criteria or use lower priorities

### "Unknown persona in blend"
**Cause**: Typo in persona name
**Solution**: Use exact names: `hyperscaler`, `colocation`, `edge_computing`

---

## Examples Summary

| Use Case | Method | Key Parameters |
|----------|--------|----------------|
| Budget-conscious | Priorities | `price_sensitivity: 5` |
| Fast deployment | Constraints | `deployment_timeline_months: 12` |
| HPC workload | Priorities | `latency: 5, cooling: 5, resilience: 5` |
| Hybrid cloud | Blending | `hyperscaler: 0.6, colocation: 0.4` |
| Speed + cost | Goals | `minimize_deployment_time + minimize_total_cost` |
| Mission-critical | Constraints | `must_have_redundancy: true, latency_sensitive: true` |

---

## Next Steps

1. **Try the API**: Test weight generation with your requirements
2. **Score Projects**: Use generated weights in `/api/projects/enhanced`
3. **Compare Results**: See how custom weights affect rankings
4. **Refine**: Iterate on priorities/constraints based on results
5. **Feedback**: Report what works and what doesn't

---

**Questions?** Check the [DYNAMIC_WEIGHTS_STRATEGY.md](DYNAMIC_WEIGHTS_STRATEGY.md) for implementation details.
