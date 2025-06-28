from flask import Flask
import os
from dotenv import load_dotenv
from .extensions import db, login_manager
from flask_migrate import Migrate

def create_app():
    load_dotenv()
    app = Flask(__name__)
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'site.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY')
    if not app.config['SECRET_KEY']:
        raise ValueError("No FLASK_SECRET_KEY set. Please set the FLASK_SECRET_KEY environment variable or add it to .env file.")
    print("Database URI:", app.config['SQLALCHEMY_DATABASE_URI'])  # Debug
    print("Current directory:", basedir)  # Debug

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'
    login_manager.login_message_category = 'info'
    migrate = Migrate(app, db)

    @login_manager.user_loader
    def load_user(user_id):
        from .models import User
        return User.query.get(int(user_id))

    from .routes import bp as main_bp
    app.register_blueprint(main_bp)

    return app