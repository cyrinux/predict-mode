from __future__ import annotations

import asyncio
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

STORAGE_VERSION = 1
MAX_RUNS = 60


class PatternStorage:
    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store = Store(hass, STORAGE_VERSION, f"appliance_patterns_{entry_id}.json")
        self._lock = asyncio.Lock()
        self._data: dict[str, Any] = {"runs": [], "patterns": []}

    async def async_load(self) -> dict[str, Any]:
        async with self._lock:
            raw = await self._store.async_load()
            if raw:
                self._data = raw
        return self._data

    def get_runs(self) -> list[dict[str, Any]]:
        return list(self._data.get("runs", []))

    def get_patterns(self) -> list[dict[str, Any]]:
        return list(self._data.get("patterns", []))

    async def async_append_run(self, run: dict[str, Any]) -> None:
        async with self._lock:
            runs: list[dict[str, Any]] = self._data.setdefault("runs", [])
            runs.append(run)
            if len(runs) > MAX_RUNS:
                del runs[0 : len(runs) - MAX_RUNS]
            await self._store.async_save(self._data)

    async def async_set_patterns(self, patterns: list[dict[str, Any]]) -> None:
        async with self._lock:
            self._data["patterns"] = patterns
            await self._store.async_save(self._data)

    async def async_reset(self) -> None:
        async with self._lock:
            self._data = {"runs": [], "patterns": []}
            await self._store.async_save(self._data)

    async def async_import(self, payload: dict[str, Any]) -> None:
        async with self._lock:
            runs = payload.get("runs", [])
            patterns = payload.get("patterns", [])
            self._data = {
                "runs": runs[-MAX_RUNS:],
                "patterns": patterns,
            }
            await self._store.async_save(self._data)

    def export(self) -> dict[str, Any]:
        return {"runs": self.get_runs(), "patterns": self.get_patterns()}
