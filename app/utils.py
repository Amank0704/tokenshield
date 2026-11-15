"""
TokenShield Utility Functions
=============================

Helper functions for authentication, JWT handling, session validation,
request identity, and administrative access.

TokenShield security behavior:
    JWT
      ↓
    Session validation
      ↓
    Account validation
      ↓
    Authenticated route

A session that has been revoked by TokenShield can no longer be used,
even if the JWT itself has not expired.

A hard-locked account cannot authenticate through an existing active
session or create a new session until an administrator unlocks it.
"""

import hashlib
import uuid
from datetime import datetime
from functools import wraps

import jwt

from flask import (
    request,
    jsonify,
    current_app,
)

from app import db
from app.models import Session, User


# ============================================================================
# JWT
# ============================================================================

def generate_token(user_id, username):
    """
    Generate a JWT authentication token for a user.
    """

    now = datetime.utcnow()

    payload = {
        "user_id": user_id,
        "username": username,
        "jti": uuid.uuid4().hex,

        "exp": (
            now
            + current_app.config["JWT_EXPIRATION_DELTA"]
        ),

        "iat": now,
    }

    token = jwt.encode(
        payload,
        current_app.config["JWT_SECRET_KEY"],
        algorithm=current_app.config["JWT_ALGORITHM"],
    )

    return token


def decode_token(token):
    """
    Decode and validate a JWT token.

    Returns:
        dict: decoded payload
        None: invalid/expired token
    """

    try:
        payload = jwt.decode(
            token,
            current_app.config["JWT_SECRET_KEY"],
            algorithms=[
                current_app.config["JWT_ALGORITHM"]
            ],
        )

        return payload

    except jwt.ExpiredSignatureError:
        return None

    except jwt.InvalidTokenError:
        return None

    except Exception:
        return None


# ============================================================================
# TOKEN HASHING
# ============================================================================

def hash_token(token):
    """
    Create a deterministic SHA-256 hash of the authentication token.

    The raw JWT is never stored in the Session table.
    """

    if not token:
        return None

    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


# ============================================================================
# REQUEST IDENTITY
# ============================================================================

def get_client_ip():
    """
    Get the client's IP address.

    Supports:
        X-Forwarded-For
        X-Real-IP
        Flask remote_addr

    X-Forwarded-For is commonly used when the application is behind
    Nginx or another reverse proxy.
    """

    forwarded_for = request.headers.get(
        "X-Forwarded-For"
    )

    if forwarded_for:
        # First address is the original client according to the
        # conventional proxy header format.
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get(
        "X-Real-IP"
    )

    if real_ip:
        return real_ip.strip()

    return request.remote_addr


def get_user_agent():
    """
    Get the browser/client User-Agent.
    """

    return request.headers.get(
        "User-Agent",
        "Unknown",
    )


# ============================================================================
# AUTHENTICATION TOKEN EXTRACTION
# ============================================================================

def _extract_bearer_token():
    """
    Extract a Bearer token from the Authorization header.

    Expected:
        Authorization: Bearer <JWT>

    Returns:
        str | None
    """

    auth_header = request.headers.get(
        "Authorization",
        "",
    ).strip()

    if not auth_header:
        return None

    parts = auth_header.split()

    if len(parts) != 2:
        return None

    if parts[0].lower() != "bearer":
        return None

    return parts[1].strip() or None


# ============================================================================
# ACCOUNT LOCK CHECK
# ============================================================================

def _check_account_lock(user):
    """
    Check whether a user account is currently locked.

    Hard lock:
        user.is_active == False

    Soft lock:
        failed_login_attempts >= 99

    The account_lock module is consulted when available so Redis-backed
    lock metadata can also be considered.

    Returns:
        None if account is allowed.

        Flask response tuple if account must be rejected.
    """

    if user is None:
        return jsonify({
            "success": False,
            "message": "User account does not exist",
        }), 401

    # ------------------------------------------------------------------------
    # HARD LOCK
    # ------------------------------------------------------------------------

    if not user.is_active:
        return jsonify({
            "success": False,
            "message": (
                "Account is locked by TokenShield. "
                "Administrator unlock is required."
            ),
            "account_locked": True,
            "lock_type": "hard",
            "requires_admin_unlock": True,
        }), 403

    # ------------------------------------------------------------------------
    # SOFT LOCK
    # ------------------------------------------------------------------------

    if (
        user.failed_login_attempts or 0
    ) >= 99:

        return jsonify({
            "success": False,
            "message": (
                "Account security lock is active. "
                "Additional authentication is required."
            ),
            "account_locked": True,
            "lock_type": "soft",
            "requires_2fa": True,
        }), 403

    # ------------------------------------------------------------------------
    # Optional account_lock module
    # ------------------------------------------------------------------------

    try:
        from app.middleware.account_lock import (
            is_account_locked,
        )

        locked, lock_info = is_account_locked(
            user.id
        )

        if locked and lock_info:
            lock_type = lock_info.get(
                "lock_type",
                "hard",
            )

            if lock_type == "hard":
                return jsonify({
                    "success": False,
                    "message": (
                        "Account is locked by TokenShield. "
                        "Administrator unlock is required."
                    ),
                    "account_locked": True,
                    "lock_type": "hard",
                    "requires_admin_unlock": True,
                    "lock_info": lock_info,
                }), 403

    except Exception:
        # Database checks above remain authoritative if the optional
        # Redis/account-lock layer is unavailable.
        pass

    return None


