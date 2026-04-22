from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from extensions import db
from models.programa import Programa
from models.registro_gasto import RegistroGasto
from models.notificacion import Notificacion
from functools import wraps
from flask import redirect, url_for, flash

analytics = Blueprint('analytics', __name__)


def admin_tesorera_operador(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.rol not in ('admin', 'tesorera', 'operador'):
            flash('Acceso no permitido.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


@analytics.route('/analytics')
@login_required
@admin_tesorera_operador
def dashboard():
    return render_template('analytics/dashboard.html')


# ── API: datos para los graficos ──────────────────────────────────────────────

@analytics.route('/api/analytics/kpis')
@login_required
def api_kpis():
    tipo = request.args.get('tipo', '')   # MAESTRIA, DOCTORADO, o vacio = todos
    facs = request.args.getlist('fac')
    ments = request.args.getlist('men')

    programas = _filtrar(tipo, facs, ments)

    total_ing  = sum(p.ingresos for p in programas)
    total_gas  = sum(p.gastos_total for p in programas)
    total_ocep = sum(p.retencion_ocep for p in programas)
    total_epg  = sum(p.retencion_epg for p in programas)
    total_sal  = sum(p.saldo_actual for p in programas)

    return jsonify({
        'ingresos': total_ing,
        'gastos': total_gas,
        'ret_ocep': total_ocep,
        'ret_epg': total_epg,
        'saldo': total_sal,
    })


@analytics.route('/api/analytics/treemap_facultad')
@login_required
def api_treemap_facultad():
    tipo = request.args.get('tipo', '')
    facs = request.args.getlist('fac')
    ments = request.args.getlist('men')
    programas = _filtrar(tipo, facs, ments)

    facultades = {}
    for p in programas:
        if p.facultad not in facultades:
            facultades[p.facultad] = {'ingresos': 0, 'gastos': 0, 'saldo': 0}
        facultades[p.facultad]['ingresos'] += p.ingresos
        facultades[p.facultad]['gastos']   += p.gastos_total
        facultades[p.facultad]['saldo']    += p.saldo_actual

    result = [
        {
            'facultad': fac,
            'ingresos': round(v['ingresos'], 2),
            'gastos':   round(v['gastos'],   2),
            'saldo':    round(v['saldo'],    2),
        }
        for fac, v in sorted(facultades.items(), key=lambda x: -x[1]['ingresos'])
    ]
    return jsonify(result)


@analytics.route('/api/analytics/top10')
@login_required
def api_top10():
    tipo = request.args.get('tipo', '')
    facs = request.args.getlist('fac')
    ments = request.args.getlist('men')
    programas = _filtrar(tipo, facs, ments)

    top = sorted(programas, key=lambda p: p.ingresos, reverse=True)[:10]
    result = []
    for p in top:
        # Abreviar nombre para el grafico
        nombre = p.mencion
        if ' - ' in nombre:
            partes = nombre.split(' - ')
            nombre = partes[-1] if len(partes[-1]) < 30 else partes[0][:35]
        result.append({
            'mencion': nombre,
            'ingresos': round(p.ingresos, 2),
            'gastos': round(p.gastos_total, 2),
            'saldo': round(p.saldo_actual, 2),
            'situacion': p.situacion,
        })
    return jsonify(result)


@analytics.route('/api/analytics/donut_nivel')
@login_required
def api_donut_nivel():
    tipo = request.args.get('tipo', '')
    facs = request.args.getlist('fac')
    ments = request.args.getlist('men')
    programas = _filtrar(tipo, facs, ments)

    por_nivel = {}
    for p in programas:
        t = p.tipo_programa
        if t not in por_nivel:
            por_nivel[t] = 0
        por_nivel[t] += max(p.saldo_actual, 0)

    total = sum(por_nivel.values()) or 1
    result = [
        {'nivel': k, 'saldo': round(v, 2), 'pct': round(v / total * 100, 1)}
        for k, v in por_nivel.items()
    ]
    return jsonify(result)


@analytics.route('/api/analytics/erosion')
@login_required
def api_erosion():
    tipo = request.args.get('tipo', '')
    facs = request.args.getlist('fac')
    ments = request.args.getlist('men')
    programas = _filtrar(tipo, facs, ments)

    ingresos  = sum(p.ingresos for p in programas)
    ocep      = sum(p.retencion_ocep for p in programas)
    epg       = sum(p.retencion_epg  for p in programas)
    gastos    = sum(p.gastos_total   for p in programas)
    saldo     = sum(p.saldo_actual   for p in programas)

    pct_ocep = round((ingresos - ocep) / ingresos * 100, 1) if ingresos else 0
    pct_epg  = round((ingresos - ocep - epg) / ingresos * 100, 1) if ingresos else 0
    pct_sal  = round(saldo / ingresos * 100, 1) if ingresos else 0

    return jsonify({
        'ingresos':       round(ingresos, 2),
        'despues_ocep':   round(ingresos - ocep, 2),
        'pct_ocep':       pct_ocep,
        'despues_epg':    round(ingresos - ocep - epg, 2),
        'pct_epg':        pct_epg,
        'saldo_final':    round(saldo, 2),
        'pct_saldo':      pct_sal,
    })


@analytics.route('/api/analytics/dist_gasto')
@login_required
def api_dist_gasto():
    tipo  = request.args.get('tipo', '')
    facs  = request.args.getlist('fac')
    ments = request.args.getlist('men')

    query = db.session.query(
        RegistroGasto.descripcion,
        db.func.sum(RegistroGasto.monto).label('total')
    ).filter(RegistroGasto.estado == 'APROBADO')

    if tipo:
        menciones_tipo = [p.mencion for p in Programa.query.filter_by(tipo_programa=tipo).all()]
        query = query.filter(RegistroGasto.mencion.in_(menciones_tipo))
    if facs:
        query = query.filter(RegistroGasto.facultad.in_(facs))
    if ments:
        query = query.filter(RegistroGasto.mencion.in_(ments))

    rows = query.group_by(RegistroGasto.descripcion).all()
    return jsonify([{'desc': r.descripcion, 'total': round(r.total, 2)} for r in rows])


@analytics.route('/api/analytics/filtros')
@login_required
def api_filtros():
    tipo = request.args.get('tipo', '')
    q = Programa.query
    if tipo:
        q = q.filter_by(tipo_programa=tipo)
    programas = q.order_by(Programa.facultad, Programa.mencion).all()

    facultades = sorted(list({p.facultad for p in programas}))
    menciones  = [{'mencion': p.mencion, 'facultad': p.facultad} for p in programas]
    return jsonify({'facultades': facultades, 'menciones': menciones})


# ── API Notificaciones ────────────────────────────────────────────────────────

@analytics.route('/api/notificaciones')
@login_required
def api_notificaciones():
    notifs = Notificacion.query.filter(
        Notificacion.destinatario_rol.in_([current_user.rol, 'todos']),
        Notificacion.leida == False
    ).order_by(Notificacion.fecha.desc()).limit(20).all()
    return jsonify([n.to_dict() for n in notifs])


@analytics.route('/api/notificaciones/marcar_leida/<int:nid>', methods=['POST'])
@login_required
def marcar_leida(nid):
    n = Notificacion.query.get_or_404(nid)
    n.leida = True
    db.session.commit()
    return jsonify({'ok': True})


@analytics.route('/api/notificaciones/marcar_todas', methods=['POST'])
@login_required
def marcar_todas():
    Notificacion.query.filter(
        Notificacion.destinatario_rol.in_([current_user.rol, 'todos']),
        Notificacion.leida == False
    ).update({'leida': True})
    db.session.commit()
    return jsonify({'ok': True})


# ── Helper ─────────────────────────────────────────────────────────────────────

def _filtrar(tipo, facs, ments):
    q = Programa.query
    if tipo:
        q = q.filter_by(tipo_programa=tipo)
    if facs:
        q = q.filter(Programa.facultad.in_(facs))
    if ments:
        q = q.filter(Programa.mencion.in_(ments))
    return q.all()
