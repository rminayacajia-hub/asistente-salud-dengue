"""
Pruebas del endpoint oficial del Caso 05 (POST /api/chat y /chat) con dobles (mocks) de IA.
Seminario de Titulación UNIANDES 2026 - Caso 05 (Dengue Ecuador).

Cumple la rúbrica de Semana 2:
- Pruebas que corren sin saldo ni internet.
- Validación del principio "El modelo propone, el código dispone".
- Manejo limpio de errores 503 y contingencia humana.
"""
from fastapi.testclient import TestClient

from app.main import app, obtener_llm
from app.schemas import RespuestaAsistente, Fuente
from app.services.llm import ProveedorNoDisponible, Resultado, SalidaInvalida


class LLMDoble:
    """Doble de prueba (Mock) que simula respuestas de Gemini / Groq sin gastar saldo."""
    def __init__(self, resultado=None, error=None):
        self.resultado = resultado
        self.error = error

    def generar_json(self, system, usuario, esquema):
        if self.error:
            raise self.error
        return self.resultado


def cliente_con(llm):
    """Inyecta el doble de prueba en la dependencia obtener_llm de FastAPI."""
    app.dependency_overrides[obtener_llm] = lambda: llm
    return TestClient(app)


def respuesta_modelo_base(**kw):
    """Genera una instancia de RespuestaAsistente empaquetada en un Resultado."""
    base = {
        "respuesta": "El dengue se transmite por la picadura del mosquito Aedes aegypti.",
        "se_abstiene": False,
        "derivar_a": None,
        "fuentes": [Fuente(documento="Guía Dengue MSP 2026", seccion="Transmisión")],
        "proveedor": "gemini",
    }
    base.update(kw)
    datos = RespuestaAsistente(**base)
    return Resultado(
        datos=datos,
        proveedor="gemini",
        modelo="gemini-3.8-flash",
        tokens_entrada=40,
        tokens_salida=25,
        latencia_ms=120,
        intentos=1
    )


def test_chat_orientacion_exitosa():
    """Valida que una consulta legítima de dengue devuelva HTTP 200 con el esquema correcto."""
    client = cliente_con(LLMDoble(resultado=respuesta_modelo_base()))
    resp = client.post("/api/chat", json={"texto": "¿Cómo se transmite el dengue y qué mosquito lo produce?"})
    assert resp.status_code == 200
    data = resp.json()
    assert "Aedes aegypti" in data["respuesta"]
    assert data["se_abstiene"] is False
    assert data["proveedor"] == "gemini"


def test_regla_signos_alarma_forzada_en_codigo():
    """
    Regla de Oro (ADR-004): Si el usuario menciona signos de alarma, el código Python
    impone la derivación médica urgente, aunque el modelo no la hubiera puesto.
    """
    doble = LLMDoble(resultado=respuesta_modelo_base(derivar_a=None))
    client = cliente_con(doble)
    # El usuario menciona dolor continuo en la barriga y vómitos
    resp = client.post("/api/chat", json={"texto": "Tengo mucho dolor en la barriga continuo y vómitos frecuentes"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["derivar_a"] is not None
    assert "Emergencias" in data["derivar_a"] or "ECU-911" in data["derivar_a"]


def test_abstencion_fuera_de_dominio():
    """Valida que una pregunta ajena al dengue active se_abstiene = True."""
    doble = LLMDoble(resultado=respuesta_modelo_base(
        respuesta="Mi ámbito de orientación se limita exclusivamente a dengue y salud pública.",
        se_abstiene=True,
        derivar_a=None
    ))
    client = cliente_con(doble)
    resp = client.post("/api/chat", json={"texto": "¿Cuáles son los requisitos para renovar la licencia en la ANT?"})
    assert resp.status_code == 200
    assert resp.json()["se_abstiene"] is True


def test_proveedor_caido_devuelve_503_limpio():
    """Si los proveedores de IA caen, el endpoint responde HTTP 503 con mensaje de usuario claro."""
    client = cliente_con(LLMDoble(error=ProveedorNoDisponible()))
    resp = client.post("/api/chat", json={"texto": "¿Cuáles son los síntomas del dengue?"})
    assert resp.status_code == 503
    assert "no está disponible" in resp.json()["detail"]


def test_salida_invalida_activa_contingencia_humana():
    """Si el modelo devuelve una salida ininteligible, el sistema activa revisión sin romper el API."""
    client = cliente_con(LLMDoble(error=SalidaInvalida()))
    resp = client.post("/api/chat", json={"texto": "¿Qué hago si tengo fiebre alta?"})
    assert resp.status_code == 200
    assert "revisión humana" in resp.json()["respuesta"]


def test_entrada_demasiado_larga_se_rechaza_con_422():
    """Entradas gigantes que excedan el límite de Pydantic se rechazan con HTTP 422 (OWASP LLM10)."""
    client = cliente_con(LLMDoble(resultado=respuesta_modelo_base()))
    resp = client.post("/api/chat", json={"texto": "a" * 2005})
    assert resp.status_code == 422
