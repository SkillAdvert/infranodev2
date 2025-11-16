-- RPC function to return GSP boundaries as GeoJSON
-- This function converts PostGIS geometry to GeoJSON format

CREATE OR REPLACE FUNCTION get_gsp_boundaries_geojson()
RETURNS TABLE (
  id INTEGER,
  name TEXT,
  type TEXT,
  operator TEXT,
  geometry_json JSONB
)
LANGUAGE SQL
STABLE
AS $$
  SELECT
    id,
    name,
    type,
    operator,
    ST_AsGeoJSON(geometry)::jsonb as geometry_json
  FROM electrical_grid
  WHERE type = 'gsp_boundary';
$$;

-- Grant execute permission to authenticated and anonymous users
GRANT EXECUTE ON FUNCTION get_gsp_boundaries_geojson() TO anon, authenticated;
