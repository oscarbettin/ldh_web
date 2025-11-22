"""
Modelo de Configuración del Sistema
"""
from extensions import db
import json


class Configuracion(db.Model):
    """Parámetros de configuración general"""
    __tablename__ = 'configuracion'
    
    configuracion_id = db.Column(db.Integer, primary_key=True)
    clave = db.Column(db.String(100), unique=True, nullable=False, index=True)
    valor = db.Column(db.Text)
    tipo = db.Column(db.String(20))  # STRING, INTEGER, BOOLEAN, JSON
    descripcion = db.Column(db.Text)
    categoria = db.Column(db.String(50), index=True)
    
    @staticmethod
    def get(clave, default=None):
        """
        Obtiene un valor de configuración
        
        Args:
            clave: Clave de configuración
            default: Valor por defecto si no existe
        
        Returns:
            El valor de la configuración convertido al tipo apropiado
        """
        config = Configuracion.query.filter_by(clave=clave).first()
        if not config:
            return default
        
        # Convertir según el tipo
        if config.tipo == 'INTEGER':
            return int(config.valor) if config.valor else default
        elif config.tipo == 'BOOLEAN':
            return config.valor.lower() in ('true', '1', 'yes') if config.valor else default
        elif config.tipo == 'JSON':
            return json.loads(config.valor) if config.valor else default
        else:  # STRING
            return config.valor if config.valor else default
    
    @staticmethod
    def set(clave, valor, tipo='STRING', descripcion=None, categoria=None):
        """
        Establece un valor de configuración
        
        Args:
            clave: Clave de configuración
            valor: Valor a establecer
            tipo: Tipo de dato (STRING, INTEGER, BOOLEAN, JSON)
            descripcion: Descripción de la configuración
            categoria: Categoría de la configuración
        """
        config = Configuracion.query.filter_by(clave=clave).first()
        
        # Convertir el valor a string según el tipo
        if tipo == 'JSON':
            valor_str = json.dumps(valor)
        elif tipo == 'BOOLEAN':
            valor_str = 'true' if valor else 'false'
        else:
            valor_str = str(valor)
        
        if config:
            # Actualizar existente
            config.valor = valor_str
            config.tipo = tipo
            if descripcion:
                config.descripcion = descripcion
            if categoria:
                config.categoria = categoria
        else:
            # Crear nuevo
            config = Configuracion(
                clave=clave,
                valor=valor_str,
                tipo=tipo,
                descripcion=descripcion,
                categoria=categoria
            )
            db.session.add(config)
        
        db.session.commit()
    
    @staticmethod
    def init_defaults():
        """Inicializa las configuraciones por defecto"""
        defaults = [
            ('laboratorio_nombre', 'Laboratorio de Anatomía Patológica', 'STRING', 'Nombre del laboratorio', 'GENERAL'),
            ('laboratorio_direccion', '', 'STRING', 'Dirección del laboratorio', 'GENERAL'),
            ('laboratorio_telefono', '', 'STRING', 'Teléfono del laboratorio', 'GENERAL'),
            ('laboratorio_email', '', 'STRING', 'Email del laboratorio', 'GENERAL'),
            ('contador_biopsias_actual', '0', 'INTEGER', 'Contador actual de biopsias', 'CONTADORES'),
            ('contador_citologia_actual', '0', 'INTEGER', 'Contador actual de citología', 'CONTADORES'),
            ('contador_pap_actual', '0', 'INTEGER', 'Contador actual de PAP', 'CONTADORES'),
            ('items_por_pagina', '50', 'INTEGER', 'Items por página en listados', 'GENERAL'),
        ]
        
        for clave, valor, tipo, descripcion, categoria in defaults:
            if not Configuracion.query.filter_by(clave=clave).first():
                Configuracion.set(clave, valor, tipo, descripcion, categoria)
    
    def __repr__(self):
        return f'<Configuracion {self.clave}={self.valor}>'

