"""
Rutas del Dashboard principal
"""
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from extensions import db
from models.protocolo import Protocolo
from models.paciente import Afiliado
from models.prestador import Prestador
from models.obra_social import ObraSocial
from sqlalchemy import func, case
from datetime import datetime, timedelta
import unicodedata

bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')


def _rol_es_prestador(nombre_rol: str) -> bool:
    if not nombre_rol:
        return False
    texto = unicodedata.normalize('NFD', nombre_rol.strip().lower())
    texto = ''.join(ch for ch in texto if unicodedata.category(ch) != 'Mn')
    return 'prestador' in texto


@bp.route('/')
@login_required
def index():
    """Dashboard principal"""

    if _rol_es_prestador(getattr(current_user.rol, 'nombre', '')):
        return redirect(url_for('portal_prestador.dashboard'))
    
    # Estadísticas generales (excluir protocolos de prueba)
    total_protocolos = Protocolo.query.filter_by(es_prueba=False).count()
    total_pacientes = Afiliado.query.filter_by(activo=True).count()
    total_prestadores = Prestador.query.filter_by(activo=True).count()
    total_obras_sociales = ObraSocial.query.count()
    
    # Protocolos pendientes (incluye URGENTE, PENDIENTE, EN_PROCESO)
    protocolos_urgentes = Protocolo.query.filter_by(estado='URGENTE', es_prueba=False).count()
    protocolos_pendientes = Protocolo.query.filter_by(estado='PENDIENTE', es_prueba=False).count()
    protocolos_en_proceso = Protocolo.query.filter_by(estado='EN_PROCESO', es_prueba=False).count()
    
    # Protocolos por tipo
    protocolos_biopsias = Protocolo.query.filter_by(tipo_estudio='BIOPSIA', es_prueba=False).count()
    protocolos_citologia = Protocolo.query.filter_by(tipo_estudio='CITOLOGÍA', es_prueba=False).count()
    protocolos_pap = Protocolo.query.filter_by(tipo_estudio='PAP', es_prueba=False).count()
    
    # Protocolos del mes actual
    hoy = datetime.now().date()
    primer_dia_mes = hoy.replace(day=1)
    protocolos_mes = Protocolo.query.filter(
        Protocolo.fecha_ingreso >= primer_dia_mes,
        Protocolo.es_prueba == False
    ).count()
    
    # Últimos 10 protocolos ingresados (ordenados por fecha de ingreso, excluir prueba)
    ultimos_protocolos = Protocolo.query.filter_by(es_prueba=False).order_by(
        Protocolo.fecha_ingreso.desc()
    ).limit(10).all()
    for protocolo in ultimos_protocolos:
        if protocolo.usuario_informe:
            _ = protocolo.usuario_informe.nombre_completo  # acceder para cargar lazy
    
    # Protocolos Pendientes (incluye URGENTE, EN_PROCESO, PENDIENTE)
    # Configuración de umbrales
    UMBRAL_AMARILLO = 3  # días para alerta amarilla
    UMBRAL_NARANJA = 7   # días para alerta naranja  
    UMBRAL_ROJO = 14     # días para alerta roja
    
    # Obtener todos los protocolos pendientes (sin completar)
    # Primero los URGENTES, luego por antigüedad
    protocolos_pendientes_query = Protocolo.query.filter(
        Protocolo.estado.in_(['URGENTE', 'EN_PROCESO', 'PENDIENTE']),
        Protocolo.es_prueba == False
    )
    
    # Ordenar: primero URGENTE, luego por fecha de ingreso (más antiguos primero)
    protocolos_pendientes_list = protocolos_pendientes_query.order_by(
        case((Protocolo.estado == 'URGENTE', 1), else_=2),  # URGENTE primero
        Protocolo.fecha_ingreso.asc()  # Luego por antigüedad
    ).limit(10).all()
    
    # Calcular días pendientes y clasificar por color
    protocolos_clasificados = []
    for protocolo in protocolos_pendientes_list:
        dias_pendiente = (hoy - protocolo.fecha_ingreso).days
        
        # Si el protocolo está marcado como URGENTE, siempre mostrar como urgente
        if protocolo.estado == 'URGENTE':
            color = 'danger'  # Rojo
            icono = 'bi-exclamation-triangle-fill'
            es_urgente = True
        elif dias_pendiente >= UMBRAL_ROJO:
            color = 'danger'  # Rojo
            icono = 'bi-exclamation-triangle-fill'
            es_urgente = False
        elif dias_pendiente >= UMBRAL_NARANJA:
            color = 'warning'  # Naranja
            icono = 'bi-exclamation-triangle'
            es_urgente = False
        elif dias_pendiente >= UMBRAL_AMARILLO:
            color = 'info'  # Azul
            icono = 'bi-info-circle'
            es_urgente = False
        else:
            color = 'secondary'  # Gris
            icono = 'bi-clock'
            es_urgente = False
            
        protocolos_clasificados.append({
            'protocolo': protocolo,
            'dias_pendiente': dias_pendiente,
            'color': color,
            'icono': icono,
            'es_urgente': es_urgente
        })
    
    # Guardar también la lista original para compatibilidad
    protocolos_antiguos = protocolos_pendientes_list
    
    # Gráfico: Protocolos por estado (últimos 30 días)
    hace_30_dias = hoy - timedelta(days=30)
    protocolos_30_dias = db.session.query(
        Protocolo.estado,
        func.count(Protocolo.protocolo_id).label('count')
    ).filter(
        Protocolo.fecha_ingreso >= hace_30_dias,
        Protocolo.es_prueba == False
    ).group_by(Protocolo.estado).all()
    
    # Gráfico: Protocolos por tipo (últimos 30 días)
    protocolos_tipo_30_dias = db.session.query(
        Protocolo.tipo_estudio,
        func.count(Protocolo.protocolo_id).label('count')
    ).filter(
        Protocolo.fecha_ingreso >= hace_30_dias,
        Protocolo.es_prueba == False
    ).group_by(Protocolo.tipo_estudio).all()
    
    return render_template('dashboard/index.html',
                         total_protocolos=total_protocolos,
                         total_pacientes=total_pacientes,
                         total_prestadores=total_prestadores,
                         total_obras_sociales=total_obras_sociales,
                         protocolos_urgentes=protocolos_urgentes,
                         protocolos_pendientes=protocolos_pendientes,
                         protocolos_en_proceso=protocolos_en_proceso,
                         protocolos_biopsias=protocolos_biopsias,
                         protocolos_citologia=protocolos_citologia,
                         protocolos_pap=protocolos_pap,
                         protocolos_mes=protocolos_mes,
                         ultimos_protocolos=ultimos_protocolos,
                         protocolos_antiguos=protocolos_antiguos,
                         protocolos_clasificados=protocolos_clasificados,
                         protocolos_30_dias=protocolos_30_dias,
                         protocolos_tipo_30_dias=protocolos_tipo_30_dias)


