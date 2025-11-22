#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Cliente para integración con Google Gemini API
Especializado en análisis de imágenes médicas
"""

import os
import json
import requests
import base64
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class GeminiClient:
    """Cliente para interactuar con Google Gemini API"""
    
    def __init__(self, modelo=None):
        # Intentar obtener API key desde variable de entorno primero
        self.api_key = os.getenv('GEMINI_API_KEY')
        
        # Si no está en variable de entorno, intentar desde Flask config (para desarrollo)
        if not self.api_key:
            try:
                from flask import current_app
                self.api_key = current_app.config.get('GEMINI_API_KEY', '')
            except:
                pass
        
        # Si aún no hay API key, intentar leerla desde config.py directamente (fallback)
        if not self.api_key:
            try:
                from config import Config
                config = Config()
                self.api_key = getattr(config, 'GEMINI_API_KEY', '')
            except:
                pass
        
        # Modelos disponibles:
        # - gemini-2.5-flash (estable, multimodal, rápido) - RECOMENDADO
        # - gemini-2.0-flash (estable, multimodal, rápido)
        # - gemini-2.5-pro (estable, multimodal, más potente)
        # - gemini-pro-vision (legacy, siempre disponible)
        
        # Intentar obtener modelo desde Flask config
        try:
            from flask import current_app
            modelo_config = current_app.config.get('GEMINI_MODEL')
        except:
            modelo_config = None
        
        if modelo:
            self.model = modelo
        elif modelo_config:
            self.model = modelo_config
        else:
            self.model = os.getenv('GEMINI_MODEL', "gemini-2.5-flash")  # Por defecto usar gemini-2.5-flash (multimodal)
        
        # Base URL para Gemini API
        # Intentar primero con v1beta (más reciente), si falla usar v1
        # Formato: https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent
        self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        self.base_url_v1 = f"https://generativelanguage.googleapis.com/v1/models/{self.model}:generateContent"
        
        # Log del modelo seleccionado
        modelo_origen = "parámetro" if modelo else ("config.py" if modelo_config else "variable de entorno o default")
        logger.info(f"🤖 GeminiClient inicializado - Modelo: {self.model} (origen: {modelo_origen})")
    
    def is_configured(self) -> bool:
        """Verificar si la API key está configurada"""
        return bool(self.api_key)
    
    def listar_modelos_disponibles(self) -> List[Dict]:
        """
        Listar modelos disponibles en Gemini API
        """
        if not self.api_key:
            return []
        
        modelos_disponibles = []
        
        # Intentar con v1beta primero
        for version in ['v1beta', 'v1']:
            try:
                url = f"https://generativelanguage.googleapis.com/{version}/models"
                params = {"key": self.api_key}
                
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                if 'models' in data:
                    for modelo in data['models']:
                        nombre = modelo.get('name', '')
                        # Extraer solo el nombre del modelo (sin el prefijo "models/")
                        if 'models/' in nombre:
                            nombre = nombre.split('models/')[1]
                        
                        metodos = modelo.get('supportedGenerationMethods', [])
                        
                        # Los modelos Gemini 2.0+ son multimodales por defecto (soportan visión)
                        # También modelos con "vision" en el nombre
                        es_multimodal = (
                            'vision' in nombre.lower() or 
                            'pro-vision' in nombre.lower() or
                            nombre.startswith('gemini-2.') or  # Gemini 2.0+ son multimodales
                            nombre.startswith('gemini-3.') or  # Gemini 3.0+ son multimodales
                            'multimodal' in modelo.get('description', '').lower()
                        )
                        
                        modelos_disponibles.append({
                            'nombre': nombre,
                            'display_name': modelo.get('displayName', ''),
                            'description': modelo.get('description', ''),
                            'supported_generation_methods': metodos,
                            'version': version,
                            'soporta_vision': es_multimodal,
                            'soporta_generateContent': 'generateContent' in metodos
                        })
                
                # Si encontramos modelos, no intentar con la siguiente versión
                if modelos_disponibles:
                    break
                    
            except Exception as e:
                logger.warning(f"Error listando modelos de Gemini con {version}: {e}")
                continue
        
        return modelos_disponibles
    
    def encontrar_modelo_funcional(self) -> Optional[str]:
        """
        Encontrar automáticamente un modelo que funcione con visión
        
        Returns:
            Nombre del modelo que funciona, o None si no se encuentra ninguno
        """
        modelos_a_probar = [
            'gemini-2.5-flash',  # Estable, multimodal
            'gemini-2.0-flash',  # Estable, multimodal
            'gemini-2.5-pro',    # Estable, multimodal, más potente
            'gemini-2.0-flash-001',  # Versión específica estable
            'gemini-flash-latest',  # Latest
            'gemini-pro-latest',    # Latest
            'gemini-pro-vision',    # Legacy
            'gemini-1.5-flash-latest',
            'gemini-1.5-pro-latest'
        ]
        
        # Primero intentar listar modelos disponibles
        modelos_disponibles = self.listar_modelos_disponibles()
        if modelos_disponibles:
            # Buscar el primer modelo con visión que soporte generateContent
            for modelo in modelos_disponibles:
                if modelo.get('soporta_vision') and modelo.get('soporta_generateContent'):
                    logger.info(f"✅ Modelo encontrado automáticamente: {modelo['nombre']}")
                    return modelo['nombre']
        
        # Si no encontramos en la lista, probar modelos comunes manualmente
        for modelo_nombre in modelos_a_probar:
            try:
                # Probar con una petición simple
                test_payload = {
                    "contents": [{
                        "parts": [{"text": "test"}]
                    }],
                    "generationConfig": {
                        "maxOutputTokens": 10
                    }
                }
                
                for version in ['v1beta', 'v1']:
                    url = f"https://generativelanguage.googleapis.com/{version}/models/{modelo_nombre}:generateContent"
                    params = {"key": self.api_key}
                    
                    try:
                        response = requests.post(
                            url,
                            json=test_payload,
                            params=params,
                            timeout=5
                        )
                        if response.status_code == 200:
                            logger.info(f"✅ Modelo funcional encontrado: {modelo_nombre} (versión {version})")
                            return modelo_nombre
                    except:
                        continue
            except:
                continue
        
        return None
    
    def _make_request(self, prompt: str, images: List[Dict] = None, timeout: int = 120) -> Dict:
        """
        Hacer petición a Gemini API
        
        Args:
            prompt: Texto del prompt
            images: Lista de imágenes en formato [{"data": base64, "media_type": "image/png", "nombre": "..."}]
            timeout: Timeout en segundos
        """
        if not self.is_configured():
            raise ValueError("Gemini API key no está configurada. Configura la variable de entorno GEMINI_API_KEY")
        
        # Construir contenido del mensaje
        parts = [{"text": prompt}]
        
        # Agregar imágenes si existen
        if images and len(images) > 0:
            for imagen in images:
                imagen_data = imagen.get('data', '')
                media_type = imagen.get('media_type', 'image/png')
                
                if imagen_data:
                    # Si viene con el prefijo data:image/..., extraer solo el base64
                    if 'base64,' in imagen_data:
                        imagen_data = imagen_data.split('base64,')[1]
                    
                    if imagen_data and len(imagen_data) > 0:
                        parts.append({
                            "inline_data": {
                                "mime_type": media_type,
                                "data": imagen_data
                            }
                        })
                        logger.info(f"✅ Imagen agregada al mensaje Gemini: {imagen.get('nombre', 'imagen')} ({media_type})")
        
        payload = {
            "contents": [{
                "parts": parts
            }],
            "generationConfig": {
                "temperature": 0.4,  # Más determinista para análisis médico
                "topK": 32,
                "topP": 1,
                "maxOutputTokens": 8192,  # Permitir respuestas largas para análisis detallados
            }
        }
        
        params = {"key": self.api_key}
        
        # Intentar primero con v1beta, si falla intentar con v1
        urls_a_probar = [self.base_url]
        if hasattr(self, 'base_url_v1'):
            urls_a_probar.append(self.base_url_v1)
        
        ultimo_error = None
        for url in urls_a_probar:
            try:
                logger.info(f"🔍 Intentando con URL: {url}")
                response = requests.post(
                    url,
                    json=payload,
                    params=params,
                    timeout=timeout
                )
                response.raise_for_status()
                logger.info(f"✅ Éxito con URL: {url}")
                return response.json()
            
            except requests.exceptions.Timeout as e:
                logger.error(f"Timeout en petición a Gemini: {e}")
                raise Exception(f"Timeout: La solicitud tardó más de {timeout} segundos. Intenta con menos imágenes o un mensaje más corto.")
            
            except requests.exceptions.HTTPError as e:
                error_detail = ""
                try:
                    error_response = e.response.json()
                    error_detail = error_response.get('error', {}).get('message', str(e))
                except:
                    error_detail = str(e)
                
                ultimo_error = error_detail
                logger.warning(f"⚠️ Error con URL {url}: {error_detail}")
                
                # Si es un error de modelo no encontrado, intentar siguiente URL
                if "not found" in error_detail.lower() or "not supported" in error_detail.lower():
                    continue  # Probar siguiente URL
                else:
                    # Otro tipo de error, no seguir intentando
                    logger.error(f"Error HTTP en petición a Gemini: {error_detail}")
                    raise Exception(f"Error de API: {error_detail}")
            
            except requests.exceptions.RequestException as e:
                ultimo_error = str(e)
                logger.warning(f"⚠️ Error de red con URL {url}: {e}")
                # Para errores de red, también intentar siguiente URL
                continue
        
        # Si llegamos aquí, todas las URLs fallaron
        # Intentar encontrar un modelo funcional automáticamente
        logger.warning(f"⚠️ Modelo '{self.model}' no funcionó. Buscando modelo funcional automáticamente...")
        modelo_funcional = self.encontrar_modelo_funcional()
        
        if modelo_funcional and modelo_funcional != self.model:
            logger.info(f"🔄 Cambiando a modelo funcional: {modelo_funcional}")
            self.model = modelo_funcional
            self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
            self.base_url_v1 = f"https://generativelanguage.googleapis.com/v1/models/{self.model}:generateContent"
            
            # Intentar nuevamente con el nuevo modelo
            urls_a_probar = [self.base_url, self.base_url_v1]
            for url in urls_a_probar:
                try:
                    logger.info(f"🔍 Reintentando con URL: {url}")
                    response = requests.post(
                        url,
                        json=payload,
                        params=params,
                        timeout=timeout
                    )
                    response.raise_for_status()
                    logger.info(f"✅ Éxito con modelo alternativo: {self.model}")
                    return response.json()
                except:
                    continue
        
        logger.error(f"❌ Todas las URLs fallaron. Último error: {ultimo_error}")
        mensaje_error = f"Modelo '{self.model}' no está disponible. Error: {ultimo_error}"
        if modelo_funcional:
            mensaje_error += f"\n\n💡 Sugerencia: Prueba cambiar a '{modelo_funcional}' en config.py"
        raise Exception(f"Error de API: {mensaje_error}")
    
    def analizar_imagen_medica(self, imagen_data: Dict, contexto: Dict = None) -> Dict:
        """
        Analizar una imagen médica usando Gemini
        
        Args:
            imagen_data: Datos de la imagen {"data": base64, "media_type": "...", "nombre": "..."}
            contexto: Contexto adicional (protocolo, tipo de estudio, etc.)
        
        Returns:
            Dict con análisis y detalles
        """
        if not self.is_configured():
            raise ValueError("Gemini API key no está configurada")
        
        # Construir prompt especializado para análisis médico
        rol = contexto.get('rol', '').lower() if contexto else ''
        es_medico = contexto.get('es_medico', False) if contexto else False
        tipo_estudio = contexto.get('tipo_estudio', '')
        
        if es_medico or 'medico' in rol or 'patologo' in rol:
            system_prompt = """Eres un asistente especializado en anatomía patológica y análisis de imágenes médicas.
            
