# ESQUEMA DE BASE DE DATOS - LDH Web
**Sistema de Gestión de Laboratorio de Anatomía Patológica**

---

## TABLAS DEL SISTEMA

### 1. USUARIOS Y PERMISOS

#### `usuarios`
Usuarios del sistema con autenticación
```sql
id                  INTEGER PRIMARY KEY AUTOINCREMENT
username            VARCHAR(50) UNIQUE NOT NULL
password_hash       VARCHAR(255) NOT NULL
email               VARCHAR(100) UNIQUE NOT NULL
nombre_completo     VARCHAR(100) NOT NULL
telefono            VARCHAR(20)
activo              BOOLEAN DEFAULT 1
rol_id              INTEGER NOT NULL (FK -> roles.id)
fecha_creacion      DATETIME DEFAULT CURRENT_TIMESTAMP
ultimo_acceso       DATETIME
```

#### `roles`
Roles de usuario en el sistema
```sql
id                  INTEGER PRIMARY KEY AUTOINCREMENT
nombre              VARCHAR(50) UNIQUE NOT NULL
descripcion         TEXT
```

**Roles predefinidos:**
- Administrador
- Médico Patólogo
- Técnico de Laboratorio
- Secretaría/Administrativo
- Consulta (solo lectura)

#### `permisos`
Permisos específicos del sistema
```sql
id                  INTEGER PRIMARY KEY AUTOINCREMENT
codigo              VARCHAR(50) UNIQUE NOT NULL
nombre              VARCHAR(100) NOT NULL
descripcion         TEXT
modulo              VARCHAR(50)
```

#### `roles_permisos`
Relación muchos a muchos entre roles y permisos
```sql
id                  INTEGER PRIMARY KEY AUTOINCREMENT
rol_id              INTEGER NOT NULL (FK -> roles.id)
permiso_id          INTEGER NOT NULL (FK -> permisos.id)
```

---

### 2. GESTIÓN DE PACIENTES

#### `afiliados`
Pacientes del laboratorio
```sql
id                  INTEGER PRIMARY KEY AUTOINCREMENT
nombre              VARCHAR(200) NOT NULL
obra_social_id      INTEGER (FK -> obras_sociales.id)
numero_afiliado     VARCHAR(50)
tipo_documento      VARCHAR(10)
numero_documento    VARCHAR(20)
fecha_nacimiento    DATE
edad                INTEGER
codigo_postal       VARCHAR(10)
localidad           VARCHAR(100)
telefono            VARCHAR(20)
email               VARCHAR(100)
observaciones       TEXT
activo              BOOLEAN DEFAULT 1
fecha_registro      DATETIME DEFAULT CURRENT_TIMESTAMP
ultima_modificacion DATETIME
```

**Índices:**
- `idx_afiliados_documento` (tipo_documento, numero_documento)
- `idx_afiliados_nombre` (nombre)
- `idx_afiliados_obra_social` (obra_social_id)

---

### 3. GESTIÓN DE PRESTADORES

#### `prestadores`
Médicos solicitantes de estudios
```sql
id                  INTEGER PRIMARY KEY AUTOINCREMENT
nombre              VARCHAR(200) NOT NULL
codigo              VARCHAR(20) UNIQUE
tipo_matricula      VARCHAR(10)
numero_matricula    VARCHAR(20)
fecha_matricula     DATE
especialidad        VARCHAR(100)
tipo_documento      VARCHAR(10)
numero_documento    VARCHAR(20)
cuit                VARCHAR(13)
direccion           VARCHAR(200)
codigo_postal       VARCHAR(10)
localidad           VARCHAR(100)
provincia           VARCHAR(50)
telefono            VARCHAR(20)
email               VARCHAR(100)
activo              BOOLEAN DEFAULT 1
fecha_registro      DATETIME DEFAULT CURRENT_TIMESTAMP
```

**Índices:**
- `idx_prestadores_nombre` (nombre)
- `idx_prestadores_matricula` (numero_matricula)

---

### 4. GESTIÓN DE OBRAS SOCIALES

#### `obras_sociales`
Obras sociales, prepagas y mutuales
```sql
id                  INTEGER PRIMARY KEY AUTOINCREMENT
codigo              VARCHAR(20) UNIQUE NOT NULL
nombre              VARCHAR(200) NOT NULL
direccion           VARCHAR(200)
localidad           VARCHAR(100)
codigo_postal       VARCHAR(10)
telefono            VARCHAR(50)
codigo_inos         VARCHAR(20)
plan_id             INTEGER (FK -> planes_facturacion.id)
activo              BOOLEAN DEFAULT 1
observaciones       TEXT
fecha_registro      DATETIME DEFAULT CURRENT_TIMESTAMP
```

#### `planes_facturacion`
Planes de facturación con porcentajes
```sql
id                  INTEGER PRIMARY KEY AUTOINCREMENT
codigo              VARCHAR(20) UNIQUE NOT NULL
nombre              VARCHAR(200) NOT NULL
porcentaje_base     DECIMAL(5,2) DEFAULT 100.0
activo              BOOLEAN DEFAULT 1
observaciones       TEXT
```

