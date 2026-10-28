"""
Frontend Streamlit - Asistente de Orientación en Salud Pública sobre Dengue y Arbovirosis.
Seminario de Titulación UNIANDES 2026 - Caso 05 (Grupo 5).

Arquitectura desacoplada:
Este frontend no contiene lógica de negocio clínica ni credenciales de IA.
Se comunica exclusivamente con la API Backend de FastAPI mediante peticiones HTTP REST.
"""
import os
import requests
import streamlit as st

# ==============================================================================
# 1. CONFIGURACIÓN DE PÁGINA Y METADATOS
# ==============================================================================
st.set_page_config(
    page_title="Asistente Dengue | Salud Pública Ecuador",
    page_icon="🦟",
    layout="wide",
    initial_sidebar_state="expanded",
)

# URL del backend FastAPI (configurable por variable de entorno o localhost por defecto)
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


# ==============================================================================
# 2. FUNCIONES AUXILIARES DE COMUNICACIÓN CON EL BACKEND
# ==============================================================================
def verificar_salud_backend() -> dict | None:
    """
    Consulta el endpoint GET /health del backend FastAPI para comprobar
    si el servicio está operativo y conectado.
    """
    try:
        respuesta = requests.get(f"{BACKEND_URL}/health", timeout=3)
        if respuesta.status_code == 200:
            return respuesta.json()
    except requests.exceptions.RequestException:
        return None
    return None


def consultar_asistente(mensaje: str, historial: list[dict]) -> dict:
    """
    Envía la consulta del ciudadano al endpoint POST /api/chat del backend FastAPI.
    Transmite el historial para mantener coherencia conversacional.
    """
    payload = {
        "mensaje": mensaje,
        "historial": [
            {"rol": m["role"], "contenido": m["content"]}
            for m in historial[-6:]  # Enviamos los últimos 6 turnos para optimizar contexto
        ]
    }
    try:
        # Tiempo de espera amplio (60s) para permitir que el backend complete reintentos y conmutación a Groq sin interrupción
        respuesta = requests.post(
            f"{BACKEND_URL}/api/chat",
            json=payload,
            timeout=60,
        )
        if respuesta.status_code == 200:
            return {"exito": True, "datos": respuesta.json()}
        elif respuesta.status_code == 503:
            # Error controlado del backend cuando los proveedores LLM están saturados
            detalle = respuesta.json().get("detail", "Servicio temporalmente saturado.")
            return {"exito": False, "error": detalle}
        else:
            return {
                "exito": False,
                "error": f"Error del servidor ({respuesta.status_code}). Intente nuevamente más tarde."
            }
    except requests.exceptions.ConnectionError:
        return {
            "exito": False,
            "error": "No se pudo conectar con el servidor backend. Verifique que FastAPI esté ejecutándose en el puerto 8000."
        }
    except requests.exceptions.Timeout:
        return {
            "exito": False,
            "error": "El servidor tardó demasiado en responder (tiempo límite agotado). Por favor reintente."
        }
    except Exception as e:
        return {"exito": False, "error": f"Error inesperado: {str(e)}"}


def obtener_centros_geosalud(termino: str = "") -> list[dict]:
    """Consulta el directorio determinista de centros de salud en el backend."""
    try:
        url = f"{BACKEND_URL}/api/geosalud/centros"
        params = {"termino": termino} if termino else {}
        resp = requests.get(url, params=params, timeout=5)
        if resp.status_code == 200:
            return resp.json().get("establecimientos", [])
        return []
    except Exception:
        return []


