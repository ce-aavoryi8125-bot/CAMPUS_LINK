"""
core/config.py
--------------
Centralized Platform Configuration, Secret Validation & Commission Service for CampusLink 2.0.
Provides:
1. Authoritative configuration settings with environment variable overrides.
2. Strict production secret & infrastructure validation (fails fast on default/insecure keys).
3. Centralized CommissionService for financial splits.
"""
import os
import logging
from typing import List, Tuple, Dict, Any
from decimal import Decimal, ROUND_HALF_UP

logger = logging.getLogger("campuslink.config")

class ConfigurationError(Exception):
    """Raised when application configuration violates production security constraints."""
    pass

class PlatformConfig:
    """Platform Configuration Settings with environment variable overrides."""
    
    # Environment Mode
    CAMPUSLINK_ENV = os.environ.get("CAMPUSLINK_ENV", "development").lower()
    
    # Environment & Secret Keys
    SECRET_KEY = os.environ.get("CAMPUSLINK_SECRET_KEY", "campuslink_umat_secret_key_2026")
    JWT_SECRET_KEY = os.environ.get("CAMPUSLINK_JWT_SECRET", "campuslink_umat_jwt_super_secret_key_2026_ghana")
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRATION_HOURS = int(os.environ.get("CAMPUSLINK_JWT_EXP_HOURS", 24))
    
    # Payment Gateway & Webhook Security
    MOMO_WEBHOOK_SECRET = os.environ.get("MOMO_WEBHOOK_SECRET", "campuslink_momo_webhook_secret_2026")
    
    # Insecure default keys prohibited in production
    DEFAULT_INSECURE_SECRETS = {
        "campuslink_umat_secret_key_2026",
        "campuslink_umat_jwt_super_secret_key_2026_ghana",
        "campuslink_momo_webhook_secret_2026",
        "secret", "changeme", "password", "admin", "123456"
    }
    
    # Redis Configuration
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    REDIS_ENABLED = os.environ.get("REDIS_ENABLED", "true").lower() in ("true", "1", "yes")
    REDIS_CONNECT_TIMEOUT_SEC = float(os.environ.get("REDIS_CONNECT_TIMEOUT_SEC", 1.0))
    
    # Celery Background Task Configuration
    CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", os.environ.get("REDIS_URL", "redis://localhost:6379/1"))
    CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", os.environ.get("REDIS_URL", "redis://localhost:6379/2"))
    CELERY_ALWAYS_EAGER = os.environ.get("CELERY_ALWAYS_EAGER", "true").lower() in ("true", "1", "yes")
    CELERY_TASK_TIME_LIMIT_SEC = int(os.environ.get("CELERY_TASK_TIME_LIMIT_SEC", 300))
    
    # Commission Rates
    # NOTE: Default is 10% (0.10) to preserve tested regression baseline.
    # Future 20% model can be enabled via CAMPUSLINK_COMMISSION_RATE=0.20
    DEFAULT_RENTAL_COMMISSION_RATE = Decimal(os.environ.get("CAMPUSLINK_COMMISSION_RATE", "0.10"))
    DEFAULT_SERVICE_COMMISSION_RATE = Decimal(os.environ.get("CAMPUSLINK_SERVICE_COMMISSION_RATE", "0.10"))
    
    # Upload & Media Constraints
    MAX_UPLOAD_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
    MAX_IMAGE_DIMENSION = 2560                # Max width/height in pixels
    ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
    
    # Rate Limiting Defaults
    LOGIN_RATE_LIMIT = (5, 60)         # 5 requests per 60s
    REGISTER_RATE_LIMIT = (3, 600)     # 3 requests per 600s
    PASSWORD_CHANGE_LIMIT = (3, 300)   # 3 requests per 300s
    FINANCIAL_RATE_LIMIT = (5, 60)     # 5 requests per 60s

    @classmethod
    def is_production(cls) -> bool:
        """Returns True if the application is running in production mode."""
        return cls.CAMPUSLINK_ENV == "production"

    @classmethod
    def validate_production_config(cls) -> Tuple[bool, List[str]]:
        """
        Audits configuration against strict production requirements.
        Returns: (is_valid: bool, violations: List[str])
        """
        violations: List[str] = []
        
        # 1. SECRET_KEY validation
        if not cls.SECRET_KEY or cls.SECRET_KEY in cls.DEFAULT_INSECURE_SECRETS:
            violations.append("CAMPUSLINK_SECRET_KEY must be set to a non-default secret in production.")
        elif len(cls.SECRET_KEY) < 32:
            violations.append("CAMPUSLINK_SECRET_KEY must be at least 32 characters long in production.")

        # 2. JWT_SECRET_KEY validation
        if not cls.JWT_SECRET_KEY or cls.JWT_SECRET_KEY in cls.DEFAULT_INSECURE_SECRETS:
            violations.append("CAMPUSLINK_JWT_SECRET must be set to a non-default secret in production.")
        elif len(cls.JWT_SECRET_KEY) < 32:
            violations.append("CAMPUSLINK_JWT_SECRET must be at least 32 characters long in production.")

        # 3. Webhook Secret validation
        if not cls.MOMO_WEBHOOK_SECRET or cls.MOMO_WEBHOOK_SECRET in cls.DEFAULT_INSECURE_SECRETS:
            violations.append("MOMO_WEBHOOK_SECRET must be set to a non-default secret in production.")
        elif len(cls.MOMO_WEBHOOK_SECRET) < 16:
            violations.append("MOMO_WEBHOOK_SECRET must be at least 16 characters long in production.")

        # 4. Database Engine validation
        use_mysql = os.environ.get("USE_MYSQL", "true").lower() in ("true", "1", "yes")
        if not use_mysql:
            violations.append("Production requires MySQL (USE_MYSQL=true); SQLite is strictly prohibited in production.")
        mysql_pass = os.environ.get("MYSQL_PASSWORD", "")
        if not mysql_pass:
            violations.append("MYSQL_PASSWORD must be configured and non-empty in production.")

        # 5. Celery & Worker validation
        if cls.CELERY_ALWAYS_EAGER:
            violations.append("CELERY_ALWAYS_EAGER must be false in production (asynchronous workers required).")

        return len(violations) == 0, violations

    @classmethod
    def assert_production_ready(cls):
        """
        Fails fast if the environment is configured as production but violates security rules.
        In development/testing, logs warning notices instead.
        """
        if cls.is_production():
            valid, violations = cls.validate_production_config()
            if not valid:
                err_msg = "PRODUCTION STARTUP ABORTED due to configuration violations:\n - " + "\n - ".join(violations)
                logger.critical(err_msg)
                raise ConfigurationError(err_msg)
        else:
            # Development/Testing fallback notice
            if cls.SECRET_KEY in cls.DEFAULT_INSECURE_SECRETS:
                logger.debug("Operating with default development SECRET_KEY.")


