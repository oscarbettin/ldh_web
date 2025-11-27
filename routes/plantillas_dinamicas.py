"""
Rutas para el sistema de plantillas dinámicas con secciones y líneas
"""
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from flask_login import login_required, current_user
from extensions import db
from models.plantilla_dinamica import SeccionPlantilla, LineaPlantilla, ConfiguracionBotones, PlantillaGenerada
from models.protocolo import Protocolo
from models.paciente import Afiliado
from datetime import date
from sqlalchemy import or_, and_
import json
import unicodedata

def _normalizar_texto(texto: str) -> str:
    if not texto:
        return ''
    texto = unicodedata.normalize('NFD', texto.strip().lower())
    return ''.join(ch for ch in texto if unicodedata.category(ch) != 'Mn')


def _usuario_es_medico() -> bool:
    if not current_user.is_authenticated or not getattr(current_user, 'rol', None):
        return False
    nombre = getattr(current_user.rol, 'nombre', '')
    normalizado = _normalizar_texto(nombre)
    return 'medico' in normalizado if normalizado else False


def _obtener_o_crear_protocolo_prueba(tipo_estudio: str):
    """
    Obtiene o crea un protocolo de prueba para el paciente "000 PRUEBA"
    Los protocolos de prueba no generan números de protocolo reales y se marcan con es_prueba=True
    """
    # Buscar paciente "000 PRUEBA" (nombre_completo es una @property, buscar por columnas reales)
    # Intentar varias combinaciones posibles: "000" en apellido y "PRUEBA" en nombre, o viceversa
    paciente_prueba = Afiliado.query.filter(
        or_(
            and_(Afiliado.apellido.ilike('%000%'), Afiliado.nombre.ilike('%PRUEBA%')),
            and_(Afiliado.apellido.ilike('%PRUEBA%'), Afiliado.nombre.ilike('%000%')),
            Afiliado.apellido.ilike('%000 PRUEBA%'),
            Afiliado.nombre.ilike('%000 PRUEBA%')
        )
    ).first()
    
    if not paciente_prueba:
        flash('No se encontró el paciente "000 PRUEBA". Por favor créelo primero.', 'error')
        return None
    
    # Normalizar tipo de estudio
    tipo_normalizado = tipo_estudio.upper().strip()
    if tipo_normalizado == 'CITOLOGIA':
        tipo_normalizado = 'CITOLOGÍA'
    
    # Buscar protocolo de prueba existente para este tipo
    protocolo_prueba = Protocolo.query.filter_by(
        afiliado_id=paciente_prueba.afiliado_id,
        tipo_estudio=tipo_normalizado,
        es_prueba=True
    ).first()
    
    if protocolo_prueba:
        return protocolo_prueba
    
    # Crear nuevo protocolo de prueba
    # Número especial para protocolos de prueba: PRUEBA-TIPO-0001
    numero_prueba = f'PRUEBA-{tipo_normalizado[:3]}-0001'
    
    protocolo_prueba = Protocolo(
        numero_protocolo=numero_prueba,
        tipo_estudio=tipo_normalizado,
        afiliado_id=paciente_prueba.afiliado_id,
        prestador_id=None,
        obra_social_id=None,
        fecha_ingreso=date.today(),
        estado='EN_PROCESO',
        es_prueba=True,  # Marcar como protocolo de prueba
        usuario_ingreso_id=current_user.usuario_id
    )
    
    db.session.add(protocolo_prueba)
    db.session.commit()
    
    return protocolo_prueba

bp = Blueprint('plantillas_dinamicas', __name__, url_prefix='/plantillas-dinamicas')


@bp.route('/editor-prueba/<tipo_estudio>')
@login_required
def editor_prueba(tipo_estudio):
    """
    Abre el editor de análisis directamente desde el paciente "000 PRUEBA"
    Crea o reutiliza un protocolo de prueba según el tipo de estudio
    """
    tipos_validos = ['PAP', 'BIOPSIA', 'CITOLOGÍA', 'CITOLOGIA']
    tipo_normalizado = tipo_estudio.upper().strip()
    
    if tipo_normalizado == 'CITOLOGIA':
        tipo_normalizado = 'CITOLOGÍA'
    
    if tipo_normalizado not in tipos_validos:
        flash('Tipo de estudio no válido.', 'error')
        return redirect(url_for('dashboard.index'))
    
    protocolo_prueba = _obtener_o_crear_protocolo_prueba(tipo_normalizado)
    
    if not protocolo_prueba:
        return redirect(url_for('dashboard.index'))
    
    # Redirigir al editor correspondiente
    if tipo_normalizado == 'PAP':
        return redirect(url_for('editor_avanzado.editor_pap_avanzado', protocolo_id=protocolo_prueba.protocolo_id))
    elif tipo_normalizado == 'BIOPSIA':
        return redirect(url_for('plantillas_dinamicas.editor_biopsias_v2', protocolo_id=protocolo_prueba.protocolo_id))
    elif tipo_normalizado == 'CITOLOGÍA':
        return redirect(url_for('plantillas_dinamicas.editor_citologia', protocolo_id=protocolo_prueba.protocolo_id))
    else:
        flash('Tipo de estudio no soportado.', 'error')
        return redirect(url_for('dashboard.index'))


