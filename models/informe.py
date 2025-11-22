"""
Modelos de Informes (Biopsias, Citología, PAP)
"""
from extensions import db
from datetime import datetime
import json


class BiopsiaInforme(db.Model):
    """Informes específicos de biopsias"""
    __tablename__ = 'biopsias_informes'
    
    biopsia_informe_id = db.Column(db.Integer, primary_key=True)
    protocolo_id = db.Column(db.Integer, db.ForeignKey('protocolos.protocolo_id'), unique=True, nullable=False)
    material_remitido = db.Column(db.Text)
    descripcion_macroscopica = db.Column(db.Text)
    descripcion_microscopica = db.Column(db.Text)
    diagnostico = db.Column(db.Text)
    observaciones = db.Column(db.Text)
    fecha_informe = db.Column(db.Date)
    
    def __repr__(self):
        return f'<BiopsiaInforme protocolo_id={self.protocolo_id}>'


class CitologiaInforme(db.Model):
    """Informes de citología general"""
    __tablename__ = 'citologia_informes'
    
    citologia_informe_id = db.Column(db.Integer, primary_key=True)
    protocolo_id = db.Column(db.Integer, db.ForeignKey('protocolos.protocolo_id'), unique=True, nullable=False)
    descripcion = db.Column(db.Text)
    diagnostico = db.Column(db.Text)
    observaciones = db.Column(db.Text)
    fecha_informe = db.Column(db.Date)
    
    def __repr__(self):
        return f'<CitologiaInforme protocolo_id={self.protocolo_id}>'


class PapInforme(db.Model):
    """Informes de citología cérvico vaginal (PAP)"""
    __tablename__ = 'pap_informes'
    
    pap_informe_id = db.Column(db.Integer, primary_key=True)
    protocolo_id = db.Column(db.Integer, db.ForeignKey('protocolos.protocolo_id'), unique=True, nullable=False)
    
    # Datos clínicos
    fum = db.Column(db.Date)  # Fecha Última Menstruación
    datos_clinicos_1 = db.Column(db.Text)
    datos_clinicos_2 = db.Column(db.Text)
    datos_clinicos_3 = db.Column(db.Text)
    datos_clinicos_4 = db.Column(db.Text)
    datos_clinicos_5 = db.Column(db.Text)
    
    # Extendido
    extendido_1 = db.Column(db.Text)
    extendido_2 = db.Column(db.Text)
    extendido_3 = db.Column(db.Text)
    extendido_4 = db.Column(db.Text)
    extendido_5 = db.Column(db.Text)
    
    # Células
    celulas_1 = db.Column(db.Text)
    celulas_2 = db.Column(db.Text)
    celulas_3 = db.Column(db.Text)
    celulas_4 = db.Column(db.Text)
    celulas_5 = db.Column(db.Text)
    
    # Componente inflamatorio
    comp_inflamatorio_1 = db.Column(db.Text)
    comp_inflamatorio_2 = db.Column(db.Text)
    comp_inflamatorio_3 = db.Column(db.Text)
    
    # Flora
    flora_1 = db.Column(db.Text)
    flora_2 = db.Column(db.Text)
    
    # Diagnóstico
    diagnostico_1 = db.Column(db.Text)
    diagnostico_2 = db.Column(db.Text)
    diagnostico_3 = db.Column(db.Text)
    diagnostico_4 = db.Column(db.Text)
    diagnostico_5 = db.Column(db.Text)
    
    # Informe completo generado
    informe_completo = db.Column(db.Text)
    fecha_informe = db.Column(db.Date)
    
    def generar_informe_completo(self):
        """Genera el texto completo del informe concatenando las secciones"""
        secciones = []
        
        # Datos clínicos
        datos_clinicos = [self.datos_clinicos_1, self.datos_clinicos_2, 
                         self.datos_clinicos_3, self.datos_clinicos_4, 
                         self.datos_clinicos_5]
        datos_clinicos = [d for d in datos_clinicos if d]
        if datos_clinicos:
            secciones.append("DATOS CLÍNICOS:\n" + " ".join(datos_clinicos))
        
        # Extendido
        extendidos = [self.extendido_1, self.extendido_2, self.extendido_3,
                     self.extendido_4, self.extendido_5]
        extendidos = [e for e in extendidos if e]
        if extendidos:
            secciones.append("EXTENDIDO:\n" + " ".join(extendidos))
        
        # Células
        celulas = [self.celulas_1, self.celulas_2, self.celulas_3,
                  self.celulas_4, self.celulas_5]
        celulas = [c for c in celulas if c]
        if celulas:
            secciones.append("CÉLULAS:\n" + " ".join(celulas))
        
        # Componente inflamatorio
        comp_inflam = [self.comp_inflamatorio_1, self.comp_inflamatorio_2,
                      self.comp_inflamatorio_3]
        comp_inflam = [c for c in comp_inflam if c]
        if comp_inflam:
            secciones.append("COMPONENTE INFLAMATORIO:\n" + " ".join(comp_inflam))
        
        # Flora
        floras = [self.flora_1, self.flora_2]
        floras = [f for f in floras if f]
        if floras:
            secciones.append("FLORA:\n" + " ".join(floras))
        
        # Diagnóstico
        diagnosticos = [self.diagnostico_1, self.diagnostico_2, self.diagnostico_3,
                       self.diagnostico_4, self.diagnostico_5]
        diagnosticos = [d for d in diagnosticos if d]
        if diagnosticos:
            secciones.append("DIAGNÓSTICO:\n" + " ".join(diagnosticos))
        
        self.informe_completo = "\n\n".join(secciones)
        return self.informe_completo
    
    def __repr__(self):
        return f'<PapInforme protocolo_id={self.protocolo_id}>'


