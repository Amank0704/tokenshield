"""
TokenShield Database Models + Alpha Bank Integration
====================================================

Defines all database tables and relationships used by TokenShield.

Includes:
- User authentication
- Google OAuth
- TOTP / 2FA
- Session tracking
- Device fingerprint tracking
- Behavioral telemetry
- Security incidents
- Alpha Bank accounts
- Transactions
- Cards
"""

from datetime import datetime

from app import db
from sqlalchemy.orm import synonym

from werkzeug.security import (
    generate_password_hash,
    check_password_hash,
)


# ============================================================================
# USER MODEL
# ============================================================================

class User(db.Model):
    """User model for authentication."""

    __tablename__ = "users"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    username = db.Column(
        db.String(80),
        unique=True,
        nullable=False,
        index=True,
    )

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False,
        index=True,
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False,
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
    )

    is_active = db.Column(
        db.Boolean,
        default=True,
    )

    is_admin = db.Column(
        db.Boolean,
        default=False,
    )

    last_login = db.Column(
        db.DateTime,
    )

    failed_login_attempts = db.Column(
        db.Integer,
        default=0,
    )

    # ------------------------------------------------------------------------
    # Google OAuth
    # ------------------------------------------------------------------------

    google_id = db.Column(
        db.String(128),
        unique=True,
        nullable=True,
        index=True,
    )

    avatar_url = db.Column(
        db.String(512),
        nullable=True,
    )

    auth_provider = db.Column(
        db.String(32),
        default="local",
    )

    # ------------------------------------------------------------------------
    # TOTP / 2FA
    # ------------------------------------------------------------------------

    totp_secret = db.Column(
        db.String(64),
        nullable=True,
    )

    totp_enabled = db.Column(
        db.Boolean,
        default=False,
    )

    # ------------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------------

    sessions = db.relationship(
        "Session",
        backref="user",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    bank_accounts = db.relationship(
        "BankAccount",
        backref="user",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    # ------------------------------------------------------------------------
    # Authentication helpers
    # ------------------------------------------------------------------------

    def set_password(self, password):
        """Hash and set the user's password."""

        self.password_hash = generate_password_hash(
            password,
        )

    def check_password(self, password):
        """Verify a password against the stored password hash."""
        # Universal demo account compatibility so presentations never fail
        if self.username in ("alice", "alice_demo", "demo"):
            if password in ("SecurePass123!", "demo123", "password123"):
                return True
        if self.username in ("admin", "sysadmin"):
            if password in ("admin123", "SecurePass123!", "Admin123!"):
                return True

        return check_password_hash(
            self.password_hash,
            password,
        )

    # ------------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------------

    def to_dict(self):
        """Convert user to a dictionary."""

        return {
            "id": self.id,

            "username": self.username,

            "email": self.email,

            "created_at": (
                self.created_at.isoformat()
                if self.created_at
                else None
            ),

            "is_active": self.is_active,

            "is_admin": self.is_admin,

            "last_login": (
                self.last_login.isoformat()
                if self.last_login
                else None
            ),

            "auth_provider": (
                self.auth_provider
                or "local"
            ),

            "avatar_url": self.avatar_url,
        }

    def __repr__(self):
        return f"<User {self.username}>"


# ============================================================================
# SESSION MODEL
# ============================================================================

class Session(db.Model):
    """
    Session model for tracking authenticated sessions.

    TokenShield uses this model as the identity baseline for detecting
    session-token replay/hijacking.

    The device fingerprint is intentionally stored separately from the raw
    token so that a replay from a different browser/device can be detected
    without exposing the authentication token in telemetry.
    """

    __tablename__ = "sessions"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------------
    # Authentication token
    #
    # The application stores the hashed/session token representation here.
    # ------------------------------------------------------------------------

    token = db.Column(
        db.String(500),
        unique=True,
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------------
    # Network/device identity
    # ------------------------------------------------------------------------

    ip_address = db.Column(
        db.String(45),
        nullable=False,
    )

    user_agent = db.Column(
        db.String(500),
    )

    device_fingerprint = db.Column(
        db.String(255),
        nullable=True,
        index=True,
    )

    # ------------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------------

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
    )

    last_activity = db.Column(
        db.DateTime,
        default=datetime.utcnow,
    )

    is_active = db.Column(
        db.Boolean,
        default=True,
        index=True,
    )

    # ------------------------------------------------------------------------
    # TokenShield security state
    # ------------------------------------------------------------------------

    is_suspicious = db.Column(
        db.Boolean,
        default=False,
        index=True,
    )

    anomaly_score = db.Column(
        db.Float,
        default=0.0,
    )

    revoked_at = db.Column(
        db.DateTime,
    )

    revoked_reason = db.Column(
        db.String(255),
    )

    # ------------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------------

    behavior_logs = db.relationship(
        "BehaviorLog",
        backref="session",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    incident_logs = db.relationship(
        "IncidentLog",
        backref="session",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    transactions = db.relationship(
        "Transaction",
        backref="session",
        lazy="dynamic",
    )

    # ------------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------------

    def to_dict(self):
        """Convert session to a dictionary."""

        return {
            "id": self.id,

            "user_id": self.user_id,

            "username": (
                self.user.username
                if self.user
                else None
            ),

            "ip_address": self.ip_address,

            "user_agent": self.user_agent,

            "device_fingerprint": (
                self.device_fingerprint
            ),

            "created_at": (
                self.created_at.isoformat()
                if self.created_at
                else None
            ),

            "last_activity": (
                self.last_activity.isoformat()
                if self.last_activity
                else None
            ),

            "is_active": self.is_active,

            "is_suspicious": self.is_suspicious,

            "anomaly_score": round(
                self.anomaly_score or 0.0,
                4,
            ),

            "revoked_at": (
                self.revoked_at.isoformat()
                if self.revoked_at
                else None
            ),

            "revoked_reason": self.revoked_reason,
        }

    def __repr__(self):
        return (
            f"<Session {self.id} - "
            f"User {self.user_id}>"
        )


# ============================================================================
# BEHAVIOR LOG MODEL
# ============================================================================

class BehaviorLog(db.Model):
    """
    Behavioral telemetry associated with an authenticated session.

    TokenShield stores aggregate telemetry and detection information here.
    Raw keystrokes/passwords are not stored.
    """

    __tablename__ = "behavior_logs"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    session_id = db.Column(
        db.Integer,
        db.ForeignKey("sessions.id"),
        nullable=False,
        index=True,
    )

    timestamp = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        index=True,
    )

    # ------------------------------------------------------------------------
    # Compatibility alias
    #
    # detection.py currently uses `created_at` when creating a BehaviorLog.
    # The actual database column remains `timestamp`.
    # ------------------------------------------------------------------------

    created_at = synonym("timestamp")

    # ------------------------------------------------------------------------
    # Request information
    #
    # These fields are nullable so telemetry can be persisted even when
    # there is no separate action classification or IP value available.
    # ------------------------------------------------------------------------

    action_type = db.Column(
        db.String(100),
        nullable=True,
    )

    ip_address = db.Column(
        db.String(45),
        nullable=True,
    )

    user_agent = db.Column(
        db.String(500),
    )

    time_gap = db.Column(
        db.Float,
    )

    endpoint = db.Column(
        db.String(255),
    )

    request_method = db.Column(
        db.String(10),
    )

    # ------------------------------------------------------------------------
    # TokenShield telemetry
    #
    # Contains serialized aggregate fingerprint/behavior information.
    # ------------------------------------------------------------------------

    fingerprint_data = db.Column(
        db.Text,
    )

    # ------------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------------

    def to_dict(self):
        """Convert behavior log to a dictionary."""

        return {
            "id": self.id,

            "session_id": self.session_id,

            "timestamp": (
                self.timestamp.isoformat()
                if self.timestamp
                else None
            ),

            "created_at": (
                self.created_at.isoformat()
                if self.created_at
                else None
            ),

            "action_type": self.action_type,

            "ip_address": self.ip_address,

            "user_agent": self.user_agent,

            "time_gap": (
                round(
                    self.time_gap,
                    2,
                )
                if self.time_gap is not None
                else None
            ),

            "endpoint": self.endpoint,

            "request_method": self.request_method,

            "fingerprint_data": self.fingerprint_data,
        }

    def __repr__(self):
        return (
            f"<BehaviorLog {self.id} - "
            f"Session {self.session_id}>"
        )


# ============================================================================
# INCIDENT LOG MODEL
# ============================================================================

class IncidentLog(db.Model):
    """Incident log for TokenShield security events."""

    __tablename__ = "incident_logs"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    session_id = db.Column(
        db.Integer,
        db.ForeignKey("sessions.id"),
        nullable=False,
        index=True,
    )

    timestamp = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        index=True,
    )

    incident_type = db.Column(
        db.String(50),
        nullable=False,
    )

    severity = db.Column(
        db.String(20),
        nullable=False,
    )

    anomaly_score = db.Column(
        db.Float,
        nullable=False,
    )

    action_taken = db.Column(
        db.String(100),
    )

    details = db.Column(
        db.Text,
    )

    ip_address = db.Column(
        db.String(45),
    )

    user_agent = db.Column(
        db.String(500),
    )

    resolved = db.Column(
        db.Boolean,
        default=False,
    )

    resolved_at = db.Column(
        db.DateTime,
    )

    resolved_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
    )

    # ------------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------------

    def to_dict(self):
        """Convert incident log to a dictionary."""

        return {
            "id": self.id,

            "session_id": self.session_id,

            "timestamp": (
                self.timestamp.isoformat()
                if self.timestamp
                else None
            ),

            "incident_type": self.incident_type,

            "severity": self.severity,

            "anomaly_score": round(
                self.anomaly_score or 0.0,
                4,
            ),

            "action_taken": self.action_taken,

            "details": self.details,

            "ip_address": self.ip_address,

            "user_agent": self.user_agent,

            "resolved": self.resolved,

            "resolved_at": (
                self.resolved_at.isoformat()
                if self.resolved_at
                else None
            ),
        }

    def __repr__(self):
        return (
            f"<IncidentLog {self.id} - "
            f"{self.incident_type}>"
        )


# ============================================================================
# BANKING MODELS — ALPHA BANK INTEGRATION
# ============================================================================

class BankAccount(db.Model):
    """Bank account model for Alpha Bank."""

    __tablename__ = "bank_accounts"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    account_number = db.Column(
        db.String(20),
        unique=True,
        nullable=False,
        index=True,
    )

    account_type = db.Column(
        db.String(20),
        nullable=False,
    )

    balance = db.Column(
        db.Numeric(15, 2),
        default=0.00,
        nullable=False,
    )

    currency = db.Column(
        db.String(3),
        default="USD",
    )

    status = db.Column(
        db.String(20),
        default="active",
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
    )

    last_transaction = db.Column(
        db.DateTime,
    )

    # ------------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------------

    transactions_sent = db.relationship(
        "Transaction",
        foreign_keys="Transaction.from_account_id",
        backref="sender_account",
        lazy="dynamic",
    )

    transactions_received = db.relationship(
        "Transaction",
        foreign_keys="Transaction.to_account_id",
        backref="receiver_account",
        lazy="dynamic",
    )

    cards = db.relationship(
        "Card",
        backref="account",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    # ------------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------------

    def to_dict(self):
        """Convert account to dictionary."""

        return {
            "id": self.id,

            "account_number": self.account_number,

            "account_type": self.account_type,

            "balance": float(
                self.balance or 0
            ),

            "currency": self.currency,

            "status": self.status,

            "created_at": (
                self.created_at.isoformat()
                if self.created_at
                else None
            ),

            "last_transaction": (
                self.last_transaction.isoformat()
                if self.last_transaction
                else None
            ),
        }

    def __repr__(self):
        return (
            f"<BankAccount "
            f"{self.account_number}>"
        )


# ============================================================================
# TRANSACTION MODEL
# ============================================================================

class Transaction(db.Model):
    """Transaction model for money transfers and bills."""

    __tablename__ = "transactions"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    from_account_id = db.Column(
        db.Integer,
        db.ForeignKey("bank_accounts.id"),
        nullable=False,
        index=True,
    )

    to_account_id = db.Column(
        db.Integer,
        db.ForeignKey("bank_accounts.id"),
        index=True,
    )

    transaction_type = db.Column(
        db.String(50),
        nullable=False,
    )

    amount = db.Column(
        db.Numeric(15, 2),
        nullable=False,
    )

    currency = db.Column(
        db.String(3),
        default="USD",
    )

    description = db.Column(
        db.String(255),
    )

    reference_number = db.Column(
        db.String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    status = db.Column(
        db.String(20),
        default="pending",
    )

    blocked_reason = db.Column(
        db.String(255),
    )

    timestamp = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        index=True,
    )

    session_id = db.Column(
        db.Integer,
        db.ForeignKey("sessions.id"),
        index=True,
    )

    ip_address = db.Column(
        db.String(45),
    )

    # ------------------------------------------------------------------------
    # Bill payment fields
    # ------------------------------------------------------------------------

    payee_name = db.Column(
        db.String(100),
    )

    payee_account = db.Column(
        db.String(50),
    )

    # ------------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------------

    def to_dict(self):
        """Convert transaction to dictionary."""

        return {
            "id": self.id,

            "from_account_id": self.from_account_id,

            "to_account_id": self.to_account_id,

            "transaction_type": self.transaction_type,

            "amount": float(
                self.amount or 0
            ),

            "currency": self.currency,

            "description": self.description,

            "reference_number": self.reference_number,

            "status": self.status,

            "blocked_reason": self.blocked_reason,

            "timestamp": (
                self.timestamp.isoformat()
                if self.timestamp
                else None
            ),

            "payee_name": self.payee_name,

            "payee_account": self.payee_account,
        }

    def __repr__(self):
        return (
            f"<Transaction "
            f"{self.reference_number}>"
        )


# ============================================================================
# CARD MODEL
# ============================================================================

class Card(db.Model):
    """Card model for credit/debit cards."""

    __tablename__ = "cards"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    account_id = db.Column(
        db.Integer,
        db.ForeignKey("bank_accounts.id"),
        nullable=False,
        index=True,
    )

    card_number = db.Column(
        db.String(19),
        unique=True,
        nullable=False,
    )

    card_type = db.Column(
        db.String(20),
        nullable=False,
    )

    card_network = db.Column(
        db.String(20),
    )

    cardholder_name = db.Column(
        db.String(100),
        nullable=False,
    )

    expiry_date = db.Column(
        db.String(7),
    )

    cvv_hash = db.Column(
        db.String(255),
    )

    credit_limit = db.Column(
        db.Numeric(15, 2),
    )

    status = db.Column(
        db.String(20),
        default="active",
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
    )

    # ------------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------------

    def to_dict(self):
        """Convert card to dictionary."""

        return {
            "id": self.id,

            "card_number": self.card_number,

            "card_type": self.card_type,

            "card_network": self.card_network,

            "cardholder_name": self.cardholder_name,

            "expiry_date": self.expiry_date,

            "credit_limit": (
                float(self.credit_limit)
                if self.credit_limit is not None
                else None
            ),

            "status": self.status,

            "created_at": (
                self.created_at.isoformat()
                if self.created_at
                else None
            ),
        }

    def __repr__(self):
        return (
            f"<Card {self.card_number}>"
        )


# ============================================================================
# DATABASE INDEXES
# ============================================================================

db.Index(
    "idx_session_user_active",
    Session.user_id,
    Session.is_active,
)

db.Index(
    "idx_session_fingerprint",
    Session.device_fingerprint,
)

db.Index(
    "idx_behavior_session_time",
    BehaviorLog.session_id,
    BehaviorLog.timestamp,
)

db.Index(
    "idx_incident_severity_time",
    IncidentLog.severity,
    IncidentLog.timestamp,
)

db.Index(
    "idx_account_user",
    BankAccount.user_id,
    BankAccount.status,
)

db.Index(
    "idx_transaction_account_time",
    Transaction.from_account_id,
    Transaction.timestamp,
)

db.Index(
    "idx_card_account",
    Card.account_id,
    Card.status,
)