# ============================================================================
# TOKEN REQUIRED
# ============================================================================

def token_required(f):
    """
    Decorator for routes that require authentication.

    Security flow:

        Authorization header
                ↓
        Extract JWT
                ↓
        Decode JWT
                ↓
        Locate session by token hash
                ↓
        Confirm session is active
                ↓
        Confirm session belongs to JWT user
                ↓
        Load user
                ↓
        Confirm account is active
                ↓
        Update session activity
                ↓
        Execute protected route
    """

    @wraps(f)
    def decorated(*args, **kwargs):

        # ====================================================================
        # 1. EXTRACT TOKEN
        # ====================================================================

        token = _extract_bearer_token()

        if not token:
            return jsonify({
                "success": False,
                "message": "Authentication token is missing",
            }), 401

        # ====================================================================
        # 2. DECODE JWT
        # ====================================================================

        payload = decode_token(token)

        if not payload:
            return jsonify({
                "success": False,
                "message": "Invalid or expired token",
            }), 401

        # ====================================================================
        # 3. VALIDATE USER ID FROM JWT
        # ====================================================================

        user_id = payload.get(
            "user_id"
        )

        if user_id is None:
            return jsonify({
                "success": False,
                "message": "Invalid authentication payload",
            }), 401

        # ====================================================================
        # 4. FIND ACTIVE SESSION
        # ====================================================================

        token_hash = hash_token(token)

        if not token_hash:
            return jsonify({
                "success": False,
                "message": "Invalid authentication token",
            }), 401

        session = Session.query.filter_by(
            token=token_hash,
            is_active=True,
        ).first()

        # --------------------------------------------------------------------
        # This is the critical TokenShield protection.
        #
        # A JWT can still be cryptographically valid while its corresponding
        # database session has already been revoked.
        #
        # Therefore JWT validation alone is NOT sufficient.
        # --------------------------------------------------------------------

        if not session:
            return jsonify({
                "success": False,
                "message": (
                    "Session has been revoked or does not exist"
                ),
                "session_revoked": True,
            }), 401

        # ====================================================================
        # 5. LOAD USER
        # ====================================================================

        user = User.query.get(
            user_id
        )

        if not user:
            return jsonify({
                "success": False,
                "message": "User account does not exist",
            }), 401

        # ====================================================================
        # 6. SESSION ↔ JWT USER CONSISTENCY CHECK
        # ====================================================================

        if session.user_id != user.id:
            return jsonify({
                "success": False,
                "message": "Authentication session mismatch",
            }), 401

        # ====================================================================
        # 7. ACCOUNT LOCK CHECK
        # ====================================================================

        lock_response = _check_account_lock(
            user
        )

        if lock_response:
            return lock_response

        # ====================================================================
        # 8. UPDATE SESSION ACTIVITY
        # ====================================================================

        session.last_activity = datetime.utcnow()

        try:
            db.session.commit()

        except Exception:
            db.session.rollback()

            return jsonify({
                "success": False,
                "message": "Unable to update session",
            }), 500

        # ====================================================================
        # 9. EXECUTE PROTECTED ROUTE
        # ====================================================================

        return f(
            current_user=user,
            current_session=session,
            *args,
            **kwargs,
        )

    return decorated


# ============================================================================
# ADMIN REQUIRED
# ============================================================================

def admin_required(f):
    """
    Decorator for routes that require administrator privileges.

    IMPORTANT:
        This decorator expects token_required to have already supplied
        current_user.

    Example:

        @app.route("/admin/example")
        @token_required
        @admin_required
        def example(current_user, current_session):
            ...
    """

    @wraps(f)
    def decorated(*args, **kwargs):

        current_user = kwargs.get(
            "current_user"
        )

        if not current_user:
            return jsonify({
                "success": False,
                "message": "Authentication required",
            }), 401

        if not current_user.is_active:
            return jsonify({
                "success": False,
                "message": "Account is inactive",
            }), 403

        if not current_user.is_admin:
            return jsonify({
                "success": False,
                "message": "Admin privileges required",
            }), 403

        return f(
            *args,
            **kwargs,
        )

    return decorated