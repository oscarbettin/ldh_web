"""
Modelos para el Asistente IA
"""
from extensions import db
from datetime import datetime


class CasoHistorico(db.Model):
    """Casos históricos completos para aprendizaje del asistente"""
    __tablename__ = 'casos_historicos'
    
    caso_id = db.Column(db.Integer, primary_key=True)
    tipo_estudio = db.Column(db.String(20), nullable=False, index=True)  # BIOPSIA, CITOLOGIA, PAP
    protocolo_original = db.Column(db.String(50), index=True)  # Número de protocolo original
    
    # Datos clínicos
    datos_clinicos = db.Column(db.Text)
    
    # Descripción macroscópica (biopsias)
    descripcion_macroscopica = db.Column(db.Text)
    
    # Descripción microscópica (biopsias)
    descripcion_microscopica = db.Column(db.Text)
    
    # Descripción general (citologías)
    descripcion = db.Column(db.Text)
    
    # Diagnóstico final
    diagnostico = db.Column(db.Text, nullable=False)
    
    # Metadatos
    fecha_original = db.Column(db.Date)
    importado_en = db.Column(db.DateTime, default=datetime.utcnow)
    activo = db.Column(db.Boolean, default=True)
    
    # Para búsqueda y análisis
    palabras_clave = db.Column(db.Text)  # JSON con palabras clave extraídas
    categoria = db.Column(db.String(100))  # Categoría del diagnóstico
    
    __table_args__ = (
        db.Index('idx_caso_tipo_categoria', 'tipo_estudio', 'categoria'),
    )
    
    def __repr__(self):
        return f'<CasoHistorico {self.protocolo_original} - {self.tipo_estudio}>'


class PlantillaTexto(db.Model):
    """Plantillas de texto reutilizables"""
    __tablename__ = 'plantillas_texto'
    
    plantilla_id = db.Column(db.Integer, primary_key=True)
    tipo_estudio = db.Column(db.String(20), nullable=False, index=True)
    seccion = db.Column(db.String(50), nullable=False, index=True)  # EXTENDIDO, CELULAS, FLORA, DIAGNOSTICO, etc.
    
    nombre = db.Column(db.String(200))
    texto = db.Column(db.Text, nullable=False)
    
    # Estadísticas de uso
    veces_usado = db.Column(db.Integer, default=1)
    ultima_vez_usado = db.Column(db.DateTime)
    
    # Organización
    categoria = db.Column(db.String(100))
    orden = db.Column(db.Integer, default=0)
    activo = db.Column(db.Boolean, default=True)
    
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.Index('idx_plantilla_tipo_seccion', 'tipo_estudio', 'seccion'),
    )
    
    def __repr__(self):
        return f'<PlantillaTexto {self.nombre}>'


class FragmentoTexto(db.Model):
    """Fragmentos de texto comunes para autocompletar"""
    __tablename__ = 'fragmentos_texto'
    
    fragmento_id = db.Column(db.Integer, primary_key=True)
    tipo_estudio = db.Column(db.String(20), nullable=False, index=True)
    contexto = db.Column(db.String(100))  # En qué contexto aparece
    
    texto = db.Column(db.String(500), nullable=False)
    frecuencia = db.Column(db.Integer, default=1)
    
    activo = db.Column(db.Boolean, default=True)
    
    __table_args__ = (
        db.Index('idx_fragmento_tipo_contexto', 'tipo_estudio', 'contexto'),
    )
    
    def __repr__(self):
        return f'<FragmentoTexto {self.texto[:50]}...>'


class SugerenciaIA(db.Model):
    """Registro de sugerencias del asistente IA"""
    __tablename__ = 'sugerencias_ia'
    
    sugerencia_id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.usuario_id'))
    protocolo_id = db.Column(db.Integer, db.ForeignKey('protocolos.protocolo_id'))
    
    tipo_sugerencia = db.Column(db.String(50))  # DESCRIPCION, DIAGNOSTICO, PLANTILLA
    seccion = db.Column(db.String(50))
    
    texto_original = db.Column(db.Text)  # Lo que escribió el usuario
    texto_sugerido = db.Column(db.Text)  # Lo que sugirió la IA
    texto_final = db.Column(db.Text)  # Lo que finalmente usó el usuario
    
    aceptada = db.Column(db.Boolean)  # Si el usuario aceptó la sugerencia
    fecha_hora = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Para mejorar el sistema
    feedback_usuario = db.Column(db.String(20))  # UTIL, NO_UTIL, PARCIAL
    
    def __repr__(self):
        return f'<SugerenciaIA {self.tipo_sugerencia} - {"Aceptada" if self.aceptada else "Rechazada"}>'


class ConfiguracionAsistente(db.Model):
    """Configuración del asistente IA"""
    __tablename__ = 'configuracion_asistente'
    
    config_id = db.Column(db.Integer, primary_key=True)
    clave = db.Column(db.String(100), unique=True, nullable=False)
    valor = db.Column(db.Text)
    descripcion = db.Column(db.String(500))
    tipo_dato = db.Column(db.String(20))  # STRING, INTEGER, BOOLEAN, JSON
    
    fecha_modificacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<ConfigAsistente {self.clave}>'

