"""
tests/test_stage5_3_production_config.py
----------------------------------------
Focused Unit & Integration Test Suite for Phase 5 - Stage 5.3:
Production Configuration, Secrets Management & Health Endpoints (/healthz, /readyz).

Validates:
1. /healthz lightweight liveness probe (HTTP 200, zero I/O).
2. /readyz readiness probe evaluating database and Redis health.
3. Secret and password masking across status and health endpoints.
4. Strict production configuration validation on secure credentials.
5. Fast-fail rejection of default secrets in production (ConfigurationError).
6. Rejection of SQLite and eager Celery in production mode.
7. Graceful development/test mode fallback without crashing.
"""
import unittest
import json
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from core.config import PlatformConfig, ConfigurationError
import db_engine

class Stage53ProductionConfigTestSuite(unittest.TestCase):

    def setUp(self):
        app.testing = True
        self.client = app.test_client()

    # -------------------------------------------------------------------------
    # 1. /healthz LIVENESS PROBE
    # -------------------------------------------------------------------------

    def test_01_healthz_liveness_probe(self):
        response = self.client.get('/healthz')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertEqual(data["status"], "healthy")
        self.assertIn("timestamp", data)
        self.assertIn("environment", data)
        self.assertEqual(data["version"], "2.0.0")
        print("  [OK] PASS (01) | /healthz lightweight liveness probe returned HTTP 200 OK")

    # -------------------------------------------------------------------------
    # 2. /readyz READINESS PROBE
    # -------------------------------------------------------------------------

    def test_02_readyz_readiness_probe(self):
        response = self.client.get('/readyz')
        self.assertIn(response.status_code, (200, 503))
        data = json.loads(response.data)
        
        self.assertIn("status", data)
        self.assertIn("checks", data)
        self.assertIn("database", data["checks"])
        self.assertIn("redis", data["checks"])
        
        db_check = data["checks"]["database"]
        self.assertEqual(db_check["status"], "healthy")
        self.assertIn("latency_ms", db_check)
        print(f"  [OK] PASS (02) | /readyz probe evaluated database ({db_check['engine']}) and Redis connectivity")

    # -------------------------------------------------------------------------
    # 3. SECRET AND CREDENTIAL MASKING
    # -------------------------------------------------------------------------

    def test_03_readyz_and_status_secret_masking(self):
        # Verify /readyz output doesn't contain raw secret values
        res_ready = self.client.get('/readyz')
        raw_ready_str = res_ready.data.decode('utf-8')
        
        self.assertNotIn("campuslink_umat_secret_key_2026", raw_ready_str)
        self.assertNotIn("campuslink_umat_jwt_super_secret_key_2026_ghana", raw_ready_str)
        
        # Verify /api/status does not expose database password
        res_status = self.client.get('/api/status')
        status_data = json.loads(res_status.data)
        self.assertNotIn("password", status_data)
        self.assertNotIn("secret", status_data)
        print("  [OK] PASS (03) | Sensitive credentials masked across health & diagnostic endpoints")

    # -------------------------------------------------------------------------
    # 4. STRICT PRODUCTION CONFIGURATION VALIDATION (SUCCESS)
    # -------------------------------------------------------------------------

    def test_04_production_validation_success_on_valid_secrets(self):
        secure_secret = "a_super_secure_production_secret_key_32_chars_long_2026"
        secure_jwt = "a_super_secure_production_jwt_secret_key_32_chars_long_2026"
        secure_webhook = "webhook_secret_32_chars_long_2026"
        
        with patch.object(PlatformConfig, 'CAMPUSLINK_ENV', 'production'):
            with patch.object(PlatformConfig, 'SECRET_KEY', secure_secret):
                with patch.object(PlatformConfig, 'JWT_SECRET_KEY', secure_jwt):
                    with patch.object(PlatformConfig, 'MOMO_WEBHOOK_SECRET', secure_webhook):
                        with patch.object(PlatformConfig, 'CELERY_ALWAYS_EAGER', False):
                            with patch.dict(os.environ, {"USE_MYSQL": "true", "MYSQL_PASSWORD": "secure_db_password_123"}):
                                is_valid, violations = PlatformConfig.validate_production_config()
                                self.assertTrue(is_valid, f"Expected valid production config, got violations: {violations}")
                                self.assertEqual(len(violations), 0)
        print("  [OK] PASS (04) | Production configuration validated successfully with compliant secrets")

    # -------------------------------------------------------------------------
    # 5. PRODUCTION VALIDATION REJECTS DEFAULT SECRETS (FAST FAIL)
    # -------------------------------------------------------------------------

    def test_05_production_validation_rejects_default_secrets(self):
        with patch.object(PlatformConfig, 'CAMPUSLINK_ENV', 'production'):
            with patch.object(PlatformConfig, 'SECRET_KEY', 'campuslink_umat_secret_key_2026'):
                is_valid, violations = PlatformConfig.validate_production_config()
                self.assertFalse(is_valid)
                self.assertTrue(any("CAMPUSLINK_SECRET_KEY" in v for v in violations))
                
                # Verify assert_production_ready raises ConfigurationError
                with self.assertRaises(ConfigurationError):
                    PlatformConfig.assert_production_ready()
        print("  [OK] PASS (05) | Fast-fail rejection of default secrets in production verified (ConfigurationError raised)")

    # -------------------------------------------------------------------------
    # 6. PRODUCTION VALIDATION REJECTS SQLITE & EAGER CELERY
    # -------------------------------------------------------------------------

    def test_06_production_validation_rejects_sqlite_and_eager_celery(self):
        secure_secret = "a_super_secure_production_secret_key_32_chars_long_2026"
        secure_jwt = "a_super_secure_production_jwt_secret_key_32_chars_long_2026"
        secure_webhook = "webhook_secret_32_chars_long_2026"
        
        with patch.object(PlatformConfig, 'CAMPUSLINK_ENV', 'production'):
            with patch.object(PlatformConfig, 'SECRET_KEY', secure_secret):
                with patch.object(PlatformConfig, 'JWT_SECRET_KEY', secure_jwt):
                    with patch.object(PlatformConfig, 'MOMO_WEBHOOK_SECRET', secure_webhook):
                        with patch.object(PlatformConfig, 'CELERY_ALWAYS_EAGER', True):
                            with patch.dict(os.environ, {"USE_MYSQL": "false", "MYSQL_PASSWORD": ""}):
                                is_valid, violations = PlatformConfig.validate_production_config()
                                self.assertFalse(is_valid)
                                self.assertTrue(any("SQLite is strictly prohibited" in v for v in violations))
                                self.assertTrue(any("CELERY_ALWAYS_EAGER" in v for v in violations))
        print("  [OK] PASS (06) | Production validation correctly blocked SQLite and synchronous Celery")

    # -------------------------------------------------------------------------
    # 7. DEVELOPMENT / TESTING FALLBACK PERMITTED
    # -------------------------------------------------------------------------

    def test_07_development_mode_allows_defaults_without_error(self):
        with patch.object(PlatformConfig, 'CAMPUSLINK_ENV', 'development'):
            # In development, assert_production_ready must not raise
            try:
                PlatformConfig.assert_production_ready()
                success = True
            except ConfigurationError:
                success = False
            self.assertTrue(success, "Development mode must allow default fallback keys without raising ConfigurationError")
        print("  [OK] PASS (07) | Development mode seamlessly permits default fallback keys without crashing")

if __name__ == '__main__':
    print("========================================================================")
    print("   CampusLink Phase 5 Stage 5.3: Production Config & Health Probes Suite")
    print("========================================================================")
    unittest.main()
