"""
Esquemas de Datos Pydantic para el Asistente de Orientación en Dengue.
Define contratos estrictos para validación de entrada/salida y serialización UTF-8.
"""
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator


class HealthResponse(BaseModel):
    """Esquema de respuesta para monitoreo de salud del backend (GET /health)."""
    status: str = Field(default="ok", description="Estado operativo del servicio")
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
