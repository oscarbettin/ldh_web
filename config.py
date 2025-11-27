"""
Configuración de la aplicación LDH Web
"""
import os
from datetime import timedelta

# Directorio base del proyecto
basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Configuración base"""
    
    # Clave secreta para sesiones (cambiar en producción)
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-cambiar-en-produccion'
    
    # Base de datos SQLite
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'ldh_database.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configuración de sesiones
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_COOKIE_SECURE = False  # Cambiar a True en producción con HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Paginación
    ITEMS_PER_PAGE = 50
    
    # Uploads (para logos, imágenes, etc)
    UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
    
    # PDFs
    PDF_FOLDER = os.path.join(basedir, 'static', 'pdf')
    
    # Configuración de informes
    LABORATORIO_NOMBRE = "Laboratorio de Diagnóstico Histopatológico"
    LABORATORIO_DIRECCION = ""
    LABORATORIO_TELEFONO = ""
    # Email del laboratorio (usado como remitente en respuestas automáticas)
    # IMPORTANTE: Configura este email para que funcione la respuesta a mensajes
    LABORATORIO_EMAIL = os.environ.get('LABORATORIO_EMAIL', 'info@laboratorio.com')
    
    # Configuración de SMTP para envío de emails
    # 
    # EJEMPLOS DE CONFIGURACIÓN POR PROVEEDOR:
    # 
    # Gmail:
    #   SMTP_HOST = 'smtp.gmail.com'
    #   SMTP_PORT = 587
    #   SMTP_USER = 'tu-email@gmail.com'
    #   SMTP_PASSWORD = 'tu-app-password'  # Necesitas crear una "App Password" en Google
    #   SMTP_USE_TLS = True
    # 
    # Outlook/Hotmail:
    #   SMTP_HOST = 'smtp-mail.outlook.com'
    #   SMTP_PORT = 587
    #   SMTP_USER = 'tu-email@outlook.com'
    #   SMTP_PASSWORD = 'tu-password'
    #   SMTP_USE_TLS = True
    # 
    # Servidor propio (ej: postfix, sendmail):
    #   SMTP_HOST = 'localhost' o la IP de tu servidor
    #   SMTP_PORT = 25 o 587
    #   SMTP_USER = ''  # Dejar vacío si no requiere autenticación
    #   SMTP_PASSWORD = ''  # Dejar vacío si no requiere autenticación
    #   SMTP_USE_TLS = False (generalmente)
    #
    # También puedes configurar estos valores mediante variables de entorno:
    #   export SMTP_HOST=smtp.gmail.com
    #   export SMTP_PORT=587
    #   export SMTP_USER=tu-email@gmail.com
    #   export SMTP_PASSWORD=tu-password
    #   export SMTP_USE_TLS=True
    
    SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
    SMTP_USER = os.environ.get('SMTP_USER', '')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
    SMTP_USE_TLS = os.environ.get('SMTP_USE_TLS', 'True').lower() in ('true', '1', 'yes')
    
    # Configuración de Claude API
    # IMPORTANTE: Verifica qué modelos están disponibles en tu plan de Anthropic
    # Modelos disponibles (ordenados por disponibilidad común):
    # - claude-3-haiku-20240307 (SIEMPRE disponible, NO soporta visión) - FALLBACK SEGURO
    # - claude-3-sonnet-20240229 (balanceado, soporta visión)
    # - claude-3-5-sonnet-20240620 (más reciente, soporta visión)
    # - claude-3-opus-20240229 (más potente, soporta visión, requiere plan Pro)
    # - claude-3-5-opus-20241022 (más reciente, requiere plan Pro)
    # Si tienes problemas, usa Haiku primero para verificar que la API funciona
    CLAUDE_MODEL = os.environ.get('CLAUDE_MODEL', 'claude-3-haiku-20240307')
    
    # Configuración de Google Gemini API (para análisis de imágenes médicas)
    # Modelos disponibles (todos los Gemini 2.0+ son multimodales y soportan visión):
    # - gemini-2.5-flash (estable, multimodal, rápido) - RECOMENDADO
    # - gemini-2.0-flash (estable, multimodal, rápido)
    # - gemini-2.5-pro (estable, multimodal, más potente)
    # - gemini-2.0-flash-001 (versión específica estable)
    # - gemini-flash-latest (latest, multimodal)
    # - gemini-pro-vision (legacy, siempre disponible)
    # IMPORTANTE: La API key debe configurarse mediante variable de entorno GEMINI_API_KEY
    # No hardcodear la API key en el código por seguridad
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
    GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash')  # Gemini 2.5 Flash es multimodal (soporta visión)
    
    # Formato de números de protocolo
    FORMATO_PROTOCOLO_BIOPSIA = "B-{año}-{numero:04d}"
    FORMATO_PROTOCOLO_CITOLOGIA = "C-{año}-{numero:04d}"
    FORMATO_PROTOCOLO_PAP = "P-{año}-{numero:04d}"
    
    # Debug
    DEBUG = True


class ProductionConfig(Config):
    """Configuración para producción"""
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    
    # En producción, SECRET_KEY debe venir de variable de entorno
    # IMPORTANTE: No usar @property, Flask necesita un valor string directo
    SECRET_KEY = os.environ.get('SECRET_KEY') or ''


class DevelopmentConfig(Config):
    """Configuración para desarrollo"""
    DEBUG = True
    SQLALCHEMY_ECHO = False  # True para ver queries SQL


class TestingConfig(Config):
    """Configuración para testing"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


# Configuración por defecto
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

