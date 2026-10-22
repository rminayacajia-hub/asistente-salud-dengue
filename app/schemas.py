"""
Esquemas de Datos Pydantic para el Asistente de Orientación en Dengue.
Define contratos estrictos para validación de entrada/salida y serialización UTF-8.
"""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator


class HealthResponse(BaseModel):
    """Esquema de respuesta para monitoreo de salud del backend (GET /health)."""
    status: str = Field(default="ok", description="Estado operativo del servicio")
    estado: str = Field(default="ok", description="Compatibilidad con el estándar del kit del seminario")
    environment: str = Field(description="Entorno de ejecución (development / production)")
    service: str = Field(default="asistente-dengue-backend", description="Identificador del microservicio")
    version: str = Field(default="1.0.0", description="Versión semántica del API")
    timestamp: str = Field(description="Marca de tiempo ISO-8601 del chequeo")


class FuenteReferencia(BaseModel):
    """Cita formal de documento oficial normativo (Regla de Oro 1)."""
    documento: str = Field(..., description="Nombre formal del documento oficial (MSP / OPS)")
    origen: str = Field(..., description="Institución emisora (ej. Ministerio de Salud Pública / OPS OMS)")
    seccion_o_pagina: str = Field(..., description="Acápite, tabla, capítulo o número de página oficial")
    url: str = Field(..., description="Permalink o URL institucional de verificación")


