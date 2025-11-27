"""
Herramientas (tools) para que el asistente pueda consultar la base de datos
"""
from typing import Dict, List, Any
from extensions import db
from models.protocolo import Protocolo
from models.paciente import Afiliado
from models.prestador import Prestador
from models.obra_social import ObraSocial
from sqlalchemy import func, desc, distinct
import logging

logger = logging.getLogger(__name__)


def obtener_top_prestadores_por_pacientes(limite: int = 10) -> Dict[str, Any]:
    """
    Obtener los prestadores con más pacientes únicos
    
    Args:
        limite: Número máximo de prestadores a retornar (por defecto 10)
    
    Returns:
        Dict con lista de prestadores y cantidad de pacientes
    """
    try:
        # Contar pacientes únicos por prestador (excluyendo protocolos de prueba)
        query = db.session.query(
            Prestador.prestador_id,
            Prestador.nombre_completo,
            Prestador.especialidad,
            func.count(distinct(Protocolo.afiliado_id)).label('cantidad_pacientes')
        ).join(
            Protocolo, Prestador.prestador_id == Protocolo.prestador_id
        ).filter(
            Protocolo.es_prueba == False,
            Prestador.activo == True,
            Prestador.es_entidad == False  # Solo prestadores médicos, no entidades
        ).group_by(
            Prestador.prestador_id,
            Prestador.nombre_completo,
            Prestador.especialidad
        ).order_by(
            desc('cantidad_pacientes')
        ).limit(limite).all()
        
        resultado = []
        for prestador_id, nombre, especialidad, cantidad in query:
            resultado.append({
                'prestador_id': prestador_id,
                'nombre': nombre,
                'especialidad': especialidad or 'Sin especialidad',
                'cantidad_pacientes': cantidad
            })
        
        return {
            'success': True,
            'prestadores': resultado,
            'total': len(resultado)
        }
    except Exception as e:
        logger.error(f"Error obteniendo top prestadores: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'prestadores': []
        }


def obtener_pacientes_con_multiples_protocolos(min_protocolos: int = 2) -> Dict[str, Any]:
    """
    Obtener pacientes que tienen más de un protocolo
    
    Args:
        min_protocolos: Número mínimo de protocolos que debe tener el paciente (por defecto 2)
    
    Returns:
        Dict con lista de pacientes y cantidad de protocolos
    """
    try:
        query = db.session.query(
            Afiliado.afiliado_id,
            Afiliado.nombre,
            Afiliado.numero_documento,
            func.count(Protocolo.protocolo_id).label('cantidad_protocolos')
        ).join(
            Protocolo, Afiliado.afiliado_id == Protocolo.afiliado_id
        ).filter(
            Protocolo.es_prueba == False,
            Afiliado.activo == True
        ).group_by(
            Afiliado.afiliado_id,
            Afiliado.nombre,
            Afiliado.numero_documento
        ).having(
            func.count(Protocolo.protocolo_id) >= min_protocolos
        ).order_by(
            desc('cantidad_protocolos')
        ).all()
        
        resultado = []
        for afiliado_id, nombre, documento, cantidad in query:
            resultado.append({
                'paciente_id': afiliado_id,
                'nombre': nombre,
                'documento': documento or 'Sin documento',
                'cantidad_protocolos': cantidad
            })
        
        return {
            'success': True,
            'pacientes': resultado,
            'total': len(resultado)
        }
    except Exception as e:
        logger.error(f"Error obteniendo pacientes con múltiples protocolos: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'pacientes': []
        }


def obtener_estadisticas_protocolos() -> Dict[str, Any]:
    """
    Obtener estadísticas generales de protocolos
    
    Returns:
        Dict con estadísticas de protocolos
    """
    try:
        # Total de protocolos (excluyendo pruebas)
        total = Protocolo.query.filter_by(es_prueba=False).count()
        
        # Por estado
        por_estado = db.session.query(
            Protocolo.estado,
            func.count(Protocolo.protocolo_id).label('cantidad')
        ).filter(
            Protocolo.es_prueba == False
        ).group_by(
            Protocolo.estado
        ).all()
        
        estados = {estado: cantidad for estado, cantidad in por_estado}
        
        # Por tipo de estudio
        por_tipo = db.session.query(
            Protocolo.tipo_estudio,
            func.count(Protocolo.protocolo_id).label('cantidad')
        ).filter(
            Protocolo.es_prueba == False
        ).group_by(
            Protocolo.tipo_estudio
        ).all()
        
        tipos = {tipo: cantidad for tipo, cantidad in por_tipo}
        
        # Pacientes únicos
        pacientes_unicos = db.session.query(
            func.count(distinct(Protocolo.afiliado_id))
        ).filter(
            Protocolo.es_prueba == False
        ).scalar()
        
        return {
            'success': True,
            'total_protocolos': total,
            'pacientes_unicos': pacientes_unicos or 0,
            'por_estado': estados,
            'por_tipo_estudio': tipos
        }
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }


# Diccionario de herramientas disponibles
TOOLS = [
    {
        "name": "obtener_top_prestadores_por_pacientes",
        "description": "Obtiene los prestadores (médicos) con más pacientes únicos. Útil para responder preguntas como '¿cuáles son los 10 prestadores con más pacientes?'",
        "input_schema": {
            "type": "object",
            "properties": {
                "limite": {
                    "type": "integer",
                    "description": "Número máximo de prestadores a retornar (por defecto 10)"
                }
            },
            "required": []
        }
    },
    {
        "name": "obtener_pacientes_con_multiples_protocolos",
        "description": "Obtiene pacientes que tienen más de un protocolo. Útil para responder preguntas como '¿qué pacientes tienen más de un protocolo?'",
        "input_schema": {
            "type": "object",
            "properties": {
                "min_protocolos": {
                    "type": "integer",
                    "description": "Número mínimo de protocolos que debe tener el paciente (por defecto 2)"
                }
            },
            "required": []
        }
    },
    {
        "name": "obtener_estadisticas_protocolos",
        "description": "Obtiene estadísticas generales de protocolos: total, por estado, por tipo de estudio, y cantidad de pacientes únicos",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]


# Mapeo de nombres de funciones a implementaciones
FUNCIONES_IMPLEMENTACIONES = {
    "obtener_top_prestadores_por_pacientes": obtener_top_prestadores_por_pacientes,
    "obtener_pacientes_con_multiples_protocolos": obtener_pacientes_con_multiples_protocolos,
    "obtener_estadisticas_protocolos": obtener_estadisticas_protocolos
}


def ejecutar_funcion(nombre_funcion: str, argumentos: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ejecutar una función de consulta a la base de datos
    
    Args:
        nombre_funcion: Nombre de la función a ejecutar
        argumentos: Argumentos para la función
    
    Returns:
        Resultado de la ejecución de la función
    """
    if nombre_funcion not in FUNCIONES_IMPLEMENTACIONES:
        return {
            'success': False,
            'error': f'Función {nombre_funcion} no encontrada'
        }
    
    try:
        funcion = FUNCIONES_IMPLEMENTACIONES[nombre_funcion]
        resultado = funcion(**argumentos)
        return resultado
    except Exception as e:
        logger.error(f"Error ejecutando función {nombre_funcion}: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }

