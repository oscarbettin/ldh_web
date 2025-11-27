-- Script SQL para aplicar cambios de esquema en PythonAnywhere
-- Ejecutar estos comandos en la base de datos de producción

-- ============================================
-- CAMBIOS EN TABLA protocolos
-- ============================================

-- Agregar campo prestador_medico_id (si no existe)
-- Verificar primero si existe la columna antes de agregarla
-- En SQLite no hay ALTER COLUMN IF NOT EXISTS, así que si ya existe dará error pero no pasa nada

-- Agregar prestador_medico_id a protocolos
ALTER TABLE protocolos ADD COLUMN prestador_medico_id INTEGER REFERENCES prestadores(prestador_id);

-- Agregar campos de control a protocolos (si no existen)
ALTER TABLE protocolos ADD COLUMN con_orden BOOLEAN DEFAULT 0;
ALTER TABLE protocolos ADD COLUMN entregado BOOLEAN DEFAULT 0;
ALTER TABLE protocolos ADD COLUMN cobrado BOOLEAN DEFAULT 0;

-- ============================================
-- CAMBIOS EN TABLA prestadores
-- ============================================

-- Agregar campo es_entidad (si no existe)
ALTER TABLE prestadores ADD COLUMN es_entidad BOOLEAN DEFAULT 0;

-- Agregar campos de visibilidad (si no existen)
ALTER TABLE prestadores ADD COLUMN puede_ver_ambulatorio BOOLEAN DEFAULT 1;
ALTER TABLE prestadores ADD COLUMN puede_ver_internacion BOOLEAN DEFAULT 1;

-- Agregar campos de notificaciones (si no existen)
ALTER TABLE prestadores ADD COLUMN notificar_email BOOLEAN DEFAULT 0;
ALTER TABLE prestadores ADD COLUMN notificar_whatsapp BOOLEAN DEFAULT 0;
ALTER TABLE prestadores ADD COLUMN notificar_ambulatorio BOOLEAN DEFAULT 0;
ALTER TABLE prestadores ADD COLUMN notificar_internacion BOOLEAN DEFAULT 0;
ALTER TABLE prestadores ADD COLUMN whatsapp VARCHAR(20);

-- ============================================
-- ÍNDICES (opcional, para mejorar rendimiento)
-- ============================================

-- Índice para prestador_medico_id
CREATE INDEX IF NOT EXISTS idx_protocolos_prestador_medico ON protocolos(prestador_medico_id);

-- Índice para es_entidad en prestadores
CREATE INDEX IF NOT EXISTS idx_prestadores_es_entidad ON prestadores(es_entidad);

-- ============================================
-- VERIFICACIÓN
-- ============================================

-- Para verificar que los cambios se aplicaron, ejecuta:
-- PRAGMA table_info(protocolos);
-- PRAGMA table_info(prestadores);

