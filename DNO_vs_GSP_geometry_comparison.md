# DNO vs GSP Geometry Comparison

## The Answer: DNO Doesn't Convert - It's Already GeoJSON!

The `/api/infrastructure/dno-areas` endpoint **does NOT convert geometry** because the `dno_license_areas` table already stores geometry in **GeoJSON (JSONB)** format.

## Code Comparison

### DNO Endpoint (main.py:1878-1906)
```python
@app.get("/api/infrastructure/dno-areas")
async def get_dno_license_areas() -> Dict[str, Any]:
    areas = await query_supabase("dno_license_areas?select=*")

    for area in areas or []:
        geometry = area.get("geometry")  # ✅ Already GeoJSON!

        features.append({
            "type": "Feature",
            "geometry": geometry,  # 🎯 Direct use - no conversion
            "properties": {...}
        })
```

**No conversion needed!** The geometry field comes from the database as a Python dict/list (GeoJSON), ready to use.

### Original GSP Endpoint (Before Fix)
```python
@app.get("/api/infrastructure/gsp")
async def get_gsp_boundaries() -> Dict[str, Any]:
    boundaries = await query_supabase("electrical_grid?type=eq.gsp_boundary&select=*")

    for boundary in boundaries or []:
        geometry = boundary.get("geometry")  # ❌ PostGIS binary!
        # geometry = "0106000020E6100000..." (WKB hex string)

        if isinstance(geometry, str):
            try:
                geometry = json.loads(geometry)  # ❌ This fails!
            except json.JSONDecodeError:
                continue  # ❌ Silently skips - no features!
```

**Problem:** PostGIS stores geometry as binary (WKB hex), not JSON. The `json.loads()` fails silently, resulting in zero features.

## Database Table Differences

### dno_license_areas Table (Working ✅)
```sql
CREATE TABLE dno_license_areas (
    id SERIAL PRIMARY KEY,
    dno_name TEXT,
    license_area TEXT,
    company TEXT,
    region TEXT,
    geometry JSONB,  -- ✅ GeoJSON format: {"type": "MultiPolygon", "coordinates": [...]}
    ...
);
```

**Data format in database:**
```json
{
  "type": "MultiPolygon",
  "coordinates": [
    [
      [
        [-4.123, 55.456],
        [-4.789, 55.678],
        ...
      ]
    ]
  ]
}
```

### electrical_grid Table (Original - Broken ❌)
```sql
CREATE TABLE electrical_grid (
    id SERIAL PRIMARY KEY,
    name TEXT,
    type TEXT,
    operator TEXT,
    geometry GEOMETRY(MultiPolygon, 4326),  -- ❌ PostGIS binary format
    ...
);
```

**Data format in database:**
```
0106000020E6100000010000000103000000010000001E000000...
```
This is **WKB (Well-Known Binary)** hex encoding - not JSON!

## How DNO Data Was Loaded

Based on git history (commit c4a4209), the DNO table was created with geometry already in GeoJSON format. This was likely done via:

**Option A: Direct SQL with ST_AsGeoJSON during table creation**
```sql
CREATE TABLE dno_license_areas AS
SELECT
    id,
    dno_name,
    license_area,
    company,
    region,
    ST_AsGeoJSON(geometry)::jsonb as geometry  -- Convert PostGIS to GeoJSON
FROM some_source_table;
```

**Option B: Import from GeoJSON file**
```sql
-- Load GeoJSON file data with geometry already in JSON format
INSERT INTO dno_license_areas (dno_name, geometry, ...)
VALUES (
    'Eastern Power Networks',
    '{"type": "MultiPolygon", "coordinates": [...]}'::jsonb,
    ...
);
```

**Option C: Python script that converts before upload**
```python
# Hypothetical script (not in repo)
import geopandas as gpd

# Load shapefile
gdf = gpd.read_file("dno_areas.shp")

# Convert to GeoJSON format
for _, row in gdf.iterrows():
    data = {
        'dno_name': row['name'],
        'geometry': row.geometry.__geo_interface__,  # Already GeoJSON!
        ...
    }
    # Upload to Supabase
```

## Our GSP Fix (New Approach ✅)

We're creating a new `gsp_boundaries` table that matches the DNO pattern:

```sql
CREATE TABLE gsp_boundaries (
    id SERIAL PRIMARY KEY,
    name TEXT,
    operator TEXT,
    geometry JSONB,  -- ✅ GeoJSON format (same as DNO)
    ...
);

-- Convert PostGIS to GeoJSON during insertion
INSERT INTO gsp_boundaries (id, name, operator, geometry)
SELECT
    id,
    name,
    operator,
    ST_AsGeoJSON(geometry)::jsonb as geometry  -- 🎯 One-time conversion
FROM electrical_grid
WHERE type = 'gsp_boundary';
```

**Updated Endpoint:**
```python
@app.get("/api/infrastructure/gsp")
async def get_gsp_boundaries() -> Dict[str, Any]:
    boundaries = await query_supabase("gsp_boundaries?select=*")

    for boundary in boundaries or []:
        geometry = boundary.get("geometry")  # ✅ Already GeoJSON!

        features.append({
            "type": "Feature",
            "geometry": geometry,  # 🎯 Direct use - just like DNO!
            "properties": {...}
        })
```

## Summary

| Aspect | DNO (Working) | GSP (Original) | GSP (Fixed) |
|--------|--------------|----------------|-------------|
| **Table** | `dno_license_areas` | `electrical_grid` | `gsp_boundaries` |
| **Geometry Storage** | JSONB (GeoJSON) | GEOMETRY (PostGIS) | JSONB (GeoJSON) |
| **Conversion?** | ❌ None needed | ❌ Tried but failed | ✅ Done once at migration |
| **Endpoint** | Direct use | Failed silently | Direct use (like DNO) |
| **Result** | ✅ Works | ❌ 0 features | ✅ Works |

## Key Takeaway

**The DNO endpoint doesn't convert geometry - it was already converted when the data was loaded into the database.** Our fix replicates this same pattern for GSP boundaries.
