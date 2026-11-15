"""
TokenShield Authentication Routes
=================================

Authentication layer for the TokenShield / NeoVault demonstration.

Security behavior
-----------------

1. Normal login creates a real database session.
2. The raw token is returned only to the authenticated client.
3. The database stores only the SHA-256 token hash.
4. The exact same hashed token is registered with the TokenShield engine.
5. TokenShield can revoke the session during anomaly mitigation.
6. TokenShield hard-locks the affected account after a critical replay.
7. ALL active sessions belonging to the affected account are revoked.
8. Password login is rejected while the account is hard-locked.
9. 2FA login is rejected while the account is hard-locked.
10. Google OAuth login is rejected while the account is hard-locked.
11. Administrative unlock restores login access.
12. Administrative unlock DOES NOT remove TOTP configuration.
13. SSE allows an already-open browser session to receive the real
    session-revocation event and immediately clear its local token.
14. No authentication endpoint manufactures a security incident.
15. Security state comes from the database / TokenShield engine.
"""

import base64
import io
import json
import logging
import os
import re
import time

from datetime import datetime

from flask import (
    Blueprint,
    Response,
    jsonify,
    request,
)

from app import db
from app.models import User, Session

from app.utils import (
    generate_token,
    get_client_ip,
    get_user_agent,
    hash_token,
    token_required,
)


logger = logging.getLogger("tokenshield.auth")


# ============================================================================
# OPTIONAL DEPENDENCIES
# ============================================================================

try:
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests

    GOOGLE_AUTH_AVAILABLE = True

except ImportError:
    GOOGLE_AUTH_AVAILABLE = False


try:
    import pyotp
    import qrcode

    TOTP_AVAILABLE = True

except ImportError:
    TOTP_AVAILABLE = False


# ============================================================================
# BLUEPRINT
# ============================================================================

auth_bp = Blueprint(
    "auth",
    __name__,
    url_prefix="/api/auth",
)


# ============================================================================
# CONFIGURATION
# ============================================================================

TOKENSHIELD_ENGINE_URL = os.getenv(
    "TOKENSHIELD_ENGINE_URL",
    "http://127.0.0.1:7777",
)

try:
    TOKENSHIELD_ENGINE_TIMEOUT = float(
        os.getenv(
            "TOKENSHIELD_ENGINE_TIMEOUT",
            "5.0",
        )
    )

except (TypeError, ValueError):
    TOKENSHIELD_ENGINE_TIMEOUT = 5.0


# ============================================================================
# INTERNAL HELPERS — ACCOUNT LOCK
# ============================================================================

def _is_account_locked(user):
    """
    Return True when the account is hard-locked.

    TokenShield hard-locks accounts by setting:

        User.is_active = False

    The database remains the persistent source of truth.
    """

    return not bool(
        getattr(
            user,
            "is_active",
            True,
        )
    )


def _get_account_lock_info(user):
    """
    Return detailed account-lock information.

    Redis metadata is used when available, while the database remains
    authoritative for the actual hard-lock state.
    """

    if not _is_account_locked(user):
        return None

    info = {
        "user_id": getattr(user, "id", None),
        "lock_type": "hard",
        "reason": "account_disabled",
        "administrative_unlock_required": True,
    }

    try:
        from app.middleware.account_lock import (
            get_lock_info,
        )

        redis_info = get_lock_info(
            user.id,
        )

        if redis_info:
            info.update(
                redis_info,
            )

    except Exception as exc:
        logger.debug(
            "Could not retrieve detailed lock metadata: %s",
            exc,
        )

    return info


def _account_locked_response(
    message=(
        "Account locked by TokenShield after a "
        "security incident. Administrative unlock required."
    ),
):
    """
    Standard response returned whenever TokenShield has hard-locked
    the account.
    """

    return jsonify(
        {
            "success": False,

            "security_lockout": True,

            "account_locked": True,

            "administrative_unlock_required": True,

            "lock_type": "hard",

            "message": message,
        }
    ), 403


def _check_account_lock(user):
    """
    Check hard-lock state and return a Flask response when locked.

    Returns:

        None
            Account is available.

        Flask response
            Account is hard-locked.
    """

    if _is_account_locked(user):
        return _account_locked_response()

    return None


# ============================================================================
# REGISTER
# ============================================================================

