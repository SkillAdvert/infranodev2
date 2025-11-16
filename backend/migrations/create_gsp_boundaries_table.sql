-- Drop existing table if it exists
DROP TABLE IF EXISTS gsp_boundaries CASCADE;

-- Create new table with JSONB geometry
CREATE TABLE gsp_boundaries (
    id SERIAL PRIMARY KEY,
    name TEXT,
    type TEXT DEFAULT 'gsp_boundary',
    operator TEXT DEFAULT 'NESO',
    geometry JSONB,  -- GeoJSON format
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS if needed
ALTER TABLE gsp_boundaries ENABLE ROW LEVEL SECURITY;

-- Create policy to allow public read access
CREATE POLICY "Allow public read access"
    ON gsp_boundaries
    FOR SELECT
    TO anon, authenticated
    USING (true);

-- Insert data from electrical_grid with geometry conversion
INSERT INTO gsp_boundaries (id, name, type, operator, geometry)
SELECT
    id,
    name,
    type,
    operator,
    ST_AsGeoJSON(geometry)::jsonb as geometry
FROM electrical_grid
WHERE type = 'gsp_boundary';
