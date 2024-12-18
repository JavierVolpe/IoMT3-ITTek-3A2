from flask_login import current_user
from models import Users

def load_user(user_id):
    return Users.query.get(int(user_id))
