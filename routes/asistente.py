"""
Rutas para el Asistente Inteligente con integración Claude API
"""
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from extensions import db
from models.asistente import CasoHistorico, PlantillaTexto, SugerenciaIA
from models.protocolo import Protocolo
from models.plantilla_dinamica import SeccionPlantilla, LineaPlantilla
from models.prestador import Prestador
from models.usuario import Usuario
from models.auditoria import Auditoria
from services.claude_client import claude_client
from services.gemini_client import gemini_client
from sqlalchemy import or_, func, desc
import re
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('asistente', __name__, url_prefix='/asistente')


@bp.route('/buscar-casos', methods=['POST'])
@login_required
def buscar_casos():
    """
    Buscar casos similares en el histórico
    """
    data = request.get_json()
    termino = data.get('termino', '').strip()
    tipo_estudio = data.get('tipo_estudio', '')
    limite = data.get('limite', 10)
    
    if len(termino) < 3:
        return jsonify({
            'success': False,
            'message': 'Escribe al menos 3 caracteres'
        })
    
    # Construir query
    query = CasoHistorico.query.filter(CasoHistorico.activo == True)
    
    # Filtrar por tipo si se especifica
    if tipo_estudio:
        query = query.filter(CasoHistorico.tipo_estudio == tipo_estudio)
    
    # Buscar en múltiples campos
    palabras = termino.split()
    filtros = []
    
    for palabra in palabras:
        if len(palabra) >= 3:
            filtros.append(
                or_(
                    CasoHistorico.descripcion_microscopica.ilike(f'%{palabra}%'),
                    CasoHistorico.descripcion.ilike(f'%{palabra}%'),
                    CasoHistorico.diagnostico.ilike(f'%{palabra}%'),
                    CasoHistorico.categoria.ilike(f'%{palabra}%')
                )
            )
    
    if filtros:
        query = query.filter(or_(*filtros))
    
    # Obtener resultados
    casos = query.order_by(desc(CasoHistorico.caso_id)).limit(limite).all()
    
    # Formatear resultados
    resultados = []
    for caso in casos:
        # Determinar qué mostrar según el tipo
        if caso.tipo_estudio == 'BIOPSIA':
            descripcion_preview = caso.descripcion_microscopica[:200] if caso.descripcion_microscopica else ''
        else:
            descripcion_preview = caso.descripcion[:200] if caso.descripcion else ''
        
        diagnostico_preview = caso.diagnostico[:150] if caso.diagnostico else ''
        
        resultados.append({
            'caso_id': caso.caso_id,
            'protocolo': caso.protocolo_original,
            'tipo': caso.tipo_estudio,
            'categoria': caso.categoria,
            'descripcion_preview': descripcion_preview + '...' if len(descripcion_preview) >= 200 else descripcion_preview,
            'diagnostico_preview': diagnostico_preview + '...' if len(diagnostico_preview) >= 150 else diagnostico_preview,
            'descripcion_completa': caso.descripcion_microscopica or caso.descripcion,
            'diagnostico_completo': caso.diagnostico
        })
    
    return jsonify({
        'success': True,
        'total': len(resultados),
        'casos': resultados
    })


@bp.route('/plantillas/<tipo_estudio>')
@login_required
def obtener_plantillas(tipo_estudio):
    """
    Obtener plantillas por tipo de estudio
    """
    seccion = request.args.get('seccion', '')
    
    query = PlantillaTexto.query.filter_by(
        tipo_estudio=tipo_estudio.upper(),
        activo=True
    )
    
    if seccion:
        query = query.filter_by(seccion=seccion)
    
    plantillas = query.order_by(
        PlantillaTexto.veces_usado.desc(),
        PlantillaTexto.orden
    ).all()
    
    # Agrupar por sección
    plantillas_agrupadas = {}
    for plantilla in plantillas:
        seccion_key = plantilla.seccion
        if seccion_key not in plantillas_agrupadas:
            plantillas_agrupadas[seccion_key] = []
        
        plantillas_agrupadas[seccion_key].append({
            'id': plantilla.plantilla_id,
            'nombre': plantilla.nombre,
            'texto': plantilla.texto,
            'veces_usado': plantilla.veces_usado
        })
    
    return jsonify({
        'success': True,
        'plantillas': plantillas_agrupadas
    })


