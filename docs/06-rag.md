# 06. Arquitectura e Implementación de RAG (Generación Aumentada por Recuperación)

**Proyecto:** Asistente de Orientación en Salud Pública sobre Dengue y Arbovirosis  
**Seminario de Titulación Complexivo – UNIANDES 2026**  
**Caso N.º 05 – Grupo 5**

---

## 1. Justificación de la Estrategia de Fragmentación (Chunking)

### 1.1 ¿Por qué fragmentación por Secciones Temáticas y no por párrafos fijos?
A diferencia de los códigos normativos legales (como el Código del Trabajo o la LOSNCP) que se estructuran de forma granular por artículos numerados (`Art. 188`), las **guías clínicas de práctica médica de la OPS y los lineamientos del MSP** no se dividen por artículos, sino por **secciones temáticas clínicas continuas**.

Si se utilizara una estrategia de corte ciego por tamaño de caracteres (ej. bloques arbitrarios de 500 caracteres):
- Se cortarían oraciones médicas por la mitad.
- Un signo de alarma (ej. *"dolor abdominal intenso"*) quedaría desvinculado de su consecuencia clínica obligatoria (*"derivación urgente a sala de emergencias"*).
- El modelo generativo recibiría fragmentos incompletos o huérfanos sin contexto, provocando alucinaciones clínicas.

### 1.2 Parámetros de Fragmentación Adoptados
Siguiendo las directrices oficiales de la **Guía de RAG por caso (Módulo 3)**:
- **Estrategia:** Corte por sección temática canónica.
- **Patrón de división (Regex):** `/(?=SECCIÓN\s+\d+)/`
- **Cabecera obligatoria:** `/^SECCIÓN\s+\d+/`
- **Longitud por fragmento:** Entre **500 y 800 palabras** por sección.
- **Preservación de Títulos:** Cada fragmento conserva intacto su encabezado y título canónico (ej. `SECCIÓN 3. Signos de alarma de dengue y criterios de derivación urgente`), permitiendo que el LLM cite con precisión:  
  *«Según la Guía de la OPS, sección 3...»*.

---

## 2. Catálogo de Secciones Normativas Indexadas

| ID Fragmento | Documento Fuente | Sección Canónica | Tema | Año | Contenido Clínico Fundamental |
|:---:|---|---|:---:|:---:|---|
| `ops-sec-01` | Guía OPS dengue | SECCIÓN 1. Qué es el dengue, transmisión y fases clínicas | `sintomas` | 2024 | Vector *Aedes aegypti*, serotipos DENV 1-4, fase febril (2-7 días), fase crítica y fase de recuperación. |
| `ops-sec-02` | Guía OPS dengue | SECCIÓN 2. Prevención y control vectorial en el hogar | `prevencion` | 2024 | Eliminación de criaderos, lavado de tanques, repelentes autorizados (DEET/Icaridina) y mosquiteros. |
| `ops-sec-03` | Guía OPS dengue | SECCIÓN 3. Signos de alarma y criterios de derivación | `alarma` | 2024 | Dolor abdominal continuo, vómitos persistentes, sangrado de mucosas, letargo/lipotimia. **Derivación 911**. |
| `ops-sec-04` | Guía OPS dengue | SECCIÓN 4. Medicamentos prohibidos y contraindicaciones | `tratamiento` | 2024 | **Prohibición absoluta de AINEs** (ibuprofeno, aspirina). Dosis segura de paracetamol e hidratación oral. |
| `msp-sec-05` | Lineamiento MSP | SECCIÓN 5. Clasificación clínica y niveles de atención | `tratamiento` | 2026 | Grupos A (ambulatorio), B (hospitalario CS Tipo C) y C (UCI). Línea 171 y ECU-911 en Ecuador. |
| `msp-sec-06` | Lineamiento MSP | SECCIÓN 6. Protocolo de hidratación oral en el hogar | `tratamiento` | 2026 | Sales de Rehidratación Oral (SRO), líquidos caseros, prohibición de bebidas gaseosas y vigilancia de diuresis. |

---

## 3. Modelo de Embeddings y Base Vectorial ChromaDB

### 3.1 Base Vectorial Persistente
Se seleccionó **ChromaDB** como base de datos vectorial local bajo modo cliente persistente (`chromadb.PersistentClient(path="data/index/")`).
- **Ventaja de diseño:** Sobrevive a reinicios del servidor, no depende de servicios cloud de pago y opera con latencia sub-milisegundo en búsquedas por similitud de coseno.

### 3.2 Modelo de Embeddings
Se adoptó la función de embedding local optimizada con ONNX Runtime (`all-MiniLM-L6-v2`), que transforma los textos en vectores densos de 384 dimensiones:
- **Reproducibilidad:** Se ejecuta 100% en local sin gastar saldo de API de OpenAI ni Gemini.
- **Idempotencia:** Ante cualquier máquina de evaluación limpia, el script `scripts/ingest.py` recrea exactamente el mismo índice vectorial en segundos.

---

## 4. Esquema de Metadatos y Filtros de Búsqueda

Para evitar que el asistente mezcle prevención comunitaria con emergencias clínicas, cada fragmento almacena 4 metadatos obligatorios:
1. `documento`: Nombre legible de la institución fuente (*"Guía OPS dengue"* o *"Lineamiento MSP Ecuador"*).
2. `seccion`: Identificador formal para la cita textual (*"SECCIÓN 3. Signos de alarma..."*).
3. `tema`: Categoría de filtrado (`sintomas`, `prevencion`, `alarma`, `tratamiento`).
4. `anio`: Año de emisión normativa (*"2024"* / *"2026"*) para validar vigencia.

---

## 5. Separación Arquitectónica: ¿Qué va al RAG y qué no?

Siguiendo la instrucción estricta de la cátedra:
- **Al RAG van:** Las guías clínicas, protocolos de manejo, medidas de prevención y señales de alarma (documentos no estructurados).
- **NO va al RAG:** El listado de centros de salud públicos de GeoSalud Ecuador (`data/geosalud_ecuador.json`). Este listado es una base de datos tabular estructurada que alimenta exclusivamente a la **herramienta determinista `ubicar_establecimiento(ciudad_o_canton)`**. Buscar establecimientos de salud por similitud vectorial semántica sería un error arquitectónico porque el modelo podría inventar hospitales que no existen en esa parroquia.
