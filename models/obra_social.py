"""
Modelos de Obra Social y Planes de Facturación
"""
from extensions import db
from datetime import datetime


class ObraSocial(db.Model):
    """Obras sociales, prepagas y mutuales"""
    __tablename__ = 'obras_sociales'
    
    obra_social_id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), unique=True, nullable=False, index=True)
    nombre = db.Column(db.String(200), nullable=False, index=True)
    direccion = db.Column(db.String(200))
    localidad = db.Column(db.String(100))
    codigo_postal = db.Column(db.String(10))
    telefono = db.Column(db.String(50))
    codigo_inos = db.Column(db.String(20))
    plan_id = db.Column(db.Integer, db.ForeignKey('planes_facturacion.plan_facturacion_id'))
    activo = db.Column(db.Boolean, default=True, nullable=False)
    observaciones = db.Column(db.Text)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relaciones
    plan = db.relationship('PlanFacturacion', backref='obras_sociales')
    protocolos = db.relationship('Protocolo', backref='obra_social')
    
    @property
    def nombre_con_codigo(self):
        """Devuelve nombre con código para mostrar en selects"""
        return f"{self.nombre} ({self.codigo})"
    
    def __repr__(self):
        return f'<ObraSocial {self.nombre}>'


class PlanFacturacion(db.Model):
    """Planes de facturación con porcentajes"""
    __tablename__ = 'planes_facturacion'
    
    plan_facturacion_id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), unique=True, nullable=False, index=True)
    nombre = db.Column(db.String(200), nullable=False)
    porcentaje_base = db.Column(db.Numeric(5, 2), default=100.0)
    activo = db.Column(db.Boolean, default=True, nullable=False)
    observaciones = db.Column(db.Text)
    
    # Relaciones
    categorias = db.relationship('PlanCategoria', backref='plan', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<PlanFacturacion {self.nombre}>'


class PlanCategoria(db.Model):
    """Porcentajes por categoría en cada plan"""
    __tablename__ = 'planes_categorias'
    
    plan_categoria_id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('planes_facturacion.plan_facturacion_id'), nullable=False)
    categoria_codigo = db.Column(db.String(10), nullable=False)
    porcentaje = db.Column(db.Numeric(5, 2), nullable=False)
    
    # Índice único para evitar duplicados
    __table_args__ = (
        db.UniqueConstraint('plan_id', 'categoria_codigo', name='uq_plan_categoria'),
    )
    
    def __repr__(self):
        return f'<PlanCategoria {self.categoria_codigo}: {self.porcentaje}%>'