class PlantillaPap(db.Model):
    """Plantillas predefinidas para informes PAP"""
    __tablename__ = 'plantillas_pap'
    
    plantilla_pap_id = db.Column(db.Integer, primary_key=True)
    categoria = db.Column(db.String(50), nullable=False, index=True)
    codigo = db.Column(db.String(20), nullable=True)
    descripcion = db.Column(db.Text, nullable=False)
    orden = db.Column(db.Integer, default=0)
    activo = db.Column(db.Boolean, default=True, nullable=False)
    
    # Índice para ordenar las plantillas
    __table_args__ = (
        db.Index('idx_plantilla_categoria_orden', 'categoria', 'orden'),
    )
    
    @staticmethod
    def get_categorias():
        """Devuelve las categorías disponibles"""
        return [
            'EXTENDIDO',
            'CELULAS_CONFORMACION',
            'CELULAS_JUNTO_A',
            'COMPONENTE_INFLAMATORIO',
            'FLORA',
            'DIAGNOSTICO',
            'DATOS_CLINICOS'
        ]
    
    def __repr__(self):
        return f'<PlantillaPap {self.categoria}>'


class LineaPap(db.Model):
    """Líneas individuales reutilizables para informes PAP"""
    __tablename__ = 'lineas_pap'
    
    linea_id = db.Column(db.Integer, primary_key=True)
    categoria = db.Column(db.String(50), nullable=False, index=True)
    texto = db.Column(db.Text, nullable=False)
    orden = db.Column(db.Integer, default=0)
    activo = db.Column(db.Boolean, default=True, nullable=False)
    veces_usado = db.Column(db.Integer, default=0)
    ultima_vez_usado = db.Column(db.DateTime)
    
    # Índices para optimizar consultas
    __table_args__ = (
        db.Index('idx_lineas_categoria_orden', 'categoria', 'orden'),
    )
    
    def __repr__(self):
        return f'<LineaPap categoria={self.categoria} texto={self.texto[:30]}...>'


