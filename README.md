# LDH Web - Sistema de Gestión de Laboratorio de Anatomía Patológica

Sistema web multiusuario para la gestión integral de un laboratorio de anatomía patológica, que incluye biopsias, citología general y citología cérvico vaginal (PAP).

## Características Principales

- **Gestión de Protocolos**: Biopsias, Citología General y PAP
- **Sistema de Plantillas**: Para generación rápida de informes PAP
- **Gestión de Pacientes**: Base de datos completa de afiliados
- **Obras Sociales**: Gestión de obras sociales, planes y facturación
- **Prestadores**: Registro de médicos solicitantes
- **Multiusuario**: Sistema de roles y permisos
- **Auditoría**: Registro de todas las operaciones críticas
- **Generación de PDFs**: Informes en formato PDF
- **Búsqueda Avanzada**: Filtros y reportes estadísticos

## Requisitos

- Python 3.8 o superior
- SQLite (incluido con Python)
- Navegador web moderno

## Instalación

### 1. Instalar dependencias

```bash
cd C:\LDH\LDH_Web
pip install -r requirements.txt
```

### 2. Inicializar la base de datos

```bash
python -m flask --app app initdb
```

Este comando creará:
- La base de datos SQLite
- Las tablas necesarias
- Los roles por defecto
- Un usuario administrador (usuario: `admin`, contraseña: `admin123`)

### 3. Ejecutar la aplicación

```bash
python app.py
```

La aplicación estará disponible en: `http://localhost:5000`

## Primer Uso

1. Acceder a `http://localhost:5000`
2. Iniciar sesión con:
   - Usuario: `admin`
   - Contraseña: `admin123`
3. **IMPORTANTE**: Cambiar la contraseña del administrador inmediatamente
4. Configurar los datos del laboratorio en Admin → Configuración

## Estructura del Proyecto

```
LDH_Web/
├── app.py                  # Aplicación principal
├── config.py               # Configuración
├── requirements.txt        # Dependencias
├── models/                 # Modelos de datos (SQLAlchemy)
│   ├── usuario.py
│   ├── paciente.py
│   ├── prestador.py
│   ├── obra_social.py
│   ├── protocolo.py
│   ├── informe.py
│   ├── auditoria.py
│   └── configuracion.py
├── routes/                 # Rutas (Blueprints)
│   ├── auth.py
│   ├── dashboard.py
│   ├── pacientes.py
│   ├── prestadores.py
│   ├── obras_sociales.py
│   ├── biopsias.py
│   ├── citologia.py
│   ├── pap.py
│   ├── reportes.py
│   └── admin.py
├── templates/              # Templates HTML
│   ├── base.html
│   ├── auth/
│   ├── dashboard/
│   ├── pacientes/
│   ├── prestadores/
│   ├── obras_sociales/
│   ├── biopsias/
│   ├── citologia/
│   ├── pap/
│   ├── reportes/
│   └── admin/
├── static/                 # Archivos estáticos
│   ├── css/
│   ├── js/
│   ├── img/
│   └── uploads/
├── migrations/             # Scripts de migración
├── docs/                   # Documentación
└── backups/                # Respaldos
```

## Migración de Datos desde Access

Para migrar los datos desde las bases de datos Access existentes:

```bash
python migrations/migrar_desde_access.py
```

Este script migrará:
- Pacientes (Afiliados)
- Obras Sociales
- Prestadores
- Protocolos de Biopsias
- Protocolos de Citología
- Protocolos de PAP
- Plantillas predefinidas

**IMPORTANTE**: Realizar un backup antes de migrar.

## Roles y Permisos

El sistema incluye 5 roles por defecto:

- **Administrador**: Acceso completo al sistema
- **Médico Patólogo**: Puede crear y editar informes
- **Técnico de Laboratorio**: Puede ingresar muestras y datos básicos
- **Secretaría**: Puede gestionar pacientes y citas
- **Consulta**: Solo puede consultar informes (lectura)

## Configuración

Las configuraciones se gestionan desde:
- Admin → Configuración
- O directamente en la base de datos (tabla `configuracion`)

Configuraciones importantes:
- Datos del laboratorio (nombre, dirección, teléfono)
- Formato de números de protocolo
- Contadores automáticos

## Backup y Restauración

### Backup Manual

La base de datos está en: `ldh_database.db`

Para hacer backup:
```bash
copy ldh_database.db backups\backup_YYYY-MM-DD.db
```

### Backup Automático

(Funcionalidad a implementar)

## Desarrollo

### Agregar nuevas funcionalidades

1. Crear modelo en `models/`
2. Crear rutas en `routes/`
3. Crear templates en `templates/`
4. Actualizar base de datos si es necesario

### Modo Debug

El modo debug está activado por defecto en desarrollo. Para producción, editar `config.py` y establecer `DEBUG = False`.

## Seguridad

- Las contraseñas se almacenan hasheadas (bcrypt)
- Las sesiones tienen tiempo de expiración (8 horas por defecto)
- Sistema de auditoría registra operaciones críticas
- Protección CSRF en formularios
- Validación de permisos en cada operación

## Soporte y Documentación

- Documentación completa: `docs/`
- Esquema de base de datos: `ESQUEMA_BASE_DATOS.md`
- Bitácoras de sesiones: `BITACORA_*.md`

## Tecnologías Utilizadas

- **Backend**: Flask 3.0, SQLAlchemy 2.0
- **Frontend**: Bootstrap 5, jQuery
- **Base de Datos**: SQLite
- **Autenticación**: Flask-Login
- **PDFs**: ReportLab / WeasyPrint

## Licencia

(Definir según corresponda)

## Autor

Desarrollado para modernizar el sistema LDHv2 (1995-2025)

---

**Versión**: 1.0.0  
**Fecha**: Octubre 2025

