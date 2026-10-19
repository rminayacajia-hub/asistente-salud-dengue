# Evidencias Técnicas - Semana 1: Definición del Problema y Diseño de la Solución
**Seminario de Titulación Complexivo – Carrera de Software (UNIANDES 2026)**  
**Caso N.º 05 – Asistente de Orientación en Salud Pública sobre Dengue y Arbovirosis**  
**Grupo 5**

---

## 1. Resumen de Entregables Auditados de la Fase 1
Durante la Semana 1 se estructuró la base conceptual, normativa, técnica y de código del proyecto, cumpliendo con la totalidad de los requisitos estipulados por la guía del seminario:

1. **Definición de Propuesta ([docs/01-propuesta.md](../../docs/01-propuesta.md)):** Alcance positivo y negativo riguroso, matriz de riesgos éticos y justificación de Gemini 1.5 Flash.
2. **Ingeniería de Requisitos ([docs/02-requisitos.md](../../docs/02-requisitos.md)):** 8 Historias de Usuario en formato Gherkin y 5 Requisitos No Funcionales medibles.
3. **Investigación Empírica ([docs/02-anexo-preguntas.md](../../docs/02-anexo-preguntas.md)):** Estudio de campo con 15 preguntas en escala Likert (`ANALISIS DE PREGUNTAS.pdf` y `RESPUESTAS.xlsx`) y matriz de trazabilidad hacia las historias de usuario.
4. **Diseño de Arquitectura ([docs/03-arquitectura.md](../../docs/03-arquitectura.md)):** Diagramas Mermaid (modular, clases Pydantic, DFD niveles 0 y 1) y descripción de flujos.
5. **Inventario de Fuentes Oficiales ([docs/04-fuentes.md](../../docs/04-fuentes.md)):** Catalogación APA 7.ª con permalinks verificables (OMS 2009, OPS 2016, OPS 2022, MSP 2026, GeoSalud) y estrategia de chunking clínico.
6. **Configuración del Repositorio:** `.gitignore` protegiendo secretos, `.env.example`, `requirements.txt` y `README.md` formal.

---

## 2. Evidencia de Ejecución de Pruebas Automatizadas (pytest)

Se ejecutó la suite de pruebas unitarias sobre el backend FastAPI mediante `pytest tests/`, verificando el comportamiento del endpoint de salud y el contrato de datos:

```text
============================= test session starts =============================
platform win32 -- Python 3.14.5, pytest-9.1.1, pluggy-1.7.0
rootdir: C:\Users\rminaya\OneDrive - UNIANDES\Octavo\Seminario\Proyecto
plugins: anyio-4.15.1
collected 3 items

tests\test_health.py ...                                                 [100%]

======================== 3 passed, 2 warnings in 0.55s ========================
```

### Detalle de las Pruebas Certificadas:
* `test_health_check_status_code`: Valida que `GET /health` responda con código HTTP `200 OK`.
* `test_health_check_payload_structure`: Valida que el payload JSON cumpla estrictamente con el modelo Pydantic `HealthResponse` (campos `status`, `environment`, `service`, `version` y `timestamp`).
* `test_root_endpoint`: Valida que la ruta raíz informativa `GET /` responda con HTTP `200 OK` y declare el principio de triaje determinista en Python puro.

---

## 3. Evidencia de Respuesta del Endpoint de Salud (`GET /health`)

Al realizar una petición HTTP contra el microservicio en ejecución local, se obtiene el siguiente payload JSON validado:

```json
{
  "status": "ok",
  "environment": "development",
  "service": "asistente-dengue-backend",
  "version": "1.0.0",
  "timestamp": "2026-10-15T15:25:28.123456Z"
}
```

---

## 4. Evidencia de Levantamiento Empírico de Campo

Se integraron al repositorio los insumos primarios de la investigación ciudadana:
- `data/raw/preguntas`: Cuestionario de 15 preguntas aplicado a ciudadanos y cuidadores.
- `data/raw/RESPUESTAS.xlsx`: Matriz de datos con las respuestas tabuladas.
- `data/raw/ANALISIS DE PREGUNTAS.pdf`: Informe estadístico con porcentajes de acuerdo y análisis clínico.
- `docs/02-anexo-preguntas.md`: Documento de síntesis y correlación con los requisitos funcionales.

---

## 5. Evidencia de Cumplimiento de las Reglas de Oro de Seguridad

* **Regla 5 (Secretos nunca en Git):**  
  El archivo `.gitignore` incluye la exclusión explícita de `.env` y de cualquier variante local (`.env.local`, `.env.*.local`).  
  El repositorio solo versiona [.env.example](../../.env.example), que documenta las variables sin exponer ninguna clave real de API.
* **Regla 4 (Configuración desacoplada):**  
  Los parámetros de modelos, umbrales y rutas residen en [config/settings.py](../../config/settings.py), garantizando que ningún valor esté quemado en el código fuente.
