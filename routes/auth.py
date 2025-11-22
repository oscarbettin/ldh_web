"""
Rutas de autenticación (login, logout)
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db
from models.usuario import Usuario
from models.auditoria import Auditoria
from datetime import datetime
import unicodedata

bp = Blueprint('auth', __name__, url_prefix='/auth')


def _normalizar_texto(texto: str) -> str:
    if not texto:
        return ''
    texto = unicodedata.normalize('NFD', texto.strip().lower())
    return ''.join(ch for ch in texto if unicodedata.category(ch) != 'Mn')


def _rol_es_prestador(nombre_rol: str) -> bool:
    return 'prestador' in _normalizar_texto(nombre_rol) if nombre_rol else False


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Página de inicio de sesión"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember', False) == 'on'
        
        if not username or not password:
            flash('Por favor ingrese usuario y contraseña.', 'warning')
            return render_template('auth/login.html', asistente_context='login')
        
        # Búsqueda case-insensitive del username
        usuario = Usuario.query.filter(Usuario.username.ilike(username)).first()
        
        if not usuario:
            flash('Usuario no encontrado.', 'danger')
            return render_template('auth/login.html', asistente_context='login')
        
        if not usuario.activo:
            flash('Usuario inactivo. Contacte al administrador.', 'warning')
            return render_template('auth/login.html', asistente_context='login')
        
        if not usuario.check_password(password):
            flash('Contraseña incorrecta.', 'danger')
            # Registrar intento fallido
            Auditoria.registrar(
                usuario_id=usuario.usuario_id,
                accion='LOGIN_FALLIDO',
                descripcion=f'Intento de login fallido para usuario {username}',
                ip_address=request.remote_addr
            )
            return render_template('auth/login.html', asistente_context='login')
        
        # Login exitoso
        login_user(usuario, remember=remember)
        usuario.ultimo_acceso = datetime.utcnow()
        db.session.commit()
        
        # Registrar login exitoso
        Auditoria.registrar(
            usuario_id=usuario.usuario_id,
            accion='LOGIN',
            descripcion=f'Login exitoso de {username}',
            ip_address=request.remote_addr
        )
        
        # Mensaje de bienvenida temporal (se maneja en el frontend)
        # flash(f'Bienvenido, {usuario.nombre_completo}!', 'success')
        
        # Redirigir a la página solicitada o al dashboard
        next_page = request.args.get('next')
        if next_page and next_page.startswith('/'):
            return redirect(next_page)
        if _rol_es_prestador(getattr(usuario.rol, 'nombre', '')):
            return redirect(url_for('portal_prestador.dashboard'))
        return redirect(url_for('dashboard.index'))
    
    return render_template('auth/login.html', asistente_context='login')


@bp.route('/logout')
@login_required
def logout():
    """Cerrar sesión"""
    # Registrar logout
    Auditoria.registrar(
        usuario_id=current_user.usuario_id,
        accion='LOGOUT',
        descripcion=f'Logout de {current_user.username}',
        ip_address=request.remote_addr
    )
    
    logout_user()
    flash('Sesión cerrada correctamente.', 'info')
    return redirect(url_for('auth.login'))


@bp.route('/cambiar-password', methods=['GET', 'POST'])
@login_required
def cambiar_password():
    """Cambiar contraseña del usuario actual"""
    if request.method == 'POST':
        password_actual = request.form.get('password_actual')
        password_nuevo = request.form.get('password_nuevo')
        password_confirmar = request.form.get('password_confirmar')
        
        if not current_user.check_password(password_actual):
            flash('La contraseña actual es incorrecta.', 'danger')
            return render_template('auth/cambiar_password.html')
        
        if password_nuevo != password_confirmar:
            flash('Las contraseñas nuevas no coinciden.', 'danger')
            return render_template('auth/cambiar_password.html')
        
        if len(password_nuevo) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'warning')
            return render_template('auth/cambiar_password.html')
        
        # Cambiar contraseña
        current_user.set_password(password_nuevo)
        db.session.commit()
        
        # Registrar cambio
        Auditoria.registrar(
            usuario_id=current_user.usuario_id,
            accion='CAMBIO_PASSWORD',
            descripcion=f'Cambio de contraseña de {current_user.username}',
            ip_address=request.remote_addr
        )
        
        flash('Contraseña cambiada correctamente.', 'success')
        return redirect(url_for('dashboard.index'))
    
    return render_template('auth/cambiar_password.html')

