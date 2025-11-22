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
from utils.decorators import permission_required
from datetime import datetime, date
from sqlalchemy import or_, and_, desc, asc
import unicodedata

bp = Blueprint('protocolos', __name__, url_prefix='/protocolos')


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
    
    # Query base
    query = Protocolo.query.join(Afiliado).join(Prestador, isouter=True)
    
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
    
    # Estadísticas rápidas
    stats = {
        'total': Protocolo.query.count(),
        'pendientes': Protocolo.query.filter_by(estado='PENDIENTE').count(),
        'en_proceso': Protocolo.query.filter_by(estado='EN_PROCESO').count(),
        'completados': Protocolo.query.filter_by(estado='COMPLETADO').count(),
        'biopsias': Protocolo.query.filter_by(tipo_estudio='BIOPSIA').count(),
        'citologias': Protocolo.query.filter_by(tipo_estudio='CITOLOGÍA').count(),
        'pap': Protocolo.query.filter_by(tipo_estudio='PAP').count()
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
    prestadores = Prestador.query.filter_by(activo=True).order_by(Prestador.apellido, Prestador.nombre).all()
    obras_sociales = ObraSocial.query.order_by(ObraSocial.nombre).all()
    tipos_analisis = TipoAnalisis.query.filter_by(activo=True).order_by(TipoAnalisis.nombre).all()
    
    # Tipo predefinido si viene en la URL
    tipo_predefinido = request.args.get('tipo', '')
    
    return render_template('protocolos/form.html',
                         afiliados=afiliados,
                         prestadores=prestadores,
                         obras_sociales=obras_sociales,
                         tipos_analisis=tipos_analisis,
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
        obra_social_id = request.form.get('obra_social_id', type=int) or None
        tipo_analisis_id = request.form.get('tipo_analisis_id', type=int) or None
        datos_clinicos = request.form.get('datos_clinicos', '').strip()
        accion = request.form.get('accion', 'guardar')
        marcar_completado = accion == 'guardar_completar'

        if marcar_completado and not _es_usuario_medico():
            flash('Solo un usuario con rol médico puede completar el protocolo. Se guardará como pendiente.', 'warning')
            marcar_completado = False
        
        if not afiliado_id or not tipo_estudio:
            flash('Datos obligatorios faltantes.', 'error')
            return redirect(url_for('protocolos.nuevo'))
        
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
            obra_social_id=obra_social_id,
            obra_social_nombre=obra_social_nombre,
            obra_social_codigo=obra_social_codigo,
            obra_social_activa=obra_social_activa,
            tipo_analisis_id=tipo_analisis_id,
            fecha_ingreso=date.today(),
            datos_clinicos=datos_clinicos,
            estado='COMPLETADO' if marcar_completado else 'PENDIENTE',
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
    
    return render_template('protocolos/ver.html',
                         protocolo=protocolo,
                         informe=informe)


@bp.route('/<int:id>/editar')
@login_required
@permission_required('protocolos_editar')
def editar(id):
    """Formulario para editar protocolo"""
    protocolo = Protocolo.query.get_or_404(id)
    
    # Solo se puede editar si está pendiente o en proceso
    if protocolo.estado not in ['PENDIENTE', 'EN_PROCESO']:
        flash('Solo se pueden editar protocolos pendientes o en proceso.', 'warning')
        return redirect(url_for('protocolos.ver', id=id))
    
    # Obtener datos para el formulario
    afiliados = Afiliado.query.filter_by(activo=True).order_by(Afiliado.apellido, Afiliado.nombre).all()
    prestadores = Prestador.query.filter_by(activo=True).order_by(Prestador.apellido, Prestador.nombre).all()
    obras_sociales = ObraSocial.query.order_by(ObraSocial.nombre).all()
    tipos_analisis = TipoAnalisis.query.filter_by(activo=True).order_by(TipoAnalisis.nombre).all()
    
    return render_template('protocolos/form.html',
                         protocolo=protocolo,
                         afiliados=afiliados,
                         prestadores=prestadores,
                         obras_sociales=obras_sociales,
                         tipos_analisis=tipos_analisis)


@bp.route('/<int:id>/actualizar', methods=['POST'])
@login_required
@permission_required('protocolos_editar')
def actualizar(id):
    """Actualizar protocolo"""
    protocolo = Protocolo.query.get_or_404(id)
    
    try:
        # Solo se puede editar si está pendiente o en proceso
        if protocolo.estado not in ['PENDIENTE', 'EN_PROCESO']:
            flash('Solo se pueden editar protocolos pendientes o en proceso.', 'warning')
            return redirect(url_for('protocolos.ver', id=id))
        
        # Actualizar campos
        protocolo.prestador_id = request.form.get('prestador_id', type=int) or None
        protocolo.obra_social_id = request.form.get('obra_social_id', type=int) or None
        protocolo.tipo_analisis_id = request.form.get('tipo_analisis_id', type=int) or None
        protocolo.datos_clinicos = request.form.get('datos_clinicos', '').strip()
        accion = request.form.get('accion', 'guardar')
        marcar_completado = accion == 'guardar_completar'

        if marcar_completado and not _es_usuario_medico():
            flash('Solo un usuario con rol médico puede completar el protocolo. Se guardará sin completar.', 'warning')
            marcar_completado = False
        
        estado_anterior = protocolo.estado
        if marcar_completado:
            protocolo.estado = 'COMPLETADO'
            protocolo.fecha_informe = date.today()
            protocolo.usuario_informe_id = current_user.usuario_id
        
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
        protocolo.estado = nuevo_estado
        
        if nuevo_estado == 'COMPLETADO':
            protocolo.fecha_informe = date.today()
            protocolo.usuario_informe_id = current_user.usuario_id
        
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
