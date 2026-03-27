from extensions import db
from datetime import datetime


class Programa(db.Model):
    __tablename__ = 'programas'

    id = db.Column(db.Integer, primary_key=True)
    tipo_programa = db.Column(db.String(20), nullable=False)  # MAESTRIA/DOCTORADO/EPG
    facultad = db.Column(db.String(150), nullable=False)
    mencion = db.Column(db.String(300), unique=True, nullable=False)
    ingresos = db.Column(db.Float, default=0.0)

    registros = db.relationship('RegistroGasto', backref='programa_obj', lazy=True)
    historial = db.relationship('HistorialIngreso', backref='programa_obj', lazy=True)

    @property
    def gastos_total(self):
        from models.registro_gasto import RegistroGasto
        total = db.session.query(db.func.sum(RegistroGasto.monto)).filter(
            RegistroGasto.mencion == self.mencion,
            RegistroGasto.estado == 'APROBADO'
        ).scalar()
        return total or 0.0

    @property
    def retencion_ocep(self):
        return self.ingresos * 0.10

    @property
    def es_epg(self):
        return self.mencion == 'ESCUELA DE POST GRADO'

    @property
    def retencion_epg(self):
        # EPG especial: recauda el 5% de TODOS los programas (incluyendose)
        # Para los demas: pagan el 5% de sus propios ingresos a EPG
        if self.es_epg:
            total = db.session.query(db.func.sum(Programa.ingresos)).scalar()
            return (total or 0.0) * 0.05
        return self.ingresos * 0.05

    @property
    def saldo_actual(self):
        if self.es_epg:
            # EPG: SALDO = INGRESOS + RET_EPG - GASTOS - RET_OCEP
            # La RET_EPG se suma porque EPG la RECAUDA (es ingreso para EPG)
            return self.ingresos + self.retencion_epg - self.gastos_total - self.retencion_ocep
        # Otros programas: SALDO = INGRESOS - GASTOS - RET_OCEP - RET_EPG
        return self.ingresos - self.gastos_total - self.retencion_ocep - self.retencion_epg

    @property
    def situacion(self):
        saldo = self.saldo_actual
        # Base para calcular el 15%: para EPG usamos ingresos + ret_epg, para otros ingresos
        base = (self.ingresos + self.retencion_epg) if self.es_epg else self.ingresos
        if base == 0:
            return 'EN EL LIMITE' if saldo == 0 else ('SOBREPASADO' if saldo < 0 else 'BIEN')
        if saldo < 0:
            return 'SOBREPASADO'
        elif saldo == 0:
            return 'EN EL LIMITE'
        elif saldo <= base * 0.15:
            return 'CRITICO'
        else:
            return 'BIEN'

    def __repr__(self):
        return f'<Programa {self.mencion}>'


class HistorialIngreso(db.Model):
    __tablename__ = 'historial_ingresos'

    id = db.Column(db.Integer, primary_key=True)
    programa_id = db.Column(db.Integer, db.ForeignKey('programas.id'), nullable=False)
    monto_anterior = db.Column(db.Float, nullable=False)
    monto_nuevo = db.Column(db.Float, nullable=False)
    modificado_por = db.Column(db.String(50), nullable=False)
    fecha_modificacion = db.Column(db.DateTime, default=datetime.utcnow)