@bp.route('/usar-plantilla/<int:plantilla_id>', methods=['POST'])
@login_required
def usar_plantilla(plantilla_id):
    """
    Registrar uso de una plantilla
    """
    plantilla = PlantillaTexto.query.get_or_404(plantilla_id)
    
    # Actualizar estadísticas
    plantilla.veces_usado += 1
    plantilla.ultima_vez_usado = db.func.now()
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'texto': plantilla.texto
    })


@bp.route('/top-diagnosticos/<tipo_estudio>')
@login_required
def top_diagnosticos(tipo_estudio):
    """
    Obtener diagnósticos más frecuentes por tipo
    """
    categoria = request.args.get('categoria', '')
    limite = request.args.get('limite', 20, type=int)
    
    query = db.session.query(
        CasoHistorico.diagnostico,
        func.count(CasoHistorico.caso_id).label('frecuencia')
    ).filter(
        CasoHistorico.tipo_estudio == tipo_estudio.upper(),
        CasoHistorico.activo == True
    )
    
    if categoria:
        query = query.filter(CasoHistorico.categoria == categoria)
    
    resultados = query.group_by(
        CasoHistorico.diagnostico
    ).order_by(
        desc('frecuencia')
    ).limit(limite).all()
    
    diagnosticos = [{
        'diagnostico': diag[0][:200] + '...' if len(diag[0]) > 200 else diag[0],
        'diagnostico_completo': diag[0],
        'frecuencia': diag[1]
    } for diag in resultados]
    
    return jsonify({
        'success': True,
        'diagnosticos': diagnosticos
    })


@bp.route('/categorias/<tipo_estudio>')
@login_required
def obtener_categorias(tipo_estudio):
    """
    Obtener categorías disponibles por tipo de estudio
    """
    categorias = db.session.query(
        CasoHistorico.categoria,
        func.count(CasoHistorico.caso_id).label('total')
    ).filter(
        CasoHistorico.tipo_estudio == tipo_estudio.upper(),
        CasoHistorico.activo == True
    ).group_by(
        CasoHistorico.categoria
    ).order_by(
        desc('total')
    ).all()
    
    resultado = [{
        'categoria': cat[0],
        'nombre_mostrar': cat[0].replace('_', ' ').title(),
        'total_casos': cat[1]
    } for cat in categorias]
    
    return jsonify({
        'success': True,
        'categorias': resultado
    })


@bp.route('/registrar-sugerencia', methods=['POST'])
@login_required
def registrar_sugerencia():
    """
    Registrar una sugerencia usada (para análisis futuro)
    """
    data = request.get_json()
    
    sugerencia = SugerenciaIA(
        usuario_id=current_user.usuario_id,
        protocolo_id=data.get('protocolo_id'),
        tipo_sugerencia=data.get('tipo_sugerencia'),
        seccion=data.get('seccion'),
        texto_original=data.get('texto_original'),
        texto_sugerido=data.get('texto_sugerido'),
        texto_final=data.get('texto_final'),
        aceptada=data.get('aceptada', False)
    )
    
    db.session.add(sugerencia)
    db.session.commit()
    
    return jsonify({'success': True})


@bp.route('/estadisticas')
@login_required
def estadisticas():
    """
    Estadísticas del asistente
    """
    stats = {
        'total_casos': CasoHistorico.query.filter_by(activo=True).count(),
        'biopsias': CasoHistorico.query.filter_by(tipo_estudio='BIOPSIA', activo=True).count(),
        'citologias': CasoHistorico.query.filter_by(tipo_estudio='CITOLOGIA', activo=True).count(),
        'pap': CasoHistorico.query.filter_by(tipo_estudio='PAP', activo=True).count(),
        'plantillas': PlantillaTexto.query.filter_by(activo=True).count(),
        'sugerencias_usadas': SugerenciaIA.query.filter_by(aceptada=True).count()
    }
    
    return jsonify({
        'success': True,
        'estadisticas': stats
    })


# ============================================================================
# NUEVAS RUTAS CON INTEGRACIÓN CLAUDE API
# ============================================================================

