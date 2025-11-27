"""
Script para inicializar roles y permisos del sistema
"""
from extensions import db
from models.usuario import Rol, Permiso, RolPermiso


def init_roles_y_permisos():
    """Inicializa roles y permisos del sistema"""
    
    # ============================================================================
    # 1. CREAR ROLES
    # ============================================================================
    
    roles_data = [
        {'nombre': 'OSCAR', 'descripcion': 'Super administrador - Oculto', 'oculto': True},
        {'nombre': 'Administrador', 'descripcion': 'Administrador del sistema', 'oculto': False},
        {'nombre': 'Médico', 'descripcion': 'Médico patólogo - Crea y firma informes', 'oculto': False},
        {'nombre': 'Técnico', 'descripcion': 'Técnico de laboratorio - Procesamiento técnico', 'oculto': False},
        {'nombre': 'Secretaria', 'descripcion': 'Personal administrativo - Recepción y entrega', 'oculto': False},
        {'nombre': 'Contable', 'descripcion': 'Administración contable - Solo facturación', 'oculto': False},
        {'nombre': 'Solo Lectura', 'descripcion': 'Consulta únicamente - Sin exportar', 'oculto': False},
        {'nombre': 'Prestador', 'descripcion': 'Prestador externo - Acceso al portal', 'oculto': False},
        {'nombre': 'Entidades', 'descripcion': 'Entidad externa (hospital, sanatorio, clínica) - Portal con múltiples prestadores', 'oculto': False}
    ]
    
    roles = {}
    for rol_data in roles_data:
        rol = Rol.query.filter_by(nombre=rol_data['nombre']).first()
        if not rol:
            rol = Rol(**rol_data)
            db.session.add(rol)
            db.session.flush()
        roles[rol_data['nombre']] = rol
    
    db.session.commit()
    print(f'✓ {len(roles_data)} roles creados')
    
    # ============================================================================
    # 2. CREAR PERMISOS
    # ============================================================================
    
    permisos_data = [
        # Usuarios
        {'codigo': 'usuarios_ver', 'nombre': 'Ver usuarios', 'modulo': 'USUARIOS'},
        {'codigo': 'usuarios_crear', 'nombre': 'Crear usuarios', 'modulo': 'USUARIOS'},
        {'codigo': 'usuarios_editar', 'nombre': 'Editar usuarios', 'modulo': 'USUARIOS'},
        {'codigo': 'usuarios_eliminar', 'nombre': 'Eliminar usuarios', 'modulo': 'USUARIOS'},
        {'codigo': 'roles_gestionar', 'nombre': 'Gestionar roles y permisos', 'modulo': 'USUARIOS'},
        
        # Pacientes
        {'codigo': 'pacientes_ver', 'nombre': 'Ver pacientes', 'modulo': 'PACIENTES'},
        {'codigo': 'pacientes_crear', 'nombre': 'Crear pacientes', 'modulo': 'PACIENTES'},
        {'codigo': 'pacientes_editar', 'nombre': 'Editar pacientes', 'modulo': 'PACIENTES'},
        {'codigo': 'pacientes_eliminar', 'nombre': 'Eliminar pacientes', 'modulo': 'PACIENTES'},
        
        # Prestadores
        {'codigo': 'prestadores_ver', 'nombre': 'Ver prestadores', 'modulo': 'PRESTADORES'},
        {'codigo': 'prestadores_crear', 'nombre': 'Crear prestadores', 'modulo': 'PRESTADORES'},
        {'codigo': 'prestadores_editar', 'nombre': 'Editar prestadores', 'modulo': 'PRESTADORES'},
        {'codigo': 'prestadores_eliminar', 'nombre': 'Eliminar prestadores', 'modulo': 'PRESTADORES'},
        
        # Obras Sociales
        {'codigo': 'obras_sociales_ver', 'nombre': 'Ver obras sociales', 'modulo': 'OBRAS_SOCIALES'},
        {'codigo': 'obras_sociales_crear', 'nombre': 'Crear obras sociales', 'modulo': 'OBRAS_SOCIALES'},
        {'codigo': 'obras_sociales_editar', 'nombre': 'Editar obras sociales', 'modulo': 'OBRAS_SOCIALES'},
        {'codigo': 'obras_sociales_eliminar', 'nombre': 'Eliminar obras sociales', 'modulo': 'OBRAS_SOCIALES'},
        
        # Protocolos
        {'codigo': 'protocolos_ver', 'nombre': 'Ver protocolos', 'modulo': 'PROTOCOLOS'},
        {'codigo': 'protocolos_crear', 'nombre': 'Crear protocolos', 'modulo': 'PROTOCOLOS'},
        {'codigo': 'protocolos_editar', 'nombre': 'Editar protocolos', 'modulo': 'PROTOCOLOS'},
        {'codigo': 'protocolos_eliminar', 'nombre': 'Eliminar protocolos', 'modulo': 'PROTOCOLOS'},
        
        # Informes
        {'codigo': 'informes_ver', 'nombre': 'Ver informes', 'modulo': 'INFORMES'},
        {'codigo': 'informes_crear', 'nombre': 'Crear informes', 'modulo': 'INFORMES'},
        {'codigo': 'informes_editar', 'nombre': 'Editar informes', 'modulo': 'INFORMES'},
        {'codigo': 'informes_firmar', 'nombre': 'Firmar informes', 'modulo': 'INFORMES'},
        {'codigo': 'informes_pdf', 'nombre': 'Generar PDFs', 'modulo': 'INFORMES'},
        {'codigo': 'informes_imprimir', 'nombre': 'Imprimir informes', 'modulo': 'INFORMES'},
        
        # Contable
        {'codigo': 'contable_acceso', 'nombre': 'Acceso módulo contable', 'modulo': 'CONTABLE'},
        {'codigo': 'contable_facturacion', 'nombre': 'Generar facturación', 'modulo': 'CONTABLE'},
        {'codigo': 'contable_reportes', 'nombre': 'Reportes contables', 'modulo': 'CONTABLE'},
        
        # Reportes
        {'codigo': 'reportes_ver', 'nombre': 'Ver reportes', 'modulo': 'REPORTES'},
        {'codigo': 'reportes_avanzados', 'nombre': 'Reportes avanzados', 'modulo': 'REPORTES'},
        
        # Administración
        {'codigo': 'admin_acceso', 'nombre': 'Acceso panel admin', 'modulo': 'ADMIN'},
        {'codigo': 'admin_configuracion', 'nombre': 'Modificar configuración', 'modulo': 'ADMIN'},
        {'codigo': 'admin_auditoria', 'nombre': 'Ver auditoría', 'modulo': 'ADMIN'},
    ]
    
    permisos = {}
    for perm_data in permisos_data:
        permiso = Permiso.query.filter_by(codigo=perm_data['codigo']).first()
        if not permiso:
            permiso = Permiso(**perm_data)
            db.session.add(permiso)
            db.session.flush()
        permisos[perm_data['codigo']] = permiso
    
    db.session.commit()
    print(f'✓ {len(permisos_data)} permisos creados')
    
    # ============================================================================
    # 3. ASIGNAR PERMISOS A ROLES
    # ============================================================================
    
    # Limpiar asignaciones existentes
    RolPermiso.query.delete()
    
    # OSCAR - TODOS LOS PERMISOS (Super-admin oculto)
    for codigo_permiso in permisos.keys():
        asignar_permiso(roles['OSCAR'], permisos[codigo_permiso])
    
    # ADMINISTRADOR - TODOS LOS PERMISOS (menos algunos reservados)
    for codigo_permiso in permisos.keys():
        asignar_permiso(roles['Administrador'], permisos[codigo_permiso])
    
    # MÉDICO
    permisos_medico = [
        'pacientes_ver', 'prestadores_ver', 'obras_sociales_ver',
        'protocolos_ver', 'protocolos_crear', 'protocolos_editar',
        'informes_ver', 'informes_crear', 'informes_editar', 'informes_firmar',
        'informes_pdf', 'informes_imprimir',
        'reportes_ver', 'reportes_avanzados'
    ]
    for codigo in permisos_medico:
        asignar_permiso(roles['Médico'], permisos[codigo])
    
    # TÉCNICO
    permisos_tecnico = [
        'pacientes_ver', 'pacientes_crear', 'pacientes_editar',
        'prestadores_ver', 'prestadores_crear', 'prestadores_editar',
        'obras_sociales_ver', 'obras_sociales_crear', 'obras_sociales_editar',
        'protocolos_ver', 'protocolos_crear', 'protocolos_editar',
        'informes_ver',
        'reportes_ver'
    ]
    for codigo in permisos_tecnico:
        asignar_permiso(roles['Técnico'], permisos[codigo])
    
    # SECRETARIA (Recepción principal)
    permisos_secretaria = [
        'pacientes_ver', 'pacientes_crear', 'pacientes_editar',
        'prestadores_ver', 'prestadores_crear', 'prestadores_editar',
        'obras_sociales_ver', 'obras_sociales_crear', 'obras_sociales_editar',
        'protocolos_ver', 'protocolos_crear',  # Puede crear protocolos (recepción)
        'informes_ver', 'informes_pdf', 'informes_imprimir',
        'contable_acceso', 'contable_facturacion', 'contable_reportes',
        'reportes_ver'
    ]
    for codigo in permisos_secretaria:
        asignar_permiso(roles['Secretaria'], permisos[codigo])
    
    # CONTABLE
    permisos_contable = [
        'pacientes_ver', 'prestadores_ver', 'obras_sociales_ver',
        'protocolos_ver',
        'contable_acceso', 'contable_facturacion', 'contable_reportes'
    ]
    for codigo in permisos_contable:
        asignar_permiso(roles['Contable'], permisos[codigo])
    
    # SOLO LECTURA
    permisos_lectura = [
        'pacientes_ver', 'prestadores_ver', 'obras_sociales_ver',
        'protocolos_ver', 'informes_ver'
    ]
    for codigo in permisos_lectura:
        asignar_permiso(roles['Solo Lectura'], permisos[codigo])
    
    # PRESTADOR - Acceso al portal para ver sus protocolos completados
    permisos_prestador = [
        'protocolos_ver', 'informes_ver', 'informes_pdf', 'informes_imprimir'
    ]
    for codigo in permisos_prestador:
        asignar_permiso(roles['Prestador'], permisos[codigo])
    
    # ENTIDADES - Mismo acceso que prestador pero puede ver protocolos de múltiples prestadores asociados
    permisos_entidades = [
        'protocolos_ver', 'informes_ver', 'informes_pdf', 'informes_imprimir'
    ]
    for codigo in permisos_entidades:
        asignar_permiso(roles['Entidades'], permisos[codigo])
    
    db.session.commit()
    print('✓ Permisos asignados a roles')
    
    # Resumen
    print('\n' + '='*60)
    print('RESUMEN DE PERMISOS POR ROL:')
    print('='*60)
    for rol_nombre, rol in roles.items():
        permisos_rol = RolPermiso.query.filter_by(rol_id=rol.rol_id).count()
        oculto_str = "(OCULTO)" if rol.oculto else ""
        print(f'  {rol_nombre:20} {oculto_str:10} → {permisos_rol} permisos')
    print('='*60)


def asignar_permiso(rol, permiso):
    """Asigna un permiso a un rol si no existe ya"""
    existe = RolPermiso.query.filter_by(
        rol_id=rol.rol_id,
        permiso_id=permiso.permiso_id
    ).first()
    
    if not existe:
        asignacion = RolPermiso(
            rol_id=rol.rol_id,
            permiso_id=permiso.permiso_id
        )
        db.session.add(asignacion)

