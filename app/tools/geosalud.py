"""
Herramienta Determinista de GeoSalud Ecuador (Semana 3 / Caso 05).

Principio SOLID - Responsabilidad Única (SRP):
Este módulo tiene como única responsabilidad consultar, filtrar y formatear
el directorio estructurado de establecimientos de salud del MSP de Ecuador
(almacenado en data/geosalud_ecuador.json).

¿Por qué es una herramienta determinista y no parte del RAG vectorial?
Siguiendo las directivas del Módulo 3, los datos tabulares con atributos exactos
(provincia, cantón, nivel de atención, teléfono) sufren alucinaciones si se
indexan en una base vectorial. Una función en Python garantiza búsqueda exacta,
filtrado sin errores y preservación fiel de direcciones y teléfonos de emergencia.
"""
from __future__ import annotations

import json
import logging
import unicodedata
from pathlib import Path
from typing import Any

# Logger para auditoría de consultas de geolocalización
logger = logging.getLogger("asistente.tools.geosalud")

# Ruta canónica al archivo de centros de salud
RUTA_BASE = Path(__file__).resolve().parent.parent.parent
RUTA_GEOSALUD_JSON = RUTA_BASE / "data" / "geosalud_ecuador.json"


def _normalizar_texto(texto: str) -> str:
    """
    Elimina tildes, caracteres especiales y convierte a minúsculas.
    
    ¿Para qué sirve?
    Permite que la búsqueda sea insensible a acentos (ej. 'Manabí' coincide con 'manabi',
    'Guayaquil' con 'guayaquil', 'Sinaí' con 'sinai').
    """
    texto_limpio = unicodedata.normalize("NFD", texto)
    texto_sin_tildes = "".join(c for c in texto_limpio if unicodedata.category(c) != "Mn")
    return texto_sin_tildes.lower().strip()


def cargar_directorio_geosalud() -> list[dict[str, Any]]:
    """
    Lee y deserializa el archivo data/geosalud_ecuador.json.
    
    ¿Para qué sirve?
    Provee el conjunto de datos de centros de salud y hospitales de la red MSP.
    Si el archivo no existe o falla su lectura, retorna una lista vacía de forma segura.
    """
    if not RUTA_GEOSALUD_JSON.exists():
        logger.error("No se encontró el archivo de geosalud en %s", RUTA_GEOSALUD_JSON)
        return []

    try:
        with open(RUTA_GEOSALUD_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error("Error al cargar data/geosalud_ecuador.json: %s", e)
        return []


def ubicar_establecimiento(
    termino_busqueda: str,
    solo_emergencia_24h: bool = False,
    requiere_pediatria: bool = False,
    requiere_uci: bool = False,
) -> list[dict[str, Any]]:
    """
    Busca establecimientos de salud por cantón (ciudad), provincia o nombre de hospital.
    
    ¿Por qué lo creamos?
    Para localizar de forma determinista el centro de salud u hospital más adecuado
    en la zona endémica del paciente (Costa y Amazonía ecuatoriana).
    
    Parámetros:
        termino_busqueda: Nombre de la ciudad, cantón, provincia o centro médico.
        solo_emergencia_24h: Si es True, filtra únicamente centros con atención de guardia 24 horas.
        requiere_pediatria: Si es True, prioriza centros con infectología pediátrica o UCIP.
        requiere_uci: Si es True, prioriza hospitales con Unidad de Cuidados Intensivos.
        
    Retorna:
        Lista de diccionarios con los establecimientos que cumplen los criterios.
    """
    directorio = cargar_directorio_geosalud()
    if not directorio or not termino_busqueda.strip():
        return []

    termino_norm = _normalizar_texto(termino_busqueda)
    coincidencias: list[dict[str, Any]] = []

    for est in directorio:
        ciudad_norm = _normalizar_texto(est.get("ciudad", ""))
        provincia_norm = _normalizar_texto(est.get("provincia", ""))
        nombre_norm = _normalizar_texto(est.get("nombre", ""))

        # Coincidencia parcial o total en ciudad, provincia o nombre
        coincide_lugar = (
            termino_norm in ciudad_norm
            or termino_norm in provincia_norm
            or termino_norm in nombre_norm
            or ciudad_norm in termino_norm
            or provincia_norm in termino_norm
        )

        if not coincide_lugar:
            continue

        # Filtro de emergencia 24 horas
        if solo_emergencia_24h and not est.get("emergencia_24h", False):
            continue

        capacidades = [c.lower() for c in est.get("capacidad_critica", [])]

        # Filtro de pediatría
        if requiere_pediatria and not any("pediat" in cap or "ucip" in cap for cap in capacidades):
            continue

        # Filtro de UCI para casos críticos
        if requiere_uci and not any("uci" in cap or "terapia intensiva" in cap for cap in capacidades):
            continue

        coincidencias.append(est)

    return coincidencias


def formatear_establecimientos_para_asistente(establecimientos: list[dict[str, Any]]) -> str:
    """
    Transforma la lista de establecimientos en un texto limpio y empático
    para ser entregado al ciudadano o incorporado en la derivación del asistente.
    
    ¿Para qué sirve?
    Entrega al usuario la dirección exacta, el teléfono y los servicios críticos
    de forma estructurada y legible.
    """
    if not establecimientos:
        return (
            "No se encontraron centros de salud específicos registrados para esa localidad. "
            "Ante cualquier emergencia o signo de alarma, acuda de inmediato al centro de salud "
            "u hospital del MSP más cercano o comuníquese a la línea de emergencia nacional ECU-911."
        )

    lineas: list[str] = []
    for i, est in enumerate(establecimientos, 1):
        nombre = est.get("nombre", "Establecimiento de Salud")
        ciudad = est.get("ciudad", "")
        provincia = est.get("provincia", "")
        direccion = est.get("direccion", "Dirección no registrada")
        telefono = est.get("telefono", "Sin teléfono directo")
        nivel = est.get("nivel", "")
        emergencia = "Emergencia 24h: Sí" if est.get("emergencia_24h") else "Emergencia 24h: No"
        capacidades = ", ".join(est.get("capacidad_critica", []))

        lineas.append(
            f"{i}. **{nombre}** ({nivel} - {ciudad}, {provincia})\n"
            f"   - Dirección: {direccion}\n"
            f"   - Teléfono: {telefono}\n"
            f"   - Horario: {emergencia}\n"
            f"   - Capacidad destacada: {capacidades}"
        )

    return "\n\n".join(lineas)
