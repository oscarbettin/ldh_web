"""
Rutas de gestión de obras sociales
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from extensions import db
from models.obra_social import ObraSocial, PlanFacturacion
from models.auditoria import Auditoria
from datetime import datetime

bp = Blueprint('obras_sociales', __name__, url_prefix='/obras-sociales')


@bp.route('/')
@login_required
def index():
    """Listado de obras sociales"""
    page = request.args.get('page', 1, type=int)
    buscar = request.args.get('buscar', '')
    
    query = ObraSocial.query
    
    if buscar:
        query = query.filter(
            db.or_(
                ObraSocial.nombre.ilike(f'%{buscar}%'),
                ObraSocial.codigo.ilike(f'%{buscar}%')
            )
        )
    
    obras_sociales = query.order_by(ObraSocial.nombre).paginate(
        page=page, per_page=50, error_out=False
    )
    
    return render_template('obras_sociales/index.html', obras_sociales=obras_sociales, buscar=buscar)


@bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo():
    """Crear nueva obra social"""
    if request.method == 'POST':
        codigo = request.form.get('codigo')
        nombre = request.form.get('nombre')
        direccion = request.form.get('direccion')
        localidad = request.form.get('localidad')
        codigo_postal = request.form.get('codigo_postal')
        telefono = request.form.get('telefono')
        codigo_inos = request.form.get('codigo_inos')
        plan_id = request.form.get('plan_id')
        observaciones = request.form.get('observaciones')
        
        if not codigo or not nombre:
            flash('El código y nombre son obligatorios.', 'danger')
            planes = PlanFacturacion.query.filter_by(activo=True).order_by(PlanFacturacion.nombre).all()
            return render_template('obras_sociales/form.html', planes=planes)
        
        try:
            obra_social = ObraSocial(
                codigo=codigo,
                nombre=nombre,
                direccion=direccion,
                localidad=localidad,
                codigo_postal=codigo_postal,
                telefono=telefono,
                codigo_inos=codigo_inos,
                plan_id=int(plan_id) if plan_id and plan_id != '' else None,
                observaciones=observaciones
            )
            
            db.session.add(obra_social)
            db.session.commit()
            
            Auditoria.registrar(
                usuario_id=current_user.usuario_id,
                accion='CREAR',
                tabla='obras_sociales',
                registro_id=obra_social.obra_social_id,
                descripcion=f'Creada obra social: {obra_social.nombre}',
                ip_address=request.remote_addr
            )
            
            flash(f'Obra Social {obra_social.nombre} creada correctamente.', 'success')
            return redirect(url_for('obras_sociales.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear: {str(e)}', 'danger')
            planes = PlanFacturacion.query.filter_by(activo=True).order_by(PlanFacturacion.nombre).all()
            return render_template('obras_sociales/form.html', planes=planes)
    
    planes = PlanFacturacion.query.filter_by(activo=True).order_by(PlanFacturacion.nombre).all()
    return render_template('obras_sociales/form.html', planes=planes)


@bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar(id):
    """Editar obra social existente"""
    obra_social = ObraSocial.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            obra_social.codigo = request.form.get('codigo')
            obra_social.nombre = request.form.get('nombre')
            obra_social.direccion = request.form.get('direccion')
            obra_social.localidad = request.form.get('localidad')
            obra_social.codigo_postal = request.form.get('codigo_postal')
            obra_social.telefono = request.form.get('telefono')
            obra_social.codigo_inos = request.form.get('codigo_inos')
            plan_id = request.form.get('plan_id')
            obra_social.plan_id = int(plan_id) if plan_id and plan_id != '' else None
            obra_social.observaciones = request.form.get('observaciones')
            
            db.session.commit()
            
            Auditoria.registrar(
                usuario_id=current_user.usuario_id,
                accion='MODIFICAR',
                tabla='obras_sociales',
                registro_id=obra_social.obra_social_id,
                descripcion=f'Modificada obra social: {obra_social.nombre}',
                ip_address=request.remote_addr
            )
            
            flash(f'Obra Social {obra_social.nombre} actualizada correctamente.', 'success')
            return redirect(url_for('obras_sociales.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al guardar: {str(e)}', 'danger')
            planes = PlanFacturacion.query.filter_by(activo=True).order_by(PlanFacturacion.nombre).all()
            return render_template('obras_sociales/form.html', obra_social=obra_social, planes=planes)
    
    planes = PlanFacturacion.query.filter_by(activo=True).order_by(PlanFacturacion.nombre).all()
    return render_template('obras_sociales/form.html', obra_social=obra_social, planes=planes)


@bp.route('/<int:id>/ver')
@login_required
def ver(id):
    """Ver detalle de obra social"""
    obra_social = ObraSocial.query.get_or_404(id)
    return render_template('obras_sociales/ver.html', obra_social=obra_social)


@bp.route('/<int:id>/toggle')
@login_required
def toggle_activo(id):
    """Activar/desactivar obra social"""
    obra_social = ObraSocial.query.get_or_404(id)
    obra_social.activo = not obra_social.activo
    db.session.commit()
    
    accion = 'activada' if obra_social.activo else 'desactivada'
    flash(f'Obra Social {obra_social.nombre} {accion} correctamente.', 'success')
    return redirect(url_for('obras_sociales.index'))

