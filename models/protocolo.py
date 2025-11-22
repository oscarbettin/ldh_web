"""
Modelo de Protocolo (tabla central de estudios)
"""
from extensions import db
from datetime import datetime


class Protocolo(db.Model):
    """Tabla central de todos los estudios"""
    __tablename__ = 'protocolos'
    
    protocolo_id = db.Column(db.Integer, primary_key=True)
    numero_protocolo = db.Column(db.String(20), unique=True, nullable=False, index=True)
    tipo_estudio = db.Column(db.String(20), nullable=False, index=True)  # BIOPSIA, CITOLOGIA, PAP
    afiliado_id = db.Column(db.Integer, db.ForeignKey('afiliados.afiliado_id'), nullable=False, index=True)
    prestador_id = db.Column(db.Integer, db.ForeignKey('prestadores.prestador_id'), index=True)
    obra_social_id = db.Column(db.Integer, db.ForeignKey('obras_sociales.obra_social_id'), index=True)
    # Campos para registrar el estado de OS al momento del protocolo
    obra_social_nombre = db.Column(db.String(100))  # Nombre de OS al momento del protocolo
    obra_social_codigo = db.Column(db.String(20))    # Código de OS al momento del protocolo
    obra_social_activa = db.Column(db.Boolean, default=True)  # Estado de OS al momento del protocolo
    tipo_analisis_id = db.Column(db.Integer, db.ForeignKey('tipos_analisis.tipo_analisis_id'))
    fecha_ingreso = db.Column(db.Date, nullable=False, index=True)
    fecha_informe = db.Column(db.Date)
    datos_clinicos = db.Column(db.Text)
    estado = db.Column(db.String(20), default='EN_PROCESO', nullable=False, index=True)
    usuario_ingreso_id = db.Column(db.Integer, db.ForeignKey('usuarios.usuario_id'))
    usuario_informe_id = db.Column(db.Integer, db.ForeignKey('usuarios.usuario_id'))
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ultima_modificacion = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    # Relaciones
    tipo_analisis = db.relationship('TipoAnalisis', backref='protocolos')
    informe_biopsia = db.relationship('BiopsiaInforme', uselist=False, backref='protocolo')
    informe_citologia = db.relationship('CitologiaInforme', uselist=False, backref='protocolo')
    informe_pap = db.relationship('PapInforme', uselist=False, backref='protocolo')
    
    # Índice compuesto para búsquedas comunes
    __table_args__ = (
        db.Index('idx_protocolo_busqueda', 'tipo_estudio', 'estado', 'fecha_ingreso'),
    )
    
    @staticmethod
    def generar_numero_protocolo(tipo_estudio, año=None):
        """
        Genera el siguiente número de protocolo disponible
        
        Args:
            tipo_estudio: BIOPSIA, CITOLOGIA o PAP
            año: Año del protocolo (por defecto el año actual)
        
        Returns:
            String con el número de protocolo (ej: "B-25-0001")
        """
        if año is None:
            año = datetime.now().year
        
        # Prefijo según tipo
        prefijos = {
            'BIOPSIA': 'B',
            'CITOLOGIA': 'C',
            'PAP': 'P'
        }
        prefijo = prefijos.get(tipo_estudio, 'X')
        
        # Buscar el último número del año
        ultimo = Protocolo.query.filter(
            Protocolo.numero_protocolo.like(f'{prefijo}-{año%100:02d}-%')
        ).order_by(Protocolo.numero_protocolo.desc()).first()
        
        if ultimo:
            # Extraer el número del protocolo
            partes = ultimo.numero_protocolo.split('-')
            ultimo_num = int(partes[2])
            siguiente_num = ultimo_num + 1
        else:
            siguiente_num = 1
        
        # Formato: B-25-0001
        return f"{prefijo}-{año%100:02d}-{siguiente_num:04d}"
    
    def get_informe(self):
        """Devuelve el informe asociado según el tipo de estudio"""
        if self.tipo_estudio == 'BIOPSIA':
            return self.informe_biopsia
        elif self.tipo_estudio == 'CITOLOGIA':
            return self.informe_citologia
        elif self.tipo_estudio == 'PAP':
            return self.informe_pap
        return None
    
    @property
    def dias_pendiente(self):
        """Calcula los días que lleva pendiente el estudio"""
        if self.estado == 'PENDIENTE' or self.estado == 'EN_PROCESO':
            hoy = datetime.now().date()
            delta = hoy - self.fecha_ingreso
            return delta.days
        return 0
    
    def __repr__(self):
        return f'<Protocolo {self.numero_protocolo}>'


class TipoAnalisis(db.Model):
    """Tipos de análisis disponibles"""
    __tablename__ = 'tipos_analisis'
    
    tipo_analisis_id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), unique=True, nullable=False, index=True)
    nombre = db.Column(db.String(100), nullable=False)
    categoria = db.Column(db.String(50))  # BIOPSIA, CITOLOGIA, PAP
    activo = db.Column(db.Boolean, default=True, nullable=False)
    
    def __repr__(self):
        return f'<TipoAnalisis {self.nombre}>'