"""
Security, Authentication, RBAC, Webhook Verification & Rate Limiting (app/security/auth.py)
Implements:
- Password hashing using PBKDF2-HMAC-SHA256 with random salt
- Signed JWT-style token authentication with expiration
- Role-based access control (admin, manager, executive)
- Meta X-Hub-Signature-256 HMAC-SHA256 verification
- DoubleTick Webhook secret/HMAC verification
- In-memory sliding window rate limiting middleware
- Audit logging helper
"""
import base64
import hashlib
import hmac
import json
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, Optional

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from app.database import Session, get_db
from app.models import AuditLog, User
from app.utils.logger import get_logger, sanitize_dict

logger = get_logger("security")
bearer_scheme = HTTPBearer(auto_error=False)


# 1. Password Hashing (PBKDF2-HMAC-SHA256)
def hash_password(password: str, salt: Optional[str] = None) -> str:
    salt_val = salt or secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt_val.encode("utf-8"),
        120_000,
    )
    return f"pbkdf2_sha256$120000${salt_val}${dk.hex()}"


def verify_password(plain_password: str, stored_hash: str) -> bool:
    if not plain_password or not stored_hash:
        return False
    try:
        parts = stored_hash.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        iterations = int(parts[1])
        salt = parts[2]
        expected_hex = parts[3]
        dk = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
        )
        return hmac.compare_digest(dk.hex(), expected_hex)
    except Exception:
        return False


# 2. Signed Access Tokens (HMAC-SHA256 JWT format)
def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_access_token(
    user_id: str,
    email: str,
    role: str,
    expires_minutes: Optional[int] = None,
) -> str:
    exp_mins = expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    header = {"alg": "HS256", "typ": "JWT"}
    now_ts = int(time.time())
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "iat": now_ts,
        "exp": now_ts + (exp_mins * 60),
    }
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    sig = hmac.new(settings.SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b64 = _b64url_encode(sig)
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_access_token(token: str) -> Dict[str, Any]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid token structure")
        header_b64, payload_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        expected_sig = _b64url_encode(
            hmac.new(settings.SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
        )
        if not hmac.compare_digest(sig_b64, expected_sig):
            raise ValueError("Invalid token signature")
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
        if int(payload.get("exp", 0)) < int(time.time()):
            raise ValueError("Token expired")
        return payload
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired authentication token: {str(exc)}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


# 3. Current User & RBAC Dependencies
def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(credentials.credentials)
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or inactive.",
        )
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges are required to perform this action.",
        )
    return current_user


def require_staff(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in ("admin", "manager", "executive"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions.",
        )
    return current_user


# 4. Webhook Signature Verification
def verify_meta_webhook_signature(
    raw_body: bytes,
    signature_header: Optional[str],
    app_secret: Optional[str] = None,
) -> bool:
    """
    Verifies X-Hub-Signature-256 header sent by Meta Webhooks:
    X-Hub-Signature-256: sha256=<hex_digest>
    """
    secret = app_secret if app_secret is not None else settings.META_APP_SECRET
    if not secret:
        logger.warning("META_APP_SECRET is not configured; rejecting unverified Meta webhook.")
        return False
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    received_sig = signature_header.split("sha256=", 1)[1].strip()
    expected_sig = hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(received_sig, expected_sig)


def verify_doubletick_webhook(
    raw_body: bytes,
    authorization_header: Optional[str] = None,
    signature_header: Optional[str] = None,
    webhook_secret_header: Optional[str] = None,
    configured_secret: Optional[str] = None,
) -> bool:
    """
    Verifies incoming DoubleTick webhook requests according to DoubleTick's
    configured webhook authorization (Bearer token, raw secret token in Authorization
    or X-Webhook-Secret header, or HMAC-SHA256 in X-Doubletick-Signature).
    """
    secret = configured_secret if configured_secret is not None else settings.DOUBLETICK_WEBHOOK_SECRET
    if not secret:
        logger.warning("DOUBLETICK_WEBHOOK_SECRET is not configured; rejecting webhook.")
        return False

    # Check Authorization header (Bearer <secret> or <secret>)
    if authorization_header:
        token = authorization_header.strip()
        if token.lower().startswith("bearer "):
            token = token[7:].strip()
        if hmac.compare_digest(token, secret):
            return True

    # Check X-Webhook-Secret header
    if webhook_secret_header and hmac.compare_digest(webhook_secret_header.strip(), secret):
        return True

    # Check HMAC-SHA256 signature in X-Doubletick-Signature header
    if signature_header:
        sig = signature_header.strip()
        if sig.startswith("sha256="):
            sig = sig.split("sha256=", 1)[1].strip()
        expected_hmac = hmac.new(
            secret.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
        if hmac.compare_digest(sig, expected_hmac) or hmac.compare_digest(sig, secret):
            return True

    return False


# 5. Audit Logging Helper
def record_audit_log(
    db: Session,
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    actor: Optional[User] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    entry = AuditLog(
        actor_id=actor.id if actor else None,
        actor_email=actor.email if actor else "system",
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id else None,
        details=sanitize_dict(details or {}),
        ip_address=ip_address,
    )
    db.add(entry)
    db.commit()
    return entry


# 6. Sliding Window Rate Limiter
class RateLimiter:
    def __init__(self, max_requests_per_minute: int = 120):
        self.max_requests = max_requests_per_minute
        self.window_seconds = 60.0
        self._buckets: Dict[str, Deque[float]] = defaultdict(deque)

    def is_allowed(self, client_key: str) -> bool:
        now = time.time()
        dq = self._buckets[client_key]
        while dq and (now - dq[0]) > self.window_seconds:
            dq.popleft()
        if len(dq) >= self.max_requests:
            return False
        dq.append(now)
        return True


rate_limiter = RateLimiter(max_requests_per_minute=settings.RATE_LIMIT_REQUESTS_PER_MINUTE)
