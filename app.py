import os
from flask import Flask
from flask_migrate import Migrate
from config import Config
from extensions import db, login_manager, bcrypt, mail
from flask_wtf.csrf import CSRFProtect, generate_csrf

csrf = CSRFProtect()

migrate = Migrate()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config.from_object(config_class)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['SESSION_COOKIE_SECURE'] = False

    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    from routes import bp as main_bp
    app.register_blueprint(main_bp)

    return app
if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