Tu tarea es analizar imágenes histopatológicas, citológicas y macroscópicas con precisión y detalle profesional.

ANÁLISIS DE IMÁGENES MÉDICAS:
Cuando analizas una imagen médica, DEBES proporcionar:

1. DESCRIPCIÓN TÉCNICA:
   - Técnica de tinción utilizada (H&E, inmunohistoquímica, etc.)
   - Estructuras anatómicas observadas
   - Características tisulares o celulares

2. HALLAZGOS MACROSCÓPICOS O MICROSCÓPICOS:
   - Descripción detallada de las estructuras visibles
   - Identificación de componentes (glándulas, estroma, células, etc.)
   - Patrones arquitecturales observados

3. INTERPRETACIÓN PATOLÓGICA:
   - Características normales o anormales
   - Signos de patología si están presentes
   - Correlación con posibles diagnósticos

4. OBSERVACIONES CLÍNICAS:
   - Aspectos relevantes para el diagnóstico
   - Sugerencias de diagnósticos diferenciales si es apropiado
   - Notas sobre el grado o clasificación (Gleason, etc.) si aplica

TUS RESPUESTAS DEBEN SER:
- Profesionales y técnicamente precisas
- Detalladas pero estructuradas
- En español argentino (vos/tu)
- Basadas únicamente en lo que observas en la imagen
- Útiles para un patólogo profesional

