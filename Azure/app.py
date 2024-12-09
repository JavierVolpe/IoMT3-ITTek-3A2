from flask import Flask, render_template, request, url_for, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import re  # For CPR number validation
import paho.mqtt.client as mqtt
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
#app.config["SQLALCHEMY_DATABASE_URI"] = Config.SQLALCHEMY_DATABASE_URI
app.config["SECRET_KEY"] = Config.SECRET_KEY
db = SQLAlchemy()
 
login_manager = LoginManager()
login_manager.init_app(app)
 
 
class Users(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
 
class VitaleTegn(db.Model):
    __tablename__ = 'vitale_tegn'
    
    id = db.Column(db.Integer, primary_key=True)
    cpr_nummer = db.Column(db.String(11), nullable=False)
    tidspunkt = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    puls = db.Column(db.Integer, nullable=False)
    temperatur = db.Column(db.Float, nullable=False)
    
    def __repr__(self):
        return f"<VitaleTegn {self.cpr_nummer} - {self.puls} bpm - {self.temperatur}°C>"

 
db.init_app(app)
 
 
with app.app_context():
    db.create_all()
 
 
@login_manager.user_loader
def loader_user(user_id):
    return Users.query.get(user_id)
 
 
@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        hashed_password = generate_password_hash(request.form.get("password"), method="pbkdf2:sha1") # Hashing the password
        user = Users(username=request.form.get("username"),
                     password=hashed_password)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for("login"))
    return render_template("sign_up.html")
 
 
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = Users.query.filter_by(username=request.form.get("username")).first()
        if user and check_password_hash(user.password, request.form.get("password")):
            login_user(user)
            return redirect(url_for("home"))
    return render_template("login.html")
 
 
@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("home"))
 
 
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/vis_vitale_tegn", methods=["GET", "POST"])
@login_required
def vis_vitale_tegn():
    if request.method == "POST":
        cpr = request.form.get("cpr").strip()  # Remove any leading/trailing whitespace
        
        if cpr:
            # Validate CPR number format (e.g., DDMMYY-XXXX)
            if not re.match(r"^\d{6}-\d{4}$", cpr):
                flash("CPR-nummeret er ikke i korrekt format (DDMMYY-XXXX).", "danger")
                return render_template("vis_vitale_tegn.html", cpr=cpr, records=None, submitted=True)
            
            # Fetch records for the given CPR number, ordered by tidspunkt descending
            records = VitaleTegn.query.filter_by(cpr_nummer=cpr).order_by(VitaleTegn.tidspunkt.desc()).all()
            
            if records:
                flash(f"Vitale tegn fundet for CPR-nummer: {cpr}", "success")
            else:
                flash(f"Ingen vitale tegn fundet for CPR-nummer: {cpr}", "warning")
            
            return render_template("vis_vitale_tegn.html", cpr=cpr, records=records, submitted=True)
        else:
            # Form was submitted without CPR
            flash("Indtast venligst patientens CPR-nummer.", "danger")
            return render_template("vis_vitale_tegn.html", cpr=None, records=None, submitted=True)
    else:
        # GET request; no form submission
        return render_template("vis_vitale_tegn.html")

@app.route("/request_update", methods=["POST"])
@login_required
def request_update():
    cpr = request.form.get("cpr").strip()
    if cpr:
        try:
            mqtt_client = mqtt.Client()
            mqtt_client.username_pw_set(Config.MQTT_USERNAME, Config.MQTT_PASSWORD)
            mqtt_client.connect(Config.MQTT_BROKER_URL, Config.MQTT_BROKER_PORT)
            mqtt_client.publish(Config.MQTT_TOPIC, cpr)
            mqtt_client.disconnect()
            flash(f"Opdatering anmodet for CPR-nummer: {cpr}", "info")
            return redirect(url_for("vis_vitale_tegn"))
        except Exception as e:
            flash(f"Fejl ved opdatering af CPR-nummer: {cpr} {e}", "danger")
            return redirect(url_for("vis_vitale_tegn"))
    else:
        flash("Ingen CPR-nummer angivet for opdatering.", "danger")
        return redirect(url_for("vis_vitale_tegn"))

 
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)