from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, send_file
from flask_login import login_required, current_user
from functools import wraps
from extensions import db
from models.programa import Programa
from models.registro_gasto import RegistroGasto
from datetime import datetime
import io

operador = Blueprint('operador', __name__)

MESES = ['ENERO', 'FEBRERO', 'MARZO', 'ABRIL', 'MAYO', 'JUNIO',
         'JULIO', 'AGOSTO', 'SEPTIEMBRE', 'OCTUBRE', 'NOVIEMBRE', 'DICIEMBRE']

DESCRIPCIONES = ['HONORARIOS', 'SUBVENCION', 'PLANILLA DIRECTORIO', 'PLANILLA DE SUSTENTACION',
                 'PLANILLA DOCENTE INVITADO', 'PLANILLA DOCENTE NOMBRADO', 'OTROS']


def rol_requerido(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if current_user.rol not in roles:
                flash('No tienes permiso para acceder a esta seccion.', 'danger')
                return redirect(url_for('auth.login'))
            return f(*args, **kwargs)
        return decorated
    return decorator


@operador.route('/operador/registro', methods=['GET', 'POST'])
@login_required
@rol_requerido('operador', 'admin')
def registro():
    facultades = db.session.query(Programa.facultad).distinct().order_by(Programa.facultad).all()
    facultades = [f[0] for f in facultades]

    if request.method == 'POST':
        mes = request.form.get('mes')
        anio = int(request.form.get('anio', datetime.now().year))
        facultad = request.form.get('facultad')
        mencion = request.form.get('mencion')
        expediente = request.form.get('expediente', '').strip() or 'S/N'
        oficio = request.form.get('oficio', '').strip()
        descripcion = request.form.get('descripcion')
        monto = float(request.form.get('monto', 0))
        observacion = request.form.get('observacion', '').strip()

        # Verificar expediente duplicado
        dup = RegistroGasto.query.filter_by(expediente=expediente).first()
        if dup:
            flash(f'Advertencia: el expediente {expediente} ya existe en el registro #{dup.id}.', 'warning')

        # Calcular saldo disponible
        prog = Programa.query.filter_by(mencion=mencion).first()
        if not prog:
            flash('Mencion no encontrada.', 'danger')
            return redirect(url_for('operador.registro'))

        saldo_disp = prog.saldo_actual

        if saldo_disp >= monto:
            estado = 'APROBADO'
        else:
            flash('Sin saldo disponible. El registro no puede guardarse.', 'danger')
            return redirect(url_for('operador.registro'))

        reg = RegistroGasto(
            mes=mes, anio=anio, facultad=facultad, mencion=mencion,
            expediente=expediente, oficio=oficio, descripcion=descripcion,
            monto=monto, estado=estado, observacion=observacion,
            condicion='EN PROCESO', registrado_por=current_user.username
        )
        db.session.add(reg)
        db.session.commit()
        flash('Gasto registrado correctamente.', 'success')
        return redirect(url_for('operador.lista'))

    return render_template('operador/registro.html',
                           facultades=facultades,
                           meses=MESES,
                           descripciones=DESCRIPCIONES,
                           anio_actual=datetime.now().year)


@operador.route('/operador/saldo_tiempo_real')
@login_required
@rol_requerido('operador', 'admin')
def saldo_tiempo_real():
    mencion = request.args.get('mencion', '')
    monto = float(request.args.get('monto', 0))
    prog = Programa.query.filter_by(mencion=mencion).first()
    if not prog:
        return jsonify({'ok': False, 'mensaje': 'Mencion no encontrada'})

    saldo_disp = prog.saldo_actual
    aprobado = saldo_disp >= monto
    return jsonify({
        'ok': True,
        'saldo_disponible': saldo_disp,
        'aprobado': aprobado,
        'ingresos': prog.ingresos,
        'gastos': prog.gastos_total,
        'retencion_ocep': prog.retencion_ocep,
        'retencion_epg': prog.retencion_epg
    })


@operador.route('/operador/menciones_por_facultad')
@login_required
def menciones_por_facultad():
    facultad = request.args.get('facultad', '')
    programas = Programa.query.filter_by(facultad=facultad).order_by(Programa.mencion).all()
    return jsonify([{'mencion': p.mencion} for p in programas])


@operador.route('/operador/lista')
@login_required
@rol_requerido('operador', 'admin')
def lista():
    page = request.args.get('page', 1, type=int)
    per_page = 20

    query = RegistroGasto.query

    # Filtros
    f_mes = request.args.get('mes', '')
    f_facultad = request.args.get('facultad', '')
    f_mencion = request.args.get('mencion', '')
    f_descripcion = request.args.get('descripcion', '')
    f_estado = request.args.get('estado', '')
    f_condicion = request.args.get('condicion', '')
    f_anio = request.args.get('anio', '')

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

    registros = query.order_by(RegistroGasto.fecha_registro.desc()).paginate(
        page=page, per_page=per_page, error_out=False)

    facultades = db.session.query(Programa.facultad).distinct().order_by(Programa.facultad).all()
    return render_template('operador/lista.html',
                           registros=registros,
                           facultades=[f[0] for f in facultades],
                           meses=MESES,
                           descripciones=DESCRIPCIONES,
                           filtros={
                               'mes': f_mes, 'facultad': f_facultad,
                               'mencion': f_mencion, 'descripcion': f_descripcion,
                               'estado': f_estado, 'condicion': f_condicion, 'anio': f_anio
                           })


@operador.route('/operador/editar/<int:reg_id>', methods=['POST'])
@login_required
@rol_requerido('operador', 'admin')
def editar_registro(reg_id):
    reg = RegistroGasto.query.get_or_404(reg_id)
    reg.mes         = request.form.get('mes', reg.mes).upper()
    reg.anio        = int(request.form.get('anio', reg.anio))
    reg.facultad    = request.form.get('facultad', reg.facultad)
    reg.mencion     = request.form.get('mencion', reg.mencion)
    reg.expediente  = request.form.get('expediente', '').strip() or 'S/N'
    reg.oficio      = request.form.get('oficio', '').strip()
    reg.descripcion = request.form.get('descripcion', reg.descripcion).upper()
    reg.monto       = float(request.form.get('monto', reg.monto))
    reg.estado      = request.form.get('estado', reg.estado).upper()
    reg.condicion   = request.form.get('condicion', reg.condicion).upper()
    reg.observacion = request.form.get('observacion', '').strip()
    db.session.commit()
    flash('Registro actualizado correctamente.', 'success')
    return redirect(request.referrer or url_for('operador.lista'))


@operador.route('/operador/eliminar/<int:reg_id>', methods=['POST'])
@login_required
@rol_requerido('operador', 'admin')
def eliminar_registro(reg_id):
    reg = RegistroGasto.query.get_or_404(reg_id)
    db.session.delete(reg)
    db.session.commit()
    flash('Registro eliminado correctamente.', 'success')
    return redirect(request.referrer or url_for('operador.lista'))


@operador.route('/operador/exportar_registros')
@login_required
@rol_requerido('operador', 'admin')
def exportar_registros():
    import openpyxl
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Registros de Gastos'

    header_fill = PatternFill(start_color='960000', end_color='960000', fill_type='solid')
    header_font = Font(color='FFFFFF', bold=True)
    thin = Side(style='thin')
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    headers = ['#', 'MES', 'AÑO', 'FACULTAD', 'MENCION', 'EXPEDIENTE', 'OFICIO',
               'DESCRIPCION', 'MONTO', 'ESTADO', 'CONDICION', 'OBSERVACION',
               'REGISTRADO POR', 'FECHA REGISTRO']

    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center')
        cell.border = border

    registros = RegistroGasto.query.order_by(RegistroGasto.fecha_registro.desc()).all()
    for i, r in enumerate(registros, 1):
        row = i + 1
        datos = [i, r.mes, r.anio, r.facultad, r.mencion, r.expediente, r.oficio,
                 r.descripcion, r.monto, r.estado, r.condicion, r.observacion,
                 r.registrado_por,
                 r.fecha_registro.strftime('%d/%m/%Y %H:%M') if r.fecha_registro else '']
        for col, val in enumerate(datos, 1):
            cell = ws.cell(row=row, column=col, value=val)
            cell.border = border
            if col == 9:
                cell.number_format = '#,##0.00'

    ws.column_dimensions['D'].width = 30
    ws.column_dimensions['E'].width = 50
    ws.column_dimensions['H'].width = 30

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return send_file(output, download_name='registros_gastos.xlsx',
                     as_attachment=True,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