@bp.route('/claude/sugerir-plantillas', methods=['POST'])
@login_required
def claude_sugerir_plantillas():
    """
    Sugerir plantillas usando Claude API
    """
    try:
        data = request.get_json()
        protocolo_id = data.get('protocolo_id')
        seccion_actual = data.get('seccion_actual', '')
        plantillas_seleccionadas = data.get('plantillas_seleccionadas', [])
        
        # Obtener protocolo
        protocolo = Protocolo.query.get_or_404(protocolo_id)
        
        # Preparar contexto para Claude
        contexto = {
            'datos_clinicos': protocolo.datos_clinicos or '',
            'edad': protocolo.afiliado.edad if protocolo.afiliado else None,
            'antecedentes': '',  # Se puede expandir
            'seccion_actual': seccion_actual,
            'plantillas_seleccionadas': plantillas_seleccionadas
        }
        
        # Verificar si Claude está configurado
        if not claude_client.is_configured():
            return jsonify({
                'success': False,
                'error': 'Claude API no está configurada',
                'sugerencias': []
            })
        
        # Obtener sugerencias de Claude
        resultado = claude_client.sugerir_plantillas_pap(contexto)
        
        # Mapear sugerencias a plantillas reales
        sugerencias_mapeadas = []
        if resultado.get('sugerencias'):
            for sugerencia in resultado['sugerencias']:
                categoria = sugerencia.get('categoria', '')
                codigo = sugerencia.get('codigo', '')
                
                # Buscar plantillas que coincidan
                secciones = SeccionPlantilla.query.filter(
                    SeccionPlantilla.codigo.like(f'{categoria}%')
                ).all()
                
                for seccion in secciones:
                    lineas = LineaPlantilla.query.filter_by(seccion_id=seccion.seccion_id).all()
                    for linea in lineas:
                        linea_codigo = f"L{linea.linea_id}"  # Generar código automático
                        if codigo.lower() in linea_codigo.lower():
                            sugerencias_mapeadas.append({
                                'linea_id': linea.linea_id,
                                'codigo': linea_codigo,
                                'texto': linea.texto,
                                'seccion': seccion.nombre,
                                'categoria': categoria,
                                'razon': sugerencia.get('razon', ''),
                                'confianza': resultado.get('confianza', 0.5)
                            })
        
        return jsonify({
            'success': True,
            'sugerencias': sugerencias_mapeadas,
            'confianza': resultado.get('confianza', 0.5),
            'observaciones': resultado.get('observaciones', ''),
            'claude_disponible': True
        })
        
    except Exception as e:
        logger.error(f"Error en claude_sugerir_plantillas: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'sugerencias': [],
            'claude_disponible': claude_client.is_configured()
        })


@bp.route('/claude/analizar-caso', methods=['POST'])
@login_required
def claude_analizar_caso():
    """
    Analizar caso completo usando Claude API
    """
    try:
        data = request.get_json()
        protocolo_id = data.get('protocolo_id')
        
        # Obtener protocolo
        protocolo = Protocolo.query.get_or_404(protocolo_id)
        
        # Preparar datos del caso
        datos_caso = {
            'paciente': protocolo.afiliado.nombre if protocolo.afiliado else 'No especificado',
            'edad': protocolo.afiliado.edad if protocolo.afiliado else None,
            'datos_clinicos': protocolo.datos_clinicos or '',
            'antecedentes': '',  # Se puede expandir
            'hallazgos': ''  # Se puede expandir
        }
        
        # Verificar si Claude está configurado
        if not claude_client.is_configured():
            return jsonify({
                'success': False,
                'error': 'Claude API no está configurada',
                'analisis': {}
            })
        
        # Analizar con Claude
        resultado = claude_client.analizar_caso_completo(datos_caso)
        
        return jsonify({
            'success': True,
            'analisis': resultado,
            'claude_disponible': True
        })
        
    except Exception as e:
        logger.error(f"Error en claude_analizar_caso: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'analisis': {},
            'claude_disponible': claude_client.is_configured()
        })


