# ML-Based Data Center Location Recommendation System

## 🎯 Overview

This MVP machine learning system analyzes your **existing data center locations** and their proximity to critical infrastructure to recommend optimal locations for **future data centers**.

**✨ New: CSV Scalability Support!** Now supports testing with **1000+ data center sites** by reading from CSV files. See [CSV Scalability Guide](CSV_SCALABILITY_GUIDE.md) for details.

### Key Features

- ✅ **Scalable CSV Input**: Load 10 to 1500+ locations from CSV files
- ✅ **Automated Testing**: Generate synthetic datasets for scalability testing
- ✅ **Performance Optimized**: Sub-linear scaling with batch processing
- ✅ **Flexible Format**: Supports multiple CSV column naming conventions
- ✅ **Production Ready**: API endpoint integrated with existing infrastructure

## 🏗️ Architecture

### How It Works

1. **Training Phase**: Analyzes existing data center locations to understand infrastructure proximity patterns
   - Calculates distance to substations, transmission lines, fiber networks, internet exchange points (IXPs), and water sources
   - Computes composite "infrastructure quality score" for each existing location
   - Establishes threshold score (25th percentile of existing locations)

2. **Recommendation Phase**: Evaluates candidate locations across the UK
   - Generates random candidate locations within UK bounds
   - Scores each candidate using the same infrastructure proximity metrics
   - Ranks candidates by composite score
   - Returns top N recommendations

### Infrastructure Features Used

| Feature | Weight | Description |
|---------|--------|-------------|
| **Substation Proximity** | 30% | Distance to nearest electrical substation |
| **Transmission Lines** | 25% | Distance to high-voltage transmission infrastructure |
| **Fiber Networks** | 25% | Distance to fiber optic cable networks |
| **Internet Exchange Points** | 15% | Distance to IXP facilities |
| **Water Sources** | 5% | Distance to water resources (for cooling) |

### Composite Score Formula

```
composite_score = (
    substation_score * 0.30 +
    transmission_score * 0.25 +
    fiber_score * 0.25 +
    ixp_score * 0.15 +
    water_score * 0.05
)
```

Individual feature scores use exponential decay based on distance.

## 🚀 Quick Start

### 1. Start the Backend Server

```bash
python main.py
```

The server will start on `http://127.0.0.1:8000`

### 2. Test the ML Endpoint

```bash
python test_ml_endpoint.py
```

This will:
- Send your existing data center locations to the API
- Evaluate 100 candidate locations
- Return top 15 recommendations
- Save results to `ml_recommendations.json`

## 📊 Working with CSV Files (1000+ Locations)

### Load from Your CSV File

```bash
# Test with your own data center CSV
python test_ml_endpoint.py your_datacenters.csv
```

**Required CSV columns:**
- `Latitude` or `latitude` - Decimal degrees
- `Longitude` or `longitude` - Decimal degrees
- `Data Centre Name` or `name` - Facility name (optional)

### Generate Large Test Datasets

```bash
# Generate 1500 synthetic data centers
python generate_large_dataset.py 1500 test_dataset.csv

# Test with generated dataset
python test_ml_endpoint.py test_dataset.csv
```

### Run Scalability Tests

Test performance with increasing dataset sizes (10 to 1500 locations):

```bash
python test_scalability.py
```

**Expected performance (1000 locations):** ~40-50s processing time

📖 **See [CSV Scalability Guide](CSV_SCALABILITY_GUIDE.md) for detailed documentation**

## 🔌 API Endpoint

**Endpoint**: `POST /api/ml/datacenter-locations`

**Request Body**:
```json
{
  "existing_locations": [
    {
      "latitude": 57.1437,
      "longitude": -2.0981,
      "name": "IFB Union Street"
    },
    {
      "latitude": 51.7634,
      "longitude": -0.2242,
      "name": "Computacentre"
    }
  ],
  "num_candidates": 100,
  "top_n": 10,
  "grid_spacing_deg": 0.75
}
```

**Response**:
```json
{
  "top_recommendations": [
    {
      "latitude": 53.4808,
      "longitude": -2.2426,
      "composite_score": 8.5,
      "recommendation": "Recommended",
      "percentile_rank": 95.0,
      "feature_scores": {
        "substation": 9.2,
        "transmission": 8.1,
        "fiber": 9.5,
        "ixp": 7.8,
        "water": 6.5
      },
      "distances_km": {
        "substation": 2.3,
        "transmission": 4.1,
        "fiber": 1.2,
        "ixp": 15.7,
        "water": 8.9
      }
    }
  ],
  "model_info": {
    "model_type": "infrastructure_proximity_based",
    "training_samples": 6,
    "threshold_score": 5.2,
    "candidates_evaluated": 100
  },
  "processing_time_seconds": 3.45
}
```

## 📊 Data Files

### Input

**`existing_datacenters.csv`** - Your existing data center locations:
```csv
Postcode,Data Centre Name,Data Centre Address,Longitude,Latitude,ref_id
AB116BX,IFB Union Street,,-2.0981,57.1437,1
AB123LE,IFB Union Street,,-2.0981,57.1437,2
...
```

### Output

**`ml_recommendations.json`** - Top recommended locations with scores and infrastructure proximity metrics

## 🎛️ Configuration Options

### Request Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `existing_locations` | List | Required | Array of your existing data centers (lat/lon) |
| `num_candidates` | int | 50 | Number of candidate locations to evaluate |
| `top_n` | int | 10 | Number of top recommendations to return |
| `grid_spacing_deg` | float | 0.75 | Grid spacing for systematic coverage (not used in random mode) |

### Adjusting Feature Weights