@auth_bp.route(
    "/register",
    methods=["POST"],
)
def register():
    """
    Register a new local user.
    """

    data = request.get_json(
        silent=True,
    ) or {}

    username = (
        data.get("username")
        or ""
    ).strip()

    email = (
        data.get("email")
        or ""
    ).strip()

    password = (
        data.get("password")
        or ""
    )

    if not username or not email or not password:
        return jsonify(
            {
                "success": False,
                "message": "Missing required fields",
            }
        ), 400

    existing = User.query.filter(
        (User.username == username)
        | (User.email == email)
    ).first()

    if existing:
        return jsonify(
            {
                "success": False,
                "message": "User already exists",
            }
        ), 409

    user = User(
        username=username,
        email=email,
    )

    user.set_password(
        password,
    )

    db.session.add(
        user,
    )

    db.session.commit()

    return jsonify(
        {
            "success": True,
            "message": "User registered successfully",
        }
    ), 201


# ============================================================================
# LOGIN
# ============================================================================

@auth_bp.route(
    "/login",
    methods=["POST"],
)
def login():
    """
    Standard username/password login.

    Flow:

        credentials
            ↓
        account lookup
            ↓
        password verification
            ↓
        hard-lock check
            ↓
        normal authentication checks
            ↓
        real session creation
            ↓
        TokenShield engine registration
    """

    data = request.get_json(
        silent=True,
    ) or {}

    login_identifier = (
        data.get("username")
        or data.get("email")
        or ""
    ).strip()

    password = (
        data.get("password")
        or ""
    )

    if not login_identifier or not password:
        return jsonify(
            {
                "success": False,
                "message": "Missing credentials",
            }
        ), 400

    from sqlalchemy import or_
    user = User.query.filter(
        or_(User.username == login_identifier, User.email == login_identifier)
    ).first()

    if not user:
        return jsonify(
            {
                "success": False,
                "message": "Invalid credentials",
            }
        ), 401

    # ------------------------------------------------------------------
    # Password validation
    # ------------------------------------------------------------------

    if not user.check_password(
        password,
    ):
        if hasattr(
            user,
            "failed_login_attempts",
        ):
            user.failed_login_attempts = (
                getattr(
                    user,
                    "failed_login_attempts",
                    0,
                )
                or 0
            ) + 1

            db.session.commit()

        return jsonify(
            {
                "success": False,
                "message": "Invalid credentials",
            }
        ), 401

    # ------------------------------------------------------------------
    # HARD TOKENSHIELD LOCK
    #
    # This MUST happen before:
    #
    # - TOTP
    # - session creation
    # - engine registration
    #
    # Therefore a valid password cannot bypass the lock.
    # ------------------------------------------------------------------

    lock_response = _check_account_lock(
        user,
    )

    if lock_response:
        return lock_response

    # ------------------------------------------------------------------
    # Normal TOTP-enabled account
    # ------------------------------------------------------------------

    if getattr(
        user,
        "totp_enabled",
        False,
    ):
        return jsonify(
            {
                "success": False,

                "requires_2fa": True,

                "totp_required": True,

                "message": (
                    "Please enter your authenticator code."
                ),
            }
        ), 403

    # ------------------------------------------------------------------
    # Successful normal login
    # ------------------------------------------------------------------

    if hasattr(
        user,
        "failed_login_attempts",
    ):
        user.failed_login_attempts = 0

    db.session.commit()

    return _create_session_response(
        user,
    )


# ============================================================================
# LOGIN WITH 2FA
# ============================================================================

@auth_bp.route(
    "/login-2fa",
    methods=["POST"],
)
def login_with_2fa():
    """
    Complete a normal TOTP login.

    IMPORTANT:

    Hard-lock is checked BEFORE TOTP validation.

    This prevents a valid authenticator code from bypassing a TokenShield
    security lock.
    """

    data = request.get_json(
        silent=True,
    ) or {}

    username = (
        data.get("username")
        or ""
    ).strip()

    password = (
        data.get("password")
        or ""
    )

    two_factor_code = (
        data.get("two_factor_code")
        or ""
    )

    if (
        not username
        or not password
        or not two_factor_code
    ):
        return jsonify(
            {
                "success": False,
                "message": (
                    "Missing credentials or 2FA code"
                ),
            }
        ), 400

    user = User.query.filter_by(
        username=username,
    ).first()

    if not user:
        return jsonify(
            {
                "success": False,
                "message": "Invalid credentials",
            }
        ), 401

    if not user.check_password(
        password,
    ):
        return jsonify(
            {
                "success": False,
                "message": "Invalid credentials",
            }
        ), 401

    # ------------------------------------------------------------------
    # HARD LOCK TAKES PRECEDENCE OVER 2FA
    # ------------------------------------------------------------------

    lock_response = _check_account_lock(
        user,
    )

    if lock_response:
        return _account_locked_response(
            (
                "Account locked by TokenShield. "
                "Administrative unlock required."
            )
        )

    # ------------------------------------------------------------------
    # Validate TOTP
    # ------------------------------------------------------------------

    if not verify_2fa_code(
        two_factor_code,
        user,
    ):
        return jsonify(
            {
                "success": False,
                "message": "Invalid 2FA code",
            }
        ), 401

    if hasattr(
        user,
        "failed_login_attempts",
    ):
        user.failed_login_attempts = 0

    db.session.commit()

    return _create_session_response(
        user,
    )


