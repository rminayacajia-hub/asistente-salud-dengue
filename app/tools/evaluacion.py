"""
Herramienta Determinista de Triaje y Evaluación de Signos de Alarma (Semana 3 / Caso 05).

Principio SOLID - Responsabilidad Única (SRP):
Este módulo tiene como única responsabilidad evaluar de forma 100% determinista
la presencia de signos de alarma de dengue grave y aplicar los umbrales clínicos
definidos en config/umbrales.json (sección "triaje_clinico").

¿Por qué reside en una herramienta en Python y nunca en el LLM?
Cumple con la Regla de Oro 3 de la Guía Estándar UNIANDES y el ADR-004:
«Lo que se calcula o triajea, lo calcula el código». El LLM jamás decide si un
paciente tiene signos de alarma o si requiere derivación urgente.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger("asistente.tools.evaluacion")

RUTA_BASE = Path(__file__).resolve().parent.parent.parent
RUTA_CONFIG_UMBRALES = RUTA_BASE / "config" / "umbrales.json"

# Palabras y raíces léxicas canónicas que corresponden a signos de alarma según OPS (2016/2024) y MSP
SIGNOS_ALARMA_CLAVE = (
    "dolor abdominal",
    "barriga",
    "vomit",
    "vomita",
    "vomito",
    "vómito",
    "sangrad",
    "sangre",
    "encía",
    "encia",
    "nariz",
    "mareo",
    "desmay",
    "somnolen",
    "letargo",
    "irritab",
    "acumulacion de liquido",
    "acumulación de líquido",
    "hepatomegalia",
)


class ParametrosTriajeInput(BaseModel):
    """
    Esquema Pydantic validado de entrada para la herramienta determinista de triaje.
    Acepta tanto banderas booleanas de síntomas de alarma como signos vitales/laboratorio
    que se contrastan contra config/umbrales.json.
    """
    dolor_abdominal_intenso: bool = Field(default=False, description="Dolor abdominal intenso y continuo")
    vomitos_persistentes: bool = Field(default=False, description="Vómitos persistentes o frecuentes")
    numero_vomitos_24h: int | None = Field(default=None, ge=0, description="Número de episodios de vómito en 24 horas")
    sangrado_mucosas: bool = Field(default=False, description="Sangrado de encías, nariz u otras mucosas")
    letargo_o_irritabilidad: bool = Field(default=False, description="Somnolencia extrema, letargo o irritabilidad")
    hipotension_o_mareo: bool = Field(default=False, description="Mareo severo al ponerse de pie o desmayo")
    acumulacion_liquidos: bool = Field(default=False, description="Edema, ascitis o derrame pleural")
    dias_evolucion: int | None = Field(default=None, ge=0, description="Días desde el inicio de la fiebre")
    temperatura_celsius: float | None = Field(default=None, description="Temperatura corporal en grados Celsius")
    plaquetas_por_mm3: int | None = Field(default=None, ge=0, description="Recuento de plaquetas en laboratorio")


def cargar_umbrales_triaje() -> dict[str, Any]:
    """
    Lee en tiempo real los umbrales clínicos desde config/umbrales.json.
    Cumple el principio 4 de la Guía: «Lo que cambia con el tiempo, vive en configuración».
    Si el docente modifica config/umbrales.json en vivo, el cambio surte efecto de inmediato.
    """
    defaults = {
        "dias_fase_critica_min": 3,
        "dias_fase_critica_max": 7,
        "vomitos_persistentes_umbral_24h": 3,
        "temperatura_alerta_celsius": 38.5,
        "plaquetas_limite_alerta": 100000,
    }
    if not RUTA_CONFIG_UMBRALES.exists():
        return defaults

    try:
        with open(RUTA_CONFIG_UMBRALES, "r", encoding="utf-8") as f:
            datos = json.load(f)
            cfg = datos.get("triaje_clinico", {})
            return {
                "dias_fase_critica_min": int(cfg.get("dias_fase_critica_min", defaults["dias_fase_critica_min"])),
                "dias_fase_critica_max": int(cfg.get("dias_fase_critica_max", defaults["dias_fase_critica_max"])),
                "vomitos_persistentes_umbral_24h": int(cfg.get("vomitos_persistentes_umbral_24h", defaults["vomitos_persistentes_umbral_24h"])),
                "temperatura_alerta_celsius": float(cfg.get("temperatura_alerta_celsius", defaults["temperatura_alerta_celsius"])),
                "plaquetas_limite_alerta": int(cfg.get("plaquetas_limite_alerta", defaults["plaquetas_limite_alerta"])),
            }
    except Exception as e:
        logger.error("Error leyendo triaje_clinico en %s: %s", RUTA_CONFIG_UMBRALES, e)
        return defaults


def detectar_signos_alarma_en_texto(texto: str) -> bool:
    """
    Verifica de forma estricta y determinista si la consulta del ciudadano
    contiene signos de alarma de dengue grave (por palabras clave o por superación
    de los umbrales numéricos de config/umbrales.json como plaquetas o vómitos).
    """
    texto_lower = texto.lower()
    if any(signo in texto_lower for signo in SIGNOS_ALARMA_CLAVE):
        return True

    umbrales = cargar_umbrales_triaje()

    # Verificar si menciona número de vómitos >= umbral de configuración
    match_vomitos = re.search(r"(\d+)\s*(?:veces|episodios)?\s*(?:de\s*)?v[oó]mit", texto_lower)
    if match_vomitos and int(match_vomitos.group(1)) >= umbrales["vomitos_persistentes_umbral_24h"]:
        return True

    # Verificar si menciona recuento de plaquetas <= límite de configuración
    match_plaquetas = re.search(r"plaquetas\s*(?:en|de|a)?\s*(\d[\d\.,]*)", texto_lower)
    if match_plaquetas:
        valor_str = match_plaquetas.group(1).replace(".", "").replace(",", "")
        if valor_str.isdigit() and int(valor_str) <= umbrales["plaquetas_limite_alerta"]:
            return True

    return False


def evaluar_signos_alarma(entrada: ParametrosTriajeInput | dict[str, Any]) -> dict[str, Any]:
    """
    Herramienta determinista oficial del Caso 05:
    Evalúa el checklist estructurado y parámetros clínicos frente a config/umbrales.json.
    Retorna clasificación clínica MSP (Grupo A, Grupo B o Emergencia Crítica),
    signos detectados y orden de derivación.
    """
    datos = entrada if isinstance(entrada, ParametrosTriajeInput) else ParametrosTriajeInput(**entrada)
    umbrales = cargar_umbrales_triaje()

    signos_detectados: list[str] = []

    if datos.dolor_abdominal_intenso:
        signos_detectados.append("Dolor abdominal intenso y continuo (OPS Sección 3)")
    if datos.vomitos_persistentes or (
        datos.numero_vomitos_24h is not None
        and datos.numero_vomitos_24h >= umbrales["vomitos_persistentes_umbral_24h"]
    ):
        signos_detectados.append(
            f"Vómitos persistentes (umbral >= {umbrales['vomitos_persistentes_umbral_24h']} episodios en 24h)"
        )
    if datos.sangrado_mucosas:
        signos_detectados.append("Sangrado activo de mucosas (encías/nariz)")
    if datos.letargo_o_irritabilidad:
        signos_detectados.append("Letargo, somnolencia extrema o irritabilidad")
    if datos.hipotension_o_mareo:
        signos_detectados.append("Mareo postural severo o lipotimia")
    if datos.acumulacion_liquidos:
        signos_detectados.append("Acumulación clínica de líquidos (edema/ascitis)")
    if datos.plaquetas_por_mm3 is not None and datos.plaquetas_por_mm3 <= umbrales["plaquetas_limite_alerta"]:
        signos_detectados.append(
            f"Trombocitopenia de alerta (plaquetas <= {umbrales['plaquetas_limite_alerta']:,}/mm³)"
        )

    en_fase_critica = (
        datos.dias_evolucion is not None
        and umbrales["dias_fase_critica_min"] <= datos.dias_evolucion <= umbrales["dias_fase_critica_max"]
    )
    fiebre_alta_alerta = (
        datos.temperatura_celsius is not None
        and datos.temperatura_celsius >= umbrales["temperatura_alerta_celsius"]
    )

    alerta_inmediata = len(signos_detectados) >= 1

    if alerta_inmediata:
        clasificacion = "GRUPO_B_O_C_EMERGENCIA_CRITICA"
        accion = (
            "TRASLADO URGENTE INMEDIATO: Acuda a la Sala de Emergencias del Hospital o Centro de Salud Tipo C "
            "más cercano o comuníquese al ECU-911. Prohibido automedicarse con AINEs (ibuprofeno/aspirina)."
        )
    else:
        clasificacion = "GRUPO_A_VIGILANCIA_AMBULATORIA"
        accion = (
            "Manejo ambulatorio con hidratación oral abundante (Sales de Rehidratación Oral), "
            "reposo, vigilancia de signos de alarma cada 4 horas y valoración médica en Centro de Salud MSP (Línea 171)."
        )

    return {
        "alerta_inmediata": alerta_inmediata,
        "clasificacion_msp": clasificacion,
        "signos_detectados": signos_detectados,
        "en_ventana_fase_critica": en_fase_critica,
        "fiebre_sobre_umbral": fiebre_alta_alerta,
        "umbrales_aplicados": umbrales,
        "accion_recomendada": accion,
        "requiere_confirmacion_humana": alerta_inmediata,
    }
