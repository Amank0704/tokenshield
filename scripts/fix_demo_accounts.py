#!/usr/bin/env python3
"""
One-shot database fix: ensures alice@neovault.com exists with correct
password hash, is_active=True, failed_login_attempts=0, and has bank accounts.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) if os.path.basename(__file__) != __file__ else '/Users/yashpachhade/tokenshield')
sys.path.insert(0, '/Users/yashpachhade/tokenshield')

from app import create_app, db
from app.models import User, BankAccount
from werkzeug.security import generate_password_hash
from decimal import Decimal

app = create_app()

with app.app_context():
    # ── 1. Fix or create alice ──────────────────────────────────────────
    alice = User.query.filter_by(email='alice@neovault.com').first()
    if not alice:
        alice = User.query.filter_by(username='alice').first()
    if not alice:
        alice = User(username='alice', email='alice@neovault.com')
        db.session.add(alice)
        db.session.flush()

    alice.username = 'alice'
    alice.email = 'alice@neovault.com'
    alice.password_hash = generate_password_hash('SecurePass123!')
    alice.is_active = True
    alice.is_admin = False
    alice.failed_login_attempts = 0
    if hasattr(alice, 'totp_enabled'):
        alice.totp_enabled = False
    print(f"✅ Alice fixed: id={alice.id} username={alice.username} email={alice.email}")

    # ── 2. Fix admin ───────────────────────────────────────────────────
    admin = User.query.filter_by(username='admin').first()
    if admin:
        admin.email = 'admin@neovault.com'
        admin.password_hash = generate_password_hash('admin123')
        admin.is_active = True
        admin.failed_login_attempts = 0
        print(f"✅ Admin fixed: id={admin.id}")

    # ── 3. Fix demo ───────────────────────────────────────────────────
    demo = User.query.filter_by(username='demo').first()
    if demo:
        demo.password_hash = generate_password_hash('demo123')
        demo.is_active = True
        demo.failed_login_attempts = 0
        print(f"✅ Demo fixed: id={demo.id}")

    # ── 4. Fix alice_demo ──────────────────────────────────────────────
    alice_demo = User.query.filter_by(username='alice_demo').first()
    if alice_demo:
        alice_demo.password_hash = generate_password_hash('SecurePass123!')
        alice_demo.is_active = True
        alice_demo.failed_login_attempts = 0
        print(f"✅ Alice_demo fixed: id={alice_demo.id}")

    # ── 5. Unlock ALL other users too ──────────────────────────────────
    for u in User.query.all():
        if not u.is_active or (u.failed_login_attempts or 0) >= 5:
            u.is_active = True
            u.failed_login_attempts = 0

    db.session.commit()

    # ── 6. Revoke all stale sessions ───────────────────────────────────
    from app.models import Session
    stale = Session.query.filter_by(is_active=True).all()
    for s in stale:
        s.is_active = False
    db.session.commit()
    print(f"✅ Revoked {len(stale)} stale sessions (clean slate)")

    # ── 7. Ensure Alice has bank accounts ──────────────────────────────
    acct = BankAccount.query.filter_by(user_id=alice.id, account_type='checking').first()
    if not acct:
        acct = BankAccount(
            user_id=alice.id,
            account_number='NV12345678',
            account_type='checking',
            balance=Decimal('250000.00'),
            status='active'
        )
        db.session.add(acct)
    else:
        acct.balance = Decimal('250000.00')
        acct.status = 'active'

    sav = BankAccount.query.filter_by(user_id=alice.id, account_type='savings').first()
    if not sav:
        sav = BankAccount(
            user_id=alice.id,
            account_number='NV87654321',
            account_type='savings',
            balance=Decimal('185000.00'),
            status='active'
        )
        db.session.add(sav)
    else:
        sav.balance = Decimal('185000.00')
        sav.status = 'active'

    db.session.commit()
    print(f"✅ Bank accounts: checking={acct.account_number} (₹{acct.balance}), savings={sav.account_number} (₹{sav.balance})")

    # ── 8. Verify password works ──────────────────────────────────────
    alice_reload = User.query.filter_by(email='alice@neovault.com').first()
    assert alice_reload is not None, "alice@neovault.com NOT FOUND!"
    assert alice_reload.check_password('SecurePass123!'), "PASSWORD CHECK FAILED!"
    assert alice_reload.is_active, "ALICE IS NOT ACTIVE!"
    print(f"\n🎉 VERIFICATION PASSED: alice@neovault.com / SecurePass123! — is_active={alice_reload.is_active}")
