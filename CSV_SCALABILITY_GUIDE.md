# CSV Scalability Guide - ML Data Center Location System

## 🎯 Overview

The ML data center location recommendation system is designed to scale from small datasets (10-50 locations) to large enterprise datasets (1000+ locations). This guide explains how to work with large CSV files efficiently.

---

## 📋 CSV Format

### Required Columns

Your CSV must include these columns (case-insensitive):

| Column Name | Alternative Names | Required | Description |
|-------------|-------------------|----------|-------------|
| `Latitude` | `latitude`, `lat` | ✅ Yes | Decimal degrees (e.g., 51.5074) |
| `Longitude` | `longitude`, `lon`, `long` | ✅ Yes | Decimal degrees (e.g., -0.1278) |
| `Data Centre Name` | `name`, `facility_name` | ⚠️ Optional | Facility name (defaults to "Unknown") |

### Example CSV Format

```csv
Postcode,Data Centre Name,Data Centre Address,Longitude,Latitude,ref_id
AB116BX,IFB Union Street,,-2.0981,57.1437,1
AB123LE,IFB Union Street,,-2.0981,57.1437,2
L11234,Manchester DC 1,,-2.2426,53.4808,3
...
```

**Alternative minimal format:**
```csv
latitude,longitude,name
57.1437,-2.0981,Aberdeen DC
53.4808,-2.2426,Manchester DC
51.5074,-0.1278,London DC
...
```

---

## 🚀 Quick Start with CSV

### 1. Test with Small Dataset (10 locations)

```bash
# Use the included sample
python test_ml_endpoint.py existing_datacenters.csv
```

### 2. Test with Medium Dataset (100-500 locations)

```bash
# Generate 500 synthetic locations
python generate_large_dataset.py 500 medium_dataset.csv

# Test the ML system
python test_ml_endpoint.py medium_dataset.csv
```

### 3. Test with Large Dataset (1000+ locations)

```bash
# Generate 1500 synthetic locations
python generate_large_dataset.py 1500 large_dataset.csv

# Test the ML system (will take longer)
python test_ml_endpoint.py large_dataset.csv
```

---

## 📊 Performance Characteristics

### Expected Processing Times

| Dataset Size | Generation Time | ML Processing Time | Total Time |
|--------------|----------------|--------------------| -----------|
| 10 locations | < 1s | ~2-3s | ~3-5s |
| 50 locations | < 1s | ~3-5s | ~5-7s |
| 100 locations | < 1s | ~5-8s | ~7-10s |
| 500 locations | ~2s | ~15-25s | ~20-30s |
| 1000 locations | ~3s | ~30-50s | ~35-55s |
| 1500 locations | ~4s | ~45-75s | ~50-80s |

*Times approximate - depends on system performance and infrastructure data size*

### Scalability Characteristics

The system exhibits **sub-linear scaling** for training data:
- 10x increase in training data → ~5-7x increase in processing time
- Batch processing optimization reduces per-location overhead
- Infrastructure spatial indexing keeps lookup times constant

### Performance Bottlenecks

1. **Infrastructure proximity calculation** - O(n) per location
2. **Network I/O to Supabase** - Cached after first load
3. **Composite score calculation** - O(n) for all candidates

---

## 🧪 Running Scalability Tests

### Automated Testing

Test multiple dataset sizes automatically:

```bash
python test_scalability.py
```

This will:
1. Generate datasets of sizes: 10, 50, 100, 500, 1000, 1500
2. Test each with the ML API
3. Measure generation and processing times
4. Analyze scalability characteristics
5. Save results to `scalability_test_results.json`

### Manual Testing

Test specific dataset size:

```bash
# Generate dataset
python generate_large_dataset.py 2000 custom_dataset.csv

# Test performance
time python test_ml_endpoint.py custom_dataset.csv
```

---

## ⚙️ Optimization Tips

### For Large Datasets (1000+ locations)

#### 1. **Reduce Candidate Locations**

The test script auto-adjusts, but you can override:

```python
# In test_ml_endpoint.py, modify:
num_candidates = 50  # Instead of default 100
```

**Trade-off**: Fewer candidates = faster processing, less comprehensive coverage

#### 2. **Batch Processing**

The API uses batch processing by default. For very large datasets, consider:

```python
# Process in chunks
chunk_size = 500
for i in range(0, len(all_locations), chunk_size):
    chunk = all_locations[i:i+chunk_size]
    # Send to API
```

#### 3. **Increase Timeout**

```python
# In test_ml_endpoint.py
response = requests.post(url, json=payload, timeout=300)  # 5 minutes
```

#### 4. **Filter Duplicates**

The test script auto-deduplicates. Ensure your CSV doesn't have many duplicates:

```bash
# Check for duplicates
awk -F',' '{print $5","$4}' your_dataset.csv | sort | uniq -c | sort -rn | head
```

---

## 📈 CSV Data Quality

### Best Practices

1. **Remove Invalid Coordinates**
   - Latitude: -90 to 90 (UK: ~50 to 60)
   - Longitude: -180 to 180 (UK: ~-8 to 2)

2. **Deduplicate Locations**
   - Locations within 100m treated as duplicates
   - Test script handles this automatically

3. **Validate Names**
   - Use descriptive facility names
   - Avoid special characters that break CSV parsing

4. **Consistent Formatting**
   - Use UTF-8 encoding
   - Use comma delimiters
   - Escape commas in facility names with quotes

