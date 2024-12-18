from flask import render_template, session, redirect, request, url_for, flash
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from . import main_bp
from models import db, Users
from encryption import encrypt_data, decrypt_data
from datetime import datetime
import re

@main_bp.route("/")
def home():
    return render_template("home.html")

@main_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        # Changing password
        new_password = request.form.get("new_password", "").strip()
        if new_password:
            current_user.password = generate_password_hash(new_password, method="pbkdf2:sha1")
            flash("Adgangskode opdateret.", "success")
        
        # Update dark mode preference
        new_theme_pref = request.form.get("dark_mode") == 'on'
        current_user.dark_mode = new_theme_pref
        db.session.commit()
        session['dark_mode'] = new_theme_pref  # Update session immediately
        return redirect(url_for("main.profile"))
    
    return render_template("profile.html", user=current_user)
