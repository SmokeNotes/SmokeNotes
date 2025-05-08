import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import jinja2
from flask import send_file, flash
import io

db = SQLAlchemy()


def create_app():
    app = Flask(__name__)

    # Use absolute paths for the database
    db_path = os.environ.get("DATABASE_PATH", "/app/data/bbq_sessions.db")

    # Make sure parent directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    print(f"Using database at: {db_path}")
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-key-for-smokenotes")

    db.init_app(app)

    # Register blueprints
    from app.routes import main

    app.register_blueprint(main)

    # Add custom filter for newlines
    @app.template_filter("nl2br")
    def nl2br_filter(s):
        if s:
            return s.replace("\n", "<br>")
        return s

    # Create database if it doesn't exist
    with app.app_context():
        try:
            db.create_all()
            print("Database initialized successfully")
        except Exception as e:
            print(f"Error initializing database: {e}")
            import traceback

            traceback.print_exc()

    return app
