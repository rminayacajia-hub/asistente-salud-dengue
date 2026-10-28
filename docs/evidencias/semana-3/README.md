# Evidencias Técnicas - Semana 3: RAG Normativo, Base Vectorial y GeoSalud Determinista
**Seminario de Titulación Complexivo – Carrera de Software (UNIANDES 2026)**  
**Caso N.º 05 – Asistente de Orientación en Salud Pública sobre Dengue y Arbovirosis**  
**Grupo 5**

---

## 1. Resumen de Entregables Auditados de la Fase 3 (Semana 3)

Durante la Semana 3 se diseñó, implementó y certificó la capa de **Generación Aumentada por Recuperación (RAG)** y la herramienta determinista de **GeoSalud**, cumpliendo al 100% con los requerimientos de la guía docente y la rúbrica de evaluación:

1. **Ingesta Reproducible ([scripts/ingest.py](../../scripts/ingest.py)):**  
   Script automatizado que procesa el corpus normativo oficial (OPS y MSP), aplica la técnica de **chunking por sección temática canónica** (500 a 800 palabras) guiado por el patrón regex `/(?=SECCIÓN\s+\d+)/`, extrae 5 metadatos obligatorios y genera la base vectorial persistente.

2. **Base Vectorial Persistente ChromaDB ([data/index/](../../data/)):**  
   Base de datos vectorial local configurada con `all-MiniLM-L6-v2` mediante ONNX Runtime local (79 MB). Garantiza costo cero de APIs, cero consumo de tokens externos y reproducibilidad total en entornos de integración continua (CI/CD).

3. **Documento Técnico de Justificación RAG ([docs/06-rag.md](../../docs/06-rag.md)):**  
   Documentación detallada que formaliza la estrategia de fragmentación clínica, el esquema de metadatos, la justificación del modelo de embeddings y la regla de separación arquitectónica de datos tabulares.

4. **Servicio Recuperador RAG Desacoplado ([app/services/retriever.py](../../app/services/retriever.py)):**  
   Módulo construido bajo el principio de **Responsabilidad Única (SOLID - SRP)**. Realiza búsquedas vectoriales por similitud semántica con anclaje de dominio médico en español, descarta consultas irrelevantes mediante umbral calibrado en `1.28` e implementa **modo degradado seguro (*graceful fallback*)** si la base vectorial no se encuentra disponible.

5. **Configuración Desacoplada ([config/umbrales.json](../../config/umbrales.json)):**  
   Centraliza en formato JSON los hiperparámetros operativos (`top_k: 2`, `distancia_maxima: 1.28`) y los umbrales de triaje clínico (fase crítica de 3 a 7 días, vómitos $\ge 3$, temperatura $\ge 38.5^\circ\text{C}$, plaquetas $\le 100\,000$), erradicando números mágicos (*hardcoded values*) del código fuente.

6. **Esquema Estricto con 5 Metadatos Canónicos ([app/schemas.py](../../app/schemas.py)):**  
   Actualización de la clase `Fuente(Estricto)` para capturar obligatoriamente:
   - `id`: Identificador oficial del fragmento (`ops-sec-01` a `ops-sec-04`, `msp-sec-05`, `msp-sec-06`, `CS-GYE-001`).
   - `documento`: Institución normativa (`Guía OPS dengue`, `Lineamiento MSP Ecuador`, `Directorio GeoSalud MSP`).
   - `seccion`: Título formal de la sección temática o red cantonal.
   - `tema`: Categoría temática de triaje (`sintomas`, `alarma`, `tratamiento`, `prevencion`, `derivacion`).
   - `anio`: Año oficial de vigencia (`2024`, `2026`).

