"""
Modelo para gestionar entidades y su asociación con prestadores
"""
from extensions import db
from datetime import datetime


# Tabla intermedia para relación many-to-many entre usuarios (entidades) y prestadores
usuario_prestador = db.Table(
    'usuario_prestador',
    db.Column('usuario_id', db.Integer, db.ForeignKey('usuarios.usuario_id'), primary_key=True),
    db.Column('prestador_id', db.Integer, db.ForeignKey('prestadores.prestador_id'), primary_key=True),
    db.Column('fecha_asociacion', db.DateTime, default=datetime.utcnow, nullable=False),
    db.Column('puede_ver_ambulatorio', db.Boolean, default=True, nullable=False),
    db.Column('puede_ver_internacion', db.Boolean, default=True, nullable=False),
    db.Index('idx_usuario_prestador', 'usuario_id', 'prestador_id')
)

