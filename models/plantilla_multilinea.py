"""
Modelo para plantillas multilinea mejoradas
"""
from extensions import db
from datetime import datetime

class PlantillaMultilinea(db.Model):
    """Plantillas que pueden contener múltiples líneas"""
    __tablename__ = 'plantillas_multilinea'
    
    plantilla_id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    
    # Configuración de la plantilla
    tipo_estudio = db.Column(db.String(20), nullable=False)  # PAP, BIOPSIA, etc.
    seccion = db.Column(db.String(50), nullable=False)  # Extendido, Células, etc.
    
    # Líneas que contiene esta plantilla
    lineas = db.Column(db.Text)  # JSON con array de lineas
    
    # Metadatos
    veces_usado = db.Column(db.Integer, default=0)
    activo = db.Column(db.Boolean, default=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    ultima_vez_usado = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<PlantillaMultilinea {self.nombre}: {self.tipo_estudio}>'


class CasoHistoricoCompleto(db.Model):
    """Casos históricos completos con múltiples secciones"""
    __tablename__ = 'casos_historicos_completos'
    
    caso_id = db.Column(db.Integer, primary_key=True)
    protocolo_original = db.Column(db.String(50))
    tipo_estudio = db.Column(db.String(20), nullable=False)
    
    # Información del paciente
    paciente_nombre = db.Column(db.String(200))
    paciente_edad = db.Column(db.Integer)
    paciente_sexo = db.Column(db.String(10))
    
    # Información médica
    prestador_nombre = db.Column(db.String(200))
    obra_social = db.Column(db.String(100))
    fecha_estudio = db.Column(db.Date)
    
    # Contenido del caso (JSON estructurado)
    contenido_completo = db.Column(db.Text)  # JSON con todas las secciones
    
    # Secciones individuales para búsqueda
    seccion_extendido = db.Column(db.Text)
    seccion_celulas = db.Column(db.Text)
    seccion_inflamatorio = db.Column(db.Text)
    seccion_flora = db.Column(db.Text)
    seccion_diagnostico = db.Column(db.Text)
    
    # Metadatos
    categoria = db.Column(db.String(100))
    subcategoria = db.Column(db.String(100))
    confianza_clasificacion = db.Column(db.Float, default=1.0)
    
    activo = db.Column(db.Boolean, default=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<CasoHistoricoCompleto {self.protocolo_original}: {self.tipo_estudio}>'


class SugerenciaInteligente(db.Model):
    """Sugerencias generadas por el asistente"""
    __tablename__ = 'sugerencias_inteligentes'
    
    sugerencia_id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.usuario_id'), nullable=False)
    protocolo_id = db.Column(db.Integer, db.ForeignKey('protocolos.protocolo_id'))
    
    # Contexto de la sugerencia
    seccion = db.Column(db.String(50), nullable=False)
    tipo_sugerencia = db.Column(db.String(50), nullable=False)  # plantilla, linea, diagnostico
    
    # Contenido de la sugerencia
    texto_sugerido = db.Column(db.Text, nullable=False)
    plantilla_id = db.Column(db.Integer, db.ForeignKey('plantillas_multilinea.plantilla_id'))
    
    # Metadatos de la sugerencia
    nivel_confianza = db.Column(db.Float, nullable=False)  # 0.0 a 1.0
    casos_base = db.Column(db.Integer, default=1)  # Cuántos casos respaldan la sugerencia
    razon_sugerencia = db.Column(db.Text)  # Explicación de por qué se sugiere
    
    # Estado de la sugerencia
    estado = db.Column(db.String(20), default='pendiente')  # pendiente, aceptada, rechazada
    feedback_usuario = db.Column(db.String(20))  # aceptada, rechazada, modificada
    
    # Metadatos
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    procesado_en = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<SugerenciaInteligente {self.seccion}: {self.nivel_confianza}>'
