"""
Modelo de Paciente (Afiliado)
"""
from extensions import db
from datetime import datetime


class Afiliado(db.Model):
    """Pacientes del laboratorio"""
    __tablename__ = 'afiliados'
    
    afiliado_id = db.Column(db.Integer, primary_key=True)
    apellido = db.Column(db.String(100), nullable=False, index=True)
    nombre = db.Column(db.String(100), nullable=False)
    obra_social_id = db.Column(db.Integer, db.ForeignKey('obras_sociales.obra_social_id'))
    numero_afiliado = db.Column(db.String(50))
    tipo_documento = db.Column(db.String(10))
    numero_documento = db.Column(db.String(20), index=True)
    fecha_nacimiento = db.Column(db.Date)
    codigo_postal = db.Column(db.String(10))
    localidad = db.Column(db.String(100))
    telefono = db.Column(db.String(20))
    email = db.Column(db.String(100))
    observaciones = db.Column(db.Text)
    activo = db.Column(db.Boolean, default=True, nullable=False)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ultima_modificacion = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    # Relaciones
    obra_social = db.relationship('ObraSocial', backref='afiliados')
    protocolos = db.relationship('Protocolo', backref='afiliado')
    
    @property
    def nombre_completo(self):
        """Devuelve apellido y nombre"""
        return f"{self.apellido}, {self.nombre}"
    
    @property
    def edad(self):
        """Calcula la edad actual del paciente basándose en la fecha de nacimiento"""
        if self.fecha_nacimiento:
            hoy = datetime.now().date()
            edad = hoy.year - self.fecha_nacimiento.year
            if (hoy.month, hoy.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day):
                edad -= 1
            return edad
        return None
    
    @property
    def nombre_completo_con_documento(self):
        """Devuelve nombre completo con documento para mostrar en selects"""
        if self.tipo_documento and self.numero_documento:
            return f"{self.nombre_completo} ({self.tipo_documento} {self.numero_documento})"
        return self.nombre_completo
    
    def __repr__(self):
        return f'<Afiliado {self.nombre_completo}>'

