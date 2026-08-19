"""
core/redis_client.py
--------------------
Redis Connection Manager and Health-Check Component for CampusLink 2.0.
Provides:
1. Thread-safe Redis connection pool management.
2. Graceful connectivity detection with timeout guards.
3. Health check probes for liveness/readiness monitoring.
4. Safe fallback support when Redis is unconfigured or unreachable.
"""
import os
import time
from typing import Optional, Dict, Any
import logging

try:
    import redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False

from .config import PlatformConfig

logger = logging.getLogger("campuslink.redis")

_redis_pool: Optional[Any] = None
_redis_client: Optional[Any] = None
_redis_available: Optional[bool] = None
_last_health_check_time: float = 0.0
_HEALTH_CHECK_CACHE_TTL = 5.0  # seconds

def get_redis_client(force: bool = False) -> Optional[Any]:
    """
    Returns a shared Redis client instance if Redis is enabled and accessible.
    Returns None if Redis is disabled, uninstalled, or unreachable.
    Caches failed connection state for _HEALTH_CHECK_CACHE_TTL to prevent socket timeout latency.
    """
    global _redis_pool, _redis_client, _redis_available, _last_health_check_time
    now = time.time()
    
    if not HAS_REDIS or not PlatformConfig.REDIS_ENABLED:
        _redis_available = False
        return None
        
    if _redis_client is not None:
        return _redis_client
        
    # If recently checked and failed, return None immediately without blocking
    if not force and _redis_available is False and (now - _last_health_check_time < _HEALTH_CHECK_CACHE_TTL):
        return None
        
    _last_health_check_time = now
    try:
        url = PlatformConfig.REDIS_URL
        timeout = PlatformConfig.REDIS_CONNECT_TIMEOUT_SEC
        _redis_pool = redis.ConnectionPool.from_url(
            url,
            socket_connect_timeout=timeout,
            socket_timeout=timeout,
            max_connections=20,
            decode_responses=True
        )
        client = redis.Redis(connection_pool=_redis_pool)
        # Verify connection
        client.ping()
        _redis_client = client
        _redis_available = True
        logger.info("Connected to Redis at %s", url)
        return _redis_client
    except Exception as e:
        _redis_available = False
        _redis_client = None
        _redis_pool = None
        logger.warning("Redis unavailable (%s). Operating in fallback mode.", str(e))
        return None

def is_redis_available(force_check: bool = False) -> bool:
    """
    Checks if Redis is currently responsive.
    Caches the health check result for short interval unless force_check=True.
    """
    global _redis_available, _last_health_check_time
    now = time.time()
    
    if not force_check and _redis_available is not None and (now - _last_health_check_time < _HEALTH_CHECK_CACHE_TTL):
        return _redis_available
        
    _last_health_check_time = now
    client = get_redis_client()
    if client is None:
        _redis_available = False
        return False
        
    try:
        client.ping()
        _redis_available = True
        return True
    except Exception:
        _redis_available = False
        return False

def _mask_url(url: str) -> str:
    """Masks credentials in connection URLs (e.g. redis://:password@host:6379/0 -> redis://:***@host:6379/0)."""
    import re
    return re.sub(r'://([^:]+):([^@]+)@', r'://\1:***@', re.sub(r'://:([^@]+)@', r'://:***@', url))

def check_redis_health() -> Dict[str, Any]:
    """
    Detailed health check dictionary for monitoring probes (/readyz, /healthz).
    Masks any embedded connection credentials.
    """
    masked_url = _mask_url(PlatformConfig.REDIS_URL) if hasattr(PlatformConfig, "REDIS_URL") else "redis://localhost:6379/0"
    
    if not HAS_REDIS:
        return {
            "status": "unavailable",
            "enabled": PlatformConfig.REDIS_ENABLED,
            "error": "redis library not installed",
            "latency_ms": None
        }
        
    if not PlatformConfig.REDIS_ENABLED:
        return {
            "status": "disabled",
            "enabled": False,
            "latency_ms": None
        }
        
    client = get_redis_client()
    if client is None:
        return {
            "status": "unreachable",
            "enabled": True,
            "url": masked_url,
            "latency_ms": None
        }
        
    try:
        start = time.perf_counter()
        client.ping()
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "status": "healthy",
            "enabled": True,
            "url": masked_url,
            "latency_ms": latency_ms
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "enabled": True,
            "url": masked_url,
            "error": str(e),
            "latency_ms": None
        }

def reset_redis_client():
    """Resets the global Redis client and pool (used in unit testing)."""
    global _redis_pool, _redis_client, _redis_available, _last_health_check_time
    if _redis_client is not None:
        try:
            _redis_client.close()
        except Exception:
            pass
    if _redis_pool is not None:
        try:
            _redis_pool.disconnect()
        except Exception:
            pass
    _redis_pool = None
    _redis_client = None
    _redis_available = None
    _last_health_check_time = 0.0
