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

app = Flask(__name__)
app.config.from_object(Config)
app.config["SECRET_KEY"] = Config.SECRET_KEY
db = SQLAlchemy(app)  # Initialize SQLAlchemy with the app's config

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"  # Ensure a defined login view

# Context Processor to inject dark_mode into all templates
@app.context_processor
def inject_dark_mode():
    return {'dark_mode': session.get('dark_mode', False)}

# Helper function to derive a key of appropriate length
def get_aes_key():
    key = app.config["SECRET_KEY"]
    if isinstance(key, str):
        key = key.encode('utf-8')
    # Ensure the key is 16, 24, or 32 bytes long for AES
    if len(key) not in (16, 24, 32):
        raise ValueError("SECRET_KEY must be 16, 24, or 32 bytes long for AES encryption.")
    return key

# Encryption Functions
def encrypt_cpr(cpr_number):
    key = get_aes_key()
    cipher = AES.new(key, AES.MODE_EAX)
    ciphertext, tag = cipher.encrypt_and_digest(cpr_number.encode('utf-8'))
    return base64.b64encode(cipher.nonce + tag + ciphertext).decode('utf-8')

def decrypt_cpr(encrypted_cpr):
    key = get_aes_key()
    try:
        data = base64.b64decode(encrypted_cpr.encode('utf-8'))
        nonce, tag, ciphertext = data[:16], data[16:32], data[32:]
        cipher = AES.new(key, AES.MODE_EAX, nonce=nonce)
        return cipher.decrypt_and_verify(ciphertext, tag).decode('utf-8')
    except (ValueError, KeyError) as e:
        # Handle incorrect decryption
        app.logger.error(f"Decryption failed: {e}")
        return "Decryption Error"

# Models
class Users(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)

class VitaleTegn(db.Model):
    __tablename__ = 'vitale_tegn'
    
    id = db.Column(db.Integer, primary_key=True)
    cpr_nummer = db.Column(db.String(256), nullable=False)  # Encrypted CPR
    cpr_hash = db.Column(db.String(64), nullable=False, index=True)  # Hashed CPR for search
    tidspunkt = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    puls = db.Column(db.Integer, nullable=False)
    temperatur = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f"<VitaleTegn {self.cpr_nummer} - {self.puls} bpm - {self.temperatur}°C>"

    @staticmethod
    def hash_cpr(cpr):
        # Using plain SHA-256
        return hashlib.sha256(cpr.encode('utf-8')).hexdigest()

    @staticmethod
    def insert_data(cpr, puls, temperatur):
        encrypted_cpr = encrypt_cpr(cpr)
        cpr_hash = VitaleTegn.hash_cpr(cpr)
        new_record = VitaleTegn(
            cpr_nummer=encrypted_cpr,
            cpr_hash=cpr_hash,
            puls=puls,
            temperatur=temperatur
        )
        db.session.add(new_record)
        db.session.commit()

    @staticmethod
    def get_records_by_cpr(cpr):
        cpr_hash = VitaleTegn.hash_cpr(cpr)
        return VitaleTegn.query.filter_by(cpr_hash=cpr_hash).order_by(VitaleTegn.tidspunkt.desc()).all()

# Create all tables
with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))

# Route to toggle dark mode
@app.route('/toggle_dark_mode', methods=['POST'])
def toggle_dark_mode():
    # Toggle the dark_mode session variable
    current_theme = session.get('dark_mode', False)
    session['dark_mode'] = not current_theme
    return redirect(request.referrer or url_for('home'))