To customize infrastructure weights for different data center types, modify the composite score calculation in `main.py:4190-4196`:

**Example for Edge Computing** (prioritize latency/fiber over power):
```python
composite = (
    prox.get("substation_score", 0.0) * 0.15 +   # Lower weight
    prox.get("transmission_score", 0.0) * 0.10 +  # Lower weight
    prox.get("fiber_score", 0.0) * 0.40 +         # Higher weight
    prox.get("ixp_score", 0.0) * 0.30 +           # Higher weight
    prox.get("water_score", 0.0) * 0.05
)
```

**Example for Hyperscale** (prioritize power and cooling):
```python
composite = (
    prox.get("substation_score", 0.0) * 0.35 +   # Higher weight
    prox.get("transmission_score", 0.0) * 0.30 +  # Higher weight
    prox.get("fiber_score", 0.0) * 0.15 +
    prox.get("ixp_score", 0.0) * 0.05 +
    prox.get("water_score", 0.0) * 0.15           # Higher weight
)
```

## 🧪 Testing with Different Scenarios

### Scenario 1: Quick Scan (50 candidates)
```bash
curl -X POST http://127.0.0.1:8000/api/ml/datacenter-locations \
  -H "Content-Type: application/json" \
  -d @- <<EOF
{
  "existing_locations": [
    {"latitude": 57.1437, "longitude": -2.0981, "name": "Aberdeen DC"}
  ],
  "num_candidates": 50,
  "top_n": 5
}
EOF
```

### Scenario 2: Comprehensive Analysis (200 candidates)
```bash
curl -X POST http://127.0.0.1:8000/api/ml/datacenter-locations \
  -H "Content-Type: application/json" \
  -d @existing_request.json
```

Where `existing_request.json` contains:
```json
{
  "existing_locations": [
    {"latitude": 57.1437, "longitude": -2.0981, "name": "Aberdeen DC 1"},
    {"latitude": 51.7634, "longitude": -0.2242, "name": "London DC 1"},
    {"latitude": 53.4808, "longitude": -2.2426, "name": "Manchester DC"}
  ],
  "num_candidates": 200,
  "top_n": 20
}
```

## 📈 Interpreting Results

### Composite Score Scale

- **8.0 - 10.0**: Excellent - Similar or better infrastructure than best existing sites
- **6.0 - 7.9**: Good - Above average infrastructure proximity
- **4.0 - 5.9**: Moderate - Acceptable infrastructure but may require investment
- **< 4.0**: Poor - Significant infrastructure challenges

### Recommendation Status

- **"Recommended"**: Composite score ≥ threshold (25th percentile of existing sites)
- **"Not Recommended"**: Below threshold

### Percentile Rank

Shows how a location compares to all evaluated candidates (95th percentile = top 5%)

## 🔧 Troubleshooting

### Issue: "Database error: 403"
**Solution**: Ensure Supabase credentials are configured in `.env`:
```bash
SUPABASE_URL=your_url
SUPABASE_ANON_KEY=your_key
```

### Issue: "Request timeout"
**Solution**: Reduce `num_candidates` or increase timeout in test script

### Issue: All scores are 0
**Solution**: Infrastructure data may not be loaded. Check server logs for errors during startup

## 🚀 Next Steps & Enhancements

### Short Term
1. **Add Persona Support**: Integrate with existing `PERSONA_WEIGHTS` (hyperscaler, colocation, edge)
2. **Visualization**: Create map visualization of recommendations
3. **Batch Processing**: Support uploading CSV of existing locations
4. **Export**: Download recommendations as CSV/GeoJSON

### Medium Term
1. **Advanced ML**: Train gradient boosting model with negative samples
2. **Clustering**: Use DBSCAN to identify optimal regional hubs
3. **Multi-Criteria**: Add population density, energy costs, planning regulations
4. **Time Series**: Consider capacity expansion plans over time

### Long Term
1. **Optimization**: Recommend N locations that minimize total latency to population centers
2. **Risk Analysis**: Factor in climate risk, political stability, natural disasters
3. **Cost Modeling**: Integrate land costs, energy prices, tax incentives
4. **Portfolio Diversification**: Recommend geographically diverse locations for resilience

## 📚 Technical Details

### ML Approach

This MVP uses **supervised learning with positive-only samples**:

- **Training data**: Existing data center locations (all labeled as "good")
- **Assumption**: Existing locations represent successful infrastructure proximity patterns
- **Model**: Statistical threshold-based classification
- **Features**: 5 infrastructure proximity scores
- **Output**: Binary recommendation + composite score

### Why This Approach?

1. **No labeled negative samples needed** - We don't have data on "failed" or "bad" locations
2. **Interpretable** - Clear relationship between infrastructure and score
3. **Fast** - No complex model training required
4. **Robust** - Works with small sample sizes (6+ existing locations)
5. **Practical** - Directly actionable recommendations

### Limitations

1. **Sample bias**: Assumes existing locations are optimal (may not be true)
2. **Limited features**: Only infrastructure proximity (no costs, regulations, etc.)
3. **No geographic constraints**: Doesn't consider land availability or zoning
4. **Static model**: Doesn't learn from new deployments over time

## 🤝 Contributing

To extend this system:

1. **Add new infrastructure sources**: Edit `main.py` to load additional data (e.g., renewable energy sites)
2. **Modify feature weights**: Adjust weights in `main.py:4240-4246`
3. **Change threshold**: Use median (50th percentile) instead of 25th for stricter filtering
4. **Add filters**: Filter candidates by region, proximity to cities, etc.

## 📄 License & Support

Part of the Infranodal infrastructure analysis platform.

For questions or issues, contact the development team.
