from flask import Blueprint, render_template
from flask_login import login_required

bp = Blueprint('calendar', __name__)

@bp.route('/')
@login_required
def index():
    return render_template('calendar.html')