@bp.route('/pap/<int:protocolo_id>')
@login_required
def editor_pap(protocolo_id):
    """
    Editor de plantillas PAP dinámicas
    """
    protocolo = Protocolo.query.get_or_404(protocolo_id)
    es_medico = _usuario_es_medico()
    
    # Verificar que el protocolo sea de tipo PAP
    if protocolo.tipo_estudio != 'PAP':
        return jsonify({'error': 'Este editor es solo para protocolos PAP'}), 400
    
    # Obtener secciones y botones
    secciones = SeccionPlantilla.query.filter_by(
        tipo_estudio='PAP',
        activo=True
    ).order_by(SeccionPlantilla.orden).all()
    
    botones = ConfiguracionBotones.query.filter_by(
        tipo_estudio='PAP',
        activo=True
    ).order_by(ConfiguracionBotones.numero_boton).all()
    
    # Cargar plantilla guardada si existe
    plantilla_guardada = PlantillaGenerada.query.filter_by(
        protocolo_id=protocolo_id,
        tipo_estudio='PAP',
        activo=True
    ).first()
    
    contenido_guardado = {}
    if plantilla_guardada and plantilla_guardada.contenido:
        try:
            contenido_guardado = json.loads(plantilla_guardada.contenido)
        except:
            contenido_guardado = {}
    
    # Convertir objetos a diccionarios para JSON
    secciones_dict = [{
        'seccion_id': s.seccion_id,
        'codigo': s.codigo,
        'nombre': s.nombre,
        'descripcion': s.descripcion,
        'orden': s.orden
    } for s in secciones]
    
    botones_dict = [{
        'codigo_boton': b.codigo_boton,
        'numero_boton': b.numero_boton,
        'seccion_id': b.seccion_id,
        'descripcion': b.descripcion
    } for b in botones]
    
    return render_template('plantillas_dinamicas/editor_pap.html',
                         protocolo=protocolo,
                         secciones=secciones_dict,
                         botones=botones_dict,
                         contenido_guardado=contenido_guardado,
                         es_medico=es_medico)


@bp.route('/obtener-lineas/<int:seccion_id>')
@login_required
def obtener_lineas_seccion(seccion_id):
    """
    Obtener líneas de una sección específica
    """
    try:
        seccion = SeccionPlantilla.query.get(seccion_id)
        if not seccion:
            return jsonify({'success': False, 'error': 'Sección no encontrada'}), 404

        lineas = LineaPlantilla.query.filter_by(
            seccion_id=seccion_id, activo=True
        ).order_by(LineaPlantilla.orden).all()

        payload_lineas = []
        for linea in lineas:
            payload_lineas.append({
                'id': linea.linea_id,
                'texto': linea.texto or '',
                'orden': int(linea.orden or 0),
                'veces_usado': int(linea.veces_usado or 0)
            })

        return jsonify({
            'success': True,
            'seccion': {
                'id': seccion.seccion_id,
                'nombre': seccion.nombre or '',
                'codigo': seccion.codigo or '',
                'descripcion': seccion.descripcion or ''
            },
            'lineas': payload_lineas
        })
    except Exception as e:
        # Evitar 500 opaco devolviendo detalle controlado
        return jsonify({'success': False, 'error': f'Error al obtener líneas: {str(e)}'}), 200


@bp.route('/usar-linea/<int:linea_id>', methods=['POST'])
@login_required
def usar_linea(linea_id):
    """
    Registrar uso de una línea y devolver su texto
    """
    linea = LineaPlantilla.query.get_or_404(linea_id)
    
    # Actualizar estadísticas
    linea.veces_usado += 1
    linea.ultima_vez_usado = db.func.now()
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'texto': linea.texto,
        'linea_id': linea.linea_id,
        'seccion_id': linea.seccion_id
    })


@bp.route('/guardar-plantilla/<int:protocolo_id>', methods=['POST'])
@login_required
def guardar_plantilla(protocolo_id):
    """
    Guardar plantilla generada por el usuario
    """
    protocolo = Protocolo.query.get_or_404(protocolo_id)
    data = request.get_json()
    
    # Buscar plantilla existente
    plantilla = PlantillaGenerada.query.filter_by(
        protocolo_id=protocolo_id,
        tipo_estudio='PAP',
        activo=True
    ).first()
    
    if not plantilla:
        plantilla = PlantillaGenerada(
            protocolo_id=protocolo_id,
            tipo_estudio='PAP',
            usuario_id=current_user.usuario_id,
            nombre=f"Plantilla PAP - {protocolo.numero_protocolo}"
        )
        db.session.add(plantilla)
    
    # Actualizar contenido
    plantilla.contenido = json.dumps(data.get('contenido', {}))
    plantilla.modificado_en = db.func.now()
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Plantilla guardada correctamente'
    })


@bp.route('/cargar-plantilla/<int:protocolo_id>')
@login_required
def cargar_plantilla(protocolo_id):
    """
    Cargar plantilla guardada
    """
    plantilla = PlantillaGenerada.query.filter_by(
        protocolo_id=protocolo_id,
        tipo_estudio='PAP',
        activo=True
    ).first()
    
    if not plantilla:
        return jsonify({
            'success': False,
            'message': 'No hay plantilla guardada'
        })
    
    try:
        contenido = json.loads(plantilla.contenido) if plantilla.contenido else {}
        return jsonify({
            'success': True,
            'contenido': contenido,
            'nombre': plantilla.nombre,
            'modificado': plantilla.modificado_en.isoformat() if plantilla.modificado_en else None
        })
    except:
        return jsonify({
            'success': False,
            'message': 'Error al cargar la plantilla'
        })


