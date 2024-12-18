# routes/vitale_routes.py

from flask import render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from datetime import datetime
import re
from encryption import decrypt_data
from models import db, VitaleTegn
from . import vitale_bp
import paho.mqtt.client as mqtt  # Import the MQTT client
from config import Config
import logging

# Configure logging for audit logs
audit_logger = logging.getLogger("audit")
audit_logger.setLevel(logging.INFO)

# Avoid adding multiple handlers if this code runs multiple times
if not audit_logger.handlers:
    file_handler = logging.FileHandler("audit.log")
    # Define the formatter with named placeholders
    formatter = logging.Formatter(
        "%(asctime)s - USER: %(username)s - CPR: %(cpr)s - RECORDS_FETCHED: %(records_fetched)d"
    )
    file_handler.setFormatter(formatter)
    audit_logger.addHandler(file_handler)

@vitale_bp.route("/vis_vitale_tegn", methods=["GET", "POST"])
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

            # Log the audit information with named fields using 'extra'
            audit_logger.info(
                "Fetched records",
                extra={
                    'username': current_user.username,
                    'cpr': cpr,
                    'records_fetched': len(records)
                }
            )

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
        decrypted_battery = decrypt_data(record.battery) if record.battery else "N/A"
        decrypted_records.append({
            'id': record.id,
            'cpr_nummer': decrypted_cpr,
            'puls': decrypted_puls,
            'battery': decrypted_battery,
            'tidspunkt': record.tidspunkt.strftime('%Y-%m-%d %H:%M:%S')
        })

    return render_template(
        "vis_vitale_tegn.html",
        cpr=cpr,
        records=decrypted_records,
        submitted=submitted,
        pagination=pagination,
        date_from=date_from,
        date_to=date_to
    )

@vitale_bp.route("/request_update", methods=["POST"])
@login_required
def request_update():
    cpr = request.form.get("cpr", "").strip()
    if not cpr:
        flash("Ingen CPR-nummer angivet for opdatering.", "danger")
        return redirect(url_for("vitale.vis_vitale_tegn"))

    # Validate CPR format
    if not re.match(r"^\d{6}-\d{4}$", cpr):
        flash("CPR-nummeret er ikke i korrekt format (DDMMYY-XXXX).", "danger")
        return redirect(url_for("vitale.vis_vitale_tegn"))

    try:
        message = f"send_update:{cpr}"
        current_app.logger.debug(f"Preparing to publish message: {message}")
        
        # Initialize MQTT client with the latest callback API
        mqtt_client = mqtt.Client(protocol=mqtt.MQTTv311)
        mqtt_client.username_pw_set(
            Config.MQTT_USERNAME,
            Config.MQTT_PASSWORD
        )
        mqtt_client.connect(
            Config.MQTT_BROKER_URL,
            Config.MQTT_BROKER_PORT,
            Config.MQTT_KEEPALIVE
        )
        mqtt_client.publish(Config.MQTT_CONTROL_TOPIC, message)
        current_app.logger.info(f"Published message: {message} to topic {Config.MQTT_CONTROL_TOPIC}")
        mqtt_client.disconnect()
        flash(f"Opdatering anmodet for CPR-nummer: {cpr}", "info")
    except Exception as e:
        current_app.logger.error(f"Error updating CPR number {cpr}: {e}")
        flash(f"Fejl ved opdatering af CPR-nummer: {cpr} {e}", "danger")

    return redirect(url_for("vitale.vis_vitale_tegn", cpr=cpr))
