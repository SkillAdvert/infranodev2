from __future__ import annotations

import os
from typing import Any, List, Optional

import httpx
from fastapi import HTTPException

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")


async def query_supabase(
    endpoint: str, *, limit: Optional[int] = None, page_size: int = 1000
) -> Any:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise HTTPException(500, "Supabase credentials not configured")

    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}

    if limit is not None and limit <= 0:
        return []

    def append_limit(query: str, limit_value: int) -> str:
        separator = "&" if "?" in query else "?"
        return f"{query}{separator}limit={limit_value}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        if limit is None or limit <= page_size:
            endpoint_with_limit = append_limit(endpoint, limit) if limit is not None else endpoint
            response = await client.get(
                f"{SUPABASE_URL}/rest/v1/{endpoint_with_limit}", headers=headers
            )
            if response.status_code == 200:
                return response.json()
            error_message = f"Database error: {response.status_code}"
            print(f"Error querying Supabase for {endpoint_with_limit}: {error_message}")
            raise HTTPException(500, error_message)

        assert limit is not None
        aggregated_results: List[Any] = []
        offset = 0

        while len(aggregated_results) < limit:
            chunk_size = min(page_size, limit - len(aggregated_results))
            endpoint_with_pagination = f"{endpoint}&offset={offset}&limit={chunk_size}"

            response = await client.get(
                f"{SUPABASE_URL}/rest/v1/{endpoint_with_pagination}",
                headers=headers,
            )

            if response.status_code != 200:
                error_message = f"Database error: {response.status_code}"
                print(f"Error paginating Supabase at offset {offset}: {error_message}")
                raise HTTPException(500, error_message)

            chunk = response.json()

            if not isinstance(chunk, list):
                return chunk

            if not chunk:
                print(f"   Empty response at offset {offset} - end of data")
                break

            aggregated_results.extend(chunk)
            print(
                f"   Fetched {len(chunk)} rows at offset {offset} (total: {len(aggregated_results)}/{limit})"
            )

            if len(chunk) < chunk_size:
                print(f"   Reached end of data at offset {offset}")
                break

            offset += chunk_size

        print(f"   ✓ Retrieved {len(aggregated_results)} total records")
        return aggregated_results


__all__ = ["SUPABASE_URL", "SUPABASE_KEY", "query_supabase"]