def construir_contexto_reporte(protocolo_id, lineas_json=None, disenio_id=None):
    from models.informe import ProtocoloLinea, DisenioInforme
    from models.protocolo import Protocolo
    from models.configuracion import Configuracion
    import json

    protocolo = Protocolo.query.get_or_404(protocolo_id)

    lineas = ProtocoloLinea.query.filter_by(protocolo_id=protocolo_id).order_by(
        ProtocoloLinea.seccion, ProtocoloLinea.orden
    ).all()

    lineas_por_seccion = {}
    for linea in lineas:
        lineas_por_seccion.setdefault(linea.seccion, []).append({
            'texto': linea.texto,
            'orden': linea.orden
        })

    if lineas_json:
        try:
            lineas_editor = json.loads(lineas_json) if isinstance(lineas_json, str) else lineas_json
            lineas_editor_por_seccion = {}
            for linea in lineas_editor:
                if isinstance(linea, dict):
                    seccion = linea.get('seccion', '')
                    if seccion:
                        lineas_editor_por_seccion.setdefault(seccion, []).append({
                            'texto': linea.get('texto', ''),
                            'orden': linea.get('orden', 0)
                        })
            if lineas_editor_por_seccion:
                lineas_por_seccion = lineas_editor_por_seccion
        except Exception:
            pass

    mapeo_secciones = {}
    orden_secciones = []
    subtitulo_reporte = ""
    titulo_reporte = ""

    if protocolo.tipo_estudio == 'PAP':
        titulo_reporte = "INFORME DE CITOLOGÍA CERVICOVAGINAL"
        subtitulo_reporte = "PAP - Papanicolaou"
        mapeo_secciones = {
            'DATOS_CLINICOS': 'DATOS CLÍNICOS',
            'EXTENDIDO': 'EXTENDIDO',
            'CELULAS_CONFORMACION': 'DESCRIPCIÓN CITOLÓGICA',
            'CELULAS_JUNTO_A': 'Junto a',
            'COMP_INFLAMATORIO': 'COMPONENTE INFLAMATORIO',
            'FLORA': 'Flora',
            'DIAGNOSTICO': 'DIAGNÓSTICO'
        }
        orden_secciones = ['DATOS_CLINICOS', 'EXTENDIDO', 'CELULAS_CONFORMACION', 'CELULAS_JUNTO_A', 'COMP_INFLAMATORIO', 'FLORA', 'DIAGNÓSTICO']
    elif protocolo.tipo_estudio == 'BIOPSIA':
        titulo_reporte = "INFORME DE ANATOMÍA PATOLÓGICA"
        subtitulo_reporte = "BIOPSIA"
        mapeo_secciones = {
            'MATERIAL_REMITIDO': 'MATERIAL REMITIDO',
            'DESCRIPCION_MACROSCOPICA': 'DESCRIPCIÓN MACROSCÓPICA',
            'DESCRIPCION_MICROSCOPICA': 'DESCRIPCIÓN MICROSCÓPICA',
            'DIAGNOSTICO': 'DIAGNÓSTICO'
        }
        orden_secciones = ['MATERIAL_REMITIDO', 'DESCRIPCION_MACROSCOPICA', 'DESCRIPCION_MICROSCOPICA', 'DIAGNÓSTICO']
    elif protocolo.tipo_estudio == 'CITOLOGÍA':
        titulo_reporte = "INFORME DE CITOLOGÍA"
        subtitulo_reporte = "CITOLOGÍA"
        mapeo_secciones = {
            'MATERIAL_REMITIDO': 'MATERIAL REMITIDO',
            'DESCRIPCION_MICROSCOPICA': 'DESCRIPCIÓN MICROSCÓPICA',
            'DIAGNOSTICO': 'DIAGNÓSTICO'
        }
        orden_secciones = ['MATERIAL_REMITIDO', 'DESCRIPCION_MICROSCOPICA', 'DIAGNÓSTICO']
    else:
        titulo_reporte = "INFORME"
        subtitulo_reporte = protocolo.tipo_estudio or ""

    if orden_secciones:
        lineas_por_seccion_ordenado = {}
        for seccion in orden_secciones:
            if seccion in lineas_por_seccion:
                lineas_por_seccion_ordenado[seccion] = lineas_por_seccion[seccion]
        for seccion, lineas_list in lineas_por_seccion.items():
            if seccion not in lineas_por_seccion_ordenado:
                lineas_por_seccion_ordenado[seccion] = lineas_list
        lineas_por_seccion = lineas_por_seccion_ordenado

    config = {
        'laboratorio_direccion': Configuracion.get('laboratorio_direccion', 'Pellegrini 630'),
        'laboratorio_telefono': Configuracion.get('laboratorio_telefono', '03462-15412472'),
        'laboratorio_ciudad': Configuracion.get('laboratorio_ciudad', '2600 - Venado Tuerto'),
        'laboratorio_nombre': Configuracion.get('laboratorio_nombre', 'LABORATORIO DE DIAGNÓSTICO HISTOPATOLÓGICO'),
        'mostrar_logo_reporte': Configuracion.get('mostrar_logo_reporte', 'true'),
        'reporte_footer': Configuracion.get('reporte_footer', '')
    }

    def _normalizar_tipo_estudio(valor: str) -> str:
        if not valor:
            return ''
        texto = unicodedata.normalize('NFD', valor.strip().upper())
        return ''.join(ch for ch in texto if unicodedata.category(ch) != 'Mn')

    tipo_estudio_normalizado = _normalizar_tipo_estudio(protocolo.tipo_estudio)

    disenio_config = None
    disenio_actual = None

    disenios_activos = DisenioInforme.query.filter_by(
        activo=True
    ).order_by(
        DisenioInforme.tipo_estudio,
        DisenioInforme.es_default.desc(),
        DisenioInforme.nombre
    ).all()

    disenios_filtrados = [
        d for d in disenios_activos
        if _normalizar_tipo_estudio(d.tipo_estudio) == tipo_estudio_normalizado
    ]

    if disenio_id:
        disenio_actual = next((d for d in disenios_filtrados if d.disenio_id == disenio_id), None)
        if disenio_actual:
            disenio_config = disenio_actual.get_configuracion()
    if not disenio_actual and disenios_filtrados:
        disenio_actual = next((d for d in disenios_filtrados if d.es_default), None) or disenios_filtrados[0]
    if disenio_actual and not disenio_config:
        disenio_config = disenio_actual.get_configuracion()

    if disenio_config:
        header_cfg = disenio_config.get('header', {}) or {}
        if header_cfg.get('titulo'):
            titulo_reporte = header_cfg['titulo']
        if header_cfg.get('subtitulo'):
            subtitulo_reporte = header_cfg['subtitulo']

    disenios_disponibles = []
    for d in sorted(disenios_filtrados, key=lambda x: (not x.es_default, x.nombre.lower())):
        disenios_disponibles.append({
            'disenio_id': d.disenio_id,
            'nombre': d.nombre,
            'es_default': d.es_default
        })

    estructura_visual = None
    if disenio_config and isinstance(disenio_config.get('estructura_visual'), list):
        try:
            estructura_visual = sorted(
                disenio_config['estructura_visual'],
                key=lambda x: x.get('orden', 999) if isinstance(x, dict) else getattr(x, 'orden', 999)
            )
        except Exception:
            estructura_visual = disenio_config['estructura_visual']

    return dict(
        protocolo=protocolo,
        lineas_por_seccion=lineas_por_seccion,
        mapeo_secciones=mapeo_secciones,
        titulo_reporte=titulo_reporte,
        subtitulo_reporte=subtitulo_reporte,
        config=config,
        disenio_config=disenio_config,
        disenio_actual=disenio_actual,
        disenios_disponibles=disenios_disponibles,
        estructura_visual=estructura_visual
    )


