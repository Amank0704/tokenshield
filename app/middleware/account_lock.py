"""
TokenShield — Step 3.4: Account Lock
====================================

Handles account-level locking after TokenShield detects suspicious
session activity.

Lock modes
----------
SOFT LOCK
    failed_login_attempts is set to 99.
    The authentication layer can require additional verification.

HARD LOCK
    is_active is set to False.
    The account cannot log in until an administrator explicitly unlocks it.

Redis
-----
    ts:lock:{user_id}

Redis is used as a fast lock-state cache. The database remains the
persistent source of truth.

Important
---------
Unlocking an account does NOT remove the user's TOTP configuration.
The administrator is only clearing the security lock.
"""

import json
import logging

from datetime import datetime
from typing import Optional


logger = logging.getLogger("tokenshield.account_lock")


# ============================================================================
# CONFIGURATION
# ============================================================================

LOCK_PREFIX = "ts:lock:"

# Redis lock metadata lifetime.
LOCK_TTL = 24 * 3600

# Value used by auth.py to recognize a soft lock.
SOFT_LOCK_THRESHOLD = 99


# ============================================================================
# SOFT LOCK
# ============================================================================

def soft_lock_account(
    user_id: int,
    session_id: int,
    reason: str,
) -> bool:
    """
    Apply a soft security lock to an account.

    Database:
        failed_login_attempts = 99

    Redis:
        Stores lock metadata.

    Returns:
        True if the database update succeeded.
    """

    success = _write_db_lock(
        user_id=user_id,
        soft=True,
    )

    _write_redis_lock(
        user_id=user_id,
        session_id=session_id,
        reason=reason,
        lock_type="soft",
    )

    if success:
        logger.warning(
            "TokenShield SOFT LOCK | uid=%d | sid=%d | reason=%s",
            user_id,
            session_id,
            reason,
        )

    return success


# ============================================================================
# HARD LOCK
# ============================================================================

def hard_lock_account(
    user_id: int,
    session_id: int,
    reason: str,
) -> bool:
    """
    Apply a complete account-level lock.

    Database:
        is_active = False
        failed_login_attempts = 99

    Redis:
        Stores lock metadata.

    A hard-locked account cannot authenticate again until
    unlock_account() is explicitly called.

    Returns:
        True if the database update succeeded.
    """

    success = _write_db_lock(
        user_id=user_id,
        soft=False,
    )

    _write_redis_lock(
        user_id=user_id,
        session_id=session_id,
        reason=reason,
        lock_type="hard",
    )

    if success:
        logger.warning(
            "TokenShield HARD LOCK | uid=%d | sid=%d | reason=%s",
            user_id,
            session_id,
            reason,
        )

    return success


# ============================================================================
# UNLOCK
# ============================================================================

def unlock_account(user_id: int) -> bool:
    """
    Unlock a previously locked account.

    Database:
        failed_login_attempts = 0
        is_active = True

    Redis:
        Lock metadata is removed.

    IMPORTANT:
        TOTP configuration is intentionally preserved.

    Returns:
        True if the database update succeeded.
    """

    success = _clear_db_lock(user_id)

    _clear_redis_lock(user_id)

    if success:
        logger.info(
            "TokenShield ACCOUNT UNLOCKED | uid=%d",
            user_id,
        )

    return success


# ============================================================================
# CHECK LOCK STATUS
# ============================================================================

def is_account_locked(
    user_id: int,
) -> tuple[bool, Optional[dict]]:
    """
    Check whether an account is currently locked.

    Redis is checked first for fast access.
    Database is used as the fallback/source of truth.

    Returns:
        (
            locked: bool,
            lock_info: dict | None
        )
    """

    # ------------------------------------------------------------------------
    # Redis fast path
    # ------------------------------------------------------------------------

    try:
        from app.middleware.redis_client import get_redis

        redis_client = get_redis()

        if redis_client:
            raw = redis_client.get(
                LOCK_PREFIX + str(user_id)
            )

            if raw:
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8")

                try:
                    return True, json.loads(raw)
                except json.JSONDecodeError:
                    logger.warning(
                        "TokenShield invalid Redis lock record | uid=%d",
                        user_id,
                    )

    except Exception as exc:
        logger.debug(
            "TokenShield Redis lock check failed | %s",
            exc,
        )

    # ------------------------------------------------------------------------
    # Database fallback
    # ------------------------------------------------------------------------

    try:
        from app.models import User

        user = User.query.get(user_id)

        if user is None:
            return False, None

        # Hard lock
        if not user.is_active:
            return True, {
                "user_id": user_id,
                "lock_type": "hard",
                "reason": "account_disabled",
            }

        # Soft lock
        if (
            user.failed_login_attempts or 0
        ) >= SOFT_LOCK_THRESHOLD:

            return True, {
                "user_id": user_id,
                "lock_type": "soft",
                "reason": "failed_attempts_threshold",
            }

        return False, None

    except Exception as exc:
        logger.error(
            "TokenShield database lock check failed | %s",
            exc,
        )

        return False, None


