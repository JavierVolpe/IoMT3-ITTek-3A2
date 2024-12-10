from flask import Flask, render_template, request, url_for, redirect, flash
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

app = Flask(__name__)
app.config.from_object(Config)
app.config["SECRET_KEY"] = Config.SECRET_KEY
db = SQLAlchemy(app)  # Initialize SQLAlchemy with the app's config

login_manager = LoginManager()
login_manager.init_app(app)

# AES Encryption Functions
def encrypt_cpr(cpr_number):
    # Ensure the key is in bytes (if it's not already)
    cipher = AES.new(Config.SECRET_KEY, AES.MODE_EAX)
    ciphertext, tag = cipher.encrypt_and_digest(cpr_number.encode('utf-8'))
    return base64.b64encode(cipher.nonce + tag + ciphertext).decode('utf-8')

def decrypt_cpr(encrypted_cpr):
    data = base64.b64decode(encrypted_cpr.encode('utf-8'))
    nonce, tag, ciphertext = data[:16], data[16:32], data[32:]
    cipher = AES.new(Config.SECRET_KEY, AES.MODE_EAX, nonce=nonce)
    return cipher.decrypt_and_verify(ciphertext, tag).decode('utf-8')

# Models
class Users(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)

class VitaleTegn(db.Model):
    __tablename__ = 'vitale_tegn'
    
    id = db.Column(db.Integer, primary_key=True)
    cpr_nummer = db.Column(db.String(256), nullable=False)  # Store encrypted CPR number
    tidspunkt = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    puls = db.Column(db.Integer, nullable=False)
    temperatur = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f"<VitaleTegn {self.cpr_nummer} - {self.puls} bpm - {self.temperatur}°C>"

    @staticmethod
    def insert_data(cpr, puls, temperatur):
        encrypted_cpr = encrypt_cpr(cpr)
        new_record = VitaleTegn(
            cpr_nummer=encrypted_cpr,
            puls=puls,
            temperatur=temperatur
        )
        db.session.add(new_record)
        db.session.commit()

    @staticmethod
    def get_records_by_cpr(cpr):
        encrypted_cpr = encrypt_cpr(cpr)
        return VitaleTegn.query.filter_by(cpr_nummer=encrypted_cpr).all()

with app.app_context():
    db.create_all()


# Routes
@login_manager.user_loader
def loader_user(user_id):
    return Users.query.get(user_id)

@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        hashed_password = generate_password_hash(request.form.get("password"), method="pbkdf2:sha1")  # Hashing the password
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
            records = VitaleTegn.get_records_by_cpr(cpr)
            
            if records:
                flash(f"Vitale tegn fundet for CPR-nummer: {cpr}", "success")
            else:
                flash(f"Ingen vitale tegn fundet for CPR-nummer: {cpr}", "warning")
            
            return render_template("vis_vitale_tegn.html", cpr=cpr, records=records, submitted=True)
        else:
            flash("Indtast venligst patientens CPR-nummer.", "danger")
            return render_template("vis_vitale_tegn.html", cpr=None, records=None, submitted=True)
    else:
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

@app.route('/insert_data', methods=['GET'])
def insert_data():
    # Predefined CPR number
    predefined_cpr = "010101-1111"

    # Insert 10 rows of data into vitale_tegn
    for i in range(10):
        # Generate random pulse and temperature values
        puls = random.randint(60, 100)  # Random pulse between 60 and 100
        temperatur = round(random.uniform(36.5, 39.0), 1)  # Random temperature between 36.5°C and 39°C

        # Use predefined CPR for the first 2 records, others will follow a different pattern
        if i < 2:
            cpr_nummer = predefined_cpr
        else:
            cpr_nummer = f"{random.randint(1, 31):02d}{random.randint(1, 12):02d}{random.randint(0, 99):02d}-{random.randint(1000, 9999)}"

        # Encrypt CPR number
        encrypted_cpr = encrypt_cpr(cpr_nummer)

        # Create and add a new record
        record = VitaleTegn(cpr_nummer=encrypted_cpr, puls=puls, temperatur=temperatur)
        db.session.add(record)

    # Commit the changes to the database
    db.session.commit()

    # Get all records and decrypt CPR for verification
    records = VitaleTegn.query.all()
    decrypted_records = []

    for record in records:
        decrypted_cpr = decrypt_cpr(record.cpr_nummer)
        decrypted_records.append({
            'id': record.id,
            'cpr_nummer': decrypted_cpr,
            'puls': record.puls,
            'temperatur': record.temperatur,
            'tidspunkt': record.tidspunkt
        })

    # Return the decrypted data as JSON response for verification
    return jsonify(decrypted_records)
    
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