#### `planes_categorias`
Porcentajes por categoría en cada plan
```sql
id                  INTEGER PRIMARY KEY AUTOINCREMENT
plan_id             INTEGER NOT NULL (FK -> planes_facturacion.id)
categoria_codigo    VARCHAR(10) NOT NULL
porcentaje          DECIMAL(5,2) NOT NULL
```

---

### 5. TIPOS DE ANÁLISIS Y PLANTILLAS

#### `tipos_analisis`
Tipos de análisis disponibles
```sql
id                  INTEGER PRIMARY KEY AUTOINCREMENT
codigo              VARCHAR(20) UNIQUE NOT NULL
nombre              VARCHAR(100) NOT NULL
categoria           VARCHAR(50) (BIOPSIA, CITOLOGIA, PAP)
activo              BOOLEAN DEFAULT 1
```

#### `plantillas_pap`
Plantillas predefinidas para informes PAP
```sql
id                  INTEGER PRIMARY KEY AUTOINCREMENT
categoria           VARCHAR(50) NOT NULL
descripcion         TEXT NOT NULL
orden               INTEGER DEFAULT 0
activo              BOOLEAN DEFAULT 1
```

**Categorías de plantillas PAP:**
- EXTENDIDO
- CELULAS_CONFORMACION
- CELULAS_JUNTO_A
- COMPONENTE_INFLAMATORIO
- FLORA
- DIAGNOSTICO
- DATOS_CLINICOS

---

### 6. PROTOCOLOS - TABLA CENTRAL

#### `protocolos`
Tabla central de todos los estudios
```sql
id                  INTEGER PRIMARY KEY AUTOINCREMENT
numero_protocolo    VARCHAR(20) UNIQUE NOT NULL
tipo_estudio        VARCHAR(20) NOT NULL (BIOPSIA, CITOLOGIA, PAP)
afiliado_id         INTEGER NOT NULL (FK -> afiliados.id)
prestador_id        INTEGER (FK -> prestadores.id)
obra_social_id      INTEGER (FK -> obras_sociales.id)
tipo_analisis_id    INTEGER (FK -> tipos_analisis.id)
fecha_ingreso       DATE NOT NULL
fecha_informe       DATE
datos_clinicos      TEXT
estado              VARCHAR(20) DEFAULT 'PENDIENTE'
usuario_ingreso_id  INTEGER (FK -> usuarios.id)
usuario_informe_id  INTEGER (FK -> usuarios.id)
fecha_creacion      DATETIME DEFAULT CURRENT_TIMESTAMP
ultima_modificacion DATETIME
```

**Estados posibles:**
- PENDIENTE
- EN_PROCESO
- INFORMADO
- ENTREGADO
- FACTURADO

**Índices:**
- `idx_protocolos_numero` (numero_protocolo)
- `idx_protocolos_tipo` (tipo_estudio)
- `idx_protocolos_fecha` (fecha_ingreso)
- `idx_protocolos_estado` (estado)
- `idx_protocolos_afiliado` (afiliado_id)

---

### 7. INFORMES DE BIOPSIAS

#### `biopsias_informes`
Informes específicos de biopsias
```sql
id                      INTEGER PRIMARY KEY AUTOINCREMENT
protocolo_id            INTEGER UNIQUE NOT NULL (FK -> protocolos.id)
material_remitido       TEXT
descripcion_macroscopica TEXT
descripcion_microscopica TEXT
diagnostico             TEXT
observaciones           TEXT
fecha_informe           DATE
```

---

### 8. INFORMES DE CITOLOGÍA GENERAL

#### `citologia_informes`
Informes de citología general
```sql
id                  INTEGER PRIMARY KEY AUTOINCREMENT
protocolo_id        INTEGER UNIQUE NOT NULL (FK -> protocolos.id)
descripcion         TEXT
diagnostico         TEXT
observaciones       TEXT
fecha_informe       DATE
```

---

### 9. INFORMES DE PAP (CITOLOGÍA CÉRVICO VAGINAL)

#### `pap_informes`
Informes de citología cérvico vaginal
```sql
id                  INTEGER PRIMARY KEY AUTOINCREMENT
protocolo_id        INTEGER UNIQUE NOT NULL (FK -> protocolos.id)
fum                 DATE (Fecha Última Menstruación)
datos_clinicos_1    TEXT
datos_clinicos_2    TEXT
datos_clinicos_3    TEXT
datos_clinicos_4    TEXT
datos_clinicos_5    TEXT
extendido_1         TEXT
extendido_2         TEXT
extendido_3         TEXT
extendido_4         TEXT
extendido_5         TEXT
celulas_1           TEXT
celulas_2           TEXT
celulas_3           TEXT
celulas_4           TEXT
celulas_5           TEXT
comp_inflamatorio_1 TEXT
comp_inflamatorio_2 TEXT
comp_inflamatorio_3 TEXT
flora_1             TEXT
flora_2             TEXT
diagnostico_1       TEXT
diagnostico_2       TEXT
diagnostico_3       TEXT
diagnostico_4       TEXT
diagnostico_5       TEXT
informe_completo    TEXT (Generado automáticamente)
fecha_informe       DATE
```

