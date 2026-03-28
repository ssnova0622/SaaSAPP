"""
Optional Redis cache. If REDIS_URI is not set, all operations are no-ops.
Use for tenant settings, session data, or other frequently read data.
"""
from __future__ import annotations
import json
from datetime import datetime
from typing import Any, Optional

TENANT_SETTINGS_TTL = 300


def _default_encoder(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    try:
        from bson import ObjectId
        if isinstance(obj, ObjectId):
            return str(obj)
    except ImportError:
        pass
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


class _NoOpCache:
    def get(self, key: str) -> Optional[str]:
        return None

    def set(self, key: str, value: str, ttl_seconds: Optional[int] = None) -> None:
        pass

    def delete(self, key: str) -> None:
        pass


class _RedisCache:
    def __init__(self, redis_client: Any) -> None:
        self._client = redis_client

    def get(self, key: str) -> Optional[str]:
        try:
            return self._client.get(key)
        except Exception:
            return None

    def set(self, key: str, value: str, ttl_seconds: Optional[int] = None) -> None:
        try:
            self._client.set(key, value, ex=ttl_seconds or 0)
        except Exception:
            pass

    def delete(self, key: str) -> None:
        try:
            self._client.delete(key)
        except Exception:
            pass


_cache: Optional[_RedisCache] = None


def get_cache() -> Any:
    """Return cache implementation. Uses Redis if REDIS_URI is set, else no-op."""
    global _cache
    if _cache is not None:
        return _cache
    try:
        from settings import env
        uri = env.str("REDIS_URI", "").strip()
        if not uri:
            return _NoOpCache()
        import redis
        client = redis.from_url(uri, decode_responses=True)
        client.ping()
        _cache = _RedisCache(client)
        return _cache
    except Exception:
        return _NoOpCache()


def cache_get_tenant_settings(tenant: str) -> Optional[dict]:
    """Get tenant settings from cache. Returns None on miss or error."""
    cache = get_cache()
    key = f"tenant_settings:{tenant}"
    raw = cache.get(key)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        cache.delete(key)
        return None


def cache_set_tenant_settings(tenant: str, doc: dict, ttl_seconds: int = TENANT_SETTINGS_TTL) -> None:
    """Store tenant settings in cache."""
    cache = get_cache()
    key = f"tenant_settings:{tenant}"
    try:
        cache.set(key, json.dumps(doc, default=_default_encoder), ttl_seconds=ttl_seconds)
    except Exception:
        pass


def cache_delete_tenant_settings(tenant: str) -> None:
    """Invalidate cached tenant settings (call after update or delete)."""
    get_cache().delete(f"tenant_settings:{tenant}")


# List tenants (full list for super_admin; filtered in router). TTL 120s.
LIST_TENANTS_TTL = 120
LIST_TENANTS_KEY = "list_tenants"


def cache_get_list_tenants() -> Optional[list]:
    """Get cached list of tenants. Returns None on miss or error."""
    cache = get_cache()
    raw = cache.get(LIST_TENANTS_KEY)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        cache.delete(LIST_TENANTS_KEY)
        return None


def cache_set_list_tenants(data: list, ttl_seconds: int = LIST_TENANTS_TTL) -> None:
    """Store list of tenants in cache."""
    cache = get_cache()
    try:
        cache.set(LIST_TENANTS_KEY, json.dumps(data, default=_default_encoder), ttl_seconds=ttl_seconds)
    except Exception:
        pass


def cache_delete_list_tenants() -> None:
    """Invalidate list_tenants cache (call after tenant create or delete)."""
    get_cache().delete(LIST_TENANTS_KEY)


# User by ID. TTL 120s. Invalidate on user update/delete.
USER_TTL = 120


def cache_get_user(user_id: str) -> Optional[dict]:
    """Get cached user doc by id. Returns None on miss or error."""
    cache = get_cache()
    key = f"user:{user_id}"
    raw = cache.get(key)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        cache.delete(key)
        return None


def cache_set_user(user_id: str, doc: dict, ttl_seconds: int = USER_TTL) -> None:
    """Store user doc in cache. Caller should strip password_hash before caching."""
    cache = get_cache()
    key = f"user:{user_id}"
    try:
        cache.set(key, json.dumps(doc, default=_default_encoder), ttl_seconds=ttl_seconds)
    except Exception:
        pass


def cache_delete_user(user_id: str) -> None:
    """Invalidate user cache (call after user update or delete)."""
    get_cache().delete(f"user:{user_id}")


# Default message bundle (MongoDB ``default_message`` collection). TTL 300s.
DEFAULT_MESSAGE_BUNDLE_TTL = 300
DEFAULT_MESSAGE_BUNDLE_KEY = "default_message_bundle"


def cache_get_default_message_bundle() -> Optional[dict]:
    cache = get_cache()
    raw = cache.get(DEFAULT_MESSAGE_BUNDLE_KEY)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        cache.delete(DEFAULT_MESSAGE_BUNDLE_KEY)
        return None


def cache_set_default_message_bundle(data: dict, ttl_seconds: int = DEFAULT_MESSAGE_BUNDLE_TTL) -> None:
    cache = get_cache()
    try:
        cache.set(
            DEFAULT_MESSAGE_BUNDLE_KEY,
            json.dumps(data, default=_default_encoder),
            ttl_seconds=ttl_seconds,
        )
    except Exception:
        pass


def cache_delete_default_message_bundle() -> None:
    get_cache().delete(DEFAULT_MESSAGE_BUNDLE_KEY)


def cache_invalidate_all_tenant_settings() -> None:
    """Drop all cached tenant settings (e.g. after platform default_message update). No-op without Redis."""
    cache = get_cache()
    if isinstance(cache, _NoOpCache):
        return
    try:
        for k in cache._client.scan_iter(match="tenant_settings:*"):
            cache.delete(k)
    except Exception:
        pass


# Backward compatibility (deprecated — use default_message_*).
def cache_get_whatsapp_platform() -> Optional[dict]:
    return cache_get_default_message_bundle()


def cache_set_whatsapp_platform(data: dict, ttl_seconds: int = DEFAULT_MESSAGE_BUNDLE_TTL) -> None:
    cache_set_default_message_bundle(data, ttl_seconds=ttl_seconds)


def cache_delete_whatsapp_platform() -> None:
    cache_delete_default_message_bundle()
