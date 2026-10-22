"""
Backend API - Asistente de Orientación en Salud Pública sobre Dengue y Arbovirosis.
Seminario de Titulación UNIANDES 2026 - Caso 05 (Grupo 5).

Idea de diseño: «El modelo propone, el código dispone».
El modelo orienta al ciudadano en lenguaje claro; las decisiones clínicas críticas
(detección de signos de alarma y derivación urgente) las toma el código determinista en Python.
"""
from datetime import datetime, timezone
from functools import lru_cache

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings
from app.schemas import (
    HealthResponse,
    Solicitud,
    RespuestaAsistente,
    Clasificacion,
    RespuestaClasificar,
    calcular_prioridad,
)
from app.services.llm import (
    ClienteLLM,
    ProveedorNoDisponible,
    SalidaInvalida,
    cargar_prompt,
)

# Metadatos del servicio y versión semántica
APP_NAME = "asistente-dengue-backend"
APP_VERSION = "1.0.0"

# Versión del prompt ganadora para orientación médica ciudadana
PROMPT_ASISTENTE = "system_v3"

# Inicialización de la aplicación FastAPI
app = FastAPI(
    title="Asistente de Orientación en Salud Pública (Dengue Ecuador)",
    description=(
        "API REST para la orientación ciudadana en dengue basada en guías oficiales "
        "del MSP y la OPS, con triaje determinista de signos de alarma y geolocalización de salud."
    ),
    version=APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configuración de CORS para integración con Frontend (Streamlit / Angular / Web)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@lru_cache
def obtener_llm() -> ClienteLLM:
    """Proveedor del servicio de IA (inyectable como dependencia de FastAPI)."""
    return ClienteLLM()


# ------------------------------------------------------------------------------
# 1. ENDPOINTS DE MONITOREO Y SALUD
# ------------------------------------------------------------------------------
@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Chequeo de salud del servicio",
    tags=["Monitoreo"],
)
def get_health() -> HealthResponse:
    """
    Endpoint de monitoreo de salud (Liveness / Readiness probe).
    Verifica que el servicio esté arriba y devuelve metadatos del entorno.
    """
    return HealthResponse(
        status="ok",
        estado="ok",
        environment=settings.APP_ENV,
        service=APP_NAME,
        version=APP_VERSION,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.get(
    "/",
    summary="Información raíz del servicio",
    tags=["General"],
)
def root():
    """Ruta raíz informativa con accesos directos a documentación."""
    return {
        "sistema": "Asistente de Orientación en Dengue y Arbovirosis (Ecuador)",
        "instituciones_fuente": ["MSP Ecuador", "OPS / OMS"],
        "estado": "operativo",
        "documentacion": "/docs",
        "salud": "/health",
        "chat": "/api/chat",
        "regla_oro_3": "Triaje y signos de alarma evaluados exclusivamente en código Python",
    }


# ------------------------------------------------------------------------------
# 2. ENDPOINT OFICIAL CASO 05: ASISTENTE CONVERSACIONAL DE DENGUE
# ------------------------------------------------------------------------------
# Signos de alarma canónicos de OPS 2016 y MSP Ecuador que fuerzan derivación inmediata
SIGNOS_ALARMA_CLAVE = (
    "dolor abdominal",
    "barriga",
    "vomit",
    "vomita",
    "vomito",
    "sangrad",
    "sangre",
    "encía",
    "nariz",
    "mareo",
    "desmay",
    "somnolen",
    "letargo",
    "irritab",
)


def _evaluar_regla_signos_alarma(texto: str, respuesta: RespuestaAsistente) -> RespuestaAsistente:
    """
    Regla de Oro en Python (ADR-004): Si el texto del ciudadano menciona signos de alarma,
    el código Python FUERZA la derivación médica urgente, sin dejar que el LLM lo omita.
    """
    texto_lower = texto.lower()
    detecto_alarma = any(s in texto_lower for s in SIGNOS_ALARMA_CLAVE)

    if detecto_alarma:
        # El código Python impone la derivación clínica inmediata
        respuesta.derivar_a = "Sala de Emergencias del Hospital más cercano o llamar al ECU-911 de inmediato"
    return respuesta


@app.post(
    "/api/chat",
    response_model=RespuestaAsistente,
    summary="Consulta ciudadana de orientación sobre dengue",
    tags=["Asistente Dengue"],
)
@app.post(
    "/chat",
    response_model=RespuestaAsistente,
    summary="Consulta ciudadana de orientación sobre dengue (alias)",
    tags=["Asistente Dengue"],
)
def chat(solicitud: Solicitud, llm: ClienteLLM = Depends(obtener_llm)) -> RespuestaAsistente:
    """
    Endpoint principal para interacción ciudadana:
    1. Valida el texto de entrada mediante Pydantic (límite de longitud anti-inyección).
    2. Carga el system prompt enjaulado de producción (system_v3.md).
    3. Invoca al ClienteLLM con tiempo límite, reintentos (backoff 429) y conmutación a respaldo.
    4. Aplica la regla determinista en Python para asegurar derivación inmediata ante signos de peligro.
    """
    try:
        resultado = llm.generar_json(
            cargar_prompt(PROMPT_ASISTENTE),
            solicitud.texto,
            RespuestaAsistente,
        )
    except ProveedorNoDisponible as e:
        # 503 claro y limpio para el ciudadano, sin exponer trazas técnicas internas
        raise HTTPException(status_code=503, detail=e.mensaje_usuario)
    except SalidaInvalida as e:
        # Si la salida del modelo fue irrecuperable, se envía a revisión humana
        return RespuestaAsistente(
            respuesta="No pudimos estructurar la respuesta automáticamente. Tu consulta ha sido enviada para revisión humana.",
            se_abstiene=True,
            derivar_a="Línea 171 del MSP para agendamiento médico",
            fuentes=[],
            proveedor=None,
        )

    respuesta_modelo: RespuestaAsistente = resultado.datos
    respuesta_modelo.proveedor = resultado.proveedor
    # Decisión del negocio determinista en Python puro
    return _evaluar_regla_signos_alarma(solicitud.texto, respuesta_modelo)


# ------------------------------------------------------------------------------
# 3. ENDPOINT COMPATIBILIDAD KIT: CLASIFICAR
# ------------------------------------------------------------------------------
@app.post(
    "/clasificar",
    response_model=RespuestaClasificar,
    summary="Clasificación de solicitudes (compatibilidad con suite de pruebas)",
    tags=["Soporte Kit"],
)
def clasificar(solicitud: Solicitud, llm: ClienteLLM = Depends(obtener_llm)):
    """Endpoint de ejemplo y compatibilidad con las pruebas unitarias del kit."""
    try:
        r = llm.generar_json(cargar_prompt(PROMPT_ASISTENTE), solicitud.texto, Clasificacion)
    except ProveedorNoDisponible as e:
        raise HTTPException(status_code=503, detail=e.mensaje_usuario)
    except SalidaInvalida as e:
        return RespuestaClasificar(
            clasificacion=None,
            prioridad=None,
            requiere_revision_humana=True,
            mensaje=e.mensaje_usuario,
        )
    c = r.datos
    if not c.es_soporte_tecnologico:
        return RespuestaClasificar(
            clasificacion=c,
            prioridad=None,
            requiere_revision_humana=False,
            mensaje="Esta solicitud no es de soporte tecnológico. Escríbele a Talento Humano.",
            proveedor=r.proveedor,
        )
    return RespuestaClasificar(
        clasificacion=c,
        prioridad=calcular_prioridad(c),
        requiere_revision_humana=False,
        mensaje="Solicitud registrada.",
        proveedor=r.proveedor,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG,
    )
