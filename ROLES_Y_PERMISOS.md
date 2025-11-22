# 🔬 ROLES Y PERMISOS - LDH Web
**Laboratorio de Diagnóstico Histopatológico**

---

## 📋 RESUMEN DE ROLES

El sistema cuenta con **6 roles** diferenciados:

| Rol | Código | Enfoque Principal |
|-----|--------|-------------------|
| 🔑 Administrador | ADMIN | Gestión total del sistema |
| 🩺 Médico | MEDICO | Creación de informes médicos |
| 🔬 Técnico | TECNICO | Ingreso de muestras y datos |
| 📋 Secretaria | SECRETARIA | Gestión administrativa |
| 💰 Contable | CONTABLE | Facturación (sin datos médicos) |
| 👁️ Solo Lectura | LECTURA | Consulta únicamente |

---

## 🔑 ROL: ADMINISTRADOR

**Descripción:** Acceso total al sistema  
**Puede haber múltiples administradores**

**Nota especial:** El usuario `admin` es el administrador principal del sistema.

### Puede hacer TODO:
✅ Crear, editar y eliminar usuarios  
✅ Gestionar roles y permisos  
✅ Gestión completa de pacientes, prestadores, obras sociales  
✅ Crear, editar y eliminar protocolos  
✅ Crear, editar y firmar informes  
✅ Generar e imprimir PDFs  
✅ Acceso completo a módulo contable  
✅ Ver todos los reportes y estadísticas  
✅ Modificar configuración del sistema  
✅ Ver auditoría completa  

**En resumen:** No tiene restricciones

---

## 🩺 ROL: MÉDICO

**Usuario:** Médico patólogo  
**Enfoque:** Creación de informes médicos

### Puede hacer:
✅ Ver pacientes, prestadores y obras sociales  
✅ Crear y editar protocolos  
✅ **Crear informes médicos** (su función principal)  
✅ **Editar y firmar informes**  
✅ Generar PDFs de informes  
✅ Imprimir informes  
✅ Ver reportes estadísticos médicos  

### NO puede hacer:
❌ Modificar pacientes, prestadores u obras sociales  
❌ Eliminar protocolos  
❌ Acceder al módulo contable  
❌ Gestionar usuarios  
❌ Modificar configuración del sistema  

**En resumen:** Solo lo médico - creación y firma de informes

---

## 🔬 ROL: TÉCNICO

**Usuario:** Técnico de laboratorio  
**Enfoque:** Procesamiento técnico de muestras

### Puede hacer:
✅ **Crear y editar pacientes** (si es necesario)  
✅ **Crear y editar prestadores** (médicos solicitantes)  
✅ **Crear y editar obras sociales**  
✅ **Ingresar protocolos** (puede recibirlos si no está secretaria)  
✅ **Registrar datos técnicos** de las muestras  
✅ Editar datos básicos de protocolos  
✅ Ver informes (para consulta)  

### NO puede hacer:
❌ **Crear ni editar informes** (eso es del médico)  
❌ Firmar informes  
❌ Eliminar nada  
❌ Acceder al módulo contable  
❌ Gestionar usuarios  

**En resumen:** Procesamiento técnico de muestras y carga de datos, pero no creación de informes

---

## 📋 ROL: SECRETARIA

**Usuario:** Personal administrativo  
**Enfoque:** Recepción de pacientes y gestión administrativa

### Puede hacer:
✅ **Recibir al paciente** (primer contacto, por lo general)  
✅ **Crear y editar pacientes**  
✅ **Crear y editar prestadores**  
✅ **Crear y editar obras sociales**  
✅ **Crear protocolos** (recepción de muestras y órdenes)  
✅ Ver todos los protocolos  
✅ Ver todos los informes  
✅ **Imprimir informes finalizados** (para entregar al paciente)  
✅ **Acceso al módulo contable** (facturación)  

### NO puede hacer:
❌ **Editar datos técnicos de protocolos** (eso es del técnico)  
❌ **Crear ni editar informes médicos**  
❌ Firmar informes  
❌ Eliminar nada  
❌ Gestionar usuarios  

**En resumen:** Primera atención al paciente, recepción de muestras, entrega de informes y facturación

---

## 💰 ROL: CONTABLE

**Usuario:** Administración contable  
**Enfoque:** Facturación y reportes económicos

### Puede hacer:
✅ Ver pacientes (solo nombre, documento, obra social)  
✅ Ver prestadores (solo nombre, matrícula)  
✅ Ver obras sociales (completo con planes)  
✅ Ver protocolos (solo: número, fecha, paciente, obra social, tipo)  
✅ **Acceso completo al módulo contable**  
✅ **Generar facturación a obras sociales**  
✅ **Reportes contables y estadísticas de facturación**  
✅ Imprimir reportes contables  

### NO puede hacer:
❌ **Ver informes médicos** (descripción, diagnóstico)  
❌ **Ver datos clínicos sensibles**  
❌ Crear ni editar pacientes, prestadores u obras sociales  
❌ Crear ni editar protocolos  
❌ Crear ni editar informes  
❌ Gestionar usuarios  

**En resumen:** Solo facturación y contabilidad, sin acceso a datos médicos

---

