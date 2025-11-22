# Configuración de Google Gemini para Análisis de Imágenes

El sistema LDH ahora integra **Google Gemini** para análisis de imágenes médicas, mientras usa **Claude Haiku** para conversaciones de texto.

## 🎯 Uso Automático

El sistema selecciona automáticamente qué API usar:

- **📸 Con imágenes**: Usa **Gemini** (especializado en visión)
- **💬 Solo texto**: Usa **Claude Haiku** (rápido y económico)

## 🔑 Obtener API Key de Gemini

1. Ve a: https://aistudio.google.com/app/apikey
2. Inicia sesión con tu cuenta de Google
3. Haz clic en "Create API Key" o "Crear clave de API"
4. Copia la API key generada

## ⚙️ Configuración

### Opción 1: Variable de Entorno (Recomendado)

En PowerShell (Anaconda):

```powershell
$env:GEMINI_API_KEY="tu-api-key-aqui"
```

**Importante**: Esta configuración solo dura mientras la ventana de PowerShell esté abierta.

### Opción 2: Configuración Permanente en Windows

1. Panel de Control → Sistema → Configuración avanzada del sistema
2. Variables de entorno → Variables de usuario → Nueva
3. Nombre: `GEMINI_API_KEY`
4. Valor: Tu API key de Gemini
5. Reinicia la aplicación Flask

### Opción 3: Archivo .env (si lo usas)

Crea un archivo `.env` en la raíz del proyecto:

```
GEMINI_API_KEY=tu-api-key-aqui
```

## 📝 Modelos Disponibles

Por defecto se usa `gemini-1.5-flash` (rápido, soporta visión).

Para cambiar el modelo, edita `config.py` línea 63:

```python
GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-1.5-flash')
```

Modelos disponibles:
- `gemini-1.5-flash` - Rápido, soporta visión (recomendado)
- `gemini-1.5-pro` - Más potente, soporta visión
- `gemini-pro-vision` - Legacy, soporta visión

## ✅ Verificar Configuración

1. Reinicia el servidor Flask
2. En el navegador: `http://127.0.0.1:5000/asistente/gemini/estado`
3. Deberías ver `"gemini_disponible": true`

## 🔍 Uso en el Chat

El sistema detecta automáticamente si hay imágenes:

- **Si adjuntas imágenes**: El sistema usa Gemini automáticamente
- **Si solo escribes texto**: El sistema usa Claude Haiku

No necesitas hacer nada especial, el sistema selecciona la API correcta automáticamente.

## 🆘 Solución de Problemas

### Error: "Gemini API no está configurada"

- Verifica que la variable de entorno `GEMINI_API_KEY` esté configurada
- Reinicia el servidor Flask después de configurar la variable

### Error: "Invalid API key"

- Verifica que copiaste correctamente la API key
- Asegúrate de que la API key esté activa en Google AI Studio

### No analiza imágenes

- Verifica que la variable `GEMINI_API_KEY` esté configurada
- Verifica el estado en `/asistente/gemini/estado`
- Revisa los logs del servidor Flask para más detalles

## 📊 Límites

- **Imágenes por mensaje**: Máximo 5 imágenes
- **Timeout**: 120 segundos para análisis de imágenes
- **Tamaño**: Las imágenes se envían en base64

## 💡 Notas

- Gemini es gratuito para uso básico (con límites de uso)
- Para uso comercial, revisa los términos de Google AI Studio
- El sistema usa automáticamente la mejor API según el tipo de solicitud