@bp.route('/preview-plantilla/<int:protocolo_id>')
@login_required
def preview_plantilla(protocolo_id):
    """Vista previa del protocolo con líneas guardadas (sistema nuevo)"""
    try:
        contexto = construir_contexto_reporte(
            protocolo_id,
            lineas_json=request.args.get('lineas'),
            disenio_id=request.args.get('disenio_id', type=int)
        )
        return render_template('plantillas_dinamicas/reporte_unificado.html', **contexto)
    except Exception as e:
        return f"Error generando vista previa: {str(e)}", 500


@bp.route('/exportar-plantilla/<int:protocolo_id>')
@login_required
def exportar_plantilla(protocolo_id):
    """
    Exportar plantilla como texto plano
    """
    protocolo = Protocolo.query.get_or_404(protocolo_id)
    plantilla = PlantillaGenerada.query.filter_by(
        protocolo_id=protocolo_id,
        tipo_estudio='PAP',
        activo=True
    ).first()
    
    if not plantilla or not plantilla.contenido:
        return "No hay plantilla para exportar"
    
    try:
        contenido = json.loads(plantilla.contenido)
        
        # Construir texto final
        texto_final = []
        texto_final.append(f"PROTOCOLO: {protocolo.numero_protocolo}")
        texto_final.append(f"PACIENTE: {protocolo.afiliado.nombre_completo}")
        texto_final.append(f"FECHA: {protocolo.fecha_ingreso.strftime('%d/%m/%Y')}")
        texto_final.append("")
        texto_final.append("DESCRIPCIÓN CITOLÓGICA:")
        texto_final.append("=" * 50)
        
        for seccion_id, linea_id in contenido.items():
            linea = LineaPlantilla.query.get(linea_id)
            seccion = SeccionPlantilla.query.get(seccion_id)
            if linea and seccion:
                texto_final.append(f"\n{seccion.nombre}:")
                texto_final.append(linea.texto)
        
        return "\n".join(texto_final)
    except:
        return "Error al exportar la plantilla"


@bp.route('/pap-moderno/<int:protocolo_id>')
@login_required
def editor_pap_moderno(protocolo_id):
    """
    Editor moderno de plantillas PAP con selector categorizado
    """
    protocolo = Protocolo.query.get_or_404(protocolo_id)
    es_medico = _usuario_es_medico()
    
    # Verificar que el protocolo sea de tipo PAP
    if protocolo.tipo_estudio != 'PAP':
        return jsonify({'error': 'Este editor es solo para protocolos PAP'}), 400
    
    # Obtener secciones organizadas por categorías
    secciones = SeccionPlantilla.query.order_by(SeccionPlantilla.orden).all()
    
    categorias = {}
    for seccion in secciones:
        categoria = seccion.codigo[0] if seccion.codigo else 'O'
        if categoria not in categorias:
            categorias[categoria] = {
                'nombre': get_categoria_nombre(categoria),
                'color': get_categoria_color(categoria),
                'icono': get_categoria_icono(categoria),
                'secciones': []
            }
        categorias[categoria]['secciones'].append({
            'seccion_id': seccion.seccion_id,
            'codigo': seccion.codigo,
            'nombre': seccion.nombre,
            'descripcion': seccion.descripcion,
            'lineas': []  # Se cargarán dinámicamente
        })
    
    return render_template('plantillas_dinamicas/editor_pap_moderno_v2.html', 
                         protocolo=protocolo, categorias=categorias, es_medico=es_medico)


def get_categoria_nombre(categoria):
    """Obtener nombre descriptivo de la categoría"""
    nombres = {
        'T': 'Trófico',
        'H': 'Hipotrófico', 
        'A': 'Atrófico',
        'I': 'Inflamatorio',
        'O': 'Otros'
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
        'T': 'bi-lightning',         # Trófoco - Energía
        'H': 'bi-heart',             # Hipotrófoco - Corazón
        'A': 'bi-circle',            # Atrófico - Círculo
        'I': 'bi-exclamation-triangle', # Inflamatorio - Alerta
        'O': 'bi-question-circle'    # Otros - Pregunta
    }
    return iconos.get(categoria, 'bi-question-circle')


# ===== RUTAS API PARA PLANTILLAS PAP DESDE BASE DE DATOS =====

@bp.route('/api/plantillas-pap')
def api_plantillas_pap():
    """Obtener todas las plantillas PAP disponibles"""
    try:
        from models.informe import PlantillaPap
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


@bp.route('/api/plantilla-pap/<codigo>')
def api_plantilla_pap(codigo):
    """Obtener plantilla PAP específica con sus líneas"""
    try:
        from models.informe import PlantillaPap, LineaPap, PlantillaLinea
        
        plantilla = PlantillaPap.query.filter_by(codigo=codigo, activo=True).first()
        if not plantilla:
            return jsonify({'error': 'Plantilla no encontrada'}), 404
        
        # Obtener líneas asociadas
        lineas = db.session.query(LineaPap, PlantillaLinea).join(
            PlantillaLinea, LineaPap.linea_id == PlantillaLinea.linea_plantilla_id
        ).filter(
            PlantillaLinea.plantilla_id == plantilla.plantilla_pap_id
        ).order_by(PlantillaLinea.orden).all()
        
        resultado = {
            'codigo': plantilla.codigo,
            'descripcion': plantilla.descripcion,
            'categoria': plantilla.categoria,
            'lineas': []
        }
        
        for linea, plantilla_linea in lineas:
            resultado['lineas'].append({
                'lineas_pap_id': linea.linea_id,
                'categoria': linea.categoria,
                'texto': linea.texto,
                'orden': plantilla_linea.orden
            })
        
        return jsonify(resultado)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/lineas-pap/<categoria>')