---

### 10. AUDITORÍA Y LOGS

#### `auditoria`
Registro de todas las operaciones importantes
```sql
id                  INTEGER PRIMARY KEY AUTOINCREMENT
usuario_id          INTEGER (FK -> usuarios.id)
accion              VARCHAR(50) NOT NULL
tabla               VARCHAR(50)
registro_id         INTEGER
descripcion         TEXT
ip_address          VARCHAR(50)
fecha_hora          DATETIME DEFAULT CURRENT_TIMESTAMP
```

**Acciones auditables:**
- LOGIN
- LOGOUT
- CREAR
- MODIFICAR
- ELIMINAR
- IMPRIMIR
- EXPORTAR

---

### 11. CONFIGURACIÓN DEL SISTEMA

#### `configuracion`
Parámetros de configuración general
```sql
id                  INTEGER PRIMARY KEY AUTOINCREMENT
clave               VARCHAR(100) UNIQUE NOT NULL
valor               TEXT
tipo                VARCHAR(20) (STRING, INTEGER, BOOLEAN, JSON)
descripcion         TEXT
categoria           VARCHAR(50)
```

**Configuraciones importantes:**
- `laboratorio_nombre`
- `laboratorio_direccion`
- `laboratorio_telefono`
- `laboratorio_email`
- `laboratorio_logo_path`
- `contador_biopsias_actual`
- `contador_citologia_actual`
- `contador_pap_actual`
- `formato_numero_protocolo`

---

## RELACIONES PRINCIPALES

```
usuarios (N) -> (1) roles
roles (N) <-> (N) permisos

afiliados (N) -> (1) obras_sociales
obras_sociales (N) -> (1) planes_facturacion

protocolos (N) -> (1) afiliados
protocolos (N) -> (1) prestadores
protocolos (N) -> (1) obras_sociales
protocolos (N) -> (1) tipos_analisis
protocolos (N) -> (1) usuarios (ingreso)
protocolos (N) -> (1) usuarios (informe)

protocolos (1) <-> (1) biopsias_informes
protocolos (1) <-> (1) citologia_informes
protocolos (1) <-> (1) pap_informes

auditoria (N) -> (1) usuarios
```

---

## VISTAS ÚTILES

### `vista_protocolos_completa`
Vista con todos los datos del protocolo
```sql
SELECT 
    p.numero_protocolo,
    p.tipo_estudio,
    p.fecha_ingreso,
    p.estado,
    a.nombre as paciente,
    a.edad,
    pr.nombre as prestador,
    os.nombre as obra_social,
    u_ing.nombre_completo as usuario_ingreso,
    u_inf.nombre_completo as usuario_informe
FROM protocolos p
LEFT JOIN afiliados a ON p.afiliado_id = a.id
LEFT JOIN prestadores pr ON p.prestador_id = pr.id
LEFT JOIN obras_sociales os ON p.obra_social_id = os.id
LEFT JOIN usuarios u_ing ON p.usuario_ingreso_id = u_ing.id
LEFT JOIN usuarios u_inf ON p.usuario_informe_id = u_inf.id
```

---

## ÍNDICES ADICIONALES RECOMENDADOS

Para mejorar el rendimiento de búsquedas:

```sql
CREATE INDEX idx_protocolos_compuesto ON protocolos(tipo_estudio, estado, fecha_ingreso DESC);
CREATE INDEX idx_afiliados_busqueda ON afiliados(nombre, numero_documento);
CREATE INDEX idx_auditoria_fecha ON auditoria(fecha_hora DESC);
CREATE INDEX idx_auditoria_usuario ON auditoria(usuario_id, fecha_hora DESC);
```

---

## MIGRACIÓN DE DATOS

Los datos se migrarán así:

**Access → SQLite:**
- `Afiliados` → `afiliados`
- `Obras Sociales` → `obras_sociales`
- `Prestadores` → `prestadores`
- `PLANES` → `planes_facturacion`
- Protocolos de Biopsias → `protocolos` + `biopsias_informes`
- Protocolos de Citología → `protocolos` + `citologia_informes`
- Protocolos de PAP → `protocolos` + `pap_informes`
- Plantillas PAP → `plantillas_pap`
- Tipos de Análisis → `tipos_analisis`

---

## NOTAS DE DISEÑO

**Normalización:**
- Tercera forma normal (3NF)
- Evita redundancia de datos
- Facilita mantenimiento

**Integridad referencial:**
- Todas las FK con ON DELETE RESTRICT por defecto
- Eliminaciones lógicas con campo `activo`

**Auditoría:**
- Todas las tablas principales tienen timestamps
- Tabla de auditoría para operaciones críticas

**Escalabilidad:**
- Diseño permite agregar nuevos tipos de estudios
- Sistema de plantillas extensible
- Configuración flexible en BD

**Seguridad:**
- Contraseñas hasheadas
- Sistema de permisos granular
- Auditoría de accesos

---

**Fecha de Diseño:** 2025-10-10  
**Versión:** 1.0  
**Estado:** Propuesta inicial para revisión

