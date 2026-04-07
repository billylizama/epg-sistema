from flask import Blueprint, render_template, request, jsonify, send_file, flash, redirect, url_for
from flask_login import login_required, current_user
from functools import wraps
from extensions import db
from models.programa import Programa, HistorialIngreso
import io

tesorera = Blueprint('tesorera', __name__)


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


@tesorera.route('/tesorera/presupuesto')
@login_required
@rol_requerido('tesorera', 'admin')
def presupuesto():
    programas = Programa.query.order_by(Programa.facultad, Programa.tipo_programa).all()
    return render_template('tesorera/presupuesto.html', programas=programas)


@tesorera.route('/tesorera/actualizar_ingreso/<int:prog_id>', methods=['POST'])
@login_required
@rol_requerido('tesorera', 'admin')
def actualizar_ingreso(prog_id):
    prog = Programa.query.get_or_404(prog_id)
    data = request.get_json()
    nuevo_monto = float(data.get('ingresos', 0))

    historial = HistorialIngreso(
        programa_id=prog.id,
        monto_anterior=prog.ingresos,
        monto_nuevo=nuevo_monto,
        modificado_por=current_user.username
    )
    db.session.add(historial)
    prog.ingresos = nuevo_monto
    db.session.commit()

    return jsonify({
        'ok': True,
        'gastos': prog.gastos_total,
        'retencion_ocep': prog.retencion_ocep,
        'retencion_epg': prog.retencion_epg,
        'saldo': prog.saldo_actual,
        'situacion': prog.situacion
    })


@tesorera.route('/tesorera/exportar')
@login_required
@rol_requerido('tesorera', 'admin')
def exportar():
    import openpyxl
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Presupuesto EPG'

    header_fill = PatternFill(start_color='6B1A2A', end_color='6B1A2A', fill_type='solid')
    header_font = Font(color='FFFFFF', bold=True)
    thin = Side(style='thin')
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    subrow_fill = PatternFill(start_color='F2E8EA', end_color='F2E8EA', fill_type='solid')
    total_fill = PatternFill(start_color='D9D9D9', end_color='D9D9D9', fill_type='solid')

    fills_sit = {
        'BIEN':        PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid'),
        'CRITICO':     PatternFill(start_color='FFEB9C', end_color='FFEB9C', fill_type='solid'),
        'EN EL LIMITE':PatternFill(start_color='FFEB9C', end_color='FFEB9C', fill_type='solid'),
        'SOBREPASADO': PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid'),
    }

    headers = ['N°', 'TIPO', 'FACULTAD', 'MENCION', 'INGRESOS', 'GASTOS',
               'RET. OCEP (10%)', 'RET. EPG (5%)', 'SALDO', 'SITUACION']
    col_widths = [5, 12, 35, 60, 15, 15, 16, 16, 15, 14]

    for col, (h, w) in enumerate(zip(headers, col_widths), 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.border = border
        ws.column_dimensions[cell.column_letter].width = w
    ws.row_dimensions[1].height = 30

    def write_money(ws, r, c, val, brd):
        cell = ws.cell(row=r, column=c, value=val)
        cell.number_format = '#,##0.00'
        cell.alignment = Alignment(horizontal='right')
        cell.border = brd
        return cell

    current_row = 2
    numero = 1

    # ── Fila EPG primero ──────────────────────────────────────────────
    epg = Programa.query.filter_by(es_epg=True).first()
    if epg:
        mencion_epg = f'{epg.mencion} - DERECHO DE TRÁMITES ACADÉMICOS'
        datos_epg = [numero, epg.tipo_programa, epg.facultad, mencion_epg,
                     epg.ingresos, epg.gastos_total, epg.retencion_ocep,
                     None,            # RET EPG vacío en fila principal
                     epg.saldo_actual, epg.situacion]
        for col, val in enumerate(datos_epg, 1):
            cell = ws.cell(row=current_row, column=col, value=val)
            cell.border = border
            if col in [5, 6, 7, 9]:
                cell.number_format = '#,##0.00'
                cell.alignment = Alignment(horizontal='right')
                cell.font = Font(bold=True)
            elif col == 10:
                cell.alignment = Alignment(horizontal='center')
                if epg.situacion in fills_sit:
                    cell.fill = fills_sit[epg.situacion]
            elif col == 1:
                cell.alignment = Alignment(horizontal='center')
        current_row += 1
        numero += 1

        # Sub-fila: "Retención del 5% a favor de la Escuela" + valor en col INGRESOS
        for col in range(1, 11):
            c = ws.cell(row=current_row, column=col)
            c.border = border
            c.fill = subrow_fill

        label_cell = ws.cell(row=current_row, column=4,
                             value='Retención del 5% a favor de la Escuela')
        label_cell.alignment = Alignment(horizontal='right')
        label_cell.fill = subrow_fill
        label_cell.border = border
        label_cell.font = Font(italic=True, color='5A5A5A')

        # Valor va en columna INGRESOS (col 5)
        ret_cell = ws.cell(row=current_row, column=5, value=epg.retencion_epg)
        ret_cell.number_format = '#,##0.00'
        ret_cell.alignment = Alignment(horizontal='right')
        ret_cell.fill = subrow_fill
        ret_cell.border = border
        ret_cell.font = Font(italic=True)

        ws.row_dimensions[current_row].height = 13
        current_row += 1

    # ── Demás programas ───────────────────────────────────────────────
    otros = Programa.query.filter_by(es_epg=False).order_by(
        Programa.facultad, Programa.tipo_programa, Programa.mencion).all()

    for p in otros:
        datos = [numero, p.tipo_programa, p.facultad, p.mencion,
                 p.ingresos, p.gastos_total, p.retencion_ocep,
                 p.retencion_epg, p.saldo_actual, p.situacion]
        for col, val in enumerate(datos, 1):
            cell = ws.cell(row=current_row, column=col, value=val)
            cell.border = border
            if col in [5, 6, 7, 8, 9]:
                cell.number_format = '#,##0.00'
                cell.alignment = Alignment(horizontal='right')
            elif col == 10:
                cell.alignment = Alignment(horizontal='center')
                if p.situacion in fills_sit:
                    cell.fill = fills_sit[p.situacion]
            elif col == 1:
                cell.alignment = Alignment(horizontal='center')
        current_row += 1
        numero += 1

    # ── Fila TOTALES ──────────────────────────────────────────────────
    total_row = current_row
    # La fila de sub-EPG no entra en los SUM, calculamos manualmente
    all_progs = ([epg] if epg else []) + otros
    t_ing  = sum(p.ingresos      for p in all_progs)
    t_gas  = sum(p.gastos_total  for p in all_progs)
    t_ocep = sum(p.retencion_ocep for p in all_progs)
    t_epg  = sum(p.retencion_epg  for p in all_progs)
    t_sal  = sum(p.saldo_actual   for p in all_progs)

    totales = [None, None, None, 'TOTALES', t_ing, t_gas, t_ocep, t_epg, t_sal, None]
    for col, val in enumerate(totales, 1):
        cell = ws.cell(row=total_row, column=col, value=val)
        cell.border = border
        cell.fill = total_fill
        cell.font = Font(bold=True)
        if col == 4:
            cell.alignment = Alignment(horizontal='right')
        if col in [5, 6, 7, 8, 9]:
            cell.number_format = '#,##0.00'
            cell.alignment = Alignment(horizontal='right')

    ws.freeze_panes = 'A2'

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return send_file(output, download_name='presupuesto_epg.xlsx',
                     as_attachment=True,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