def api_lineas_pap_categoria(categoria):
    """Obtener líneas disponibles para una categoría específica"""
    try:
        from models.informe import LineaPap
        
        lineas = LineaPap.query.filter_by(categoria=categoria, activo=True).order_by(LineaPap.orden).all()
        
        resultado = []
        for linea in lineas:
            resultado.append({
                'lineas_pap_id': linea.linea_id,
                'texto': linea.texto,
                'orden': linea.orden
            })
        
        return jsonify({'lineas': resultado})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/plantillas/personalizadas/<tipo_estudio>', methods=['GET', 'POST'])
@login_required
def api_plantillas_personalizadas(tipo_estudio):
    """
    Gestionar plantillas personalizadas para un tipo de estudio (PAP, BIOPSIA, etc.)
    Reutiliza plantillas_generadas almacenando el contenido como JSON.
    """
    tipo_estudio_normalizado = (tipo_estudio or '').strip().upper()
    if tipo_estudio_normalizado == 'PAP':
        tipo_template = 'PAP_CUSTOM'
    elif tipo_estudio_normalizado == 'BIOPSIA':
        tipo_template = 'BIOPSIA_CUSTOM'
    else:
        return jsonify({'success': False, 'error': 'Tipo de estudio no soportado'}), 400

    try:
        if request.method == 'GET':
            plantillas = PlantillaGenerada.query.filter_by(
                tipo_estudio=tipo_template,
                activo=True
            ).order_by(PlantillaGenerada.nombre.asc()).all()

            resultado = []
            for plantilla in plantillas:
                try:
                    contenido = json.loads(plantilla.contenido) if plantilla.contenido else {}
                except Exception:
                    contenido = {}
                resultado.append({
                    'nombre': plantilla.nombre,
                    'lineas': contenido,
                    'modificado_en': plantilla.modificado_en.isoformat() if plantilla.modificado_en else None,
                    'creado_por': plantilla.usuario_id
                })

            return jsonify({'success': True, 'plantillas': resultado})

        data = request.get_json(silent=True) or {}
        nombre = (data.get('nombre') or '').strip()
        lineas = data.get('lineas') or {}
        sobrescribir = bool(data.get('sobrescribir', False))

        if not nombre:
            return jsonify({'success': False, 'error': 'El nombre de la plantilla es obligatorio.'}), 400

        # Normalizar contenido
        lineas_normalizadas = {}
        for seccion, textos in lineas.items():
            if not textos:
                continue
            clave = (seccion or '').strip().upper()
            if not clave:
                continue
            valores = []
            for texto in textos:
                txt = (texto or '').strip()
                if txt:
                    valores.append(txt)
            if valores:
                lineas_normalizadas[clave] = valores

        plantilla = PlantillaGenerada.query.filter_by(
            tipo_estudio=tipo_template,
            nombre=nombre
        ).first()

        if plantilla and not sobrescribir:
            return jsonify({'success': False, 'error': 'exists'})

        if not plantilla:
            plantilla = PlantillaGenerada(
                protocolo_id=None,
                tipo_estudio=tipo_template,
                usuario_id=current_user.usuario_id,
                nombre=nombre
            )
            db.session.add(plantilla)

        plantilla.contenido = json.dumps(lineas_normalizadas, ensure_ascii=False)
        plantilla.activo = True
        plantilla.usuario_id = current_user.usuario_id

        asignada_a_boton = False
        
        # Si el nombre coincide con un código de botón existente, crear/actualizar la plantilla estándar
        if tipo_estudio_normalizado == 'PAP':
            boton_existente = ConfiguracionBotones.query.filter_by(
                tipo_estudio='PAP',
                codigo_boton=nombre.upper(),
                activo=True
            ).first()
            
            if boton_existente:
                # Buscar o crear la plantilla estándar asociada
                from models.informe import PlantillaPap, LineaPap, PlantillaLinea
                
                plantilla_std = PlantillaPap.query.filter_by(
                    codigo=nombre.upper(),
                    activo=True
                ).first()
                
                if not plantilla_std:
                    # Crear nueva plantilla estándar
                    plantilla_std = PlantillaPap(
                        categoria='PERSONALIZADA',
                        codigo=nombre.upper(),
                        descripcion=f'Plantilla personalizada: {nombre}',
                        activo=True
                    )
                    db.session.add(plantilla_std)
                    db.session.flush()  # Para obtener el ID
                
                # Eliminar líneas anteriores asociadas
                PlantillaLinea.query.filter_by(plantilla_id=plantilla_std.plantilla_pap_id).delete()
                
                # Crear/actualizar líneas en LineaPap y asociarlas
                orden_global = 0
                for categoria, textos in lineas_normalizadas.items():
                    for idx, texto in enumerate(textos):
                        # Buscar si existe la línea
                        linea_existente = LineaPap.query.filter_by(
                            categoria=categoria,
                            texto=texto,
                            activo=True
                        ).first()
                        
                        if not linea_existente:
                            # Crear nueva línea
                            linea_existente = LineaPap(
                                categoria=categoria,
                                texto=texto,
                                orden=orden_global,
                                activo=True
                            )
                            db.session.add(linea_existente)
                            db.session.flush()
                        
                        # Asociar línea a plantilla
                        plantilla_linea = PlantillaLinea(
                            plantilla_id=plantilla_std.plantilla_pap_id,
                            linea_plantilla_id=linea_existente.linea_id,
                            orden=orden_global
                        )
                        db.session.add(plantilla_linea)
                        orden_global += 1
                
                asignada_a_boton = True

        db.session.commit()

        return jsonify({'success': True, 'asignada_a_boton': asignada_a_boton})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/plantillas/personalizadas/<tipo_estudio>/<nombre>', methods=['DELETE'])
