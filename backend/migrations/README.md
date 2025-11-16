# Database Migrations

## GSP Boundaries Table Migration

### Purpose
This migration creates a new `gsp_boundaries` table with geometry stored in GeoJSON format, converted from the PostGIS geometry in the `electrical_grid` table.

### Problem
The `electrical_grid` table stores geometry as PostGIS MULTIPOLYGON (binary WKB format like `0106000020E6100000...`), which cannot be directly used by the frontend map. The geometry needs to be converted to GeoJSON format.

### Solution
Create a new table `gsp_boundaries` that:
1. Stores geometry in JSONB format (GeoJSON)
2. Matches the pattern used by `dno_license_areas` table
3. Makes the API endpoint simpler (no conversion needed at runtime)

## Migration Options

### Option 1: Quick Migration (Recommended)

Run the SQL script directly in Supabase Dashboard:

1. Go to your Supabase project dashboard
2. Navigate to **SQL Editor**
3. Copy the contents of `create_gsp_boundaries_table.sql`
4. Run the SQL query
5. Verify with the queries below

### Option 2: Using Python Script

Use the provided Python script to generate and verify the migration:

```bash
# Generate the SQL (already generated in create_gsp_boundaries_table.sql)
python convert_gsp_geometry.py

# After running the SQL in Supabase, verify:
python convert_gsp_geometry.py --verify
```

### Option 3: Using psql

```bash
psql -h <your-supabase-host> -U postgres -d postgres -f backend/migrations/create_gsp_boundaries_table.sql
```

## What the Migration Does

The SQL script:
1. Drops existing `gsp_boundaries` table if it exists
2. Creates new table with JSONB geometry field
3. Enables Row Level Security (RLS)
4. Creates public read access policy
5. Inserts data from `electrical_grid` with geometry converted using `ST_AsGeoJSON()`

## Verification

After applying the migration, test the endpoint:

```bash
# Should return 4 features
curl https://infranodev2.onrender.com/api/infrastructure/gsp | jq '.features | length'
# Expected: 4

# Check first feature has proper geometry
curl https://infranodev2.onrender.com/api/infrastructure/gsp | jq '.features[0].geometry.type'
# Expected: "MultiPolygon"

# Check that properties are present
curl https://infranodev2.onrender.com/api/infrastructure/gsp | jq '.features[0].properties'
# Expected: {"id": 7451, "name": "GSP", "operator": "NESO", "type": "gsp_boundary"}

# Verify all 4 features have valid geometry
curl https://infranodev2.onrender.com/api/infrastructure/gsp | jq '.features[].geometry.type'
# Expected: 4 lines of "MultiPolygon"
```

Or verify directly in the database:

```sql
-- Check table exists and has data
SELECT COUNT(*) FROM gsp_boundaries;
-- Expected: 4

-- Check geometry format
SELECT id, name, geometry->>'type' as geom_type
FROM gsp_boundaries;
-- Expected: All rows should have geom_type = 'MultiPolygon'
```

## Rollback

To remove the table if needed:

```sql
DROP TABLE IF EXISTS gsp_boundaries CASCADE;
```

To revert to using `electrical_grid` table:
1. Drop the `gsp_boundaries` table
2. Update `main.py` endpoint to query `electrical_grid` instead
3. You'll need to implement geometry conversion in the endpoint

## Files

- `create_gsp_boundaries_table.sql` - SQL migration script
- `create_gsp_geojson_function.sql` - Alternative RPC function approach (not used)
- `convert_gsp_geometry.py` - Python script to help with migration
