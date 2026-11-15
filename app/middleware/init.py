import os

from flask import Flask
from flask_cors import CORS

from app.config import get_config
from app.extensions import db, login_manager


def _ensure_database_schema(app):
    """
    Ensure the existing SQLite database contains all columns required
    by the current TokenShield models.

    db.create_all() only creates missing tables. It does NOT add new
    columns to tables that already exist, so we explicitly add the
    required compatibility columns here.
    """

    from sqlalchemy import inspect, text

    with app.app_context():
        try:
            # First create any tables that do not exist.
            db.create_all()

            inspector = inspect(db.engine)

            # ---------------------------------------------------------
            # sessions table
            # ---------------------------------------------------------
            session_columns = {
                column["name"]
                for column in inspector.get_columns("sessions")
            }

            session_columns_to_add = {
                "device_fingerprint": "VARCHAR(255)",
            }

            for column_name, column_type in session_columns_to_add.items():
                if column_name not in session_columns:
                    db.session.execute(
                        text(
                            f"ALTER TABLE sessions "
                            f"ADD COLUMN {column_name} {column_type}"
                        )
                    )
                    print(
                        f"✅ Database schema updated: "
                        f"sessions.{column_name}"
                    )

            # ---------------------------------------------------------
            # behavior_logs table
            # ---------------------------------------------------------
            if inspector.has_table("behavior_logs"):
                behavior_columns = {
                    column["name"]
                    for column in inspector.get_columns("behavior_logs")
                }

                behavior_columns_to_add = {
                    "action_type": "VARCHAR(100)",
                    "ip_address": "VARCHAR(45)",
                    "time_gap": "FLOAT",
                    "endpoint": "VARCHAR(255)",
                    "request_method": "VARCHAR(20)",
                    "fingerprint_data": "TEXT",
                }

                for column_name, column_type in behavior_columns_to_add.items():
                    if column_name not in behavior_columns:
                        db.session.execute(
                            text(
                                f"ALTER TABLE behavior_logs "
                                f"ADD COLUMN {column_name} {column_type}"
                            )
                        )
                        print(
                            f"✅ Database schema updated: "
                            f"behavior_logs.{column_name}"
                        )

            db.session.commit()

            print("✅ Database initialized successfully")

        except Exception as exc:
            db.session.rollback()
            print(
                "❌ Database schema initialization failed:"
            )
            print(f"   {exc}")
            raise


def create_app(config_class=None):
    """
    Application factory for TokenShield.
    """

    app = Flask(
        __name__,
        static_folder="../frontend",
        static_url_path=""
    )

    # ---------------------------------------------------------
    # Configuration
    # ---------------------------------------------------------
    if config_class is None:
        config_class = get_config()

    app.config.from_object(config_class)

    # ---------------------------------------------------------
    # Extensions
    # ---------------------------------------------------------
    db.init_app(app)
    login_manager.init_app(app)

    # ---------------------------------------------------------
    # CORS
    # ---------------------------------------------------------
    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": app.config.get(
                    "CORS_ORIGINS",
                    ["http://localhost:3000", "http://localhost:5000"]
                )
            }
        },
        supports_credentials=True
    )

    # ---------------------------------------------------------
    # Login manager
    # ---------------------------------------------------------
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return User.query.get(int(user_id))
        except (TypeError, ValueError):
            return None

    login_manager.login_view = "auth.login"

    # ---------------------------------------------------------
    # Database initialization + schema compatibility
    # ---------------------------------------------------------
    _ensure_database_schema(app)

    # ---------------------------------------------------------
    # Authentication routes
    # ---------------------------------------------------------
    from app.routes.auth import auth_bp

    app.register_blueprint(auth_bp)

    # ---------------------------------------------------------
    # Simulation routes
    # ---------------------------------------------------------
    from app.routes.simulation import simulation_bp

    app.register_blueprint(simulation_bp)

    # ---------------------------------------------------------
    # Optional application blueprints
    # ---------------------------------------------------------
    optional_blueprints = [
        ("app.routes.main", "main_bp"),
        ("app.routes.banking", "banking_bp"),
        ("app.routes.dashboard", "dashboard_bp"),
        ("app.routes.security", "security_bp"),
    ]

    for module_name, blueprint_name in optional_blueprints:
        try:
            module = __import__(
                module_name,
                fromlist=[blueprint_name]
            )

            blueprint = getattr(module, blueprint_name)

            app.register_blueprint(blueprint)

        except (ImportError, AttributeError):
            # These modules are optional in some TokenShield builds.
            continue

    print("✅ All blueprints registered successfully")

    # ---------------------------------------------------------
    # Frontend
    # ---------------------------------------------------------
    @app.route("/")
    def index():
        """
        Serve the main frontend page.
        """

        frontend_index = os.path.join(
            app.static_folder,
            "index.html"
        )

        if os.path.exists(frontend_index):
            return app.send_static_file("index.html")

        return {
            "application": "TokenShield",
            "status": "running",
            "message": "TokenShield backend is running."
        }

    # ---------------------------------------------------------
    # Health endpoint
    # ---------------------------------------------------------
    @app.route("/health")
    def health():
        return {
            "status": "healthy",
            "application": "TokenShield"
        }

    return app