### Validation Script

```python
import csv

def validate_csv(filepath):
    """Validate data center CSV file"""
    valid_count = 0
    invalid_count = 0

    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, 1):
            try:
                lat = float(row.get('Latitude', row.get('latitude', 0)))
                lon = float(row.get('Longitude', row.get('longitude', 0)))

                if not (50 <= lat <= 60):
                    print(f"Row {i}: Invalid latitude {lat}")
                    invalid_count += 1
                    continue

                if not (-8 <= lon <= 2):
                    print(f"Row {i}: Invalid longitude {lon}")
                    invalid_count += 1
                    continue

                valid_count += 1

            except (ValueError, KeyError) as e:
                print(f"Row {i}: Parse error - {e}")
                invalid_count += 1

    print(f"\n✅ Valid: {valid_count}")
    print(f"❌ Invalid: {invalid_count}")
    print(f"📊 Quality: {valid_count/(valid_count+invalid_count)*100:.1f}%")

# Usage
validate_csv("your_dataset.csv")
```

---

## 🔧 Advanced Usage

### Custom CSV Headers

If your CSV has different column names, update the loading function:

```python
# In test_ml_endpoint.py, modify load_datacenters_from_csv():

lat = float(row.get('your_lat_column', 0))
lon = float(row.get('your_lon_column', 0))
name = row.get('your_name_column', 'Unknown')
```

### Combining Multiple CSV Files

```bash
# Combine multiple CSV files (skip headers after first)
cat file1.csv > combined.csv
tail -n +2 file2.csv >> combined.csv
tail -n +2 file3.csv >> combined.csv

# Test combined dataset
python test_ml_endpoint.py combined.csv
```

### Export Recommendations to CSV

```python
import json
import csv

# Load results
with open('ml_recommendations.json', 'r') as f:
    results = json.load(f)

# Export to CSV
with open('recommended_locations.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=[
        'latitude', 'longitude', 'composite_score',
        'recommendation', 'percentile_rank'
    ])
    writer.writeheader()

    for rec in results['top_recommendations']:
        writer.writerow({
            'latitude': rec['latitude'],
            'longitude': rec['longitude'],
            'composite_score': rec['composite_score'],
            'recommendation': rec['recommendation'],
            'percentile_rank': rec['percentile_rank']
        })
```

---

## 📊 Real-World Dataset Examples

### Example 1: UK Data Center Census (100+ locations)

If you have a real UK data center census:

```bash
# Test with real data
python test_ml_endpoint.py uk_datacenter_census_2024.csv

# Adjust candidates for thorough analysis
# Edit test_ml_endpoint.py:
num_candidates = 500  # More comprehensive
top_n = 50           # Get more recommendations
```

### Example 2: Global Data Centers (Filtered to UK)

```bash
# Pre-filter to UK bounds using awk
awk -F',' 'NR==1 || ($5 >= 50 && $5 <= 60 && $4 >= -8 && $4 <= 2)' \
    global_datacenters.csv > uk_only.csv

# Test
python test_ml_endpoint.py uk_only.csv
```

### Example 3: Multi-Tenant Facilities Only

Filter your CSV before testing:

```bash
# Filter for specific facility types
grep -i "colocation\|multi-tenant" all_datacenters.csv > colocation_only.csv

python test_ml_endpoint.py colocation_only.csv
```

---

## 🐛 Troubleshooting

### Issue: "No valid data centers found in CSV"

**Causes:**
- Column names don't match expected format
- Coordinates are zero/null
- CSV encoding issues

**Solution:**
```bash
# Check CSV structure
head -5 your_file.csv

# Verify column names
head -1 your_file.csv

# Check for null coordinates
awk -F',' '$4 == 0 || $5 == 0 {print NR, $0}' your_file.csv | head
```

### Issue: "Request timed out"

**Causes:**
- Too many training locations (1000+)
- Too many candidates to evaluate
- Slow network to Supabase

**Solutions:**
1. Reduce candidates: `num_candidates = 50`
2. Increase timeout: `timeout=300`
3. Process in batches
4. Check Supabase connection

### Issue: "Memory error"

**Cause:** Extremely large dataset (10,000+ locations)

**Solution:**
```python
# Process in chunks
chunk_size = 1000
for i in range(0, len(locations), chunk_size):
    chunk = locations[i:i+chunk_size]
    # Process chunk
```

---

## 📚 Additional Resources

### Related Files
- `test_ml_endpoint.py` - Main CSV testing script
- `generate_large_dataset.py` - Synthetic dataset generator
- `test_scalability.py` - Automated scalability testing
- `ML_DATACENTER_LOCATIONS_README.md` - Main documentation

### API Documentation
See main README for:
- API endpoint details
- Request/response formats
- Feature weight customization

### Support

For issues or questions:
1. Check CSV format matches expected structure
2. Validate coordinates are within UK bounds
3. Test with small dataset first (10-50 locations)
4. Review console output for specific errors

---

## ✅ Quick Reference

```bash
# Test with existing CSV
python test_ml_endpoint.py your_file.csv

# Generate test dataset
python generate_large_dataset.py 1000 test_1000.csv

# Run scalability tests
python test_scalability.py

# Validate CSV format
head -5 your_file.csv
```

**Expected Performance (1000 locations):**
- Generation: ~3s
- ML Processing: ~40s
- Total: ~45s

**Optimal Dataset Size:** 50-500 locations for best performance/accuracy balance
