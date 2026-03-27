from flask import Flask
from config import Config
from extensions import db, login_manager
import os


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    # Registrar blueprints
    from routes.auth import auth
    from routes.tesorera import tesorera
    from routes.operador import operador
    from routes.admin import admin_bp
    from routes.analytics import analytics

    app.register_blueprint(auth)
    app.register_blueprint(tesorera)
    app.register_blueprint(operador)
    app.register_blueprint(admin_bp)
    app.register_blueprint(analytics)

    # Filtro de formato moneda
    @app.template_filter('format_sol')
    def format_sol(value):
        try:
            return 'S/ {:,.2f}'.format(float(value))
        except (ValueError, TypeError):
            return 'S/ 0.00'

    # Context processor: navbar badges
    @app.context_processor
    def inject_globales():
        from flask_login import current_user
        ctx = {'pendientes_docente_nav': 0, 'notif_count': 0}
        if current_user.is_authenticated:
            from models.registro_gasto import RegistroGasto
            from models.notificacion import Notificacion
            if current_user.rol == 'admin':
                ctx['pendientes_docente_nav'] = RegistroGasto.query.filter_by(
                    descripcion='PLANILLA DOCENTE INVITADO', condicion='EN PROCESO'
                ).count()
            ctx['notif_count'] = Notificacion.query.filter(
                Notificacion.destinatario_rol.in_([current_user.rol, 'todos']),
                Notificacion.leida == False
            ).count()
        return ctx

    # Crear directorios necesarios
    os.makedirs(os.path.join(os.path.dirname(__file__), 'database'), exist_ok=True)
    os.makedirs(Config.BACKUP_DIR, exist_ok=True)

    with app.app_context():
        db.create_all()

    _setup_backup(app)
    _setup_notificaciones(app)

    return app


def _setup_backup(app):
    import threading, time, shutil

    def backup_loop():
        while True:
            time.sleep(86400)
            with app.app_context():
                try:
                    from datetime import datetime
                    src = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
                    backup_dir = Config.BACKUP_DIR
                    os.makedirs(backup_dir, exist_ok=True)
                    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                    dst = os.path.join(backup_dir, f'epg_{ts}.db')
                    if os.path.exists(src):
                        shutil.copy2(src, dst)
                        backups = sorted([
                            os.path.join(backup_dir, f)
                            for f in os.listdir(backup_dir) if f.endswith('.db')
                        ])
                        for old in backups[:-30]:
                            os.remove(old)
                except Exception as e:
                    print(f'[Backup] Error: {e}')

    threading.Thread(target=backup_loop, daemon=True).start()


def _setup_notificaciones(app):
    """Verifica cada 5 minutos programas en estado critico/sobrepasado y genera notificaciones."""
    import threading, time

    def notif_loop():
        # Esperar 10s al arrancar para que la BD este lista
        time.sleep(10)
        while True:
            with app.app_context():
                try:
                    _verificar_presupuesto()
                except Exception as e:
                    print(f'[Notif] Error: {e}')
            time.sleep(300)  # cada 5 minutos

    threading.Thread(target=notif_loop, daemon=True).start()


def _verificar_presupuesto():
    from models.programa import Programa
    from models.notificacion import Notificacion
    from datetime import datetime, timedelta

    programas = Programa.query.all()
    hace_1h = datetime.utcnow() - timedelta(hours=1)

    for p in programas:
        sit = p.situacion
        if sit not in ('CRITICO', 'SOBREPASADO'):
            continue

        # No repetir la misma notificacion en menos de 1 hora
        ya_existe = Notificacion.query.filter(
            Notificacion.mencion == p.mencion,
            Notificacion.tipo == sit,
            Notificacion.fecha >= hace_1h
        ).first()
        if ya_existe:
            continue

        if sit == 'SOBREPASADO':
            titulo = f'SOBREPASADO: {p.mencion[:60]}'
            msg = (f'El programa "{p.mencion[:80]}" tiene saldo NEGATIVO de '
                   f'S/ {abs(p.saldo_actual):,.2f}. Se han gastado mas fondos de los disponibles.')
        else:
            pct = round(p.saldo_actual / (p.ingresos or 1) * 100, 1)
            titulo = f'CRITICO: {p.mencion[:60]}'
            msg = (f'El programa "{p.mencion[:80]}" tiene solo S/ {p.saldo_actual:,.2f} '
                   f'disponible ({pct}% del presupuesto). Se recomienda aumentar ingresos.')

        # Notificar a tesorera y admin
        for rol in ('tesorera', 'admin'):
            n = Notificacion(
                destinatario_rol=rol,
                tipo=sit,
                titulo=titulo,
                mensaje=msg,
                mencion=p.mencion
            )
            db.session.add(n)

    db.session.commit()


if __name__ == '__main__':
    from config import Config
    app = create_app()
    app.run(debug=True, host='localhost', port=5000)
