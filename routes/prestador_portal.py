"""
Portal y funcionalidades específicas para usuarios con rol Prestador.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, current_app, jsonify
from flask_login import login_required, current_user
from models.protocolo import Protocolo
from models.paciente import Afiliado
from models.auditoria import Auditoria
from routes.plantillas_dinamicas import construir_contexto_reporte
from sqlalchemy import or_, func
from datetime import datetime
import unicodedata
import io
import zipfile

bp = Blueprint('portal_prestador', __name__, url_prefix='/prestador')


def _rol_es_prestador(nombre_rol: str) -> bool:
    if not nombre_rol:
        return False
    texto = unicodedata.normalize('NFD', nombre_rol.strip().lower())
    texto = ''.join(ch for ch in texto if unicodedata.category(ch) != 'Mn')
    return 'prestador' in texto


def _usuario_es_prestador() -> bool:
    return _rol_es_prestador(getattr(getattr(current_user, 'rol', None), 'nombre', ''))


@bp.route('/', methods=['GET', 'POST'])
@login_required
def dashboard():
    """Listado de protocolos y área de contacto para prestadores."""
    if not _usuario_es_prestador():
        flash('No tiene permisos para acceder al portal de prestadores.', 'danger')
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        mensaje = (request.form.get('mensaje') or '').strip()
        if mensaje:
            Auditoria.registrar(
                usuario_id=current_user.usuario_id,
                accion='CONTACTO_PRESTADOR',
                descripcion=f'Mensaje desde portal prestador: {mensaje}',
                ip_address=request.remote_addr
            )
            flash('Mensaje enviado. Nos contactaremos a la brevedad.', 'success')
        else:
            flash('Ingrese un mensaje antes de enviar.', 'warning')
        return redirect(url_for('portal_prestador.dashboard'))

    if not current_user.prestador_id:
        flash('Su usuario no está asociado a un prestador. Contacte al laboratorio para regularizar la situación.', 'warning')
        return render_template('prestador/dashboard.html', protocolos=[], total=0, sin_prestador=True, body_class='body-prestador-background', asistente_context='prestador')

    buscar = (request.args.get('buscar') or '').strip()
    fecha_desde = request.args.get('fecha_desde') or ''
    fecha_hasta = request.args.get('fecha_hasta') or ''
    orden = request.args.get('orden') or 'fecha_desc'

    query = Protocolo.query.join(Afiliado).filter(
        Protocolo.prestador_id == current_user.prestador_id,
        Protocolo.estado == 'COMPLETADO'
    )

    if buscar:
        like = f"%{buscar.lower()}%"
        query = query.filter(
            or_(
                func.lower(Afiliado.nombre).like(like),
                func.lower(Afiliado.apellido).like(like),
                Afiliado.numero_documento.ilike(f'%{buscar}%'),
                Protocolo.numero_protocolo.ilike(f'%{buscar}%')
            )
        )

    formato_fecha = '%Y-%m-%d'
    if fecha_desde:
        try:
            fecha_inicio = datetime.strptime(fecha_desde, formato_fecha).date()
            query = query.filter(Protocolo.fecha_informe >= fecha_inicio)
        except ValueError:
            flash('La fecha "desde" es inválida. Use el formato YYYY-MM-DD.', 'warning')
    if fecha_hasta:
        try:
            fecha_fin = datetime.strptime(fecha_hasta, formato_fecha).date()
            query = query.filter(Protocolo.fecha_informe <= fecha_fin)
        except ValueError:
            flash('La fecha "hasta" es inválida. Use el formato YYYY-MM-DD.', 'warning')

    orden_map = {
        'fecha_desc': [Protocolo.fecha_informe.desc()],
        'fecha_asc': [Protocolo.fecha_informe.asc()],
        'paciente_asc': [Afiliado.apellido.asc(), Afiliado.nombre.asc()],
        'paciente_desc': [Afiliado.apellido.desc(), Afiliado.nombre.desc()],
        'protocolo_asc': [Protocolo.numero_protocolo.asc()],
        'protocolo_desc': [Protocolo.numero_protocolo.desc()]
    }
    for criterio in orden_map.get(orden, orden_map['fecha_desc']):
        query = query.order_by(criterio)

    protocolos_encontrados = query.all()
    protocolos = []
    for protocolo in protocolos_encontrados:
        afiliado = protocolo.afiliado
        fecha_ref = protocolo.fecha_informe or protocolo.fecha_ingreso
        protocolos.append({
            'id': protocolo.protocolo_id,
            'numero': protocolo.numero_protocolo,
            'paciente': afiliado.nombre_completo if afiliado else 'Sin paciente',
            'dni': afiliado.numero_documento if afiliado else '',
            'fecha': fecha_ref,
            'tipo': protocolo.tipo_estudio
        })

    return render_template(
        'prestador/dashboard.html',
        protocolos=protocolos,
        total=len(protocolos),
        buscar=buscar,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        orden=orden,
        prestador=current_user.prestador,
        sin_prestador=False,
        body_class='body-prestador-background',
        asistente_context='prestador'
    )


@bp.route('/descargar-multiples', methods=['POST'])
@login_required
def descargar_multiples():
    if not _usuario_es_prestador():
        return jsonify({'success': False, 'error': 'No autorizado'}), 403

    data = request.get_json(silent=True) or {}
    ids = data.get('protocolos') or []
    if not isinstance(ids, list) or not ids:
        return jsonify({'success': False, 'error': 'No se recibieron protocolos para descargar'}), 400

    ids_limpios = [int(pid) for pid in ids if str(pid).isdigit()]
    if not ids_limpios:
        return jsonify({'success': False, 'error': 'Listado de protocolos inválido'}), 400

    protocolos = Protocolo.query.filter(
        Protocolo.protocolo_id.in_(ids_limpios),
        Protocolo.prestador_id == current_user.prestador_id,
        Protocolo.estado == 'COMPLETADO'
    ).order_by(Protocolo.fecha_informe.desc()).all()

    if not protocolos:
        return jsonify({'success': False, 'error': 'No se encontraron protocolos válidos para descargar'}), 404

    try:
        from weasyprint import HTML  # Importar aquí para evitar fallos en el arranque
    except Exception as exc:
        return jsonify({
            'success': False,
            'error': 'WeasyPrint no está disponible en el servidor. Instale las dependencias (cairo, pango, gobject) y la librería weasyprint para habilitar la exportación a PDF.',
            'detalle': str(exc)
        }), 500

    try:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for protocolo in protocolos:
                contexto = construir_contexto_reporte(protocolo.protocolo_id)
                html = render_template('plantillas_dinamicas/reporte_unificado.html', **contexto)
                try:
                    pdf_bytes = HTML(string=html, base_url=request.url_root).write_pdf()
                except Exception as pdf_error:
                    return jsonify({
                        'success': False,
                        'error': f'No se pudo generar el PDF del protocolo {protocolo.numero_protocolo}.',
                        'detalle': str(pdf_error)
                    }), 500
                nombre_pdf = f"{protocolo.numero_protocolo}.pdf"
                zip_file.writestr(nombre_pdf, pdf_bytes)
        zip_buffer.seek(0)
    except Exception as general_error:
        return jsonify({
            'success': False,
            'error': 'No fue posible preparar la descarga.',
            'detalle': str(general_error)
        }), 500

    Auditoria.registrar(
        usuario_id=current_user.usuario_id,
        accion='DESCARGA_PROTOCOLOS_ZIP',
        descripcion=f'Descarga múltiple de protocolos: {len(protocolos)} items',
        ip_address=request.remote_addr
    )

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    nombre_zip = f"protocolos_{timestamp}.zip"
    return send_file(zip_buffer, mimetype='application/zip', as_attachment=True, download_name=nombre_zip)