@bp.route('/claude/generar-informe', methods=['POST'])
@login_required
def claude_generar_informe():
    """
    Generar informe usando Claude API
    """
    try:
        data = request.get_json()
        protocolo_id = data.get('protocolo_id')
        plantillas_seleccionadas = data.get('plantillas_seleccionadas', [])
        
        # Obtener protocolo
        protocolo = Protocolo.query.get_or_404(protocolo_id)
        
        # Preparar contexto
        contexto = {
            'paciente': protocolo.afiliado.nombre if protocolo.afiliado else 'No especificado',
            'edad': protocolo.afiliado.edad if protocolo.afiliado else None,
            'datos_clinicos': protocolo.datos_clinicos or ''
        }
        
        # Verificar si Claude está configurado
        if not claude_client.is_configured():
            return jsonify({
                'success': False,
                'error': 'Claude API no está configurada',
                'informe': ''
            })
        
        # Generar informe con Claude
        informe = claude_client.generar_informe(plantillas_seleccionadas, contexto)
        
        return jsonify({
            'success': True,
            'informe': informe,
            'claude_disponible': True
        })
        
    except Exception as e:
        logger.error(f"Error en claude_generar_informe: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'informe': '',
            'claude_disponible': claude_client.is_configured()
        })


@bp.route('/claude/estado')
@login_required
def claude_estado():
    """
    Verificar estado de Claude API
    """
    modelo_actual = claude_client.model if claude_client.is_configured() else None
    
    # Probar si el modelo actual está disponible
    modelo_disponible = None
    if claude_client.is_configured():
        resultado_prueba = claude_client.probar_modelo()
        modelo_disponible = resultado_prueba.get('disponible', False)
    
    return jsonify({
        'claude_disponible': claude_client.is_configured(),
        'modelo': modelo_actual,
        'modelo_funciona': modelo_disponible,
        'gemini_disponible': gemini_client.is_configured(),
        'gemini_modelo': gemini_client.model if gemini_client.is_configured() else None
    })


@bp.route('/gemini/estado')
@login_required
def gemini_estado():
    """
    Verificar estado de Gemini API
    """
    modelo_actual = gemini_client.model if gemini_client.is_configured() else None
    
    return jsonify({
        'gemini_disponible': gemini_client.is_configured(),
        'modelo': modelo_actual,
        'claude_disponible': claude_client.is_configured(),
        'claude_modelo': claude_client.model if claude_client.is_configured() else None
    })


@bp.route('/gemini/modelos', methods=['GET'])
@login_required
def gemini_modelos():
    """
    Listar modelos disponibles de Gemini API
    """
    if not gemini_client.is_configured():
        return jsonify({
            'success': False,
            'error': 'Gemini API no está configurada',
            'modelos': []
        })
    
    modelos = gemini_client.listar_modelos_disponibles()
    
    # Filtrar solo modelos que soporten generateContent y visión
    # Los modelos Gemini 2.0+ son multimodales (soportan visión) aunque no tengan "vision" en el nombre
    modelos_con_vision = []
    for modelo in modelos:
        metodos = modelo.get('supported_generation_methods', [])
        if 'generateContent' in metodos:
            # Usar el flag soporta_vision que ya calculamos en listar_modelos_disponibles
            if modelo.get('soporta_vision', False):
                modelos_con_vision.append(modelo)
    
    return jsonify({
        'success': True,
        'modelos': modelos,
        'modelos_con_vision': modelos_con_vision,
        'modelo_actual': gemini_client.model
    })


@bp.route('/claude/probar-modelos', methods=['GET', 'POST'])
@login_required
def probar_modelos():
    """
    Probar qué modelos están disponibles
    GET: Muestra página HTML para probar modelos
    POST: Devuelve JSON con resultados
    """
    if not claude_client.is_configured():
        if request.method == 'GET':
            return render_template('admin/claude_test.html', 
                                 error='Claude API no está configurada',
                                 modelo_actual=None)
        return jsonify({
            'success': False,
            'error': 'Claude API no está configurada'
        })
    
    modelos_a_probar = [
        'claude-3-haiku-20240307',
        'claude-3-sonnet-20240229',
        'claude-3-5-sonnet-20240620',
        'claude-3-opus-20240229',
        'claude-3-5-opus-20241022'
    ]
    
    resultados = {}
    for modelo in modelos_a_probar:
        resultado = claude_client.probar_modelo(modelo=modelo, timeout=5)
        resultados[modelo] = {
            'disponible': resultado.get('disponible', False),
            'error': resultado.get('error')
        }
    
    modelos_disponibles = [m for m, r in resultados.items() if r['disponible']]
    
    if request.method == 'GET':
        return render_template('admin/claude_test.html',
                             modelo_actual=claude_client.model,
                             resultados=resultados,
                             modelos_disponibles=modelos_disponibles,
                             error=None)
    
    return jsonify({
        'success': True,
        'modelos_disponibles': modelos_disponibles,
        'resultados': resultados
    })