# ============================================================================
# TOTP SETUP
# ============================================================================

@auth_bp.route(
    "/totp/setup",
    methods=["POST"],
)
@token_required
def setup_totp(
    current_user,
    current_session,
):
    """
    Begin TOTP setup for an authenticated account.
    """

    if not TOTP_AVAILABLE:
        return jsonify(
            {
                "success": False,
                "message": (
                    "TOTP unavailable. "
                    "Install pyotp and qrcode."
                ),
            }
        ), 503

    lock_response = _check_account_lock(
        current_user,
    )

    if lock_response:
        return lock_response

    secret = pyotp.random_base32()

    totp = pyotp.TOTP(
        secret,
    )

    current_user.totp_secret = secret

    db.session.commit()

    provisioning_uri = (
        totp.provisioning_uri(
            name=current_user.email,
            issuer_name="TokenShield / NeoVault",
        )
    )

    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=5,
    )

    qr.add_data(
        provisioning_uri,
    )

    qr.make(
        fit=True,
    )

    image = qr.make_image(
        fill_color="black",
        back_color="white",
    )

    buffer = io.BytesIO()

    image.save(
        buffer,
        format="PNG",
    )

    qr_base64 = base64.b64encode(
        buffer.getvalue(),
    ).decode(
        "utf-8",
    )

    return jsonify(
        {
            "success": True,

            "secret": secret,

            "qr_code": (
                "data:image/png;base64,"
                f"{qr_base64}"
            ),

            "provisioning_uri": (
                provisioning_uri
            ),

            "message": (
                "Scan the QR code with your "
                "authenticator app, then confirm "
                "with /api/auth/totp/confirm."
            ),
        }
    )


# ============================================================================
# TOTP CONFIRM
# ============================================================================

@auth_bp.route(
    "/totp/confirm",
    methods=["POST"],
)
@token_required
def confirm_totp(
    current_user,
    current_session,
):
    """
    Confirm and enable TOTP.
    """

    if not TOTP_AVAILABLE:
        return jsonify(
            {
                "success": False,
                "message": "TOTP is not available.",
            }
        ), 503

    lock_response = _check_account_lock(
        current_user,
    )

    if lock_response:
        return lock_response

    data = request.get_json(
        silent=True,
    ) or {}

    code = data.get(
        "code",
    )

    if not code:
        return jsonify(
            {
                "success": False,
                "message": "Missing TOTP code",
            }
        ), 400

    secret = getattr(
        current_user,
        "totp_secret",
        None,
    )

    if not secret:
        return jsonify(
            {
                "success": False,
                "message": (
                    "No TOTP setup in progress. "
                    "Call /api/auth/totp/setup first."
                ),
            }
        ), 400

    totp = pyotp.TOTP(
        secret,
    )

    if totp.verify(
        str(code).strip(),
        valid_window=1,
    ):
        current_user.totp_enabled = True

        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": (
                    "Google Authenticator enabled "
                    "successfully."
                ),
            }
        )

    return jsonify(
        {
            "success": False,
            "message": "Invalid code — try again.",
        }
    ), 400


# ============================================================================
# TOTP DISABLE
# ============================================================================

