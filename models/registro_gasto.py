from extensions import db
from datetime import datetime


class RegistroGasto(db.Model):
    __tablename__ = 'registros_gastos'

    id = db.Column(db.Integer, primary_key=True)
    mes = db.Column(db.String(20), nullable=False)
    anio = db.Column(db.Integer, nullable=False)
    facultad = db.Column(db.String(150), nullable=False)
    mencion = db.Column(db.String(300), db.ForeignKey('programas.mencion'), nullable=False)
    expediente = db.Column(db.String(100), nullable=False)
    oficio = db.Column(db.String(100), nullable=True)
    descripcion = db.Column(db.String(100), nullable=False)
    monto = db.Column(db.Float, nullable=False)
    estado = db.Column(db.String(20), nullable=False)  # APROBADO / SIN SALDO
    observacion = db.Column(db.String(300), nullable=True)
    condicion = db.Column(db.String(20), default='EN PROCESO')  # EN PROCESO / REALIZADO
    registrado_por = db.Column(db.String(50), nullable=False)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    validado_por = db.Column(db.String(50), nullable=True)
    fecha_validacion = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f'<RegistroGasto {self.expediente}>'