@login_required
def api_borrar_plantilla_personalizada(tipo_estudio, nombre):
    """
    Borrar una plantilla personalizada por nombre
    """
    tipo_estudio_normalizado = (tipo_estudio or '').strip().upper()
    if tipo_estudio_normalizado == 'PAP':
        tipo_template = 'PAP_CUSTOM'
    elif tipo_estudio_normalizado == 'BIOPSIA':
        tipo_template = 'BIOPSIA_CUSTOM'
    else:
        return jsonify({'success': False, 'error': 'Tipo de estudio no soportado'}), 400

    try:
        nombre_normalizado = (nombre or '').strip()
        if not nombre_normalizado:
            return jsonify({'success': False, 'error': 'El nombre de la plantilla es obligatorio.'}), 400

        plantilla = PlantillaGenerada.query.filter_by(
            tipo_estudio=tipo_template,
            nombre=nombre_normalizado,
            activo=True
        ).first()

        if not plantilla:
            return jsonify({'success': False, 'error': 'Plantilla no encontrada'}), 404

        # Verificar permisos: solo el usuario que la creó o un administrador puede borrarla
        if plantilla.usuario_id != current_user.usuario_id:
            # Verificar si el usuario es administrador
            from models.usuario import Rol
            rol = Rol.query.get(current_user.rol_id) if current_user.rol_id else None
            if not rol or rol.nombre.upper() != 'ADMINISTRADOR':
                return jsonify({'success': False, 'error': 'No tiene permisos para borrar esta plantilla'}), 403

        # Si la plantilla personalizada está asignada a un botón, eliminar también la plantilla estándar asociada
        if tipo_estudio_normalizado == 'PAP':
            from models.informe import PlantillaPap, PlantillaLinea
            
            # Buscar plantilla estándar asociada por código
            plantilla_std = PlantillaPap.query.filter_by(
                codigo=nombre_normalizado.upper(),
                activo=True
            ).first()
            
            if plantilla_std:
                # Eliminar relaciones PlantillaLinea (las líneas en LineaPap se mantienen por si otras plantillas las usan)
                PlantillaLinea.query.filter_by(plantilla_id=plantilla_std.plantilla_pap_id).delete()
                
                # Marcar la plantilla estándar como inactiva
                plantilla_std.activo = False

        # Soft delete: marcar como inactiva
        plantilla.activo = False
        db.session.commit()

        return jsonify({'success': True, 'message': 'Plantilla borrada correctamente'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ===== RUTAS API PARA PLANTILLAS Y LÍNEAS DE BIOPSIAS =====

@bp.route('/api/lineas-biopsias/<seccion>')
@login_required
def api_lineas_biopsias_seccion(seccion):
    """Obtener líneas disponibles para una sección específica de Biopsias"""
    try:
        from models.informe import LineaBiopsia
        
        lineas = LineaBiopsia.query.filter_by(seccion=seccion.upper(), activo=True).order_by(LineaBiopsia.orden).all()
        
        resultado = []
        for linea in lineas:
            resultado.append({
                'linea_id': linea.linea_id,
                'texto': linea.texto,
                'orden': linea.orden
            })
        
        return jsonify({'lineas': resultado})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/plantilla-biopsias/<nombre>')
@login_required
def api_plantilla_biopsias_nombre(nombre):
    """Obtener plantilla completa de Biopsias por nombre con todas sus líneas por sección"""
    try:
        from models.informe import PlantillaBiopsia, LineaBiopsia, PlantillaLineaBiopsia
        
        # Obtener todas las entradas de esta plantilla (una por sección)
        plantillas = PlantillaBiopsia.query.filter_by(
            nombre=nombre,
            activo=True
        ).all()
        
        if not plantillas:
            return jsonify({'error': 'Plantilla no encontrada'}), 404
        
        # Agrupar por sección y obtener líneas asociadas
        resultado = {
            'nombre': nombre,
            'secciones': {}
        }
        
        for plantilla in plantillas:
            # Obtener líneas asociadas a esta plantilla+sección
            lineas = db.session.query(LineaBiopsia, PlantillaLineaBiopsia).join(
                PlantillaLineaBiopsia, LineaBiopsia.linea_id == PlantillaLineaBiopsia.linea_plantilla_id
            ).filter(
                PlantillaLineaBiopsia.plantilla_id == plantilla.plantilla_biopsia_id
            ).order_by(PlantillaLineaBiopsia.orden).all()
            
            resultado['secciones'][plantilla.seccion] = [
                {
                    'linea_id': linea.linea_id,
                    'texto': linea.texto,
                    'orden': plantilla_linea.orden
                }
                for linea, plantilla_linea in lineas
            ]
        
        return jsonify(resultado)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/plantillas-biopsias')
@login_required
def api_listar_plantillas_biopsias():
    """Listar todas las plantillas de Biopsias disponibles"""
    try:
        from models.informe import PlantillaBiopsia
        
        plantillas = PlantillaBiopsia.query.filter_by(activo=True).order_by(
            PlantillaBiopsia.nombre, PlantillaBiopsia.seccion
        ).all()
        
        # Agrupar por nombre
        plantillas_por_nombre = {}
        for p in plantillas:
            if p.nombre not in plantillas_por_nombre:
                plantillas_por_nombre[p.nombre] = []
            plantillas_por_nombre[p.nombre].append(p.seccion)
        
        resultado = [
            {
                'nombre': nombre,
                'secciones': secciones
            }
            for nombre, secciones in plantillas_por_nombre.items()
        ]
        
        return jsonify({'plantillas': resultado})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ===== RUTAS API PARA GESTIONAR LÍNEAS DE PROTOCOLOS =====

@bp.route('/api/protocolo/<int:protocolo_id>/lineas')
@login_required
def api_obtener_lineas_protocolo(protocolo_id):
    """Obtener todas las líneas de un protocolo específico"""
    try:
        from models.informe import ProtocoloLinea
        
        lineas = ProtocoloLinea.query.filter_by(protocolo_id=protocolo_id).order_by(
            ProtocoloLinea.seccion, ProtocoloLinea.orden
        ).all()
        
        # Agrupar por sección
        resultado = {}
        for linea in lineas:
            if linea.seccion not in resultado:
                resultado[linea.seccion] = []
            resultado[linea.seccion].append({
                'protocolo_linea_id': linea.protocolo_linea_id,
                'texto': linea.texto,
                'orden': linea.orden,
                'creado_en': linea.creado_en.isoformat() if linea.creado_en else None
            })
        
        return jsonify({'lineas_por_seccion': resultado})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/protocolo/<int:protocolo_id>/lineas', methods=['POST'])
@login_required
def api_agregar_linea_protocolo(protocolo_id):
    """Agregar nueva línea a un protocolo"""
    try:
        from models.informe import ProtocoloLinea
        
        data = request.get_json()
        seccion = data.get('seccion')
        texto = data.get('texto')
        
        if not seccion or not texto:
            return jsonify({'error': 'Sección y texto son requeridos'}), 400
        
        # Obtener el siguiente orden para la sección
        ultima_linea = ProtocoloLinea.query.filter_by(
            protocolo_id=protocolo_id, seccion=seccion
        ).order_by(ProtocoloLinea.orden.desc()).first()
        
        siguiente_orden = (ultima_linea.orden + 1) if ultima_linea else 1
        
        # Crear nueva línea
        nueva_linea = ProtocoloLinea(
            protocolo_id=protocolo_id,
            seccion=seccion,
            texto=texto,
            orden=siguiente_orden
        )
        
        db.session.add(nueva_linea)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'protocolo_linea_id': nueva_linea.protocolo_linea_id,
            'message': 'Línea agregada correctamente'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/api/protocolo/lineas/<int:linea_id>', methods=['PUT'])
@login_required
def api_editar_linea_protocolo(linea_id):
    """Editar línea existente de un protocolo"""
    try:
        from models.informe import ProtocoloLinea
        
        data = request.get_json()
        nuevo_texto = data.get('texto')
        
        if not nuevo_texto:
            return jsonify({'error': 'Texto es requerido'}), 400
        
        linea = ProtocoloLinea.query.get_or_404(linea_id)
        linea.texto = nuevo_texto
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Línea editada correctamente'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/api/protocolo/lineas/<int:linea_id>', methods=['DELETE'])
@login_required
def api_eliminar_linea_protocolo(linea_id):
    """Eliminar línea de un protocolo"""
    try:
        from models.informe import ProtocoloLinea
        
        linea = ProtocoloLinea.query.get_or_404(linea_id)
        protocolo_id = linea.protocolo_id
        seccion = linea.seccion
        
        db.session.delete(linea)
        db.session.commit()
        
        # Reordenar las líneas restantes de la misma sección
        lineas_restantes = ProtocoloLinea.query.filter_by(
            protocolo_id=protocolo_id, seccion=seccion
        ).order_by(ProtocoloLinea.orden).all()
        
        for i, linea_restante in enumerate(lineas_restantes, 1):
            linea_restante.orden = i
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Línea eliminada correctamente'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/api/protocolo/<int:protocolo_id>/guardar-lineas', methods=['POST'])
@login_required
def api_guardar_lineas_protocolo(protocolo_id):
    """Guardar todas las líneas de un protocolo"""
    try:
        from models.informe import ProtocoloLinea
        
        # Verificar si es protocolo de prueba
        protocolo = Protocolo.query.get_or_404(protocolo_id)
        if protocolo.es_prueba:
            return jsonify({
                'success': False,
                'error': 'Los protocolos de prueba no se pueden guardar. Use "Guardar como plantilla" en su lugar.'
            }), 400
        
        data = request.get_json()
        lineas = data.get('lineas', [])
        
        if not lineas:
            return jsonify({
                'success': False,
                'error': 'No se proporcionaron líneas para guardar'
            }), 400
        
        # Eliminar líneas existentes del protocolo
        ProtocoloLinea.query.filter_by(protocolo_id=protocolo_id).delete()
        
        # Insertar nuevas líneas
        for linea_data in lineas:
            nueva_linea = ProtocoloLinea(
                protocolo_id=protocolo_id,
                seccion=linea_data['seccion'],
                texto=linea_data['texto'],
                orden=linea_data['orden']
            )
            db.session.add(nueva_linea)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Se guardaron {len(lineas)} líneas correctamente'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ===== RUTAS API PARA EDITOR MODERNO V2 =====

