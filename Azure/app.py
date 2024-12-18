from flask import Flask, render_template, request, url_for, redirect, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import re  # For CPR number validation
import paho.mqtt.client as mqtt
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import base64
from config import Config
import random
import hashlib

from models import db, Users, VitaleTegn  # Import models
from encryption import encrypt_data, decrypt_data  # Import encryption functions
from routes import main_bp, auth_bp, vitale_bp  # Import Blueprints

app = Flask(__name__)
app.config.from_object(Config)
app.config["SECRET_KEY"] = Config.SECRET_KEY
db.init_app(app)  # Initialize SQLAlchemy with the app's config

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"  # Reference to Blueprint endpoint

# Context Processor to inject dark_mode into all templates
@app.context_processor
def inject_dark_mode():
    if current_user.is_authenticated:
        return {'dark_mode': current_user.dark_mode}
    else:
        return {'dark_mode': session.get('dark_mode', False)}

# Register Blueprints
app.register_blueprint(main_bp, url_prefix="/")
app.register_blueprint(auth_bp, url_prefix="/")
app.register_blueprint(vitale_bp, url_prefix="/")

# Create all tables
with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))

# Error Handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
