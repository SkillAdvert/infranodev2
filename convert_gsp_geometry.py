#!/usr/bin/env python3
"""
Convert GSP boundaries from PostGIS geometry to GeoJSON format.

This script:
1. Fetches GSP boundaries from electrical_grid table
2. Converts PostGIS geometry to GeoJSON using ST_AsGeoJSON
3. Creates a new gsp_boundaries table with JSON geometry (matching dno_license_areas pattern)
4. Inserts the converted data

Usage:
    python convert_gsp_geometry.py
"""

import os
import asyncio
import httpx
from typing import Any, Dict, List
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")


async def fetch_gsp_with_geojson() -> List[Dict[str, Any]]:
    """Fetch GSP boundaries with geometry converted to GeoJSON."""

    # Use PostgREST to call a custom query with ST_AsGeoJSON
    # We'll use the select parameter with a custom column
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Prefer": "return=representation"
    }

    # First, let's try to fetch using rpc if the function exists
    # If not, we'll create the table structure

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Try to call the RPC function first
        try:
            response = await client.post(
                f"{SUPABASE_URL}/rest/v1/rpc/get_gsp_boundaries_geojson",
                headers=headers
            )

            if response.status_code == 200:
                print("✅ RPC function exists, using it for conversion")
                return response.json()
        except Exception as e:
            print(f"⚠️ RPC function not available: {e}")

        # Alternative: Fetch raw data and we'll need to convert differently
        print("📊 Fetching raw GSP data from electrical_grid...")
        response = await client.get(
            f"{SUPABASE_URL}/rest/v1/electrical_grid?type=eq.gsp_boundary&select=*",
            headers=headers
        )

        if response.status_code != 200:
            raise Exception(f"Failed to fetch data: {response.status_code} - {response.text}")

        raw_data = response.json()
        print(f"📦 Fetched {len(raw_data)} raw GSP records")

        return raw_data


async def create_gsp_boundaries_table() -> None:
    """Create gsp_boundaries table with JSONB geometry (like dno_license_areas)."""

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }

    # SQL to create table
    sql = """
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
    """

    print("🔨 Creating gsp_boundaries table...")

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Note: Direct SQL execution requires the SQL endpoint or RPC
        # For now, let's provide the SQL for manual execution

        print("\n" + "="*80)
        print("📋 EXECUTE THIS SQL IN SUPABASE DASHBOARD:")
        print("="*80)
        print(sql)
        print("="*80 + "\n")

        return sql


async def verify_conversion() -> None:
    """Verify the gsp_boundaries table has correct data."""

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{SUPABASE_URL}/rest/v1/gsp_boundaries?select=*",
            headers=headers
        )

        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Verification successful!")
            print(f"   Found {len(data)} GSP boundaries")

            if data:
                print(f"\n📊 Sample record:")
                sample = data[0]
                print(f"   ID: {sample.get('id')}")
                print(f"   Name: {sample.get('name')}")
                print(f"   Operator: {sample.get('operator')}")
                print(f"   Geometry type: {sample.get('geometry', {}).get('type')}")

                # Check if geometry is valid GeoJSON
                geom = sample.get('geometry')
                if isinstance(geom, dict) and 'type' in geom and 'coordinates' in geom:
                    print(f"   ✅ Geometry is valid GeoJSON")
                else:
                    print(f"   ❌ Geometry is NOT valid GeoJSON: {type(geom)}")

            return data
        else:
            print(f"\n❌ Verification failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None


async def main():
    print("🚀 GSP Geometry Conversion Tool\n")

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Error: SUPABASE_URL and SUPABASE_KEY must be set in .env file")
        return

    print(f"🔗 Supabase URL: {SUPABASE_URL}\n")

    # Step 1: Generate SQL for table creation
    sql = await create_gsp_boundaries_table()

    print("\n📝 Next steps:")
    print("1. Copy the SQL above")
    print("2. Go to Supabase Dashboard → SQL Editor")
    print("3. Paste and execute the SQL")
    print("4. Run this script again with --verify flag to check the data")
    print("5. Update the endpoint in main.py to use 'gsp_boundaries' table")

    # Save SQL to file
    with open("backend/migrations/create_gsp_boundaries_table.sql", "w") as f:
        f.write(sql)

    print(f"\n💾 SQL saved to: backend/migrations/create_gsp_boundaries_table.sql")


if __name__ == "__main__":
    import sys

    if "--verify" in sys.argv:
        asyncio.run(verify_conversion())
    else:
        asyncio.run(main())
