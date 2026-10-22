# Evidencias Técnicas - Semana 2: Integración del Servicio de IA y Sistema de Prompts
**Seminario de Titulación Complexivo – Carrera de Software (UNIANDES 2026)**  
**Caso N.º 05 – Asistente de Orientación en Salud Pública sobre Dengue y Arbovirosis**  
**Grupo 5**

---

## 1. Resumen de Entregables Auditados de la Fase 2 (Semana 2)
Durante la Semana 2 se implementó y certificó la capa de inteligencia artificial desacoplada, cumpliendo con la totalidad de los requisitos exigidos en la guía del seminario y la rúbrica de evaluación:

1. **Decisiones de Arquitectura ([docs/09-decisiones.md](../../docs/09-decisiones.md)):**  
   Formalización de 4 ADRs canónicos bajo el formato Michael Nygard (ADR-001: Selección de Modelos y Fallback Dual, ADR-002: Workflow Determinista vs Agente Autónomo, ADR-003: Almacenamiento Seguro de Secretos y Cumplimiento LOPDP Ecuador por Rafael Minaya, ADR-004: Triaje Determinista Booleano en Python Puro por Luis Cahuana).
2. **Cliente LLM Desacoplado y Resiliente ([app/services/llm.py](../../app/services/llm.py)):**  
   Implementación del `ClienteLLM` con proveedor principal Google Gemini (`gemini-3.8-flash`) y conmutación automática ante fallos a Groq (`openai/gpt-oss-20b`).
3. **Manejo de Saturación y Tasa Límite (Error 429):**  
   Algoritmo de reintentos con espera exponencial y azar (*jitter*) ($1\text{s}, 2\text{s}, 4\text{s}\dots$) y respeto riguroso de cabeceras `Retry-After`.
4. **Esquemas Estrictos de Validación ([app/schemas.py](../../app/schemas.py)):**  
   Definición del esquema `RespuestaAsistente` con configuración `extra="forbid"`, forzando al modelo a entregar salida estructurada libre de alucinaciones.
5. **Regla de Negocio en Código Determinista ([app/main.py](../../app/main.py)):**  
   Cumplimiento del principio *"El modelo propone, el código dispone"*: la detección de signos de alarma de dengue se ejecuta de forma determinista en Python, forzando la derivación inmediata a urgencias o ECU-911 sin delegar decisiones críticas en el modelo.
6. **Sistema de Prompts y Comparativa ([docs/05-prompts.md](../../docs/05-prompts.md)):**  
   Evolución documentada de `system_v1.md`, `system_v2.md` y `system_v3.md` (con las 6 partes obligatorias), evaluada empíricamente contra 10 casos en `eval/entradas_prompts.csv` con tokens y latencia real.
7. **Observabilidad sin Datos Personales ([logs/llm.jsonl](../../logs/llm.jsonl)):**  
   Registro persistente de tokens consumidos, tiempo en ms y estado de proveedor, garantizando la anonimización total de las preguntas de los ciudadanos (cumplimiento LOPDP).

---

## 2. Evidencia de Ejecución de Pruebas Automatizadas (pytest)

Se ejecutó la suite completa de pruebas unitarias y de integración mediante `py -m pytest -v`:

```text
============================= test session starts =============================
platform win32 -- Python 3.14.5, pytest-9.1.1, pluggy-1.7.0 -- C:\Users\rminaya\AppData\Local\Python\pythoncore-3.14-64\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\rminaya\OneDrive - UNIANDES\Octavo\Seminario\Proyecto
plugins: anyio-4.15.1
collecting ... collected 31 items

tests/test_endpoint.py::test_health PASSED                               [  3%]
tests/test_endpoint.py::test_prioridad_la_calcula_el_codigo PASSED       [  6%]
tests/test_endpoint.py::test_fuera_de_dominio_no_tiene_prioridad PASSED  [  9%]
tests/test_endpoint.py::test_proveedor_caido_da_503_con_mensaje_claro PASSED [ 12%]
tests/test_endpoint.py::test_salida_invalida_va_a_revision_humana PASSED [ 16%]
tests/test_endpoint.py::test_entrada_demasiado_larga_se_rechaza_antes_del_modelo PASSED [ 19%]
tests/test_health.py::test_health_check_status_code PASSED               [ 22%]
tests/test_health.py::test_health_check_payload_structure PASSED         [ 25%]
tests/test_health.py::test_root_endpoint PASSED                          [ 29%]
tests/test_integracion_simulado.py::test_json_por_http_con_429_real PASSED [ 32%]
tests/test_llm.py::test_json_valido PASSED                               [ 35%]
tests/test_llm.py::test_pide_el_esquema_al_proveedor PASSED              [ 38%]
tests/test_llm.py::test_json_invalido_se_corrige_una_vez PASSED          [ 41%]
tests/test_llm.py::test_json_invalido_dos_veces_va_a_revision_humana PASSED [ 45%]
tests/test_llm.py::test_429_respeta_retry_after_y_reintenta PASSED       [ 48%]
tests/test_llm.py::test_espera_exponencial_sin_retry_after PASSED        [ 51%]
tests/test_llm.py::test_respuesta_vacia_se_reintenta PASSED              [ 54%]
tests/test_llm.py::test_principal_caido_pasa_al_respaldo PASSED          [ 58%]
tests/test_llm.py::test_clave_invalida_no_se_reintenta PASSED            [ 61%]
tests/test_llm.py::test_todos_caidos_da_error_claro PASSED               [ 64%]
tests/test_llm.py::test_retry_after_muy_largo_va_directo_al_respaldo PASSED [ 67%]
tests/test_mi_caso.py::test_chat_orientacion_exitosa PASSED              [ 70%]
tests/test_mi_caso.py::test_regla_signos_alarma_forzada_en_codigo PASSED [ 74%]
tests/test_mi_caso.py::test_abstencion_fuera_de_dominio PASSED           [ 77%]
tests/test_mi_caso.py::test_proveedor_caido_devuelve_503_limpio PASSED   [ 80%]
tests/test_mi_caso.py::test_salida_invalida_activa_contingencia_humana PASSED [ 83%]
tests/test_mi_caso.py::test_entrada_demasiado_larga_se_rechaza_con_422 PASSED [ 87%]
tests/test_semver_bumper.py::test_release_increment_and_calculation_main PASSED [ 90%]
tests/test_semver_bumper.py::test_snapshot_rc_progression_develop PASSED [ 93%]
tests/test_semver_bumper.py::test_manual_version_override_detection PASSED [ 96%]
tests/test_semver_bumper.py::test_update_app_version_in_file PASSED      [100%]

============================= 31 passed in 3.82s ==============================
```

