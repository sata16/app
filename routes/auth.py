from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User

bp = Blueprint('auth', __name__, url_prefix='/auth')

# === Вход ===
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        user = User.query.filter_by(username=username).first()

        if not user:
            flash('Пользователь не найден', 'danger')
        elif user.password != password:
            flash('Неверный пароль', 'danger')
        else:
            login_user(user)
            flash(f'Добро пожаловать, {user.username}!', 'success')
            return redirect(url_for('index'))

    return render_template('login.html')

# === Регистрация ===
@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        confirm = request.form.get('confirm_password', '').strip()

        if not username or not email or not password or not confirm:
            flash('Заполните все поля', 'danger')
        elif password != confirm:
            flash('Пароли не совпадают', 'danger')
        elif User.query.filter_by(username=username).first():
            flash('Такое имя пользователя уже существует', 'danger')
        elif User.query.filter_by(email=email).first():
            flash('Такой email уже зарегистрирован', 'danger')
        else:
            new_user = User(username=username, email=email, password=password)
            db.session.add(new_user)
            db.session.commit()
            flash('Регистрация успешна! Теперь войдите.', 'success')
            return redirect(url_for('auth.login'))

    return render_template('register.html')

# === Выход ===
@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('auth.login'))