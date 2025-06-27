from flask import Flask
import os
from .extensions import db, login_manager # <--- IMPORT login_manager

def create_app():
    app = Flask(__name__)

    # Database Configuration
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = \
        'sqlite:///' + os.path.join(basedir, 'site.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'your_super_secret_and_random_key_here'

    db.init_app(app)

    # NEW: Initialize Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'main.login' # Where to redirect if login required
    login_manager.login_message_category = 'info' # Category for login required flash message

    @login_manager.user_loader # Decorator to tell Flask-Login how to load a user
    def load_user(user_id):
        from .models import User # Import User here to avoid circular dependency
        return User.query.get(int(user_id))

    with app.app_context():
        from . import models
        db.create_all()

    from app.routes import bp as main_bp
    app.register_blueprint(main_bp)

    return app