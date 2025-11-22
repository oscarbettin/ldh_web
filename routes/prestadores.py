"""
Rutas de gestión de prestadores (médicos)
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from extensions import db
from models.prestador import Prestador, Especialidad
from models.usuario import Usuario, Rol
from models.auditoria import Auditoria
from datetime import datetime
import unicodedata

bp = Blueprint('prestadores', __name__, url_prefix='/prestadores')


def _normalizar_texto(valor: str) -> str:
    if not valor:
        return ''
    texto = unicodedata.normalize('NFD', valor.strip().lower())
    return ''.join(ch for ch in texto if unicodedata.category(ch) != 'Mn')


def _sugerir_username(prestador: Prestador) -> str:
    base_apellido = _normalizar_texto(prestador.apellido).replace(' ', '').replace("'", '')
    inicial_nombre = _normalizar_texto(prestador.nombre)[:1]
    base = (base_apellido + inicial_nombre) or f'prestador{prestador.prestador_id}'
    username = base
    sufijo = 1
    while Usuario.query.filter(Usuario.username.ilike(username)).first():
        username = f'{base}{sufijo}'
        sufijo += 1
    return username


def _generar_email(username: str, email_original: str | None) -> str:
    if email_original:
        candidato = email_original.strip()
        if candidato:
            existente = Usuario.query.filter_by(email=candidato).first()
            if not existente:
                return candidato
    base = f'{username}@prestadores.ldh'
    email = base
    sufijo = 1
    while Usuario.query.filter_by(email=email).first():
        email = f'{username}{sufijo}@prestadores.ldh'
        sufijo += 1
    return email


@bp.route('/')
@login_required
def index():
    """Listado de prestadores"""
    page = request.args.get('page', 1, type=int)
    buscar = request.args.get('buscar', '')
    
    query = Prestador.query
    
    if buscar:
        query = query.filter(
            db.or_(
                Prestador.apellido.ilike(f'%{buscar}%'),
                Prestador.nombre.ilike(f'%{buscar}%'),
                Prestador.numero_matricula.ilike(f'%{buscar}%')
            )
        )
    
    prestadores = query.order_by(Prestador.apellido, Prestador.nombre).paginate(
        page=page, per_page=50, error_out=False
    )
    
    return render_template('prestadores/index.html', prestadores=prestadores, buscar=buscar)


@bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo():
    """Crear nuevo prestador"""
    if request.method == 'POST':
        apellido = request.form.get('apellido')
        nombre = request.form.get('nombre')
        codigo = request.form.get('codigo')
        tipo_matricula = request.form.get('tipo_matricula')
        numero_matricula = request.form.get('numero_matricula')
        fecha_matricula = request.form.get('fecha_matricula')
        especialidad_id = request.form.get('especialidad_id')
        especialidad_otra = request.form.get('especialidad_otra')
        tipo_documento = request.form.get('tipo_documento')
        numero_documento = request.form.get('numero_documento')
        cuit = request.form.get('cuit')
        direccion = request.form.get('direccion')
        codigo_postal = request.form.get('codigo_postal')
        localidad = request.form.get('localidad')
        provincia = request.form.get('provincia')
        telefono = request.form.get('telefono')
        email = request.form.get('email')
        
        if not apellido or not nombre:
            flash('El apellido y nombre son obligatorios.', 'danger')
            especialidades = Especialidad.query.filter_by(activo=True).order_by(Especialidad.nombre).all()
            return render_template('prestadores/form.html', especialidades=especialidades)
        
        # Validar fecha de matrícula
        fecha_mat_obj = None
        if fecha_matricula:
            try:
                fecha_mat_obj = datetime.strptime(fecha_matricula, '%Y-%m-%d').date()
                if fecha_mat_obj.year < 1950 or fecha_mat_obj > datetime.now().date():
                    flash('La fecha de matrícula no es válida.', 'danger')
                    especialidades = Especialidad.query.filter_by(activo=True).order_by(Especialidad.nombre).all()
                    return render_template('prestadores/form.html', especialidades=especialidades)
            except ValueError:
                flash('Formato de fecha de matrícula inválido.', 'danger')
                especialidades = Especialidad.query.filter_by(activo=True).order_by(Especialidad.nombre).all()
                return render_template('prestadores/form.html', especialidades=especialidades)
        
        try:
            prestador = Prestador(
                apellido=apellido,
                nombre=nombre,
                codigo=codigo,
                tipo_matricula=tipo_matricula,
                numero_matricula=numero_matricula,
                fecha_matricula=fecha_mat_obj,
                especialidad_id=int(especialidad_id) if especialidad_id and especialidad_id != '' and especialidad_id != 'OTRA' else None,
                especialidad_otra=especialidad_otra if especialidad_otra else None,
                tipo_documento=tipo_documento,
                numero_documento=numero_documento,
                cuit=cuit,
                direccion=direccion,
                codigo_postal=codigo_postal,
                localidad=localidad,
                provincia=provincia,
                telefono=telefono,
                email=email
            )
        except Exception as e:
            flash(f'Error al crear prestador: {str(e)}', 'danger')
            especialidades = Especialidad.query.filter_by(activo=True).order_by(Especialidad.nombre).all()
            return render_template('prestadores/form.html', especialidades=especialidades)
        
        db.session.add(prestador)
        db.session.commit()
        
        Auditoria.registrar(
            usuario_id=current_user.usuario_id,
            accion='CREAR',
            tabla='prestadores',
            registro_id=prestador.prestador_id,
            descripcion=f'Creado prestador: {prestador.nombre_completo}',
            ip_address=request.remote_addr
        )
        
        flash(f'Prestador {prestador.nombre_completo} creado correctamente.', 'success')
        return redirect(url_for('prestadores.index'))
    
    especialidades = Especialidad.query.filter_by(activo=True).order_by(Especialidad.nombre).all()
    return render_template('prestadores/form.html', especialidades=especialidades)


@bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar(id):
    """Editar prestador existente"""
    prestador = Prestador.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            prestador.apellido = request.form.get('apellido')
            prestador.nombre = request.form.get('nombre')
            prestador.codigo = request.form.get('codigo')
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
                    especialidades = Especialidad.query.filter_by(activo=True).order_by(Especialidad.nombre).all()
                    return render_template('prestadores/form.html', prestador=prestador, especialidades=especialidades)
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
            
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f'Error al guardar: {str(e)}', 'danger')
            especialidades = Especialidad.query.filter_by(activo=True).order_by(Especialidad.nombre).all()
            return render_template('prestadores/form.html', prestador=prestador, especialidades=especialidades)
        
        Auditoria.registrar(
            usuario_id=current_user.usuario_id,
            accion='MODIFICAR',
            tabla='prestadores',
            registro_id=prestador.prestador_id,
            descripcion=f'Modificado prestador: {prestador.nombre_completo}',
            ip_address=request.remote_addr
        )
        
        flash(f'Prestador {prestador.nombre_completo} actualizado correctamente.', 'success')
        return redirect(url_for('prestadores.index'))
    
    especialidades = Especialidad.query.filter_by(activo=True).order_by(Especialidad.nombre).all()
    return render_template('prestadores/form.html', prestador=prestador, especialidades=especialidades)


@bp.route('/<int:id>/ver')
@login_required
def ver(id):
    """Ver detalle de prestador"""
    prestador = Prestador.query.get_or_404(id)
    return render_template('prestadores/ver.html', prestador=prestador)


@bp.route('/<int:id>/toggle')
@login_required
def toggle_activo(id):
    """Activar/desactivar prestador"""
    prestador = Prestador.query.get_or_404(id)
    prestador.activo = not prestador.activo
    db.session.commit()
    
    accion = 'activado' if prestador.activo else 'desactivado'
    flash(f'Prestador {prestador.nombre_completo} {accion} correctamente.', 'success')
    return redirect(url_for('prestadores.index'))


@bp.route('/buscar-json')
@login_required
def buscar_json():
    """Buscar prestadores para autocomplete (AJAX)"""
    termino = request.args.get('q', '')
    
    if len(termino) < 2:
        return jsonify([])
    
    prestadores = Prestador.query.filter(
        db.or_(
            Prestador.nombre.ilike(f'%{termino}%'),
            Prestador.numero_matricula.ilike(f'%{termino}%')
        ),
        Prestador.activo == True
    ).limit(20).all()
    
    resultados = [{
        'id': p.prestador_id,
        'text': p.nombre_con_matricula,
        'apellido': p.apellido,
        'nombre': p.nombre,
        'matricula': p.numero_matricula,
        'especialidad': p.nombre_especialidad
    } for p in prestadores]
    
    return jsonify(resultados)


@bp.route('/<int:prestador_id>/generar-usuario', methods=['POST'])
@login_required
def generar_usuario(prestador_id):
    """Crear un usuario del sistema a partir de un prestador."""
    prestador = Prestador.query.get_or_404(prestador_id)
    
    # Verificar si ya existe un usuario asociado
    if prestador.usuarios:
        return jsonify({
            'success': False,
            'error': 'Este prestador ya tiene un usuario asociado.'
        }), 409
    
    rol_prestador = Rol.query.filter(Rol.nombre.ilike('prestador')).first()
    if not rol_prestador:
        return jsonify({
            'success': False,
            'error': 'No se encontró el rol Prestador en el sistema.'
        }), 400
    
    password = None
    datos = request.get_json(silent=True) or {}
    if prestador.numero_documento:
        password = prestador.numero_documento.strip().split('.')[0]
    else:
        password = (datos.get('password') or '').strip()
        if not password:
            return jsonify({
                'success': False,
                'require_password': True,
                'error': 'Se requiere una contraseña cuando el prestador no tiene DNI registrado.'
            }), 400
        if len(password) < 6:
            return jsonify({
                'success': False,
                'require_password': True,
                'error': 'La contraseña debe tener al menos 6 caracteres.'
            }), 400
    
    username = _sugerir_username(prestador)
    email = _generar_email(username, prestador.email)
    
    usuario = Usuario(
        username=username.lower(),
        email=email,
        nombre_completo=prestador.nombre_completo,
        telefono=prestador.telefono,
        rol_id=rol_prestador.rol_id,
        matricula_tipo=prestador.tipo_matricula,
        matricula_numero=prestador.numero_matricula,
        especialidad=prestador.nombre_especialidad,
        prestador_id=prestador.prestador_id,
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
        descripcion=f'Creado usuario prestador desde gestor: {usuario.username}',
        ip_address=request.remote_addr
    )
    
    return jsonify({
        'success': True,
        'username': usuario.username,
        'password': password,
        'email': usuario.email
    })

