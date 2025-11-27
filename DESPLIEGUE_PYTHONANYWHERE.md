# 🚀 Guía de Despliegue en PythonAnywhere

## 📋 Preparación

### 1. Archivos importantes
- ✅ `wsgi.py` - Configurado y listo
- ✅ `requirements.txt` - Todas las dependencias incluidas
- ✅ `config.py` - Configuración de producción disponible

### 2. Cambios recientes a desplegar

#### Nuevas funcionalidades:
- ✅ **Herramientas de base de datos para el asistente**: Ahora el asistente puede consultar datos reales del sistema
  - `services/asistente_db_tools.py` - Nuevo archivo con funciones de consulta
  - `services/claude_client.py` - Actualizado con soporte de function calling
  - El asistente puede responder preguntas como:
    - "¿Cuáles son los 10 prestadores con más pacientes?"
    - "¿Qué pacientes tienen más de un protocolo?"
    - "Estadísticas de protocolos"

## 🔧 Pasos de Despliegue

### Paso 1: Subir archivos
```bash
# Desde tu máquina local, en el directorio LDH_Web:
# Subir todos los archivos al servidor PythonAnywhere
# Puedes usar Git o FileZilla/FTP
```

### Paso 2: Configurar wsgi.py
1. En PythonAnywhere, abre el archivo `wsgi.py`
2. Cambia `/home/tuusuario/LDH_Web` por tu ruta real:
   ```python
   project_home = '/home/tuusuario/LDH_Web'  # Reemplazar 'tuusuario'
   ```

### Paso 3: Instalar dependencias
En la consola Bash de PythonAnywhere:
```bash
cd /home/tuusuario/LDH_Web
pip3.10 install --user -r requirements.txt
```

### Paso 4: Configurar variables de entorno
En la pestaña "Web" → "Environment variables", agregar:
```
SECRET_KEY=tu-clave-secreta-super-segura-aqui
DATABASE_URL=sqlite:////home/tuusuario/LDH_Web/ldh_database.db
LABORATORIO_EMAIL=info@tudominio.com
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=...
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu-email@gmail.com
SMTP_PASSWORD=tu-password
SMTP_USE_TLS=True
```

### Paso 5: Crear directorios necesarios
```bash
cd /home/tuusuario/LDH_Web
mkdir -p static/uploads static/pdf
```

### Paso 6: Inicializar base de datos (si es primera vez)
```bash
cd /home/tuusuario/LDH_Web
python3.10 -m flask --app app initdb
```

### Paso 7: Configurar la aplicación web
1. En PythonAnywhere, ve a la pestaña **"Web"**
2. Haz clic en **"Add a new web app"** (o edita la existente)
3. Selecciona **"Manual configuration"**
4. Selecciona **Python 3.10** (o la versión que uses)
5. En **"WSGI configuration file"**, edita el archivo y asegúrate de que apunte a tu `wsgi.py`
6. El contenido debe ser algo como:
   ```python
   import sys
   project_home = '/home/tuusuario/LDH_Web'
   if project_home not in sys.path:
       sys.path.insert(0, project_home)
   
   from wsgi import application
   ```

### Paso 8: Configurar dominio y HTTPS
1. En la pestaña **"Web"**, en **"Domains"**, agrega tu dominio personalizado (ej: `ldh.com.ar`)
2. Si ya tienes el dominio configurado, verifica que esté apuntando a PythonAnywhere
3. En **"Security"**, configura el SSL/TLS (Let's Encrypt es gratuito)

### Paso 9: Reiniciar la aplicación
1. Haz clic en el botón verde **"Reload"** en la pestaña "Web"
2. Verifica los logs si hay errores

### Paso 10: Verificar funcionamiento
1. Accede a tu dominio (ej: `https://ldh.com.ar`)
2. Verifica que el login funcione
3. Prueba el asistente con una consulta como: "¿cuáles son los 10 prestadores con más pacientes?"

## 🐛 Solución de Problemas

### Error: "No module named 'services.asistente_db_tools'"
**Solución**: Verifica que el archivo `services/asistente_db_tools.py` esté en el servidor.

### Error: "SECRET_KEY not set"
**Solución**: Agrega `SECRET_KEY` en las variables de entorno de PythonAnywhere.

### Error: "Database locked"
**Solución**: Asegúrate de que solo una instancia de la aplicación esté usando la base de datos.

### El asistente no puede consultar la base de datos
**Verifica**:
1. Que `services/asistente_db_tools.py` esté presente
2. Que las herramientas estén importadas correctamente en `claude_client.py`
3. Revisa los logs del servidor para ver errores específicos

### Error: "Application failed to respond"
**Solución**: 
1. Revisa los logs en la pestaña "Web" → "Error log"
2. Verifica que todas las dependencias estén instaladas
3. Verifica que la ruta en `wsgi.py` sea correcta

## 📝 Notas Importantes

- **Backups**: Asegúrate de hacer backups regulares de la base de datos
- **Variables de entorno**: Nunca subas archivos `.env` con claves secretas al repositorio
- **Logs**: Revisa periódicamente los logs en PythonAnywhere
- **Actualizaciones**: Cuando subas cambios, siempre reinicia la aplicación web

## 🔄 Actualizar después de cambios

1. Subir archivos modificados
2. En PythonAnywhere, en la consola Bash:
   ```bash
   cd /home/tuusuario/LDH_Web
   pip3.10 install --user -r requirements.txt  # Solo si hay nuevas dependencias
   ```
3. Reiniciar la aplicación web (botón "Reload")

## 📚 Recursos

- [Documentación de PythonAnywhere](https://help.pythonanywhere.com/)
- [Documentación de Flask en producción](https://flask.palletsprojects.com/en/latest/deploying/)
- Logs del servidor: Pestaña "Web" → "Error log" y "Server log"

