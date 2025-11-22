# Sistema de Permisos - LDH Web
**Laboratorio de Diagnóstico Histopatológico**

---

## ROLES DEL SISTEMA (6 ROLES)

### 1. Administrador (OSCAR)
**Descripción:** Acceso total al sistema  
**Código:** `ADMIN`

**Permisos:**
- ✅ Gestión completa de usuarios (crear, editar, eliminar)
- ✅ Gestión de roles y permisos
- ✅ Gestión de pacientes, prestadores, obras sociales
- ✅ Crear, editar, eliminar protocolos
- ✅ Crear, editar, firmar informes
- ✅ Generar e imprimir PDFs
- ✅ Reportes y estadísticas (médicos y contables)
- ✅ Acceso a módulo contable completo
- ✅ Configuración del sistema
- ✅ Auditoría completa

### 2. Médico
**Descripción:** Médico patólogo  
**Código:** `MEDICO`

**Permisos:**
- ✅ Ver pacientes, prestadores, obras sociales
- ✅ Crear y editar protocolos
- ✅ **Crear y editar informes** (principal)
- ✅ **Firmar informes**
- ✅ Generar e imprimir PDFs de informes
- ✅ Ver estadísticas propias
- ❌ No puede modificar usuarios
- ❌ No puede acceder a configuración
- ❌ No puede acceder a módulo contable

### 3. Técnico
**Descripción:** Técnico de laboratorio  
**Código:** `TECNICO`

**Permisos:**
- ✅ Crear y editar pacientes
- ✅ Crear y editar prestadores
- ✅ Crear y editar obras sociales
- ✅ **Ingresar protocolos nuevos** (recepción)
- ✅ Editar datos básicos de protocolos
- ✅ Ver informes
- ❌ No puede crear ni editar informes (eso es del médico)
- ❌ No puede firmar informes
- ❌ No puede acceder a módulo contable
- ❌ No puede gestionar usuarios

### 4. Secretaria
**Descripción:** Personal administrativo  
**Código:** `SECRETARIA`

**Permisos:**
- ✅ **Recibir al paciente** (primer contacto, por lo general)
- ✅ Crear y editar pacientes
- ✅ Crear y editar prestadores
- ✅ Crear y editar obras sociales
- ✅ **Crear protocolos** (recepción de muestras y órdenes)
- ✅ Ver protocolos
- ✅ Ver informes
- ✅ **Imprimir informes finalizados** (para entregar)
- ✅ Acceso a módulo contable (facturación)
- ❌ No puede editar datos técnicos de protocolos
- ❌ No puede crear ni editar informes médicos
- ❌ No puede gestionar usuarios

### 5. Contable
**Descripción:** Administración contable y facturación  
**Código:** `CONTABLE`

**Permisos:**
- ✅ Ver pacientes (solo datos básicos)
- ✅ Ver prestadores (solo datos básicos)
- ✅ Ver obras sociales (completo)
- ✅ Ver protocolos (solo datos administrativos, no médicos)
- ✅ **Acceso completo a módulo contable**
- ✅ **Facturación a obras sociales**
- ✅ **Reportes contables**
- ✅ Imprimir reportes contables
- ❌ **No puede ver informes médicos** (descripción, diagnóstico)
- ❌ No puede crear ni editar protocolos
- ❌ No puede crear ni editar informes
- ❌ No puede gestionar usuarios
- ❌ No puede ver datos clínicos sensibles

### 6. Solo Lectura
**Descripción:** Consulta sin modificaciones  
**Código:** `LECTURA`

**Permisos:**
- ✅ Ver pacientes
- ✅ Ver prestadores
- ✅ Ver obras sociales
- ✅ Ver protocolos
- ✅ Ver informes (solo en pantalla)
- ❌ **No puede generar PDFs**
- ❌ **No puede imprimir**
- ❌ **No puede acceder a módulo contable**
- ❌ No puede crear ni editar nada
- ❌ No puede gestionar usuarios

---

## CÓDIGOS DE PERMISOS