@bp.route('/api/editor-moderno/guardar', methods=['POST'])
@login_required
def api_guardar_editor_moderno():
    """Guardar contenido del editor moderno"""
    try:
        from models.informe import ProtocoloLinea
        
        data = request.get_json()
        protocolo_id = data.get('protocolo_id')
        seccion = data.get('seccion', 'general')
        contenido = data.get('contenido', '')
        
        if not protocolo_id:
            return jsonify({'success': False, 'error': 'ID de protocolo requerido'}), 400
        
        # Verificar si es protocolo de prueba
        protocolo = Protocolo.query.get(protocolo_id)
        if protocolo and protocolo.es_prueba:
            return jsonify({
                'success': False,
                'error': 'Los protocolos de prueba no se pueden guardar. Use "Guardar como plantilla" en su lugar.'
            }), 400
        
        # Eliminar líneas existentes de esta sección
        ProtocoloLinea.query.filter_by(
            protocolo_id=protocolo_id,
            seccion=seccion
        ).delete()
        
        # Crear nueva línea con el contenido
        if contenido.strip():
            nueva_linea = ProtocoloLinea(
                protocolo_id=protocolo_id,
                seccion=seccion,
                texto=contenido,
                orden=1
            )
            db.session.add(nueva_linea)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Contenido guardado correctamente'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/editor-moderno/cargar/<int:protocolo_id>')