# ==============================================================================
# 3. BARRA LATERAL (SIDEBAR) - INFORMACIÓN Y ESTADO DEL SISTEMA
# ==============================================================================
with st.sidebar:
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e0/Coat_of_arms_of_Ecuador.svg/300px-Coat_of_arms_of_Ecuador.svg.png",
        width=70,
    )
    st.title("Alerta Dengue")
    st.caption("Orientación Oficial en Salud Pública · MSP Ecuador / OPS")
    
    st.divider()

    # Verificación en vivo del estado del backend
    info_salud = verificar_salud_backend()
    if info_salud and info_salud.get("estado") == "ok":
        st.success("🟢 Backend FastAPI: Conectado")
    else:
        st.error("🔴 Backend FastAPI: Desconectado")
        st.caption(f"Verifique `uvicorn app.main:app` en `{BACKEND_URL}`")

    st.divider()

    # Directorio de Hospitales MSP (Semana 3 / GeoSalud)
    with st.expander("🏥 Directorio MSP en Zona Endémica"):
        ciudad_sel = st.selectbox(
            "Filtrar por localidad:",
            ["Todas", "Guayaquil", "Portoviejo", "Manta", "Chone", "Esmeraldas", "Babahoyo", "Machala", "Santo Domingo", "Orellana", "Sucumbíos", "Pastaza"],
            key="filtro_ciudad"
        )
        termino_filtro = "" if ciudad_sel == "Todas" else ciudad_sel
        centros = obtener_centros_geosalud(termino_filtro)
        if centros:
            for c in centros[:3]:
                st.markdown(f"**{c.get('nombre')}**")
                st.caption(f"📍 {c.get('direccion')}\n📞 {c.get('telefono')} | Emergencia 24h: {'Sí' if c.get('emergencia_24h') else 'No'}")
        else:
            st.caption("Conecte el backend para consultar hospitales en tiempo real.")

    st.divider()

    # Signos de Alarma Clave (Guía Rápida para el Ciudadano)
    st.markdown("### ⚠️ Signos de Alarma")
    st.markdown(
        """
        Si presenta cualquiera de estos síntomas, **acuda de inmediato** a emergencias:
        - 🔴 Dolor abdominal intenso y continuo
        - 🔴 Vómitos persistentes
        - 🔴 Sangrado de mucosas (encías, nariz)
        - 🔴 Somnolencia, mareo o desmayo
        - 🔴 Dificultad para respirar
        """
    )

    st.divider()

    # Canales de Emergencia Nacionales
    st.markdown("### 📞 Contactos de Emergencia")
    st.markdown("- **ECU-911:** Emergencias médicas inmediatas")
    st.markdown("- **Línea 171:** Citas y orientación MSP")

    st.divider()

    # Botón para reiniciar y limpiar la conversación
    if st.button("🧹 Limpiar Conversación", use_container_width=True):
        st.session_state.mensajes = []
        st.rerun()


# ==============================================================================
# 4. CUERPO PRINCIPAL DE LA APLICACIÓN
# ==============================================================================
st.header("🦟 Asistente Virtual sobre Dengue y Arbovirosis")
st.markdown(
    """
    Bienvenido al sistema de orientación ciudadana en salud pública. 
    Puede consultar sobre **síntomas iniciales, prevención del mosquito, cuidados en el hogar y cuándo acudir al médico**.
    
    > **Aviso de Salud Pública:** Este asistente ofrece orientación informativa basada en las guías oficiales 
    > del **Ministerio de Salud Pública del Ecuador** y la **OPS/OMS**. **No prescribe fármacos ni sustituye el diagnóstico médico presencial**.
    """
)

# Inicialización del historial de mensajes en la sesión de Streamlit
if "mensajes" not in st.session_state:
    st.session_state.mensajes = [
        {
            "role": "assistant",
            "content": (
                "¡Hola! Soy tu asistente de orientación sobre dengue y arbovirosis. "
                "¿En qué puedo ayudarte hoy? Recuerda que si sientes dolor de estómago muy fuerte, "
                "vómitos continuos o sangrado, debes acudir urgentemente a un centro de salud."
            ),
            "alerta": False,
            "derivar_a": None,
            "fuentes": [],
            "proveedor": None,
        }
    ]