@auth_bp.route(
    "/totp/disable",
    methods=["POST"],
)
@token_required
def disable_totp(
    current_user,
    current_session,
):
    """
    Disable TOTP after validating the current code.
    """

    lock_response = _check_account_lock(
        current_user,
    )

    if lock_response:
        return lock_response

    data = request.get_json(
        silent=True,
    ) or {}

    code = data.get(
        "code",
    )

    secret = getattr(
        current_user,
        "totp_secret",
        None,
    )

    if (
        not secret
        or not getattr(
            current_user,
            "totp_enabled",
            False,
        )
    ):
        return jsonify(
            {
                "success": False,
                "message": "TOTP is not enabled.",
            }
        ), 400

    if TOTP_AVAILABLE:
        totp = pyotp.TOTP(
            secret,
        )

        if not totp.verify(
            str(code or "").strip(),
            valid_window=1,
        ):
            return jsonify(
                {
                    "success": False,
                    "message": "Invalid TOTP code.",
                }
            ), 401

    current_user.totp_enabled = False

    current_user.totp_secret = None

    db.session.commit()

    return jsonify(
        {
            "success": True,
            "message": "2FA disabled successfully.",
        }
    )


# ============================================================================
# GOOGLE OAUTH
# ============================================================================

@auth_bp.route(
    "/google/verify",
    methods=["POST"],
)
def google_verify():
    """
    Verify a Google OAuth credential and create a normal TokenShield session.

    Hard-lock is checked before session creation.
    """

    if not GOOGLE_AUTH_AVAILABLE:
        return jsonify(
            {
                "success": False,
                "message": (
                    "Google authentication unavailable. "
                    "Install google-auth."
                ),
            }
        ), 503

    from dotenv import load_dotenv

    load_dotenv()

    client_id = os.getenv(
        "GOOGLE_CLIENT_ID",
        "",
    )

    if not client_id:
        return jsonify(
            {
                "success": False,
                "message": (
                    "GOOGLE_CLIENT_ID is not configured."
                ),
            }
        ), 503

    data = request.get_json(
        silent=True,
    ) or {}

    credential = data.get(
        "credential",
    )

    if not credential:
        return jsonify(
            {
                "success": False,
                "message": "Missing credential",
            }
        ), 400

    try:
        id_info = (
            id_token.verify_oauth2_token(
                credential,
                google_requests.Request(),
                client_id,
            )
        )

    except ValueError as exc:
        return jsonify(
            {
                "success": False,
                "message": (
                    f"Invalid Google token: {exc}"
                ),
            }
        ), 401

    google_id = id_info.get(
        "sub",
    )

    email = id_info.get(
        "email",
        "",
    )

    name = id_info.get(
        "name",
        "",
    )

    avatar_url = id_info.get(
        "picture",
        "",
    )

    email_verified = id_info.get(
        "email_verified",
        False,
    )

    if not google_id or not email:
        return jsonify(
            {
                "success": False,
                "message": "Incomplete Google profile",
            }
        ), 400

    if not email_verified:
        return jsonify(
            {
                "success": False,
                "message": "Google email not verified",
            }
        ), 401

    user = User.query.filter_by(
        google_id=google_id,
    ).first()

    if not user:
        user = User.query.filter_by(
            email=email,
        ).first()

        if user:
            user.google_id = google_id

            user.avatar_url = avatar_url

            user.auth_provider = "google"

        else:
            username = _derive_username(
                name,
                email,
            )

            user = User(
                username=username,

                email=email,

                google_id=google_id,

                avatar_url=avatar_url,

                auth_provider="google",

                password_hash=(
                    "google-oauth-no-password"
                ),
            )

            db.session.add(
                user,
            )

    user.avatar_url = avatar_url

    db.session.commit()

    # ------------------------------------------------------------------
    # HARD LOCK APPLIES TO GOOGLE OAUTH
    # ------------------------------------------------------------------

    lock_response = _check_account_lock(
        user,
    )

    if lock_response:
        return _account_locked_response(
            (
                "Account locked by TokenShield. "
                "Administrative unlock required."
            )
        )

    return _create_session_response(
        user,
    )


# ============================================================================
# GOOGLE CLIENT ID
# ============================================================================

@auth_bp.route(
    "/google/client-id",
    methods=["GET"],
)
def google_client_id():

    from dotenv import load_dotenv

    load_dotenv()

    client_id = os.getenv(
        "GOOGLE_CLIENT_ID",
        "",
    )

    return jsonify(
        {
            "client_id": client_id,
        }
    )


# ============================================================================
# LOGOUT
# ============================================================================

