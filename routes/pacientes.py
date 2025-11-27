"""
Rutas de gestión de pacientes (afiliados)
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from extensions import db
from models.paciente import Afiliado
from models.obra_social import ObraSocial
from models.auditoria import Auditoria
from datetime import datetime

bp = Blueprint('pacientes', __name__, url_prefix='/pacientes')


@bp.route('/')
@login_required
def index():
    """Listado de pacientes"""
    page = request.args.get('page', 1, type=int)
    buscar = request.args.get('buscar', '')
    
    # Excluir paciente de prueba "000 PRUEBA" de los listados
    # Excluir si tiene "000" en apellido Y "PRUEBA" en nombre, o viceversa
    query = Afiliado.query.filter(
        ~db.or_(
            db.and_(Afiliado.apellido.ilike('%000%'), Afiliado.nombre.ilike('%PRUEBA%')),
            db.and_(Afiliado.apellido.ilike('%PRUEBA%'), Afiliado.nombre.ilike('%000%'))
        )
    )
    
    if buscar:
        query = query.filter(
            db.or_(
                Afiliado.apellido.ilike(f'%{buscar}%'),
                Afiliado.nombre.ilike(f'%{buscar}%'),
                Afiliado.numero_documento.ilike(f'%{buscar}%')
            )
        )
    
    pacientes = query.order_by(Afiliado.apellido, Afiliado.nombre).paginate(
        page=page, per_page=50, error_out=False
    )
    
    return render_template('pacientes/index.html', pacientes=pacientes, buscar=buscar)


@bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo():
    """Crear nuevo paciente"""
    if request.method == 'POST':
        # Obtener datos del formulario
        apellido = request.form.get('apellido')
        nombre = request.form.get('nombre')
        obra_social_id = request.form.get('obra_social_id')
        numero_afiliado = request.form.get('numero_afiliado')
        tipo_documento = request.form.get('tipo_documento')
        numero_documento = request.form.get('numero_documento')
        fecha_nacimiento = request.form.get('fecha_nacimiento')
        localidad = request.form.get('localidad')
        telefono = request.form.get('telefono')
        email = request.form.get('email')
        observaciones = request.form.get('observaciones')
        
        # Validaciones básicas
        if not apellido or not nombre:
            flash('El apellido y nombre son obligatorios.', 'danger')
            obras_sociales = ObraSocial.query.order_by(ObraSocial.nombre).all()
            return render_template('pacientes/form.html', obras_sociales=obras_sociales)
        
        # Validar y convertir fecha de nacimiento
        fecha_nac_obj = None
        if fecha_nacimiento:
            try:
                fecha_nac_obj = datetime.strptime(fecha_nacimiento, '%Y-%m-%d').date()
                # Validar que la fecha sea razonable
                if fecha_nac_obj.year < 1900 or fecha_nac_obj > datetime.now().date():
                    flash('La fecha de nacimiento no es válida.', 'danger')
                    obras_sociales = ObraSocial.query.order_by(ObraSocial.nombre).all()
                    return render_template('pacientes/form.html', obras_sociales=obras_sociales)
            except ValueError:
                flash('Formato de fecha de nacimiento inválido.', 'danger')
                obras_sociales = ObraSocial.query.order_by(ObraSocial.nombre).all()
                return render_template('pacientes/form.html', obras_sociales=obras_sociales)
        
        # Crear paciente
        try:
            paciente = Afiliado(
                apellido=apellido,
                nombre=nombre,
                obra_social_id=int(obra_social_id) if obra_social_id and obra_social_id != '' else None,
                numero_afiliado=numero_afiliado,
                tipo_documento=tipo_documento,
                numero_documento=numero_documento,
                fecha_nacimiento=fecha_nac_obj,
                localidad=localidad,
                telefono=telefono,
                email=email,
                observaciones=observaciones
            )
        except Exception as e:
            flash(f'Error al crear paciente: {str(e)}', 'danger')
            obras_sociales = ObraSocial.query.order_by(ObraSocial.nombre).all()
            return render_template('pacientes/form.html', obras_sociales=obras_sociales)
        
        db.session.add(paciente)
        db.session.commit()
        
        # Registrar en auditoría
        Auditoria.registrar(
            usuario_id=current_user.usuario_id,
            accion='CREAR',
            tabla='afiliados',
            registro_id=paciente.afiliado_id,
            descripcion=f'Creado paciente: {paciente.nombre_completo}',
            ip_address=request.remote_addr
        )
        
        flash(f'Paciente {paciente.nombre_completo} creado correctamente.', 'success')
        return redirect(url_for('pacientes.index'))
    
    obras_sociales = ObraSocial.query.order_by(ObraSocial.nombre).all()
    return render_template('pacientes/form.html', obras_sociales=obras_sociales)


@bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar(id):
    """Editar paciente existente"""
    paciente = Afiliado.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            paciente.apellido = request.form.get('apellido')
            paciente.nombre = request.form.get('nombre')
            os_id = request.form.get('obra_social_id')
            paciente.obra_social_id = int(os_id) if os_id and os_id != '' else None
            paciente.numero_afiliado = request.form.get('numero_afiliado')
            paciente.tipo_documento = request.form.get('tipo_documento')
            paciente.numero_documento = request.form.get('numero_documento')
            
            # Validar fecha
            fecha_nac = request.form.get('fecha_nacimiento')
            if fecha_nac:
                try:
                    fecha_nac_obj = datetime.strptime(fecha_nac, '%Y-%m-%d').date()
                    if fecha_nac_obj.year < 1900 or fecha_nac_obj > datetime.now().date():
                        raise ValueError("Fecha fuera de rango válido")
                    paciente.fecha_nacimiento = fecha_nac_obj
                except ValueError as e:
                    flash(f'Fecha de nacimiento inválida: {str(e)}', 'danger')
                    obras_sociales = ObraSocial.query.order_by(ObraSocial.nombre).all()
                    return render_template('pacientes/form.html', paciente=paciente, obras_sociales=obras_sociales)
            else:
                paciente.fecha_nacimiento = None
            
            paciente.localidad = request.form.get('localidad')
            paciente.telefono = request.form.get('telefono')
            paciente.email = request.form.get('email')
            paciente.observaciones = request.form.get('observaciones')
            
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f'Error al guardar: {str(e)}', 'danger')
            obras_sociales = ObraSocial.query.order_by(ObraSocial.nombre).all()
            return render_template('pacientes/form.html', paciente=paciente, obras_sociales=obras_sociales)
        
        # Registrar en auditoría
        Auditoria.registrar(
            usuario_id=current_user.usuario_id,
            accion='MODIFICAR',
            tabla='afiliados',
            registro_id=paciente.afiliado_id,
            descripcion=f'Modificado paciente: {paciente.nombre_completo}',
            ip_address=request.remote_addr
        )
        
        flash(f'Paciente {paciente.nombre_completo} actualizado correctamente.', 'success')
        return redirect(url_for('pacientes.index'))
    
    obras_sociales = ObraSocial.query.order_by(ObraSocial.nombre).all()
    return render_template('pacientes/form.html', paciente=paciente, obras_sociales=obras_sociales)


@bp.route('/<int:id>/ver')
@login_required
def ver(id):
    """Ver detalle de paciente"""
    paciente = Afiliado.query.get_or_404(id)
    return render_template('pacientes/ver.html', paciente=paciente)


@bp.route('/<int:id>/toggle')
@login_required
def toggle_activo(id):
    """Activar/desactivar paciente"""
    paciente = Afiliado.query.get_or_404(id)
    paciente.activo = not paciente.activo
    db.session.commit()
    
    accion = 'activado' if paciente.activo else 'desactivado'
    flash(f'Paciente {paciente.nombre_completo} {accion} correctamente.', 'success')
    return redirect(url_for('pacientes.index'))


@bp.route('/buscar-json')
@login_required
def buscar_json():
    """Buscar pacientes para autocomplete (AJAX)"""
    termino = request.args.get('q', '')
    
    if len(termino) < 2:
        return jsonify([])
    
    # Excluir paciente de prueba del autocomplete
    pacientes = Afiliado.query.filter(
        db.or_(
            Afiliado.apellido.ilike(f'%{termino}%'),
            Afiliado.nombre.ilike(f'%{termino}%'),
            Afiliado.numero_documento.ilike(f'%{termino}%'),
            Afiliado.numero_afiliado.ilike(f'%{termino}%')
        ),
        Afiliado.activo == True
    ).filter(
        ~db.or_(
            db.and_(Afiliado.apellido.ilike('%000%'), Afiliado.nombre.ilike('%PRUEBA%')),
            db.and_(Afiliado.apellido.ilike('%PRUEBA%'), Afiliado.nombre.ilike('%000%'))
        )
    ).limit(20).all()
    
    resultados = [{
        'afiliado_id': p.afiliado_id,
        'id': p.afiliado_id,  # Compatibilidad
        'text': p.nombre_completo_con_documento,
        'nombre_completo': p.nombre_completo,
        'apellido': p.apellido,
        'nombre': p.nombre,
        'documento': p.numero_documento,
        'numero_afiliado': p.numero_afiliado,
        'edad': p.edad,
        'obra_social_id': p.obra_social_id,
        'obra_social': p.obra_social.nombre if p.obra_social else None
    } for p in pacientes]
    
    return jsonify(resultados)

