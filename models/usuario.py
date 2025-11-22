"""
Modelos relacionados con usuarios, roles y permisos
"""
from extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


class Usuario(UserMixin, db.Model):
    """Usuario del sistema"""
    __tablename__ = 'usuarios'
    
    usuario_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    nombre_completo = db.Column(db.String(100), nullable=False)
    telefono = db.Column(db.String(20))
    matricula_tipo = db.Column(db.String(10))
    matricula_numero = db.Column(db.String(30))
    especialidad = db.Column(db.String(120))
    prestador_id = db.Column(db.Integer, db.ForeignKey('prestadores.prestador_id'))
    activo = db.Column(db.Boolean, default=True, nullable=False)
    rol_id = db.Column(db.Integer, db.ForeignKey('roles.rol_id'), nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ultimo_acceso = db.Column(db.DateTime)
    
    # Relaciones
    rol = db.relationship('Rol', backref='usuarios')
    protocolos_ingresados = db.relationship('Protocolo', foreign_keys='Protocolo.usuario_ingreso_id', backref='usuario_ingreso')
    protocolos_informados = db.relationship('Protocolo', foreign_keys='Protocolo.usuario_informe_id', backref='usuario_informe')
    firma = db.relationship('UsuarioFirma', uselist=False, backref='usuario', cascade='all, delete-orphan')
    prestador = db.relationship('Prestador', backref='usuarios')
    auditorias = db.relationship('Auditoria', backref='usuario')
    
    # Flask-Login requiere get_id()
    def get_id(self):
        return str(self.usuario_id)
    
    def set_password(self, password):
        """Establece la contraseña hasheada"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verifica la contraseña"""
        return check_password_hash(self.password_hash, password)
    
    def tiene_permiso(self, codigo_permiso):
        """Verifica si el usuario tiene un permiso específico"""
        # OSCAR y Administrador tienen todos los permisos
        if self.rol.nombre in ['OSCAR', 'Administrador']:
            return True
        
        # Verificar si el rol tiene el permiso
        for permiso in self.rol.permisos:
            if permiso.codigo == codigo_permiso:
                return True
        return False
    
    @property
    def matricula_completa(self):
        """Retorna matrícula formateada con tipo y número."""
        if self.matricula_numero:
            tipo = (self.matricula_tipo or '').strip()
            numero = self.matricula_numero.strip()
            return f"{tipo} {numero}".strip()
        return ''
    
    def __repr__(self):
        return f'<Usuario {self.username}>'


class Rol(db.Model):
    """Roles de usuario"""
    __tablename__ = 'roles'
    
    rol_id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False, index=True)
    descripcion = db.Column(db.Text)
    oculto = db.Column(db.Boolean, default=False, nullable=False)
    
    # Relación muchos a muchos con Permiso
    permisos = db.relationship('Permiso', secondary='roles_permisos', backref='roles')
    
    def __repr__(self):
        return f'<Rol {self.nombre}>'


class Permiso(db.Model):
    """Permisos del sistema"""
    __tablename__ = 'permisos'
    
    permiso_id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), unique=True, nullable=False, index=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    modulo = db.Column(db.String(50))
    
    def __repr__(self):
        return f'<Permiso {self.codigo}>'


class RolPermiso(db.Model):
    """Tabla intermedia roles-permisos"""
    __tablename__ = 'roles_permisos'
    
    rol_permiso_id = db.Column(db.Integer, primary_key=True)
    rol_id = db.Column(db.Integer, db.ForeignKey('roles.rol_id'), nullable=False)
    permiso_id = db.Column(db.Integer, db.ForeignKey('permisos.permiso_id'), nullable=False)
    
    # Índice único para evitar duplicados
    __table_args__ = (
        db.UniqueConstraint('rol_id', 'permiso_id', name='uq_rol_permiso'),
    )


class UsuarioFirma(db.Model):
    """Firmas digitales de los usuarios médicos"""
    __tablename__ = 'usuario_firmas'

    usuario_firma_id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.usuario_id'), nullable=False, unique=True, index=True)
    archivo = db.Column(db.String(255), nullable=False)
    fecha_subida = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<UsuarioFirma usuario_id={self.usuario_id}>'