class CommissionService:
    """
    Centralized Platform Commission Calculation Service.
    All financial split calculations across rentals, services, wallets, and reports
    MUST use this service rather than ad-hoc inline math.
    """
    
    @classmethod
    def get_rental_commission_rate(cls) -> Decimal:
        """Returns active rental platform commission rate (e.g. 0.10 = 10%)."""
        return PlatformConfig.DEFAULT_RENTAL_COMMISSION_RATE

    @classmethod
    def get_service_commission_rate(cls) -> Decimal:
        """Returns active service platform fee rate (e.g. 0.10 = 10%)."""
        return PlatformConfig.DEFAULT_SERVICE_COMMISSION_RATE

    @classmethod
    def calculate_rental_split(cls, gross_amount) -> dict:
        """
        Calculates platform commission and lender net earnings for a rental transaction.
        Returns exact Decimal split: {'gross_amount', 'commission_amount', 'owner_earnings', 'commission_rate'}
        """
        gross = Decimal(str(gross_amount))
        rate = cls.get_rental_commission_rate()
        
        commission = (gross * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        earnings = (gross - commission).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        return {
            "gross_amount": gross,
            "commission_amount": commission,
            "owner_earnings": earnings,
            "commission_rate": rate
        }

    @classmethod
    def calculate_service_split(cls, order_amount) -> dict:
        """
        Calculates platform fee and provider net earnings for a student service order.
        Returns exact Decimal split: {'amount', 'platform_fee', 'provider_earnings', 'fee_rate'}
        """
        amt = Decimal(str(order_amount))
        rate = cls.get_service_commission_rate()
        
        fee = (amt * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        earnings = (amt - fee).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        return {
            "amount": amt,
            "platform_fee": fee,
            "provider_earnings": earnings,
            "fee_rate": rate
        }
