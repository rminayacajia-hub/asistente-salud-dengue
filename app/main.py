"""
Backend API - Asistente de Orientación en Salud Pública sobre Dengue y Arbovirosis.
Seminario de Titulación UNIANDES 2026 - Caso 05 (Grupo 5).

Idea de diseño: «El modelo propone, el código dispone».
El modelo orienta al ciudadano en lenguaje claro; las decisiones clínicas críticas
(detección de signos de alarma y derivación urgente) las toma el código determinista en Python.
"""
from datetime import datetime, timezone
from functools import lru_cache
from typing import Iterator

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from config.settings import settings
from app.schemas import (
    HealthResponse,
    Solicitud,
    SolicitudChat,
    RespuestaAsistente,
    RespuestaChatAPI,
    Fuente,
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
from app.services.retriever import RecuperadorDengue
from app.tools.geosalud import (
    ubicar_establecimiento,
    formatear_establecimientos_para_asistente,
)

# Metadatos del servicio y versión semántica
APP_NAME = "asistente-dengue-backend"
APP_VERSION = "1.1.0"

# Versión del prompt ganadora para orientación médica ciudadana (con salvaguardas y prohibición de AINEs)
PROMPT_ASISTENTE = "system_v3"

# Inicialización de la aplicación FastAPI con documentación automática OpenAPI
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

# Configuración de CORS para permitir peticiones desde el Frontend (Streamlit / Web)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@lru_cache
def obtener_llm() -> ClienteLLM:
    """
    Proveedor del servicio de IA (Singleton inyectable como dependencia de FastAPI).
    Mantiene la conexión y configuración de clientes Gemini / Groq.
    """
    return ClienteLLM()


@lru_cache
def obtener_retriever() -> RecuperadorDengue:
    """
    Proveedor del servicio RAG (Singleton inyectable como dependencia de FastAPI).
    Mantiene la conexión persistente con la base vectorial ChromaDB y
    la recuperación semántica de fragmentos oficiales de la OPS y el MSP.
    """
    return RecuperadorDengue()


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
    Verifica que el servicio esté operativo y devuelve metadatos del entorno.
    """
    return HealthResponse(
        estado="ok",
        status="ok",
        version="1.0.0",
        service=APP_NAME,
        environment=settings.APP_ENV,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.get(
    "/",
    summary="Información raíz del servicio",
    tags=["General"],
)
def root():
    """
    Ruta raíz informativa con accesos directos a documentación y endpoints clave.
    """
    return {
        "sistema": "Asistente de Orientación en Dengue y Arbovirosis (Ecuador)",
        "instituciones_fuente": ["MSP Ecuador", "OPS / OMS"],
        "estado": "operativo",
        "documentacion": "/docs",
        "salud": "/health",
        "chat": "/api/chat",
        "chat_stream": "/api/chat/stream",
        "regla_oro": "Triaje y signos de alarma evaluados exclusivamente en código Python",
    }


# ------------------------------------------------------------------------------
# 2. LÓGICA CLÍNICA DETERMINISTA (REGLA DE ORO ADR-004)
# ------------------------------------------------------------------------------
# Palabras y lemas que corresponden a signos de alarma de dengue grave según la OPS y MSP
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

LOCALIDADES_CONOCIDAS = (
    "guayaquil", "portoviejo", "manta", "chone", "esmeraldas",
    "babahoyo", "machala", "santo domingo", "francisco de orellana",
    "nueva loja", "puyo", "guayas", "manabi", "manabí", "los rios",
    "los ríos", "el oro", "sucumbios", "sucumbíos", "pastaza", "orellana"
)


def _detectar_signos_alarma(texto: str) -> bool:
    """
    Verifica de forma estricta y determinista si la consulta del usuario
    contiene términos indicativos de alarma médica (dengue con signos de alarma).
    """
    texto_lower = texto.lower()
    return any(signo in texto_lower for signo in SIGNOS_ALARMA_CLAVE)


def _identificar_lugar_en_texto(texto: str) -> str | None:
    """
    Detecta si el mensaje del usuario menciona alguna ciudad o provincia
    del directorio GeoSalud Ecuador.
    """
    texto_lower = texto.lower()
    for loc in LOCALIDADES_CONOCIDAS:
        if loc in texto_lower:
            return loc
    return None


def _evaluar_regla_signos_alarma(
    texto: str,
    datos_llm: RespuestaAsistente,
    proveedor: str | None,
    fuentes: list[Fuente] | None = None,
) -> RespuestaChatAPI:
    """
    Regla de Oro en Python (ADR-004):
    Si el texto del ciudadano menciona signos de alarma, el código Python impone
    la derivación médica urgente, sin dejar que el LLM lo omita o suavice.
    Si el usuario mencionó su ciudad o cantón, ubica el centro de salud específico
    mediante la herramienta determinista GeoSalud.
    Inyecta deterministamente las fuentes recuperadas por el RAG y GeoSalud (Semana 3).
    """
    derivar_a = datos_llm.derivar_a
    alerta_activa = _detectar_signos_alarma(texto)
    lugar = _identificar_lugar_en_texto(texto)

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
    elif lugar and (derivar_a or any(t in texto.lower() for t in ("donde", "dónde", "hospital", "centro", "salud", "voy", "acudir"))):
        # Si no es alarma crítica pero el usuario pregunta dónde ir o se sugiere derivación en esa localidad
        centros = ubicar_establecimiento(lugar, solo_emergencia_24h=True) or ubicar_establecimiento(lugar)
        if centros:
            c0 = centros[0]
            derivar_a = f"{c0['nombre']} ({c0['ciudad']} - {c0['direccion']}, Tel: {c0['telefono']})"

    # Si el asistente se abstiene (fuera de dominio), no se adjuntan fuentes
    fuentes_finales = [] if datos_llm.se_abstiene else (fuentes or [])

    return RespuestaChatAPI(
        respuesta=datos_llm.respuesta,
        se_abstiene=datos_llm.se_abstiene,
        derivar_a=derivar_a,
        fuentes=fuentes_finales,
        proveedor=proveedor,
        alerta_signo_alarma=alerta_activa,
    )


# ------------------------------------------------------------------------------
# 3. ENDPOINTS OFICIALES DEL CASO 05: ASISTENTE CONVERSACIONAL DE DENGUE
# ------------------------------------------------------------------------------
class EntradaFlexibleChat(BaseModel):
    """
    Esquema de entrada flexible para el chat.
    Acepta tanto {"mensaje": "...", "historial": [...]} como el formato legacy {"texto": "..."}.
    """
    mensaje: str | None = None
    texto: str | None = None
    historial: list[dict] = Field(default_factory=list, description="Lista de mensajes previos [{'role': 'user'|'assistant', 'content': '...'}]")

    def obtener_consulta(self) -> str:
        """Extrae el mensaje del usuario y valida los límites de longitud (OWASP LLM10)."""
        c = (self.mensaje or self.texto or "").strip()
        if len(c) < 2:
            raise HTTPException(status_code=422, detail="La consulta debe tener al menos 2 caracteres.")
        if len(c) > 2000:
            raise HTTPException(status_code=422, detail="La consulta no puede exceder 2000 caracteres.")
        return c


@app.post(
    "/api/chat",
    response_model=RespuestaChatAPI,
    summary="Consulta ciudadana estructurada sobre dengue",
    tags=["Asistente Dengue"],
)
@app.post(
    "/chat",
    response_model=RespuestaChatAPI,
    summary="Consulta ciudadana estructurada sobre dengue (alias)",
    tags=["Asistente Dengue"],
)
def chat(
    entrada: EntradaFlexibleChat,
    llm: ClienteLLM = Depends(obtener_llm),
    retriever: RecuperadorDengue = Depends(obtener_retriever),
) -> RespuestaChatAPI:
    """
    Endpoint principal para interacción ciudadana en modo estructurado (JSON):
    1. Valida el texto de entrada y límites contra inyecciones de prompt (OWASP LLM10).
    2. Consulta al RecuperadorDengue (RAG) para buscar fragmentos en guías OPS/MSP.
    3. Si existen fragmentos relevantes, inyecta el contexto oficial al LLM.
    4. Invoca al ClienteLLM con tiempo límite, reintentos (backoff) y conmutación por falla.
    5. Aplica la regla determinista en Python para asegurar derivación inmediata ante signos de peligro.
    6. Inyecta deterministamente las fuentes oficiales recuperadas por el RAG (Semana 3).
    """
    consulta = entrada.obtener_consulta()
    lugar = _identificar_lugar_en_texto(consulta)

    # 1. Recuperación semántica RAG de guías OPS/MSP
    recuperacion = retriever.recuperar(consulta)

    # 2. Consulta determinista GeoSalud si se menciona una localidad
    texto_geosalud = ""
    fuente_geosalud = None
    if lugar:
        centros = ubicar_establecimiento(lugar, solo_emergencia_24h=True) or ubicar_establecimiento(lugar)
        if centros:
            texto_geosalud = formatear_establecimientos_para_asistente(centros[:2])
            nombre_ciudad = centros[0].get("ciudad", lugar.capitalize())
            fuente_geosalud = Fuente(
                id=str(centros[0].get("id", "geo-msp")),
                documento="Directorio GeoSalud MSP Ecuador 2026",
                seccion=f"Establecimientos de Salud en {nombre_ciudad}",
                tema="derivacion",
                anio="2026",
            )

    # 3. Ensamblado de bloques de contexto oficial
    bloques_contexto = []
    if recuperacion.relevante and recuperacion.texto_contexto:
        bloques_contexto.append(
            f"=== GUÍAS OFICIALES OPS / MSP (RAG) ===\n{recuperacion.texto_contexto}"
        )
    if texto_geosalud:
        bloques_contexto.append(
            f"=== RED DE ESTABLECIMIENTOS DE SALUD EN {lugar.upper()} (GEOSALUD) ===\n{texto_geosalud}\n"
            f"DIRECTIVA: Informa con claridad al ciudadano los nombres, direcciones y teléfonos "
            f"de los centros de salud indicados arriba para su localidad."
        )

    fuentes_candidatas = list(recuperacion.fuentes)
    if fuente_geosalud and fuente_geosalud not in fuentes_candidatas:
        fuentes_candidatas.append(fuente_geosalud)

    if bloques_contexto:
        contexto_completo = "\n\n".join(bloques_contexto)
        consulta_para_llm = (
            f"CONSULTA DEL CIUDADANO:\n{consulta}\n\n"
            f"INFORMACIÓN OFICIAL RECUPERADA (RAG Y GEOSALUD):\n"
            f"{contexto_completo}\n\n"
            f"INSTRUCCIÓN: Responde fundamentándote estrictamente en la información oficial recuperada. "
            f"Si se especifican centros de salud para la ciudad, menciónalos textualmente con su dirección y teléfono."
        )
    else:
        consulta_para_llm = consulta

    try:
        resultado = llm.generar_json(
            cargar_prompt(PROMPT_ASISTENTE),
            consulta_para_llm,
            RespuestaAsistente,
        )
    except ProveedorNoDisponible as e:
        # Error 503 controlado y comprensible para el usuario
        raise HTTPException(status_code=503, detail=e.mensaje_usuario)
    except SalidaInvalida as e:
        # Contingencia humana si el modelo devolvió un JSON irreconocible
        return RespuestaChatAPI(
            respuesta="No pudimos estructurar la respuesta automáticamente. Tu consulta ha sido enviada para revisión humana.",
            se_abstiene=True,
            derivar_a="Línea 171 del MSP para agendamiento médico",
            fuentes=[],
            proveedor=None,
            alerta_signo_alarma=False,
        )

    datos_llm: RespuestaAsistente = resultado.datos
    return _evaluar_regla_signos_alarma(
        consulta,
        datos_llm,
        resultado.proveedor,
        fuentes=fuentes_candidatas,
    )


@app.post(
    "/api/chat/stream",
    summary="Consulta ciudadana con respuesta en streaming",
    tags=["Asistente Dengue"],
)
@app.post(
    "/chat/stream",
    summary="Consulta ciudadana con respuesta en streaming (alias)",
    tags=["Asistente Dengue"],
)
def chat_stream(
    entrada: EntradaFlexibleChat,
    llm: ClienteLLM = Depends(obtener_llm),
    retriever: RecuperadorDengue = Depends(obtener_retriever),
):
    """
    Endpoint para respuesta conversacional en streaming (Server-Sent Events / Text chunks):
    1. Ensambla el historial previo si existe para mantener el contexto del diálogo.
    2. Consulta al RAG y GeoSalud para fundamentar la respuesta en las guías oficiales.
    3. Verifica la presencia de signos de alarma para inyectar advertencia médica urgente de inicio.
    4. Emite los trozos de texto en vivo a medida que los genera el modelo generativo.
    """
    consulta = entrada.obtener_consulta()
    hay_alarma = _detectar_signos_alarma(consulta)
    lugar = _identificar_lugar_en_texto(consulta)

    # Recuperación contextual RAG y GeoSalud para streaming
    recuperacion = retriever.recuperar(consulta)
    partes_stream = []
    if recuperacion.relevante and recuperacion.texto_contexto:
        partes_stream.append(f"=== GUÍAS OFICIALES OPS/MSP (RAG) ===\n{recuperacion.texto_contexto}")

    if lugar:
        centros = ubicar_establecimiento(lugar, solo_emergencia_24h=True) or ubicar_establecimiento(lugar)
        if centros:
            partes_stream.append(
                f"=== ESTABLECIMIENTOS EN {lugar.upper()} (GEOSALUD) ===\n"
                f"{formatear_establecimientos_para_asistente(centros[:2])}"
            )

    if partes_stream:
        consulta_contextualizada = (
            f"CONSULTA DEL CIUDADANO:\n{consulta}\n\n"
            f"INFORMACIÓN OFICIAL RECUPERADA:\n"
            f"{'\n\n'.join(partes_stream)}"
        )
    else:
        consulta_contextualizada = consulta

    # Construcción de la lista de mensajes con historial conversacional
    mensajes: list[dict] = []
    for m in entrada.historial:
        rol = m.get("rol") or m.get("role") or "user"
        contenido = m.get("contenido") or m.get("content") or ""
        if contenido:
            mensajes.append({"role": rol, "content": contenido})
    mensajes.append({"role": "user", "content": consulta_contextualizada})

    def generador_respuesta() -> Iterator[str]:
        # Si se detectaron signos de alarma, anteponer de forma inmediata la advertencia médica prioritaria
        if hay_alarma:
            yield "🚨 ALERTA MÉDICA PRIORITARIA (MSP / OPS): Ha mencionado síntomas que pueden ser signos de alarma de dengue grave (como dolor abdominal intenso, vómitos persistentes o sangrado). Debe acudir DE INMEDIATO a la Sala de Emergencias del hospital más cercano o comunicarse con el ECU-911.\n\n"
        
        try:
            # Invocar streaming del ClienteLLM (Gemini o Groq)
            system_prompt = cargar_prompt(PROMPT_ASISTENTE)
            for trozo in llm.generar_stream(system_prompt, mensajes):
                yield trozo
        except ProveedorNoDisponible as e:
            yield f"\n\n[Error de servicio: {e.mensaje_usuario}]"

    return StreamingResponse(generador_respuesta(), media_type="text/plain")


# ------------------------------------------------------------------------------
# 4. ENDPOINT COMPATIBILIDAD KIT: CLASIFICAR
# ------------------------------------------------------------------------------
@app.post(
    "/clasificar",
    response_model=RespuestaClasificar,
    summary="Clasificación de solicitudes (compatibilidad con suite de pruebas del kit)",
    tags=["Soporte Kit"],
)
def clasificar(solicitud: Solicitud, llm: ClienteLLM = Depends(obtener_llm)):
    """
    Endpoint de ejemplo de triaje de mesa de ayuda (compatibilidad con tests del kit).
    """
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


# ------------------------------------------------------------------------------
# 5. ENDPOINT DETERMINISTA DE GEOSALUD (DATOS TABULARES ECUADOR)
# ------------------------------------------------------------------------------
@app.get(
    "/api/geosalud/centros",
    summary="Directorio determinista de establecimientos de salud para dengue en Ecuador",
    tags=["GeoSalud"],
)
def buscar_centros_salud(
    termino: str | None = None,
    emergencia_24h: bool = False,
    requiere_pediatria: bool = False,
    requiere_uci: bool = False,
):
    """
    Herramienta determinista para consultar centros de salud y hospitales del MSP
    en zonas endémicas de dengue (Ecuador), sin pasar por embeddings vectoriales.
    """
    if not termino:
        from app.tools.geosalud import cargar_directorio_geosalud
        todos = cargar_directorio_geosalud()
        return {"total": len(todos), "establecimientos": todos}

    encontrados = ubicar_establecimiento(
        termino_busqueda=termino,
        solo_emergencia_24h=emergencia_24h,
        requiere_pediatria=requiere_pediatria,
        requiere_uci=requiere_uci,
    )
    return {
        "termino": termino,
        "total": len(encontrados),
        "establecimientos": encontrados,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG,
    )
