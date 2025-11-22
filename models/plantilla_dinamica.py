"""
Modelo para plantillas dinámicas con secciones y líneas
"""
from extensions import db
from datetime import datetime

class SeccionPlantilla(db.Model):
    """Secciones de plantillas (Extendido, Células, etc.)"""
    __tablename__ = 'secciones_plantilla'
    
    seccion_id = db.Column(db.Integer, primary_key=True)
    tipo_estudio = db.Column(db.String(20), nullable=False)  # PAP, BIOPSIA, etc.
    codigo = db.Column(db.String(10), nullable=False)  # T1, H2, A3, etc.
    nombre = db.Column(db.String(100), nullable=False)  # "Extendido", "Células", etc.
    descripcion = db.Column(db.Text)
    orden = db.Column(db.Integer, default=0)
    activo = db.Column(db.Boolean, default=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    lineas = db.relationship('LineaPlantilla', backref='seccion', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<SeccionPlantilla {self.codigo}: {self.nombre}>'


class LineaPlantilla(db.Model):
    """Líneas individuales dentro de cada sección"""
    __tablename__ = 'lineas_plantilla'
    
    linea_id = db.Column(db.Integer, primary_key=True)
    seccion_id = db.Column(db.Integer, db.ForeignKey('secciones_plantilla.seccion_id'), nullable=False)
    texto = db.Column(db.Text, nullable=False)
    orden = db.Column(db.Integer, default=0)
    veces_usado = db.Column(db.Integer, default=0)
    activo = db.Column(db.Boolean, default=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    ultima_vez_usado = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<LineaPlantilla {self.linea_id}: {self.texto[:50]}...>'


class ConfiguracionBotones(db.Model):
    """Configuración de los botones (T1, H2, etc.)"""
    __tablename__ = 'configuracion_botones'
    
    config_id = db.Column(db.Integer, primary_key=True)
    tipo_estudio = db.Column(db.String(20), nullable=False)
    codigo_boton = db.Column(db.String(10), nullable=False)  # T1, H2, etc.
    numero_boton = db.Column(db.Integer, nullable=False)  # 1, 2, 3, etc.
    seccion_id = db.Column(db.Integer, db.ForeignKey('secciones_plantilla.seccion_id'))
    descripcion = db.Column(db.String(200))
    activo = db.Column(db.Boolean, default=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ConfiguracionBotones {self.codigo_boton}({self.numero_boton})>'


class PlantillaGenerada(db.Model):
    """Plantillas generadas por el usuario"""
    __tablename__ = 'plantillas_generadas'
    
    plantilla_id = db.Column(db.Integer, primary_key=True)
    protocolo_id = db.Column(db.Integer, db.ForeignKey('protocolos.protocolo_id'))
    tipo_estudio = db.Column(db.String(20), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.usuario_id'))
    nombre = db.Column(db.String(200))
    contenido = db.Column(db.Text)  # JSON con las selecciones
    activo = db.Column(db.Boolean, default=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    modificado_en = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<PlantillaGenerada {self.plantilla_id}: {self.nombre}>'
