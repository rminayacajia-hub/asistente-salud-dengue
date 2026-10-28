"""
Pruebas unitarias para el servicio Retriever y el pipeline RAG (Semana 3).
Seminario de Titulación UNIANDES 2026 - Caso 05 (Dengue Ecuador).

Objetivo:
Validar de forma aislada y reproducible:
1. Recuperación semántica de fragmentos normativos oficiales.
2. Filtrado por umbral de distancia (consultas irrelevantes).
3. Modo degradado seguro (fallback graceful si no existe el índice).
4. Entrega de fuentes estructuradas en el endpoint /api/chat.
"""
from fastapi.testclient import TestClient

from app.main import app, obtener_llm, obtener_retriever
from app.schemas import RespuestaAsistente, Fuente
from app.services.llm import Resultado
from app.services.retriever import RecuperadorDengue, ResultadoRecuperacion


class LLMDoble:
    """Mock del modelo LLM para evitar consumo de tokens en pruebas."""
    def __init__(self, resultado=None):
        self.resultado = resultado

    def generar_json(self, system, usuario, esquema):
        return self.resultado


def test_retriever_recupera_fragmentos_y_fuentes_en_dengue():
    """Valida que una consulta sobre signos de alarma recupere fragmentos y fuentes oficiales."""
    retriever = RecuperadorDengue()
    res = retriever.recuperar("¿Cuáles son los signos de alarma del dengue?")
    assert res.relevante is True
    assert len(res.fragmentos) > 0
    assert len(res.fuentes) > 0
    # Verifica que los metadatos oficiales contengan la guía de la OPS o MSP
    textos_fuentes = [f.documento for f in res.fuentes]
    assert any("OPS" in doc or "MSP" in doc for doc in textos_fuentes)


def test_retriever_filtra_consultas_irrelevantes():
    """Valida que consultas totalmente ajenas al dengue se descarten por distancia máxima."""
    retriever = RecuperadorDengue()
    res = retriever.recuperar("receta de pastel de chocolate con cobertura de dulce de leche")
    assert res.relevante is False
    assert res.fuentes == []
    assert res.texto_contexto == ""


def test_retriever_fallback_graceful_si_no_existe_indice():
    """Valida que si la ruta no existe, el retriever no colapse y devuelva modo degradado."""
    retriever = RecuperadorDengue(ruta_indice="data/directorio_inexistente_12345")
    assert retriever.esta_disponible is False
    res = retriever.recuperar("¿Qué es el dengue?")
    assert res.relevante is False
    assert res.fuentes == []


def test_chat_endpoint_inyecta_fuentes_rag():
    """Valida que el endpoint /api/chat incorpore las fuentes oficiales devueltas por el RAG."""
    datos = RespuestaAsistente(
        respuesta="El dengue se transmite por la picadura del mosquito Aedes aegypti infectado.",
        se_abstiene=False,
        derivar_a=None,
    )
    mock_llm = LLMDoble(
        resultado=Resultado(
            datos=datos,
            proveedor="gemini",
            modelo="gemini-3.8-flash",
            tokens_entrada=50,
            tokens_salida=30,
            latencia_ms=100,
            intentos=1,
        )
    )
    app.dependency_overrides[obtener_llm] = lambda: mock_llm

    client = TestClient(app)
    resp = client.post("/api/chat", json={"texto": "¿Cómo se contagia el dengue según la OPS?"})
    assert resp.status_code == 200
    cuerpo = resp.json()
    assert cuerpo["se_abstiene"] is False
    # La lista de fuentes debe venir poblada por el RAG
    assert len(cuerpo["fuentes"]) > 0
    assert any("OPS" in f["documento"] or "MSP" in f["documento"] for f in cuerpo["fuentes"])

    # Limpiar override
    app.dependency_overrides.pop(obtener_llm, None)
