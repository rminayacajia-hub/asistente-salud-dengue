"""
Pruebas unitarias para la herramienta de GeoSalud Ecuador (Semana 3 / Caso 05).

Objetivo:
Validar de forma determinista y reproducible:
1. Búsqueda exacta e insensible a mayúsculas/tildes en cantones y provincias.
2. Filtros de emergencia 24h, UCI y pediatría.
3. Formateo legible de establecimientos para el asistente.
4. Manejo seguro de casos sin resultados o entradas vacías.
"""
from app.tools.geosalud import (
    cargar_directorio_geosalud,
    ubicar_establecimiento,
    formatear_establecimientos_para_asistente,
)


def test_cargar_directorio_geosalud():
    """Valida que el archivo JSON contenga los 14 establecimientos de la red MSP."""
    datos = cargar_directorio_geosalud()
    assert len(datos) == 14
    assert any(d["ciudad"] == "Guayaquil" for d in datos)
    assert any(d["provincia"] == "Manabí" for d in datos)


def test_ubicar_establecimiento_por_ciudad_con_tildes_y_mayusculas():
    """Valida que 'GUAYAQUIL', 'guayaquil' y 'Guayaquil' encuentren los mismos centros."""
    r1 = ubicar_establecimiento("Guayaquil")
    r2 = ubicar_establecimiento("guayaquil")
    r3 = ubicar_establecimiento("GUAYAQUIL")
    assert len(r1) == 4
    assert len(r1) == len(r2) == len(r3)


def test_ubicar_establecimiento_por_provincia():
    """Valida que buscar por provincia ('Manabí' o 'manabi') agrupe Manta, Portoviejo y Chone."""
    res = ubicar_establecimiento("manabi")
    assert len(res) == 3
    ciudades = {e["ciudad"] for e in res}
    assert ciudades == {"Portoviejo", "Manta", "Chone"}


def test_filtro_emergencia_24h_y_uci():
    """Valida que los filtros de capacidad crítica funcionen con exactitud."""
    res_24h = ubicar_establecimiento("Guayaquil", solo_emergencia_24h=True)
    assert all(e["emergencia_24h"] is True for e in res_24h)

    res_uci = ubicar_establecimiento("Guayaquil", requiere_uci=True)
    assert len(res_uci) >= 1
    assert any("UCI" in cap for e in res_uci for cap in e.get("capacidad_critica", []))


def test_busqueda_sin_coincidencias_retorna_lista_vacia():
    """Valida que términos inexistentes devuelvan lista vacía sin excepciones."""
    res = ubicar_establecimiento("CiudadInexistente999")
    assert res == []

    formato = formatear_establecimientos_para_asistente(res)
    assert "No se encontraron centros de salud específicos" in formato
    assert "ECU-911" in formato


def test_formatear_establecimientos_legible():
    """Valida que el texto formateado contenga dirección, teléfono y nombre."""
    res = ubicar_establecimiento("Machala")
    assert len(res) == 1
    texto = formatear_establecimientos_para_asistente(res)
    assert "Hospital General Teófilo Dávila" in texto
    assert "Teléfono" in texto
    assert "Dirección" in texto


def test_endpoint_geosalud_directorio():
    """Valida que el endpoint GET /api/geosalud/centros devuelva la lista correcta."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    resp = client.get("/api/geosalud/centros?termino=Esmeraldas")
    assert resp.status_code == 200
    datos = resp.json()
    assert datos["total"] == 1
    assert "Delfina Torres" in datos["establecimientos"][0]["nombre"]


def test_signos_alarma_con_ciudad_personaliza_derivacion():
    """Valida que si el paciente tiene alarma y menciona Guayaquil, derive al hospital de la zona."""
    from fastapi.testclient import TestClient
    from app.main import app, obtener_llm
    from app.schemas import RespuestaAsistente
    from app.services.llm import Resultado

    class MockLLM:
        def generar_json(self, s, u, e):
            return Resultado(
                datos=RespuestaAsistente(
                    respuesta="Atención urgente requerida.",
                    se_abstiene=False,
                    derivar_a=None,
                ),
                proveedor="gemini",
                modelo="gemini-3.8-flash",
                tokens_entrada=10,
                tokens_salida=10,
                latencia_ms=50,
                intentos=1,
            )

    app.dependency_overrides[obtener_llm] = lambda: MockLLM()
    client = TestClient(app)
    resp = client.post(
        "/api/chat",
        json={"texto": "Mi hijo tiene vómitos persistentes y dolor abdominal intenso, estamos en Guayaquil"}
    )
    assert resp.status_code == 200
    cuerpo = resp.json()
    assert cuerpo["alerta_signo_alarma"] is True
    assert "Guayaquil" in cuerpo["derivar_a"]
    assert "Emergencias" in cuerpo["derivar_a"]
    app.dependency_overrides.pop(obtener_llm, None)

