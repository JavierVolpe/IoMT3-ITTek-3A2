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
    # If user is authenticated, use their preference. Otherwise, fall back to session.
    if current_user.is_authenticated:
        return {'dark_mode': current_user.dark_mode}
    else:
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

# Generic Encryption/Decryption Functions
def encrypt_data(plaintext):
    key = get_aes_key()
    cipher = AES.new(key, AES.MODE_EAX)
    ciphertext, tag = cipher.encrypt_and_digest(plaintext.encode('utf-8'))
    return base64.b64encode(cipher.nonce + tag + ciphertext).decode('utf-8')

def decrypt_data(encrypted_text):
    key = get_aes_key()
    try:
        data = base64.b64decode(encrypted_text.encode('utf-8'))
        nonce, tag, ciphertext = data[:16], data[16:32], data[32:]
        cipher = AES.new(key, AES.MODE_EAX, nonce=nonce)
        return cipher.decrypt_and_verify(ciphertext, tag).decode('utf-8')
    except (ValueError, KeyError) as e:
        app.logger.error(f"Decryption failed: {e}")
        return "Decryption Error"

# Models
class Users(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    dark_mode = db.Column(db.Boolean, default=False)  # User preference for dark mode

class VitaleTegn(db.Model):
    __tablename__ = 'vitale_tegn'
    
    id = db.Column(db.Integer, primary_key=True)
    cpr_nummer = db.Column(db.String(256), nullable=False)  # Encrypted CPR
    cpr_hash = db.Column(db.String(64), nullable=False, index=True)  # Hashed CPR for search
    tidspunkt = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    puls = db.Column(db.String(256), nullable=False)  # Encrypted puls

    def __repr__(self):
        return f"<VitaleTegn {self.cpr_nummer}>"

    @staticmethod
    def hash_cpr(cpr):
        # Using plain SHA-256
        return hashlib.sha256(cpr.encode('utf-8')).hexdigest()

    @staticmethod
    def insert_data(cpr, puls):
        # Encrypt data fields
        encrypted_cpr = encrypt_data(cpr)
        encrypted_puls = encrypt_data(str(puls))
        cpr_hash = VitaleTegn.hash_cpr(cpr)
        new_record = VitaleTegn(
            cpr_nummer=encrypted_cpr,
            cpr_hash=cpr_hash,
            puls=encrypted_puls
        )
        db.session.add(new_record)
        db.session.commit()

    @staticmethod
    def get_records_by_cpr_query(cpr):
        cpr_hash = VitaleTegn.hash_cpr(cpr)
        return VitaleTegn.query.filter_by(cpr_hash=cpr_hash)

# Create all tables
with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))

# Route to toggle dark mode (session-based, deprecated by user preference but still can be used)
@app.route('/toggle_dark_mode', methods=['POST'])
def toggle_dark_mode():
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

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password").strip()
        remember = request.form.get("remember") == 'on'  # Capture the remember option

        user = Users.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user, remember=remember)
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
        date_from = request.form.get("date_from", "").strip()
        date_to = request.form.get("date_to", "").strip()
        page = 1
    else:
        # For pagination links
        cpr = request.args.get("cpr", "").strip() if request.args.get("cpr") else ""
        date_from = request.args.get("date_from", "").strip() if request.args.get("date_from") else ""
        date_to = request.args.get("date_to", "").strip() if request.args.get("date_to") else ""
        page = request.args.get('page', 1, type=int)

    submitted = (request.method == "POST")
    records = []
    pagination = None

    if cpr:
        if not re.match(r"^\d{6}-\d{4}$", cpr):
            flash("CPR-nummeret er ikke i korrekt format (DDMMYY-XXXX).", "danger")
        else:
            query = VitaleTegn.get_records_by_cpr_query(cpr)

            # Apply date filters if valid
            if date_from:
                try:
                    dt_from = datetime.strptime(date_from, "%Y-%m-%d")
                    query = query.filter(VitaleTegn.tidspunkt >= dt_from)
                except ValueError:
                    flash("Ugyldig startdato format. Brug YYYY-MM-DD.", "danger")

            if date_to:
                try:
                    dt_to = datetime.strptime(date_to, "%Y-%m-%d")
                    query = query.filter(VitaleTegn.tidspunkt <= dt_to)
                except ValueError:
                    flash("Ugyldig slutdato format. Brug YYYY-MM-DD.", "danger")

            pagination = query.order_by(VitaleTegn.tidspunkt.desc()).paginate(page=page, per_page=10)
            records = pagination.items

            if records:
                flash(f"Vitale tegn fundet for CPR-nummer: {cpr}", "success")
            else:
                flash(f"Ingen vitale tegn fundet for CPR-nummer: {cpr}", "warning")
    else:
        if submitted:
            flash("Indtast venligst patientens CPR-nummer.", "danger")

    # Decrypt records
    decrypted_records = []
    for record in records:
        decrypted_cpr = decrypt_data(record.cpr_nummer)
        decrypted_puls = decrypt_data(record.puls)
        decrypted_records.append({
            'id': record.id,
            'cpr_nummer': decrypted_cpr,
            'puls': decrypted_puls,
            'tidspunkt': record.tidspunkt.strftime('%Y-%m-%d %H:%M:%S')
        })

    return render_template("vis_vitale_tegn.html", cpr=cpr, records=decrypted_records, submitted=submitted, pagination=pagination, date_from=date_from, date_to=date_to)

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
        message = f"send_update:{cpr}"
        mqtt_client = mqtt.Client()
        mqtt_client.username_pw_set(Config.MQTT_USERNAME, Config.MQTT_PASSWORD)
        mqtt_client.connect(Config.MQTT_BROKER_URL, Config.MQTT_BROKER_PORT)
        mqtt_client.publish(Config.MQTT_TOPIC, message)
        mqtt_client.disconnect()
        flash(f"Opdatering anmodet for CPR-nummer: {cpr}", "info")
    except Exception as e:
        app.logger.error(f"Error updating CPR number {cpr}: {e}")
        flash(f"Fejl ved opdatering af CPR-nummer: {cpr} {e}", "danger")

    return redirect(url_for("vis_vitale_tegn", cpr=cpr))

@app.route('/insert_data', methods=['GET'])
def insert_data():
    predefined_cpr = "010101-1111"

    try:
        for i in range(10):
            puls = random.randint(60, 100)
            if i < 2:
                cpr_nummer = predefined_cpr
            else:
                day = random.randint(1, 28)
                month = random.randint(1, 12)
                year = random.randint(0, 99)
                serial = random.randint(1000, 9999)
                cpr_nummer = f"{day:02d}{month:02d}{year:02d}-{serial}"

            VitaleTegn.insert_data(cpr_nummer, puls)

        # Fetch and decrypt all records for verification
        records = VitaleTegn.query.all()
        decrypted_records = []
        for record in records:
            decrypted_cpr = decrypt_data(record.cpr_nummer)
            decrypted_puls = decrypt_data(record.puls)
            decrypted_records.append({
                'id': record.id,
                'cpr_nummer': decrypted_cpr,
                'puls': decrypted_puls,
                'tidspunkt': record.tidspunkt.strftime('%Y-%m-%d %H:%M:%S')
            })

        return jsonify(decrypted_records)
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error inserting data: {e}")
        flash(f"Error inserting data: {e}", "danger")
        return jsonify({'error': str(e)}), 500

@app.route("/profile", methods=["GET", "POST"])
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
        return redirect(url_for("profile"))
    
    return render_template("profile.html", user=current_user)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)