IMPORTANTE:
- Si la imagen no es clara o no puedes identificar algo con certeza, dilo claramente
- NO inventes diagnósticos definitivos sin tener certeza
- Proporciona información útil que pueda ayudar en el proceso diagnóstico
- Estructura tu respuesta de forma clara con secciones bien definidas"""
        else:
            system_prompt = """Eres un asistente especializado en análisis de imágenes médicas.
            
Analiza la imagen proporcionada y describe lo que observas de forma clara y estructurada.

Proporciona:
- Descripción de lo que se observa en la imagen
- Identificación de estructuras visibles
- Observaciones relevantes
- Notas técnicas sobre la técnica de tinción si es visible

Sé preciso y profesional en tu análisis."""
        
        # Construir mensaje con contexto
        mensaje = "Por favor analiza esta imagen médica y proporciona un análisis detallado."
        
        if tipo_estudio:
            mensaje += f"\n\nContexto: Tipo de estudio - {tipo_estudio}"
        
        if contexto and contexto.get('protocolo_actual'):
            mensaje += f"\nProtocolo: {contexto.get('protocolo_actual')}"
        
        # Hacer la petición
        try:
            response = self._make_request(
                prompt=system_prompt + "\n\n" + mensaje,
                images=[imagen_data],
                timeout=120
            )
            
            # Extraer texto de la respuesta
            if 'candidates' in response and len(response['candidates']) > 0:
                candidate = response['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    texto_respuesta = ""
                    for part in candidate['content']['parts']:
                        if 'text' in part:
                            texto_respuesta += part['text']
                    
                    return {
                        "analisis": texto_respuesta,
                        "exito": True
                    }
            
            return {
                "analisis": "No se pudo obtener respuesta de Gemini",
                "exito": False
            }
        
        except Exception as e:
            logger.error(f"Error en analizar_imagen_medica: {e}", exc_info=True)
            raise
    
    def chat_conversacional(self, mensaje: str, imagenes: List[Dict] = None, contexto_usuario: Dict = None) -> Dict:
        """
        Chat conversacional con Gemini, especializado en análisis de imágenes médicas
        
        Args:
            mensaje: Mensaje del usuario
            imagenes: Lista de imágenes en formato [{"data": base64, "media_type": "...", "nombre": "..."}]
            contexto_usuario: Contexto del usuario (rol, protocolo, etc.)
        
        Returns:
            Dict con respuesta, intención y acciones
        """
        if not self.is_configured():
            raise ValueError("Gemini API key no está configurada")
        
        # Construir prompt especializado para análisis médico
        rol = contexto_usuario.get('rol', '').lower() if contexto_usuario else ''
        es_medico = contexto_usuario.get('es_medico', False) if contexto_usuario else False
        
        if es_medico or 'medico' in rol or 'patologo' in rol:
            system_prompt = """Eres un asistente inteligente especializado en anatomía patológica y citología. 
