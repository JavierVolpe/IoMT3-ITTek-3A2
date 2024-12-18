from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import hashlib
from encryption import encrypt_data, decrypt_data
from flask import current_app

db = SQLAlchemy()

class Users(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    dark_mode = db.Column(db.Boolean, default=False)

class VitaleTegn(db.Model):
    __tablename__ = 'vitale_tegn'
    
    id = db.Column(db.Integer, primary_key=True)
    cpr_nummer = db.Column(db.String(256), nullable=False)  # Encrypted CPR
    cpr_hash = db.Column(db.String(64), nullable=False, index=True)  # Hashed CPR for search
    tidspunkt = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    puls = db.Column(db.String(256), nullable=False)  # Encrypted puls
    battery = db.Column(db.String(256), nullable=True)  # Encrypted battery
    
    def __repr__(self):
        return f"<VitaleTegn {self.cpr_nummer}>"

    @staticmethod
    def hash_cpr(cpr):
        return hashlib.sha256(cpr.encode('utf-8')).hexdigest()

    @staticmethod
    def insert_data(cpr, pulse, battery):
        encrypted_cpr = encrypt_data(cpr)
        encrypted_puls = encrypt_data(str(pulse))
        encrypted_battery = encrypt_data(str(battery))
        cpr_hash = VitaleTegn.hash_cpr(cpr)

        new_record = VitaleTegn(
            cpr_nummer=encrypted_cpr,
            cpr_hash=cpr_hash,
            puls=encrypted_puls,
            battery=encrypted_battery
        )
        db.session.add(new_record)
        try:
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error inserting data: {e}")
            return False

    @staticmethod
    def get_records_by_cpr_query(cpr):
        cpr_hash = VitaleTegn.hash_cpr(cpr)
        return VitaleTegn.query.filter_by(cpr_hash=cpr_hash)
