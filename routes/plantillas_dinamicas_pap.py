#!/usr/bin/env python3
"""
Rutas para el sistema PAP con plantillas desde base de datos
"""
from flask import Blueprint, render_template, request, jsonify
from LDH_Web.models.informe import PlantillaPap, LineaPap, PlantillaLinea
from LDH_Web import db
import json

bp = Blueprint('plantillas_dinamicas_pap', __name__, url_prefix='/plantillas-dinamicas-pap')

@bp.route('/editor-pap')
def editor_pap():
    """Editor PAP con plantillas desde base de datos"""
    return render_template('plantillas_dinamicas/editor_pap_bd.html')

@bp.route('/api/plantillas')
def obtener_plantillas():
    """Obtener todas las plantillas disponibles"""
    try:
        plantillas = PlantillaPap.query.filter_by(activo=True).order_by(PlantillaPap.orden).all()
        
        resultado = []
        for plantilla in plantillas:
            resultado.append({
                'codigo': plantilla.codigo,
                'descripcion': plantilla.descripcion,
                'categoria': plantilla.categoria
            })
        
        return jsonify({'plantillas': resultado})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/plantilla/<codigo>')
def obtener_plantilla(codigo):
    """Obtener plantilla específica con sus líneas"""
    try:
        plantilla = PlantillaPap.query.filter_by(codigo=codigo, activo=True).first()
        if not plantilla:
            return jsonify({'error': 'Plantilla no encontrada'}), 404
        
        # Obtener líneas asociadas
        lineas = db.session.query(LineaPap, PlantillaLinea).join(
            PlantillaLinea, LineaPap.lineas_pap_id == PlantillaLinea.lineas_pap_id
        ).filter(
            PlantillaLinea.plantillas_pap_id == plantilla.plantilla_pap_id
        ).order_by(PlantillaLinea.orden).all()
        
        resultado = {
            'codigo': plantilla.codigo,
            'descripcion': plantilla.descripcion,
            'categoria': plantilla.categoria,
            'lineas': []
        }
        
        for linea, plantilla_linea in lineas:
            resultado['lineas'].append({
                'categoria': linea.categoria,
                'texto': linea.texto,
                'orden': plantilla_linea.orden
            })
        
        return jsonify(resultado)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/lineas/<categoria>')
def obtener_lineas_categoria(categoria):
    """Obtener líneas disponibles para una categoría específica"""
    try:
        lineas = LineaPap.query.filter_by(categoria=categoria, activo=True).order_by(LineaPap.orden).all()
        
        resultado = []
        for linea in lineas:
            resultado.append({
                'lineas_pap_id': linea.lineas_pap_id,
                'texto': linea.texto,
                'orden': linea.orden
            })
        
        return jsonify({'lineas': resultado})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/guardar-informe', methods=['POST'])
def guardar_informe():
    """Guardar informe PAP en pap_informes"""
    try:
        data = request.get_json()
        
        # Aquí implementarías la lógica para guardar en pap_informes
        # Por ahora solo retornamos éxito
        return jsonify({'success': True, 'message': 'Informe guardado correctamente'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