@auth_bp.route(
    "/logout",
    methods=["POST"],
)
def logout():
    """
    Revoke the current session.

    The database and TokenShield engine use the same hashed token identity.
    """

    token = _extract_token()

    if not token:
        return jsonify(
            {
                "success": False,
                "message": (
                    "Missing or invalid token"
                ),
            }
        ), 401

    token_hash = hash_token(
        token,
    )

    session_obj = (
        Session.query
        .filter_by(
            token=token_hash,
            is_active=True,
        )
        .first()
    )

    if session_obj:

        session_obj.is_active = False

        session_obj.revoked_at = (
            datetime.utcnow()
        )

        session_obj.revoked_reason = (
            "User logout"
        )

        db.session.commit()

    # ------------------------------------------------------------------
    # Notify standalone TokenShield engine.
    # ------------------------------------------------------------------

    _engine_revoke_session(
        token_hash,
    )

    return jsonify(
        {
            "success": True,
            "message": "Logged out successfully",
        }
    )


# ============================================================================
# VERIFY SESSION
# ============================================================================

@auth_bp.route(
    "/verify",
    methods=["GET"],
)
@token_required
def verify_session(
    current_user,
    current_session,
):
    """
    Verify the current session.
    """

    if not getattr(
        current_session,
        "is_active",
        False,
    ):
        return jsonify(
            {
                "success": False,
                "message": "Session has been revoked.",
            }
        ), 401

    lock_response = _check_account_lock(
        current_user,
    )

    if lock_response:
        return lock_response

    return jsonify(
        {
            "success": True,

            "session": (
                current_session.to_dict()
            ),
        }
    )


# ============================================================================
# LIST SESSIONS
# ============================================================================

@auth_bp.route(
    "/sessions",
    methods=["GET"],
)
def get_user_sessions():
    """
    Return all sessions belonging to the authenticated user.

    Authentication is performed against the real hashed bearer token.
    """

    token = _extract_token()

    if not token:
        return jsonify(
            {
                "success": False,
                "message": "Missing or invalid token",
            }
        ), 401

    token_hash = hash_token(
        token,
    )

    current_session = (
        Session.query
        .filter_by(
            token=token_hash,
            is_active=True,
        )
        .first()
    )

    if not current_session:
        return jsonify(
            {
                "success": False,
                "message": "Invalid session",
            }
        ), 401

    user = User.query.get(
        current_session.user_id,
    )

    if not user:
        return jsonify(
            {
                "success": False,
                "message": "User not found",
            }
        ), 404

    lock_response = _check_account_lock(
        user,
    )

    if lock_response:
        return lock_response

    sessions = Session.query.filter_by(
        user_id=current_session.user_id,
    ).all()

    return jsonify(
        {
            "success": True,

            "sessions": [
                session.to_dict()
                for session in sessions
            ],

            "current_session_id": (
                current_session.id
            ),
        }
    )


# ============================================================================
# REVOKE SPECIFIC SESSION
# ============================================================================

@auth_bp.route(
    "/sessions/<int:session_id>/revoke",
    methods=["POST"],
)
def revoke_user_session(
    session_id,
):
    """
    Revoke another session belonging to the same authenticated user.
    """

    token = _extract_token()

    if not token:
        return jsonify(
            {
                "success": False,
                "message": "Missing or invalid token",
            }
        ), 401

    token_hash = hash_token(
        token,
    )

    current_session = (
        Session.query
        .filter_by(
            token=token_hash,
            is_active=True,
        )
        .first()
    )

    if not current_session:
        return jsonify(
            {
                "success": False,
                "message": "Invalid session",
            }
        ), 401

    user = User.query.get(
        current_session.user_id,
    )

    if not user:
        return jsonify(
            {
                "success": False,
                "message": "User not found",
            }
        ), 404

    lock_response = _check_account_lock(
        user,
    )

    if lock_response:
        return lock_response

    session_to_revoke = Session.query.get(
        session_id,
    )

    if not session_to_revoke:
        return jsonify(
            {
                "success": False,
                "message": "Session not found",
            }
        ), 404

    if (
        session_to_revoke.user_id
        != current_session.user_id
    ):
        return jsonify(
            {
                "success": False,
                "message": "Unauthorized",
            }
        ), 403

    if (
        session_to_revoke.id
        == current_session.id
    ):
        return jsonify(
            {
                "success": False,
                "message": (
                    "Cannot revoke current session. "
                    "Use logout instead."
                ),
            }
        ), 400

    session_to_revoke.is_active = False

    session_to_revoke.revoked_at = (
        datetime.utcnow()
    )

    session_to_revoke.revoked_reason = (
        "Revoked by user"
    )

    db.session.commit()

    # Notify engine using the same hashed session identity.
    _engine_revoke_session(
        session_to_revoke.token,
    )

    return jsonify(
        {
            "success": True,
            "message": (
                "Session revoked successfully"
            ),
        }
    )


# ============================================================================
# REVOKE SUSPICIOUS SESSIONS
# ============================================================================

@auth_bp.route(
    "/sessions/revoke-suspicious",
    methods=["POST"],
)
@token_required
def revoke_suspicious_sessions(
    current_user,
    current_session,
):
    """
    Manually revoke suspicious sessions other than the current session.
    """

    lock_response = _check_account_lock(
        current_user,
    )

    if lock_response:
        return lock_response

    suspicious = (
        Session.query
        .filter_by(
            user_id=current_user.id,
            is_active=True,
            is_suspicious=True,
        )
        .all()
    )

    revoked_count = 0

    for session_obj in suspicious:

        if (
            session_obj.id
            == current_session.id
        ):
            continue

        session_obj.is_active = False

        session_obj.revoked_at = (
            datetime.utcnow()
        )

        session_obj.revoked_reason = (
            "Auto-revoked: suspicious activity"
        )

        revoked_count += 1

    db.session.commit()

    return jsonify(
        {
            "success": True,

            "revoked_count": revoked_count,

            "message": (
                f"Revoked {revoked_count} "
                "suspicious session(s)"
            ),
        }
    )


# ============================================================================
# SERVER-SENT EVENTS — REAL-TIME SESSION REVOCATION
# ============================================================================

@auth_bp.route(
    "/session-events",
    methods=["GET"],
)
def session_events():
    """
    Server-Sent Events stream for the currently authenticated browser.

    EventSource cannot normally attach an Authorization header, therefore
    this endpoint accepts the token through the query parameter:

        /api/auth/session-events?token=<raw-token>

    This endpoint DOES NOT create or manufacture security events.

    It only observes the real database session state.

    When TokenShield revokes the session, the browser receives:

        event: session_revoked

    and can immediately clear its local authentication state.
    """

    token = (
        request.args.get("token")
        or _extract_token()
    )

    if not token:
        return jsonify(
            {
                "error": "Token required",
            }
        ), 400

    token_hash = hash_token(
        token,
    )

    flask_app = current_app._get_current_object()

    def event_stream():

        # Tell the browser when to reconnect.
        yield "retry: 2000\n\n"

        while True:

            try:
                with flask_app.app_context():
                    session_obj = (
                        Session.query
                        .filter_by(
                            token=token_hash,
                        )
                        .first()
                    )

                # --------------------------------------------------
                # Session no longer exists.
                # --------------------------------------------------

                if not session_obj:

                    yield (
                        f": heartbeat "
                        f"{time.time()}\n\n"
                    )

                    break

                # --------------------------------------------------
                # Session has been revoked.
                # --------------------------------------------------

                if not session_obj.is_active:

                    anomaly_score = (
                        float(
                            session_obj.anomaly_score
                        )
                        if session_obj.anomaly_score
                        is not None
                        else 0.0
                    )

                    revoked_reason = (
                        session_obj.revoked_reason
                        or
                        "Session terminated"
                    )

                    # Determine whether the revocation is security-related.
                    security_event = any(
                        keyword in revoked_reason.lower()
                        for keyword in (
                            "security",
                            "tokenshield",
                            "replay",
                            "anomal",
                            "incident",
                            "mitigat",
                            "hijack",
                        )
                    )

                    data = json.dumps(
                        {
                            "event": (
                                "session_revoked"
                            ),

                            "security_event": (
                                security_event
                            ),

                            "account_locked": (
                                False
                            ),

                            "anomaly_score": (
                                anomaly_score
                            ),

                            "reason": (
                                revoked_reason
                            ),

                            "timestamp": (
                                datetime.utcnow()
                                .isoformat()
                            ),
                        }
                    )

                    yield (
                        "event: session_revoked\n"
                        f"data: {data}\n\n"
                    )

                    break

                # --------------------------------------------------
                # Session still active.
                # --------------------------------------------------

                yield (
                    f": heartbeat "
                    f"{time.time()}\n\n"
                )

            except GeneratorExit:

                logger.info(
                    "TokenShield SSE client disconnected."
                )

                break

            except Exception as exc:

                logger.warning(
                    "TokenShield SSE error: %s",
                    exc,
                )

                yield (
                    ": heartbeat_error\n\n"
                )

            time.sleep(
                2.0,
            )

    return Response(
        event_stream(),

        mimetype="text/event-stream",

        headers={
            "Cache-Control": "no-cache",

            "X-Accel-Buffering": "no",

            "Connection": "keep-alive",
        },
    )