# ============================================================================
# GET LOCK INFORMATION
# ============================================================================

def get_lock_info(
    user_id: int,
) -> Optional[dict]:
    """
    Return Redis lock metadata for a user.

    Returns:
        dict if a Redis lock exists, otherwise None.
    """

    try:
        from app.middleware.redis_client import get_redis

        redis_client = get_redis()

        if not redis_client:
            return None

        raw = redis_client.get(
            LOCK_PREFIX + str(user_id)
        )

        if not raw:
            return None

        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    except Exception:
        return None


# ============================================================================
# LOCKED ACCOUNT COUNT
# ============================================================================

def locked_accounts_count() -> int:
    """
    Return the number of accounts currently represented by
    TokenShield lock keys in Redis.

    Redis may be unavailable, in which case zero is returned.
    """

    try:
        from app.middleware.redis_client import get_redis

        redis_client = get_redis()

        if not redis_client:
            return 0

        keys = redis_client.keys(
            LOCK_PREFIX + "*"
        )

        return len(keys)

    except Exception:
        return 0


# ============================================================================
# INTERNAL — DATABASE LOCK
# ============================================================================

def _write_db_lock(
    user_id: int,
    soft: bool,
) -> bool:
    """
    Write the persistent account-lock state to the database.
    """

    try:
        from app.extensions import db
        from app.models import User

        user = User.query.get(user_id)

        if user is None:
            logger.warning(
                "TokenShield lock failed: user not found | uid=%d",
                user_id,
            )
            return False

        # --------------------------------------------------------------------
        # SOFT LOCK
        # --------------------------------------------------------------------

        if soft:
            user.failed_login_attempts = (
                SOFT_LOCK_THRESHOLD
            )

        # --------------------------------------------------------------------
        # HARD LOCK
        # --------------------------------------------------------------------

        else:
            user.is_active = False

            user.failed_login_attempts = (
                SOFT_LOCK_THRESHOLD
            )

        db.session.commit()

        return True

    except Exception as exc:

        logger.error(
            "TokenShield database lock write failed | %s",
            exc,
        )

        try:
            from app.extensions import db

            db.session.rollback()

        except Exception:
            pass

        return False


# ============================================================================
# INTERNAL — DATABASE UNLOCK
# ============================================================================

def _clear_db_lock(
    user_id: int,
) -> bool:
    """
    Clear the persistent database lock.

    IMPORTANT:
    TOTP configuration is deliberately NOT changed here.

    The user may already have a working authenticator configured,
    and unlocking an account should not silently remove it.
    """

    try:
        from app.extensions import db
        from app.models import User

        user = None
        if isinstance(user_id, str):
            if user_id.isdigit():
                user = User.query.get(int(user_id))
            else:
                user = User.query.filter(
                    (User.email == user_id) | (User.username == user_id)
                ).first()
        else:
            user = User.query.get(user_id)

        if user is None:
            logger.warning(
                "TokenShield unlock failed: user not found | uid=%s",
                user_id,
            )
            return False

        # Clear authentication lock.
        user.failed_login_attempts = 0

        # Re-enable account.
        user.is_active = True

        # DO NOT do this:
        #
        # user.totp_secret = None
        # user.totp_enabled = False
        #
        # TOTP must remain configured.

        db.session.commit()

        return True

    except Exception as exc:

        logger.error(
            "TokenShield database unlock failed | %s",
            exc,
        )

        try:
            from app.extensions import db

            db.session.rollback()

        except Exception:
            pass

        return False


# ============================================================================
# INTERNAL — REDIS LOCK
# ============================================================================

def _write_redis_lock(
    user_id: int,
    session_id: int,
    reason: str,
    lock_type: str,
) -> None:
    """
    Store lock metadata in Redis.

    Redis failures are intentionally non-fatal because the database
    remains the persistent source of truth.
    """

    try:
        from app.middleware.redis_client import get_redis

        redis_client = get_redis()

        if redis_client is None:
            return

        record = {
            "user_id": user_id,
            "session_id": session_id,
            "reason": reason,
            "lock_type": lock_type,
            "locked_at": datetime.utcnow().isoformat(),
        }

        redis_client.setex(
            LOCK_PREFIX + str(user_id),
            LOCK_TTL,
            json.dumps(record),
        )

    except Exception as exc:

        logger.debug(
            "TokenShield Redis lock write failed | %s",
            exc,
        )


# ============================================================================
# INTERNAL — REDIS UNLOCK
# ============================================================================

def _clear_redis_lock(
    user_id: int,
) -> None:
    """
    Remove the Redis lock record.
    """

    try:
        from app.middleware.redis_client import get_redis

        redis_client = get_redis()

        if redis_client:
            redis_client.delete(
                LOCK_PREFIX + str(user_id)
            )
            if isinstance(user_id, str) and not user_id.isdigit():
                try:
                    from app.models import User
                    u = User.query.filter((User.email == user_id) | (User.username == user_id)).first()
                    if u:
                        redis_client.delete(LOCK_PREFIX + str(u.id))
                except Exception:
                    pass

    except Exception:
        pass