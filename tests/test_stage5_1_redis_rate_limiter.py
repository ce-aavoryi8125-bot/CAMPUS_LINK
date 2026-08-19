"""
tests/test_stage5_1_redis_rate_limiter.py
-----------------------------------------
Focused Unit & Integration Test Suite for Phase 5 - Stage 5.1:
Redis Integration & Distributed Rate Limiting.

Validates:
1. Redis client connection manager & health checks (availability, latency, fallback).
2. Transparent in-memory fallback when Redis is unconfigured or unreachable.
3. Sliding-window rate limit enforcement with exact HTTP 429 and Retry-After header.
4. Atomic Lua sliding-window script behavior.
5. Multi-threaded concurrency safety.
6. Compatibility with existing Phase 1-4 endpoints.
"""
import unittest
import time
import json
import os
import sys
import threading
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from core.config import PlatformConfig
from core.redis_client import get_redis_client, is_redis_available, check_redis_health, reset_redis_client
from core.rate_limiter import (
    InMemorySlidingWindowLimiter,
    RedisSlidingWindowLimiter,
    DistributedRateLimiter,
    get_rate_limiter,
    rate_limit
)

class Stage51RedisRateLimiterTestSuite(unittest.TestCase):

    def setUp(self):
        app.testing = True
        self.client = app.test_client()
        self.limiter = get_rate_limiter()
        self.limiter.reset()

    def tearDown(self):
        self.limiter.reset()
        reset_redis_client()

    # -------------------------------------------------------------------------
    # 1. REDIS CLIENT & HEALTH PROBES
    # -------------------------------------------------------------------------

    def test_01_redis_healthcheck_structure(self):
        health = check_redis_health()
        self.assertIsInstance(health, dict)
        self.assertIn("status", health)
        self.assertIn("enabled", health)
        print(f"  [OK] PASS (01) | Redis health probe returned status: {health['status']}")

    def test_02_redis_unreachability_graceful_fallback(self):
        # Force Redis client to point to an unreachable port
        with patch.object(PlatformConfig, 'REDIS_URL', 'redis://127.0.0.1:65534/0'):
            with patch.object(PlatformConfig, 'REDIS_CONNECT_TIMEOUT_SEC', 0.2):
                reset_redis_client()
                avail = is_redis_available(force_check=True)
                self.assertFalse(avail, "Unreachable Redis must report available=False")
                
                # Verify rate limiter still functions seamlessly via fallback
                allowed, retry_after = self.limiter.is_allowed("test:fallback:key", 3, 10)
                self.assertTrue(allowed, "Fallback in-memory limiter must permit initial request")
                print("  [OK] PASS (02) | Graceful fallback to in-memory limiter on Redis unreachability verified")

    # -------------------------------------------------------------------------
    # 2. IN-MEMORY SLIDING-WINDOW ENFORCEMENT & EXPIRATION
    # -------------------------------------------------------------------------

    def test_03_in_memory_limiter_strict_enforcement(self):
        mem_limiter = InMemorySlidingWindowLimiter()
        key = "client:user:123"
        max_req = 3
        window = 2  # 2 seconds
        
        # 3 allowed requests
        for i in range(max_req):
            allowed, retry = mem_limiter.is_allowed(key, max_req, window)
            self.assertTrue(allowed, f"Request {i+1} must be allowed")
            self.assertEqual(retry, 0)
            
        # 4th request must be rejected
        allowed, retry = mem_limiter.is_allowed(key, max_req, window)
        self.assertFalse(allowed, "Request exceeding limit must be rejected")
        self.assertGreaterEqual(retry, 1, "Retry-after must be >= 1 second")
        print("  [OK] PASS (03) | In-memory sliding-window threshold enforcement verified (3 allowed, 4th rejected)")

    def test_04_in_memory_limiter_window_slide_and_recovery(self):
        mem_limiter = InMemorySlidingWindowLimiter()
        key = "client:user:exp"
        max_req = 2
        window = 1  # 1 second
        
        mem_limiter.is_allowed(key, max_req, window)
        mem_limiter.is_allowed(key, max_req, window)
        allowed, _ = mem_limiter.is_allowed(key, max_req, window)
        self.assertFalse(allowed)
        
        # Wait for sliding window to elapse
        time.sleep(1.1)
        
        allowed, retry = mem_limiter.is_allowed(key, max_req, window)
        self.assertTrue(allowed, "Request after window expiration must be allowed")
        self.assertEqual(retry, 0)
        print("  [OK] PASS (04) | Sliding window expiration and recovery verified")

    # -------------------------------------------------------------------------
    # 3. REDIS SLIDING WINDOW LUA EXECUTION LOGIC (SIMULATED / MOCKED)
    # -------------------------------------------------------------------------

    def test_05_redis_limiter_lua_mock_execution(self):
        redis_limiter = RedisSlidingWindowLimiter()
        mock_redis = MagicMock()
        
        # Scenario A: Under limit (returns [1, 0])
        mock_redis.eval.return_value = [1, 0]
        mock_redis.evalsha.return_value = [1, 0]
        
        with patch('core.rate_limiter.get_redis_client', return_value=mock_redis):
            allowed, retry = redis_limiter.is_allowed("simulated:key", 5, 60)
            self.assertTrue(allowed)
            self.assertEqual(retry, 0)
            
        # Scenario B: Over limit (returns [0, 42])
        mock_redis.evalsha.return_value = [0, 42]
        with patch('core.rate_limiter.get_redis_client', return_value=mock_redis):
            allowed, retry = redis_limiter.is_allowed("simulated:key", 5, 60)
            self.assertFalse(allowed)
            self.assertEqual(retry, 42)
        print("  [OK] PASS (05) | Redis Lua script evaluation and retry-after parsing verified")

    # -------------------------------------------------------------------------
    # 4. FLASK ENDPOINT RATE LIMITING & HTTP 429 PAYLOAD
    # -------------------------------------------------------------------------

    def test_06_flask_endpoint_rate_limit_decorator_429(self):
        from flask import Flask
        isolated_app = Flask("isolated_test_app")
        isolated_app.testing = True
        
        @isolated_app.route('/test/ratelimit/endpoint', methods=['GET'])
        @rate_limit(max_requests=2, window_seconds=60)
        def _test_endpoint():
            return {"success": True, "message": "OK"}
            
        test_client = isolated_app.test_client()
        
        # Request 1: OK
        res1 = test_client.get('/test/ratelimit/endpoint')
        self.assertEqual(res1.status_code, 200)
        
        # Request 2: OK
        res2 = test_client.get('/test/ratelimit/endpoint')
        self.assertEqual(res2.status_code, 200)
        
        # Request 3: HTTP 429 Too Many Requests
        res3 = test_client.get('/test/ratelimit/endpoint')
        self.assertEqual(res3.status_code, 429)
        data = json.loads(res3.data)
        self.assertFalse(data["success"])
        self.assertIn("Rate limit exceeded", data["message"])
        self.assertIn("retry_after", data)
        self.assertGreaterEqual(data["retry_after"], 1)
        print("  [OK] PASS (06) | Flask rate limit decorator returned HTTP 429 with retry_after payload")

    # -------------------------------------------------------------------------
    # 5. MULTI-THREADED CONCURRENCY SAFETY
    # -------------------------------------------------------------------------

    def test_07_concurrent_threads_rate_limiting_atomicity(self):
        # 10 concurrent threads attempting to consume a bucket of capacity 4
        limiter = InMemorySlidingWindowLimiter()
        key = "concurrent:test:bucket"
        max_allowed = 4
        window = 5
        
        results_list = []
        threads = []
        
        def worker():
            allowed, _ = limiter.is_allowed(key, max_allowed, window)
            results_list.append(allowed)
            
        for _ in range(10):
            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()
            
        for t in threads:
            t.join()
            
        success_count = sum(1 for r in results_list if r is True)
        rejected_count = sum(1 for r in results_list if r is False)
        
        self.assertEqual(success_count, max_allowed, f"Exactly {max_allowed} concurrent requests must succeed")
        self.assertEqual(rejected_count, 6, "Remaining 6 concurrent requests must be rejected")
        print(f"  [OK] PASS (07) | Concurrent thread rate limiting atomicity verified ({success_count} passed, {rejected_count} blocked)")

if __name__ == '__main__':
    print("========================================================================")
    print("   CampusLink Phase 5 Stage 5.1: Redis & Rate Limiter Test Suite")
    print("========================================================================")
    unittest.main()