7. **Herramienta Determinista GeoSalud ([app/tools/geosalud.py](../../app/tools/geosalud.py)):**  
   Aplica la **Regla Crítica del Módulo 3**: los datos tabulares estructurados (14 hospitales y centros tipo C de [`data/geosalud_ecuador.json](../../data/geosalud_ecuador.json)) **NUNCA se vectorizan en un RAG**. Se consultan mediante un algoritmo determinista en Python con normalización de tildes y mayúsculas, filtros de emergencia 24h, UCI y pediatría.

8. **Frontend Interactivo Streamlit ([frontend/app.py](../../frontend/app.py)):**  
   - Despliegue del acordeón **«📚 Fuentes normativas consultadas (RAG / GeoSalud)»** con la ficha bibliográfica estructurada completa.
   - Tarjetas diferenciadas por criticidad: roja urgente ante signos de alarma (**🚨 DERIVACIÓN MÉDICA URGENTE**) y azul informativa con datos de contacto verificados (**🏥 ESTABLECIMIENTO DE SALUD SUGERIDO (GEOSALUD)**).
   - Selector en barra lateral para explorar la red de hospitales MSP por cantón en tiempo real.

9. **Suite de Pruebas Automatizadas ([tests/](../../tests/)):**  
   Ampliación de la suite de pruebas a **50 pruebas unitarias pasando al 100% en verde** en menos de 11 segundos (`tests/test_rag.py`, `tests/test_geosalud.py`, `tests/test_mi_caso.py`), garantizando cobertura completa de recuperación, filtrado, fallback y geolocalización.

---

## 2. Pruebas de Búsqueda RAG y Citas en Vivo (Semana 3)

Se ejecutaron pruebas representativas contra el backend FastAPI operativo (`http://localhost:8000/api/chat`), certificando la correcta inyección de citas y comportamiento seguro:

| # | Tipo de Consulta | Entrada del Ciudadano | Salida Estructurada (Fuentes / Derivación) | Estado RAG / GeoSalud |
|:---:|---|---|---|:---:|
| **1** | **Síntomas Iniciales** | *«Me duele la cabeza y tengo dolor de estomago!»* | • `[msp-sec-05]` Lineamiento MSP (2026): *SECCIÓN 5. Clasificación clínica* \| Tema: `tratamiento`<br>• `[ops-sec-01]` Guía OPS (2024): *SECCIÓN 1. Fases clínicas y síntomas* \| Tema: `sintomas` | ✅ **RAG Activo**<br>Recupera 2 fuentes normativas completas. |
| **2** | **Signos de Alarma** | *«Tengo dolor en la barriga muy fuerte y vómitos continuos, estamos en Guayaquil»* | • `[ops-sec-03]` Guía OPS (2024): *SECCIÓN 3. Signos de alarma y criterios de derivación* \| Tema: `alarma`<br>• `derivar_a`: *Hospital de Infectología Dr. José Daniel Rodríguez Maridueña (Guayaquil - Julián Coronel y Esmeraldas, Tel: (04) 228-7400)* | 🚨 **Regla de Oro + GeoSalud**<br>Alerta roja y hospital específico de la zona. |
| **3** | **Medicamentos Prohibidos** | *«¿Puedo tomar ibuprofeno o aspirina para calmar la fiebre?»* | • `[ops-sec-04]` Guía OPS (2024): *SECCIÓN 4. Medicamentos prohibidos y contraindicaciones* \| Tema: `tratamiento`<br>• Prohibición tajante de AINEs por riesgo de hemorragias. | 🛡️ **Salvaguarda Clínica Activa**<br>Cita sección oficial de contraindicaciones. |
| **4** | **Prevención Comunitaria** | *«¿Cómo eliminar los criaderos de mosquitos en mi patio?»* | • `[ops-sec-02]` Guía OPS (2024): *SECCIÓN 2. Prevención y control vectorial en el hogar* \| Tema: `prevencion`<br>• Explica cepillado de tanques, abate y repelentes DEET. | 🌿 **Educación Sanitaria**<br>Orientación preventiva comunitaria. |
| **5** | **Geolocalización Directa** | *«Estoy en guayaquil a donde voy.»* | • `[CS-GYE-001]` Directorio GeoSalud MSP (2026): *Establecimientos en Guayaquil* \| Tema: `derivacion`<br>• Detalla dirección, teléfono y emergencia 24h. | 🏥 **GeoSalud Determinista**<br>Cero alucinación de teléfonos o direcciones. |
| **6** | **Consulta Fuera de Dominio** | *«¿Cuál es la receta para preparar pastel de chocolate?»* | • `se_abstiene: true`<br>• `fuentes: []`<br>• `derivar_a: null`<br>• Explicación empática de que su ámbito es exclusivamente dengue y salud pública. | 🚫 **Filtro de Umbral Exitoso**<br>Distancia > 1.28 descartada sin alucinación. |

---

## 3. Ejemplo de Payload JSON Devuelto por el Backend

A continuación se presenta la evidencia técnica del JSON estructurado entregado por el endpoint `/api/chat` ante la consulta del ciudadano:

```json
{
  "respuesta": "El dolor de cabeza intenso y el malestar estomacal pueden ser síntomas iniciales de la fase febril del dengue. Es indispensable vigilar atentamente si aparecen signos de alarma como dolor abdominal continuo e intenso, vómitos persistentes o sangrado. Está estrictamente contraindicado automedicarse con antiinflamatorios (como aspirina o ibuprofeno) debido al alto riesgo de desencadenar hemorragias graves. Mantenga reposo e hidratación constante con sales de rehidratación oral y acuda a un centro de salud para evaluación clínica.",
  "se_abstiene": false,
  "derivar_a": "Centro de Salud / Hospital MSP más cercano o llamar al ECU-911 de forma urgente si presenta signos de alarma",
  "fuentes": [
    {
      "id": "msp-sec-05",
      "documento": "Lineamiento MSP Ecuador",
      "seccion": "SECCIÓN 5. Clasificación clínica del dengue y niveles de atención en Ecuador",
      "tema": "tratamiento",
      "anio": "2026"
    },
    {
      "id": "ops-sec-01",
      "documento": "Guía OPS dengue",
      "seccion": "SECCIÓN 1. Qué es el dengue, transmisión y fases clínicas",
      "tema": "sintomas",
      "anio": "2024"
    }
  ],
  "proveedor": "gemini",
  "alerta_signo_alarma": false
}
```

---

## 4. Certificación de Resiliencia: Modo Degradado Seguro (Graceful Degradation)

Se validó de forma automatizada (`tests/test_rag.py::test_retriever_fallback_graceful_si_no_existe_indice`) el comportamiento del sistema ante la ausencia física o corrupción del directorio vectorial `data/index/`:

```python
# Simulación de falla de base vectorial
retriever = RecuperadorDengue(ruta_indice="data/directorio_inexistente_12345")
assert retriever.esta_disponible is False

resultado = retriever.recuperar("¿Qué es el dengue?")
assert resultado.relevante is False
assert resultado.fuentes == []
assert resultado.texto_contexto == ""
```

* **Comportamiento en Producción:**  
  La API FastAPI **nunca colapsa con error 500**. Si la base vectorial no está disponible, el sistema emite un log de advertencia y atiende al ciudadano sustentándose en las salvaguardas base de su prompt versionado (`system_v3.md`), manteniendo la **Regla de Oro determinista en Python** 100% activa para proteger la vida del paciente.

---

## 5. Reporte de Ejecución de Pruebas Automatizadas (pytest)

Ejecución de la suite completa tras integrar RAG y GeoSalud:

```text
============================= test session starts =============================
platform win32 -- Python 3.14.5, pytest-9.1.1, pluggy-1.7.0
rootdir: C:\Users\rminaya\OneDrive - UNIANDES\Octavo\Seminario\Proyecto
collected 50 items

tests/test_config.py PASSED                                            [ 10%]
tests/test_endpoint.py PASSED                                          [ 22%]
tests/test_geosalud.py PASSED                                           [ 38%]
tests/test_health.py PASSED                                            [ 44%]
tests/test_integracion_simulado.py PASSED                              [ 46%]
tests/test_llm.py PASSED                                               [ 68%]
tests/test_mi_caso.py PASSED                                           [ 84%]
tests/test_rag.py PASSED                                               [ 92%]
tests/test_semver_bumper.py PASSED                                     [100%]

======================== 50 passed, 1 warning in 10.75s ========================
```

---

## 6. Actualización de Decisiones de Arquitectura (ADRs Semana 3)

Se incorporaron dos nuevos registros de decisión arquitectónica en [`docs/09-decisiones.md](../../docs/09-decisiones.md):
- **ADR-005:** *Estrategia de Fragmentación por Secciones Temáticas Canónicas y Base Vectorial ChromaDB Local*.
- **ADR-006:** *Separación Arquitectónica Estricta de Datos Tabulares (GeoSalud Determinista vs. RAG Vectorial)*.
