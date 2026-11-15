"""
Main Routes - NeoVault + TokenShield
Serves all HTML pages and static files
"""

from flask import Blueprint, send_from_directory, redirect, request, jsonify
import os
import json
from engine.state.user_profiles import UserProfileStore

main_bp = Blueprint('main', __name__)


# ============================================================================
# BIOMETRICS TELEMETRY & WARM-UP (Phase 3)
# ============================================================================

@main_bp.route('/api/biometrics/update', methods=['POST'])
def biometrics_update():
    """
    Accepts client-side behavioral telemetry (typing, mouse, idle patterns)
    and updates the user baseline in UserProfileStore.
    Non-blocking, does not run threat detection.
    """
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    if not user_id:
        # Check if auth bearer session is present
        from app.utils import decode_token
        auth = request.headers.get("Authorization", "")
        token = auth[7:] if auth.startswith("Bearer ") else None
        if token:
            payload = decode_token(token)
            if payload and "sub" in payload:
                user_id = str(payload["sub"])

    metrics = data.get("metrics") or data.get("features")
    if not metrics and request.headers.get("X-TS-Biometrics"):
        try:
            metrics = json.loads(request.headers.get("X-TS-Biometrics"))
        except Exception:
            pass

    if not user_id or not metrics:
        return jsonify({"success": False, "error": "user_id and metrics required"}), 400

    store = UserProfileStore()
    profile = store.update_profile(str(user_id), metrics)
    sample_count = profile.get("sample_count", 0)

    # Sync to standalone engine
    try:
        from sdk.python.tokenshield_sdk import TokenShieldClient
        ts_client = TokenShieldClient(engine_url="http://127.0.0.1:7777", timeout=0.1)
        ts_client.report_biometrics(user_id=str(user_id), biometrics=metrics)
    except Exception:
        pass

    return jsonify({
        "success": True,
        "user_id": str(user_id),
        "samples_collected": sample_count,
        "warmup_complete": sample_count >= 5
    }), 200



# ============================================================================
# HTML PAGES
# ============================================================================

@main_bp.route('/')
def index():
    """Serve landing page - Use the professional NeoVault index"""
    return send_from_directory('../frontend', 'neovault_index_pro.html')



@main_bp.route('/login')
def login_page():
    """Serve login page"""
    return send_from_directory('../frontend', 'login.html')


@main_bp.route('/dashboard')
def dashboard():
    """Serve banking dashboard - Use the professional dashboard"""
    return send_from_directory('../frontend', 'neovault_dashboard_pro.html')


@main_bp.route('/security-dashboard')
def security_dashboard():
    """Serve security dashboard for users"""
    return send_from_directory('../frontend', 'security_dashboard_user.html')


@main_bp.route('/admin')
def admin_panel():
    """Serve admin panel"""
    return send_from_directory('../frontend', 'admin.html')


# ============================================================================
# ALTERNATIVE ROUTES (Backwards compatibility)
# ============================================================================

@main_bp.route('/index')
def index_alt():
    """Alternative index route"""
    return send_from_directory('../frontend', 'index.html')


# ============================================================================
# STATIC FILE ROUTES
# ============================================================================

@main_bp.route('/css/<path:filename>')
def serve_css(filename):
    """Serve CSS files from frontend/css/"""
    return send_from_directory('../frontend/css', filename)


@main_bp.route('/js/<path:filename>')
def serve_js(filename):
    """Serve JavaScript files from frontend/js/"""
    return send_from_directory('../frontend/js', filename)


@main_bp.route('/images/<path:filename>')
def serve_images(filename):
    """Serve images if any"""
    return send_from_directory('../frontend/images', filename)


@main_bp.route('/assets/<path:filename>')
def serve_assets(filename):
    """Serve other assets"""
    return send_from_directory('../frontend/assets', filename)


@main_bp.route('/simulation')
def simulation_dashboard():
    return send_from_directory('../frontend', 'simulation_dashboard.html')


@main_bp.route('/war-room')
@main_bp.route('/command-center')
def war_room_dashboard():
    return send_from_directory('../frontend', 'war_room.html')


@main_bp.route('/attacker-studio')
def attacker_studio():
    return send_from_directory('../frontend', 'attacker_studio.html')
# ============================================================================
# UTILITY ROUTES
# ============================================================================

@main_bp.route('/health')
def health_check():
    """Health check endpoint"""
    return {'status': 'ok', 'service': 'NeoVault + TokenShield'}, 200


@main_bp.route('/favicon.ico')
def favicon():
    """Serve favicon if exists"""
    return send_from_directory('../frontend', 'favicon.ico', mimetype='image/vnd.microsoft.icon')

@main_bp.route('/security-engine')
def security_engine():
       return send_from_directory('../frontend', 'security_engine.html')
# ============================================================================
# ERROR HANDLERS
# ============================================================================

@main_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return send_from_directory('../frontend', 'index.html'), 404




# ============================================================================
# ROUTE REFERENCE
# ============================================================================
"""
Available Routes:

PUBLIC PAGES:
- GET  /                    → neovault_index_pro.html (Landing page)
- GET  /login               → login.html (Login/Register)

AUTHENTICATED PAGES:
- GET  /dashboard           → neovault_dashboard_pro.html (Banking dashboard)
- GET  /security-dashboard  → security_dashboard_user.html (User security)
- GET  /admin               → admin.html (Admin panel)

STATIC FILES:
- GET  /css/<file>          → CSS files
- GET  /js/<file>           → JavaScript files
- GET  /images/<file>       → Images
- GET  /assets/<file>       → Other assets

 #   GET  /simulation  → simulation_dashboard.html (GNS3 + resource graphs)

UTILITY:
- GET  /health              → Health check
- GET  /favicon.ico         → Favicon
"""