class PlantillaLinea(db.Model):
    """Relación entre plantillas y líneas individuales"""
    __tablename__ = 'plantilla_lineas'
    
    plantilla_linea_id = db.Column(db.Integer, primary_key=True)
    plantilla_id = db.Column(db.Integer, db.ForeignKey('plantillas_pap.plantilla_pap_id'), nullable=False)
    linea_plantilla_id = db.Column(db.Integer, db.ForeignKey('lineas_pap.linea_id'), nullable=False)
    orden = db.Column(db.Integer, default=0)
    
    # Relaciones
    plantilla = db.relationship('PlantillaPap', backref='lineas_asociadas')
    linea = db.relationship('LineaPap', backref='plantillas_asociadas')
    
    # Índices únicos
    __table_args__ = (
        db.UniqueConstraint('plantilla_id', 'linea_plantilla_id', name='uq_plantilla_linea'),
        db.Index('idx_plantilla_lineas_plantilla', 'plantilla_id'),
        db.Index('idx_plantilla_lineas_linea', 'linea_plantilla_id'),
    )
    
    def __repr__(self):
        return f'<PlantillaLinea plantilla_id={self.plantilla_id} linea_id={self.linea_plantilla_id}>'


class ProtocoloLinea(db.Model):
    """Líneas individuales de cada protocolo (genérico para todos los tipos)"""
    __tablename__ = 'protocolo_lineas'
    
    protocolo_linea_id = db.Column(db.Integer, primary_key=True)
    protocolo_id = db.Column(db.Integer, db.ForeignKey('protocolos.protocolo_id'), nullable=False)
    seccion = db.Column(db.String(50), nullable=False, index=True)
    texto = db.Column(db.Text, nullable=False)
    orden = db.Column(db.Integer, default=0)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relación con protocolo
    protocolo = db.relationship('Protocolo', backref='lineas')
    
    # Índices para optimizar consultas
    __table_args__ = (
        db.Index('idx_protocolo_lineas_protocolo', 'protocolo_id'),
        db.Index('idx_protocolo_lineas_seccion', 'seccion'),
        db.Index('idx_protocolo_lineas_orden', 'protocolo_id', 'seccion', 'orden'),
    )
    
    def __repr__(self):
        return f'<ProtocoloLinea protocolo_id={self.protocolo_id} seccion={self.seccion} texto={self.texto[:30]}...>'


class PlantillaBiopsia(db.Model):
    """Plantillas predefinidas para informes de Biopsias"""
    __tablename__ = 'plantillas_biopsias'
    
    plantilla_biopsia_id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, index=True)  # Nombre de la plantilla (ej: "Gastritis")
    seccion = db.Column(db.String(50), nullable=False, index=True)  # MATERIAL_REMITIDO, DESCRIPCION_MACROSCOPICA, etc.
    descripcion = db.Column(db.Text)
    orden = db.Column(db.Integer, default=0)
    activo = db.Column(db.Boolean, default=True, nullable=False)
    
    # Índice para ordenar las plantillas
    __table_args__ = (
        db.Index('idx_plantilla_biopsia_nombre_seccion', 'nombre', 'seccion'),
        db.Index('idx_plantilla_biopsia_seccion_orden', 'seccion', 'orden'),
    )
    
    @staticmethod
    def get_secciones():
        """Devuelve las secciones disponibles para biopsias"""
        return [
            'MATERIAL_REMITIDO',
            'DESCRIPCION_MACROSCOPICA',
            'DESCRIPCION_MICROSCOPICA',
            'DIAGNOSTICO'
        ]
    
    def __repr__(self):
        return f'<PlantillaBiopsia {self.nombre} - {self.seccion}>'


