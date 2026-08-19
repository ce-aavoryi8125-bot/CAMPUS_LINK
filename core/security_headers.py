"""
core/security_headers.py
------------------------
OWASP-aligned security headers middleware for CampusLink 2.0.
Injects defense-in-depth headers into all HTTP responses.
"""
from flask import Flask, Response

def register_security_headers(app: Flask):
    """Registers the after_request security header injector on the Flask application."""
    @app.after_request
    def apply_security_headers(response: Response) -> Response:
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Clickjacking defense
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        
        # Legacy XSS protection filter
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Content Security Policy baseline
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "img-src 'self' data: https:; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
            "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
            "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com;"
        )
        
        return response
