from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, send_file
from flask_login import login_required, current_user
from functools import wraps
from extensions import db
from models.programa import Programa
from models.registro_gasto import RegistroGasto
from models.usuario import Usuario
from werkzeug.security import generate_password_hash
from datetime import datetime
import io

admin_bp = Blueprint('admin', __name__)

MESES = ['ENERO', 'FEBRERO', 'MARZO', 'ABRIL', 'MAYO', 'JUNIO',
         'JULIO', 'AGOSTO', 'SEPTIEMBRE', 'OCTUBRE', 'NOVIEMBRE', 'DICIEMBRE']

DESCRIPCIONES = ['HONORARIOS', 'SUBVENCION', 'PLANILLA DIRECTORIO', 'PLANILLA DE SUSTENTACION',
                 'PLANILLA DOCENTE INVITADO', 'PLANILLA DOCENTE NOMBRADO', 'OTROS']


def admin_requerido(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.rol != 'admin':
            flash('Acceso solo para administrador.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/admin/dashboard')
@login_required
@admin_requerido
def dashboard():
    programas = Programa.query.all()
    total_ingresos = sum(p.ingresos for p in programas)
    total_gastos = sum(p.gastos_total for p in programas)
    total_ret_ocep = sum(p.retencion_ocep for p in programas)
    total_ret_epg = sum(p.retencion_epg for p in programas)
    total_saldo = total_ingresos - total_gastos - total_ret_ocep - total_ret_epg

    pendientes_docente = RegistroGasto.query.filter_by(
        descripcion='PLANILLA DOCENTE INVITADO', condicion='EN PROCESO').count()

    return render_template('admin/dashboard.html',
                           programas=programas,
                           total_ingresos=total_ingresos,
                           total_gastos=total_gastos,
                           total_ret_ocep=total_ret_ocep,
                           total_ret_epg=total_ret_epg,
                           total_saldo=total_saldo,
                           pendientes_docente=pendientes_docente)


@admin_bp.route('/admin/registros')
@login_required
@admin_requerido
def registros():
    page = request.args.get('page', 1, type=int)
    per_page = 20

    query = RegistroGasto.query

    f_mes = request.args.get('mes', '')
    f_facultad = request.args.get('facultad', '')
    f_mencion = request.args.get('mencion', '')
    f_descripcion = request.args.get('descripcion', '')
    f_estado = request.args.get('estado', '')
    f_condicion = request.args.get('condicion', '')
    f_anio = request.args.get('anio', '')
    f_docente_invitado = request.args.get('docente_invitado', '')

    if f_mes:
        query = query.filter(RegistroGasto.mes == f_mes)
    if f_facultad:
        query = query.filter(RegistroGasto.facultad == f_facultad)
    if f_mencion:
        query = query.filter(RegistroGasto.mencion.contains(f_mencion))
    if f_descripcion:
        query = query.filter(RegistroGasto.descripcion == f_descripcion)
    if f_estado:
        query = query.filter(RegistroGasto.estado == f_estado)
    if f_condicion:
        query = query.filter(RegistroGasto.condicion == f_condicion)
    if f_anio:
        query = query.filter(RegistroGasto.anio == int(f_anio))
    if f_docente_invitado:
        query = query.filter(RegistroGasto.descripcion == 'PLANILLA DOCENTE INVITADO',
                             RegistroGasto.condicion == 'EN PROCESO')

    regs = query.order_by(RegistroGasto.fecha_registro.desc()).paginate(
        page=page, per_page=per_page, error_out=False)

    pendientes_docente = RegistroGasto.query.filter_by(
        descripcion='PLANILLA DOCENTE INVITADO', condicion='EN PROCESO').count()

    facultades = db.session.query(Programa.facultad).distinct().order_by(Programa.facultad).all()
    return render_template('admin/registros.html',
                           registros=regs,
                           facultades=[f[0] for f in facultades],
                           meses=MESES,
                           descripciones=DESCRIPCIONES,
                           pendientes_docente=pendientes_docente,
                           filtros={
                               'mes': f_mes, 'facultad': f_facultad,
                               'mencion': f_mencion, 'descripcion': f_descripcion,
                               'estado': f_estado, 'condicion': f_condicion,
                               'anio': f_anio, 'docente_invitado': f_docente_invitado
                           })


@admin_bp.route('/admin/actualizar_condicion/<int:reg_id>', methods=['POST'])
@login_required
@admin_requerido
def actualizar_condicion(reg_id):
    reg = RegistroGasto.query.get_or_404(reg_id)
    data = request.get_json()
    nueva_condicion = data.get('condicion')
    if nueva_condicion in ['EN PROCESO', 'REALIZADO']:
        reg.condicion = nueva_condicion
        reg.validado_por = current_user.username
        reg.fecha_validacion = datetime.utcnow()
        db.session.commit()
        return jsonify({'ok': True})
    return jsonify({'ok': False, 'mensaje': 'Condicion invalida'}), 400


@admin_bp.route('/admin/usuarios')
@login_required
@admin_requerido
def usuarios():
    users = Usuario.query.order_by(Usuario.username).all()
    return render_template('admin/usuarios.html', usuarios=users)


@admin_bp.route('/admin/usuarios/nuevo', methods=['POST'])
@login_required
@admin_requerido
def nuevo_usuario():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    nombre = request.form.get('nombre_completo', '').strip()
    rol = request.form.get('rol', '')

    if Usuario.query.filter_by(username=username).first():
        flash(f'El usuario "{username}" ya existe.', 'danger')
        return redirect(url_for('admin.usuarios'))

    u = Usuario(username=username, nombre_completo=nombre, rol=rol)
    u.set_password(password)
    db.session.add(u)
    db.session.commit()
    flash('Usuario creado correctamente.', 'success')
    return redirect(url_for('admin.usuarios'))


@admin_bp.route('/admin/usuarios/toggle/<int:user_id>', methods=['POST'])
@login_required
@admin_requerido
def toggle_usuario(user_id):
    u = Usuario.query.get_or_404(user_id)
    if u.id == current_user.id:
        flash('No puedes desactivar tu propia cuenta.', 'warning')
    else:
        u.activo = not u.activo
        db.session.commit()
        estado = 'activado' if u.activo else 'desactivado'
        flash(f'Usuario {u.username} {estado}.', 'success')
    return redirect(url_for('admin.usuarios'))


@admin_bp.route('/admin/usuarios/cambiar_password/<int:user_id>', methods=['POST'])
@login_required
@admin_requerido
def cambiar_password(user_id):
    u = Usuario.query.get_or_404(user_id)
    nueva = request.form.get('nueva_password', '')
    if len(nueva) < 4:
        flash('La contrasena debe tener al menos 4 caracteres.', 'danger')
    else:
        u.set_password(nueva)
        db.session.commit()
        flash(f'Contrasena de {u.username} actualizada.', 'success')
    return redirect(url_for('admin.usuarios'))


@admin_bp.route('/admin/eliminar_registro/<int:reg_id>', methods=['POST'])
@login_required
@admin_requerido
def eliminar_registro(reg_id):
    reg = RegistroGasto.query.get_or_404(reg_id)
    info = f'Exp. {reg.expediente} - {reg.descripcion} - S/ {reg.monto:,.2f}'
    db.session.delete(reg)
    db.session.commit()
    flash(f'Registro eliminado: {info}', 'success')
    return redirect(request.referrer or url_for('admin.registros'))


@admin_bp.route('/admin/backup')
@login_required
@admin_requerido
def backup_manual():
    import shutil, os
    from config import Config
    src = Config.SQLALCHEMY_DATABASE_URI.replace('sqlite:///', '')
    backup_dir = Config.BACKUP_DIR
    os.makedirs(backup_dir, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    dst = os.path.join(backup_dir, f'epg_{ts}.db')
    shutil.copy2(src, dst)
    flash(f'Backup creado: epg_{ts}.db', 'success')
    return redirect(url_for('admin.dashboard'))