class LineaBiopsia(db.Model):
    """Líneas individuales reutilizables para informes de Biopsias"""
    __tablename__ = 'lineas_biopsias'
    
    linea_id = db.Column(db.Integer, primary_key=True)
    seccion = db.Column(db.String(50), nullable=False, index=True)  # MATERIAL_REMITIDO, DESCRIPCION_MACROSCOPICA, etc.
    texto = db.Column(db.Text, nullable=False)
    orden = db.Column(db.Integer, default=0)
    activo = db.Column(db.Boolean, default=True, nullable=False)
    veces_usado = db.Column(db.Integer, default=0)
    ultima_vez_usado = db.Column(db.DateTime)
    
    # Índices para optimizar consultas
    __table_args__ = (
        db.Index('idx_lineas_biopsias_seccion_orden', 'seccion', 'orden'),
    )
    
    def __repr__(self):
        return f'<LineaBiopsia seccion={self.seccion} texto={self.texto[:30]}...>'


class PlantillaLineaBiopsia(db.Model):
    """Relación entre plantillas y líneas individuales de Biopsias"""
    __tablename__ = 'plantilla_lineas_biopsias'
    
    plantilla_linea_biopsia_id = db.Column(db.Integer, primary_key=True)
    plantilla_id = db.Column(db.Integer, db.ForeignKey('plantillas_biopsias.plantilla_biopsia_id'), nullable=False)
    linea_plantilla_id = db.Column(db.Integer, db.ForeignKey('lineas_biopsias.linea_id'), nullable=False)
    orden = db.Column(db.Integer, default=0)
    
    # Relaciones
    plantilla = db.relationship('PlantillaBiopsia', backref='lineas_asociadas')
    linea = db.relationship('LineaBiopsia', backref='plantillas_asociadas')
    
    # Índices únicos
    __table_args__ = (
        db.UniqueConstraint('plantilla_id', 'linea_plantilla_id', name='uq_plantilla_linea_biopsia'),
        db.Index('idx_plantilla_lineas_biopsias_plantilla', 'plantilla_id'),
        db.Index('idx_plantilla_lineas_biopsias_linea', 'linea_plantilla_id'),
    )
    
    def __repr__(self):
        return f'<PlantillaLineaBiopsia plantilla_id={self.plantilla_id} linea_id={self.linea_plantilla_id}>'