---

## 3. Evidencia de Respuesta del Endpoint Oficial (`POST /api/chat`)

Al consultar el endpoint interactivo mediante Swagger UI (`http://127.0.0.1:8000/docs`) con un caso que incluye signos de alarma:

**Petición enviada (`Request Body`):**
```json
{
  "texto": "tengo dolor fuerte de barriga, vómitos seguidos, sangrado"
}
```

**Respuesta recibida (`HTTP 200 OK`):**
```json
{
  "respuesta": "El dolor abdominal intenso, los vómitos continuos y el sangrado son signos de alarma graves que indican riesgo de complicaciones del dengue. No tome ningún medicamento en casa, especialmente no antiinflamatorios no esteroideos (ibuprofeno, aspirina, diclofenaco, naproxeno o ketorolaco). Es urgente que acuda a un centro de salud, hospital o llame al ECU-911 para recibir atención médica inmediata. Mantenga la hidratación con agua, caldos y sales de rehidratación oral, evitando bebidas azucaradas o gaseosas. La pronta derivación y evaluación son esenciales para prevenir el choque hemorrágico o hemorragias graves.",
  "se_abstiene": false,
  "derivar_a": "Sala de Emergencias del Hospital más cercano o llamar al ECU-911 de inmediato",
  "fuentes": [
    {
      "documento": "Guías para la atención de enfermos en la Región de las Américas (OPS 2016)",
      "seccion": "Signos de alarma y criterios de hospitalización"
    },
    {
      "documento": "Guía de Práctica Clínica: Prevención y Control del Dengue (MSP Ecuador 2026)",
      "seccion": "Triaje clínico y derivación oportuna"
    }
  ],
  "proveedor": "groq"
}
```

---

## 4. Evidencia de Resiliencia en Vivo y Conmutación Automática (Fallback)
Cuando la API gratuita de Google Gemini alcanzó su cuota de peticiones por minuto (`HTTP 429 Too Many Requests`), el servicio ejecutó la conmutación transparente hacia **Groq (`openai/gpt-oss-20b`)**:

```text
[llm] {"evento": "reintento", "proveedor": "gemini", "intento": 1, "tipo": "RateLimitError", "estado_http": 429, "espera_s": 0.8}
[llm] {"evento": "reintento", "proveedor": "gemini", "intento": 2, "tipo": "RateLimitError", "estado_http": 429, "espera_s": 1.6}
[llm] {"evento": "agotado", "proveedor": "gemini", "intento": 3, "tipo": "RateLimitError", "estado_http": 429, "espera_s": 2.82}
[llm] {"evento": "ok", "proveedor": "groq", "modelo": "openai/gpt-oss-20b", "intento": 1, "latencia_ms": 1091, "tokens_entrada": 1547, "tokens_salida": 601, "fin": "stop"}
```

---

## 5. Evidencia de Observabilidad y Privacidad (logs/llm.jsonl)
El archivo `logs/llm.jsonl` acumula más de 500 registros técnicos de auditoría. Cumple con la Ley Orgánica de Protección de Datos Personales (LOPDP Ecuador) al registrar únicamente variables de rendimiento técnico:

```json
{"evento": "ok", "proveedor": "groq", "modelo": "openai/gpt-oss-20b", "intento": 1, "latencia_ms": 1091, "tokens_entrada": 1547, "tokens_salida": 601, "fin": "stop"}
```
