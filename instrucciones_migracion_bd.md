# 🔄 Instrucciones para Actualizar el Esquema de la Base de Datos en PythonAnywhere

## ⚠️ IMPORTANTE

**La base de datos NO se sube automáticamente.** Solo se suben los cambios de código.

Si has agregado nuevas columnas o modificado el esquema, **debes aplicar esos cambios manualmente** en la base de datos de producción.

## 📋 Pasos para Aplicar Cambios

### Opción 1: Usando la consola Bash de PythonAnywhere

1. **Conecta a la base de datos SQLite:**
   ```bash
   cd /home/oscarbettinldh/LDH_Web  # o la ruta donde esté tu proyecto
   sqlite3 ldh_database.db
   ```

2. **Ejecuta los comandos SQL del archivo `X_MIGRACION_BD_PYTHONANYWHERE.sql`:**
   ```sql
   .read X_MIGRACION_BD_PYTHONANYWHERE.sql
   ```
   
   O copia y pega los comandos SQL uno por uno.

3. **Verifica que los cambios se aplicaron:**
   ```sql
   PRAGMA table_info(protocolos);
   PRAGMA table_info(prestadores);
   ```
   
4. **Sal de SQLite:**
   ```sql
   .quit
   ```

### Opción 2: Usando DBeaver o herramienta gráfica

1. Conecta DBeaver a tu base de datos en PythonAnywhere (vía SSH o descargando el archivo)
2. Abre el archivo `X_MIGRACION_BD_PYTHONANYWHERE.sql`
3. Ejecuta los comandos SQL

### Opción 3: Desde Python (usando Flask shell)

1. En la consola Bash de PythonAnywhere:
   ```bash
   cd /home/oscarbettinldh/LDH_Web
   python3.10 -m flask --app app shell
   ```

2. En el shell de Flask:
   ```python
   from extensions import db
   from app import create_app
   app = create_app('production')
   with app.app_context():
       # Ejecutar comandos SQL directamente
       db.session.execute("ALTER TABLE protocolos ADD COLUMN prestador_medico_id INTEGER")
       db.session.commit()
       # ... etc
   ```

## 📝 Cambios que se Aplican

### Tabla `protocolos`:
- ✅ `prestador_medico_id` - Prestador médico asociado cuando el prestador principal es una entidad
- ✅ `con_orden` - Si el protocolo tiene orden médica
- ✅ `entregado` - Si el protocolo fue entregado
- ✅ `cobrado` - Si el protocolo fue cobrado

### Tabla `prestadores`:
- ✅ `es_entidad` - Si es una entidad (hospital/clínica)
- ✅ `puede_ver_ambulatorio` - Permiso para ver protocolos ambulatorios
- ✅ `puede_ver_internacion` - Permiso para ver protocolos de internación
- ✅ `notificar_email` - Notificar por email
- ✅ `notificar_whatsapp` - Notificar por WhatsApp
- ✅ `notificar_ambulatorio` - Recibir notificaciones de ambulatorios
- ✅ `notificar_internacion` - Recibir notificaciones de internación
- ✅ `whatsapp` - Número de WhatsApp

## ⚠️ Precauciones

1. **Haz un backup antes de aplicar cambios:**
   ```bash
   cp ldh_database.db ldh_database_backup_$(date +%Y%m%d_%H%M%S).db
   ```

2. **Si una columna ya existe**, SQLite dará un error pero no afectará la base de datos.

3. **No ejecutes los comandos dos veces** si ya los aplicaste anteriormente.

## 🔍 Verificar que Todo Funciona

Después de aplicar los cambios:

1. Reinicia la aplicación web en PythonAnywhere
2. Verifica que no haya errores en los logs
3. Prueba crear/editar un protocolo para asegurarte de que los nuevos campos funcionan