class ChatRequest(BaseModel):
    """Petición de interacción conversacional del ciudadano."""
    mensaje: str = Field(..., min_length=1, max_length=1000, description="Texto de la consulta del usuario")
    conversacion_id: Optional[str] = Field(default=None, description="Identificador anónimo de sesión")
    ciudad: Optional[str] = Field(default=None, max_length=100, description="Ciudad o cantón del usuario")

    @field_validator("mensaje")
    @classmethod
    def validar_no_vacio(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("El mensaje de consulta no puede estar vacío.")
        return stripped


class ChatResponse(BaseModel):
    """Respuesta generada con citas oficiales y salvaguardas éticas."""
    respuesta: str = Field(..., description="Texto sintetizado en lenguaje ciudadano claro")
    fuentes: List[FuenteReferencia] = Field(
        default_factory=list,
        description="Lista de fuentes oficiales que sustentan la afirmación (Regla 1)"
    )
    derivacion_emergencia: bool = Field(
        default=False,
        description="Indica si la respuesta activa protocolo urgente de traslado o 911"
    )
    aviso_seguridad: Optional[str] = Field(
        default="Orientación en salud pública. No reemplaza el diagnóstico médico ni prescribe fármacos. No automedicarse con AINEs.",
        description="Advertencia médica obligatoria al pie de la interacción"
    )


class ChecklistInput(BaseModel):
    """
    Entrada estructurada para el triaje determinista de signos de alarma.
    Basado en las guías canónicas de OPS 2016 / MSP Ecuador.
    """
    dolor_abdominal_continuo: bool = Field(
        default=False,
        description="Dolor abdominal intenso y continuo o dolor a la palpación del abdomen"
    )
    vomitos_persistentes: bool = Field(
        default=False,
        description="Vómitos frecuentes o reiterados (3 o más episodios en pocas horas)"
    )
    acumulacion_liquidos: bool = Field(
        default=False,
        description="Evidencia clínica de acumulación de líquidos (edema, ascitis o derrame)"
    )
    sangrado_mucosas: bool = Field(
        default=False,
        description="Sangrado espontáneo de encías, nariz o hematomas anormales"
    )
    letargo_irritabilidad: bool = Field(
        default=False,
        description="Somnolencia excesiva, confusión mental, decaimiento extremo o irritabilidad"
    )
    mareo_postural: bool = Field(
        default=False,
        description="Mareo intenso o desmayo al ponerse de pie (hipotensión postural)"
    )
    hepatomegalia_dolorosa: bool = Field(
        default=False,
        description="Hígado agrandado (> 2 cm bajo reborde costal) / molestia en hipocondrio derecho"
    )
    tiene_fiebre: bool = Field(
        default=False,
        description="Presencia de fiebre o antecedentes de fiebre en los últimos 2 a 7 días"
    )
    ciudad: Optional[str] = Field(
        default=None,
        description="Ciudad del usuario para georreferenciación de emergencia inmediata"
    )


class EstablecimientoSalud(BaseModel):
    """
    Establecimiento de salud georreferenciado (GeoSalud Ecuador / MSP).
    Garantiza compatibilidad bidireccional con el dataset geosalud_ecuador.json.
    """
    model_config = ConfigDict(populate_by_name=True)

    id: Optional[str] = Field(default=None, description="Código de identificación del establecimiento")
    provincia: Optional[str] = Field(default=None, description="Provincia donde se ubica el centro")
    ciudad: str = Field(..., description="Cantón o ciudad")
    nombre: str = Field(..., description="Nombre formal del hospital o centro de salud")
    nivel: Optional[str] = Field(default=None, description="Nivel de atención (Primer, Segundo o Tercer Nivel)")
    tipo: str = Field(..., description="Tipología (Centro Tipo C, Hospital Básico, General o Especializado)")
    direccion: str = Field(..., description="Dirección física o referencia del establecimiento")
    telefono: str = Field(..., description="Número de teléfono de urgencias o recepción")
    emergencia_24h: bool = Field(
        default=True,
        alias="servicio_emergencia_24h",
        description="Disponibilidad de servicio de emergencia activo las 24 horas"
    )
    capacidad_critica: List[str] = Field(
        default_factory=list,
        description="Servicios clínicos clave (UCI, Laboratorio Viral, Rehidratación rápida)"
    )


class TriajeOutput(BaseModel):
    """Resultado determinista del triaje médico algorítmico."""
    clasificacion: str = Field(
        ...,
        description="Categoría clínica: 'EMERGENCIA_CRITICA', 'MONITOREO_AMBULATORIO' o 'PREVENCION_GENERAL'"
    )
    alerta_inmediata: bool = Field(
        ...,
        description="True si se detectó al menos un signo de alarma oficial (cero falsos negativos)"
    )
    signos_detectados: List[str] = Field(
        default_factory=list,
        description="Nombres legibles de los signos de alarma identificados en la evaluación"
    )
    accion_recomendada: str = Field(
        ...,
        description="Instrucción prioritaria y clara para el usuario o cuidador"
    )
    establecimientos_cercanos: List[EstablecimientoSalud] = Field(
        default_factory=list,
        description="Establecimientos oficiales recomendados por cercanía geográfica"
    )


# ==============================================================================
# INTEGRACIÓN DEL KIT DE IA (SEMANA 2) - ESQUEMAS ESTRICTOS Y VALIDADOS
# ==============================================================================

class Estricto(BaseModel):
    """
    Clase base con modo estricto: prohíbe atributos no declarados (extra="forbid").
    Evita que el LLM alucine campos fuera del contrato estructurado.
    """
    model_config = ConfigDict(extra="forbid")


# ------------------------------------------------------------------------------
# 1. ESQUEMAS UTILIZADOS POR LAS PRUEBAS UNITARIAS DEL KIT (tests/test_llm.py)
# ------------------------------------------------------------------------------
class Solicitud(BaseModel):
    """Contenedor de entrada con límite de caracteres para prevenir ataques de inyección."""
    texto: str = Field(min_length=5, max_length=2000, description="Texto de la consulta del usuario")


class Clasificacion(Estricto):
    """Esquema de salida utilizado para validar el comportamiento del ClienteLLM."""
    es_soporte_tecnologico: bool = Field(description="False si la solicitud no pertenece al ámbito")
    categoria: Literal["hardware", "software", "red", "accesos", "otro"]
    impacto: Literal["bajo", "medio", "alto"] = Field(description="Nivel de impacto en la operación")
    urgencia: Literal["baja", "media", "alta"] = Field(description="Nivel de urgencia requerido")
    resumen: str = Field(description="Resumen de una sola oración sin datos personales")
    datos_faltantes: list[str] = Field(description="Datos que faltan para procesar")

    @field_validator("resumen")
    @classmethod
    def resumen_corto(cls, v: str) -> str:
        if len(v) > 300:
            raise ValueError("El resumen debe tener máximo 300 caracteres")
        return v


# Matriz determinista de cálculo de prioridad (regla en Python puro, nunca en el modelo)
PRIORIDAD = {
    ("alto", "alta"): "P1", ("alto", "media"): "P2", ("medio", "alta"): "P2",
    ("alto", "baja"): "P3", ("medio", "media"): "P3", ("bajo", "alta"): "P3",
}


def calcular_prioridad(c: Clasificacion) -> str:
    """Calcula la prioridad determinista basada en impacto y urgencia."""
    return PRIORIDAD.get((c.impacto, c.urgencia), "P4")


class RespuestaClasificar(BaseModel):
    """Esquema de respuesta devuelto por el endpoint de soporte del kit."""
    clasificacion: Clasificacion | None
    prioridad: str | None
    requiere_revision_humana: bool
    mensaje: str
    proveedor: str | None = None


# Esquemas complementarios de soporte para pruebas de integración con servidor simulado
class Actividad(Estricto):
    hora: str = Field(description="HH:MM")
    lugar: str
    descripcion: str


class Dia(Estricto):
    numero: int
    actividades: list[Actividad]


class Plan(Estricto):
    titulo: str
    dias: list[Dia]
    supuestos: list[str] = Field(description="Lo que el sistema asumió y el usuario debe confirmar")


# ------------------------------------------------------------------------------
# 2. ESQUEMA OFICIAL PARA NUESTRO CASO 05: ASISTENTE DE DENGUE (UNIANDES 2026)
# ------------------------------------------------------------------------------
class Fuente(Estricto):
    """Referencia documental oficial (MSP / OPS) citada por el asistente."""
    documento: str = Field(description="Nombre oficial del documento normativo")
    seccion: str | None = Field(description="Capítulo, acápite o tabla de referencia; null si no aplica")


class RespuestaAsistente(Estricto):
    """
    Esquema de salida oficial del modelo para el Asistente de Orientación en Dengue.
    Garantiza:
      1. Orientación ciudadana clara en salud pública.
      2. Cero prescripción farmacológica (no recomienda medicamentos ni AINEs).
      3. Detección de abstención cuando la pregunta escapa a las guías oficiales.
      4. Derivación médica urgente cuando se sospechen signos de alarma.
      5. Compatibilidad total con Swagger UI (/docs) e interoperabilidad FastAPI.
    """
    respuesta: str = Field(description="Orientación clara para el ciudadano")
    se_abstiene: bool = Field(description="True si la información no está en las guías oficiales del MSP/OPS")
    derivar_a: str | None = Field(description="Establecimiento de salud, ECU-911 o médico si corresponde; null si no aplica")
    fuentes: list[Fuente] = Field(description="Citas oficiales que respaldan la orientación")
    proveedor: str | None = Field(description="Proveedor del modelo (gemini | groq); null si no aplica")