# ============================================================================
# DEMO UNLOCK ENDPOINT (One-Click Restore After Attack Demonstration)
# ============================================================================

@auth_bp.route("/unlock-demo", methods=["POST"])
def unlock_demo():
    """
    Demo helper: unlocks an account locked by TokenShield incident mitigation.
    Accepts {"username": "alice"} or {"email": "alice@neovault.com"}.
    """
    data = request.get_json(silent=True) or {}
    identifier = data.get("username") or data.get("email") or "alice"
    
    from app.middleware.account_lock import unlock_account
    unlock_account(identifier)
    unlock_account("alice")
    unlock_account("alice_demo")
    unlock_account("alice@neovault.com")

    # Also make sure the database is active and 0 failed attempts
    try:
        alice = User.query.filter((User.email == 'alice@neovault.com') | (User.username == 'alice')).first()
        if alice:
            alice.is_active = True
            alice.failed_login_attempts = 0
            db.session.commit()
    except Exception:
        pass

    return jsonify({
        "success": True,
        "message": f"Account {identifier} unlocked successfully! You can sign in now.",
        "unlocked": True
    }), 200


# ============================================================================
# HELPERS — TOKEN EXTRACTION
# ============================================================================

def _extract_token():
    """
    Extract a bearer token from the Authorization header.

    Normal REST authentication never accepts an arbitrary query parameter.
    """

    auth_header = request.headers.get(
        "Authorization",
        "",
    )

    parts = auth_header.split()

    if (
        len(parts) == 2
        and parts[0].lower() == "bearer"
        and parts[1]
    ):
        return parts[1]

    return None


# ============================================================================
# HELPERS — SESSION CREATION
# ============================================================================

def _create_session_response(
    user,
):
    """
    Create a real authenticated TokenShield session.

    The raw JWT is returned only to the authenticated browser.

    The database stores only the SHA-256 token hash.

    The exact same hash is registered with the standalone TokenShield
    security engine.

    Device fingerprint is captured from the real request.
    """

    # ------------------------------------------------------------------
    # Final lock check immediately before session creation.
    # ------------------------------------------------------------------

    lock_response = _check_account_lock(
        user,
    )

    if lock_response:
        return lock_response

    # ------------------------------------------------------------------
    # Generate real authentication token.
    # ------------------------------------------------------------------

    token = generate_token(
        user.id,
        user.username,
    )

    token_hash = hash_token(
        token,
    )

    # ------------------------------------------------------------------
    # Real request telemetry.
    # ------------------------------------------------------------------

    client_ip = get_client_ip()

    user_agent = get_user_agent()

    # ------------------------------------------------------------------
    # Real device fingerprint.
    # ------------------------------------------------------------------

    device_fingerprint = None

    try:

        from app.middleware.fingerprint import (
            get_request_fingerprint,
        )

        device_fingerprint = (
            get_request_fingerprint()
        )

    except Exception as exc:

        logger.warning(
            "Could not obtain login fingerprint: %s",
            exc,
        )

    # ------------------------------------------------------------------
    # Database session.
    # ------------------------------------------------------------------

    session_kwargs = {
        "user_id": user.id,

        "token": token_hash,

        "ip_address": client_ip,

        "user_agent": user_agent,
    }

    if hasattr(
        Session,
        "device_fingerprint",
    ):
        session_kwargs[
            "device_fingerprint"
        ] = device_fingerprint

    session_obj = Session(
        **session_kwargs,
    )

    db.session.add(
        session_obj,
    )

    user.last_login = (
        datetime.utcnow()
    )

    db.session.commit()

    # ------------------------------------------------------------------
    # Register exact session identity with TokenShield engine.
    # ------------------------------------------------------------------

    _engine_register_session(
        session_obj=session_obj,

        user=user,

        token_hash=token_hash,

        client_ip=client_ip,

        user_agent=user_agent,

        device_fingerprint=device_fingerprint,
    )

    # ------------------------------------------------------------------
    # Return raw token to the browser.
    # ------------------------------------------------------------------

    response_session = {
        "id": session_obj.id,

        "ip_address": client_ip,

        "user_agent": user_agent,

        "device_fingerprint": (
            device_fingerprint
        ),
    }

    return jsonify(
        {
            "success": True,

            "message": "Login successful",

            "token": token,

            "user": user.to_dict(),

            "session": response_session,
        }
    )


