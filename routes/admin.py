"""
Rutas de administración del sistema
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from extensions import db
from models.usuario import Usuario, Rol
from models.prestador import Prestador
from models.auditoria import Auditoria
from utils.decorators import admin_required
import unicodedata
from sqlalchemy import func
def _normalizar_texto(valor: str) -> str:
    if not valor:
        return ''
    texto = unicodedata.normalize('NFD', valor.strip().lower())
    return ''.join(ch for ch in texto if unicodedata.category(ch) != 'Mn')


def _rol_requiere_matricula(nombre_rol: str) -> bool:
    normalizado = _normalizar_texto(nombre_rol)
    return normalizado in ['medico', 'prestador']

bp = Blueprint('admin', __name__, url_prefix='/admin')


@bp.route('/')
@login_required
@admin_required
def index():
    """Panel de administración"""
    total_usuarios = Usuario.query.count()
    usuarios_activos = Usuario.query.filter_by(activo=True).count()
    total_roles = Rol.query.filter_by(oculto=False).count()
    from datetime import datetime, timedelta
    limite = datetime.utcnow() - timedelta(days=3)
    mensajes_pendientes = Auditoria.query.filter(
        Auditoria.accion.in_(['ASISTENTE_MENSAJE', 'ASISTENTE_LOGIN_MENSAJE']),
        Auditoria.fecha_hora >= limite
    ).count()
    
    return render_template('admin/index.html',
                         total_usuarios=total_usuarios,
                         usuarios_activos=usuarios_activos,
                         total_roles=total_roles,
                         mensajes_pendientes=mensajes_pendientes)


@bp.route('/usuarios')
@login_required
@admin_required
def usuarios():
    """Gestión de usuarios"""
    page = request.args.get('page', 1, type=int)
    buscar = request.args.get('buscar', '')
    rol_filtro = (request.args.get('rol_id') or '').strip()
    rol_filtro_id = None
    
    query = Usuario.query.join(Rol)
    
    if buscar:
        query = query.filter(
            db.or_(
                Usuario.username.ilike(f'%{buscar}%'),
                Usuario.nombre_completo.ilike(f'%{buscar}%'),
                Usuario.email.ilike(f'%{buscar}%')
            )
        )
    if rol_filtro == 'no_prestador':
        query = query.filter(func.lower(Rol.nombre) != 'prestador')
    elif rol_filtro:
        try:
            rol_id = int(rol_filtro)
            query = query.filter(Usuario.rol_id == rol_id)
            rol_filtro_id = rol_id
        except ValueError:
            pass
    
    usuarios = query.order_by(Usuario.nombre_completo).paginate(
        page=page, per_page=50, error_out=False
    )
    
    roles = Rol.query.filter_by(oculto=False).order_by(Rol.nombre).all()
    
    return render_template('admin/usuarios.html',
                           usuarios=usuarios,
                           buscar=buscar,
                           roles=roles,
                           rol_filtro=rol_filtro,
                           rol_filtro_id=rol_filtro_id)


@bp.route('/usuarios/nuevo', methods=['GET', 'POST'])
@login_required
@admin_required
def usuarios_nuevo():
    """Crear nuevo usuario"""
    prestadores = Prestador.query.filter_by(activo=True).order_by(Prestador.apellido, Prestador.nombre).all()
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        nombre_completo = request.form.get('nombre_completo')
        telefono = request.form.get('telefono')
        rol_id = request.form.get('rol_id')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        matricula_tipo = (request.form.get('matricula_tipo') or '').strip().upper()
        matricula_numero = (request.form.get('matricula_numero') or '').strip()
        especialidad = (request.form.get('especialidad') or '').strip()
        prestador_id = request.form.get('prestador_id', type=int)
        especialidad = (request.form.get('especialidad') or '').strip()
        
        # Validaciones
        if not username or not email or not nombre_completo or not rol_id or not password:
            flash('Todos los campos obligatorios deben completarse.', 'danger')
            roles = Rol.query.filter_by(oculto=False).order_by(Rol.nombre).all()
            return render_template('admin/usuarios_form.html', roles=roles, prestadores=prestadores)
        
        if password != password_confirm:
            flash('Las contraseñas no coinciden.', 'danger')
            roles = Rol.query.filter_by(oculto=False).order_by(Rol.nombre).all()
            return render_template('admin/usuarios_form.html', roles=roles, prestadores=prestadores)
        
        if len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'warning')
            roles = Rol.query.filter_by(oculto=False).order_by(Rol.nombre).all()
            return render_template('admin/usuarios_form.html', roles=roles, prestadores=prestadores)
        
        # Verificar que el username no exista (case-insensitive)
        existe = Usuario.query.filter(Usuario.username.ilike(username)).first()
        if existe:
            flash(f'El usuario "{username}" ya existe.', 'danger')
            roles = Rol.query.filter_by(oculto=False).order_by(Rol.nombre).all()
            return render_template('admin/usuarios_form.html', roles=roles, prestadores=prestadores)
        
        # Verificar que el email no exista
        existe_email = Usuario.query.filter_by(email=email).first()
        if existe_email:
            flash(f'El email "{email}" ya está registrado.', 'danger')
            roles = Rol.query.filter_by(oculto=False).order_by(Rol.nombre).all()
            return render_template('admin/usuarios_form.html', roles=roles, prestadores=prestadores)
        
        try:
            rol = Rol.query.get(int(rol_id))
            if not rol:
                flash('El rol seleccionado no existe.', 'danger')
                roles = Rol.query.filter_by(oculto=False).order_by(Rol.nombre).all()
                return render_template('admin/usuarios_form.html', roles=roles, prestadores=prestadores)
            
            requiere_matricula = _rol_requiere_matricula(rol.nombre)
            if requiere_matricula and not matricula_numero:
                flash('Debe ingresar la matrícula para usuarios con rol Médico o Prestador.', 'danger')
                roles = Rol.query.filter_by(oculto=False).order_by(Rol.nombre).all()
                return render_template('admin/usuarios_form.html', roles=roles, prestadores=prestadores)
            if requiere_matricula and not prestador_id:
                flash('Debe asociar el usuario a un prestador existente.', 'danger')
                roles = Rol.query.filter_by(oculto=False).order_by(Rol.nombre).all()
                return render_template('admin/usuarios_form.html', roles=roles, prestadores=prestadores)
            
            usuario = Usuario(
                username=username.lower(),  # Guardar en minúsculas
                email=email,
                nombre_completo=nombre_completo,
                telefono=telefono,
                rol_id=int(rol_id),
                matricula_tipo=matricula_tipo if requiere_matricula and matricula_numero else None,
                matricula_numero=matricula_numero if requiere_matricula and matricula_numero else None,
                especialidad=especialidad if requiere_matricula and especialidad else None,
                prestador_id=prestador_id if requiere_matricula and prestador_id else None,
                activo=True
            )
            usuario.set_password(password)
            
            db.session.add(usuario)
            db.session.commit()
            
            Auditoria.registrar(
                usuario_id=current_user.usuario_id,
                accion='CREAR',
                tabla='usuarios',
                registro_id=usuario.usuario_id,
                descripcion=f'Creado usuario: {usuario.username}',
                ip_address=request.remote_addr
            )
            
            flash(f'Usuario {usuario.username} creado correctamente.', 'success')
            return redirect(url_for('admin.usuarios'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear usuario: {str(e)}', 'danger')
            roles = Rol.query.filter_by(oculto=False).order_by(Rol.nombre).all()
            return render_template('admin/usuarios_form.html', roles=roles, prestadores=prestadores)
    
    roles = Rol.query.filter_by(oculto=False).order_by(Rol.nombre).all()
    return render_template('admin/usuarios_form.html', roles=roles, prestadores=prestadores)


@bp.route('/usuarios/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@admin_required
def usuarios_editar(id):
    """Editar usuario existente"""
    usuario = Usuario.query.get_or_404(id)
    prestadores = Prestador.query.filter_by(activo=True).order_by(Prestador.apellido, Prestador.nombre).all()
    
    if request.method == 'POST':
        try:
            usuario.nombre_completo = request.form.get('nombre_completo')
            usuario.email = request.form.get('email')
            usuario.telefono = request.form.get('telefono')
            rol_id = request.form.get('rol_id')
            nuevo_rol = Rol.query.get(int(rol_id)) if rol_id else None
            if not nuevo_rol:
                flash('El rol seleccionado no existe.', 'danger')
                roles = Rol.query.filter_by(oculto=False).order_by(Rol.nombre).all()
                return render_template('admin/usuarios_form.html', usuario=usuario, roles=roles, prestadores=prestadores)
            usuario.rol_id = nuevo_rol.rol_id
            
            matricula_tipo = (request.form.get('matricula_tipo') or '').strip().upper()
            matricula_numero = (request.form.get('matricula_numero') or '').strip()
            especialidad = (request.form.get('especialidad') or '').strip()
            prestador_id = request.form.get('prestador_id', type=int)
            requiere_matricula = _rol_requiere_matricula(nuevo_rol.nombre)
            if requiere_matricula and not matricula_numero:
                flash('Debe ingresar la matrícula para usuarios con rol Médico o Prestador.', 'danger')
                roles = Rol.query.filter_by(oculto=False).order_by(Rol.nombre).all()
                return render_template('admin/usuarios_form.html', usuario=usuario, roles=roles, prestadores=prestadores)
            if requiere_matricula and not prestador_id:
                flash('Debe asociar el usuario a un prestador existente.', 'danger')
                roles = Rol.query.filter_by(oculto=False).order_by(Rol.nombre).all()
                return render_template('admin/usuarios_form.html', usuario=usuario, roles=roles, prestadores=prestadores)
            if requiere_matricula:
                usuario.matricula_tipo = matricula_tipo or None
                usuario.matricula_numero = matricula_numero or None
                usuario.especialidad = especialidad or None
                usuario.prestador_id = prestador_id or None
            else:
                usuario.matricula_tipo = None
                usuario.matricula_numero = None
                usuario.especialidad = None
                usuario.prestador_id = None
            
            # Si se ingresó nueva contraseña
            password = request.form.get('password')
            if password:
                password_confirm = request.form.get('password_confirm')
                if password != password_confirm:
                    flash('Las contraseñas no coinciden.', 'danger')
                    roles = Rol.query.filter_by(oculto=False).order_by(Rol.nombre).all()
                    return render_template('admin/usuarios_form.html', usuario=usuario, roles=roles, prestadores=prestadores)
                if len(password) < 6:
                    flash('La contraseña debe tener al menos 6 caracteres.', 'warning')
                    roles = Rol.query.filter_by(oculto=False).order_by(Rol.nombre).all()
                    return render_template('admin/usuarios_form.html', usuario=usuario, roles=roles, prestadores=prestadores)
                usuario.set_password(password)
            
            db.session.commit()
            
            Auditoria.registrar(
                usuario_id=current_user.usuario_id,
                accion='MODIFICAR',
                tabla='usuarios',
                registro_id=usuario.usuario_id,
                descripcion=f'Modificado usuario: {usuario.username}',
                ip_address=request.remote_addr
            )
            
            flash(f'Usuario {usuario.username} actualizado correctamente.', 'success')
            return redirect(url_for('admin.usuarios'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al guardar: {str(e)}', 'danger')
            roles = Rol.query.filter_by(oculto=False).order_by(Rol.nombre).all()
            return render_template('admin/usuarios_form.html', usuario=usuario, roles=roles, prestadores=prestadores)
    
    roles = Rol.query.filter_by(oculto=False).order_by(Rol.nombre).all()
    return render_template('admin/usuarios_form.html', usuario=usuario, roles=roles, prestadores=prestadores)


@bp.route('/usuarios/<int:id>/toggle')
@login_required
@admin_required
def usuarios_toggle(id):
    """Activar/desactivar usuario"""
    usuario = Usuario.query.get_or_404(id)
    
    # No se puede desactivar a sí mismo
    if usuario.usuario_id == current_user.usuario_id:
        flash('No puede desactivar su propio usuario.', 'warning')
        return redirect(url_for('admin.usuarios'))
    
    # No se puede desactivar al super administrador
    if usuario.rol.nombre == 'OSCAR':
        flash('No se puede desactivar al super administrador.', 'danger')
        return redirect(url_for('admin.usuarios'))
    
    usuario.activo = not usuario.activo
    db.session.commit()
    
    accion = 'activado' if usuario.activo else 'desactivado'
    flash(f'Usuario {usuario.username} {accion} correctamente.', 'success')
    return redirect(url_for('admin.usuarios'))


@bp.route('/roles')
@login_required
@admin_required
def roles():
    """Gestión de roles y permisos - Redirige al gestor"""
    return redirect(url_for('admin.gestor_roles'))


@bp.route('/configuracion')
@login_required
@admin_required
def configuracion():
    """Configuración del sistema"""
    from models.configuracion import Configuracion
    
    # Obtener configuración actual
    config = {
        'laboratorio_nombre': Configuracion.get('laboratorio_nombre', ''),
        'laboratorio_direccion': Configuracion.get('laboratorio_direccion', ''),
        'laboratorio_telefono': Configuracion.get('laboratorio_telefono', ''),
        'laboratorio_ciudad': Configuracion.get('laboratorio_ciudad', ''),
        'laboratorio_email': Configuracion.get('laboratorio_email', ''),
        'items_per_pagina': Configuracion.get('items_per_pagina', '50'),
        'session_timeout': Configuracion.get('session_timeout', '8'),
        'debug_mode': Configuracion.get('debug_mode', 'false'),
        'maintenance_mode': Configuracion.get('maintenance_mode', 'false'),
        'reporte_footer': Configuracion.get('reporte_footer', ''),
        'mostrar_logo_reporte': Configuracion.get('mostrar_logo_reporte', 'true')
    }
    
    # Información de la base de datos
    from models.usuario import Usuario
    from models.protocolo import Protocolo
    from models.paciente import Afiliado
    from datetime import datetime
    
    db_info = {
        'total_usuarios': Usuario.query.count(),
        'total_protocolos': Protocolo.query.count(),
        'total_pacientes': Afiliado.query.count(),
        'total_tablas': 38  # Número aproximado de tablas
    }
    
    # Fecha actual formateada
    moment_actual = datetime.now().strftime('%d/%m/%Y %H:%M')
    
    return render_template('admin/configuracion.html', config=config, db_info=db_info, moment_actual=moment_actual)


@bp.route('/configuracion/guardar', methods=['POST'])
@login_required
@admin_required
def guardar_configuracion():
    """Guardar configuración del sistema"""
    try:
        from models.configuracion import Configuracion
        from flask import request, jsonify
        import os
        from werkzeug.utils import secure_filename
        
        # Verificar si es subida de archivo (FormData) o JSON
        if request.files:
            # Manejar subida de archivo
            logo_file = request.files.get('logo')
            tipo = request.form.get('tipo')
            
            if logo_file and logo_file.filename:
                # Crear directorio si no existe
                upload_dir = os.path.join('static', 'img')
                os.makedirs(upload_dir, exist_ok=True)
                
                # Guardar archivo como logo.png
                filename = 'logo.png'
                filepath = os.path.join(upload_dir, filename)
                logo_file.save(filepath)
                
                print(f"✅ Logo guardado en: {filepath}")
            
            # Obtener datos del formulario
            data = dict(request.form)
            print(f"🔍 DEBUG - Datos recibidos (archivo): {data}")
            
        else:
            # Manejar JSON normal
            data = request.get_json()
            print(f"🔍 DEBUG - Datos recibidos (JSON): {data}")
            tipo = data.get('tipo')
        
        if tipo == 'laboratorio':
            # Guardar configuración del laboratorio
            configuraciones = [
                ('laboratorio_nombre', data.get('laboratorio_nombre', ''), 'STRING', 'Nombre del laboratorio', 'LABORATORIO'),
                ('laboratorio_direccion', data.get('laboratorio_direccion', ''), 'STRING', 'Dirección del laboratorio', 'LABORATORIO'),
                ('laboratorio_telefono', data.get('laboratorio_telefono', ''), 'STRING', 'Teléfono del laboratorio', 'LABORATORIO'),
                ('laboratorio_ciudad', data.get('laboratorio_ciudad', ''), 'STRING', 'Ciudad del laboratorio', 'LABORATORIO'),
                ('laboratorio_email', data.get('laboratorio_email', ''), 'STRING', 'Email del laboratorio', 'LABORATORIO')
            ]
            
        elif tipo == 'sistema':
            # Guardar configuración del sistema
            configuraciones = [
                ('items_per_pagina', data.get('items_per_pagina', '50'), 'INTEGER', 'Items por página', 'SISTEMA'),
                ('session_timeout', data.get('session_timeout', '8'), 'INTEGER', 'Timeout de sesión en horas', 'SISTEMA'),
                ('debug_mode', 'true' if data.get('debug_mode') else 'false', 'BOOLEAN', 'Modo debug', 'SISTEMA'),
                ('maintenance_mode', 'true' if data.get('maintenance_mode') else 'false', 'BOOLEAN', 'Modo mantenimiento', 'SISTEMA')
            ]
            
        elif tipo == 'reportes':
            # Guardar configuración de reportes
            configuraciones = [
                ('reporte_footer', data.get('reporte_footer', ''), 'STRING', 'Pie de página de reportes', 'REPORTES'),
                ('mostrar_logo_reporte', 'true' if data.get('mostrar_logo_reporte') else 'false', 'BOOLEAN', 'Mostrar logo en reportes', 'REPORTES')
            ]
        else:
            return jsonify({'success': False, 'error': 'Tipo de configuración no válido'}), 400
        
        # Guardar configuraciones
        for clave, valor, tipo_dato, descripcion, categoria in configuraciones:
            config_existente = Configuracion.query.filter_by(clave=clave).first()
            if config_existente:
                config_existente.valor = valor
            else:
                nueva_config = Configuracion(
                    clave=clave,
                    valor=valor,
                    tipo=tipo_dato,
                    descripcion=descripcion,
                    categoria=categoria
                )
                db.session.add(nueva_config)
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Configuración guardada correctamente'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/roles/gestor')
@login_required
@admin_required
def gestor_roles():
    """Gestor visual de roles y permisos"""
    from models.usuario import Rol, Permiso
    
    # Obtener roles y permisos (excluir OSCAR)
    roles = Rol.query.filter(Rol.nombre != 'OSCAR').order_by(Rol.nombre).all()
    permisos = Permiso.query.order_by(Permiso.modulo, Permiso.nombre).all()
    
    # Agrupar permisos por módulo
    permisos_por_modulo = {}
    for permiso in permisos:
        modulo = permiso.modulo or 'General'
        if modulo not in permisos_por_modulo:
            permisos_por_modulo[modulo] = []
        permisos_por_modulo[modulo].append(permiso)
    
    # Convertir objetos a diccionarios para JSON
    roles_dict = []
    for rol in roles:
        roles_dict.append({
            'rol_id': rol.rol_id,
            'nombre': rol.nombre,
            'descripcion': rol.descripcion,
            'oculto': rol.oculto
        })
    
    permisos_dict = []
    for permiso in permisos:
        permisos_dict.append({
            'permiso_id': permiso.permiso_id,
            'codigo': permiso.codigo,
            'nombre': permiso.nombre,
            'modulo': permiso.modulo
        })
    
    return render_template('admin/roles_gestor.html', 
                         roles=roles, 
                         roles_json=roles_dict,
                         permisos=permisos,
                         permisos_json=permisos_dict,
                         permisos_por_modulo=permisos_por_modulo)


@bp.route('/roles/cambiar-permiso', methods=['POST'])
@login_required
@admin_required
def cambiar_permiso_rol():
    """Cambiar permiso de un rol"""
    try:
        from models.usuario import Rol, Permiso
        from flask import request, jsonify
        
        data = request.get_json()
        rol_id = data.get('rol_id')
        permiso_id = data.get('permiso_id')
        tiene_permiso = data.get('tiene_permiso')
        
        rol = Rol.query.get(rol_id)
        permiso = Permiso.query.get(permiso_id)
        
        if not rol or not permiso:
            return jsonify({'success': False, 'error': 'Rol o permiso no encontrado'}), 404
        
        if tiene_permiso:
            if permiso not in rol.permisos:
                rol.permisos.append(permiso)
        else:
            if permiso in rol.permisos:
                rol.permisos.remove(permiso)
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Permiso actualizado correctamente'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/roles/crear', methods=['POST'])
@login_required
@admin_required
def crear_rol():
    """Crear nuevo rol"""
    try:
        from models.usuario import Rol
        from flask import request, jsonify
        
        data = request.get_json()
        nombre = data.get('nombre')
        descripcion = data.get('descripcion', '')
        oculto = data.get('oculto', False)
        
        if not nombre:
            return jsonify({'success': False, 'error': 'El nombre del rol es requerido'}), 400
        
        # Verificar que no exista
        rol_existente = Rol.query.filter_by(nombre=nombre).first()
        if rol_existente:
            return jsonify({'success': False, 'error': 'Ya existe un rol con ese nombre'}), 400
        
        nuevo_rol = Rol(
            nombre=nombre,
            descripcion=descripcion,
            oculto=oculto
        )
        
        db.session.add(nuevo_rol)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Rol creado correctamente'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/roles/editar/<int:rol_id>', methods=['PUT'])
@login_required
@admin_required
def editar_rol(rol_id):
    """Editar rol existente"""
    try:
        from models.usuario import Rol
        from flask import request, jsonify
        
        rol = Rol.query.get(rol_id)
        if not rol:
            return jsonify({'success': False, 'error': 'Rol no encontrado'}), 404
        
        data = request.get_json()
        nombre = data.get('nombre')
        descripcion = data.get('descripcion', '')
        oculto = data.get('oculto', False)
        
        if not nombre:
            return jsonify({'success': False, 'error': 'El nombre del rol es requerido'}), 400
        
        # Verificar que no exista otro rol con el mismo nombre
        rol_existente = Rol.query.filter(Rol.nombre == nombre, Rol.rol_id != rol_id).first()
        if rol_existente:
            return jsonify({'success': False, 'error': 'Ya existe un rol con ese nombre'}), 400
        
        rol.nombre = nombre
        rol.descripcion = descripcion
        rol.oculto = oculto
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Rol actualizado correctamente'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/roles/eliminar/<int:rol_id>', methods=['DELETE'])
@login_required
@admin_required
def eliminar_rol(rol_id):
    """Eliminar rol"""
    try:
        from models.usuario import Rol
        from flask import jsonify
        
        rol = Rol.query.get(rol_id)
        if not rol:
            return jsonify({'success': False, 'error': 'Rol no encontrado'}), 404
        
        # Verificar que no esté en uso
        if rol.usuarios:
            return jsonify({'success': False, 'error': 'No se puede eliminar un rol que tiene usuarios asignados'}), 400
        
        # No permitir eliminar roles del sistema
        if rol.nombre in ['OSCAR', 'Administrador'] or _rol_requiere_matricula(rol.nombre):
            return jsonify({'success': False, 'error': 'No se puede eliminar un rol del sistema'}), 400
        
        db.session.delete(rol)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Rol eliminado correctamente'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/disenios-informes')
@login_required
@admin_required
def disenios_informes():
    """Gestor de diseños de informes"""
    from models.informe import DisenioInforme
    
    # Obtener todos los diseños activos, agrupados por tipo
    disenios = DisenioInforme.query.filter_by(activo=True).order_by(
        DisenioInforme.tipo_estudio, DisenioInforme.es_default.desc(), DisenioInforme.nombre
    ).all()
    
    # Agrupar por tipo de estudio
    disenios_por_tipo = {}
    for disenio in disenios:
        tipo = disenio.tipo_estudio
        if tipo not in disenios_por_tipo:
            disenios_por_tipo[tipo] = []
        disenios_por_tipo[tipo].append(disenio)
    
    return render_template('admin/disenios_informes.html', 
                         disenios_por_tipo=disenios_por_tipo,
                         tipos_estudio=['PAP', 'BIOPSIA', 'CITOLOGÍA'])


@bp.route('/disenios-informes/nuevo', methods=['GET', 'POST'])
@login_required
@admin_required
def disenios_informes_nuevo():
    """Crear nuevo diseño de informe"""
    from models.informe import DisenioInforme
    
    if request.method == 'POST':
        try:
            data = request.get_json()
            
            # Crear nuevo diseño
            disenio = DisenioInforme(
                nombre=data.get('nombre'),
                tipo_estudio=data.get('tipo_estudio'),
                activo=True,
                es_default=data.get('es_default', False),
                usuario_creador_id=current_user.usuario_id
            )
            
            # Si es default, desactivar otros defaults del mismo tipo
            if disenio.es_default:
                DisenioInforme.query.filter_by(
                    tipo_estudio=disenio.tipo_estudio,
                    es_default=True
                ).update({'es_default': False})
            
            # Establecer configuración
            config = data.get('configuracion', {})
            disenio.set_configuracion(config)
            
            db.session.add(disenio)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Diseño creado correctamente',
                'disenio_id': disenio.disenio_id
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # GET: retornar formulario
    return jsonify({'success': False, 'error': 'Método no permitido'}), 405


@bp.route('/disenios-informes/<int:disenio_id>')
@login_required
@admin_required
def disenios_informes_editar(disenio_id):
    """Editor de diseño de informe"""
    from models.informe import DisenioInforme
    
    disenio = DisenioInforme.query.get_or_404(disenio_id)
    config = disenio.get_configuracion()
    
    # Mapeo de títulos según tipo de estudio
    titulos_por_tipo = {
        'PAP': 'INFORME DE CITOLOGÍA CERVICOVAGINAL',
        'BIOPSIA': 'INFORME DE ANATOMÍA PATOLÓGICA',
        'CITOLOGÍA': 'INFORME DE CITOLOGÍA'
    }
    subtitulos_por_tipo = {
        'PAP': 'PAP - Papanicolaou',
        'BIOPSIA': 'BIOPSIA',
        'CITOLOGÍA': 'CITOLOGÍA'
    }
    
    return render_template('admin/editor_disenio_informe.html',
                         disenio=disenio,
                         configuracion=config,
                         titulo_reporte=titulos_por_tipo.get(disenio.tipo_estudio, 'INFORME'),
                         subtitulo_reporte=subtitulos_por_tipo.get(disenio.tipo_estudio, ''))


@bp.route('/disenios-informes/<int:disenio_id>/guardar', methods=['POST'])
@login_required
@admin_required
def disenios_informes_guardar(disenio_id):
    """Guardar configuración de diseño"""
    from models.informe import DisenioInforme
    
    try:
        disenio = DisenioInforme.query.get_or_404(disenio_id)
        data = request.get_json()
        
        # Actualizar nombre y estado
        if 'nombre' in data:
            disenio.nombre = data['nombre']
        if 'es_default' in data:
            disenio.es_default = data['es_default']
            # Si se marca como default, desactivar otros defaults del mismo tipo
            if disenio.es_default:
                DisenioInforme.query.filter(
                    DisenioInforme.disenio_id != disenio_id,
                    DisenioInforme.tipo_estudio == disenio.tipo_estudio,
                    DisenioInforme.es_default == True
                ).update({'es_default': False})
        
        # Actualizar configuración
        if 'configuracion' in data:
            disenio.set_configuracion(data['configuracion'])
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Diseño guardado correctamente'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/disenios-informes/<int:disenio_id>/eliminar', methods=['DELETE'])
@login_required
@admin_required
def disenios_informes_eliminar(disenio_id):
    """Eliminar diseño (soft delete)"""
    from models.informe import DisenioInforme
    
    try:
        disenio = DisenioInforme.query.get_or_404(disenio_id)
        
        # Soft delete (desactivar)
        disenio.activo = False
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Diseño eliminado correctamente'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/disenios-informes/<int:disenio_id>/preview')
@login_required
@admin_required
def disenios_informes_preview(disenio_id):
    """Vista previa de un diseño con un protocolo de ejemplo"""
    from models.informe import DisenioInforme
    from models.protocolo import Protocolo
    
    disenio = DisenioInforme.query.get_or_404(disenio_id)
    
    # Buscar un protocolo de ejemplo del mismo tipo
    protocolo = Protocolo.query.filter_by(
        tipo_estudio=disenio.tipo_estudio
    ).first()
    
    if not protocolo:
        flash('No hay protocolos de ejemplo para este tipo de estudio', 'warning')
        return redirect(url_for('admin.disenios_informes'))
    
    # Redirigir a la vista previa del informe con el diseño seleccionado
    return redirect(url_for('plantillas_dinamicas.preview_plantilla',
                          protocolo_id=protocolo.protocolo_id,
                          disenio_id=disenio_id))


@bp.route('/disenios-informes/nuevo/visual')
@bp.route('/disenios-informes/<int:disenio_id>/visual')
@login_required
@admin_required
def disenios_informes_visual(disenio_id=None):
    """Editor visual drag-and-drop para diseños de informes"""
    from models.informe import DisenioInforme
    
    # Si no hay ID, crear un diseño temporal para editar
    if disenio_id:
        disenio = DisenioInforme.query.get_or_404(disenio_id)
        config = disenio.get_configuracion()
        tipo_estudio = disenio.tipo_estudio
    else:
        # Crear diseño temporal (no se guarda hasta que el usuario lo guarde)
        # Obtener tipo de estudio desde parámetro URL
        tipo_estudio_param = request.args.get('tipo', 'PAP')
        if tipo_estudio_param not in ['PAP', 'BIOPSIA', 'CITOLOGÍA']:
            tipo_estudio_param = 'PAP'
        
        disenio = None
        from models.informe import DisenioInforme as DI
        temp_disenio = DI()
        config = temp_disenio._get_default_config()
        tipo_estudio = tipo_estudio_param
    
    # Mapeo de títulos según tipo de estudio
    titulos_por_tipo = {
        'PAP': 'INFORME DE CITOLOGÍA CERVICOVAGINAL',
        'BIOPSIA': 'INFORME DE ANATOMÍA PATOLÓGICA',
        'CITOLOGÍA': 'INFORME DE CITOLOGÍA'
    }
    subtitulos_por_tipo = {
        'PAP': 'PAP - Papanicolaou',
        'BIOPSIA': 'BIOPSIA',
        'CITOLOGÍA': 'CITOLOGÍA'
    }
    
    # Crear objeto temporal si no existe
    if not disenio:
        # Capturar tipo_estudio en una variable local para usarla en la clase
        tipo_estudio_valor = tipo_estudio
        class TempDisenio:
            disenio_id = None
            nombre = 'Nuevo Diseño'
            tipo_estudio = tipo_estudio_valor
            es_default = False
        disenio = TempDisenio()
    
    return render_template('admin/editor_visual_disenio.html',
                         disenio=disenio,
                         configuracion=config,
                         titulo_reporte=titulos_por_tipo.get(tipo_estudio, 'INFORME'),
                         subtitulo_reporte=subtitulos_por_tipo.get(tipo_estudio, ''))


@bp.route('/disenios-informes/<int:disenio_id>/guardar-estructura', methods=['POST'])
@login_required
@admin_required
def disenios_informes_guardar_estructura(disenio_id):
    """Guardar la estructura del diseño desde el editor visual"""
    from models.informe import DisenioInforme
    import json
    
    try:
        data = request.get_json()
        
        # Obtener datos del formulario
        nombre = data.get('nombre', '').strip()
        tipo_estudio = data.get('tipo_estudio')
        es_default = data.get('es_default', False)
        
        if not nombre:
            return jsonify({'success': False, 'error': 'El nombre del diseño es requerido'}), 400
        
        if not tipo_estudio:
            return jsonify({'success': False, 'error': 'El tipo de estudio es requerido'}), 400
        
        # Verificar si se está editando un diseño existente o creando uno nuevo
        if disenio_id and disenio_id > 0:
            disenio = DisenioInforme.query.get(disenio_id)
            if not disenio:
                return jsonify({'success': False, 'error': 'Diseño no encontrado'}), 404
            # Actualizar diseño existente
            disenio.nombre = nombre
            disenio.tipo_estudio = tipo_estudio
            disenio.es_default = es_default
        else:
            # Crear nuevo diseño
            disenio = DisenioInforme(
                nombre=nombre,
                tipo_estudio=tipo_estudio,
                activo=True,
                es_default=es_default,
                usuario_creador_id=current_user.usuario_id
            )
        
        # Guardar primero para obtener el ID si es nuevo
        db.session.add(disenio)
        db.session.flush()  # Para obtener el ID sin hacer commit aún
        
        # Si es default, desactivar otros defaults del mismo tipo
        if es_default:
            DisenioInforme.query.filter_by(
                tipo_estudio=tipo_estudio,
                es_default=True
            ).filter(DisenioInforme.disenio_id != disenio.disenio_id).update({'es_default': False})
        
        # Obtener estructura y configuración
        estructura = data.get('estructura', [])
        # Debug: verificar qué elementos de datos se están recibiendo
        elementos_datos = [el for el in estructura if el.get('tipo') in ['protocolo-fecha', 'datos-paciente', 'datos-medico']]
        print(f"🔍 DEBUG - Elementos de datos recibidos: {len(elementos_datos)}")
        for el in elementos_datos:
            print(f"  - {el.get('tipo')}: {el.get('contenido')}")
        print(f"🔍 DEBUG - Total elementos en estructura: {len(estructura)}")
        configuracion_completa = data.get('configuracion')
        
        if configuracion_completa:
            # Si viene la configuración completa, usar esa
            configuracion_actual = configuracion_completa
        else:
            # Si no, usar la actual y solo actualizar estructura
            if disenio.disenio_id:
                configuracion_actual = disenio.get_configuracion()
            else:
                from models.informe import DisenioInforme as DI
                configuracion_actual = DI()._get_default_config()
        
        # Agregar/actualizar estructura visual
        configuracion_actual['estructura_visual'] = estructura
        
        # Guardar configuración
        disenio.set_configuracion(configuracion_actual)
        # Si es nuevo, ya está agregado arriba, solo hacer commit
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Estructura guardada correctamente',
            'disenio_id': disenio.disenio_id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/asistente/mensajes')
@login_required
@admin_required
def asistente_mensajes():
    page = request.args.get('page', 1, type=int)
    tipo = request.args.get('tipo', '')
    buscar = request.args.get('buscar', '')
    acciones = ['ASISTENTE_MENSAJE', 'ASISTENTE_LOGIN_MENSAJE']
    query = Auditoria.query.filter(Auditoria.accion.in_(acciones))
    if tipo in acciones:
        query = query.filter(Auditoria.accion == tipo)
    if buscar:
        like = f"%{buscar}%"
        query = query.filter(Auditoria.descripcion.ilike(like))
    mensajes = query.order_by(Auditoria.fecha_hora.desc()).paginate(page=page, per_page=25, error_out=False)
    return render_template('admin/asistente_mensajes.html', mensajes=mensajes, tipo=tipo, buscar=buscar)


@bp.route('/auditoria')
@login_required
@admin_required
def auditoria_general():
    page = request.args.get('page', 1, type=int)
    accion = request.args.get('accion', '')
    usuario_id = request.args.get('usuario_id', type=int)
    buscar = request.args.get('buscar', '')
    fecha_desde = request.args.get('desde', '')
    fecha_hasta = request.args.get('hasta', '')
    query = Auditoria.query
    if accion:
        query = query.filter(Auditoria.accion == accion)
    if usuario_id:
        query = query.filter(Auditoria.usuario_id == usuario_id)
    if buscar:
        like = f"%{buscar}%"
        query = query.filter(Auditoria.descripcion.ilike(like))
    from datetime import datetime
    if fecha_desde:
        try:
            fecha_ini = datetime.strptime(fecha_desde, '%Y-%m-%d')
            query = query.filter(Auditoria.fecha_hora >= fecha_ini)
        except ValueError:
            pass
    if fecha_hasta:
        try:
            fecha_fin = datetime.strptime(fecha_hasta, '%Y-%m-%d')
            query = query.filter(Auditoria.fecha_hora <= fecha_fin)
        except ValueError:
            pass
    registros = query.order_by(Auditoria.fecha_hora.desc()).paginate(page=page, per_page=50, error_out=False)
    acciones_disponibles = [row[0] for row in db.session.query(Auditoria.accion).distinct().order_by(Auditoria.accion).all()]
    usuarios = Usuario.query.order_by(Usuario.nombre_completo).all()
    return render_template('admin/auditoria.html', auditorias=registros, acciones=acciones_disponibles, usuarios=usuarios,
                           accion=accion, usuario_id=usuario_id, buscar=buscar, desde=fecha_desde, hasta=fecha_hasta)

