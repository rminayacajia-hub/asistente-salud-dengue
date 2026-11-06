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

Siguiendo la instrucción estricta de la cátedra y la literatura sobre arquitecturas aumentadas por recuperación (Lewis et al., 2020; Gao et al., 2024):
- **Al RAG van:** Las guías clínicas, protocolos de manejo, medidas de prevención y señales de alarma (documentos no estructurados).
- **NO va al RAG:** El listado de centros de salud públicos de GeoSalud Ecuador (`data/geosalud_ecuador.json`). Este listado es una base de datos tabular estructurada que alimenta exclusivamente a la **herramienta determinista `ubicar_establecimiento(ciudad_o_canton)`** (Schick et al., 2023; Anthropic, 2024). Buscar establecimientos de salud por similitud vectorial semántica sería un error arquitectónico porque el modelo podría inventar hospitales que no existen en esa parroquia.

> **Nota de Evolución Arquitectónica (Semana 1 $\rightarrow$ Semana 3):**  
> En la propuesta preliminar de `docs/04-fuentes.md` (Semana 1) se contempló inicialmente un divisor recursivo por encabezados Markdown genéricos (`\n## `). Durante la implementación de la Semana 3, tras analizar la estructura interna real de los lineamientos clínicos de la OPS y del MSP y el fenómeno de pérdida de atención en contextos mal recortados (*Lost in the Middle*, Liu et al., 2024), se perfeccionó la estrategia hacia un **corte por sección temática canónica (`/(?=SECCIÓN\s+\d+)/`, de 500 a 800 palabras)**. Esto garantiza que ninguna señal de alarma ni contraindicación farmacológica quede separada de su protocolo de derivación.

---

## 6. Controles de Seguridad en el Pipeline RAG (OWASP LLM Top 10)

Para mitigar el riesgo de **Inyección Indirecta de Prompt** (Greshake et al., 2023) y **Desinformación / Alucinación** (Ji et al., 2023; OWASP Foundation, 2025):
1. **Saneamiento y Origen Confiable en la Ingesta (`scripts/ingest.py`):** Solo se indexan documentos normativos curados del directorio local auditado, verificando que cada sección cumpla la estructura canónica `^SECCIÓN\s+\d+` antes de generar embeddings.
2. **Delimitación Estricta de Contexto No Confiable (`app/main.py`):** Los fragmentos recuperados por `RecuperadorDengue` se encapsulan bajo delimitadores explícitos (`=== GUÍAS OFICIALES OPS / MSP (RAG) ===` y `--- FRAGMENTO OFICIAL #N ---`), instruyendo en `system_v3.md` que el contexto se trate como datos de consulta y jamás como comandos ejecutables.
3. **Inyección Determinista de Citas en Backend:** El LLM tiene prohibido inventar el arreglo `fuentes`. Es el código Python en `app/main.py` el que adjunta los objetos `Fuente` verificados provenientes de ChromaDB y GeoSalud.

---

## 7. Referencias Académicas (APA 7.ª Edición)

1. **Anthropic.** (2024, 19 de diciembre). *Building effective agents*. https://www.anthropic.com/research/building-effective-agents
2. **Es, S., James, J., Espinosa-Anke, L., & Schockaert, S.** (2024). RAGAS: Automated evaluation of retrieval augmented generation. *Proceedings of EACL 2024: System Demonstrations*. https://arxiv.org/abs/2309.15217
3. **Gao, Y., Xiong, Y., Gao, X., Jia, K., Pan, J., Bi, Y., Dai, Y., Sun, J., Wang, M., & Wang, H.** (2024). Retrieval-augmented generation for large language models: A survey. *arXiv*. https://arxiv.org/abs/2312.10997
4. **Greshake, K., Abdelnabi, S., Mishra, S., Endres, C., Holz, T., & Fritz, M.** (2023). Not what you've signed up for: Compromising real-world LLM-integrated applications with indirect prompt injection. *Proceedings of the 16th ACM Workshop on Artificial Intelligence and Security*. https://arxiv.org/abs/2302.12173
5. **Ji, Z., Lee, N., Frieske, R., Yu, T., Su, D., Xu, Y., Ishii, E., Bang, Y., Madotto, A., & Fung, P.** (2023). Survey of hallucination in natural language generation. *ACM Computing Surveys, 55*(12), 1–38. https://doi.org/10.1145/3571730
6. **Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Küttler, H., Lewis, M., Yih, W., Rocktäschel, T., Riedel, S., & Kiela, D.** (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. *Advances in Neural Information Processing Systems, 33*. https://arxiv.org/abs/2005.11401
7. **Liu, N. F., Lin, K., Hewitt, J., Paranjape, A., Bevilacqua, M., Petroni, F., & Liang, P.** (2024). Lost in the middle: How language models use long contexts. *Transactions of the Association for Computational Linguistics, 12*, 157–173. https://arxiv.org/abs/2307.03172
8. **OWASP Foundation.** (2025). *OWASP Top 10 for Large Language Model Applications 2025*. https://genai.owasp.org/llm-top-10/
9. **Schick, T., Dwivedi-Yu, J., Dessì, R., Raileanu, R., Lomeli, M., Zettlemoyer, L., Cancedda, N., & Scialom, T.** (2023). Toolformer: Language models can teach themselves to use tools. *Advances in Neural Information Processing Systems, 36*. https://arxiv.org/abs/2302.04761
