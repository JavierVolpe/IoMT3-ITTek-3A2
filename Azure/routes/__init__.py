from flask import Blueprint

# Define Blueprints
main_bp = Blueprint('main', __name__)
auth_bp = Blueprint('auth', __name__)
vitale_bp = Blueprint('vitale', __name__)

# Import routes to register them with the blueprints
from .auth_routes import *
from .main_routes import *
from .vitale_routes import *
