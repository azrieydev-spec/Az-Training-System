import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Database configuration
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    'pool_pre_ping': True,
    "pool_recycle": 300,
}

# File upload configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# CSRF protection
app.config['WTF_CSRF_TIME_LIMIT'] = None
csrf = CSRFProtect(app)

# Session configuration
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours

# Initialize database
db = SQLAlchemy(app, model_class=Base)

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Create tables and initialize database
with app.app_context():
    import models  # noqa: F401
    from models import User
    
    # Drop all existing tables
    logging.info("Dropping all existing tables...")
    db.drop_all()
    
    # Recreate all tables with correct schema
    logging.info("Creating all tables with new schema...")
    db.create_all()
    
    # Create admin account
    admin_email = 'azrieydev@gmail.com'
    admin = User.query.filter_by(email=admin_email).first()
    
    if not admin:
        logging.info(f"Creating admin user: {admin_email}")
        admin = User(email=admin_email, role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        logging.info(f"✓ Admin user created: {admin_email} / admin123")
    else:
        logging.info(f"Admin user already exists: {admin_email}")
    
    logging.info("Database initialization complete!")
