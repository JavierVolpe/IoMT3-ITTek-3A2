from flask import render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, Users
from . import auth_bp

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password").strip()
        if not username or not password:
            flash("Brugernavn og adgangskode er påkrævet.", "danger")
            return render_template("sign_up.html")
        try:
            hashed_password = generate_password_hash(password, method="pbkdf2:sha1")
            user = Users(username=username, password=hashed_password)
            db.session.add(user)
            db.session.commit()
            flash("Registrering lykkedes! Log ind nu.", "success")
            return redirect(url_for("auth.login"))
        except Exception as e:
            db.session.rollback()
            flash(f"Registration failed: {e}", "danger")
    return render_template("sign_up.html")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password").strip()
        remember = request.form.get("remember") == 'on'  # Capture the remember option

        user = Users.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user, remember=remember)
            flash("Login successful.", "success")
            return redirect(url_for("main.home"))
        else:
            flash("Invalid username or password.", "danger")
    return render_template("login.html")

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.home"))
