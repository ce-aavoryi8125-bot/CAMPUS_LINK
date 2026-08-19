"""
tests/test_stage5_4_container_config.py
---------------------------------------
Focused Unit & Integration Test Suite for Phase 5 - Stage 5.4:
Containerization & Multi-Service Deployment Architecture.

Validates:
1. Hardened multi-stage Dockerfile directives & non-root user execution (UID 10001).
2. Production docker-compose.yml service topology (6 services), healthchecks, and strict secrets.
3. Network topology isolation (frontend_net, backend_net) and persistent volume definitions.
4. Nginx reverse proxy routing, security headers, and static caching directives.
5. Development compose configuration (docker-compose.dev.yml).
6. Total preservation of offline SQLite development workflow.
"""
import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import db_engine
from core.config import PlatformConfig

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

class Stage54ContainerConfigTestSuite(unittest.TestCase):

    # -------------------------------------------------------------------------
    # 1. DOCKERFILE MULTI-STAGE & NON-ROOT SECURITY USER
    # -------------------------------------------------------------------------

    def test_01_dockerfile_multi_stage_structure(self):
        dockerfile_path = os.path.join(BASE_DIR, "Dockerfile")
        self.assertTrue(os.path.exists(dockerfile_path), "Dockerfile must exist")
        
        with open(dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Verify multi-stage build
        self.assertIn("AS builder", content)
        self.assertIn("AS runtime", content)
        self.assertIn("COPY --from=builder /opt/venv /opt/venv", content)
        
        # Verify non-root user setup
        self.assertIn("groupadd -g 10001 campuslink", content)
        self.assertIn("useradd -u 10001", content)
        self.assertIn("USER campuslink", content)
        
        # Verify unprivileged ownership and entrypoint
        self.assertIn("--chown=campuslink:campuslink", content)
        self.assertIn("EXPOSE 5000", content)
        self.assertIn("gunicorn", content)
        print("  [OK] PASS (01) | Dockerfile multi-stage build and non-root security user (UID 10001) verified")

    # -------------------------------------------------------------------------
    # 2. DOCKER COMPOSE PRODUCTION TOPOLOGY & STRICT ENVIRONMENT SECRETS
    # -------------------------------------------------------------------------

    def test_02_docker_compose_production_services_and_strict_secrets(self):
        compose_path = os.path.join(BASE_DIR, "docker-compose.yml")
        self.assertTrue(os.path.exists(compose_path), "docker-compose.yml must exist")
        
        with open(compose_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Verify all 6 core services are defined
        for service in ["nginx:", "web:", "worker:", "scheduler:", "redis:", "db:"]:
            self.assertIn(service, content, f"Service {service} must be declared in docker-compose.yml")
            
        # Verify healthcheck declarations
        self.assertIn("healthcheck:", content)
        self.assertIn("/healthz", content)
        self.assertIn("condition: service_healthy", content)
        
        # Verify STRICT secret variable requirements (NO insecure fallback passwords in production compose)
        self.assertNotIn("campus_secure_pass", content, "Insecure fallback campus_secure_pass must NOT be present")
        self.assertNotIn("redis_pass", content, "Insecure fallback redis_pass must NOT be present")
        self.assertNotIn("root_secure_pass", content, "Insecure fallback root_secure_pass must NOT be present")
        
        self.assertIn("${MYSQL_PASSWORD}", content)
        self.assertIn("${REDIS_PASSWORD}", content)
        self.assertIn("${CAMPUSLINK_SECRET_KEY}", content)
        self.assertIn("${CAMPUSLINK_JWT_SECRET}", content)
        print("  [OK] PASS (02) | Production docker-compose.yml services, healthchecks & strict secrets verified")

    # -------------------------------------------------------------------------
    # 3. NETWORK TOPOLOGY & PERSISTENT VOLUME ISOLATION
    # -------------------------------------------------------------------------

    def test_03_docker_compose_network_and_volume_isolation(self):
        compose_path = os.path.join(BASE_DIR, "docker-compose.yml")
        with open(compose_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        self.assertIn("frontend_net:", content)
        self.assertIn("backend_net:", content)
        self.assertIn("mysql_data:", content)
        self.assertIn("redis_data:", content)
        print("  [OK] PASS (03) | Docker networks (frontend_net, backend_net) and volume isolation verified")

    # -------------------------------------------------------------------------
    # 4. NGINX REVERSE PROXY CONFIGURATION INTEGRITY
    # -------------------------------------------------------------------------

    def test_04_nginx_configuration_integrity(self):
        nginx_path = os.path.join(BASE_DIR, "deploy", "nginx", "default.conf")
        self.assertTrue(os.path.exists(nginx_path), "deploy/nginx/default.conf must exist")
        
        with open(nginx_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        self.assertIn("upstream campuslink_app", content)
        self.assertIn("proxy_pass http://campuslink_app;", content)
        self.assertIn("proxy_set_header X-Forwarded-For", content)
        self.assertIn("location /static/", content)
        self.assertIn("location /assets/", content)
        self.assertIn("gzip on;", content)
        self.assertIn("X-Frame-Options", content)
        print("  [OK] PASS (04) | Nginx reverse proxy routing, gzip compression, and security headers verified")

    # -------------------------------------------------------------------------
    # 5. DEVELOPMENT COMPOSE CONFIGURATION
    # -------------------------------------------------------------------------

    def test_05_docker_compose_dev_structure(self):
        dev_compose_path = os.path.join(BASE_DIR, "docker-compose.dev.yml")
        self.assertTrue(os.path.exists(dev_compose_path), "docker-compose.dev.yml must exist")
        
        with open(dev_compose_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        self.assertIn("campuslink_web_dev", content)
        self.assertIn("volumes:", content)
        self.assertIn(".:/app", content)
        self.assertIn("CAMPUSLINK_ENV=development", content)
        print("  [OK] PASS (05) | Development docker-compose.dev.yml live code mounting verified")

    # -------------------------------------------------------------------------
    # 6. OFFLINE SQLITE WORKFLOW REMAINS 100% OPERATIONAL
    # -------------------------------------------------------------------------

    def test_06_local_sqlite_compatibility_unaffected(self):
        status = db_engine.get_engine_status()
        self.assertEqual(status["engine"], "SQLITE")
        self.assertEqual(status["status"], "Connected")
        self.assertEqual(status["mode"], "Development/Fallback (SQLite 3)")
        print("  [OK] PASS (06) | Local SQLite development workflow verified 100% operational outside Docker")

if __name__ == '__main__':
    print("========================================================================")
    print("   CampusLink Phase 5 Stage 5.4: Container Config & Topology Suite")
    print("========================================================================")
    unittest.main()
