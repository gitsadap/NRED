from __future__ import annotations

from typing import List


def validate_security_settings(settings) -> List[str]:
    """
    Returns a list of human-readable issues.
    Caller decides whether to warn or fail fast based on environment (e.g., debug flag).
    """
    issues: List[str] = []

    secret_key = (getattr(settings, "secret_key", "") or "").strip()
    admin_password = (getattr(settings, "admin_password", "") or "").strip()

    weak_secret_placeholders = {
        "super-secret-key-please-change-in-env",
        "your-secret-key-here-change-in-production",
        "your-secret-key-here",
        "secret",
        "changeme",
    }
    weak_passwords = {
        "admin",
        "admin123",
        "password",
        "123456",
        "changeme",
        "change-this-password",
    }

    if not secret_key or secret_key in weak_secret_placeholders or len(secret_key) < 32:
        issues.append("SECRET_KEY is weak/placeholder (set a strong random value, >= 32 chars).")

    if not admin_password or admin_password.lower() in weak_passwords or len(admin_password) < 12:
        issues.append("ADMIN_PASSWORD is weak/placeholder (set a strong password, >= 12 chars).")

    return issues

