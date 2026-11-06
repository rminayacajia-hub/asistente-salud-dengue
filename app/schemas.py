"""Esquemas (Pydantic) de lo que ENTRA al sistema y de lo que el MODELO debe devolver.

Reglas para que el esquema funcione con el modo estricto de Gemini y Groq:
  - extra="forbid" en cada modelo (no se aceptan campos inventados).
  - Todos los campos son obligatorios; si algo puede faltar, use `tipo | None`.
  - Nada de límites raros en el esquema (minLength, pattern…): esas reglas van en
    validadores de Python. El esquema GUÍA al modelo; la validación la hace su código.
"""
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Estricto(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ======================================================================
# MODELOS DE DIAGNÓSTICO Y SALUD DEL SERVICIO
# ======================================================================
class HealthResponse(BaseModel):
    """Esquema de verificación de estado y observabilidad del servicio."""
    estado: str = Field(default="ok", description="Estado operativo del servicio")
    status: str = Field(default="ok", description="Alias de compatibilidad")
    service: str = Field(default="asistente-dengue-backend", description="Identificador del servicio")
    version: str = Field(default="1.0.0", description="Versión semántica del release")
    environment: str = Field(default="development", description="Entorno de ejecución")
    timestamp: str = Field(..., description="Marca de tiempo en formato ISO 8601 UTC")


# ======================================================================
# EJEMPLO TRABAJADO · Caso 03 · Triaje de soporte (compatibilidad kit)
# ======================================================================
class Solicitud(BaseModel):
    """Lo que envía el usuario. Límite de tamaño = defensa contra consumo excesivo (OWASP LLM10)."""
    texto: str = Field(min_length=5, max_length=2000, description="Descripción del problema")


class Clasificacion(Estricto):
    """Lo que el MODELO debe devolver en el ejemplo de soporte."""
    es_soporte_tecnologico: bool = Field(description="false si la solicitud no es de soporte TI")
    categoria: Literal["hardware", "software", "red", "accesos", "otro"]
    impacto: Literal["bajo", "medio", "alto"] = Field(description="A cuántas personas o procesos afecta")
    urgencia: Literal["baja", "media", "alta"] = Field(description="Qué tan pronto hay que resolverlo")
    resumen: str = Field(description="Una sola oración, sin datos personales")
    datos_faltantes: list[str] = Field(description="Qué habría que preguntarle al usuario; lista vacía si nada")

    @field_validator("resumen")
    @classmethod
    def resumen_corto(cls, v: str) -> str:
        if len(v) > 300:
            raise ValueError("el resumen debe tener máximo 300 caracteres")
        return v


PRIORIDAD = {  # decisión DETERMINISTA: la toma el código, no el modelo
    ("alto", "alta"): "P1", ("alto", "media"): "P2", ("medio", "alta"): "P2",
    ("alto", "baja"): "P3", ("medio", "media"): "P3", ("bajo", "alta"): "P3",
}


def calcular_prioridad(c: Clasificacion) -> str:
    return PRIORIDAD.get((c.impacto, c.urgencia), "P4")


class RespuestaClasificar(BaseModel):
    clasificacion: Clasificacion | None
    prioridad: str | None
    requiere_revision_humana: bool
    mensaje: str
    proveedor: str | None = None


# ======================================================================
# CASO 05 · ASISTENTE CONVERSACIONAL EN SALUD PÚBLICA (DENGUE)
# ======================================================================
class MensajeHistorial(BaseModel):
    """Mensaje previo en el hilo de conversación."""
    rol: Literal["user", "assistant"]
    contenido: str = Field(min_length=1, max_length=2000)


class SolicitudChat(BaseModel):
    """Mensaje del ciudadano hacia el asistente de salud."""
    mensaje: str = Field(min_length=2, max_length=2000, description="Consulta o síntomas descritos por el ciudadano")
    historial: list[MensajeHistorial] = Field(default_factory=list, description="Historial previo de la conversación")


class Fuente(Estricto):
    """
    Fuente oficial recuperada por RAG o GeoSalud (Semana 3).
    Cumple con el esquema de 5 metadatos obligatorios de la guía del Caso 05:
    id, documento, seccion, tema y anio.
    La llena el código en Python a partir de ChromaDB, NUNCA el LLM.
    """
    id: str | None = Field(default=None, description="Identificador canónico del fragmento (ej. ops-sec-01)")
    documento: str = Field(description="Nombre de la institución normativa emisora (OPS / MSP)")
    seccion: str | None = Field(default=None, description="Título canónico de la sección temática")
    tema: str | None = Field(default=None, description="Categoría temática: sintomas | prevencion | alarma | tratamiento")
    anio: str | None = Field(default=None, description="Año oficial de emisión normativa")


class RespuestaAsistente(Estricto):
    """Lo que el MODELO debe devolver · Casos 01 Titulación, 05 Dengue, 09 Cacao.
    OJO: aquí NO hay campo `fuentes`. Si se le pide al modelo, las INVENTA con
    títulos creíbles (alucinación). Las fuentes las agrega su endpoint en código:
        RespuestaChatAPI(**r.datos.model_dump(), fuentes=[], proveedor=r.proveedor)
    y en la semana 3 ese [] se reemplaza por los documentos que recuperó el RAG.
    """
    respuesta: str = Field(description="Orientación clara en salud pública sin jerga médica y sin prescribir")
    se_abstiene: bool = Field(description="true si la información no está en sus fuentes normativas o médicas")
    derivar_a: str | None = Field(description="Establecimiento de salud, hospital o ECU-911 al que debe acudir si hay signos de alarma")


class RespuestaChatAPI(BaseModel):
    """Respuesta final entregada por la API REST al usuario/frontend."""
    respuesta: str
    se_abstiene: bool
    derivar_a: str | None
    fuentes: list[Fuente] = Field(default_factory=list, description="Fuentes oficiales consultadas (RAG semana 3)")
    proveedor: str | None = Field(default=None, description="Proveedor LLM que generó la respuesta")
    alerta_signo_alarma: bool = Field(default=False, description="Indica si se activó la Regla de Oro determinista en Python")


# ======================================================================
# PUNTOS DE PARTIDA para las otras familias de casos (del kit estándar)
# ======================================================================
class Hallazgo(Estricto):
    titulo: str
    detalle: str
    gravedad: Literal["baja", "media", "alta"]


class AnalisisDocumento(Estricto):
    """Procesadores de documentos · casos 02 Reclamos, 06 Pliegos, 10 Código seguro."""
    resumen: str
    hallazgos: list[Hallazgo]
    datos_faltantes: list[str]
    advertencia: str | None = Field(description="Límites del análisis; no reemplaza a un profesional")


class Actividad(Estricto):
    hora: str = Field(description="HH:MM")
    lugar: str
    descripcion: str


class Dia(Estricto):
    numero: int
    actividades: list[Actividad]


class Plan(Estricto):
    """Planificadores · caso 04 Turismo.
    (07 Liquidaciones y 11 RIMPE: el modelo EXTRAE los datos; los CÁLCULOS van en código.)"""
    titulo: str
    dias: list[Dia]
    supuestos: list[str] = Field(description="Lo que el sistema asumió y el usuario debe confirmar")


class Opcion(Estricto):
    texto: str
    es_correcta: bool
    explicacion: str = Field(description="Por qué es correcta o incorrecta")


class Escenario(Estricto):
    """Simuladores · caso 08 Situaciones viales."""
    situacion: str
    pregunta: str
    opciones: list[Opcion]
    advertencia: str | None = Field(description="Recordatorio de que es material educativo")
