"""Supabase client helpers."""
from typing import Any, Dict, Optional

import httpx

from core.config import get_settings


class SupabaseClient:
    """Lightweight async client for Supabase REST endpoints."""

    def __init__(self, *, url: Optional[str] = None, key: Optional[str] = None) -> None:
        settings = get_settings()
        self._url = url or settings.supabase_url
        self._key = key or settings.supabase_key

    @property
    def is_configured(self) -> bool:
        return bool(self._url and self._key)

    async def fetch(self, endpoint: str) -> Any:
        if not self.is_configured:
            raise RuntimeError("Supabase credentials not configured")

        headers: Dict[str, str] = {
            "apikey": str(self._key),
            "Authorization": f"Bearer {self._key}",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{self._url}/rest/v1/{endpoint}", headers=headers)
            if response.status_code == 200:
                return response.json()
            raise RuntimeError(
                f"Supabase error {response.status_code}: {response.text[:200]}"
            )
