"""
Rutas para módulo de Reportes y Búsquedas
"""
from flask import Blueprint, render_template, request
from flask_login import login_required
from extensions import db
from models.protocolo import Protocolo
from models.paciente import Afiliado
from models.prestador import Prestador
from models.obra_social import ObraSocial
from sqlalchemy import func, desc
from datetime import datetime, timedelta, date
from utils.decorators import permission_required

bp = Blueprint('reportes', __name__, url_prefix='/reportes')


@bp.route('/')
@login_required
@permission_required('reportes_ver')
def index():
    """Página principal de reportes"""
    return render_template('reportes/index.html')


@bp.route('/pacientes')
@login_required
@permission_required('reportes_ver')
def pacientes():
    """Reporte de pacientes con cantidad de protocolos"""
    page = request.args.get('page', 1, type=int)
    buscar = request.args.get('buscar', '').strip()
    
    # Query con conteo de protocolos por paciente (excluir protocolos de prueba)
    query = db.session.query(
        Afiliado,
        func.count(Protocolo.protocolo_id).label('cantidad_protocolos')
    ).outerjoin(
        Protocolo, 
        db.and_(
            Afiliado.afiliado_id == Protocolo.afiliado_id,
            Protocolo.es_prueba == False
        )
    ).group_by(Afiliado.afiliado_id)
    
    if buscar:
        query = query.filter(
            db.or_(
                Afiliado.apellido.ilike(f'%{buscar}%'),
                Afiliado.nombre.ilike(f'%{buscar}%'),
                Afiliado.numero_documento.ilike(f'%{buscar}%')
            )
        )
    
    resultados = query.order_by(desc(func.count(Protocolo.protocolo_id)), Afiliado.apellido).paginate(
        page=page, per_page=50, error_out=False
    )
    
    return render_template('reportes/pacientes.html', resultados=resultados, buscar=buscar)


@bp.route('/prestadores')
@login_required
@permission_required('reportes_ver')
def prestadores():
    """Reporte de prestadores con cantidad de protocolos"""
    page = request.args.get('page', 1, type=int)
    buscar = request.args.get('buscar', '').strip()
    
    # Query con conteo de protocolos por prestador (excluir protocolos de prueba)
    query = db.session.query(
        Prestador,
        func.count(Protocolo.protocolo_id).label('cantidad_protocolos')
    ).outerjoin(
        Protocolo, 
        db.and_(
            Prestador.prestador_id == Protocolo.prestador_id,
            Protocolo.es_prueba == False
        )
    ).filter(
        Prestador.activo == True
    ).group_by(Prestador.prestador_id)
    
    if buscar:
        query = query.filter(
            db.or_(
                Prestador.apellido.ilike(f'%{buscar}%'),
                Prestador.nombre.ilike(f'%{buscar}%'),
                Prestador.numero_matricula.ilike(f'%{buscar}%')
            )
        )
    
    resultados = query.order_by(desc(func.count(Protocolo.protocolo_id)), Prestador.apellido).paginate(
        page=page, per_page=50, error_out=False
    )
    
    return render_template('reportes/prestadores.html', resultados=resultados, buscar=buscar)


@bp.route('/obras_sociales')
@login_required
@permission_required('reportes_ver')
def obras_sociales():
    """Reporte de obras sociales con cantidad de protocolos"""
    page = request.args.get('page', 1, type=int)
    buscar = request.args.get('buscar', '').strip()
    
    # Query con conteo de protocolos por obra social (excluir protocolos de prueba)
    query = db.session.query(
        ObraSocial,
        func.count(Protocolo.protocolo_id).label('cantidad_protocolos')
    ).outerjoin(
        Protocolo,
        db.and_(
            ObraSocial.obra_social_id == Protocolo.obra_social_id,
            Protocolo.es_prueba == False
        )
    ).group_by(ObraSocial.obra_social_id)
    
    if buscar:
        query = query.filter(
            ObraSocial.nombre.ilike(f'%{buscar}%')
        )
    
    resultados = query.order_by(desc(func.count(Protocolo.protocolo_id)), ObraSocial.nombre).paginate(
        page=page, per_page=50, error_out=False
    )
    
    return render_template('reportes/obras_sociales.html', resultados=resultados, buscar=buscar)


@bp.route('/protocolos_por_tipo')
@login_required
@permission_required('reportes_ver')
def protocolos_por_tipo():
    """Reporte de protocolos agrupados por tipo de estudio"""
    resultados = db.session.query(
        Protocolo.tipo_estudio,
        func.count(Protocolo.protocolo_id).label('cantidad')
    ).filter(
        Protocolo.es_prueba == False
    ).group_by(Protocolo.tipo_estudio).all()
    
    return render_template('reportes/protocolos_por_tipo.html', resultados=resultados)


