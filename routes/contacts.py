from flask import Blueprint, render_template
bp = Blueprint('contacts', __name__)

@bp.route('/')
def contacts():
    return render_template('contacts.html')