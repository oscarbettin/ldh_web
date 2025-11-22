"""
Decoradores para control de permisos
"""
from functools import wraps
from flask import flash, redirect, url_for, abort
from flask_login import current_user


def permission_required(codigo_permiso):
    """
    Decorador para verificar permisos en las rutas
    
    Uso:
        @bp.route('/nuevo')
        @login_required
        @permission_required('pacientes_crear')
        def nuevo():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Debe iniciar sesión para acceder.', 'warning')
                return redirect(url_for('auth.login'))
            
            # OSCAR y Administrador siempre tienen permiso
            if current_user.rol.nombre in ['OSCAR', 'Administrador']:
                return f(*args, **kwargs)
            
            # Verificar si el usuario tiene el permiso
            if not current_user.tiene_permiso(codigo_permiso):
                flash('No tiene permisos para realizar esta acción.', 'danger')
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    """
    Decorador para rutas que solo puede acceder el administrador
    
    Uso:
        @bp.route('/admin/usuarios')
        @login_required
        @admin_required
        def gestionar_usuarios():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Debe iniciar sesión para acceder.', 'warning')
            return redirect(url_for('auth.login'))
        
        if current_user.rol.nombre not in ['OSCAR', 'Administrador']:
            flash('Esta sección es solo para administradores.', 'danger')
            abort(403)
        
        return f(*args, **kwargs)
    return decorated_function

