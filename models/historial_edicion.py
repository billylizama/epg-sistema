from extensions import db
from datetime import datetime


class HistorialEdicion(db.Model):
    __tablename__ = 'historial_ediciones'

    id = db.Column(db.Integer, primary_key=True)
    registro_id = db.Column(db.Integer, nullable=False)
    editado_por = db.Column(db.String(50), nullable=False)
    rol = db.Column(db.String(20), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    campo = db.Column(db.String(50), nullable=False)
    valor_anterior = db.Column(db.String(300))
    valor_nuevo = db.Column(db.String(300))
    expediente = db.Column(db.String(100))

    def __repr__(self):
        return f'<HistorialEdicion reg={self.registro_id} {self.campo}>'
