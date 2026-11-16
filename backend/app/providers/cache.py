"""Bounded async provider cache with distinct success/failure TTLs and stale-if-error."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Awaitable, Callable, Generic, TypeVar

from .contracts import ProviderProvenance, ProviderResult

LOGGER = logging.getLogger("jujosmi_trade_api.providers")
T = TypeVar("T")


@dataclass(frozen=True)
class CachePolicy:
    success_ttl_seconds: float = 300.0
    failure_ttl_seconds: float = 5.0
    stale_if_error_seconds: float = 900.0
    max_entries: int = 256
    timeout_seconds: float = 3.0

    def __post_init__(self) -> None:
        if self.success_ttl_seconds < 0 or self.failure_ttl_seconds < 0 or self.stale_if_error_seconds < 0:
            raise ValueError("Cache durations cannot be negative.")
        if self.max_entries < 1:
            raise ValueError("max_entries must be positive.")
        if not 0 < self.timeout_seconds <= 15:
            raise ValueError("timeout_seconds must be greater than zero and at most 15.")


@dataclass
class _Entry(Generic[T]):
    result: ProviderResult[T]
    expires_at: float
    last_success: ProviderResult[T] | None
    stale_until: float


class ProviderCache:
    """Process-local cache for public provider results, never private user data."""

    def __init__(self, policy: CachePolicy | None = None, clock: Callable[[], float] = time.monotonic):
        self.policy = policy or CachePolicy()
        self._clock = clock
        self._entries: OrderedDict[str, _Entry] = OrderedDict()

    @staticmethod
    def cache_key(provider_id: str, operation: str, parameters: dict) -> str:
        canonical = json.dumps(parameters, sort_keys=True, separators=(",", ":"), default=str)
        raw = f"{provider_id}\0{operation}\0{canonical}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def invalidate(self, provider_id: str, operation: str, parameters: dict) -> bool:
        """Invalidate only one canonical provider request key."""
        return self._entries.pop(self.cache_key(provider_id, operation, parameters), None) is not None

    def invalidate_provider(self, provider_id: str) -> int:
        """Clear one provider's entries while leaving other providers untouched."""
        keys = [key for key, entry in self._entries.items() if entry.result.provenance.provider_id == provider_id]
        for key in keys:
            del self._entries[key]
        return len(keys)

    async def get_or_load(
        self,
        provider_id: str,
        operation: str,
        parameters: dict,
        loader: Callable[[], Awaitable[ProviderResult[T]]],
        provenance: ProviderProvenance,
    ) -> ProviderResult[T]:
        key = self.cache_key(provider_id, operation, parameters)
        now = self._clock()
        entry = self._entries.get(key)
        if entry is not None:
            self._entries.move_to_end(key)
            if now < entry.expires_at:
                return self._stale(entry.last_success) if entry.result.data is None and entry.last_success and now <= entry.stale_until else entry.result
        previous_success = entry.last_success if entry else None
        try:
            result = await asyncio.wait_for(loader(), timeout=self.policy.timeout_seconds)
        except asyncio.TimeoutError:
            result = ProviderResult[T](data=None, status="failed", provenance=provenance,
                                       warnings=["Provider request timed out."])
        except Exception as exc:
            LOGGER.warning("Provider request failed: provider=%s operation=%s error_type=%s", provider_id, operation, type(exc).__name__)
            result = ProviderResult[T](data=None, status="failed", provenance=provenance,
                                       warnings=["Provider data is temporarily unavailable."])

        now = self._clock()
        is_success = result.data is not None and result.status in {"ok", "partial"}
        if is_success:
            previous_success = result
            ttl = self.policy.success_ttl_seconds
            stale_until = now + ttl + self.policy.stale_if_error_seconds
        else:
            ttl = self.policy.failure_ttl_seconds
            stale_until = entry.stale_until if entry else now
        stored = _Entry(result=result, expires_at=now + ttl, last_success=previous_success, stale_until=stale_until)
        self._entries[key] = stored
        self._entries.move_to_end(key)
        while len(self._entries) > self.policy.max_entries:
            self._entries.popitem(last=False)
        if not is_success and previous_success is not None and now <= stale_until:
            return self._stale(previous_success)
        return result

    @staticmethod
    def _stale(result: ProviderResult[T] | None) -> ProviderResult[T] | None:
        if result is None:
            return None
        warning = "A temporary provider issue occurred; showing the last successful result as stale."
        return result.model_copy(update={"status": "partial", "stale": True,
                                         "warnings": list(dict.fromkeys([*result.warnings, warning]))})
