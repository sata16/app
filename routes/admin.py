from flask import Blueprint, render_template, url_for
from flask_login import login_required
bp = Blueprint('admin', __name__)

@bp.route('/dashboard')
@login_required
def admin_dashboard():
    return render_template('dashboard.html')