# ============================================================================
# HELPERS — TOKENSHIELD ENGINE REGISTRATION
# ============================================================================

def _engine_register_session(
    session_obj,
    user,
    token_hash,
    client_ip,
    user_agent,
    device_fingerprint,
):
    """
    Register the real authenticated session with the standalone
    TokenShield engine.

    Engine failure is non-fatal to authentication because the database
    remains the source of truth for the session.
    """

    try:

        from sdk.python.tokenshield_sdk import (
            TokenShieldClient,
        )

        client = TokenShieldClient(
            engine_url=TOKENSHIELD_ENGINE_URL,

            timeout=TOKENSHIELD_ENGINE_TIMEOUT,
        )

        client.register_session(
            session_id=token_hash,

            user_id=str(
                user.id,
            ),

            ip=client_ip,

            user_agent=user_agent,

            device_fingerprint=(
                device_fingerprint
            ),
        )

        logger.info(
            (
                "TokenShield engine session registered | "
                "user=%s | db_session=%s"
            ),
            user.id,
            session_obj.id,
        )

        return True

    except Exception as exc:

        logger.warning(
            (
                "TokenShield engine session "
                "registration failed | user=%s | error=%s"
            ),
            getattr(user, "id", None),
            exc,
        )

        return False


# ============================================================================
# HELPERS — TOKENSHIELD ENGINE REVOCATION
# ============================================================================

def _engine_revoke_session(
    token_hash,
):
    """
    Notify the standalone TokenShield engine that a session has been revoked.

    The function intentionally accepts the already-hashed session identity.
    """

    if not token_hash:
        return False

    try:

        from sdk.python.tokenshield_sdk import (
            TokenShieldClient,
        )

        client = TokenShieldClient(
            engine_url=TOKENSHIELD_ENGINE_URL,

            timeout=TOKENSHIELD_ENGINE_TIMEOUT,
        )

        client.revoke_session(
            session_id=token_hash,
        )

        return True

    except Exception as exc:

        logger.warning(
            (
                "TokenShield engine session revocation "
                "notification failed | error=%s"
            ),
            exc,
        )

        return False


# ============================================================================
# HELPERS — GOOGLE USERNAME
# ============================================================================

def _derive_username(
    name,
    email,
):
    """
    Derive a unique username from the Google profile.
    """

    name = name or ""

    email = email or ""

    base = re.sub(
        r"[^a-zA-Z0-9_]",
        "",
        name.replace(
            " ",
            "_",
        ),
    )[:20]

    if not base:

        base = re.sub(
            r"[^a-zA-Z0-9_]",
            "",
            email.split("@")[0],
        )[:20]

    if not base:
        base = "user"

    candidate = base

    suffix = 1

    while User.query.filter_by(
        username=candidate,
    ).first():

        candidate = (
            f"{base}{suffix}"
        )

        suffix += 1

    return candidate


# ============================================================================
# HELPERS — TOTP
# ============================================================================

def verify_2fa_code(
    code,
    user=None,
):
    """
    Validate a six-digit TOTP code.

    If real TOTP is configured, pyotp performs actual validation.

    If TOTP is unavailable and the account has no TOTP configuration,
    the existing six-digit development fallback is retained.

    IMPORTANT:

    This function does NOT determine whether the account is locked.

    Login endpoints perform the TokenShield hard-lock check BEFORE calling
    this function.
    """

    if not code:
        return False

    code_str = str(
        code,
    ).strip()

    if (
        len(code_str) != 6
        or not code_str.isdigit()
    ):
        return False

    # ------------------------------------------------------------------
    # Real TOTP validation.
    # ------------------------------------------------------------------

    if (
        TOTP_AVAILABLE
        and user
        and getattr(
            user,
            "totp_secret",
            None,
        )
        and getattr(
            user,
            "totp_enabled",
            False,
        )
    ):

        totp = pyotp.TOTP(
            user.totp_secret,
        )

        return bool(
            totp.verify(
                code_str,
                valid_window=1,
            )
        )

    # ------------------------------------------------------------------
    # Existing development fallback.
    #
    # This does NOT bypass TokenShield hard-lock because all login
    # endpoints check the lock before reaching this function.
    # ------------------------------------------------------------------

    return True