@bp.route('/chat', methods=['POST'])
@login_required
def chat():
    """
    Chat conversacional con Claude API para usuarios internos
    """
    try:
        data = request.get_json()
        mensaje = data.get('mensaje', '').strip()
        protocolo_id = data.get('protocolo_id')
        historial_ids = data.get('historial_ids', [])
        tipo_estudio = data.get('tipo_estudio', '')
        imagenes = data.get('imagenes', [])  # Lista de imágenes en base64
        
        # Si hay imágenes, no es necesario que haya mensaje de texto
        if not mensaje and (not imagenes or len(imagenes) == 0):
            return jsonify({
                'success': False,
                'error': 'El mensaje debe tener al menos 2 caracteres o incluir al menos una imagen',
                'claude_disponible': claude_client.is_configured(),
                'gemini_disponible': gemini_client.is_configured()
            })
        
        if mensaje and len(mensaje) < 2 and (not imagenes or len(imagenes) == 0):
            return jsonify({
                'success': False,
                'error': 'El mensaje debe tener al menos 2 caracteres',
                'claude_disponible': claude_client.is_configured(),
                'gemini_disponible': gemini_client.is_configured()
            })
        
        # Validar y procesar imágenes
        imagenes_procesadas = []
        tiene_imagenes = imagenes and len(imagenes) > 0
        
        if tiene_imagenes:
            logger.info(f"📥 Recibidas {len(imagenes)} imagen(es) del frontend")
            # Limitar número de imágenes (máximo 5 para evitar sobrecarga)
            imagenes_limitadas = imagenes[:5]
            
            for idx, imagen in enumerate(imagenes_limitadas):
                if isinstance(imagen, dict):
                    imagen_data = imagen.get('data', '')
                    media_type = imagen.get('media_type', 'image/png')
                    nombre = imagen.get('nombre', 'imagen')
                    
                    if imagen_data:
                        # Validar formato de imagen
                        if imagen_data.startswith('data:'):
                            logger.info(f"✅ Imagen {idx+1}: {nombre} - Tipo: {media_type} - Formato: data URL (base64 incluido)")
                        elif len(imagen_data) > 100:
                            logger.info(f"✅ Imagen {idx+1}: {nombre} - Tipo: {media_type} - Formato: base64 directo ({len(imagen_data)} caracteres)")
                        else:
                            logger.warning(f"⚠️ Imagen {idx+1}: {nombre} - Datos parecen incompletos ({len(imagen_data)} caracteres)")
                        
                        imagenes_procesadas.append({
                            'data': imagen_data,
                            'media_type': media_type,
                            'nombre': nombre
                        })
                    else:
                        logger.warning(f"⚠️ Imagen {idx+1}: Sin datos")
            logger.info(f"📤 Procesando {len(imagenes_procesadas)} imagen(es)")
        
        # Construir contexto del usuario
        contexto_usuario = {
            'usuario_id': current_user.usuario_id,
            'rol': current_user.rol.nombre if current_user.rol else '',
            'es_medico': _es_usuario_medico(),
            'protocolo_actual': protocolo_id,
            'tipo_estudio': tipo_estudio
        }
        
        # Decidir qué API usar:
        # - Si hay imágenes: usar Gemini (especializado en visión)
        # - Si solo texto: usar Claude (más económico y rápido con Haiku)
        if tiene_imagenes:
            # Usar Gemini para análisis de imágenes
            if not gemini_client.is_configured():
                return jsonify({
                    'success': False,
                    'error': 'Gemini API no está configurada. Para analizar imágenes, configura la variable de entorno GEMINI_API_KEY. Obtén tu API key en: https://aistudio.google.com/app/apikey',
                    'claude_disponible': claude_client.is_configured(),
                    'gemini_disponible': False
                })
            
            logger.info(f"🔍 Usando Gemini para análisis de imágenes")
            resultado = gemini_client.chat_conversacional(
                mensaje=mensaje or 'Analiza esta imagen médica',
                imagenes=imagenes_procesadas,
                contexto_usuario=contexto_usuario
            )
            
            # Adaptar respuesta de Gemini al formato esperado
            resultado = {
                'respuesta': resultado.get('respuesta', ''),
                'intencion': resultado.get('intencion', 'analizar'),
                'acciones': resultado.get('acciones', []),
                'claude_disponible': claude_client.is_configured(),
                'gemini_disponible': True,
                'modelo_usado': 'gemini'
            }
        else:
            # Usar Claude para texto
            if not claude_client.is_configured():
                return jsonify({
                    'success': False,
                    'error': 'Claude API no está configurada. El asistente inteligente no está disponible en este momento.',
                    'claude_disponible': False,
                    'gemini_disponible': gemini_client.is_configured()
                })
            
            logger.info(f"🔍 Usando Claude para conversación de texto")
            # Obtener historial de mensajes si hay IDs
            historial = []
            if historial_ids:
                # TODO: Implementar recuperación de historial desde base de datos
                historial = []
            
            resultado = claude_client.chat_conversacional(
                mensaje=mensaje,
                historial=historial,
                contexto_usuario=contexto_usuario,
                imagenes=None
            )
            
            # Agregar información sobre modelo usado
            resultado['gemini_disponible'] = gemini_client.is_configured()
            resultado['modelo_usado'] = 'claude'
        
        # Guardar mensaje en historial (opcional)
        # TODO: Implementar guardado de historial en base de datos
        
        # Registrar en auditoría
        try:
            descripcion = f"Mensaje: {mensaje[:100]}" if mensaje else "Análisis de imagen"
            if tiene_imagenes:
                descripcion += f" ({len(imagenes_procesadas)} imagen(es))"
            Auditoria.registrar(
                usuario_id=current_user.usuario_id,
                accion='chat_asistente',
                tabla='asistente_chat',
                registro_id=None,
                descripcion=descripcion,
                ip_address=request.remote_addr
            )
        except Exception as e:
            logger.warning(f"Error registrando auditoría de chat: {e}")
        
        return jsonify({
            'success': True,
            'respuesta': resultado.get('respuesta', ''),
            'intencion': resultado.get('intencion', 'pregunta'),
            'acciones': resultado.get('acciones', []),
            'claude_disponible': True
        })
        
    except ValueError as e:
        # Claude no configurado
        return jsonify({
            'success': False,
            'error': str(e),
            'claude_disponible': False
        })
        
    except Exception as e:
        logger.error(f"Error en chat: {e}")
        return jsonify({
            'success': False,
            'error': f'Error procesando mensaje: {str(e)}',
            'claude_disponible': claude_client.is_configured()
        })


