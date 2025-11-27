"""
LDH Web - Sistema de Gestión de Laboratorio de Anatomía Patológica
Aplicación principal Flask
"""
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import current_user
from config import config
from extensions import db, login_manager
import os
import unicodedata


def create_app(config_name='development'):
    """Factory para crear la aplicación Flask"""
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Inicializar extensiones con la app
    db.init_app(app)
    login_manager.init_app(app)
    
    # Configurar Flask-Login
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor inicie sesión para acceder a esta página.'
    login_manager.login_message_category = 'warning'
    login_manager.session_protection = 'strong'
    
    # Crear carpetas necesarias si no existen
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['PDF_FOLDER'], exist_ok=True)
    if app.config.get('PDF_TEMP_FOLDER'):
        os.makedirs(app.config['PDF_TEMP_FOLDER'], exist_ok=True)

    # Configurar fontconfig para WeasyPrint en Windows (Conda)
    fontconfig_dir = os.path.join(os.environ.get('CONDA_PREFIX', ''), 'Library', 'etc', 'fonts')
    fontconfig_file = os.path.join(fontconfig_dir, 'fonts.conf')
    if os.path.isfile(fontconfig_file):
        os.environ.setdefault('FONTCONFIG_FILE', fontconfig_file)
        os.environ.setdefault('FONTCONFIG_PATH', fontconfig_dir)
    
    # Registrar blueprints (rutas)
    from routes import auth, dashboard, pacientes, prestadores, obras_sociales
    from routes import protocolos, biopsias, citologia, pap, reportes, admin, asistente, plantillas_dinamicas, editor_avanzado, selector_plantillas, usuarios
    from routes import prestador_portal, entidades
    
    app.register_blueprint(auth.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(pacientes.bp)
    app.register_blueprint(prestadores.bp)
    app.register_blueprint(obras_sociales.bp)
    app.register_blueprint(protocolos.bp)
    app.register_blueprint(biopsias.bp)
    app.register_blueprint(citologia.bp)
    app.register_blueprint(pap.bp)
    app.register_blueprint(reportes.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(asistente.bp)
    app.register_blueprint(plantillas_dinamicas.bp)
    app.register_blueprint(editor_avanzado.bp)
    app.register_blueprint(selector_plantillas.bp)
    app.register_blueprint(usuarios.bp)
    app.register_blueprint(prestador_portal.bp)
    app.register_blueprint(entidades.bp)
    
    # Ruta principal
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard.index'))
        return redirect(url_for('auth.login'))
    
    # Manejadores de errores
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500
    
    # Filtros personalizados para templates
    @app.template_filter('fecha_formato')
    def fecha_formato(fecha):
        """Convierte una fecha a formato dd/mmm/yyyy"""
        if not fecha:
            return ''
        
        meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 
                'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
        
        dia = fecha.strftime('%d')
        mes_nombre = meses[fecha.month - 1]
        año = fecha.strftime('%Y')
        
        return f"{dia}/{mes_nombre}/{año}"
    
    # Context processors (variables disponibles en todos los templates)
    @app.context_processor
    def inject_config():
        from datetime import datetime
        return {
            'laboratorio_nombre': app.config['LABORATORIO_NOMBRE'],
            'laboratorio_direccion': app.config['LABORATORIO_DIRECCION'],
            'laboratorio_telefono': app.config['LABORATORIO_TELEFONO'],
            'laboratorio_email': app.config['LABORATORIO_EMAIL'],
            'now': datetime.now
        }
    
    # Función para verificar permisos
    @app.context_processor
    def inject_permissions():
        def tiene_permiso(codigo_permiso):
            """Verifica si el usuario actual tiene un permiso específico"""
            if not current_user.is_authenticated:
                return False
            
            # OSCAR y Administrador tienen todos los permisos
            if current_user.rol.nombre in ['OSCAR', 'Administrador']:
                return True
            
            # Verificar si el rol del usuario tiene el permiso
            for permiso in current_user.rol.permisos:
                if permiso.codigo == codigo_permiso:
                    return True
            return False
        
        return dict(tiene_permiso=tiene_permiso)
    
    @app.context_processor
    def inject_medico_helpers():
        def _normalizar_texto(texto: str) -> str:
            if not texto:
                return ''
            texto = unicodedata.normalize('NFD', texto.strip().lower())
            return ''.join(ch for ch in texto if unicodedata.category(ch) != 'Mn')

        def rol_es_medico(rol_nombre: str) -> bool:
            normalizado = _normalizar_texto(rol_nombre)
            return 'medico' in normalizado if normalizado else False

        def usuario_es_medico() -> bool:
            if not current_user.is_authenticated or not getattr(current_user, 'rol', None):
                return False
            return rol_es_medico(getattr(current_user.rol, 'nombre', ''))

        def rol_es_prestador(rol_nombre: str) -> bool:
            normalizado = _normalizar_texto(rol_nombre)
            return 'prestador' in normalizado if normalizado else False

        def usuario_es_prestador() -> bool:
            if not current_user.is_authenticated or not getattr(current_user, 'rol', None):
                return False
            return rol_es_prestador(getattr(current_user.rol, 'nombre', ''))

        def rol_es_entidad(rol_nombre: str) -> bool:
            normalizado = _normalizar_texto(rol_nombre)
            return normalizado == 'entidades' if normalizado else False

        def usuario_es_entidad() -> bool:
            if not current_user.is_authenticated or not getattr(current_user, 'rol', None):
                return False
            return rol_es_entidad(getattr(current_user.rol, 'nombre', ''))
        
        return dict(
            rol_es_medico=rol_es_medico,
            usuario_es_medico=usuario_es_medico,
            rol_es_prestador=rol_es_prestador,
            usuario_es_prestador=usuario_es_prestador,
            rol_es_entidad=rol_es_entidad,
            usuario_es_entidad=usuario_es_entidad
        )
    
    @app.context_processor
    def inject_asistente_alertas():
        mensajes_asistente_pendientes = 0
        if current_user.is_authenticated and getattr(current_user, 'rol', None) and getattr(current_user.rol, 'nombre', '') == 'Administrador':
            from models.auditoria import Auditoria
            from datetime import datetime, timedelta
            limite = datetime.utcnow() - timedelta(days=3)
            mensajes_asistente_pendientes = Auditoria.query.filter(
                Auditoria.accion.in_(['ASISTENTE_MENSAJE', 'ASISTENTE_LOGIN_MENSAJE']),
                Auditoria.fecha_hora >= limite
            ).count()
        return dict(mensajes_asistente_pendientes=mensajes_asistente_pendientes)
    
    # Comando para inicializar la base de datos
    @app.cli.command()
    def initdb():
        """Inicializa la base de datos con las tablas y datos iniciales."""
        from models import Usuario, Rol
        from utils.init_permisos import init_roles_y_permisos
        
        db.create_all()
        print('✓ Base de datos inicializada')
        
        # Inicializar roles y permisos
        print('\nInicializando roles y permisos...')
        init_roles_y_permisos()
        
        # Crear usuario administrador por defecto
        admin_rol = Rol.query.filter_by(nombre='Administrador').first()
        if not Usuario.query.filter_by(username='admin').first():
            admin = Usuario(
                username='admin',
                email='admin@ldh.local',
                nombre_completo='OSCAR (Administrador)',
                rol_id=admin_rol.rol_id,
                activo=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print('\n✓ Usuario administrador creado')
            print('  Usuario: admin')
            print('  Contraseña: admin123')
            print('  Rol: Administrador')
        
        print('\n✅ Inicialización completada')
    
    return app


# User loader para Flask-Login
@login_manager.user_loader
def load_user(usuario_id):
    from models.usuario import Usuario
    try:
        # Flask-Login pasa el ID como string, convertir a int
        if isinstance(usuario_id, str):
            usuario_id = int(usuario_id)
        return Usuario.query.get(usuario_id)
    except (ValueError, TypeError):
        return None


# Punto de entrada
if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)