# Routes
@app.route('/register', methods=["GET", "POST"])
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
            return redirect(url_for("login"))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Registration failed: {e}")
            flash(f"Registration failed: {e}", "danger")
    return render_template("sign_up.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password").strip()
        user = Users.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash("Login successful.", "success")
            return redirect(url_for("home"))
        else:
            flash("Invalid username or password.", "danger")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("home"))

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/vis_vitale_tegn", methods=["GET", "POST"])
@login_required
def vis_vitale_tegn():
    if request.method == "POST":
        cpr = request.form.get("cpr", "").strip()
        
        if not cpr:
            flash("Indtast venligst patientens CPR-nummer.", "danger")
            return render_template("vis_vitale_tegn.html", cpr=None, records=None, submitted=True)

        # Validate CPR
        if not re.match(r"^\d{6}-\d{4}$", cpr):
            flash("CPR-nummeret er ikke i korrekt format (DDMMYY-XXXX).", "danger")
            return render_template("vis_vitale_tegn.html", cpr=cpr, records=None, submitted=True)

        records = VitaleTegn.get_records_by_cpr(cpr)
        if records:
            flash(f"Vitale tegn fundet for CPR-nummer: {cpr}", "success")
        else:
            flash(f"Ingen vitale tegn fundet for CPR-nummer: {cpr}", "warning")

        # Decrypt CPR numbers for display
        decrypted_records = []
        for record in records:
            try:
                decrypted_cpr = decrypt_cpr(record.cpr_nummer)
            except Exception as e:
                decrypted_cpr = "Decryption Error"
            decrypted_records.append({
                'id': record.id,
                'cpr_nummer': decrypted_cpr,
                'puls': record.puls,
                'temperatur': record.temperatur,
                'tidspunkt': record.tidspunkt.strftime('%Y-%m-%d %H:%M:%S')  # Formatted string
            })

        return render_template("vis_vitale_tegn.html", cpr=cpr, records=decrypted_records, submitted=True)
    else:
        return render_template("vis_vitale_tegn.html")


@app.route("/fald_detektion")
@login_required
def fald_detektion():
    return render_template("fald.html")


@app.route("/request_update", methods=["POST"])
@login_required
def request_update():
    cpr = request.form.get("cpr", "").strip()
    if not cpr:
        flash("Ingen CPR-nummer angivet for opdatering.", "danger")
        return redirect(url_for("vis_vitale_tegn"))

    # Validate CPR format
    if not re.match(r"^\d{6}-\d{4}$", cpr):
        flash("CPR-nummeret er ikke i korrekt format (DDMMYY-XXXX).", "danger")
        return redirect(url_for("vis_vitale_tegn"))

    try:
        mqtt_client = mqtt.Client()
        mqtt_client.username_pw_set(Config.MQTT_USERNAME, Config.MQTT_PASSWORD)
        mqtt_client.connect(Config.MQTT_BROKER_URL, Config.MQTT_BROKER_PORT)
        mqtt_client.publish(Config.MQTT_TOPIC, cpr)
        mqtt_client.disconnect()
        flash(f"Opdatering anmodet for CPR-nummer: {cpr}", "info")
    except Exception as e:
        app.logger.error(f"Error updating CPR number {cpr}: {e}")
        flash(f"Fejl ved opdatering af CPR-nummer: {cpr} {e}", "danger")

    return redirect(url_for("vis_vitale_tegn"))

@app.route('/insert_data', methods=['GET'])
def insert_data():
    predefined_cpr = "010101-1111"

    try:
        for i in range(10):
            puls = random.randint(60, 100)
            temperatur = round(random.uniform(36.5, 39.0), 1)
            if i < 2:
                cpr_nummer = predefined_cpr
            else:
                day = random.randint(1, 31)
                month = random.randint(1, 12)
                year = random.randint(0, 99)
                serial = random.randint(1000, 9999)
                cpr_nummer = f"{day:02d}{month:02d}{year:02d}-{serial}"

            VitaleTegn.insert_data(cpr_nummer, puls, temperatur)

        # Fetch and decrypt all records for verification
        records = VitaleTegn.query.all()
        decrypted_records = []
        for record in records:
            try:
                decrypted_cpr = decrypt_cpr(record.cpr_nummer)
            except Exception as e:
                decrypted_cpr = "Decryption Error"
            decrypted_records.append({
                'id': record.id,
                'cpr_nummer': decrypted_cpr,
                'puls': record.puls,
                'temperatur': record.temperatur,
                'tidspunkt': record.tidspunkt.strftime('%Y-%m-%d %H:%M:%S')
            })

        return jsonify(decrypted_records)
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error inserting data: {e}")
        flash(f"Error inserting data: {e}", "danger")
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