def _es_usuario_medico() -> bool:
    """Verificar si el usuario actual es médico"""
    if not current_user.is_authenticated or not getattr(current_user, 'rol', None):
        return False
    rol_nombre = getattr(current_user.rol, 'nombre', '').lower()
    return 'medico' in rol_nombre or 'patologo' in rol_nombre


@bp.route('/mensaje', methods=['POST'])
def registrar_mensaje_asistente():
    """
    Registrar mensaje del asistente.
    Permite mensajes sin autenticación cuando el contexto es 'login'.
    """
    data = request.get_json() or {}
    mensaje = (data.get('mensaje') or '').strip()
    tema = (data.get('tema') or 'Consulta').strip()
    contexto = (data.get('contexto') or '').strip()
    
    if len(mensaje) < 5:
        return jsonify({'success': False, 'error': 'El mensaje es demasiado corto.'}), 400
    
    descripcion = f"Tema: {tema}\nContexto: {contexto or 'general'}\nMensaje:\n{mensaje}"
    
    # Si el contexto es 'login' o no hay usuario autenticado, registrar sin usuario_id
    if contexto == 'login' or not current_user.is_authenticated:
        Auditoria.registrar(
            usuario_id=None,
            accion='ASISTENTE_MENSAJE',
            tabla='asistente',
            descripcion=descripcion,
            ip_address=request.remote_addr
        )
    else:
        Auditoria.registrar(
            usuario_id=current_user.usuario_id,
            accion='ASISTENTE_MENSAJE',
            tabla='asistente',
            descripcion=descripcion,
            ip_address=request.remote_addr
        )
    
    return jsonify({'success': True})


