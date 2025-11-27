#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Cliente para integración con Claude API
"""

import os
import json
import requests
import base64
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

# Importar herramientas de base de datos
try:
    from services.asistente_db_tools import TOOLS, ejecutar_funcion
    TOOLS_DISPONIBLES = True
except ImportError as e:
    logger.warning(f"⚠️ No se pudieron importar las herramientas de base de datos: {e}")
    TOOLS_DISPONIBLES = False
    TOOLS = []
    ejecutar_funcion = None

class ClaudeClient:
    """Cliente para interactuar con Claude API"""
    
    def __init__(self, modelo=None):
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        self.base_url = "https://api.anthropic.com/v1/messages"
        # Modelo que soporta visión para análisis de imágenes médicas
        # Modelos válidos que soportan visión:
        # - claude-3-opus-20240229 (más potente, más costoso)
        # - claude-3-sonnet-20240229 (balanceado, recomendado)
        # - claude-3-haiku-20240307 (más rápido, más económico, pero NO soporta visión)
        # El modelo puede cambiarse:
        # 1. Variable de entorno CLAUDE_MODEL
        # 2. Configuración en config.py (CLAUDE_MODEL)
        # 3. Parámetro al inicializar ClaudeClient
        try:
            from flask import current_app
            modelo_config = current_app.config.get('CLAUDE_MODEL')
        except:
            modelo_config = None
        
        if modelo:
            self.model = modelo
        elif modelo_config:
            self.model = modelo_config
        else:
            self.model = os.getenv('CLAUDE_MODEL', "claude-3-haiku-20240307")  # Por defecto usar haiku
        
        self.headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
        
        # Validar que la API key esté correctamente formateada
        if self.api_key and not self.api_key.startswith('sk-ant-'):
            logger.warning("⚠️ La API key de Claude no parece tener el formato correcto (debería empezar con 'sk-ant-')")
        
        # Log del modelo seleccionado
        modelo_origen = "parámetro" if modelo else ("config.py" if modelo_config else "variable de entorno o default")
        logger.info(f"🤖 ClaudeClient inicializado - Modelo: {self.model} (origen: {modelo_origen})")
        if 'haiku' in self.model.lower():
            logger.warning("⚠️ El modelo Haiku NO soporta análisis de imágenes. Usa claude-3-opus o claude-3-sonnet para visión.")
    
    def is_configured(self) -> bool:
        """Verificar si la API key está configurada"""
        return bool(self.api_key and self.api_key.startswith('sk-ant-'))
    
    def probar_modelo(self, modelo=None, timeout=10) -> Dict[str, Any]:
        """
        Probar si un modelo está disponible con una petición simple
        
        Args:
            modelo: Nombre del modelo a probar (si None, usa self.model)
            timeout: Timeout para la prueba
            
        Returns:
            Dict con 'disponible' (bool) y 'error' (str o None)
        """
        modelo_a_probar = modelo or self.model
        
        if not self.is_configured():
            return {
                'disponible': False,
                'error': 'API key no configurada',
                'modelo': modelo_a_probar
            }
        
        try:
            # Petición simple de prueba
            test_payload = {
                "model": modelo_a_probar,
                "max_tokens": 10,
                "messages": [{"role": "user", "content": "Hola"}]
            }
            
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=test_payload,
                timeout=timeout
            )
            
            if response.status_code == 200:
                return {
                    'disponible': True,
                    'error': None,
                    'modelo': modelo_a_probar
                }
            else:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get('error', {}).get('message', f'HTTP {response.status_code}')
                return {
                    'disponible': False,
                    'error': error_msg,
                    'modelo': modelo_a_probar
                }
        except Exception as e:
            return {
                'disponible': False,
                'error': str(e),
                'modelo': modelo_a_probar
            }
    
    def _make_request(self, messages: List[Dict], max_tokens: int = 1000, system: str = None, timeout: int = 60, tools: List[Dict] = None) -> Dict:
        """Hacer petición a Claude API"""
        if not self.is_configured():
            raise ValueError("Claude API key no está configurada")
        
        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": messages
        }
        
        if system:
            payload["system"] = system
        
        # Agregar tools si están disponibles
        if tools and len(tools) > 0:
            payload["tools"] = tools
        
        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload,
                timeout=timeout
            )
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout en petición a Claude: {e}")
            raise Exception(f"Timeout: La solicitud tardó más de {timeout} segundos. Intenta con menos imágenes o un mensaje más corto.")
        except requests.exceptions.HTTPError as e:
            error_detail = ""
            error_type = ""
            error_code = None
            try:
                error_response = e.response.json()
                error_detail = error_response.get('error', {}).get('message', str(e))
                error_type = error_response.get('error', {}).get('type', '')
                # Extraer código de estado si está disponible
                if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                    error_code = e.response.status_code
            except:
                error_detail = str(e)
                if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                    error_code = e.response.status_code
            
            logger.error(f"Error HTTP en petición a Claude: {error_detail} (tipo: {error_type}, código: {error_code})")
            
            # Si el modelo no está disponible, intentar sugerir alternativas
            if error_code == 400 or error_code == 404:
                if "model" in error_detail.lower() or error_type == "invalid_request_error":
                    raise ValueError(f"model: {self.model} - {error_detail}")
            
            raise Exception(f"Error de API: {error_detail}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error en petición a Claude: {e}")
            raise Exception(f"Error comunicándose con Claude: {str(e)}")
    
    def sugerir_plantillas_pap(self, contexto: Dict) -> Dict:
        """Sugerir plantillas PAP basadas en contexto"""
        
        system_prompt = """Eres un asistente especializado en citología cervicovaginal (PAP). 
        Tu trabajo es sugerir plantillas apropiadas basadas en el contexto del caso.
        
        Las categorías de plantillas son:
        - T (Trófoco): Para extendidos normales y bien representativos
        - H (Hipotrófoco): Para conformación celular y células adicionales
        - A (Atrófico): Para componente inflamatorio y flora
        - I (Inflamatorio): Para diagnósticos
        
        Responde en formato JSON con:
        {
            "sugerencias": [
                {
                    "categoria": "T",
                    "codigo": "T1",
                    "razon": "Explicación de por qué esta plantilla es apropiada"
                }
            ],
            "confianza": 0.85,
            "observaciones": "Notas adicionales sobre el caso"
        }"""
        
        user_prompt = f"""Analiza este contexto de PAP y sugiere plantillas apropiadas:
        
        Datos clínicos: {contexto.get('datos_clinicos', 'No especificados')}
        Edad: {contexto.get('edad', 'No especificada')}
        Antecedentes: {contexto.get('antecedentes', 'No especificados')}
        Sección actual: {contexto.get('seccion_actual', 'No especificada')}
        
        Plantillas ya seleccionadas: {contexto.get('plantillas_seleccionadas', [])}
        
        Sugiere las plantillas más apropiadas para este caso."""
        
        messages = [{"role": "user", "content": user_prompt}]
        
        try:
            response = self._make_request(messages, max_tokens=500, system=system_prompt)
            content = response.get('content', [{}])[0].get('text', '{}')
            
            # Intentar parsear JSON
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # Si no es JSON válido, crear respuesta estructurada
                return {
                    "sugerencias": [],
                    "confianza": 0.5,
                    "observaciones": content,
                    "error": "Respuesta no estructurada"
                }
        
        except Exception as e:
            logger.error(f"Error en sugerir_plantillas_pap: {e}")
            return {
                "sugerencias": [],
                "confianza": 0.0,
                "observaciones": f"Error: {str(e)}",
                "error": str(e)
            }
    
    def analizar_caso_completo(self, datos_caso: Dict) -> Dict:
        """Analizar un caso completo y sugerir enfoque"""
        
        system_prompt = """Eres un patólogo experto en citología. Analiza casos de PAP y proporciona 
        recomendaciones profesionales basadas en los datos clínicos y hallazgos.
        
        Responde en formato JSON con:
        {
            "diagnostico_sugerido": "Diagnóstico más probable",
            "plantillas_recomendadas": ["T1", "A2", "I3"],
            "nivel_complejidad": "simple|moderado|complejo",
            "observaciones": "Análisis detallado del caso",
            "recomendaciones": ["Recomendación 1", "Recomendación 2"]
        }"""
        
        user_prompt = f"""Analiza este caso completo de PAP:
        
        Paciente: {datos_caso.get('paciente', 'No especificado')}
        Edad: {datos_caso.get('edad', 'No especificada')}
        Datos clínicos: {datos_caso.get('datos_clinicos', 'No especificados')}
        Antecedentes: {datos_caso.get('antecedentes', 'No especificados')}
        Hallazgos: {datos_caso.get('hallazgos', 'No especificados')}
        
        Proporciona un análisis completo y recomendaciones."""
        
        messages = [{"role": "user", "content": user_prompt}]
        
        try:
            response = self._make_request(messages, max_tokens=800, system=system_prompt)
            content = response.get('content', [{}])[0].get('text', '{}')
            
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return {
                    "diagnostico_sugerido": "Análisis no disponible",
                    "plantillas_recomendadas": [],
                    "nivel_complejidad": "moderado",
                    "observaciones": content,
                    "recomendaciones": [],
                    "error": "Respuesta no estructurada"
                }
        
        except Exception as e:
            logger.error(f"Error en analizar_caso_completo: {e}")
            return {
                "diagnostico_sugerido": "Error en análisis",
                "plantillas_recomendadas": [],
                "nivel_complejidad": "moderado",
                "observaciones": f"Error: {str(e)}",
                "recomendaciones": [],
                "error": str(e)
            }
    
    def generar_informe(self, plantillas_seleccionadas: List[Dict], contexto: Dict) -> str:
        """Generar informe basado en plantillas seleccionadas"""
        
        system_prompt = """Eres un patólogo experto. Genera informes de PAP profesionales 
        basados en las plantillas seleccionadas y el contexto del caso.
        
        El informe debe ser:
        - Profesional y técnicamente correcto
        - Bien estructurado por secciones
        - Coherente y fluido
        - Apropiado para el contexto clínico"""
        
        plantillas_texto = "\n".join([
            f"- {p.get('codigo', 'N/A')}: {p.get('texto', '')}"
            for p in plantillas_seleccionadas
        ])
        
        user_prompt = f"""Genera un informe de PAP basado en estas plantillas y contexto:
        
        PLANTILLAS SELECCIONADAS:
        {plantillas_texto}
        
        CONTEXTO:
        Paciente: {contexto.get('paciente', 'No especificado')}
        Edad: {contexto.get('edad', 'No especificada')}
        Datos clínicos: {contexto.get('datos_clinicos', 'No especificados')}
        
        Genera un informe completo y profesional."""
        
        messages = [{"role": "user", "content": user_prompt}]
        
        try:
            response = self._make_request(messages, max_tokens=1000, system=system_prompt)
            content = response.get('content', [{}])[0].get('text', '')
            return content
        
        except Exception as e:
            logger.error(f"Error en generar_informe: {e}")
            return f"Error generando informe: {str(e)}"
    
    def buscar_casos_similares(self, criterios: Dict) -> Dict:
        """Buscar casos similares basados en criterios"""
        
        system_prompt = """Eres un asistente que ayuda a encontrar casos similares en citología.
        Basándote en los criterios proporcionados, sugiere plantillas que podrían ser apropiadas
        para casos similares."""
        
        user_prompt = f"""Busca casos similares basados en estos criterios:
        
        Edad: {criterios.get('edad', 'No especificada')}
        Síntomas: {criterios.get('sintomas', 'No especificados')}
        Antecedentes: {criterios.get('antecedentes', 'No especificados')}
        Hallazgos: {criterios.get('hallazgos', 'No especificados')}
        
        Sugiere plantillas que podrían ser apropiadas para casos similares."""
        
        messages = [{"role": "user", "content": user_prompt}]
        
        try:
            response = self._make_request(messages, max_tokens=400, system=system_prompt)
            content = response.get('content', [{}])[0].get('text', '')
            
            return {
                "casos_similares": content,
                "plantillas_sugeridas": [],
                "confianza": 0.7
            }
        
        except Exception as e:
            logger.error(f"Error en buscar_casos_similares: {e}")
            return {
                "casos_similares": f"Error: {str(e)}",
                "plantillas_sugeridas": [],
                "confianza": 0.0
            }
    
    def chat_conversacional(self, mensaje: str, historial: List[Dict] = None, contexto_usuario: Dict = None, imagenes: List[Dict] = None) -> Dict:
        """
        Chat conversacional con Claude API para usuarios internos
        
        Args:
            mensaje: Mensaje del usuario
            historial: Lista de mensajes anteriores en formato [{"role": "user|assistant", "content": "..."}]
            contexto_usuario: Información del usuario (rol, permisos, etc.)
            imagenes: Lista de imágenes en formato [{"data": "base64", "media_type": "image/png", "nombre": "..."}]
        
        Returns:
            Dict con respuesta y acciones opcionales
        """
        if not self.is_configured():
            raise ValueError("Claude API key no está configurada")
        
        # Construir prompt del sistema según el rol del usuario
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
            - Analizar imágenes médicas (fotomicrografías, imágenes macroscópicas, citologías, etc.)
            - Ayudar con navegación en el sistema
            
            ANÁLISIS DE IMÁGENES MÉDICAS:
            IMPORTANTE: Tienes capacidad completa para analizar imágenes médicas. Puedes ver y procesar imágenes adjuntas.
            Cuando el usuario adjunta imágenes médicas, DEBES analizarlas y proporcionar:
            - Descripción detallada de hallazgos macroscópicos o microscópicos
            - Identificación de estructuras celulares o tisulares
            - Sugerencias de diagnósticos basadas en los hallazgos visuales
            - Correlación con datos clínicos cuando estén disponibles
            - Observaciones relevantes para el caso
            - Descripción de características histológicas o citológicas observadas
            
            NO digas que no puedes analizar imágenes. Si el usuario adjunta una imagen, es porque espera que la analices.
            
            TUS RESPUESTAS DEBEN SER:
            - Profesionales y técnicamente precisas
            - Concisas pero completas
            - En español argentino (vos/tu)
            - Útiles y prácticas
            - BASADAS ÚNICAMENTE EN LA INFORMACIÓN REAL DEL SISTEMA LDH
            
            CONSULTAS A LA BASE DE DATOS:
            Tienes acceso a herramientas que te permiten consultar datos reales del sistema. Cuando el usuario pregunte sobre:
            - Prestadores con más pacientes
            - Pacientes con múltiples protocolos
            - Estadísticas de protocolos
            - Cualquier dato estadístico o de consulta
            
            DEBES usar las herramientas disponibles en lugar de decir que no tienes acceso a los datos.
            Siempre usa las herramientas cuando el usuario pregunte por información estadística o datos específicos del sistema.
            
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
        
        elif 'administrador' in rol or 'admin' in rol:
            system_prompt = """Eres un asistente inteligente para administradores del sistema LDH.
            
            TUS CAPACIDADES:
            - Analizar estadísticas y reportes
            - Gestionar usuarios y permisos
            - Generar reportes administrativos
            - Ayudar con configuración del sistema
            
            TUS RESPUESTAS DEBEN SER:
            - Profesionales y enfocadas en gestión
            - BASADAS ÚNICAMENTE EN LA INFORMACIÓN REAL DEL SISTEMA LDH
            
            CONSULTAS A LA BASE DE DATOS:
            Tienes acceso a herramientas que te permiten consultar datos reales del sistema. Cuando el usuario pregunte sobre:
            - Prestadores con más pacientes
            - Pacientes con múltiples protocolos
            - Estadísticas de protocolos
            - Cualquier dato estadístico o de consulta
            
            DEBES usar las herramientas disponibles en lugar de decir que no tienes acceso a los datos.
            Siempre usa las herramientas cuando el usuario pregunte por información estadística o datos específicos del sistema.
            
            INFORMACIÓN IMPORTANTE DEL SISTEMA LDH:
            
            ESTADOS DE PROTOCOLOS (solo estos existen realmente):
            - PENDIENTE: Protocolo creado pero aún no iniciado su procesamiento
            - EN_PROCESO: Protocolo que está siendo trabajado actualmente
            - COMPLETADO: Protocolo finalizado con informe completado
            
            IMPORTANTE: Si no estás seguro de algo sobre el sistema, di que no estás seguro en lugar de inventar información. 
            Nunca inventes estados, funcionalidades o características que no se mencionen explícitamente.
            
            Responde de forma profesional y enfocada en gestión."""
        
        else:
            # Para técnicos, secretarias, etc.
            system_prompt = """Eres un asistente inteligente para el personal técnico y administrativo del sistema LDH.
            
            TUS CAPACIDADES:
            - Buscar protocolos y casos
            - Generar reportes
            - Resolver dudas sobre el sistema
            - Ayudar con tareas administrativas
            
            TUS RESPUESTAS DEBEN SER:
            - Claras y prácticas
            - BASADAS ÚNICAMENTE EN LA INFORMACIÓN REAL DEL SISTEMA LDH
            
            CONSULTAS A LA BASE DE DATOS:
            Tienes acceso a herramientas que te permiten consultar datos reales del sistema. Cuando el usuario pregunte sobre:
            - Prestadores con más pacientes
            - Pacientes con múltiples protocolos
            - Estadísticas de protocolos
            - Cualquier dato estadístico o de consulta
            
            DEBES usar las herramientas disponibles en lugar de decir que no tienes acceso a los datos.
            Siempre usa las herramientas cuando el usuario pregunte por información estadística o datos específicos del sistema.
            
            INFORMACIÓN IMPORTANTE DEL SISTEMA LDH:
            
            ESTADOS DE PROTOCOLOS (solo estos existen realmente):
            - PENDIENTE: Protocolo creado pero aún no iniciado su procesamiento
            - EN_PROCESO: Protocolo que está siendo trabajado actualmente
            - COMPLETADO: Protocolo finalizado con informe completado
            
            IMPORTANTE: Si no estás seguro de algo sobre el sistema, di que no estás seguro en lugar de inventar información. 
            Nunca inventes estados, funcionalidades o características que no se mencionen explícitamente.
            
            Responde de forma clara y práctica."""
        
        # Construir historial de mensajes
        messages = []
        
        # Agregar historial si existe
        if historial:
            messages.extend(historial)
        
        # Agregar mensaje actual con imágenes si existen
        mensaje_contexto = f"{mensaje}"
        if contexto_usuario and contexto_usuario.get('protocolo_actual'):
            mensaje_contexto += f"\n\n[Contexto: Trabajando en protocolo {contexto_usuario.get('protocolo_actual')}]"
        
        # Construir contenido del mensaje
        # Si hay imágenes, usar formato array. Si solo hay texto, usar string directamente
        if imagenes and len(imagenes) > 0:
            # Verificar que el modelo soporte visión
            if 'haiku' in self.model.lower():
                logger.warning(f"⚠️ El modelo {self.model} no soporta visión. Las imágenes serán ignoradas.")
                messages.append({
                    "role": "user",
                    "content": mensaje_contexto + "\n\n[Nota: Este modelo no soporta análisis de imágenes. Se requiere claude-3-opus o claude-3-sonnet.]"
                })
            else:
                # Agregar instrucción explícita para analizar imágenes si no hay mensaje de texto
                if not mensaje or mensaje.strip() == '':
                    mensaje_contexto = "Por favor analiza esta imagen médica y proporciona una descripción detallada de los hallazgos, identificación de estructuras, y sugerencias de diagnóstico si es posible."
                
                contenido_mensaje = [{"type": "text", "text": mensaje_contexto}]
                
                # Agregar imágenes
                imagenes_agregadas = 0
                for imagen in imagenes:
                    imagen_data = imagen.get('data', '')
                    media_type = imagen.get('media_type', 'image/png')
                    nombre = imagen.get('nombre', 'imagen')
                    
                    # Validar que la imagen tenga datos
                    if imagen_data:
                        # Si viene con el prefijo data:image/..., extraer solo el base64
                        if 'base64,' in imagen_data:
                            imagen_data = imagen_data.split('base64,')[1]
                        
                        # Validar que el base64 no esté vacío
                        if imagen_data and len(imagen_data) > 0:
                            contenido_mensaje.append({
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": imagen_data
                                }
                            })
                            imagenes_agregadas += 1
                            logger.info(f"✅ Imagen agregada al mensaje: {nombre} ({media_type}), tamaño base64: {len(imagen_data)} caracteres")
                        else:
                            logger.warning(f"⚠️ Imagen {nombre} no tiene datos base64 válidos")
                
                if imagenes_agregadas == 0:
                    logger.error("❌ No se pudieron agregar imágenes válidas al mensaje")
                    # Enviar solo texto con advertencia
                    messages.append({
                        "role": "user",
                        "content": mensaje_contexto + "\n\n[Error: Las imágenes proporcionadas no pudieron ser procesadas correctamente.]"
                    })
                else:
                    logger.info(f"📤 Enviando mensaje con {imagenes_agregadas} imagen(es) usando modelo {self.model}")
                    messages.append({
                        "role": "user",
                        "content": contenido_mensaje
                    })
        else:
            # Sin imágenes: usar string directamente
            messages.append({
                "role": "user",
                "content": mensaje_contexto
            })
        
        try:
            # Aumentar max_tokens y timeout si hay imágenes (análisis puede generar respuestas más largas)
            tiene_imagenes = imagenes and len(imagenes) > 0 and not ('haiku' in self.model.lower())
            max_tokens = 4000 if tiene_imagenes else 2000
            timeout = 120 if tiene_imagenes else 60  # Más tiempo para procesar imágenes
            
            # Log del modelo y contenido que se envía
            logger.info(f"🔍 Modelo utilizado: {self.model}")
            if tiene_imagenes:
                logger.info(f"📸 Enviando {len(imagenes)} imagen(es) con {len(messages)} mensaje(s) en el historial")
                # Log del primer mensaje para debug (sin datos de imagen completos)
                if messages and len(messages) > 0:
                    ultimo_msg = messages[-1]
                    if isinstance(ultimo_msg.get('content'), list):
                        logger.info(f"📋 Formato del mensaje: array con {len(ultimo_msg['content'])} elemento(s)")
                        for i, elem in enumerate(ultimo_msg['content']):
                            if elem.get('type') == 'text':
                                logger.info(f"  [{i}] Texto: {elem.get('text', '')[:100]}...")
                            elif elem.get('type') == 'image':
                                logger.info(f"  [{i}] Imagen: {elem.get('source', {}).get('media_type', 'unknown')}")
            
            # Preparar tools si están disponibles
            tools_a_usar = []
            if TOOLS_DISPONIBLES and TOOLS:
                tools_a_usar = TOOLS
            
            # Iterar hasta obtener respuesta final (manejando tool calls)
            max_iteraciones = 5  # Máximo de iteraciones para evitar loops infinitos
            iteracion = 0
            contenido_final = ""
            
            while iteracion < max_iteraciones:
                response = self._make_request(
                    messages=messages,
                    max_tokens=max_tokens,
                    system=system_prompt,
                    timeout=timeout,
                    tools=tools_a_usar if iteracion == 0 else None  # Solo enviar tools en primera iteración
                )
                
                # Verificar si Claude quiere usar una herramienta
                content_items = response.get('content', [])
                stop_reason = response.get('stop_reason', '')
                
                if stop_reason == 'tool_use' and content_items:
                    # Claude quiere usar una herramienta
                    tool_use_item = None
                    text_content = ""
                    
                    for item in content_items:
                        if item.get('type') == 'tool_use':
                            tool_use_item = item
                        elif item.get('type') == 'text':
                            text_content += item.get('text', '')
                    
                    if tool_use_item:
                        tool_name = tool_use_item.get('name')
                        tool_input = tool_use_item.get('input', {})
                        tool_id = tool_use_item.get('id')
                        
                        logger.info(f"🔧 Claude quiere usar herramienta: {tool_name} con input: {tool_input}")
                        
                        # Ejecutar la función
                        if ejecutar_funcion:
                            resultado = ejecutar_funcion(tool_name, tool_input)
                            
                            # Agregar mensaje del asistente con tool_use
                            messages.append({
                                "role": "assistant",
                                "content": content_items
                            })
                            
                            # Convertir resultado a JSON string para que Claude pueda procesarlo
                            import json
                            try:
                                resultado_json = json.dumps(resultado, ensure_ascii=False, indent=2, default=str)
                            except Exception as e:
                                logger.warning(f"⚠️ Error serializando resultado a JSON: {e}, usando str()")
                                resultado_json = str(resultado)
                            
                            # Agregar resultado de la herramienta
                            messages.append({
                                "role": "user",
                                "content": [{
                                    "type": "tool_result",
                                    "tool_use_id": tool_id,
                                    "content": resultado_json
                                }]
                            })
                            
                            iteracion += 1
                            continue  # Continuar loop para obtener respuesta final de Claude
                        else:
                            logger.error("⚠️ ejecutar_funcion no está disponible")
                    
                # Si llegamos aquí, Claude no quiere usar herramientas o ya terminó
                # Extraer texto de la respuesta
                for item in content_items:
                    if item.get('type') == 'text':
                        contenido_final += item.get('text', '')
                
                if contenido_final:
                    break  # Tenemos respuesta final
                
                iteracion += 1
            
            # Si no hay contenido final después de todas las iteraciones, usar último contenido
            if not contenido_final:
                contenido_final = "No se pudo obtener una respuesta válida."
                logger.warning("⚠️ No se obtuvo contenido final después de todas las iteraciones")
            
            # Detectar intenciones en el mensaje del usuario
            intencion = self._detectar_intencion(mensaje, contenido_final)
            
            return {
                "respuesta": contenido_final,
                "intencion": intencion,
                "acciones": self._extraer_acciones(mensaje, contenido_final, intencion),
                "claude_disponible": True
            }
        
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error en chat_conversacional: {error_msg}", exc_info=True)
            
            # Mensaje de error más descriptivo para el usuario
            if "timeout" in error_msg.lower():
                mensaje_error = "El tiempo de espera se agotó. Por favor intenta con un mensaje más corto o menos imágenes."
            elif "api key" in error_msg.lower() or "authentication" in error_msg.lower():
                mensaje_error = "Error de autenticación con Claude API. Por favor contacta al administrador."
            elif "rate limit" in error_msg.lower():
                mensaje_error = "Se excedió el límite de solicitudes. Por favor espera un momento e intenta de nuevo."
            elif "invalid" in error_msg.lower() or "format" in error_msg.lower():
                mensaje_error = "Error en el formato de la solicitud. Por favor verifica las imágenes adjuntas."
            elif "model:" in error_msg.lower() or "model" in error_msg.lower():
                # Error específico de modelo no disponible
                modelo_actual = self.model
                if "opus" in modelo_actual.lower():
                    sugerencia = "\n\n💡 Solución: El modelo Claude Opus requiere un plan Pro de Anthropic.\n   • Cambia a 'claude-3-sonnet-20240229' en config.py (soporta visión)\n   • O usa 'claude-3-haiku-20240307' (solo texto, siempre disponible)"
                elif "sonnet" in modelo_actual.lower():
                    sugerencia = "\n\n💡 Solución: El modelo Sonnet puede requerir un plan específico.\n   • Intenta con 'claude-3-haiku-20240307' en config.py (siempre disponible)\n   • O verifica tu plan de Anthropic en https://console.anthropic.com/"
                elif "haiku" in modelo_actual.lower():
                    sugerencia = "\n\n💡 Solución: Haiku debería estar siempre disponible. Verifica:\n   • Tu API key es correcta (debe empezar con 'sk-ant-')\n   • Tienes créditos disponibles en tu cuenta\n   • La conexión a internet funciona correctamente"
                else:
                    sugerencia = "\n\n💡 Solución: Verifica que el modelo esté disponible en tu plan.\n   • Prueba con 'claude-3-haiku-20240307' primero (siempre disponible)\n   • Revisa tu plan en https://console.anthropic.com/"
                mensaje_error = f"❌ El modelo '{modelo_actual}' no está disponible o no tienes acceso a él.{sugerencia}\n\n🔧 Para cambiar el modelo, edita config.py línea 54 y reinicia el servidor."
            else:
                mensaje_error = f"Error procesando el mensaje: {error_msg[:100]}. Por favor intenta de nuevo."
            
            return {
                "respuesta": mensaje_error,
                "intencion": "error",
                "acciones": [],
                "claude_disponible": False,
                "error": error_msg,
                "modelo": self.model
            }
    
    def _detectar_intencion(self, mensaje: str, respuesta: str) -> str:
        """Detectar la intención principal del usuario"""
        mensaje_lower = mensaje.lower()
        
        # Patrones de intención
        if any(palabra in mensaje_lower for palabra in ['buscar', 'busca', 'encontrar', 'muéstrame', 'muestra', 'mostrar']):
            return "buscar"
        elif any(palabra in mensaje_lower for palabra in ['analizar', 'análisis', 'analiza', 'resumen', 'estadística']):
            return "analizar"
        elif any(palabra in mensaje_lower for palabra in ['abrir', 'ir a', 'navegar', 'mostrar protocolo']):
            return "navegar"
        elif any(palabra in mensaje_lower for palabra in ['diagnóstico', 'diagnostico', 'sugerir', 'plantilla']):
            return "diagnostico"
        elif any(palabra in mensaje_lower for palabra in ['reporte', 'informe', 'generar', 'exportar']):
            return "reporte"
        else:
            return "pregunta"
    
    def _extraer_acciones(self, mensaje: str, respuesta: str, intencion: str) -> List[Dict]:
        """Extraer acciones sugeridas de la respuesta"""
        acciones = []
        
        # Detectar números de protocolo
        import re
        protocolos = re.findall(r'protocolo\s*(\d+)', mensaje.lower())
        if protocolos:
            acciones.append({
                "tipo": "navegar",
                "accion": "abrir_protocolo",
                "protocolo_id": protocolos[0],
                "texto": f"Abrir protocolo {protocolos[0]}"
            })
        
        # Detectar búsquedas sugeridas
        if intencion == "buscar":
            acciones.append({
                "tipo": "buscar",
                "accion": "ejecutar_busqueda",
                "termino": mensaje,
                "texto": f"Buscar: {mensaje[:50]}"
            })
        
        return acciones


# Instancia global del cliente (lazy initialization)
_claude_client_instance = None

def get_claude_client():
    """Obtener o crear la instancia del cliente Claude (lazy initialization)"""
    global _claude_client_instance
    if _claude_client_instance is None:
        _claude_client_instance = ClaudeClient()
    return _claude_client_instance

# Alias para compatibilidad con código existente
# Se inicializa lazy cuando se accede por primera vez
class _ClaudeClientProxy:
    """Proxy para inicialización lazy del cliente Claude"""
    def __getattr__(self, name):
        return getattr(get_claude_client(), name)

claude_client = _ClaudeClientProxy()
