"""
Rutas para módulo de Protocolos (unificado)
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from extensions import db
from models.protocolo import Protocolo, TipoAnalisis
from models.paciente import Afiliado
from models.prestador import Prestador
from models.obra_social import ObraSocial
from models.auditoria import Auditoria
from models.entidad import usuario_prestador
from models.usuario import Usuario
from utils.decorators import permission_required
from datetime import datetime, date
from sqlalchemy import or_, and_, desc, asc, text, func
import unicodedata
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('protocolos', __name__, url_prefix='/protocolos')


@bp.route('/api/prestadores-asociados/<int:entidad_id>')
@login_required
def api_prestadores_asociados(entidad_id):
    """API para obtener prestadores asociados a una entidad"""
    try:
        entidad_prestador = Prestador.query.get_or_404(entidad_id)
        logger.info(f"🔍 Buscando prestadores asociados para prestador_id (entidad)={entidad_id}, es_entidad={entidad_prestador.es_entidad}, nombre={entidad_prestador.nombre_completo}")
        
        if not entidad_prestador.es_entidad:
            logger.warning(f"❌ Prestador {entidad_id} no es una entidad")
            return jsonify({'prestadores': []})
        
        # Buscar el Usuario asociado a este Prestador (entidad)
        # Los prestadores están asociados al usuario_id, no al prestador_id
        # Primero intentar por prestador_id directo
        usuario_entidad = Usuario.query.filter_by(prestador_id=entidad_id).first()
        
        # Si no se encuentra, buscar usuarios con rol ENTIDAD cuyo nombre coincida
        if not usuario_entidad:
            logger.warning(f"⚠️ No se encontró usuario con prestador_id={entidad_id}, buscando por nombre y rol ENTIDAD...")
            from models.usuario import Rol
            rol_entidad = Rol.query.filter(
                or_(
                    Rol.nombre == 'ENTIDAD',
                    Rol.nombre == 'Entidad',
                    Rol.nombre == 'Entidades',
                    func.upper(Rol.nombre) == 'ENTIDAD'
                )
            ).first()
            
            if rol_entidad:
                # Buscar usuarios con rol ENTIDAD cuyo nombre coincida con el prestador
                nombre_prestador = entidad_prestador.nombre_completo
                usuarios_candidatos = Usuario.query.filter_by(rol_id=rol_entidad.rol_id, activo=True).all()
                
                logger.info(f"📋 Encontrados {len(usuarios_candidatos)} usuarios con rol ENTIDAD")
                logger.info(f"🔍 Buscando coincidencia para prestador: '{nombre_prestador}'")
                
                # Buscar coincidencia exacta de nombre primero (case-insensitive, sin espacios extra)
                nombre_prestador_normalizado = nombre_prestador.lower().strip()
                for u in usuarios_candidatos:
                    nombre_usuario_normalizado = u.nombre_completo.lower().strip()
                    logger.info(f"   Comparando con usuario: '{u.nombre_completo}' (usuario_id={u.usuario_id})")
                    if nombre_usuario_normalizado == nombre_prestador_normalizado:
                        usuario_entidad = u
                        logger.info(f"✅ Usuario encontrado por nombre exacto: usuario_id={u.usuario_id}, username={u.username}")
                        break
                
                # Si no hay coincidencia exacta, buscar por similitud (palabras comunes)
                if not usuario_entidad:
                    mejor_coincidencia = None
                    mejor_score = 0
                    for u in usuarios_candidatos:
                        # Calcular similitud por palabras comunes
                        palabras_entidad = set(nombre_prestador_normalizado.split())
                        palabras_usuario = set(u.nombre_completo.lower().strip().split())
                        coincidencias = len(palabras_entidad.intersection(palabras_usuario))
                        if coincidencias > mejor_score:
                            mejor_score = coincidencias
                            mejor_coincidencia = u
                    
                    if mejor_coincidencia and mejor_score > 0:
                        usuario_entidad = mejor_coincidencia
                        logger.info(f"✅ Usuario encontrado por similitud de nombre: usuario_id={usuario_entidad.usuario_id}, username={usuario_entidad.username}, score={mejor_score}")
        
        if not usuario_entidad:
            logger.warning(f"❌ No se encontró usuario asociado al prestador {entidad_id} (nombre: {entidad_prestador.nombre_completo})")
            return jsonify({'prestadores': []})
        
        logger.info(f"✅ Usuario encontrado: usuario_id={usuario_entidad.usuario_id}, username={usuario_entidad.username}")
        
        # Buscar prestadores asociados en la tabla usuario_prestador
        prestadores_ids = db.session.query(usuario_prestador.c.prestador_id).filter(
            usuario_prestador.c.usuario_id == usuario_entidad.usuario_id
        ).all()
        
        prestador_ids_list = [pid[0] for pid in prestadores_ids]
        logger.info(f"📋 IDs de prestadores encontrados en usuario_prestador: {prestador_ids_list} (total: {len(prestador_ids_list)})")
        
        if not prestador_ids_list:
            logger.info("⚠️ No hay prestadores asociados en usuario_prestador")
            return jsonify({'prestadores': []})
        
        # Obtener los prestadores
        prestadores_asociados = Prestador.query.filter(
            Prestador.prestador_id.in_(prestador_ids_list),
            Prestador.es_entidad == False,
            Prestador.activo == True
        ).order_by(Prestador.apellido, Prestador.nombre).all()
        
        logger.info(f"✅ Prestadores encontrados después de filtros: {len(prestadores_asociados)}")
        if prestadores_asociados:
            logger.info(f"📝 Nombres de prestadores: {[p.nombre_completo for p in prestadores_asociados]}")
        else:
            # Si no se encontraron prestadores después de filtros, verificar por qué
            todos = Prestador.query.filter(Prestador.prestador_id.in_(prestador_ids_list)).all()
            logger.warning(f"⚠️ Se encontraron {len(todos)} prestadores sin filtros, pero {len(prestadores_asociados)} después de filtros")
            for p in todos:
                logger.warning(f"   - {p.nombre_completo}: es_entidad={p.es_entidad}, activo={p.activo}")
        
        resultado = [{
            'prestador_id': p.prestador_id,
            'nombre_completo': p.nombre_completo,
            'especialidad': p.nombre_especialidad
        } for p in prestadores_asociados]
        
        # Incluir información de debug si se solicita
        response = {'prestadores': resultado}
        if request.args.get('debug') == '1':
            response['debug'] = {
                'prestador_id_entidad': entidad_id,
                'es_entidad': entidad_prestador.es_entidad,
                'usuario_encontrado': usuario_entidad is not None,
                'usuario_id': usuario_entidad.usuario_id if usuario_entidad else None,
                'prestador_ids_en_tabla': prestador_ids_list,
                'total_ids_encontrados': len(prestador_ids_list),
                'prestadores_encontrados': len(prestadores_asociados)
            }
        
        return jsonify(response)
    except Exception as e:
        logger.error(f"❌ Error obteniendo prestadores asociados: {e}", exc_info=True)
        return jsonify({'prestadores': [], 'error': str(e)}), 500


def _normalizar_texto(texto: str) -> str:
    if not texto:
        return ''
    texto = unicodedata.normalize('NFD', texto.strip().lower())
    return ''.join(ch for ch in texto if unicodedata.category(ch) != 'Mn')


def _es_usuario_medico():
    nombre = getattr(current_user.rol, 'nombre', '')
    normalizado = _normalizar_texto(nombre)
    return 'medico' in normalizado if normalizado else False


@bp.route('/')
@login_required
@permission_required('protocolos_ver')
def index():
    """Listado de protocolos"""
    page = request.args.get('page', 1, type=int)
    buscar = request.args.get('buscar', '').strip()
    tipo = request.args.get('tipo', '').strip()
    estado = request.args.get('estado', '').strip()
    
    # Query base (excluir protocolos de prueba)
    # Especificar explícitamente el join con Prestador usando prestador_id (no prestador_medico_id)
    query = Protocolo.query.join(Afiliado).join(
        Prestador, 
        Protocolo.prestador_id == Prestador.prestador_id, 
        isouter=True
    ).filter(
        Protocolo.es_prueba == False
    )
    
    # Filtros
    if buscar:
        query = query.filter(
            or_(
                Protocolo.numero_protocolo.ilike(f'%{buscar}%'),
                Afiliado.apellido.ilike(f'%{buscar}%'),
                Afiliado.nombre.ilike(f'%{buscar}%'),
                Afiliado.numero_afiliado.ilike(f'%{buscar}%'),
                Prestador.apellido.ilike(f'%{buscar}%'),
                Prestador.nombre.ilike(f'%{buscar}%')
            )
        )
    
    if tipo:
        query = query.filter(Protocolo.tipo_estudio == tipo)
    
    if estado:
        query = query.filter(Protocolo.estado == estado)
    
    # Ordenamiento por fecha de ingreso (más reciente primero)
    query = query.order_by(desc(Protocolo.fecha_ingreso), desc(Protocolo.protocolo_id))
    
    # Paginación
    protocolos = query.paginate(
        page=page, 
        per_page=20, 
        error_out=False
    )
    
    # Estadísticas rápidas (excluir protocolos de prueba)
    stats = {
        'total': Protocolo.query.filter_by(es_prueba=False).count(),
        'pendientes': Protocolo.query.filter_by(estado='PENDIENTE', es_prueba=False).count(),
        'en_proceso': Protocolo.query.filter_by(estado='EN_PROCESO', es_prueba=False).count(),
        'completados': Protocolo.query.filter_by(estado='COMPLETADO', es_prueba=False).count(),
        'biopsias': Protocolo.query.filter_by(tipo_estudio='BIOPSIA', es_prueba=False).count(),
        'citologias': Protocolo.query.filter_by(tipo_estudio='CITOLOGÍA', es_prueba=False).count(),
        'pap': Protocolo.query.filter_by(tipo_estudio='PAP', es_prueba=False).count()
    }
    
    for protocolo in protocolos.items:
        tipo_original = (protocolo.tipo_estudio or '').strip()
        estado_original = (protocolo.estado or '').strip()
        tipo_normalizado = unicodedata.normalize('NFD', tipo_original.upper())
        tipo_normalizado = ''.join(ch for ch in tipo_normalizado if unicodedata.category(ch) != 'Mn')
        estado_normalizado = unicodedata.normalize('NFD', estado_original.upper())
        estado_normalizado = ''.join(ch for ch in estado_normalizado if unicodedata.category(ch) != 'Mn')
        protocolo.tipo_estudio_normalizado = tipo_normalizado
        protocolo.estado_normalizado = estado_normalizado
        protocolo.tipo_estudio_display = tipo_original
        protocolo.estado_display = estado_original
    
    return render_template('protocolos/index.html', 
                         protocolos=protocolos,
                         buscar=buscar,
                         tipo=tipo,
                         estado=estado,
                         stats=stats)


@bp.route('/nuevo')
@login_required
@permission_required('protocolos_crear')
def nuevo():
    """Formulario para nuevo protocolo"""
    # Obtener datos para el formulario
    afiliados = Afiliado.query.filter_by(activo=True).order_by(Afiliado.apellido, Afiliado.nombre).all()
    # Incluir tanto prestadores como entidades en la lista
    prestadores = Prestador.query.filter_by(activo=True).order_by(Prestador.apellido, Prestador.nombre).all()
    obras_sociales = ObraSocial.query.order_by(ObraSocial.nombre).all()
    
    # Tipo predefinido si viene en la URL
    tipo_predefinido = request.args.get('tipo', '')
    
    return render_template('protocolos/form.html',
                         afiliados=afiliados,
                         prestadores=prestadores,
                         obras_sociales=obras_sociales,
                         tipo_predefinido=tipo_predefinido)


@bp.route('/crear', methods=['POST'])
@login_required
@permission_required('protocolos_crear')
def crear():
    """Crear nuevo protocolo"""
    try:
        # Validar datos
        afiliado_id = request.form.get('afiliado_id', type=int)
        tipo_estudio = request.form.get('tipo_estudio')
        prestador_id = request.form.get('prestador_id', type=int) or None
        prestador_medico_id = request.form.get('prestador_medico_id', type=int) or None
        obra_social_id = request.form.get('obra_social_id', type=int) or None
        datos_clinicos = request.form.get('datos_clinicos', '').strip()
        accion = request.form.get('accion', 'guardar')
        marcar_completado = accion == 'guardar_completar'
        marcar_urgente = request.form.get('es_urgente') == 'on' or request.form.get('es_urgente') == 'true'
        tipo_protocolo = request.form.get('tipo_protocolo', 'AMBULATORIO').strip().upper()

        if marcar_completado and not _es_usuario_medico():
            flash('Solo un usuario con rol médico puede completar el protocolo. Se guardará como pendiente.', 'warning')
            marcar_completado = False
        
        if not afiliado_id or not tipo_estudio:
            flash('Datos obligatorios faltantes.', 'error')
            return redirect(url_for('protocolos.nuevo'))
        
        # Validar tipo_protocolo
        if tipo_protocolo not in ['AMBULATORIO', 'INTERNACION']:
            tipo_protocolo = 'AMBULATORIO'
        
        # Determinar estado inicial
        if marcar_completado:
            estado_inicial = 'COMPLETADO'
        elif marcar_urgente:
            estado_inicial = 'URGENTE'
        else:
            estado_inicial = 'PENDIENTE'
        
        # Generar número de protocolo
        numero_protocolo = Protocolo.generar_numero_protocolo(tipo_estudio)
        
        # Obtener datos de OS al momento del protocolo
        obra_social_nombre = None
        obra_social_codigo = None
        obra_social_activa = True
        
        if obra_social_id:
            obra_social = ObraSocial.query.get(obra_social_id)
            if obra_social:
                obra_social_nombre = obra_social.nombre
                obra_social_codigo = obra_social.codigo
                obra_social_activa = obra_social.activo
        
        # Crear protocolo
        protocolo = Protocolo(
            numero_protocolo=numero_protocolo,
            tipo_estudio=tipo_estudio,
            afiliado_id=afiliado_id,
            prestador_id=prestador_id,
            prestador_medico_id=prestador_medico_id,
            obra_social_id=obra_social_id,
            obra_social_nombre=obra_social_nombre,
            obra_social_codigo=obra_social_codigo,
            obra_social_activa=obra_social_activa,
            fecha_ingreso=date.today(),
            datos_clinicos=datos_clinicos,
            estado=estado_inicial,
            tipo_protocolo=tipo_protocolo,
            usuario_ingreso_id=current_user.usuario_id,
            usuario_informe_id=current_user.usuario_id if marcar_completado else None,
            fecha_informe=date.today() if marcar_completado else None
        )
        
        db.session.add(protocolo)
        db.session.commit()
        
        # Registrar auditoría
        Auditoria.registrar(
            usuario_id=current_user.usuario_id,
            accion='PROTOCOLO_CREADO',
            tabla='protocolos',
            registro_id=protocolo.protocolo_id,
            descripcion=f'Protocolo {numero_protocolo} creado',
            ip_address=request.remote_addr
        )
        
        if marcar_completado:
            Auditoria.registrar(
                usuario_id=current_user.usuario_id,
                accion='PROTOCOLO_ESTADO',
                tabla='protocolos',
                registro_id=protocolo.protocolo_id,
                descripcion=f'Protocolo {numero_protocolo}: PENDIENTE → COMPLETADO',
                ip_address=request.remote_addr
            )
            
            # Enviar notificaciones cuando se completa el protocolo
            try:
                from services.notificaciones import NotificacionesService
                NotificacionesService.enviar_notificacion_protocolo_completado(protocolo)
            except Exception as e:
                logger.error(f"Error enviando notificaciones para protocolo {protocolo.protocolo_id}: {e}")
                # No fallar la operación si las notificaciones fallan
            
            flash(f'Protocolo {numero_protocolo} creado y completado correctamente.', 'success')
        else:
            flash(f'Protocolo {numero_protocolo} creado correctamente.', 'success')
        
        # Por ahora redirigir a ver el protocolo (cuando estén los módulos específicos, se puede cambiar)
        return redirect(url_for('protocolos.ver', id=protocolo.protocolo_id))
            
    except Exception as e:
        db.session.rollback()
        flash(f'Error al crear protocolo: {str(e)}', 'error')
        return redirect(url_for('protocolos.nuevo'))


@bp.route('/<int:id>')
@login_required
@permission_required('protocolos_ver')
def ver(id):
    """Ver detalle de protocolo"""
    protocolo = Protocolo.query.get_or_404(id)
    informe = protocolo.get_informe()
    
    # Obtener entidades asociadas a este prestador (si existe)
    entidades_asociadas = []
    if protocolo.prestador_id:
        from models.usuario import Usuario, Rol
        from models.entidad import usuario_prestador
        
        # Buscar rol ENTIDAD
        rol_entidad = Rol.query.filter(
            db.or_(
                db.func.upper(Rol.nombre) == 'ENTIDAD',
                db.func.lower(Rol.nombre) == 'entidad',
                db.func.lower(Rol.nombre) == 'entidades'
            )
        ).first()
        
        if rol_entidad:
            # Buscar usuarios entidad con este prestador asociado
            usuarios_entidad = db.session.query(Usuario).join(usuario_prestador).filter(
                usuario_prestador.c.prestador_id == protocolo.prestador_id,
                Usuario.rol_id == rol_entidad.rol_id,
                Usuario.activo == True
            ).all()
            
            for usuario_entidad in usuarios_entidad:
                # Obtener el prestador asociado a la entidad (prestador_entidad)
                prestador_entidad = Prestador.query.get(usuario_entidad.prestador_id) if usuario_entidad.prestador_id else None
                
                # Obtener permisos de la asociación
                permiso = db.session.query(usuario_prestador).filter(
                    usuario_prestador.c.usuario_id == usuario_entidad.usuario_id,
                    usuario_prestador.c.prestador_id == protocolo.prestador_id
                ).first()
                
                if prestador_entidad and permiso:
                    entidades_asociadas.append({
                        'usuario': usuario_entidad,
                        'prestador': prestador_entidad,
                        'permisos': {
                            'ambulatorio': permiso.puede_ver_ambulatorio,
                            'internacion': permiso.puede_ver_internacion
                        }
                    })
    
    return render_template('protocolos/ver.html',
                         protocolo=protocolo,
                         informe=informe,
                         entidades_asociadas=entidades_asociadas)


@bp.route('/<int:id>/editar')
@login_required
@permission_required('protocolos_editar')
def editar(id):
    """Formulario para editar protocolo"""
    protocolo = Protocolo.query.get_or_404(id)
    
    # Solo se puede editar si está pendiente, en proceso o urgente
    if protocolo.estado not in ['URGENTE', 'PENDIENTE', 'EN_PROCESO']:
        flash('Solo se pueden editar protocolos urgentes, pendientes o en proceso.', 'warning')
        return redirect(url_for('protocolos.ver', id=id))
    
    # Obtener datos para el formulario
    afiliados = Afiliado.query.filter_by(activo=True).order_by(Afiliado.apellido, Afiliado.nombre).all()
    prestadores = Prestador.query.filter_by(activo=True).order_by(Prestador.apellido, Prestador.nombre).all()
    obras_sociales = ObraSocial.query.order_by(ObraSocial.nombre).all()
    
    return render_template('protocolos/form.html',
                         protocolo=protocolo,
                         afiliados=afiliados,
                         prestadores=prestadores,
                         obras_sociales=obras_sociales)


@bp.route('/<int:id>/actualizar', methods=['POST'])
@login_required
@permission_required('protocolos_editar')
def actualizar(id):
    """Actualizar protocolo"""
    protocolo = Protocolo.query.get_or_404(id)
    
    try:
        # Solo se puede editar si está pendiente, en proceso o urgente
        if protocolo.estado not in ['PENDIENTE', 'EN_PROCESO', 'URGENTE']:
            flash('Solo se pueden editar protocolos pendientes, en proceso o urgentes.', 'warning')
            return redirect(url_for('protocolos.ver', id=id))
        
        # Actualizar campos
        protocolo.prestador_id = request.form.get('prestador_id', type=int) or None
        protocolo.prestador_medico_id = request.form.get('prestador_medico_id', type=int) or None
        protocolo.obra_social_id = request.form.get('obra_social_id', type=int) or None
        protocolo.datos_clinicos = request.form.get('datos_clinicos', '').strip()
        
        # Actualizar tipo_protocolo
        tipo_protocolo = request.form.get('tipo_protocolo', 'AMBULATORIO').strip().upper()
        if tipo_protocolo in ['AMBULATORIO', 'INTERNACION']:
            protocolo.tipo_protocolo = tipo_protocolo
        
        # Manejar estado URGENTE
        marcar_urgente = request.form.get('es_urgente') == 'on' or request.form.get('es_urgente') == 'true'
        
        accion = request.form.get('accion', 'guardar')
        marcar_completado = accion == 'guardar_completar'

        if marcar_completado and not _es_usuario_medico():
            flash('Solo un usuario con rol médico puede completar el protocolo. Se guardará sin completar.', 'warning')
            marcar_completado = False
        
        estado_anterior = protocolo.estado
        
        # Determinar nuevo estado
        if marcar_completado:
            protocolo.estado = 'COMPLETADO'
            protocolo.fecha_informe = date.today()
            protocolo.usuario_informe_id = current_user.usuario_id
        elif marcar_urgente and protocolo.estado != 'COMPLETADO':
            protocolo.estado = 'URGENTE'
        elif not marcar_urgente and protocolo.estado == 'URGENTE':
            # Si desmarcan urgente, cambiar a EN_PROCESO
            protocolo.estado = 'EN_PROCESO'
        
        db.session.commit()
        
        # Registrar auditoría
        Auditoria.registrar(
            usuario_id=current_user.usuario_id,
            accion='PROTOCOLO_EDITADO',
            tabla='protocolos',
            registro_id=protocolo.protocolo_id,
            descripcion=f'Protocolo {protocolo.numero_protocolo} editado',
            ip_address=request.remote_addr
        )
        
        if marcar_completado and estado_anterior != 'COMPLETADO':
            Auditoria.registrar(
                usuario_id=current_user.usuario_id,
                accion='PROTOCOLO_ESTADO',
                tabla='protocolos',
                registro_id=protocolo.protocolo_id,
                descripcion=f'Protocolo {protocolo.numero_protocolo}: {estado_anterior} → COMPLETADO',
                ip_address=request.remote_addr
            )
            
            # Enviar notificaciones cuando se completa el protocolo
            try:
                from services.notificaciones import NotificacionesService
                NotificacionesService.enviar_notificacion_protocolo_completado(protocolo)
            except Exception as e:
                logger.error(f"Error enviando notificaciones para protocolo {protocolo.protocolo_id}: {e}")
                # No fallar la operación si las notificaciones fallan
        
        mensaje = 'Protocolo actualizado correctamente.'
        if marcar_completado and estado_anterior != 'COMPLETADO':
            mensaje = 'Protocolo actualizado y completado correctamente.'
        flash(mensaje, 'success')
        
        return redirect(url_for('protocolos.ver', id=id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al actualizar protocolo: {str(e)}', 'error')
        return redirect(url_for('protocolos.editar', id=id))


@bp.route('/<int:id>/cambiar-estado', methods=['POST'])
@login_required
@permission_required('protocolos_editar')
def cambiar_estado(id):
    """Cambiar estado del protocolo"""
    protocolo = Protocolo.query.get_or_404(id)
    nuevo_estado = request.form.get('estado')
    
    try:
        estado_anterior = protocolo.estado
        
        # Validar que el nuevo estado sea válido
        estados_validos = ['URGENTE', 'PENDIENTE', 'EN_PROCESO', 'COMPLETADO', 'CANCELADO']
        if nuevo_estado not in estados_validos:
            flash('Estado inválido.', 'error')
            return redirect(url_for('protocolos.ver', id=id))
        
        protocolo.estado = nuevo_estado
        
        if nuevo_estado == 'COMPLETADO':
            protocolo.fecha_informe = date.today()
            protocolo.usuario_informe_id = current_user.usuario_id
        elif nuevo_estado != 'COMPLETADO' and protocolo.fecha_informe:
            # Si se cambia de COMPLETADO a otro estado, limpiar fecha de informe
            protocolo.fecha_informe = None
            protocolo.usuario_informe_id = None
        
        db.session.commit()
        
        # Registrar auditoría
        Auditoria.registrar(
            usuario_id=current_user.usuario_id,
            accion='PROTOCOLO_ESTADO',
            tabla='protocolos',
            registro_id=protocolo.protocolo_id,
            descripcion=f'Protocolo {protocolo.numero_protocolo}: {estado_anterior} → {nuevo_estado}',
            ip_address=request.remote_addr
        )
        
        flash(f'Estado cambiado a {nuevo_estado}.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al cambiar estado: {str(e)}', 'error')
    
    return redirect(url_for('protocolos.ver', id=id))


@bp.route('/buscar-afiliado')
@login_required
def buscar_afiliado():
    """Buscar afiliados para autocompletar"""
    termino = request.args.get('q', '').strip()
    
    if len(termino) < 2:
        return jsonify([])
    
    afiliados = Afiliado.query.filter(
        and_(
            Afiliado.activo == True,
            or_(
                Afiliado.nombre_completo.ilike(f'%{termino}%'),
                Afiliado.numero_afiliado.ilike(f'%{termino}%')
            )
        )
    ).limit(10).all()
    
    resultados = []
    for afiliado in afiliados:
        resultados.append({
            'id': afiliado.afiliado_id,
            'text': f"{afiliado.nombre_completo} (Nº {afiliado.numero_afiliado or 'N/A'})",
            'nombre': afiliado.nombre_completo,
            'numero': afiliado.numero_afiliado
        })
    
    return jsonify(resultados)


@bp.route('/buscar-prestador')
@login_required
def buscar_prestador():
    """Buscar prestadores para autocompletar"""
    termino = request.args.get('q', '').strip()
    
    if len(termino) < 2:
        return jsonify([])
    
    prestadores = Prestador.query.filter(
        and_(
            Prestador.activo == True,
            Prestador.nombre_completo.ilike(f'%{termino}%')
        )
    ).limit(10).all()
    
    resultados = []
    for prestador in prestadores:
        resultados.append({
            'id': prestador.prestador_id,
            'text': f"{prestador.nombre_completo} - {prestador.nombre_especialidad}",
            'nombre': prestador.nombre_completo,
            'especialidad': prestador.nombre_especialidad
        })
    
    return jsonify(resultados)