# Renderizado de los mensajes históricos en el chat
for mensaje in st.session_state.mensajes:
    with st.chat_message(mensaje["role"]):
        st.markdown(mensaje["content"])

        # Si el mensaje incluye derivación por signos de alarma, renderizar tarjeta de alerta destacada
        derivacion_texto = mensaje.get("derivar_a", "")
        if mensaje.get("alerta"):
            st.error(
                f"🚨 **DERIVACIÓN MÉDICA URGENTE:**\n\n"
                f"{derivacion_texto or 'Acuda de inmediato al centro de salud u hospital más cercano o llame al ECU-911.'}"
            )
        elif derivacion_texto:
            # Distingue si es geolocalización precisa con datos de contacto o sugerencia general
            es_geosalud = any(ind in derivacion_texto for ind in ("Tel:", "Dirección", "Hospital General", "Infectología", "Bastión", "Tipo C", "Delfina", "Zambrano"))
            titulo_tarjeta = "🏥 **ESTABLECIMIENTO DE SALUD SUGERIDO (GEOSALUD):**" if es_geosalud else "🏥 **ORIENTACIÓN DE ATENCIÓN MÉDICA:**"
            st.info(f"{titulo_tarjeta}\n\n{derivacion_texto}")

        # Si hay fuentes oficiales vinculadas, mostrarlas en un bloque desplegable con todos sus metadatos (Semana 3)
        if mensaje.get("fuentes"):
            with st.expander("📚 Fuentes normativas consultadas (RAG / GeoSalud)"):
                for f in mensaje["fuentes"]:
                    fid = f"`[{f.get('id')}]` " if f.get("id") else ""
                    anio = f" ({f.get('anio')})" if f.get("anio") else ""
                    tema = f" | *Tema: {f.get('tema')}*" if f.get("tema") else ""
                    doc = f.get('documento', 'MSP Ecuador')
                    sec = f.get('seccion', 'Sección oficial')
                    st.markdown(f"- {fid}**{doc}{anio}**: {sec}{tema}")

        # Pie informativo con el proveedor de IA utilizado
        if mensaje.get("proveedor"):
            st.caption(f"Orientación generada con respaldo de `{mensaje['proveedor']}`")


# ==============================================================================
# 5. CONTROL DE ENTRADA (CHAT INPUT Y MANEJO DE ESTADO)
# ==============================================================================
pregunta_usuario = st.chat_input("Escriba su consulta o describa los síntomas...")

if pregunta_usuario:
    # 1. Agregar y mostrar inmediatamente la pregunta del usuario en pantalla
    st.session_state.mensajes.append({"role": "user", "content": pregunta_usuario})
    with st.chat_message("user"):
        st.markdown(pregunta_usuario)

    # 2. Deshabilitar entrada y mostrar indicador visual de espera
    with st.chat_message("assistant"):
        with st.spinner("Consultando guías de salud pública y evaluando síntomas..."):
            # 3. Llamar al backend FastAPI
            resultado = consultar_asistente(pregunta_usuario, st.session_state.mensajes)

        if resultado["exito"]:
            datos = resultado["datos"]
            texto_respuesta = datos.get("respuesta", "")
            es_alarma = datos.get("alerta_signo_alarma", False)
            derivacion = datos.get("derivar_a")
            fuentes = datos.get("fuentes", [])
            proveedor = datos.get("proveedor")

            # Mostrar respuesta del asistente
            st.markdown(texto_respuesta)

            # Mostrar banner según gravedad (urgencia roja vs orientación informativa)
            if es_alarma:
                st.error(
                    f"🚨 **DERIVACIÓN MÉDICA URGENTE:**\n\n"
                    f"{derivacion or 'Acuda de inmediato al centro de salud u hospital más cercano o llame al ECU-911.'}"
                )
            elif derivacion:
                es_geosalud = any(ind in derivacion for ind in ("Tel:", "Dirección", "Hospital General", "Infectología", "Bastión", "Tipo C", "Delfina", "Zambrano"))
                titulo_tarjeta = "🏥 **ESTABLECIMIENTO DE SALUD SUGERIDO (GEOSALUD):**" if es_geosalud else "🏥 **ORIENTACIÓN DE ATENCIÓN MÉDICA:**"
                st.info(f"{titulo_tarjeta}\n\n{derivacion}")

            # Guardar en el historial de sesión
            st.session_state.mensajes.append({
                "role": "assistant",
                "content": texto_respuesta,
                "alerta": es_alarma,
                "derivar_a": derivacion,
                "fuentes": fuentes,
                "proveedor": proveedor,
            })
            st.rerun()
        else:
            # Mostrar error amigable al usuario sin romper la interfaz
            st.error(f"⚠️ {resultado['error']}")
