"""
Rutas relacionadas con la gestión del perfil del usuario (firmas, preferencias personales).
"""
from datetime import datetime
import os
import unicodedata

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from extensions import db
from models.usuario import UsuarioFirma

bp = Blueprint('usuarios', __name__, url_prefix='/mi-perfil')


def _normalizar_texto(texto: str) -> str:
    if not texto:
        return ''
    texto = unicodedata.normalize('NFD', texto.strip().lower())
    return ''.join(ch for ch in texto if unicodedata.category(ch) != 'Mn')


def _rol_es_medico(rol_nombre: str) -> bool:
    normalizado = _normalizar_texto(rol_nombre)
    return 'medico' in normalizado if normalizado else False


def _es_medico():
    return _rol_es_medico(getattr(current_user.rol, 'nombre', ''))


def _resolver_ruta_absoluta(rel_path: str) -> str:
    if not rel_path:
        return ''
    if rel_path.startswith('firmas/'):
        return os.path.join(current_app.static_folder, rel_path)
    return os.path.join(current_app.static_folder, rel_path)


@bp.route('/firma', methods=['GET', 'POST'])
@login_required
def firma():
    """
    Permite a los usuarios con rol 'medico' cargar o actualizar su firma digital.
    """
    if not _es_medico():
        flash('Solo los usuarios con rol médico pueden gestionar firmas.', 'warning')
        return redirect(url_for('dashboard.index'))

    firma_actual = current_user.firma

    if request.method == 'POST':
        archivo = request.files.get('firma')
        if not archivo or archivo.filename.strip() == '':
            flash('Seleccione un archivo de imagen para la firma.', 'warning')
            return redirect(url_for('usuarios.firma'))

        nombre_seguro = secure_filename(archivo.filename)
        _, extension = os.path.splitext(nombre_seguro)
        extension = extension.lower()

        if extension not in {'.png', '.jpg', '.jpeg'}:
            flash('Formato no permitido. Suba una imagen PNG o JPG.', 'danger')
            return redirect(url_for('usuarios.firma'))

        carpeta_firmas = os.path.join(current_app.static_folder, 'firmas')
        os.makedirs(carpeta_firmas, exist_ok=True)

        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        nombre_final = f'firma_medico_{current_user.usuario_id}_{timestamp}{extension}'
        ruta_absoluta = os.path.join(carpeta_firmas, nombre_final)
        ruta_relativa = f'firmas/{nombre_final}'

        # Guardar archivo
        archivo.save(ruta_absoluta)

        # Eliminar firma anterior si existe
        if firma_actual and firma_actual.archivo:
            try:
                ruta_anterior = _resolver_ruta_absoluta(firma_actual.archivo)
                if os.path.exists(ruta_anterior):
                    os.remove(ruta_anterior)
            except OSError:
                pass

        if not firma_actual:
            firma_actual = UsuarioFirma(usuario_id=current_user.usuario_id, archivo=ruta_relativa)
            db.session.add(firma_actual)
        else:
            firma_actual.archivo = ruta_relativa
            firma_actual.fecha_subida = datetime.utcnow()

        db.session.commit()
        flash('Firma actualizada correctamente.', 'success')
        return redirect(url_for('usuarios.firma'))

    return render_template('usuarios/firma.html', firma=firma_actual)


@bp.route('/firma/eliminar', methods=['POST'])
@login_required
def eliminar_firma():
    if not _es_medico():
        flash('Solo los usuarios con rol médico pueden gestionar firmas.', 'warning')
        return redirect(url_for('dashboard.index'))

    firma_actual = current_user.firma
    if not firma_actual:
        flash('No hay firma registrada para eliminar.', 'info')
        return redirect(url_for('usuarios.firma'))

    # Eliminar archivo físico
    if firma_actual.archivo:
        try:
            ruta_archivo = _resolver_ruta_absoluta(firma_actual.archivo)
            if os.path.exists(ruta_archivo):
                os.remove(ruta_archivo)
        except OSError:
            pass

    db.session.delete(firma_actual)
    db.session.commit()
    flash('Firma eliminada correctamente.', 'success')
    return redirect(url_for('usuarios.firma'))

