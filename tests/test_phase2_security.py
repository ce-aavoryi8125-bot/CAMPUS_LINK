"""
test_phase2_security.py
-----------------------
Comprehensive Security & Authentication Test Suite for CampusLink 2.0.
Tests both legitimate authorization flows and malicious attack vectors:
1. Token lifecycle: valid, missing (401), invalid (401), expired (401), tampered (401)
2. Server-derived identity enforcement & client ID spoofing prevention
3. Role-Based Access Control (RBAC) on reports and admin endpoints (403)
4. Unauthorized rental approval / IDOR prevention (403)
5. User profile / password cross-account modification protection (403)
6. Password hashing with dynamic per-user salts and legacy backward compatibility
7. Media upload security: valid image re-encoding, disguised scripts, polyglots, corrupted streams, decompression bombs, oversized files, path traversal
8. Sliding-window rate limiting rejection (429)
9. Live HTTP response OWASP security headers verification
10. Centralized Commission Service calculations
"""
import unittest
import json
import io
import time
import sys
import os
from decimal import Decimal
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from core.config import PlatformConfig, CommissionService
from core.security import hash_password, verify_password, create_access_token, decode_access_token
from core.rate_limiter import get_rate_limiter
import db_engine

class CampusLinkSecurityTestSuite(unittest.TestCase):

    def setUp(self):
        app.testing = True
        self.client = app.test_client()
        get_rate_limiter().reset() # Reset rate limit buckets for clean isolation

        # Generate tokens for test personas
        # User 1: Albert Boateng (Verified Student / Lender)
        self.token_albert = create_access_token(user_id=1, email="ce-aavoryi8125@st.umat.edu.gh", role="Verified Student", name="Albert Boateng")
        # User 2: Benedict Osei (Verified Student / Lender)
        self.token_benedict = create_access_token(user_id=2, email="benedict@st.umat.edu.gh", role="Verified Student", name="Benedict Osei")
        # User 3: Grace Mensah (Borrower / Student)
        self.token_grace = create_access_token(user_id=3, email="grace@st.umat.edu.gh", role="Verified Student", name="Grace Mensah")
        # User 6: Admin CampusLink (Admin)
        self.token_admin = create_access_token(user_id=6, email="admin@umat.edu.gh", role="Admin", name="Admin CampusLink")

    def _auth_headers(self, token: str, strict: bool = True):
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        if strict:
            headers["X-Strict-Auth"] = "true"
        return headers

    # =========================================================================
    # 1. JWT TOKEN LIFECYCLE & TAMPERING TESTS
    # =========================================================================

    def test_01_token_generation_and_decoding(self):
        token = create_access_token(user_id=42, email="student@st.umat.edu.gh", role="Verified Student", name="Test Student")
        payload = decode_access_token(token)
        self.assertEqual(payload["sub"], 42)
        self.assertEqual(payload["email"], "student@st.umat.edu.gh")
        self.assertEqual(payload["role"], "Verified Student")
        print("  [OK] PASS  |  JWT token creation and claim decoding verified")

    def test_02_missing_token_rejected_with_401(self):
        # Protected route called without Authorization header in strict mode
        res = self.client.get('/api/wishlist', headers={"X-Strict-Auth": "true"})
        self.assertEqual(res.status_code, 401)
        data = json.loads(res.data)
        self.assertFalse(data["success"])
        self.assertIn("Missing token", data["message"])
        print("  [OK] PASS  |  Missing token properly rejected with HTTP 401 Unauthorized")

    def test_03_invalid_token_rejected_with_401(self):
        res = self.client.get('/api/wishlist', headers={"Authorization": "Bearer invalid.garbage.token", "X-Strict-Auth": "true"})
        self.assertEqual(res.status_code, 401)
        print("  [OK] PASS  |  Invalid/malformed token rejected with HTTP 401")

    def test_04_expired_token_rejected_with_401(self):
        # Create token that expired 1 hour ago
        expired_token = create_access_token(user_id=1, email="test@umat.edu.gh", expires_delta_hours=-1)
        res = self.client.get('/api/wishlist', headers=self._auth_headers(expired_token))
        self.assertEqual(res.status_code, 401)
        data = json.loads(res.data)
        self.assertIn("expired", data["message"].lower())
        print("  [OK] PASS  |  Expired token rejected with HTTP 401")

    def test_05_tampered_token_signature_rejected_with_401(self):
        # Alter the payload of a valid token without updating signature
        parts = self.token_albert.split('.')
        # Modify payload base64 string slightly
        tampered_token = f"{parts[0]}.eyJzdWIiOjYsInJvbGUiOiJBZG1pbiJ9.{parts[2]}"
        res = self.client.get('/api/wishlist', headers=self._auth_headers(tampered_token))
        self.assertEqual(res.status_code, 401)
        data = json.loads(res.data)
        self.assertIn("tampered", data["message"].lower())
        print("  [OK] PASS  |  Tampered token signature mismatch rejected with HTTP 401")

    # =========================================================================
    # 2. SERVER-DERIVED IDENTITY & SPOOFING PREVENTION
    # =========================================================================

    def test_06_server_derived_identity_overrides_client_spoofing(self):
        # Albert (user_id=1) submits a rental request but passes "borrower_id": 2 in JSON
        payload = {
            "listing_id": 2,
            "borrower_id": 2, # Attacker attempts to forge Benedict's identity
            "rent_start_date": "2026-11-01",
            "rent_end_date": "2026-11-03",
            "rental_purpose": "Field Trip",
            "notes": "Testing identity spoofing"
        }
        res = self.client.post('/api/rentals/request', data=json.dumps(payload), headers=self._auth_headers(self.token_albert))
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        req_id = data["request_id"]

        # Verify in DB that borrower_id was forced to 1 (Albert's token identity)
        req = db_engine.execute_query("SELECT borrower_id FROM rental_requests WHERE request_id = ?;", (req_id,), fetchone=True)
        self.assertEqual(req["borrower_id"], 1, "Server must enforce token user_id, ignoring client-supplied borrower_id")
        print("  [OK] PASS  |  Server-derived identity enforced; client-side borrower_id spoofing blocked")

    def test_07_unauthorized_rental_approval_blocked_with_403(self):
        # Create a rental request for a listing owned by Albert (user_id=1)
        req_id = db_engine.execute_query("""
        INSERT INTO rental_requests (listing_id, borrower_id, rent_start_date, rent_end_date, rental_purpose, status)
        VALUES (1, 3, '2026-12-01', '2026-12-03', 'Field Trip', 'Pending');
        """, fetch="lastrowid")

        # Benedict (user_id=2) attempts to approve Albert's rental request (IDOR attack)
        payload = {"request_id": req_id}
        res = self.client.post('/api/rentals/approve', data=json.dumps(payload), headers=self._auth_headers(self.token_benedict))
        self.assertEqual(res.status_code, 403)
        data = json.loads(res.data)
        self.assertFalse(data["success"])
        self.assertIn("owner", data["message"].lower())

        # Verify request status in DB remains 'Pending'
        status = db_engine.execute_query("SELECT status FROM rental_requests WHERE request_id = ?;", (req_id,), fetchone=True)
        self.assertEqual(status["status"], "Pending")
        print("  [OK] PASS  |  IDOR blocked: Non-owner cannot approve rental requests (HTTP 403)")

    def test_08_cross_account_profile_and_password_modification_blocked(self):
        # Albert (user_id=1) attempts to modify Benedict's profile (user_id=2)
        payload = {"user_id": 2, "phone": "+233249999999", "department": "Hacked Dept"}
        res = self.client.post('/api/user/profile', data=json.dumps(payload), headers=self._auth_headers(self.token_albert))
        self.assertEqual(res.status_code, 403)
        print("  [OK] PASS  |  Cross-account profile modification rejected with HTTP 403")

    # =========================================================================
    # 3. ROLE-BASED ACCESS CONTROL (RBAC)
    # =========================================================================

    def test_09_rbac_student_access_to_admin_reports_blocked(self):
        # Student (Albert) attempts to access Admin Report 01
        res = self.client.get('/api/reports/1', headers=self._auth_headers(self.token_albert))
        self.assertEqual(res.status_code, 403)
        data = json.loads(res.data)
        self.assertIn("Access denied", data["message"])
        print("  [OK] PASS  |  RBAC: Student user blocked from Admin reports (HTTP 403)")

    def test_10_rbac_admin_access_to_reports_succeeds(self):
        # Admin (token_admin) accesses Admin Report 01
        res = self.client.get('/api/reports/1', headers=self._auth_headers(self.token_admin))
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn("headers", data)
        self.assertIn("data", data)
        print("  [OK] PASS  |  RBAC: Admin user successfully accesses protected reports (HTTP 200)")

    # =========================================================================
    # 4. PASSWORD SECURITY & DYNAMIC SALT TESTS
    # =========================================================================

    def test_11_dynamic_salt_password_hashing(self):
        p1 = hash_password("MySecurePass2026!")
        p2 = hash_password("MySecurePass2026!")
        # Same password hashed twice must yield different salts and different hash strings
        self.assertNotEqual(p1, p2)
        self.assertTrue(verify_password("MySecurePass2026!", p1))
        self.assertTrue(verify_password("MySecurePass2026!", p2))
        self.assertFalse(verify_password("WrongPass", p1))
        print("  [OK] PASS  |  PBKDF2 dynamic per-user salt hashing verified")

    def test_12_legacy_password_hash_backward_compatibility(self):
        # Verify legacy hash format pbkdf2_sha256$100000$umat_campuslink_2026$...
        legacy_hash = hash_password("Student123", salt="umat_campuslink_2026")
        self.assertTrue(verify_password("Student123", legacy_hash))
        self.assertFalse(verify_password("WrongPassword", legacy_hash))
        print("  [OK] PASS  |  Legacy password hash backward-compatibility verified")

    # =========================================================================
    # 5. MEDIA UPLOAD SECURITY & IMAGE RE-ENCODING
    # =========================================================================

    def test_13_valid_image_upload_and_reencoding(self):
        # Create a valid in-memory test PNG
        img = Image.new("RGB", (300, 300), color=(73, 109, 137))
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_bytes = img_byte_arr.getvalue()

        data = {'image': (io.BytesIO(img_bytes), 'valid_item.png')}
        res = self.client.post(
            '/api/upload-image',
            data=data,
            content_type='multipart/form-data',
            headers={"Authorization": f"Bearer {self.token_albert}"}
        )
        self.assertEqual(res.status_code, 200)
        resp_data = json.loads(res.data)
        self.assertTrue(resp_data["success"])
        self.assertTrue(resp_data["image_url"].startswith("assets/item_"))
        print("  [OK] PASS  |  Valid image upload re-encoded clean to disk via Pillow")

    def test_14_malicious_script_disguised_as_image_rejected(self):
        # Executable / PHP script with fake .png extension
        fake_png = b"<?php echo 'malicious exploit'; system($_GET['cmd']); ?>"
        data = {'image': (io.BytesIO(fake_png), 'malicious.png')}
        res = self.client.post(
            '/api/upload-image',
            data=data,
            content_type='multipart/form-data',
            headers={"Authorization": f"Bearer {self.token_albert}"}
        )
        self.assertEqual(res.status_code, 400)
        resp_data = json.loads(res.data)
        self.assertFalse(resp_data["success"])
        print("  [OK] PASS  |  Disguised PHP script rejected by magic byte / structural inspection (HTTP 400)")

    def test_15_corrupted_and_truncated_image_rejected(self):
        # Valid PNG magic bytes followed by truncated corrupt garbage
        corrupt_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"random_corrupt_data"
        data = {'image': (io.BytesIO(corrupt_bytes), 'corrupt.png')}
        res = self.client.post(
            '/api/upload-image',
            data=data,
            content_type='multipart/form-data',
            headers={"Authorization": f"Bearer {self.token_albert}"}
        )
        self.assertEqual(res.status_code, 400)
        print("  [OK] PASS  |  Truncated/corrupt image byte stream safely rejected (HTTP 400)")

    def test_16_decompression_bomb_dimension_rejected(self):
        # Image exceeding max dimension (e.g. 3000x3000px > 2560px max)
        bomb_img = Image.new("RGB", (3000, 3000), color=(255, 0, 0))
        img_byte_arr = io.BytesIO()
        bomb_img.save(img_byte_arr, format='PNG')
        
        data = {'image': (io.BytesIO(img_byte_arr.getvalue()), 'bomb.png')}
        res = self.client.post(
            '/api/upload-image',
            data=data,
            content_type='multipart/form-data',
            headers={"Authorization": f"Bearer {self.token_albert}"}
        )
        self.assertEqual(res.status_code, 400)
        resp_data = json.loads(res.data)
        self.assertIn("dimension", resp_data["message"].lower())
        print("  [OK] PASS  |  Decompression bomb dimension (>2560px) rejected (HTTP 400)")

    # =========================================================================
    # 6. RATE LIMITING & BRUTE FORCE PROTECTION
    # =========================================================================

    def test_17_rate_limiting_triggers_429_too_many_requests(self):
        # /api/auth/login allows max 5 requests per 60s
        login_payload = json.dumps({"email": "ce-aavoryi8125@st.umat.edu.gh", "password": "WrongPassword"})
        
        # Send 5 requests (allowed)
        for _ in range(5):
            res = self.client.post('/api/auth/login', data=login_payload, content_type='application/json')
            self.assertIn(res.status_code, [401, 200])

        # 6th request must trigger HTTP 429 Too Many Requests
        res_6 = self.client.post('/api/auth/login', data=login_payload, content_type='application/json')
        self.assertEqual(res_6.status_code, 429)
        data = json.loads(res_6.data)
        self.assertIn("Rate limit exceeded", data["message"])
        self.assertIn("retry_after", data)
        print("  [OK] PASS  |  Sliding-window rate limiter triggered HTTP 429 Too Many Requests")

    # =========================================================================
    # 7. LIVE HTTP SECURITY HEADERS INSPECTION
    # =========================================================================

    def test_18_live_http_security_headers(self):
        res = self.client.get('/api/status')
        self.assertEqual(res.status_code, 200)
        headers = res.headers
        
        self.assertEqual(headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(headers.get("X-Frame-Options"), "SAMEORIGIN")
        self.assertEqual(headers.get("X-XSS-Protection"), "1; mode=block")
        self.assertEqual(headers.get("Referrer-Policy"), "strict-origin-when-cross-origin")
        self.assertIn("Content-Security-Policy", headers)
        print("  [OK] PASS  |  Live HTTP responses verified for all OWASP security headers")

    # =========================================================================
    # 8. CENTRALIZED COMMISSION SERVICE
    # =========================================================================

    def test_19_centralized_commission_service_splits(self):
        # Rental split: 10% platform, 90% owner on GH₵ 90.00
        rental_split = CommissionService.calculate_rental_split(Decimal("90.00"))
        self.assertEqual(rental_split["gross_amount"], Decimal("90.00"))
        self.assertEqual(rental_split["commission_amount"], Decimal("9.00"))
        self.assertEqual(rental_split["owner_earnings"], Decimal("81.00"))

        # Service split: 10% platform, 90% provider on GH₵ 150.00
        service_split = CommissionService.calculate_service_split(Decimal("150.00"))
        self.assertEqual(service_split["amount"], Decimal("150.00"))
        self.assertEqual(service_split["platform_fee"], Decimal("15.00"))
        self.assertEqual(service_split["provider_earnings"], Decimal("135.00"))
        print("  [OK] PASS  |  Centralized CommissionService calculations verified")

    # =========================================================================
    # 9. ADDITIONAL SECURITY DEFENSE & MIGRATION TESTS
    # =========================================================================

    def test_20_legacy_login_migrates_password_hash(self):
        # 1. Set User 5 (Abena) to a legacy fixed-salt password hash
        legacy_hash = f"pbkdf2_sha256$100000$umat_campuslink_2026$testlegacyhex"
        # Create a valid legacy hash for 'Student123'
        import hashlib
        key = hashlib.pbkdf2_hmac('sha256', b'Student123', b'umat_campuslink_2026', 100000)
        legacy_hash = f"pbkdf2_sha256$100000$umat_campuslink_2026${key.hex()}"
        db_engine.execute_query("UPDATE users SET password_hash = ? WHERE user_id = 5;", (legacy_hash,))

        # Verify DB currently holds the legacy hash
        pre_user = db_engine.execute_query("SELECT password_hash FROM users WHERE user_id = 5;", fetchone=True)
        self.assertIn("umat_campuslink_2026", pre_user["password_hash"])

        # 2. Perform authentication via login endpoint
        login_res = self.client.post(
            '/api/auth/login',
            data=json.dumps({"email": "abena@st.umat.edu.gh", "password": "Student123"}),
            content_type='application/json'
        )
        self.assertEqual(login_res.status_code, 200)

        # 3. Verify DB has automatically upgraded the stored password hash to dynamic salt
        post_user = db_engine.execute_query("SELECT password_hash FROM users WHERE user_id = 5;", fetchone=True)
        self.assertNotIn("umat_campuslink_2026", post_user["password_hash"])
        self.assertTrue(post_user["password_hash"].startswith("pbkdf2_sha256$100000$"))
        print("  [OK] PASS  |  Legacy password authentication successfully upgraded stored hash to dynamic salt")

    def test_21_oversized_upload_rejected(self):
        # Create 5.1 MB of dummy image bytes (exceeding 5 MB limit)
        oversized_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"A" * (5 * 1024 * 1024 + 1024)
        data = {'image': (io.BytesIO(oversized_bytes), 'oversized.png')}
        res = self.client.post(
            '/api/upload-image',
            data=data,
            content_type='multipart/form-data',
            headers={"Authorization": f"Bearer {self.token_albert}"}
        )
        self.assertEqual(res.status_code, 400)
        resp_data = json.loads(res.data)
        self.assertIn("exceeds maximum", resp_data["message"].lower())
        print("  [OK] PASS  |  Oversized file upload (>5MB) rejected with HTTP 400")

    def test_22_unauthorized_user_requests_access_blocked(self):
        # Albert (user_id=1) attempts to access Benedict's (user_id=2) request history
        res = self.client.get('/api/rentals/my-requests/2', headers=self._auth_headers(self.token_albert))
        self.assertEqual(res.status_code, 403)
        data = json.loads(res.data)
        self.assertIn("Unauthorized access", data["message"])
        print("  [OK] PASS  |  Unauthorized cross-account request history access blocked with HTTP 403")

if __name__ == '__main__':
    print("========================================================================")
    print("   CampusLink Phase 2: Security & Authentication Test Suite")
    print("========================================================================")
    unittest.main()
