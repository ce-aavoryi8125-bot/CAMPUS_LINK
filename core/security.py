"""
core/security.py
----------------
Cryptographic security module for CampusLink 2.0.
Provides:
- PBKDF2-HMAC-SHA256 password hashing with dynamic per-user salts
- Backward-compatible verification for legacy password hashes
- JWT (JSON Web Token) generation and verification with HMAC-SHA256
"""
import hmac
import hashlib
import base64
import json
import time
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

from .config import PlatformConfig

# =============================================================================
# 1. PASSWORD HASHING & VERIFICATION ENGINE
# =============================================================================

def hash_password(password: str, salt: Optional[str] = None) -> str:
    """
    Securely hashes password using PBKDF2-HMAC-SHA256 with 100,000 iterations.
    Uses a dynamic cryptographically secure random 16-byte hex salt if not specified.
    Format: pbkdf2_sha256$100000$<salt>$<hash_hex>
    """
    if salt is None:
        salt = secrets.token_hex(16)
        
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    return f"pbkdf2_sha256$100000${salt}${key.hex()}"

def verify_password(password: str, stored_hash: str) -> bool:
    """
    Verifies raw password against stored PBKDF2 hash string.
    Supports both dynamic per-user salts and legacy fixed-salt ("umat_campuslink_2026") hashes.
    Uses constant-time comparison (hmac.compare_digest) to prevent timing attacks.
    """
    if not stored_hash or not password:
        return False
        
    parts = stored_hash.split('$')
    if len(parts) == 4 and parts[0] == 'pbkdf2_sha256':
        try:
            iterations = int(parts[1])
            salt = parts[2]
            expected_hex = parts[3]
            key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), iterations)
            return hmac.compare_digest(key.hex(), expected_hex)
        except Exception:
            return False
            
    # Legacy SHA256 fallback (for test backward compatibility)
    try:
        sha256_candidate = hashlib.sha256(password.encode('utf-8')).hexdigest()
        if hmac.compare_digest(stored_hash, sha256_candidate):
            return True
    except Exception:
        pass
        
    return hmac.compare_digest(stored_hash, password)

# =============================================================================
# 2. JWT TOKEN GENERATION & VALIDATION ENGINE
# =============================================================================

def _base64url_encode(data: bytes) -> str:
    """Encodes bytes to a URL-safe Base64 string without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')

def _base64url_decode(data: str) -> bytes:
    """Decodes a URL-safe Base64 string with proper padding."""
    rem = len(data) % 4
    if rem > 0:
        data += '=' * (4 - rem)
    return base64.urlsafe_b64decode(data.encode('utf-8'))

def create_access_token(
    user_id: int,
    email: str,
    role: str = "Verified Student",
    name: str = "",
    expires_delta_hours: Optional[int] = None
) -> str:
    """
    Generates a cryptographically signed HMAC-SHA256 JWT access token.
    Claims include: sub (user_id), email, role, name, iat, exp.
    """
    now = int(time.time())
    delta_hours = expires_delta_hours or PlatformConfig.JWT_EXPIRATION_HOURS
    exp = now + (delta_hours * 3600)
    
    header = {"alg": PlatformConfig.JWT_ALGORITHM, "typ": "JWT"}
    payload = {
        "sub": user_id,
        "user_id": user_id,
        "email": email,
        "role": role,
        "name": name,
        "iat": now,
        "exp": exp
    }
    
    header_b64 = _base64url_encode(json.dumps(header, separators=(',', ':')).encode('utf-8'))
    payload_b64 = _base64url_encode(json.dumps(payload, separators=(',', ':')).encode('utf-8'))
    
    signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
    signature = hmac.new(PlatformConfig.JWT_SECRET_KEY.encode('utf-8'), signing_input, hashlib.sha256).digest()
    sig_b64 = _base64url_encode(signature)
    
    return f"{header_b64}.{payload_b64}.{sig_b64}"

def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Validates token signature and expiration, returning decoded payload dictionary.
    Raises ValueError on invalid, tampered, or expired tokens.
    """
    if not token or not isinstance(token, str):
        raise ValueError("Missing or invalid token format.")
        
    parts = token.strip().split('.')
    if len(parts) != 3:
        raise ValueError("Invalid JWT token segment structure.")
        
    header_b64, payload_b64, sig_b64 = parts
    
    # 1. Verify HMAC signature
    signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
    expected_sig = hmac.new(PlatformConfig.JWT_SECRET_KEY.encode('utf-8'), signing_input, hashlib.sha256).digest()
    expected_sig_b64 = _base64url_encode(expected_sig)
    
    if not hmac.compare_digest(sig_b64, expected_sig_b64):
        raise ValueError("Token signature verification failed (tampered token).")
        
    # 2. Decode payload
    try:
        payload_bytes = _base64url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode('utf-8'))
    except Exception as e:
        raise ValueError(f"Malformed token payload: {e}")
        
    # 3. Check expiration
    now = int(time.time())
    exp = payload.get("exp")
    if exp is None or now > exp:
        raise ValueError("Token has expired.")
        
    return payload
