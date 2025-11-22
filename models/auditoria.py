"""
Modelo de Auditoría
"""
from extensions import db
from datetime import datetime


class Auditoria(db.Model):
    """Registro de todas las operaciones importantes"""
    __tablename__ = 'auditoria'
    
    auditoria_id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.usuario_id'))
    accion = db.Column(db.String(50), nullable=False, index=True)
    tabla = db.Column(db.String(50))
    registro_id = db.Column(db.Integer)
    descripcion = db.Column(db.Text)
    ip_address = db.Column(db.String(50))
    fecha_hora = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Índice compuesto para búsquedas por usuario y fecha
    __table_args__ = (
        db.Index('idx_auditoria_usuario_fecha', 'usuario_id', 'fecha_hora'),
    )
    
    @staticmethod
    def registrar(usuario_id, accion, tabla=None, registro_id=None, descripcion=None, ip_address=None):
        """
        Registra una acción en la auditoría
        
        Args:
            usuario_id: ID del usuario que realiza la acción
            accion: Tipo de acción (LOGIN, CREAR, MODIFICAR, ELIMINAR, etc.)
            tabla: Nombre de la tabla afectada
            registro_id: ID del registro afectado
            descripcion: Descripción adicional
            ip_address: Dirección IP del usuario
        """
        auditoria = Auditoria(
            usuario_id=usuario_id,
            accion=accion,
            tabla=tabla,
            registro_id=registro_id,
            descripcion=descripcion,
            ip_address=ip_address
        )
        db.session.add(auditoria)
        db.session.commit()
    
    def __repr__(self):
        return f'<Auditoria {self.accion} - {self.fecha_hora}>'