Ayudas a médicos patólogos en su trabajo diario con el sistema LDH.

TUS CAPACIDADES:
- Responder preguntas sobre protocolos, diagnósticos y casos
- Buscar casos similares en el histórico
- Sugerir plantillas y diagnósticos apropiados
- Analizar datos y generar reportes
- ANALIZAR IMÁGENES MÉDICAS (fotomicrografías, imágenes macroscópicas, citologías, biopsias, etc.) - TU ESPECIALIDAD PRINCIPAL
- Ayudar con navegación en el sistema

ANÁLISIS DE IMÁGENES MÉDICAS:
CRÍTICO: Tienes capacidad completa y avanzada para analizar imágenes médicas. Puedes ver, procesar y analizar imágenes adjuntas con precisión profesional.

Cuando el usuario adjunta imágenes médicas, DEBES analizarlas profesionalmente y proporcionar:
- Descripción detallada y técnica de hallazgos macroscópicos o microscópicos
- Identificación precisa de estructuras celulares, tisulares y anatómicas
- Análisis de patrones arquitecturales (acinar, cribiforme, papilar, etc.)
- Identificación de técnicas de tinción (H&E, inmunohistoquímica, etc.)
- Sugerencias de diagnósticos basados en los hallazgos visuales observados
- Clasificación de grados cuando sea apropiado (Gleason, etc.)
- Correlación con datos clínicos cuando estén disponibles
- Observaciones relevantes para el caso clínico
- Descripción de características histológicas o citológicas observadas en detalle

