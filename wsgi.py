#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WSGI entry point para PythonAnywhere
"""
import sys
import os

# Agregar el directorio del proyecto al path
project_home = '/home/tuusuario/LDH_Web'  # CAMBIAR 'tuusuario' por tu usuario de PythonAnywhere
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Configurar variables de entorno si es necesario
# os.environ['FLASK_ENV'] = 'production'

# Importar la aplicación
from app import create_app

# Crear la aplicación
application = create_app(config_name='production')

# Para debugging (opcional)
if __name__ == '__main__':
    application.run()

