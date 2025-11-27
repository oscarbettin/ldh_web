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
    es_entidad = db.Column(db.Boolean, default=False, nullable=False, index=True)  # True si es hospital/sanatorio/clínica
    puede_ver_ambulatorio = db.Column(db.Boolean, default=True, nullable=False)  # Puede ver protocolos ambulatorios
    puede_ver_internacion = db.Column(db.Boolean, default=True, nullable=False)  # Puede ver protocolos de internación
    
    # Campos de notificaciones
    notificar_email = db.Column(db.Boolean, default=False, nullable=False)  # Notificar por email cuando se complete un protocolo
    notificar_whatsapp = db.Column(db.Boolean, default=False, nullable=False)  # Notificar por WhatsApp cuando se complete un protocolo
    notificar_ambulatorio = db.Column(db.Boolean, default=False, nullable=False)  # Recibir notificaciones de protocolos ambulatorios
    notificar_internacion = db.Column(db.Boolean, default=False, nullable=False)  # Recibir notificaciones de protocolos de internación
    whatsapp = db.Column(db.String(20))  # Número de WhatsApp para notificaciones
    
    # Relaciones
    especialidad = db.relationship('Especialidad', backref='prestadores')
    protocolos = db.relationship('Protocolo', foreign_keys='Protocolo.prestador_id', backref='prestador')
    # Relación many-to-many: prestadores profesionales asociados a esta entidad
    # NOTA: backref cambiado a 'entidades_legacy' para evitar conflicto con Usuario.prestadores_asociados
    prestadores_asociados = db.relationship(
        'Prestador',
        secondary='prestador_entidad',
        primaryjoin='Prestador.prestador_id == prestador_entidad.c.entidad_id',
        secondaryjoin='Prestador.prestador_id == prestador_entidad.c.prestador_id',
        backref=db.backref('entidades_legacy', lazy='dynamic'),
        lazy='dynamic'
    )
    
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


# Tabla intermedia para relación many-to-many entre entidades y prestadores
prestador_entidad = db.Table(
    'prestador_entidad',
    db.Column('entidad_id', db.Integer, db.ForeignKey('prestadores.prestador_id'), primary_key=True),
    db.Column('prestador_id', db.Integer, db.ForeignKey('prestadores.prestador_id'), primary_key=True),
    db.Column('fecha_asociacion', db.DateTime, default=datetime.utcnow, nullable=False),
    db.Index('idx_prestador_entidad', 'entidad_id', 'prestador_id')
)


class Especialidad(db.Model):
    """Especialidades médicas"""
    __tablename__ = 'especialidades'
    
    especialidad_id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False, index=True)
    activo = db.Column(db.Boolean, default=True, nullable=False)
    
    def __repr__(self):
        return f'<Especialidad {self.nombre}>'

