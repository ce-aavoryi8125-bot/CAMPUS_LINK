"""
CampusLink 2.0 Core Package
Provides security, authentication, authorization, configuration, validation, media processing,
rate limiting, and audit logging primitives.
"""
from .config import PlatformConfig, CommissionService
from .security import hash_password, verify_password, create_access_token, decode_access_token
from .auth_middleware import require_auth, require_roles, get_auth_user_id
from .validators import sanitize_text, validate_email, validate_monetary_amount
from .media import process_and_reencode_image
from .rate_limiter import rate_limit, get_rate_limiter
