# 🚀 INICIO RÁPIDO - LDH Web

## ¿Qué se ha creado?

Se ha desarrollado la **estructura completa** de una aplicación web moderna para reemplazar el sistema LDHv2 de Access, con:

✅ Sistema de autenticación multiusuario  
✅ Dashboard con estadísticas  
✅ Gestión de pacientes  
✅ Bases de datos SQL normalizada  
✅ 18 modelos de datos  
✅ 10 módulos (blueprints)  
✅ Interfaz moderna con Bootstrap 5  

## 🎯 Pasos para probar el sistema

### 1️⃣ Instalar dependencias

```bash
cd C:\LDH\LDH_Web
pip install -r requirements.txt
```

### 2️⃣ Crear la base de datos

```bash
python -m flask --app app initdb
```

Esto creará:
- Base de datos SQLite
- Roles de usuario
- Usuario administrador (admin/admin123)

### 3️⃣ Ejecutar la aplicación

```bash
python app.py
```

### 4️⃣ Abrir en el navegador

```
http://localhost:5000
```

**Usuario:** admin  
**Contraseña:** admin123

## 📊 ¿Qué funciona ahora?

✅ **Login/Logout** - Sistema de autenticación completo  
✅ **Dashboard** - Vista general con estadísticas  
✅ **Pacientes** - CRUD completo (crear, editar, listar)  
⚙️ **Otros módulos** - Estructura base creada  

## 📁 Estructura del proyecto

```
LDH_Web/
├── app.py              ← Aplicación principal
├── config.py           ← Configuración
├── requirements.txt    ← Dependencias
├── models/            ← Modelos de base de datos
├── routes/            ← Rutas/controladores
├── templates/         ← Plantillas HTML
├── static/            ← CSS, JS, imágenes
└── docs/              ← Documentación
```

## 📚 Documentación disponible

- **README.md** - Guía completa del sistema
- **docs/ESQUEMA_BASE_DATOS.md** - Estructura de la BD
- **docs/BITACORA_SESION_2025-10-10.md** - Registro detallado de desarrollo

## 🔄 Próximos pasos

1. **Migración de datos** - Traer datos desde Access
2. **Completar templates** - Todas las pantallas HTML
3. **Módulos de protocolos** - Biopsias, Citología, PAP
4. **Generación de PDFs** - Informes en PDF
5. **Plantillas PAP** - Sistema de selección rápida

## ⚠️ Importante

- El sistema está en fase de desarrollo
- Los datos de Access NO se modifican
- Primero completar la estructura, luego migrar datos
- Cambiar la contraseña del admin en primer uso

## 💡 ¿Necesitas ayuda?

Consulta la documentación en la carpeta `docs/` o revisa la bitácora de sesión para ver todos los detalles del desarrollo.

---

**Estado:** Base del sistema completa (40%)  
**Última actualización:** 10/10/2025

