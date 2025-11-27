"""
Servicio de notificaciones (Email y WhatsApp)
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app, url_for
from models.prestador import Prestador
from models.usuario import Usuario
from models.entidad import usuario_prestador
from extensions import db

logger = logging.getLogger(__name__)


class NotificacionesService:
    """Servicio para enviar notificaciones a prestadores y entidades"""
    
    @staticmethod
    def enviar_notificacion_protocolo_completado(protocolo):
        """
        Enviar notificación cuando se completa un protocolo
        
        Args:
            protocolo: Instancia del modelo Protocolo
        """
        if not protocolo.prestador_id:
            logger.warning(f"Protocolo {protocolo.numero_protocolo} no tiene prestador asociado, no se enviará notificación")
            return
        
        prestador = Prestador.query.get(protocolo.prestador_id)
        if not prestador:
            logger.warning(f"Prestador {protocolo.prestador_id} no encontrado para protocolo {protocolo.numero_protocolo}")
            return
        
        # Determinar si debe notificarse según tipo de protocolo
        debe_notificar = False
        tipo_protocolo_str = protocolo.tipo_protocolo or 'AMBULATORIO'
        
        if tipo_protocolo_str == 'INTERNACION':
            # Protocolos de internación: notificar si tiene permiso
            debe_notificar = prestador.notificar_internacion
        elif tipo_protocolo_str == 'AMBULATORIO':
            # Protocolos ambulatorios: notificar solo si tiene orden Y tiene permiso
            debe_notificar = protocolo.con_orden and prestador.notificar_ambulatorio
        
        if not debe_notificar:
            logger.info(f"No se notifica protocolo {protocolo.numero_protocolo}: no cumple condiciones de notificación")
            return
        
        # Preparar mensaje según si tiene orden completa
        tiene_orden = protocolo.con_orden
        mensaje_orden = "completa la documentación (tiene orden)" if tiene_orden else "NO completa la documentación (falta orden)"
        mensaje_acceso = "puede acceder al informe" if tiene_orden else "NO puede acceder al informe hasta completar la orden"
        
        # Enviar por email si está configurado
        if prestador.notificar_email and prestador.email:
            resultado = NotificacionesService._enviar_email(
                destinatario=prestador.email,
                asunto=f"Protocolo {protocolo.numero_protocolo} completado",
                mensaje=NotificacionesService._generar_mensaje_email(
                    protocolo=protocolo,
                    prestador=prestador,
                    tiene_orden=tiene_orden,
                    mensaje_orden=mensaje_orden,
                    mensaje_acceso=mensaje_acceso
                )
            )
            if resultado:
                logger.info(f"✅ Email enviado a {prestador.email} para protocolo {protocolo.numero_protocolo}")
            else:
                logger.warning(f"⚠️ No se pudo enviar email a {prestador.email} (SMTP no configurado o error)")
        
        # Enviar por WhatsApp si está configurado
        if prestador.notificar_whatsapp and prestador.whatsapp:
            resultado = NotificacionesService._enviar_whatsapp(
                numero=prestador.whatsapp,
                mensaje=NotificacionesService._generar_mensaje_whatsapp(
                    protocolo=protocolo,
                    prestador=prestador,
                    tiene_orden=tiene_orden,
                    mensaje_orden=mensaje_orden,
                    mensaje_acceso=mensaje_acceso
                )
            )
            if resultado:
                logger.info(f"✅ WhatsApp enviado a {prestador.whatsapp} para protocolo {protocolo.numero_protocolo}")
            else:
                logger.warning(f"⚠️ WhatsApp registrado en logs (API no configurada) para {prestador.whatsapp}")
        
        # Notificar a entidades asociadas
        NotificacionesService._notificar_entidades_asociadas(protocolo, tiene_orden, mensaje_orden, mensaje_acceso)
    
    @staticmethod
    def _notificar_entidades_asociadas(protocolo, tiene_orden, mensaje_orden, mensaje_acceso):
        """Notificar a entidades que tengan este prestador asociado"""
        if not protocolo.prestador_id:
            return
        
        # Buscar usuarios con rol ENTIDAD que tengan este prestador asociado
        from models.usuario import Rol
        rol_entidad = Rol.query.filter(
            db.or_(
                db.func.upper(Rol.nombre) == 'ENTIDAD',
                db.func.lower(Rol.nombre) == 'entidad',
                db.func.lower(Rol.nombre) == 'entidades'
            )
        ).first()
        
        if not rol_entidad:
            return
        
        # Buscar usuarios entidad con este prestador asociado
        usuarios_entidad = db.session.query(Usuario).join(usuario_prestador).filter(
            usuario_prestador.c.prestador_id == protocolo.prestador_id,
            Usuario.rol_id == rol_entidad.rol_id,
            Usuario.activo == True
        ).all()
        
        for usuario_entidad in usuarios_entidad:
            # Verificar permisos de la asociación
            permiso = db.session.query(usuario_prestador).filter(
                usuario_prestador.c.usuario_id == usuario_entidad.usuario_id,
                usuario_prestador.c.prestador_id == protocolo.prestador_id
            ).first()
            
            if not permiso:
                continue
            
            # Determinar si debe notificar según tipo y permisos
            debe_notificar = False
            tipo_protocolo_str = protocolo.tipo_protocolo or 'AMBULATORIO'
            
            if tipo_protocolo_str == 'INTERNACION' and permiso.puede_ver_internacion:
                debe_notificar = True
            elif tipo_protocolo_str == 'AMBULATORIO' and permiso.puede_ver_ambulatorio and tiene_orden:
                debe_notificar = True
            
            if not debe_notificar:
                continue
            
            # Obtener prestador asociado a la entidad (la entidad es un Prestador con es_entidad=True)
            prestador_entidad = Prestador.query.get(usuario_entidad.prestador_id) if usuario_entidad.prestador_id else None
            
            if not prestador_entidad:
                continue
            
            # Enviar email si está configurado
            if prestador_entidad.notificar_email and prestador_entidad.email:
                resultado = NotificacionesService._enviar_email(
                    destinatario=prestador_entidad.email,
                    asunto=f"Protocolo {protocolo.numero_protocolo} completado - {protocolo.prestador.nombre_completo}",
                    mensaje=NotificacionesService._generar_mensaje_email_entidad(
                        protocolo=protocolo,
                        prestador_entidad=prestador_entidad,
                        prestador_original=protocolo.prestador,
                        tiene_orden=tiene_orden,
                        mensaje_orden=mensaje_orden,
                        mensaje_acceso=mensaje_acceso
                    )
                )
                if resultado:
                    logger.info(f"✅ Email enviado a entidad {prestador_entidad.email} para protocolo {protocolo.numero_protocolo}")
                else:
                    logger.warning(f"⚠️ No se pudo enviar email a entidad {prestador_entidad.email} (SMTP no configurado o error)")
            
            # Enviar WhatsApp si está configurado
            if prestador_entidad.notificar_whatsapp and prestador_entidad.whatsapp:
                resultado = NotificacionesService._enviar_whatsapp(
                    numero=prestador_entidad.whatsapp,
                    mensaje=NotificacionesService._generar_mensaje_whatsapp_entidad(
                        protocolo=protocolo,
                        prestador_entidad=prestador_entidad,
                        prestador_original=protocolo.prestador,
                        tiene_orden=tiene_orden,
                        mensaje_orden=mensaje_orden,
                        mensaje_acceso=mensaje_acceso
                    )
                )
                if resultado:
                    logger.info(f"✅ WhatsApp enviado a entidad {prestador_entidad.whatsapp} para protocolo {protocolo.numero_protocolo}")
                else:
                    logger.warning(f"⚠️ WhatsApp registrado en logs (API no configurada) para entidad {prestador_entidad.whatsapp}")
    
    @staticmethod
    def _generar_mensaje_email(protocolo, prestador, tiene_orden, mensaje_orden, mensaje_acceso):
        """Generar mensaje de email para prestador"""
        laboratorio_nombre = current_app.config.get('LABORATORIO_NOMBRE', 'Laboratorio')
        url_base = current_app.config.get('APPLICATION_URL', 'http://localhost:5000')
        
        mensaje = f"""
