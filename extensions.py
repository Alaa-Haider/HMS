from flask_sqlalchemy import SQLAlchemy

# Initialize SQLAlchemy
db = SQLAlchemy()

def init_extensions(app):
    """Initialize Flask extensions"""
    db.init_app(app)