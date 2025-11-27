# 📦 Cambios para Despliegue - 27 de Noviembre 2025

## ✅ Nuevas Funcionalidades

### 1. Herramientas de Base de Datos para el Asistente
**Archivos nuevos:**
- `services/asistente_db_tools.py` - Funciones para consultar la base de datos

**Archivos modificados:**
- `services/claude_client.py` - Agregado soporte de function calling (tools) para Claude API

**Funcionalidades agregadas:**
- El asistente puede consultar datos reales del sistema:
  - Top 10 prestadores con más pacientes
  - Pacientes con múltiples protocolos
  - Estadísticas generales de protocolos

**Cómo funciona:**
- Cuando el usuario pregunta algo como "¿cuáles son los 10 prestadores con más pacientes?", el asistente automáticamente usa la herramienta `obtener_top_prestadores_por_pacientes`
- La herramienta consulta la base de datos y retorna los resultados
- El asistente formatea la respuesta de manera natural

## ✅ Archivos de Despliegue

### 1. `wsgi.py` (NUEVO)
- Configurado para PythonAnywhere
- **IMPORTANTE**: Cambiar `/home/tuusuario/LDH_Web` por tu usuario real

### 2. `DESPLIEGUE_PYTHONANYWHERE.md` (NUEVO)
- Guía completa paso a paso para el despliegue
- Instrucciones de configuración
- Solución de problemas comunes

## 📝 Archivos Modificados

1. **`services/claude_client.py`**
   - Importa herramientas de base de datos
   - Agrega soporte de function calling a Claude API
   - Maneja iteraciones para tool calls
   - Actualiza system prompts para indicar que tiene acceso a herramientas

2. **`.gitignore`**
   - Agregado comentario sobre wsgi.py

## 🔧 Cambios Técnicos

### Function Calling en Claude API
- Se agregó el parámetro `tools` a las peticiones a Claude API
- Se implementa un loop para manejar múltiples tool calls
- Las herramientas se ejecutan y sus resultados se envían de vuelta a Claude

### Nuevas Herramientas Disponibles
1. `obtener_top_prestadores_por_pacientes(limite=10)`
   - Retorna prestadores médicos ordenados por cantidad de pacientes únicos
   - Excluye entidades y protocolos de prueba

2. `obtener_pacientes_con_multiples_protocolos(min_protocolos=2)`
   - Retorna pacientes que tienen más de un protocolo
   - Útil para identificar pacientes recurrentes

3. `obtener_estadisticas_protocolos()`
   - Retorna estadísticas generales:
     - Total de protocolos
     - Pacientes únicos
     - Protocolos por estado
     - Protocolos por tipo de estudio

## 🚀 Pasos para Desplegar

1. **Subir archivos a PythonAnywhere**
   - Todo el directorio `LDH_Web/` debe estar en `/home/tuusuario/LDH_Web`

2. **Configurar wsgi.py**
   - Cambiar `tuusuario` por tu usuario real de PythonAnywhere

3. **Instalar dependencias**
   ```bash
   pip3.10 install --user -r requirements.txt
   ```

4. **Configurar variables de entorno**
   - SECRET_KEY
   - ANTHROPIC_API_KEY (para Claude)
   - GEMINI_API_KEY (para análisis de imágenes)
   - Variables SMTP (si usas notificaciones por email)

5. **Reiniciar la aplicación web**

6. **Probar el asistente**
   - Preguntar: "¿cuáles son los 10 prestadores con más pacientes?"

## ⚠️ Notas Importantes

- Las herramientas solo funcionan si `services/asistente_db_tools.py` está presente
- Si hay errores de importación, el sistema funcionará pero el asistente no podrá consultar la base de datos
- Los errores se registran en los logs del servidor

## 📚 Documentación

Ver `DESPLIEGUE_PYTHONANYWHERE.md` para instrucciones detalladas.

