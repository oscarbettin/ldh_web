"""
Modelo para configuración del asistente inteligente
"""
from extensions import db
from datetime import datetime

class ConfiguracionAsistenteUsuario(db.Model):
    """Configuración personal del asistente por usuario"""
    __tablename__ = 'configuracion_asistente_usuario'
    
    config_id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.usuario_id'), nullable=False)
    
    # Modo principal del asistente
    modo_principal = db.Column(db.String(20), default='sugeridor')  # silencioso, sugeridor, predictor, colaborador
    
    # Configuraciones específicas
    frecuencia_sugerencias = db.Column(db.String(20), default='siempre')  # siempre, casos_complejos, nunca
    detectar_atipicos = db.Column(db.Boolean, default=True)
    sugerir_diagnosticos = db.Column(db.Boolean, default=True)
    validar_coherencia = db.Column(db.Boolean, default=False)
    
    # Tipos de estudio habilitados
    habilitar_pap = db.Column(db.Boolean, default=True)
    habilitar_biopsias = db.Column(db.Boolean, default=True)
    habilitar_citologia = db.Column(db.Boolean, default=False)
    
    # Configuraciones avanzadas
    nivel_confianza_minimo = db.Column(db.Float, default=0.7)  # 0.0 a 1.0
    max_sugerencias_por_seccion = db.Column(db.Integer, default=5)
    mostrar_estadisticas = db.Column(db.Boolean, default=True)
    
    # Metadatos
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    modificado_en = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<ConfiguracionAsistente {self.usuario_id}: {self.modo_principal}>'


class PerfilAsistente(db.Model):
    """Perfiles predefinidos del asistente"""
    __tablename__ = 'perfiles_asistente'
    
    perfil_id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)
    descripcion = db.Column(db.Text)
    
    # Configuración del perfil
    modo_principal = db.Column(db.String(20), nullable=False)
    frecuencia_sugerencias = db.Column(db.String(20), nullable=False)
    detectar_atipicos = db.Column(db.Boolean, default=False)
    sugerir_diagnosticos = db.Column(db.Boolean, default=False)
    validar_coherencia = db.Column(db.Boolean, default=False)
    
    # Tipos de estudio
    habilitar_pap = db.Column(db.Boolean, default=True)
    habilitar_biopsias = db.Column(db.Boolean, default=True)
    habilitar_citologia = db.Column(db.Boolean, default=True)
    
    # Configuraciones avanzadas
    nivel_confianza_minimo = db.Column(db.Float, default=0.7)
    max_sugerencias_por_seccion = db.Column(db.Integer, default=5)
    mostrar_estadisticas = db.Column(db.Boolean, default=True)
    
    # Metadatos
    activo = db.Column(db.Boolean, default=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<PerfilAsistente {self.nombre}: {self.modo_principal}>'


class ConfiguracionAsistenteGlobal(db.Model):
    """Configuraciones globales del sistema de asistente"""
    __tablename__ = 'configuracion_asistente_global'
    
    config_id = db.Column(db.Integer, primary_key=True)
    
    # Configuraciones del sistema
    auto_deteccion_contexto = db.Column(db.Boolean, default=True)
    aprendizaje_continuo = db.Column(db.Boolean, default=True)
    cache_sugerencias = db.Column(db.Boolean, default=True)
    
    # Límites del sistema
    max_casos_analisis = db.Column(db.Integer, default=1000)
    timeout_busqueda_ms = db.Column(db.Integer, default=3000)
    cache_ttl_horas = db.Column(db.Integer, default=24)
    
    # Configuraciones de IA (para futura integración con Claude)
    api_claude_habilitada = db.Column(db.Boolean, default=False)
    api_claude_key = db.Column(db.String(100))  # Encriptado
    modelo_claude = db.Column(db.String(50), default='claude-3-haiku-20240307')
    
    # Metadatos
    modificado_en = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<ConfiguracionAsistenteGlobal>'


class LogUsoAsistente(db.Model):
    """Log de uso del asistente para aprendizaje"""
    __tablename__ = 'log_uso_asistente'
    
    log_id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.usuario_id'), nullable=False)
    protocolo_id = db.Column(db.Integer, db.ForeignKey('protocolos.protocolo_id'))
    
    # Contexto de la interacción
    seccion = db.Column(db.String(50))  # Extendido, Células, etc.
    modo_asistente = db.Column(db.String(20))
    
    # Sugerencias mostradas
    sugerencias_mostradas = db.Column(db.Text)  # JSON
    sugerencias_aceptadas = db.Column(db.Text)  # JSON
    sugerencias_rechazadas = db.Column(db.Text)  # JSON
    
    # Resultado de la interacción
    tiempo_interaccion_segundos = db.Column(db.Integer)
    satisfaccion_usuario = db.Column(db.Integer)  # 1-5 estrellas
    comentarios = db.Column(db.Text)
    
    # Metadatos
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<LogUsoAsistente {self.usuario_id}: {self.seccion}>'
