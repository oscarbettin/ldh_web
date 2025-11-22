"""
Modelos de datos para LDH Web
"""
from models.usuario import Usuario, Rol, Permiso, RolPermiso, UsuarioFirma
from models.paciente import Afiliado
from models.prestador import Prestador, Especialidad
from models.obra_social import ObraSocial, PlanFacturacion, PlanCategoria
from models.protocolo import Protocolo, TipoAnalisis
from models.informe import BiopsiaInforme, CitologiaInforme, PapInforme, PlantillaPap
from models.auditoria import Auditoria
from models.configuracion import Configuracion
from models.asistente import CasoHistorico, PlantillaTexto, FragmentoTexto, SugerenciaIA, ConfiguracionAsistente
from models.plantilla_dinamica import SeccionPlantilla, LineaPlantilla, ConfiguracionBotones, PlantillaGenerada
from models.plantilla_multilinea import PlantillaMultilinea, CasoHistoricoCompleto, SugerenciaInteligente
from models.configuracion_asistente import ConfiguracionAsistenteUsuario, PerfilAsistente, ConfiguracionAsistenteGlobal, LogUsoAsistente

__all__ = [
    'Usuario', 'Rol', 'Permiso', 'RolPermiso', 'UsuarioFirma',
    'Afiliado',
    'Prestador', 'Especialidad',
    'ObraSocial', 'PlanFacturacion', 'PlanCategoria',
    'Protocolo', 'TipoAnalisis',
    'BiopsiaInforme', 'CitologiaInforme', 'PapInforme', 'PlantillaPap',
    'Auditoria',
    'Configuracion',
    'CasoHistorico', 'PlantillaTexto', 'FragmentoTexto', 'SugerenciaIA', 'ConfiguracionAsistente',
    'SeccionPlantilla', 'LineaPlantilla', 'ConfiguracionBotones', 'PlantillaGenerada',
    'PlantillaMultilinea', 'CasoHistoricoCompleto', 'SugerenciaInteligente',
    'ConfiguracionAsistenteUsuario', 'PerfilAsistente', 'ConfiguracionAsistenteGlobal', 'LogUsoAsistente'
]