@login_required
def api_cargar_editor_moderno(protocolo_id):
    """Cargar contenido guardado del editor moderno"""
    try:
        from models.informe import ProtocoloLinea
        
        lineas = ProtocoloLinea.query.filter_by(
            protocolo_id=protocolo_id
        ).order_by(ProtocoloLinea.seccion, ProtocoloLinea.orden).all()
        
        contenido_por_seccion = {}
        for linea in lineas:
            if linea.seccion not in contenido_por_seccion:
                contenido_por_seccion[linea.seccion] = []
            contenido_por_seccion[linea.seccion].append(linea.texto)
        
        # Combinar líneas de cada sección
        resultado = {}
        for seccion, textos in contenido_por_seccion.items():
            resultado[seccion] = '\n'.join(textos)
        
        return jsonify({
            'success': True,
            'contenido': resultado
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/editor-moderno/plantilla/<int:seccion_id>')
@login_required
def api_obtener_plantilla_moderna(seccion_id):
    """Obtener plantilla específica para el editor moderno"""
    try:
        seccion = SeccionPlantilla.query.get(seccion_id)
        
        if not seccion:
            return jsonify({'success': False, 'error': 'Sección no encontrada'}), 404
        
        # Obtener líneas de la sección
        lineas = []
        if hasattr(seccion, 'lineas'):
            lineas = [{
                'linea_id': linea.linea_id,
                'texto': linea.texto,
                'orden': linea.orden
            } for linea in seccion.lineas if linea.activo]
        
        return jsonify({
            'success': True,
            'seccion': {
                'seccion_id': seccion.seccion_id,
                'codigo': seccion.codigo,
                'nombre': seccion.nombre,
                'descripcion': seccion.descripcion,
                'lineas': lineas
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ===== EDITOR BIOPSIAS V2 =====
@bp.route('/biopsias/<int:protocolo_id>')
@login_required
def editor_biopsias_v2(protocolo_id):
    """Editor simple de Biopsias v2 con 4 secciones y guardado por renglones"""
    protocolo = Protocolo.query.get_or_404(protocolo_id)
    # Secciones base (si existen en DB se podrían leer, pero aquí las definimos)
    secciones = [
        {'seccion_id': 8001, 'codigo': 'DESCRIPCION_MACROSCOPICA', 'nombre': 'Descripción Macroscópica', 'orden': 1},
        {'seccion_id': 8002, 'codigo': 'DESCRIPCION_MICROSCOPICA', 'nombre': 'Descripción Microscópica', 'orden': 2},
        {'seccion_id': 8003, 'codigo': 'MATERIAL_REMITIDO', 'nombre': 'Material Remitido', 'orden': 3},
        {'seccion_id': 8004, 'codigo': 'DIAGNOSTICO', 'nombre': 'Diagnóstico', 'orden': 4},
    ]
    es_medico = _usuario_es_medico()
    rol_usuario = getattr(current_user.rol, 'nombre', '') if current_user.is_authenticated else ''
    return render_template(
        'biopsias/editor_biopsias_v2.html',
        protocolo=protocolo,
        secciones=secciones,
        es_medico=es_medico,
        rol_usuario=rol_usuario
    )


@bp.route('/citologia/<int:protocolo_id>')
@login_required
def editor_citologia(protocolo_id):
    """Editor simple de Citologías sin plantillas, solo edición de texto por sección"""
    protocolo = Protocolo.query.get_or_404(protocolo_id)
    es_medico = _usuario_es_medico()
    if protocolo.tipo_estudio != 'CITOLOGÍA':
        flash('Este editor es solo para protocolos de Citologías.', 'error')
        return redirect(url_for('protocolos.ver', id=protocolo_id))
    
    secciones = [
        {'seccion_id': 9002, 'codigo': 'MATERIAL_REMITIDO', 'nombre': 'Material Remitido', 'orden': 1},
        {'seccion_id': 9003, 'codigo': 'DESCRIPCION_MICROSCOPICA', 'nombre': 'Descr. Microscópica', 'orden': 2},
        {'seccion_id': 9004, 'codigo': 'DIAGNOSTICO', 'nombre': 'Diagnóstico', 'orden': 3},
    ]
    
    # Opciones de tipo de papel
    tipos_papel = [
        {'id': 1, 'nombre': 'Papel Membretado c/datos'},
        {'id': 2, 'nombre': 'Membretado'},
        {'id': 3, 'nombre': 'Sanatorio Castelli'},
        {'id': 4, 'nombre': 'Sin Membrete'},
    ]
    
    return render_template(
        'citologia/editor_citologia.html',
        protocolo=protocolo,
        secciones=secciones,
        tipos_papel=tipos_papel,
        es_medico=es_medico
    )


# ===== RUTA API DEDICADA PARA EDITOR V2 (guardar por sección) =====
@bp.route('/api/editor-v2/guardar', methods=['POST'])
@login_required
def api_guardar_editor_v2():
    """Guardar (reemplazando) las líneas de una sección del protocolo en protocolo_lineas."""
    try:
        from models.informe import ProtocoloLinea
        data = request.get_json(silent=True) or {}
        protocolo_id = data.get('protocolo_id')
        seccion = (data.get('seccion') or '').strip()
        lineas = data.get('lineas') or []

        if not protocolo_id or not seccion:
            return jsonify({'success': False, 'error': 'Datos incompletos'}), 400
        
        # Verificar si es protocolo de prueba
        protocolo = Protocolo.query.get(protocolo_id)
        if protocolo and protocolo.es_prueba:
            return jsonify({
                'success': False,
                'error': 'Los protocolos de prueba no se pueden guardar. Use "Guardar como plantilla" en su lugar.'
            }), 400

        # Normalizar
        lineas_limpias = []
        for txt in lineas:
            if not txt:
                continue
            t = str(txt).strip()
            if t:
                lineas_limpias.append(t)

        # Reemplazar existentes
        ProtocoloLinea.query.filter_by(protocolo_id=protocolo_id, seccion=seccion).delete()

        # Insertar ordenadas
        for i, t in enumerate(lineas_limpias, start=1):
            db.session.add(ProtocoloLinea(
                protocolo_id=protocolo_id,
                seccion=seccion,
                texto=t,
                orden=i
            ))

        db.session.commit()
        return jsonify({'success': True, 'insertadas': len(lineas_limpias)})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