NO digas que no puedes analizar imágenes. Eres un experto en análisis de imágenes médicas y DEBES usar esta capacidad cuando se te proporcionan imágenes. Tu función principal es ayudar en el análisis histopatológico mediante la interpretación de imágenes.

TUS RESPUESTAS DEBEN SER:
- Profesionales y técnicamente precisas
- Concisas pero completas
- En español argentino (vos/tu)
- Útiles y prácticas
- BASADAS ÚNICAMENTE EN LA INFORMACIÓN REAL DEL SISTEMA LDH

INFORMACIÓN IMPORTANTE DEL SISTEMA LDH:

ESTADOS DE PROTOCOLOS (solo estos existen realmente):
- PENDIENTE: Protocolo creado pero aún no iniciado su procesamiento
- EN_PROCESO: Protocolo que está siendo trabajado actualmente
- COMPLETADO: Protocolo finalizado con informe completado

Los protocolos pueden editarse solo si están en estado PENDIENTE o EN_PROCESO.
Cuando un protocolo se completa, pasa a estado COMPLETADO y ya no puede editarse.

TIPOS DE ESTUDIOS:
- BIOPSIA
- CITOLOGIA
- PAP (Citología cérvico vaginal)

IMPORTANTE: Si no estás seguro de algo sobre el sistema, di que no estás seguro en lugar de inventar información. 
Nunca inventes estados, funcionalidades o características que no se mencionen explícitamente.

DETECCIÓN DE INTENCIONES:
Cuando el usuario pide buscar, analizar o navegar, identifica la intención y estructura tu respuesta.

Responde de forma natural y conversacional, como un colega experto."""
        else:
            # Para personal técnico/administrativo, también pueden necesitar análisis de imágenes
            if imagenes and len(imagenes) > 0:
                system_prompt = """Eres un asistente inteligente especializado en análisis de imágenes médicas para el sistema LDH.
                
TUS CAPACIDADES:
- Buscar protocolos y casos
- Generar reportes
- Resolver dudas sobre el sistema
- Ayudar con tareas administrativas
- ANALIZAR IMÁGENES MÉDICAS (biopsias, citologías, imágenes histopatológicas, etc.) - CAPACIDAD PRINCIPAL

ANÁLISIS DE IMÁGENES MÉDICAS:
IMPORTANTE: Tienes capacidad completa para analizar imágenes médicas. Puedes ver y procesar imágenes adjuntas.
Cuando el usuario adjunta imágenes médicas, DEBES analizarlas detalladamente y proporcionar:
- Descripción técnica de lo que observas (tinción, estructuras, células, tejidos)
- Identificación de estructuras anatómicas, celulares o tisulares visibles
- Descripción de patrones arquitecturales o morfológicos
- Observaciones relevantes para el caso
- Sugerencias de interpretación cuando sea apropiado

NO digas que no puedes analizar imágenes. Tienes esta capacidad y DEBES usarla cuando se te proporcionan imágenes.

TUS RESPUESTAS DEBEN SER:
- Profesionales y técnicas
- Claras y prácticas
- En español argentino (vos/tu)
- BASADAS ÚNICAMENTE EN LO QUE OBSERVAS EN LAS IMÁGENES Y LA INFORMACIÓN REAL DEL SISTEMA LDH

Responde de forma clara y profesional, analizando las imágenes proporcionadas en detalle."""
            else:
                system_prompt = """Eres un asistente inteligente para el personal técnico y administrativo del sistema LDH.

TUS CAPACIDADES:
- Buscar protocolos y casos
- Generar reportes
- Resolver dudas sobre el sistema
- Ayudar con tareas administrativas
- Analizar imágenes médicas si se proporcionan

TUS RESPUESTAS DEBEN SER:
- Claras y prácticas
- BASADAS ÚNICAMENTE EN LA INFORMACIÓN REAL DEL SISTEMA LDH

