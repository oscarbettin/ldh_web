"""
Extensiones de Flask
Creadas aquí para evitar importaciones circulares
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# Inicializar extensiones
db = SQLAlchemy()
login_manager = LoginManager()

