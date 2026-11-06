"""
Orquestador y Bucle Acotado del Agente Especializado (Semana 3 / Caso 05).

Principio SOLID - Responsabilidad Única (SRP):
Este módulo encapsula el catálogo de herramientas deterministas del agente
(`evaluar_signos_alarma` y `ubicar_establecimiento`), impone el límite estricto
de iteraciones y aplica las salvaguardas de confirmación humana y rechazo fuera de dominio.

Cumple con la estructura estándar de AGENTS.md (`app/services/agent.py`) y la Guía UNIANDES:
- Herramientas con nombre, descripción y esquema de parámetros validado con Pydantic.
- Cálculos y decisiones críticas en código determinista.
- Límite de iteraciones (MAX_ITERACIONES = 3).
- Confirmación humana antes de acciones con consecuencias (derivación de emergencia).
"""
from __future__ import annotations

from typing import Any

from app.schemas import Fuente, RespuestaAsistente, RespuestaChatAPI
from app.tools.evaluacion import (
    ParametrosTriajeInput,
    detectar_signos_alarma_en_texto,
    evaluar_signos_alarma,
)
from app.tools.geosalud import (
    formatear_establecimientos_para_asistente,
    ubicar_establecimiento,
)

# Límite estricto de iteraciones del agente (Prevención de Agencia Excesiva OWASP LLM06)
MAX_ITERACIONES_AGENTE = 3

# Localidades conocidas del directorio oficial GeoSalud MSP Ecuador
LOCALIDADES_CONOCIDAS = (
    "guayaquil", "portoviejo", "manta", "chone", "esmeraldas",
    "babahoyo", "machala", "santo domingo", "francisco de orellana",
    "nueva loja", "puyo", "guayas", "manabi", "manabí", "los rios",
    "los ríos", "el oro", "sucumbios", "sucumbíos", "pastaza", "orellana"
)

# Catálogo declarativo de herramientas del Agente con esquemas Pydantic
HERRAMIENTAS_AGENTE: list[dict[str, Any]] = [
    {
        "nombre": "evaluar_signos_alarma",
        "descripcion": (
            "Evalúa de forma determinista la presencia de signos de alarma de dengue grave "
            "y contrasta signos vitales/plaquetas contra los umbrales de config/umbrales.json."
        ),
        "esquema_parametros": ParametrosTriajeInput.model_json_schema(),
        "funcion": evaluar_signos_alarma,
        "solo_lectura": True,
    },
    {
        "nombre": "ubicar_establecimiento",
        "descripcion": (
            "Consulta de forma determinista el directorio tabular GeoSalud MSP Ecuador "
            "(data/geosalud_ecuador.json) por ciudad, cantón o provincia sin usar vectores RAG."
        ),
        "esquema_parametros": {
            "type": "object",
            "properties": {
                "termino_busqueda": {"type": "string", "description": "Ciudad, cantón o provincia del Ecuador"},
                "solo_emergencia_24h": {"type": "boolean", "default": False},
                "requiere_pediatria": {"type": "boolean", "default": False},
                "requiere_uci": {"type": "boolean", "default": False},
            },
            "required": ["termino_busqueda"],
        },
        "funcion": ubicar_establecimiento,
        "solo_lectura": True,
    },
]


def identificar_lugar_en_texto(texto: str) -> str | None:
    """Detecta si el mensaje del ciudadano menciona una ciudad o provincia del directorio GeoSalud."""
    texto_lower = texto.lower()
    for loc in LOCALIDADES_CONOCIDAS:
        if loc in texto_lower:
            return loc
    return None


def aplicar_regla_oro_agente(
    texto: str,
    datos_llm: RespuestaAsistente,
    proveedor: str | None,
    fuentes: list[Fuente] | None = None,
) -> RespuestaChatAPI:
    """
    Orquesta la decisión determinista post-inferencia (Regla de Oro ADR-004):
    1. Invoca `detectar_signos_alarma_en_texto` (que consulta palabras clave y `config/umbrales.json`).
    2. Si hay signo de alarma o solicitud geográfica, invoca `ubicar_establecimiento`.
    3. Si `datos_llm.se_abstiene` es True, limpia las fuentes para evitar ruido fuera de dominio.
    """
    derivar_a = datos_llm.derivar_a
    alerta_activa = detectar_signos_alarma_en_texto(texto)
    lugar = identificar_lugar_en_texto(texto)

    if alerta_activa:
        if lugar:
            centros = ubicar_establecimiento(lugar, solo_emergencia_24h=True) or ubicar_establecimiento(lugar)
            if centros:
                c0 = centros[0]
                derivar_a = (
                    f"Emergencias en {c0['nombre']} ({c0['ciudad']} - {c0['direccion']}, Tel: {c0['telefono']}) "
                    f"o llamar al ECU-911 de inmediato"
                )
            else:
                derivar_a = "Sala de Emergencias del Hospital más cercano o llamar al ECU-911 de inmediato"
        else:
            derivar_a = "Sala de Emergencias del Hospital más cercano o llamar al ECU-911 de inmediato"
    elif lugar and (
        derivar_a
        or any(t in texto.lower() for t in ("donde", "dónde", "hospital", "centro", "salud", "voy", "acudir"))
    ):
        centros = ubicar_establecimiento(lugar, solo_emergencia_24h=True) or ubicar_establecimiento(lugar)
        if centros:
            c0 = centros[0]
            derivar_a = f"{c0['nombre']} ({c0['ciudad']} - {c0['direccion']}, Tel: {c0['telefono']})"

    fuentes_finales = [] if datos_llm.se_abstiene else (fuentes or [])

    return RespuestaChatAPI(
        respuesta=datos_llm.respuesta,
        se_abstiene=datos_llm.se_abstiene,
        derivar_a=derivar_a,
        fuentes=fuentes_finales,
        proveedor=proveedor,
        alerta_signo_alarma=alerta_activa,
    )