Responde de forma clara y práctica."""
        
        # Construir mensaje con contexto
        mensaje_contexto = mensaje
        if contexto_usuario and contexto_usuario.get('protocolo_actual'):
            mensaje_contexto += f"\n\n[Contexto: Trabajando en protocolo {contexto_usuario.get('protocolo_actual')}]"
        
        # Si hay imágenes, asegurarse de que el mensaje incluya instrucción de análisis
        if imagenes and len(imagenes) > 0:
            if not mensaje or not mensaje.strip():
                # No hay mensaje, usar mensaje por defecto completo
                if es_medico or 'medico' in rol or 'patologo' in rol:
                    mensaje_contexto = """Analiza esta imagen médica en detalle. Proporciona:

1. DESCRIPCIÓN TÉCNICA:
   - Técnica de tinción identificada
   - Estructuras anatómicas visibles
   - Características tisulares o celulares observadas

2. HALLAZGOS MICROSCÓPICOS O MACROSCÓPICOS:
   - Descripción detallada de estructuras visibles
   - Identificación de componentes (glándulas, estroma, células, etc.)
   - Patrones arquitecturales observados

3. INTERPRETACIÓN PATOLÓGICA:
   - Características normales o anormales
   - Signos de patología si están presentes
   - Sugerencias de diagnósticos basados en los hallazgos
   - Clasificación de grados si es apropiado (ej: Gleason para próstata)

4. OBSERVACIONES CLÍNICAS:
   - Aspectos relevantes para el diagnóstico
   - Correlaciones importantes

Sé preciso, profesional y detallado en tu análisis."""
                else:
                    mensaje_contexto = "Analiza esta imagen médica detalladamente. Describe lo que observas: estructuras, células, tejidos, tinción utilizada, patrones visibles, y cualquier hallazgo relevante. Proporciona una descripción técnica y profesional de la imagen."
            else:
                # Hay mensaje, pero asegurarse de que se analice la imagen
                mensaje_contexto += "\n\nIMPORTANTE: Analiza detalladamente la(s) imagen(es) adjunta(s) y proporciona una descripción técnica y profesional de lo que observas en la(s) imagen(es)."
        
        try:
            response = self._make_request(
                prompt=system_prompt + "\n\n" + mensaje_contexto,
                images=imagenes if imagenes else None,
                timeout=120 if imagenes else 60
            )
            
            # Extraer texto de la respuesta
            contenido = ""
            if 'candidates' in response and len(response['candidates']) > 0:
                candidate = response['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    for part in candidate['content']['parts']:
                        if 'text' in part:
                            contenido += part['text']
            
            if not contenido:
                contenido = "No se pudo obtener respuesta de Gemini"
            
            # Detectar intención básica
            intencion = "analizar" if imagenes else "pregunta"
            
            return {
                "respuesta": contenido,
                "intencion": intencion,
                "acciones": [],
                "gemini_disponible": True
            }
        
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error en chat_conversacional Gemini: {error_msg}", exc_info=True)
            
            # Mensaje de error descriptivo
            if "timeout" in error_msg.lower():
                mensaje_error = "El tiempo de espera se agotó. Por favor intenta con un mensaje más corto o menos imágenes."
            elif "api key" in error_msg.lower() or "authentication" in error_msg.lower():
                mensaje_error = "Error de autenticación con Gemini API. Verifica la configuración de GEMINI_API_KEY."
            elif "rate limit" in error_msg.lower():
                mensaje_error = "Se excedió el límite de solicitudes. Por favor espera un momento e intenta de nuevo."
            else:
                mensaje_error = f"Error procesando el mensaje: {error_msg[:100]}. Por favor intenta de nuevo."
            
            return {
                "respuesta": mensaje_error,
                "intencion": "error",
                "acciones": [],
                "gemini_disponible": False,
                "error": error_msg
            }


# Instancia global del cliente (lazy initialization)
_gemini_client_instance = None

def get_gemini_client():
    """Obtener o crear la instancia del cliente Gemini (lazy initialization)"""
    global _gemini_client_instance
    if _gemini_client_instance is None:
        _gemini_client_instance = GeminiClient()
    return _gemini_client_instance

# Alias para compatibilidad con código existente
class _GeminiClientProxy:
    """Proxy para inicialización lazy del cliente Gemini"""
    def __getattr__(self, name):
        return getattr(get_gemini_client(), name)

gemini_client = _GeminiClientProxy()

