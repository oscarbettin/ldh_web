"""
Modelo de Prestador (Médico solicitante)
"""
from extensions import db
from datetime import datetime


class Prestador(db.Model):
    """Médicos solicitantes de estudios"""
    __tablename__ = 'prestadores'
    
    prestador_id = db.Column(db.Integer, primary_key=True)
    apellido = db.Column(db.String(100), nullable=False, index=True)
    nombre = db.Column(db.String(100), nullable=False)
    codigo = db.Column(db.String(20), unique=True)
    tipo_matricula = db.Column(db.String(10))
    numero_matricula = db.Column(db.String(20), index=True)
    fecha_matricula = db.Column(db.Date)
    especialidad_id = db.Column(db.Integer, db.ForeignKey('especialidades.especialidad_id'))
    especialidad_otra = db.Column(db.String(100))  # Para especialidades no listadas
    tipo_documento = db.Column(db.String(10))
    numero_documento = db.Column(db.String(20))
    cuit = db.Column(db.String(13))
    direccion = db.Column(db.String(200))
    codigo_postal = db.Column(db.String(10))
    localidad = db.Column(db.String(100))
    provincia = db.Column(db.String(50))
    telefono = db.Column(db.String(20))
    email = db.Column(db.String(100))
    activo = db.Column(db.Boolean, default=True, nullable=False)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relaciones
    especialidad = db.relationship('Especialidad', backref='prestadores')
    protocolos = db.relationship('Protocolo', backref='prestador')
    
    @property
    def nombre_completo(self):
        """Devuelve apellido y nombre"""
        return f"{self.apellido}, {self.nombre}"
    
    @property
    def nombre_especialidad(self):
        """Devuelve la especialidad (de la tabla o la otra)"""
        if self.especialidad:
            return self.especialidad.nombre
        return self.especialidad_otra if self.especialidad_otra else "Sin especialidad"
    
    @property
    def nombre_con_matricula(self):
        """Devuelve nombre con matrícula para mostrar en selects"""
        if self.numero_matricula:
            return f"{self.nombre_completo} (Mat. {self.numero_matricula})"
        return self.nombre_completo
    
    def __repr__(self):
        return f'<Prestador {self.nombre_completo}>'


class Especialidad(db.Model):
    """Especialidades médicas"""
    __tablename__ = 'especialidades'
    
    especialidad_id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False, index=True)
    activo = db.Column(db.Boolean, default=True, nullable=False)
    
    def __repr__(self):
        return f'<Especialidad {self.nombre}>'

