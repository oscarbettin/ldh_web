"""
Rutas de gestión de entidades (usuarios con rol Entidades)
Permite asociar prestadores a entidades para que puedan ver sus protocolos
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from extensions import db
from models.usuario import Usuario, Rol
from models.prestador import Prestador, Especialidad
from models.entidad import usuario_prestador
from models.auditoria import Auditoria
from utils.decorators import permission_required
from datetime import datetime
from sqlalchemy import and_, or_, func

bp = Blueprint('entidades', __name__, url_prefix='/entidades')


@bp.route('/')
@login_required
@permission_required('prestadores_ver')  # Usar permiso de prestadores para acceso
def index():
    """Listado de usuarios con rol Entidades"""
    # Obtener rol "Entidades" (buscar variantes del nombre)
    from sqlalchemy import or_, func
    rol_entidades = Rol.query.filter(
        or_(
            Rol.nombre == 'ENTIDAD',
            Rol.nombre == 'Entidad',
            Rol.nombre == 'Entidades',
            func.upper(Rol.nombre) == 'ENTIDAD',
            func.lower(Rol.nombre) == 'entidad',
            func.lower(Rol.nombre) == 'entidades'
        )
    ).first()
    
    if not rol_entidades:
        flash('El rol "ENTIDAD" no existe en el sistema. Ejecute el script de inicialización.', 'warning')
        return render_template('entidades/index.html', entidades=[])
    
    # Obtener todos los usuarios con rol Entidades
    entidades = Usuario.query.filter_by(rol_id=rol_entidades.rol_id, activo=True).order_by(Usuario.nombre_completo).all()
    
    # Para cada entidad, obtener sus prestadores asociados
    entidades_con_prestadores = []
    for entidad in entidades:
        prestadores_ids = db.session.query(usuario_prestador.c.prestador_id).filter(
            usuario_prestador.c.usuario_id == entidad.usuario_id
        ).all()
        
        prestadores = Prestador.query.filter(
            Prestador.prestador_id.in_([pid[0] for pid in prestadores_ids])
        ).all() if prestadores_ids else []
        
        entidades_con_prestadores.append({
            'entidad': entidad,
            'prestadores': prestadores,
            'cantidad_prestadores': len(prestadores)
        })
    
    return render_template('entidades/index.html', 
                         entidades=entidades_con_prestadores,
                         rol_entidades=rol_entidades)


@bp.route('/<int:usuario_id>/gestionar', methods=['GET', 'POST'])
@login_required
@permission_required('prestadores_editar')
def gestionar(usuario_id):
    """Gestionar prestadores asociados a una entidad"""
    entidad = Usuario.query.get_or_404(usuario_id)
    
    # Verificar que sea una entidad
    # Buscar rol ENTIDAD (variantes del nombre)
    rol_entidades = Rol.query.filter(
        or_(
            Rol.nombre == 'ENTIDAD',
            Rol.nombre == 'Entidad',
            Rol.nombre == 'Entidades',
            func.upper(Rol.nombre) == 'ENTIDAD',
            func.lower(Rol.nombre) == 'entidad',
            func.lower(Rol.nombre) == 'entidades'
        )
    ).first()
    if not rol_entidades or entidad.rol_id != rol_entidades.rol_id:
        flash('El usuario seleccionado no es una entidad.', 'error')
        return redirect(url_for('entidades.index'))
    
    if request.method == 'POST':
        try:
            # Obtener prestadores seleccionados del formulario
            prestadores_seleccionados = request.form.getlist('prestadores')
            prestadores_ids = [int(pid) for pid in prestadores_seleccionados if pid.isdigit()]
            
            # Obtener permisos por prestador
            permisos_por_prestador = {}
            for pid in prestadores_ids:
                puede_ver_ambulatorio = request.form.get(f'ambulatorio_{pid}') == 'on'
                puede_ver_internacion = request.form.get(f'internacion_{pid}') == 'on'
                permisos_por_prestador[pid] = {
                    'ambulatorio': puede_ver_ambulatorio,
                    'internacion': puede_ver_internacion
                }
            
            # Eliminar asociaciones existentes para esta entidad
            db.session.execute(
                usuario_prestador.delete().where(
                    usuario_prestador.c.usuario_id == usuario_id
                )
            )
            
            # Crear nuevas asociaciones
            for prestador_id in prestadores_ids:
                permisos = permisos_por_prestador.get(prestador_id, {
                    'ambulatorio': False,  # Default a False
                    'internacion': True    # Default a True
                })
                
                db.session.execute(
                    usuario_prestador.insert().values(
                        usuario_id=usuario_id,
                        prestador_id=prestador_id,
                        fecha_asociacion=datetime.utcnow(),
                        puede_ver_ambulatorio=permisos['ambulatorio'],
                        puede_ver_internacion=permisos['internacion']
                    )
                )
            
            db.session.commit()
            
            # Registrar auditoría
            Auditoria.registrar(
                usuario_id=current_user.usuario_id,
                accion='MODIFICAR',
                tabla='usuario_prestador',
                registro_id=usuario_id,
                descripcion=f'Actualizados prestadores asociados a entidad {entidad.nombre_completo}',
                ip_address=request.remote_addr
            )
            
            flash(f'Prestadores asociados a {entidad.nombre_completo} actualizados correctamente.', 'success')
            return redirect(url_for('entidades.index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar prestadores: {str(e)}', 'error')
    
    # Obtener todos los prestadores activos
    todos_prestadores = Prestador.query.filter_by(activo=True).order_by(Prestador.apellido, Prestador.nombre).all()
    
    # Obtener prestadores actualmente asociados
    prestadores_asociados_ids = db.session.query(usuario_prestador.c.prestador_id).filter(
        usuario_prestador.c.usuario_id == usuario_id
    ).all()
    prestadores_asociados_ids_list = [pid[0] for pid in prestadores_asociados_ids]
    
    # Obtener permisos actuales
    permisos_actuales = {}
    for pid in prestadores_asociados_ids_list:
        permiso = db.session.query(usuario_prestador).filter(
            and_(
                usuario_prestador.c.usuario_id == usuario_id,
                usuario_prestador.c.prestador_id == pid
            )
        ).first()
        if permiso:
            permisos_actuales[pid] = {
                'ambulatorio': permiso.puede_ver_ambulatorio,
                'internacion': permiso.puede_ver_internacion
            }
    
    return render_template('entidades/gestionar.html',
                         entidad=entidad,
                         todos_prestadores=todos_prestadores,
                         prestadores_asociados_ids=prestadores_asociados_ids_list,
                         permisos_actuales=permisos_actuales)
@bp.route('/<int:usuario_id>/eliminar-asociacion/<int:prestador_id>', methods=['POST'])
@login_required
@permission_required('prestadores_editar')
def eliminar_asociacion(usuario_id, prestador_id):
    """Eliminar asociación entre entidad y prestador"""
    try:
        db.session.execute(
            usuario_prestador.delete().where(
                and_(
                    usuario_prestador.c.usuario_id == usuario_id,
                    usuario_prestador.c.prestador_id == prestador_id
                )
            )
        )
        db.session.commit()
        
        entidad = Usuario.query.get(usuario_id)
        prestador = Prestador.query.get(prestador_id)
        
        Auditoria.registrar(
            usuario_id=current_user.usuario_id,
            accion='ELIMINAR',
            tabla='usuario_prestador',
            registro_id=usuario_id,
            descripcion=f'Eliminada asociación entre {entidad.nombre_completo} y {prestador.nombre_completo}',
            ip_address=request.remote_addr
        )
        
        flash(f'Asociación eliminada correctamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar asociación: {str(e)}', 'error')
    
    return redirect(url_for('entidades.gestionar', usuario_id=usuario_id))


@bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
@permission_required('prestadores_editar')
def nuevo():
    """Crear nueva entidad - Usa el formulario de prestadores con es_entidad=True"""
    # Obtener el rol ENTIDAD
    rol_entidades = Rol.query.filter(
        or_(
            Rol.nombre == 'ENTIDAD',
            Rol.nombre == 'Entidad',
            Rol.nombre == 'Entidades',
            func.upper(Rol.nombre) == 'ENTIDAD',
            func.lower(Rol.nombre) == 'entidad',
            func.lower(Rol.nombre) == 'entidades'
        )
    ).first()
    
    if not rol_entidades:
        flash('El rol "ENTIDAD" no existe en el sistema. Ejecute el script de inicialización.', 'warning')
        return redirect(url_for('entidades.index'))
    
    especialidades = Especialidad.query.filter_by(activo=True).order_by(Especialidad.nombre).all()
    
    if request.method == 'POST':
        # Primero crear el prestador con es_entidad = True usando la misma lógica que prestadores
        apellido = request.form.get('apellido', '').strip()
        nombre = request.form.get('nombre', '').strip()
        
        if not apellido or not nombre:
            flash('El apellido y nombre son obligatorios.', 'danger')
            return render_template('prestadores/form.html', especialidades=especialidades, es_entidad=True)
        
        # Validaciones de usuario (username, email, password)
        username = request.form.get('username', '').strip().lower()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        
        if not username or not email or not password:
            flash('Username, email y contraseña son obligatorios para crear la entidad.', 'danger')
            return render_template('prestadores/form.html', especialidades=especialidades, es_entidad=True)
        
        if password != password_confirm:
            flash('Las contraseñas no coinciden.', 'danger')
            return render_template('prestadores/form.html', especialidades=especialidades, es_entidad=True)
        
        if len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'warning')
            return render_template('prestadores/form.html', especialidades=especialidades, es_entidad=True)
        
        # Verificar que el username no exista
        existe = Usuario.query.filter(Usuario.username.ilike(username)).first()
        if existe:
            flash(f'El usuario "{username}" ya existe.', 'danger')
            return render_template('prestadores/form.html', especialidades=especialidades, es_entidad=True)
        
        try:
            # Crear el prestador con es_entidad = True (usando la misma lógica que prestadores.py)
            codigo_raw = request.form.get('codigo', '')
            codigo = codigo_raw.strip() if codigo_raw else ''
            if not codigo or codigo.lower() in ['none', 'null', 'undefined']:
                codigo = None
            
            fecha_mat_obj = None
            fecha_matricula = request.form.get('fecha_matricula')
            if fecha_matricula:
                try:
                    fecha_mat_obj = datetime.strptime(fecha_matricula, '%Y-%m-%d').date()
                    if fecha_mat_obj.year < 1950 or fecha_mat_obj > datetime.now().date():
                        flash('La fecha de matrícula no es válida.', 'danger')
                        return render_template('prestadores/form.html', especialidades=especialidades, es_entidad=True)
                except ValueError:
                    flash('Formato de fecha de matrícula inválido.', 'danger')
                    return render_template('prestadores/form.html', especialidades=especialidades, es_entidad=True)
            
            especialidad_id = request.form.get('especialidad_id')
            
            prestador = Prestador(
                apellido=apellido,
                nombre=nombre,
                codigo=codigo,
                tipo_matricula=request.form.get('tipo_matricula'),
                numero_matricula=request.form.get('numero_matricula'),
                fecha_matricula=fecha_mat_obj,
                especialidad_id=int(especialidad_id) if especialidad_id and especialidad_id != '' and especialidad_id != 'OTRA' else None,
                especialidad_otra=request.form.get('especialidad_otra') if request.form.get('especialidad_otra') else None,
                tipo_documento=request.form.get('tipo_documento'),
                numero_documento=request.form.get('numero_documento'),
                cuit=request.form.get('cuit'),
                direccion=request.form.get('direccion'),
                codigo_postal=request.form.get('codigo_postal'),
                localidad=request.form.get('localidad'),
                provincia=request.form.get('provincia'),
                telefono=request.form.get('telefono'),
                email=email,  # Usar el email del formulario
                es_entidad=True,  # ¡IMPORTANTE! Marcar como entidad
                notificar_email=request.form.get('notificar_email') == 'on',
                notificar_whatsapp=request.form.get('notificar_whatsapp') == 'on',
                notificar_ambulatorio=request.form.get('notificar_ambulatorio') == 'on',
                notificar_internacion=request.form.get('notificar_internacion') == 'on',
                whatsapp=request.form.get('whatsapp', '').strip() or None
            )
            
            db.session.add(prestador)
            db.session.flush()  # Para obtener el prestador_id
            
            # Crear el usuario asociado al prestador
            usuario = Usuario(
                username=username,
                email=email,
                nombre_completo=request.form.get('nombre_completo') or f"{apellido}, {nombre}",
                telefono=request.form.get('telefono'),
                rol_id=rol_entidades.rol_id,
                prestador_id=prestador.prestador_id,
                activo=True
            )
            usuario.set_password(password)
            
            db.session.add(usuario)
            db.session.commit()
            
            Auditoria.registrar(
                usuario_id=current_user.usuario_id,
                accion='CREAR',
                tabla='prestadores',
                registro_id=prestador.prestador_id,
                descripcion=f'Creada entidad (prestador): {prestador.nombre_completo}',
                ip_address=request.remote_addr
            )
            
            Auditoria.registrar(
                usuario_id=current_user.usuario_id,
                accion='CREAR',
                tabla='usuarios',
                registro_id=usuario.usuario_id,
                descripcion=f'Creada entidad (usuario): {usuario.username}',
                ip_address=request.remote_addr
            )
            
            flash(f'Entidad {prestador.nombre_completo} creada correctamente.', 'success')
            return redirect(url_for('entidades.index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear entidad: {str(e)}', 'danger')
            return render_template('prestadores/form.html', especialidades=especialidades, es_entidad=True)
    
    # GET: mostrar formulario de prestadores
    return render_template('prestadores/form.html', especialidades=especialidades, es_entidad=True)


@bp.route('/<int:usuario_id>/editar', methods=['GET', 'POST'])
@login_required
@permission_required('prestadores_editar')
def editar(usuario_id):
    """Editar entidad existente - Usa el formulario de prestadores con es_entidad=True"""
    usuario = Usuario.query.get_or_404(usuario_id)
    
    # Verificar que sea una entidad
    rol_entidades = Rol.query.filter(
        or_(
            Rol.nombre == 'ENTIDAD',
            Rol.nombre == 'Entidad',
            Rol.nombre == 'Entidades',
            func.upper(Rol.nombre) == 'ENTIDAD',
            func.lower(Rol.nombre) == 'entidad',
            func.lower(Rol.nombre) == 'entidades'
        )
    ).first()
    
    if not rol_entidades or usuario.rol_id != rol_entidades.rol_id:
        flash('El usuario seleccionado no es una entidad.', 'error')
        return redirect(url_for('entidades.index'))
    
    # Obtener el prestador asociado a la entidad, o crear uno si no existe
    if not usuario.prestador_id:
        # Si no tiene prestador asociado, crear uno básico
        prestador = Prestador(
            apellido=usuario.nombre_completo.split(',')[0] if usuario.nombre_completo and ',' in usuario.nombre_completo else usuario.nombre_completo or 'Entidad',
            nombre='',
            email=usuario.email,
            telefono=usuario.telefono,
            es_entidad=True,
            activo=True
        )
        db.session.add(prestador)
        db.session.flush()
        usuario.prestador_id = prestador.prestador_id
        db.session.commit()
    else:
        prestador = Prestador.query.get(usuario.prestador_id)
        if not prestador:
            # Si el prestador_id existe pero el prestador no, crear uno nuevo
            prestador = Prestador(
                apellido=usuario.nombre_completo.split(',')[0] if usuario.nombre_completo and ',' in usuario.nombre_completo else usuario.nombre_completo or 'Entidad',
                nombre='',
                email=usuario.email,
                telefono=usuario.telefono,
                es_entidad=True,
                activo=True
            )
            db.session.add(prestador)
            db.session.flush()
            usuario.prestador_id = prestador.prestador_id
            db.session.commit()
        else:
            # Asegurar que el prestador esté marcado como entidad
            if not prestador.es_entidad:
                prestador.es_entidad = True
                db.session.commit()
    
    especialidades = Especialidad.query.filter_by(activo=True).order_by(Especialidad.nombre).all()
    
    if request.method == 'POST':
        try:
            # Actualizar el prestador usando la misma lógica que prestadores.py
            prestador.apellido = request.form.get('apellido')
            prestador.nombre = request.form.get('nombre')
            codigo_raw = request.form.get('codigo', '')
            codigo = codigo_raw.strip() if codigo_raw else ''
            if not codigo or codigo.lower() in ['none', 'null', 'undefined']:
                prestador.codigo = None
            else:
                prestador.codigo = codigo
            prestador.tipo_matricula = request.form.get('tipo_matricula')
            prestador.numero_matricula = request.form.get('numero_matricula')
            
            # Validar fecha
            fecha_mat = request.form.get('fecha_matricula')
            if fecha_mat:
                try:
                    fecha_mat_obj = datetime.strptime(fecha_mat, '%Y-%m-%d').date()
                    if fecha_mat_obj.year < 1950 or fecha_mat_obj > datetime.now().date():
                        raise ValueError("Fecha fuera de rango válido")
                    prestador.fecha_matricula = fecha_mat_obj
                except ValueError as e:
                    flash(f'Fecha de matrícula inválida: {str(e)}', 'danger')
                    return render_template('prestadores/form.html', prestador=prestador, especialidades=especialidades, es_entidad=True, usuario=usuario)
            else:
                prestador.fecha_matricula = None
            
            esp_id = request.form.get('especialidad_id')
            prestador.especialidad_id = int(esp_id) if esp_id and esp_id != '' and esp_id != 'OTRA' else None
            prestador.especialidad_otra = request.form.get('especialidad_otra') if request.form.get('especialidad_otra') else None
            prestador.tipo_documento = request.form.get('tipo_documento')
            prestador.numero_documento = request.form.get('numero_documento')
            prestador.cuit = request.form.get('cuit')
            prestador.direccion = request.form.get('direccion')
            prestador.codigo_postal = request.form.get('codigo_postal')
            prestador.localidad = request.form.get('localidad')
            prestador.provincia = request.form.get('provincia')
            prestador.telefono = request.form.get('telefono')
            prestador.email = request.form.get('email')
            
            # Campos de notificaciones (¡esto es lo que necesitamos!)
            prestador.notificar_email = request.form.get('notificar_email') == 'on'
            prestador.notificar_whatsapp = request.form.get('notificar_whatsapp') == 'on'
            prestador.notificar_ambulatorio = request.form.get('notificar_ambulatorio') == 'on'
            prestador.notificar_internacion = request.form.get('notificar_internacion') == 'on'
            whatsapp = request.form.get('whatsapp', '').strip()
            prestador.whatsapp = whatsapp if whatsapp else None
            
            # Mantener es_entidad = True
            prestador.es_entidad = True
            
            # Actualizar datos del usuario
            usuario.nombre_completo = request.form.get('nombre_completo') or f"{prestador.apellido}, {prestador.nombre}"
            usuario.email = prestador.email
            usuario.telefono = prestador.telefono
            
            # Si se ingresó nueva contraseña
            password = request.form.get('password')
            if password:
                password_confirm = request.form.get('password_confirm')
                if password != password_confirm:
                    flash('Las contraseñas no coinciden.', 'danger')
                    return render_template('prestadores/form.html', prestador=prestador, especialidades=especialidades, es_entidad=True, usuario=usuario)
                if len(password) < 6:
                    flash('La contraseña debe tener al menos 6 caracteres.', 'warning')
                    return render_template('prestadores/form.html', prestador=prestador, especialidades=especialidades, es_entidad=True, usuario=usuario)
                usuario.set_password(password)
            
            db.session.commit()
            
            Auditoria.registrar(
                usuario_id=current_user.usuario_id,
                accion='MODIFICAR',
                tabla='prestadores',
                registro_id=prestador.prestador_id,
                descripcion=f'Modificada entidad (prestador): {prestador.nombre_completo}',
                ip_address=request.remote_addr
            )
            
            Auditoria.registrar(
                usuario_id=current_user.usuario_id,
                accion='MODIFICAR',
                tabla='usuarios',
                registro_id=usuario.usuario_id,
                descripcion=f'Modificada entidad (usuario): {usuario.username}',
                ip_address=request.remote_addr
            )
            
            flash(f'Entidad {prestador.nombre_completo} actualizada correctamente.', 'success')
            return redirect(url_for('entidades.index'))
            
        except Exception as e:
            db.session.rollback()
            import traceback
            flash(f'Error al guardar: {str(e)}', 'danger')
            print(f"Error al guardar entidad: {traceback.format_exc()}")
            return render_template('prestadores/form.html', prestador=prestador, especialidades=especialidades, es_entidad=True, usuario=usuario)
    
    # GET: mostrar formulario de prestadores
    return render_template('prestadores/form.html', prestador=prestador, especialidades=especialidades, es_entidad=True, usuario=usuario)