Estimado/a Dr/a. {prestador.nombre_completo},

Le informamos que el protocolo {protocolo.numero_protocolo} ha sido completado.

Detalles del protocolo:
- Número: {protocolo.numero_protocolo}
- Tipo: {protocolo.tipo_estudio}
- Paciente: {protocolo.afiliado.nombre_completo if protocolo.afiliado else 'N/A'}
- Estado de documentación: {mensaje_orden}
- Acceso al informe: {mensaje_acceso}

"""
        
        if tiene_orden:
            mensaje += f"""
Puede acceder al informe desde el portal del prestador:
{url_base}/prestador/

"""
        else:
            mensaje += """
IMPORTANTE: Para acceder al informe, debe completar la documentación (orden médica).
Una vez completada, podrá visualizar y descargar el informe desde el portal.

"""
        
        mensaje += f"""
Saludos cordiales,
{laboratorio_nombre}
"""
        return mensaje
    
    @staticmethod
    def _generar_mensaje_email_entidad(protocolo, prestador_entidad, prestador_original, tiene_orden, mensaje_orden, mensaje_acceso):
        """Generar mensaje de email para entidad"""
        laboratorio_nombre = current_app.config.get('LABORATORIO_NOMBRE', 'Laboratorio')
        url_base = current_app.config.get('APPLICATION_URL', 'http://localhost:5000')
        
        mensaje = f"""
Estimada Entidad {prestador_entidad.nombre_completo},

Le informamos que se ha completado un protocolo del prestador asociado {prestador_original.nombre_completo}.

Detalles del protocolo:
- Número: {protocolo.numero_protocolo}
- Tipo: {protocolo.tipo_estudio}
- Paciente: {protocolo.afiliado.nombre_completo if protocolo.afiliado else 'N/A'}
- Prestador: {prestador_original.nombre_completo}
- Estado de documentación: {mensaje_orden}
- Acceso al informe: {mensaje_acceso}

