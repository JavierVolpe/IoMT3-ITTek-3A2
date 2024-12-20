# routes/vitale_routes.py

import logging
from flask import render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from datetime import datetime
import re
from encryption import decrypt_data
from models import db, VitaleTegn
from . import vitale_bp
import paho.mqtt.client as mqtt
from config import Config

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from io import BytesIO
import base64

audit_logger = logging.getLogger("audit")
app_logger = logging.getLogger("app")

@vitale_bp.route("/vis_vitale_tegn", methods=["GET", "POST"])
@login_required
def vis_vitale_tegn():
    if request.method == "POST":
        cpr = request.form.get("cpr", "").strip()
        date_from = request.form.get("date_from", "").strip()
        date_to = request.form.get("date_to", "").strip()
        page = 1
    else:
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

            audit_logger.info(
                "Fetched records",
                extra={
                    'username': current_user.username,
                    'action': 'FETCH_RECORDS',
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

    decrypted_records = []
    for record in records:
        try:
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
        except Exception as e:
            app_logger.error(f"Decryption error for record ID {record.id}: {e}")
            # Optionally, skip this record or handle it as needed

    # NEW CODE BELOW
    graph_data = None
    if len(decrypted_records) > 5:
        # Filter records where 'puls' can be converted to a float
        valid_records = []
        for r in decrypted_records:
            try:
                puls_float = float(r['puls'].replace(',', '.'))  # Ensure decimal separator is '.'
                valid_records.append({'tidspunkt': r['tidspunkt'], 'puls': puls_float})
            except ValueError:
                app_logger.warning(f"Invalid pulse value '{r['puls']}' for CPR {cpr} at {r['tidspunkt']}.")

        if len(valid_records) > 0:
            # Sort records by timestamp to ensure the plot is chronological
            valid_records.sort(key=lambda x: datetime.strptime(x['tidspunkt'], '%Y-%m-%d %H:%M:%S'))
            timestamps = [r['tidspunkt'] for r in valid_records]
            pulses = [r['puls'] for r in valid_records]

            # Create a plot
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.plot(timestamps, pulses, marker='o', linestyle='-', color='blue')
            ax.set_title('Puls over tid', fontsize=16)
            ax.set_xlabel('Tidspunkt', fontsize=14)
            ax.set_ylabel('Puls (bpm)', fontsize=14)
            ax.grid(True)
            fig.autofmt_xdate(rotation=45)

            # Save the plot to a bytes buffer
            buf = BytesIO()
            plt.tight_layout()
            fig.savefig(buf, format='png')
            buf.seek(0)
            graph_png = buf.getvalue()
            buf.close()
            plt.close(fig)

            # Encode the PNG image to base64 string
            graph_data = base64.b64encode(graph_png).decode('utf-8')
        else:
            app_logger.info(f"No valid pulse data available to plot for CPR {cpr}.")

    return render_template(
        "vis_vitale_tegn.html",
        cpr=cpr,
        records=decrypted_records,
        submitted=submitted,
        pagination=pagination,
        date_from=date_from,
        date_to=date_to,
        graph_data=graph_data
    )

@vitale_bp.route("/request_update", methods=["POST"])
@login_required
def request_update():
    cpr = request.form.get("cpr", "").strip()
    if not cpr:
        flash("Ingen CPR-nummer angivet for opdatering.", "danger")
        return redirect(url_for("vitale.vis_vitale_tegn"))

    if not re.match(r"^\d{6}-\d{4}$", cpr):
        flash("CPR-nummeret er ikke i korrekt format (DDMMYY-XXXX).", "danger")
        return redirect(url_for("vitale.vis_vitale_tegn"))

    try:
        message = f"send_update:{cpr}"
        app_logger.debug(f"Preparing to publish message: {message}")

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
        app_logger.info(f"Published message: {message} to topic {Config.MQTT_CONTROL_TOPIC}")
        mqtt_client.disconnect()
        flash(f"Opdatering anmodet for CPR-nummer: {cpr}", "info")
    except Exception as e:
        app_logger.error(f"Error updating CPR number {cpr}: {e}")
        flash(f"Fejl ved opdatering af CPR-nummer: {cpr} {e}", "danger")

    return redirect(url_for("vitale.vis_vitale_tegn", cpr=cpr))