@bp.route('/mensaje-login', methods=['POST'])
def registrar_mensaje_login():
    data = request.get_json() or {}
    email = (data.get('email') or '').strip()
    mensaje = (data.get('mensaje') or '').strip()
    nombre = (data.get('nombre') or '').strip()
    dni = (data.get('dni') or '').strip()
    if not email or not mensaje:
        return jsonify({'success': False, 'error': 'Necesitamos un correo y un mensaje para ayudarte.'}), 400
    descripcion = (
        "Solicitud desde asistente (login)\n"
        f"Nombre: {nombre or 'No informado'}\n"
        f"Email: {email}\n"
        f"DNI: {dni or 'No informado'}\n"
        f"Mensaje:\n{mensaje}"
    )
    Auditoria.registrar(
        usuario_id=None,
        accion='ASISTENTE_LOGIN_MENSAJE',
        tabla='asistente',
        descripcion=descripcion,
        ip_address=request.remote_addr
    )
    return jsonify({'success': True})


@bp.route('/login/verificar-prestador', methods=['POST'])
def verificar_prestador_login():
    data = request.get_json() or {}
    documento = (data.get('documento') or '').strip()
    if not documento:
        return jsonify({'success': False, 'message': 'Ingresá un DNI válido.'}), 400
    documento_normalizado = documento.replace('.', '').replace('-', '').strip()
    prestador = Prestador.query.filter(Prestador.numero_documento == documento_normalizado).first()
    if prestador:
        return jsonify({
            'success': True,
            'encontrado': True,
            'nombre': prestador.nombre_completo,
            'especialidad': prestador.nombre_especialidad
        })
    return jsonify({
        'success': True,
        'encontrado': False,
        'message': 'No encontramos un prestador con ese DNI. Contactá al laboratorio para registrarte.'
    })


@bp.route('/login/buscar-usuario', methods=['POST'])
def buscar_usuario_login():
    data = request.get_json() or {}
    email = (data.get('email') or '').strip()
    if not email:
        return jsonify({'success': False, 'error': 'Necesitamos un correo para buscar.'}), 400
    usuario = Usuario.query.filter(Usuario.email.ilike(email)).first()
    if usuario:
        Auditoria.registrar(
            usuario_id=usuario.usuario_id,
            accion='ASISTENTE_LOGIN_RECUPERO',
            tabla='usuarios',
            descripcion=f'Se solicitó recuperación desde login para {email}',
            ip_address=request.remote_addr
        )
        return jsonify({'success': True, 'mensaje': 'Encontramos tu correo. El equipo se pondrá en contacto para restablecer tus credenciales.'})
    return jsonify({'success': True, 'mensaje': 'No encontramos ese correo en la base. Revisalo o comunicate con el laboratorio.'})


@bp.route('/chat/historial', methods=['GET'])
@login_required
def historial_chat():
    """
    Obtener historial de chat para el usuario actual o un protocolo específico.
    """
    limite = request.args.get('limite', 20, type=int)
    protocolo_id = request.args.get('protocolo_id', type=int)

    query = Auditoria.query.filter(
        Auditoria.usuario_id == current_user.usuario_id,
        Auditoria.accion == 'chat_asistente'
    )

    if protocolo_id:
        # Filtrar por protocolo_id si se proporciona
        query = query.filter(Auditoria.descripcion.ilike(f'%Protocolo ID: {protocolo_id}%'))
        
    historial_auditoria = query.order_by(desc(Auditoria.fecha_hora)).limit(limite).all()
    
    historial_formateado = []
    for item in reversed(historial_auditoria): # Mostrar en orden cronológico ascendente
        # Intentar parsear el mensaje y la respuesta del asistente desde la descripción
        descripcion = item.descripcion or ''
        mensaje_usuario_match = re.search(r'Mensaje: (.*?)(?=\nRespuesta:|$)', descripcion, re.DOTALL)
        respuesta_asistente_match = re.search(r'Respuesta: (.*)', descripcion, re.DOTALL)

        mensaje_usuario = mensaje_usuario_match.group(1).strip() if mensaje_usuario_match else None
        respuesta_asistente = respuesta_asistente_match.group(1).strip() if respuesta_asistente_match else None

        if mensaje_usuario and respuesta_asistente:
            historial_formateado.append({
                'historial_id': item.auditoria_id,
                'mensaje': mensaje_usuario,
                'respuesta': respuesta_asistente,
                'fecha_hora': item.fecha_hora.isoformat()
            })
    
    return jsonify({'success': True, 'historial': historial_formateado})

