#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Rutas para el selector de plantillas categorizado
"""

from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from functools import wraps
from models import SeccionPlantilla, LineaPlantilla

bp = Blueprint('selector_plantillas', __name__, url_prefix='/selector_plantillas')

def permission_required(permission):
    """Decorador para verificar permisos"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from models import Usuario
            if not current_user.is_authenticated:
                return jsonify({'error': 'No autenticado'}), 401
            
            # Verificar permiso - usar current_user directamente
            if not current_user.tiene_permiso(permission):
                return jsonify({'error': 'Sin permisos'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@bp.route('/modal_plantillas')
@login_required
def modal_plantillas():
    """Modal para selección de plantillas categorizadas"""
    
    # Obtener todas las secciones con sus líneas
    secciones = SeccionPlantilla.query.order_by(SeccionPlantilla.orden).all()
    
    secciones_data = []
    for seccion in secciones:
        lineas = LineaPlantilla.query.filter_by(seccion_id=seccion.seccion_id).all()
        
        secciones_data.append({
            'seccion_id': seccion.seccion_id,
            'codigo': seccion.codigo,
            'nombre': seccion.nombre,
            'descripcion': seccion.descripcion,
            'categoria': seccion.codigo[0] if seccion.codigo else 'O',  # T, H, A, I
            'lineas': [{
                'linea_id': linea.linea_id,
                'texto': linea.texto,
                'codigo': linea.codigo
            } for linea in lineas]
        })
    
    # Agrupar por categorías
    categorias = {}
    for seccion in secciones_data:
        cat = seccion['categoria']
        if cat not in categorias:
            categorias[cat] = {
                'nombre': get_categoria_nombre(cat),
                'color': get_categoria_color(cat),
                'icono': get_categoria_icono(cat),
                'secciones': []
            }
        categorias[cat]['secciones'].append(seccion)
    
    return render_template('components/selector_plantillas_modal.html', 
                         categorias=categorias)

@bp.route('/buscar_plantillas')
@login_required
def buscar_plantillas():
    """Buscar plantillas por texto"""
    
    termino = request.args.get('q', '').strip().lower()
    
    if not termino:
        return jsonify({'resultados': []})
    
    # Buscar en todas las líneas
    lineas = LineaPlantilla.query.filter(
        LineaPlantilla.texto.ilike(f'%{termino}%')
    ).all()
    
    resultados = []
    for linea in lineas:
        seccion = SeccionPlantilla.query.get(linea.seccion_id)
        resultados.append({
            'linea_id': linea.linea_id,
            'texto': linea.texto,
            'codigo': f"L{linea.linea_id}",  # Generar código automático
            'seccion': {
                'codigo': seccion.codigo,
                'nombre': seccion.nombre,
                'categoria': seccion.codigo[0] if seccion.codigo else 'O'
            }
        })
    
    return jsonify({'resultados': resultados})

@bp.route('/obtener_lineas_seccion/<int:seccion_id>')
@login_required
def obtener_lineas_seccion(seccion_id):
    """Obtener líneas de una sección específica"""
    try:
        seccion = SeccionPlantilla.query.get_or_404(seccion_id)
        lineas = LineaPlantilla.query.filter_by(seccion_id=seccion_id).all()
        
        return jsonify({
            'seccion': {
                'seccion_id': seccion.seccion_id,
                'codigo': seccion.codigo,
                'nombre': seccion.nombre,
                'descripcion': seccion.descripcion
            },
            'lineas': [{
                'linea_id': linea.linea_id,
                'texto': linea.texto,
                'codigo': f"L{linea.linea_id}"  # Generar código automático
            } for linea in lineas]
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'seccion': None,
            'lineas': []
        }), 500

def get_categoria_nombre(categoria):
    """Obtener nombre descriptivo de la categoría"""
    nombres = {
        'T': 'Trófoco',
        'H': 'Hipotrófoco', 
        'A': 'Atrófico',
        'I': 'Inflamatorio'
    }
    return nombres.get(categoria, 'Otros')

def get_categoria_color(categoria):
    """Obtener color para la categoría"""
    colores = {
        'T': 'primary',    # Azul
        'H': 'success',    # Verde
        'A': 'warning',    # Amarillo
        'I': 'danger'      # Rojo
    }
    return colores.get(categoria, 'secondary')

def get_categoria_icono(categoria):
    """Obtener icono para la categoría"""
    iconos = {
        'T': 'bi-check-circle',      # Trófoco - Normal
        'H': 'bi-exclamation-circle', # Hipotrófoco - Atención
        'A': 'bi-info-circle',       # Atrófico - Información
        'I': 'bi-exclamation-triangle' # Inflamatorio - Alerta
    }
    return iconos.get(categoria, 'bi-circle')