"""
        
        if tiene_orden:
            mensaje += f"""
Puede acceder al informe desde el portal de entidades:
{url_base}/prestador/

"""
        else:
            mensaje += """
IMPORTANTE: Para acceder al informe, debe completarse la documentación (orden médica).

"""
        
        mensaje += f"""
Saludos cordiales,
{laboratorio_nombre}
"""
        return mensaje
    
    @staticmethod
    def _generar_mensaje_whatsapp(protocolo, prestador, tiene_orden, mensaje_orden, mensaje_acceso):
        """Generar mensaje de WhatsApp para prestador"""
        laboratorio_nombre = current_app.config.get('LABORATORIO_NOMBRE', 'Laboratorio')
        
        mensaje = f"""📋 Protocolo {protocolo.numero_protocolo} completado

Dr/a. {prestador.nombre_completo}

El protocolo {protocolo.numero_protocolo} ha sido completado.

📌 Detalles:
• Tipo: {protocolo.tipo_estudio}
• Paciente: {protocolo.afiliado.nombre_completo if protocolo.afiliado else 'N/A'}
• Documentación: {mensaje_orden}
• Acceso: {mensaje_acceso}

"""
        
        if not tiene_orden:
            mensaje += "⚠️ IMPORTANTE: Complete la orden médica para acceder al informe.\n\n"
        
        mensaje += f"{laboratorio_nombre}"
        return mensaje
    
    @staticmethod
    def _generar_mensaje_whatsapp_entidad(protocolo, prestador_entidad, prestador_original, tiene_orden, mensaje_orden, mensaje_acceso):
        """Generar mensaje de WhatsApp para entidad"""
        laboratorio_nombre = current_app.config.get('LABORATORIO_NOMBRE', 'Laboratorio')
        
        mensaje = f"""📋 Protocolo {protocolo.numero_protocolo} completado

Entidad: {prestador_entidad.nombre_completo}

Se completó un protocolo del prestador asociado {prestador_original.nombre_completo}.

📌 Detalles:
• Número: {protocolo.numero_protocolo}
• Tipo: {protocolo.tipo_estudio}
• Paciente: {protocolo.afiliado.nombre_completo if protocolo.afiliado else 'N/A'}
• Prestador: {prestador_original.nombre_completo}
• Documentación: {mensaje_orden}
• Acceso: {mensaje_acceso}

"""
        
        if not tiene_orden:
            mensaje += "⚠️ IMPORTANTE: Complete la orden médica para acceder al informe.\n\n"
        
        mensaje += f"{laboratorio_nombre}"
        return mensaje
    
    @staticmethod
    def _enviar_email(destinatario, asunto, mensaje):
        """Enviar email usando SMTP"""
        try:
            smtp_host = current_app.config.get('SMTP_HOST')
            smtp_port = current_app.config.get('SMTP_PORT', 587)
            smtp_user = current_app.config.get('SMTP_USER')
            smtp_password = current_app.config.get('SMTP_PASSWORD')
            smtp_use_tls = current_app.config.get('SMTP_USE_TLS', True)
            remitente = current_app.config.get('LABORATORIO_EMAIL', smtp_user or 'noreply@laboratorio.com')
            
            if not smtp_host:
                logger.warning("SMTP_HOST no configurado, no se puede enviar email")
                return False
            
            msg = MIMEMultipart()
            msg['From'] = remitente
            msg['To'] = destinatario
            msg['Subject'] = asunto
            msg.attach(MIMEText(mensaje, 'plain', 'utf-8'))
            
            server = smtplib.SMTP(smtp_host, smtp_port)
            if smtp_use_tls:
                server.starttls()
            
            if smtp_user and smtp_password:
                server.login(smtp_user, smtp_password)
            
            server.send_message(msg)
            server.quit()
            
            return True
        except Exception as e:
            logger.error(f"Error enviando email: {e}")
            # No lanzar excepción, solo registrar el error para no interrumpir el flujo principal
            return False
    
    @staticmethod
    def _enviar_whatsapp(numero, mensaje):
        """
        Enviar WhatsApp
        NOTA: Requiere integración con API de WhatsApp (Twilio, WhatsApp Business API, etc.)
        Por ahora solo registra en logs
        """
        # TODO: Implementar integración con WhatsApp Business API o Twilio
        logger.info(f"WhatsApp para {numero}: {mensaje}")
        
        # Ejemplo con Twilio (descomentar cuando se configure):
        # from twilio.rest import Client
        # account_sid = current_app.config.get('TWILIO_ACCOUNT_SID')
        # auth_token = current_app.config.get('TWILIO_AUTH_TOKEN')
        # from_number = current_app.config.get('TWILIO_WHATSAPP_NUMBER')
        # 
        # if account_sid and auth_token and from_number:
        #     client = Client(account_sid, auth_token)
        #     message = client.messages.create(
        #         body=mensaje,
        #         from_=f'whatsapp:{from_number}',
        #         to=f'whatsapp:{numero}'
        #     )
        #     return message.sid
        # else:
        #     logger.warning("Twilio no configurado, no se puede enviar WhatsApp")
        
        return False