@bp.route('/protocolos_por_estado')
@login_required
@permission_required('reportes_ver')
def protocolos_por_estado():
    """Reporte de protocolos agrupados por estado"""
    resultados = db.session.query(
        Protocolo.estado,
        func.count(Protocolo.protocolo_id).label('cantidad')
    ).filter(
        Protocolo.es_prueba == False
    ).group_by(Protocolo.estado).all()
    
    return render_template('reportes/protocolos_por_estado.html', resultados=resultados)


@bp.route('/protocolos_por_periodo')
@login_required
@permission_required('reportes_ver')
def protocolos_por_periodo():
    """Reporte de protocolos agrupados por período"""
    fecha_desde = request.args.get('fecha_desde', '')
    fecha_hasta = request.args.get('fecha_hasta', '')
    
    query = db.session.query(
        func.date(Protocolo.fecha_ingreso).label('fecha'),
        func.count(Protocolo.protocolo_id).label('cantidad')
    ).filter(
        Protocolo.es_prueba == False
    ).group_by(func.date(Protocolo.fecha_ingreso))
    
    if fecha_desde:
        try:
            fecha_desde_obj = datetime.strptime(fecha_desde, '%Y-%m-%d').date()
            query = query.filter(Protocolo.fecha_ingreso >= fecha_desde_obj)
        except ValueError:
            pass
    
    if fecha_hasta:
        try:
            fecha_hasta_obj = datetime.strptime(fecha_hasta, '%Y-%m-%d').date()
            query = query.filter(Protocolo.fecha_ingreso <= fecha_hasta_obj)
        except ValueError:
            pass
    
    resultados_raw = query.order_by(desc('fecha')).limit(90).all()  # Últimos 90 días
    
    # Convertir fechas string a objetos date
    resultados = []
    total = 0
    for fecha_str, cantidad in resultados_raw:
        fecha_obj = None
        if fecha_str:
            if isinstance(fecha_str, str):
                try:
                    fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                except (ValueError, TypeError):
                    try:
                        fecha_obj = datetime.strptime(fecha_str[:10], '%Y-%m-%d').date()
                    except (ValueError, TypeError):
                        fecha_obj = None
            elif hasattr(fecha_str, 'date'):  # Si es datetime
                fecha_obj = fecha_str.date() if isinstance(fecha_str, datetime) else fecha_str
            elif isinstance(fecha_str, date):
                fecha_obj = fecha_str
        resultados.append((fecha_obj, cantidad))
        total += cantidad
    
    return render_template('reportes/protocolos_por_periodo.html', 
                         resultados=resultados,
                         total=total,
                         fecha_desde=fecha_desde,
                         fecha_hasta=fecha_hasta)


@bp.route('/protocolos_por_prestador')
@login_required
@permission_required('reportes_ver')
def protocolos_por_prestador():
    """Reporte de protocolos agrupados por prestador"""
    page = request.args.get('page', 1, type=int)
    
    # Top 50 prestadores con más protocolos (excluir protocolos de prueba)
    resultados = db.session.query(
        Prestador,
        func.count(Protocolo.protocolo_id).label('cantidad_protocolos')
    ).join(
        Protocolo, Prestador.prestador_id == Protocolo.prestador_id
    ).filter(
        Prestador.activo == True,
        Protocolo.es_prueba == False
    ).group_by(Prestador.prestador_id).order_by(
        desc(func.count(Protocolo.protocolo_id))
    ).paginate(
        page=page, per_page=50, error_out=False
    )
    
    return render_template('reportes/protocolos_por_prestador.html', resultados=resultados)


@bp.route('/facturacion_obra_social')
@login_required
@permission_required('reportes_avanzados')
def facturacion_obra_social():
    """Reporte de facturación por obra social"""
    # Por ahora, solo muestra un placeholder
    # TODO: Implementar lógica de facturación cuando esté disponible
    return render_template('reportes/facturacion_obra_social.html')


@bp.route('/facturacion_periodo')
@login_required
@permission_required('reportes_avanzados')
def facturacion_periodo():
    """Reporte de facturación por período"""
    # Por ahora, solo muestra un placeholder
    # TODO: Implementar lógica de facturación cuando esté disponible
    return render_template('reportes/facturacion_periodo.html')


@bp.route('/estadisticas_contables')
@login_required
@permission_required('reportes_avanzados')
def estadisticas_contables():
    """Reporte de estadísticas contables"""
    # Por ahora, solo muestra un placeholder
    # TODO: Implementar lógica contable cuando esté disponible
    return render_template('reportes/estadisticas_contables.html')