### Módulo de Usuarios
- `usuarios_ver` - Ver usuarios
- `usuarios_crear` - Crear usuarios
- `usuarios_editar` - Editar usuarios
- `usuarios_eliminar` - Eliminar usuarios
- `roles_gestionar` - Gestionar roles y permisos

### Módulo de Pacientes
- `pacientes_ver` - Ver pacientes
- `pacientes_crear` - Crear pacientes
- `pacientes_editar` - Editar pacientes
- `pacientes_eliminar` - Eliminar/desactivar pacientes

### Módulo de Prestadores
- `prestadores_ver` - Ver prestadores
- `prestadores_crear` - Crear prestadores
- `prestadores_editar` - Editar prestadores
- `prestadores_eliminar` - Eliminar/desactivar prestadores

### Módulo de Obras Sociales
- `obras_sociales_ver` - Ver obras sociales
- `obras_sociales_crear` - Crear obras sociales
- `obras_sociales_editar` - Editar obras sociales
- `obras_sociales_eliminar` - Eliminar/desactivar obras sociales

### Módulo de Protocolos
- `protocolos_ver` - Ver protocolos
- `protocolos_crear` - Crear/ingresar protocolos
- `protocolos_editar` - Editar protocolos
- `protocolos_eliminar` - Eliminar protocolos

### Módulo de Informes
- `informes_ver` - Ver informes
- `informes_crear` - Crear informes
- `informes_editar` - Editar informes
- `informes_firmar` - Firmar informes
- `informes_pdf` - Generar PDFs
- `informes_imprimir` - Imprimir informes

### Módulo Contable
- `contable_acceso` - Acceso al módulo contable
- `contable_facturacion` - Generar facturación
- `contable_reportes` - Reportes contables

### Módulo de Reportes
- `reportes_ver` - Ver reportes y estadísticas
- `reportes_avanzados` - Reportes avanzados

### Administración
- `admin_acceso` - Acceso al panel admin
- `admin_configuracion` - Modificar configuración del sistema
- `admin_auditoria` - Ver auditoría completa

---

## MATRIZ DE PERMISOS

| Permiso | Admin | Médico | Técnico | Secretaria | Contable | Lectura |
|---------|-------|--------|---------|------------|----------|---------|
| **USUARIOS** |
| usuarios_ver | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| usuarios_crear | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| usuarios_editar | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| usuarios_eliminar | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| roles_gestionar | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **PACIENTES** |
| pacientes_ver | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| pacientes_crear | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ |
| pacientes_editar | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ |
| pacientes_eliminar | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **PRESTADORES** |
| prestadores_ver | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| prestadores_crear | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ |
| prestadores_editar | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ |
| prestadores_eliminar | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **OBRAS SOCIALES** |
| obras_sociales_ver | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| obras_sociales_crear | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ |
| obras_sociales_editar | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ |
| obras_sociales_eliminar | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **PROTOCOLOS** |
| protocolos_ver | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| protocolos_crear | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| protocolos_editar | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| protocolos_eliminar | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **INFORMES** |
| informes_ver | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| informes_crear | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| informes_editar | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| informes_firmar | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| informes_pdf | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| informes_imprimir | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| **CONTABLE** |
| contable_acceso | ✅ | ❌ | ❌ | ✅ | ✅ | ❌ |
| contable_facturacion | ✅ | ❌ | ❌ | ✅ | ✅ | ❌ |
| contable_reportes | ✅ | ❌ | ❌ | ✅ | ✅ | ❌ |
| **REPORTES** |
| reportes_ver | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| reportes_avanzados | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **ADMINISTRACIÓN** |
| admin_acceso | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| admin_configuracion | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| admin_auditoria | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |

---

## Notas sobre OSCAR:

**Rol oculto:** No aparece en listados para usuarios normales, pero existe en BD.

¿Te parece bien esta distribución de permisos? ¿Necesitás ajustar algo? Una vez que lo confirmes, actualizo el código para implementar todos estos permisos. 😊