## 👁️ ROL: SOLO LECTURA

**Usuario:** Consulta externa  
**Enfoque:** Solo visualización

### Puede hacer:
✅ Ver pacientes  
✅ Ver prestadores  
✅ Ver obras sociales  
✅ Ver protocolos  
✅ **Ver informes solo en pantalla**  

### NO puede hacer:
❌ **Generar PDFs**  
❌ **Imprimir nada**  
❌ **Acceder a módulo contable**  
❌ Crear ni editar absolutamente nada  
❌ Gestionar usuarios  

**En resumen:** Solo consulta en pantalla, sin exportar ni imprimir

---

## 🔐 SEGURIDAD Y PRIVACIDAD

### Separación de Datos Médicos y Contables

**Importante:** El rol **Contable** tiene una restricción especial:

- Puede ver que existe un protocolo (número, fecha, paciente)
- Puede ver a qué obra social facturar
- **NO puede ver el contenido médico:** descripción microscópica, diagnóstico, datos clínicos

Esto garantiza:
- **Privacidad médica** protegida
- **Facturación** sin exponer datos sensibles
- **Cumplimiento** de normativas de confidencialidad

### Jerarquía de Acceso

```
Administrador ─────────────────► TODO (puede haber varios)
    │                             (Super-admin oculto)
    │
    ├─► Médico ────────────────► Informes médicos
    │
    ├─► Técnico ───────────────► Procesamiento técnico
    │
    ├─► Secretaria ────────────► Recepción, entrega y facturación
    │
    ├─► Contable ──────────────► Solo facturación
    │
    └─► Solo Lectura ──────────► Solo visualización
```

---

## 📊 TABLA COMPARATIVA RÁPIDA

| Funcionalidad | Admin | Médico | Técnico | Secretaria | Contable | Lectura |
|---------------|-------|--------|---------|------------|----------|---------|
| Gestionar Usuarios | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| ABM Pacientes | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ |
| ABM Prestadores | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ |
| ABM Obras Sociales | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ |
| Ingresar Protocolos | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| Crear Informes | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Firmar Informes | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Ver Informes Médicos | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| Imprimir Informes | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| Módulo Contable | ✅ | ❌ | ❌ | ✅ | ✅ | ❌ |
| Configuración | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |

**Leyenda:** ABM = Alta, Baja, Modificación

---

## 💡 CASOS DE USO

### Flujo de Trabajo Típico:

**1. Recepción (generalmente Secretaria, a veces Técnico):**
- **Secretaria** recibe al paciente
- **Secretaria** ingresa al paciente (si es nuevo)
- **Secretaria** o **Técnico** crea el protocolo
- **Técnico** registra datos técnicos de la muestra

**2. Procesamiento:**
- **Médico** revisa la muestra
- **Médico** crea el informe (descripción, diagnóstico)
- **Médico** firma el informe

**3. Entrega:**
- **Secretaria** ve que el informe está listo
- **Secretaria** imprime el informe
- **Secretaria** entrega al paciente

**4. Facturación:**
- **Contable** ve los protocolos del mes
- **Contable** genera facturación por obra social
- **Contable** no ve los diagnósticos (privacidad)

**5. Consulta Externa:**
- **Solo Lectura** puede consultar informes en pantalla
- No puede imprimir ni generar PDFs

---

## 🛡️ NOTAS DE SEGURIDAD

### Privacidad Médica
- Solo Admin, Médico, Técnico, Secretaria y Solo Lectura pueden ver informes médicos completos
- **Contable NO ve datos médicos** para proteger privacidad

### Auditoría
- Todas las acciones se registran en la tabla `auditoria`
- Solo Admin puede ver la auditoría completa
- Se registra: usuario, acción, tabla, registro_id, IP, fecha/hora

### Restricciones
- Solo Admin puede crear/modificar usuarios
- Solo Médico puede firmar informes
- Técnico puede ingresar pero no informar
- Contable separado de datos médicos

---

## 📝 CÓMO USAR LOS PERMISOS EN EL CÓDIGO

En templates:
```html
{% if tiene_permiso('pacientes_crear') %}
    <a href="{{ url_for('pacientes.nuevo') }}" class="btn btn-primary">
        Nuevo Paciente
    </a>
{% endif %}
```

En rutas Python:
```python
from utils.decorators import permission_required

@bp.route('/nuevo')
@login_required
@permission_required('pacientes_crear')
def nuevo():
    # Solo usuarios con permiso pacientes_crear pueden acceder
    pass
```

---

**Documento actualizado:** 11/10/2025  
**Total de roles:** 6  
**Total de permisos únicos:** ~35  

---

---

## ℹ️ NOTA SOBRE USUARIOS

### Usuario Administrador Principal:
- **Username:** `admin` (para login)
- **Nombre completo:** Super Administrador
- **Contraseña inicial:** admin123 (cambiar en primer uso)

**Importante:** El username `admin` no cambia, es para hacer login. El nombre completo "Super Administrador" es solo para identificación en el sistema.

**Pueden crearse múltiples usuarios con rol Administrador** según sea necesario.

---

**Ubicación:** `C:\LDH\LDH_Web\ROLES_Y_PERMISOS.md`

