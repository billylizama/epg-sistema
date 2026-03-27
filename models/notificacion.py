from extensions import db
from datetime import datetime


class Notificacion(db.Model):
    __tablename__ = 'notificaciones'

    id = db.Column(db.Integer, primary_key=True)
    destinatario_rol = db.Column(db.String(20), nullable=False)  # tesorera, admin, todos
    tipo = db.Column(db.String(30), nullable=False)              # CRITICO, SOBREPASADO
    titulo = db.Column(db.String(200), nullable=False)
    mensaje = db.Column(db.String(500), nullable=False)
    mencion = db.Column(db.String(300), nullable=True)
    leida = db.Column(db.Boolean, default=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'tipo': self.tipo,
            'titulo': self.titulo,
            'mensaje': self.mensaje,
            'mencion': self.mencion,
            'leida': self.leida,
            'fecha': self.fecha.strftime('%d/%m/%Y %H:%M')
        }
