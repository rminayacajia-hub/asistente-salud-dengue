# 09. Registro de Decisiones de Arquitectura (ADR)
**Seminario de Titulación Complexivo – Carrera de Software (UNIANDES 2026)**  
**Caso N.º 05 – Asistente de Orientación en Salud Pública sobre Dengue y Arbovirosis (GuíaVital)**  
**Grupo 5**

Este documento recopila las decisiones arquitectónicas estructurales tomadas por el equipo para el desarrollo del Producto Mínimo Viable (MVP) y las fases subsiguientes, bajo el formato estándar de **Michael Nygard**. Cada decisión refleja el balance técnico entre rendimiento, costos, resiliencia y el compromiso ético innegociable con la seguridad del paciente.

---

## Índice de Decisiones

* [ADR-001: Selección del Proveedor y Modelo Generativo Principal y de Respaldo](#adr-001-selección-del-proveedor-y-modelo-generativo-principal-y-de-respaldo)
* [ADR-002: Patrón de Integración Arquitectónica: Workflow de Enrutamiento vs. Agente Autónomo](#adr-002-patrón-de-integración-arquitectónica-workflow-de-enrutamiento-vs-agente-autónomo)
* [ADR-003: Gestión de Credenciales Seguras y Protección de Datos Personales de Salud (LOPDP Ecuador)](#adr-003-gestión-de-credenciales-seguras-y-protección-de-datos-personales-de-salud-lopdp-ecuador)
* [ADR-004: Determinismo Estricto en la Evaluación de Signos de Alarma (Reglas en Código vs. Razonamiento del Modelo)](#adr-004-determinismo-estricto-en-la-evaluación-de-signos-de-alarma-reglas-en-código-vs-razonamiento-del-modelo)
* [ADR-005: Estrategia de Chunking por Secciones Temáticas Canónicas y Base Vectorial ChromaDB Local](#adr-005-estrategia-de-chunking-por-secciones-temáticas-canónicas-y-base-vectorial-chromadb-local)
* [ADR-006: Separación Arquitectónica Estricta de Datos Tabulares (GeoSalud Determinista vs. RAG Vectorial)](#adr-006-separación-arquitectónica-estricta-de-datos-tabulares-geosalud-determinista-vs-rag-vectorial)

---

## ADR-001: Selección del Proveedor y Modelo Generativo Principal y de Respaldo

* **Estado:** Aceptado
* **Fecha:** 2026-10-19
* **Responsable:** Wilson Salinas (*Builder*)

### 1. Contexto del Problema
El sistema requiere procesar consultas ciudadanas y realizar síntesis informativas sobre guías clínicas extensas emitidas por la Organización Panamericana de la Salud (OPS) y el Ministerio de Salud Pública del Ecuador (MSP). En el contexto académico del seminario se trabaja sobre capas de servicio gratuitas (*free tiers*). 

Se identificaron dos restricciones operativas críticas:
1. Las guías clínicas y fragmentos normativos exigen una **ventana de contexto amplia** para inyectar fragmentos relevantes sin truncamiento.
2. Los límites de tasa por minuto (*Tokens Per Minute - TPM*) en planes gratuitos suelen ser muy reducidos en proveedores como Groq (6,000 a 12,000 TPM), lo que provocaría bloqueos recurrentes por error `HTTP 429 (Too Many Requests)` tras apenas una o dos consultas con contexto RAG extenso.
3. Para la demostración técnica en vivo y la posterior evaluación docente, el sistema no puede depender de un único punto de falla que inhabilite el servicio si el proveedor primario agota su cuota.

### 2. Opciones Consideradas

* **Opción 1: Groq (Llama-3.1-8B-Instant) como proveedor principal y Gemini como respaldo.**  
  * *Ventajas:* Latencia de inferencia extraordinariamente baja (velocidad cercana a 500 tokens/segundo), proporcionando un *Time-to-First-Token* (TTFT) inferior a 800 ms.
  * *Desventajas:* Su cuota gratuita de 6,000 a 12,000 TPM es insuficiente para un flujo RAG que inyecte 3 o 4 fragmentos normativos por consulta (cada consulta consumiría entre 1,500 y 2,500 tokens de contexto, agotando la cuota tras 3 peticiones simultáneas).
* **Opción 2: Google AI Studio (Gemini 2.0 / 1.5 Flash) como proveedor principal y Groq (Llama-3.1-8B-Instant) como respaldo.** *(Seleccionada)*  
  * *Ventajas:* Gemini Flash ofrece una ventana de contexto de hasta 2 millones de tokens y una generosa cuota gratuita de **1,000,000 TPM** y 15 RPM, ideal para procesar fragmentos clínicos sin riesgo de saturación prematura. Groq actúa como mecanismo de contingencia (*failover*) de alta velocidad si Google experimenta intermitencia.
  * *Desventajas:* Exige programar en el backend (`app/services/llm.py`) un adaptador polimórfico desacoplado que normalice los formatos de respuesta de ambos SDKs.
* **Opción 3: Modelos Locales en el Servidor (Ollama / Llama-cpp).**  
  * *Ventajas:* Independencia total de APIs externas y cuotas de consumo.
  * *Desventajas:* Inviable para el entorno de despliegue en la nube gratuito (Render / Cloud Run) por requerimientos severos de GPU y memoria RAM (mínimo 8 GB a 16 GB), incompatibles con contenedores estándar de 512 MB.

### 3. Decisión Adoptada
Se adopta la **Opción 2**: Google AI Studio con **Gemini 2.0 / 1.5 Flash** como proveedor principal y **Groq (Llama-3.1-8B-Instant)** como proveedor de respaldo (*failover*).

La llamada se encapsula en `app/services/llm.py`. Ante un error `HTTP 429` o tiempo de espera agotado en Gemini, el servicio activa un reintento con *exponential backoff* y, de persistir la indisponibilidad, conmuta transparentemente a Groq notificando al usuario en los metadatos de respuesta.

### 4. Consecuencias
* **Positivas:** Capacidad holgada para inyectar fragmentos RAG extensos; alta disponibilidad garantizada durante las evaluaciones docentes; resiliencia automática ante caídas de API.
* **Negativas asumidas:** Mayor esfuerzo de codificación en el servicio LLM para soportar dos librerías cliente (`google-generativeai` y `groq`) manteniendo una interfaz pública idéntica.

---

## ADR-002: Patrón de Integración Arquitectónica: Workflow de Enrutamiento vs. Agente Autónomo

* **Estado:** Aceptado
* **Fecha:** 2026-10-19
* **Responsable:** Wilson Salinas (*Builder*)

### 1. Contexto del Problema
El asistente GuíaVital debe ofrecer un diálogo empático y educativo sobre prevención y síntomas, pero debe implementar una lista de verificación de signos de alarma que **derive de forma obligatoria al 100% de los pacientes en riesgo** a un establecimiento de salud o al ECU-911. 

Se debe definir el grado de autonomía que tendrá el modelo de lenguaje generativo frente al control del flujo de la conversación y la toma de decisiones clínicas.

### 2. Opciones Consideradas

* **Opción 1: Enrutamiento Determinista por Tipo de Consulta (Workflow).** *(Seleccionada)*  
  * *Ventajas:* El backend clasifica la intención o recibe entradas estructuradas. Si la consulta involucra síntomas agudos o signos de alarma, la ejecución se bifurca hacia código condicional rígido en Python. El LLM jamás decide si un paciente debe ser derivado; el control del flujo crítico permanece 100% en software determinista.
  * *Desventajas:* Requiere una máquina de estados o enrutador más estructurado en FastAPI, limitando la improvisación conversacional en situaciones de triaje.
* **Opción 2: Agente Autónomo con Herramientas (ReAct / Tool Calling libre desde la Fase 2).**  
  * *Ventajas:* Conversación altamente fluida; el LLM infiere cuándo llamar a la función de evaluación basándose en el diálogo libre.
  * *Desventajas:* **Riesgo inaceptable de seguridad clínica.** Los LLMs son probabilísticos y sufren de sesgos y alucinaciones. Si el modelo malinterpreta una descripción coloquial (ej. *"me duele la boca del estómago y estoy mareado"*) y decide no invocar la herramienta, se genera un **falso negativo**, lo que podría ocasionar la muerte del paciente por choque hipovolémico.
* **Opción 3: Cero IA para Síntomas (Formulario Clásico sin LLM).**  
  * *Ventajas:* Simplicidad absoluta y cero costo de inferencia.
  * *Desventajas:* Pérdida de la empatía, claridad explicativa y adaptación pedagógica que el modelo generativo aporta a la orientación comunitaria en salud pública.

### 3. Decisión Adoptada
Se adopta la **Opción 1: Patrón de Enrutamiento (Workflow de Backend)**.  
El asistente utiliza IA Generativa para la educación sanitaria, prevención comunitaria y síntesis de guías clínicas, pero **subordina la evaluación de peligro a una ruta determinista estricta controlada por software**. Si el usuario activa el checklist o reporta signos de peligro, el backend intercepta el flujo y ejecuta la regla lógica, bloqueando cualquier razonamiento probabilístico del LLM sobre la urgencia del traslado.

### 4. Consecuencias
* **Positivas:** Cero falsos negativos en el triaje de signos de alarma; cumplimiento riguroso de las salvaguardas éticas del caso; trazabilidad predecible para pruebas automatizadas.
* **Negativas asumidas:** La transición entre la conversación abierta y el checklist guiado requiere que el frontend y el backend gestionen contratos de datos diferenciados (`ChatRequest` vs. `ChecklistInput`).

---

## ADR-003: Gestión de Credenciales Seguras y Protección de Datos Personales de Salud (LOPDP Ecuador)

* **Estado:** Aceptado
* **Fecha:** 2026-10-19
* **Responsable:** Rafael Minaya (*QA / Seguridad*)

### 1. Contexto del Problema
La arquitectura del asistente maneja dos vectores de vulnerabilidad de alta criticidad:
1. **Credenciales de infraestructura:** El consumo de APIs generativas (Gemini / Groq) requiere claves privadas de acceso. Una exposición accidental en el repositorio público de Git conlleva la revocación inmediata de la clave, robo de cuotas y una calificación automática de **cero puntos** en el criterio de Integración con IA según la rúbrica oficial de UNIANDES.
2. **Privacidad y Datos de Salud:** En el Ecuador rige la **Ley Orgánica de Protección de Datos Personales (LOPDP, Registro Oficial Suplemento 459, 2021)**. El artículo 25 clasifica los datos relativos a la salud (síntomas de dengue, condiciones fisiológicas, sospechas diagnósticas) como **categorías especiales de datos sensibles**, cuyo tratamiento exige medidas de seguridad reforzadas y consentimiento explícito. Los ciudadanos pueden ingresar inadvertidamente nombres, números de cédula, direcciones o números telefónicos durante su interacción.

### 2. Opciones Consideradas

* **Opción 1: Confinamiento de Claves en Backend (.env) + Arquitectura Anónima sin Estado (Stateless) sin Persistencia de PII.** *(Seleccionada)*  
  * *Manejo de Claves:* Las credenciales (`GEMINI_API_KEY`, `GROQ_API_KEY`) residen exclusivamente en el entorno del servidor a través de `.env` (ignorado de forma estricta por `.gitignore`) y se inyectan como variables de entorno seguras en la plataforma de despliegue. El frontend jamás conoce ni almacena la clave.
  * *Protección de Datos:* El sistema no almacena bases de datos de usuarios ni historiales clínicos en disco. Opera de forma efímera (*stateless*). Los logs de observabilidad aplican **sanitización estricta**: solo registran métricas cuantitativas (latencia, tokens consumidos, códigos HTTP de retorno), suprimiendo cualquier parámetro de texto libre o identificadores del ciudadano.
  * *Ventajas:* Cumplimiento total del principio de **minimización de datos (Art. 10 LOPDP)**; riesgo cero de fuga de credenciales en inspección de código o herramientas de red de navegadores (*DevTools*); cero superficie de ataque sobre bases de datos de pacientes.
  * *Desventajas:* El usuario no puede retomar una sesión anterior al refrescar la página.
* **Opción 2: Almacenamiento Cifrado de Conversaciones en Base de Datos Relacional (PostgreSQL + Cifrado en Reposo).**  
  * *Ventajas:* Permite almacenar perfiles de usuarios y auditoría clínica retrospectiva.
  * *Desventajas:* Introduce una carga legal desproporcionada bajo la LOPDP (obligación de designar delegado de protección de datos, registro de bases ante la Autoridad Nacional y desarrollo de interfaces para ejercer derechos de acceso, rectificación y eliminación ARCO), además de incrementar los costos de infraestructura en la nube.
* **Opción 3: Llamadas Directas al LLM desde el Frontend (Inyección de Clave en Código Cliente).**  
  * *Ventajas:* Evita el desarrollo de microservicios intermediarios en FastAPI.
  * *Desventajas:* **Antipatrón prohibido y brecha de seguridad inadmisible.** La clave de API queda expuesta públicamente en el código JavaScript/HTML descargado por el navegador, permitiendo que cualquier tercero la extraiga y agote la cuota de servicio. Calificación automática de 0/4 en la rúbrica semanal.

### 3. Decisión Adoptada
Se adopta la **Opción 1**.  
1. **Regla de Oro 5 Inquebrantable:** Claves únicamente en variables de entorno del backend; exclusión estricta de `.env` en `.gitignore` verificada mediante tests automatizados de clone limpio.
2. **Cumplimiento LOPDP:** La aplicación opera en modalidad 100% anónima. No se solicita ni persiste información personal identificable (cero PII). Los registros de auditoría y monitoreo se limitan a métricas técnicas de rendimiento y fallas operativas, garantizando la confidencialidad y la no maleficencia ética.

### 4. Consecuencias
* **Positivas:** Blindaje legal frente al régimen sancionatorio de la LOPDP; seguridad garantizada en el repositorio de GitHub; cumplimiento íntegro del estándar de calidad de código del seminario.
* **Negativas asumidas:** El usuario no dispone de persistencia de sesiones históricas; cada consulta se procesa de forma autónoma o dentro de una ventana temporal volátil en memoria.

---

## ADR-004: Determinismo Estricto en la Evaluación de Signos de Alarma (Reglas en Código vs. Razonamiento del Modelo)

* **Estado:** Aceptado
* **Fecha:** 2026-10-19
* **Responsable:** Luis Cahuana (*Tech Lead*)

### 1. Contexto del Problema
Las complicaciones letales del dengue (choque hipovolémico, síndrome de dificultad respiratoria y hemorragias graves) ocurren principalmente durante la **fase crítica** de la enfermedad, coincidiendo paradójicamente con la caída de la fiebre. Las directrices clínicas de la OPS (2016, 2022) y los protocolos del MSP Ecuador catalogan con precisión matemática los **signos de alarma cardinales**:
1. Dolor abdominal intenso y continuo (o dolor a la palpación).
2. Vómitos persistentes (3 o más episodios en pocas horas).
3. Acumulación clínica de líquidos (edema, ascitis, derrame pleural).
4. Sangrado de mucosas (gingivorragia, epistaxis).
5. Letargo, somnolencia extrema o irritabilidad.
6. Hipotensión postural o mareo severo al ponerse de pie.
7. Hepatomegalia dolorosa (> 2 cm bajo el reborde costal).

El lineamiento del Caso 05 exige resolver la siguiente disyuntiva: ¿Debe el LLM interpretar estos síntomas en texto libre o debe evaluarse mediante un algoritmo rígido en código Python?

### 2. Opciones Consideradas

* **Opción 1: Evaluación Algorítmica Determinista en Código Python Puro.** *(Seleccionada)*  
  * La función `evaluar_signos_alarma(respuestas: Dict[str, bool])` evalúa los síntomas reportados aplicando lógica condicional booleana rígida:
    $$\text{Alerta Roja} \iff \sum_{i=1}^{n} \text{signo\_alarma}_i \ge 1$$
    Ante la presencia de **al menos un signo de alarma**, la función emite inmediatamente `alerta_inmediata = True` y `clasificacion = "EMERGENCIA_CRITICA"`, desencadenando la derivación prioritaria hacia el centro de salud más cercano y el enlace directo al ECU-911 (`tel:911`).
  * *Ventajas:* **Cero falsos negativos.** El algoritmo es 100% predecible, auditable y verificable mediante pruebas unitarias (`pytest`). No está sujeto a variaciones estocásticas, alucinaciones ni ambigüedades lingüísticas del modelo.
  * *Desventajas:* Requiere capturar los síntomas mediante una estructura de datos normalizada (checklist interactivo de preguntas sí/no).
* **Opción 2: Evaluación Clínica Delegada al Razonamiento del Modelo Generativo (LLM Prompting).**  
  * Se instruye al modelo en el *system prompt* para que analice los síntomas descritos libremente por el usuario y decida si existe gravedad.
  * *Ventajas:* Interacción natural y abierta en lenguaje coloquial.
  * *Desventajas:* **Riesgo mortal inaceptable.** Diversos estudios científicos (Ji et al., 2023; Weidinger et al., 2021) demuestran que los LLMs pueden subestimar síntomas combinados, descartar sangrados leves considerándolos "normales" o generar respuestas complacientes que desaconsejen acudir a urgencias. En salud pública, un falso negativo en triaje significa que un paciente en riesgo de choque no acude al hospital a tiempo.

### 3. Decisión Adoptada
Se adopta la **Opción 1: Determinismo Estricto en Código Python**.  
La evaluación de signos de alarma reside en `app/tools/evaluacion.py` y opera mediante reglas booleanas rígidas extraídas textualmente de la Guía de Atención de Dengue de la OPS (2016). **El LLM jamás interviene ni calcula el nivel de riesgo de un paciente.** Si la función retorna alerta roja, la interfaz interrumpe cualquier interacción ordinaria y despliega la advertencia perentoria de traslado médico urgente.

### 4. Consecuencias
* **Positivas:** Certificación del indicador de calidad del 100% de derivación ante signos de alarma (cero falsos negativos); cumplimiento de la Regla de Oro 3; total explicabilidad del algoritmo ante la mesa de sustentación.
* **Negativas asumidas:** El ciudadano debe responder un cuestionario estructurado de confirmación para los síntomas agudos, en lugar de confiar únicamente en descripciones conversacionales abiertas.

---

## ADR-005: Estrategia de Chunking por Secciones Temáticas Canónicas y Base Vectorial ChromaDB Local

* **Estado:** Aceptado
* **Fecha:** 2026-10-28
* **Responsable:** Wilson Salinas (*Builder*) / Equipo Caso 05

### 1. Contexto del Problema
Para implementar el pipeline RAG de la Semana 3, era necesario definir la estrategia de fragmentación (*chunking*) del corpus médico-normativo (guías clínicas OPS 2016/2022 y lineamientos MSP Ecuador 2026) y seleccionar el motor de almacenamiento e indexación vectorial.
A diferencia de los códigos normativos legales que tienen artículos numerados, las guías clínicas se estructuran en secciones temáticas amplias. Un corte arbitrario por número de caracteres (ej. bloques fijos de 500 caracteres) corría el riesgo inaceptable de cortar directivas médicas por la mitad (por ejemplo, separar el término "NO" de "administrar ibuprofeno ni aspirina"), induciendo alucinaciones clínicas de riesgo vital.

### 2. Opciones Consideradas
* **Opción 1: Chunking ciego por caracteres o tokens (512 caracteres con 10% overlap) con Pinecone / Qdrant Cloud.**
  * *Desventajas:* Fragmentos incompletos o huérfanos, dependencia de conexión constante a la nube y consumo de saldo en servicios externos de embeddings.
* **Opción 2: Chunking por Sección Temática Canónica (500–800 palabras) con ChromaDB Persistente y Modelo Local ONNX (`all-MiniLM-L6-v2`).** *(Seleccionada)*
  * *Ventajas:* Mantiene íntegra cada directiva médica completa (síntomas, signos de alarma, medicamentos contraindicados, hidratación). Cada fragmento conserva su título oficial (`SECCIÓN X`) permitiendo citas verificables (*«Según la Guía OPS, sección 4...»*). El modelo local ONNX corre 100% en CPU local (79 MB), asegurando costo cero y reproducibilidad total en pruebas CI/CD.

### 3. Decisión Adoptada
Se adopta la **Opción 2**: Chunking por sección temática guiado por el patrón regex `/(?=SECCIÓN\s+\d+)/` indexado en **ChromaDB** persistente local (`data/index/`) con 5 metadatos obligatorios (`id`, `documento`, `seccion`, `tema`, `anio`).

### 4. Consecuencias
* **Positivas:** Fragmentos clínicamente coherentes; citas bibliográficas auditables; costo cero de embeddings; suite de pruebas ejecutable de forma instantánea y aislada sin conexión a internet.
* **Negativas asumidas:** El corpus normativo inicial requiere ser curado y estructurado manualmente por secciones temáticas previo a la ingesta.

---

## ADR-006: Separación Arquitectónica Estricta de Datos Tabulares (GeoSalud Determinista vs. RAG Vectorial)

* **Estado:** Aceptado
* **Fecha:** 2026-10-28
* **Responsable:** Wilson Salinas (*Builder*) / Equipo Caso 05

### 1. Contexto del Problema
El sistema cuenta con el catálogo de infraestructura hospitalaria de la red pública MSP de Ecuador ([`data/geosalud_ecuador.json`](data/geosalud_ecuador.json)), que contiene atributos exactos: provincia, cantón, nombre del hospital, dirección, teléfono y disponibilidad de guardia de emergencia 24h.
Se debía resolver si estos datos debían ser indexados en la base vectorial RAG junto a las guías clínicas o procesarse mediante una herramienta algorítmica independiente.

### 2. Opciones Consideradas
* **Opción 1: Indexar los centros de salud en la base vectorial ChromaDB.**
  * *Desventajas:* **Riesgo crítico de alucinación.** La similitud semántica vectorial no garantiza filtros exactos por atributos discretos (ej. buscar hospitales en Manta podría recuperar por proximidad semántica un hospital en Guayaquil, o el LLM podría inventar números telefónicos o alterar direcciones al sintetizar).
* **Opción 2: Herramienta Determinista en Python Puro (`app/tools/geosalud.py`).** *(Seleccionada)*
  * *Ventajas:* Aplica la Regla Crítica del Módulo 3. Los datos tabulares estructurados se filtran mediante comparaciones exactas e insensibles a tildes/mayúsculas en Python, garantizando 100% de precisión en nombres de hospitales, teléfonos de urgencia y direcciones físicas.

### 3. Decisión Adoptada
Se adopta la **Opción 2**: El directorio hospitalario reside en `data/geosalud_ecuador.json` y es consultado exclusivamente por la herramienta determinista `app/tools/geosalud.py`. Cuando un ciudadano menciona su cantón o presenta signos de alarma, Python personaliza la derivación hospitalaria con datos exactos verificados.

### 4. Consecuencias
* **Positivas:** Cero alucinación en geolocalización hospitalaria; exactitud garantizada en teléfonos y direcciones de emergencia; cumplimiento estricto de las directivas del seminario.
* **Negativas asumidas:** Requiere mantener sincronizado el archivo JSON con los registros oficiales de la Dirección Nacional de Vigilancia Epidemiológica del MSP.

