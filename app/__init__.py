from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config
import os

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure data directories exist
    os.makedirs(os.path.dirname(app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')), exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from app.routes import main, auth, vehicles, fuel, expenses, api
    app.register_blueprint(main.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(vehicles.bp)
    app.register_blueprint(fuel.bp)
    app.register_blueprint(expenses.bp)
    app.register_blueprint(api.bp)

    with app.app_context():
        db.create_all()
        # Create default admin user if no users exist
        if User.query.count() == 0:
            admin = User(username='admin', email='admin@example.com', is_admin=True)
            admin.set_password('admin')
            db.session.add(admin)
            db.session.commit()

    return app