class DisenioInforme(db.Model):
    """Configuraciones de diseño para los informes (márgenes, posiciones, tamaños, variantes)"""
    __tablename__ = 'disenios_informes'
    
    disenio_id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)  # Ej: "Membretado", "Papel común"
    tipo_estudio = db.Column(db.String(20), nullable=False)  # PAP, BIOPSIA, CITOLOGÍA
    activo = db.Column(db.Boolean, default=True)
    es_default = db.Column(db.Boolean, default=False)  # Variante por defecto para este tipo
    
    # Configuraciones generales (almacenadas como JSON)
    configuracion = db.Column(db.Text)  # JSON con todas las configuraciones
    
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_modificacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    usuario_creador_id = db.Column(db.Integer, db.ForeignKey('usuarios.usuario_id'))
    
    def get_configuracion(self):
        """Retorna la configuración como diccionario"""
        if self.configuracion:
            config = json.loads(self.configuracion)
            # Asegurar que tenga todas las claves por defecto (para diseños antiguos)
            default = self._get_default_config()
            # Mergear configuraciones faltantes con defaults
            if 'textos_personalizados' not in config:
                config['textos_personalizados'] = default['textos_personalizados']
            # Asegurar que datos_protocolo tenga las nuevas claves
            if 'datos_protocolo' in config:
                for key in default['datos_protocolo']:
                    if key not in config['datos_protocolo']:
                        config['datos_protocolo'][key] = default['datos_protocolo'][key]
            # Asegurar que header tenga las nuevas claves
            if 'header' in config:
                for key in default['header']:
                    if key not in config['header']:
                        config['header'][key] = default['header'][key]
            # Asegurar que secciones tenga las nuevas claves
            if 'secciones' in config:
                for key in default['secciones']:
                    if key not in config['secciones']:
                        config['secciones'][key] = default['secciones'][key]
            return config
        return self._get_default_config()
    
    def set_configuracion(self, config_dict):
        """Establece la configuración desde un diccionario"""
        self.configuracion = json.dumps(config_dict)
    
    def _get_default_config(self):
        """Configuración por defecto"""
        return {
            # Márgenes del documento (en mm)
            'margenes': {
                'superior': 20,
                'inferior': 20,
                'izquierdo': 20,
                'derecho': 20
            },
            # Espacio superior para membrete (0 para papel común, >0 para membretado)
            'espacio_membrete': 0,
            # Configuración del header
            'header': {
                'mostrar_logo': True,
                'logo_ancho': 240,
                'logo_alto': 240,
                'logo_posicion': 'izquierda',  # izquierda, centro, derecha
                'logo_margen_derecho': 20,
                'laboratorio_nombre': 'LABORATORIO DE DIAGNÓSTICO HISTOPATOLÓGICO',  # Texto editable
                'laboratorio_fuente': 'Arial',  # Font family
                'laboratorio_tamano': 24,
                'laboratorio_color': '#007bff',
                'titulo_tamano': 18,
                'titulo_fuente': 'Arial',
                'titulo_color': '#333',
                'subtitulo_tamano': 14,
                'subtitulo_fuente': 'Arial',
                'subtitulo_color': '#666',
                'titulo_alineacion': 'centro',
                'padding_inferior': 5
            },
            # Configuración de datos del protocolo
            'datos_protocolo': {
                'mostrar': True,
                'columnas': 3,
                'espaciado': 20,
                'padding': 15,
                'fondo': '#f8f9fa',
                'margen_inferior': 30,
                # Etiquetas editables
                'label_protocolo': 'Protocolo:',
                'label_fecha': 'Fecha:',
                'label_paciente': 'Paciente:',
                'label_dni': 'DNI:',
                'label_edad': 'Edad:',
                'label_obra_social': 'Obra Social:',
                'label_medico': 'Médico:',
                'label_especialidad': 'Especialidad:',
                'titulo_grupo_protocolo': 'PROTOCOLO Y FECHA',
                'titulo_grupo_paciente': 'DATOS DEL PACIENTE',
                'titulo_grupo_medico': 'DATOS DEL MÉDICO'
            },
            # Textos personalizables adicionales
            'textos_personalizados': {
                'texto_firma': 'Dr. [Nombre del Médico]\nMédico Patólogo\nMP: [Número de Matrícula]',
                'mostrar_firma': True,
                'texto_pie': '',  # Si está vacío, usa los datos del laboratorio
                'mostrar_pie': True,
                'textos_adicionales': []  # Lista de textos adicionales: [{'texto': '...', 'posicion': 'header|footer|despues_datos'}, ...]
            },
            # Configuración de secciones
            'secciones': {
                'espacio_entre': 20,
                'titulo_tamano': 12,
                'titulo_fuente': 'Arial',
                'titulo_negrita': True,
                'titulo_color': '#007bff',
                'color_fondo_titulo': '#e3f2fd',  # Color de fondo de los títulos de sección
                'contenido_tamano': 12,
                'contenido_fuente': 'Arial',
                'contenido_color': '#333',
                'line_height': 1.4,
                'padding_seccion': '8px 12px',
                'margen_inferior': 15,
                'indentacion': 15,  # Indentación del contenido (márgen izquierdo)
                'mostrar_vinetas': True,  # Mostrar viñetas (bullets) en las líneas
                'color_vineta': '#007bff',  # Color de las viñetas
                'alineacion_contenido': 'left'  # Alineación del contenido (left, center, right, justify)
            },
            # Configuración de impresión
            'impresion': {
                'tamaño_papel': 'A4',
                'orientacion': 'vertical',
                'escala': 100
            }
        }
    
    def __repr__(self):
        return f'<DisenioInforme {self.nombre} - {self.tipo_estudio}>'

