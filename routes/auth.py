from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models.usuario import Usuario

auth = Blueprint('auth', __name__)


@auth.route('/', methods=['GET', 'POST'])
@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return _redirect_by_role(current_user.rol)

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = Usuario.query.filter_by(username=username, activo=True).first()
        if user and user.check_password(password):
            login_user(user)
            return _redirect_by_role(user.rol)
        flash('Usuario o contrasena incorrectos.', 'danger')

    return render_template('login.html')


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


def _redirect_by_role(rol):
    if rol == 'tesorera':
        return redirect(url_for('tesorera.presupuesto'))
    elif rol == 'operador':
        return redirect(url_for('operador.registro'))
    elif rol == 'admin':
        return redirect(url_for('admin.dashboard'))
    return redirect(url_for('auth.login'))
