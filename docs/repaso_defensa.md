# Banco de Preguntas y Respuestas para la Defensa de Titulación
**Proyecto:** Asistente de Orientación en Salud Pública sobre Dengue y Arbovirosis (Caso 05 - Grupo 5)  
**Carrera de Software – Seminario de Titulación Complexivo (UNIANDES 2026)**  
**Autores:** Rafael Minaya, Luis Cahuana  
*(Este documento se actualiza al cierre de cada semana del proyecto para la preparación continua de la defensa oral ante el tribunal).*

---

## Índice Temático
1. [Bloque 1: Problema Real, Alcance y Requisitos (Semana 1)](#bloque-1-problema-real-alcance-y-requisitos-semana-1)
2. [Bloque 2: Arquitectura del Sistema y ADRs (Semanas 1 y 2)](#bloque-2-arquitectura-del-sistema-y-adrs-semanas-1-y-2)
3. [Bloque 3: Servicio de IA, Resiliencia y Fallback Dual (Semana 2)](#bloque-3-servicio-de-ia-resiliencia-y-fallback-dual-semana-2)
4. [Bloque 4: Ingeniería de Prompts y Evaluación Empírica (Semana 2)](#bloque-4-ingeniería-de-prompts-y-evaluación-empírica-semana-2)
5. [Bloque 5: DevOps, Versionado SemVer y Pruebas Automatizadas (Semanas 1 y 2)](#bloque-5-devops-versionado-semver-y-pruebas-automatizadas-semanas-1-y-2)

---

## Bloque 1: Problema Real, Alcance y Requisitos (Semana 1)

### Pregunta 1.1: ¿Cuál es el problema real que resuelve el sistema y por qué se diseñó como un asistente de orientación y no de diagnóstico?
**Respuesta para el tribunal:**  
El dengue es endémico en la Costa y Amazonía ecuatorianas y satura periódicamente los centros de salud del MSP. Gran parte de las muertes y complicaciones graves (choque por dengue) se deben a la **consulta tardía cuando aparecen signos de alarma**, y a la **automedicación peligrosa** en el hogar.  
No es un sistema de diagnóstico por dos razones fundamentales:
1. **Riesgo clínico y legal:** Un diagnóstico requiere exploración física, toma de signos vitales (presión arterial) y biometría hemática (hematocrito y plaquetas), aspectos imposibles de realizar por software.
2. **Alcance ético:** La Organización Panamericana de la Salud (OPS) y el Ministerio de Salud Pública (MSP) estipulan que la IA en salud comunitaria debe orientar en prevención, educar en signos de alarma y derivar precozmente al médico, **nunca reemplazar el criterio del profesional de la salud**.

### Pregunta 1.2: ¿Cuál es el «alcance negativo estricto» del proyecto y por qué está terminantemente prohibido formular medicamentos o AINEs?
**Respuesta para el tribunal:**  
El alcance negativo estricto define lo que el sistema **bajo ninguna circunstancia hará**:
- **Nunca emitirá un diagnóstico definitivo.**
- **Nunca prescribirá, dosificará ni sugerirá fármacos.**
- **Prohibición expresa de AINEs:** Medicamentos comunes como el ibuprofeno, aspirina (ácido acetilsalicílico), diclofenaco, naproxeno o ketorolaco tienen efecto antiplaquetario. En un paciente con dengue, su consumo desencadena hemorragias graves y letales. El sistema prohíbe de forma activa su uso y promueve exclusivamente la hidratación oral mediante sales de rehidratación oral (SRO) y el traslado a urgencias.

### Pregunta 1.3: ¿Cómo justificaron las 8 historias de usuario y cómo se verifican sus criterios de aceptación?
**Respuesta para el tribunal:**  
Se derivaron de un **estudio de campo real** aplicado a ciudadanos y cuidadores con 15 preguntas en escala Likert (`ANALISIS DE PREGUNTAS.pdf`). Cada historia de usuario sigue la estructura ágil *«Como [usuario], quiero [acción], para [beneficio]»*, estimada para completarse en menos de 3 días, y cuenta con 4 criterios de aceptación formulados en sintaxis **Gherkin (`Dado / Cuando / Entonces`)**, garantizando que sean testeables mediante pruebas automatizadas.

---

## Bloque 2: Arquitectura del Sistema y ADRs (Semanas 1 y 2)

### Pregunta 2.1: ¿Qué es un ADR y por qué es crucial documentarlos en este proyecto?
**Respuesta para el tribunal:**  
Un **ADR (Architectural Decision Record)** es un documento técnico que captura una decisión arquitectónica clave junto con su contexto, alternativas evaluadas y consecuencias. Utilizamos el estándar de **Michael Nygard**, que estructura cada decisión en: *Título, Estado, Contexto, Decisión y Consecuencias*. Demuestra al tribunal madurez en ingeniería de software, trazabilidad de decisiones técnicas y sustentación de costos y normativas.

### Pregunta 2.2: Explique el ADR-001: ¿Por qué seleccionaron Gemini 1.5/3.8 Flash como principal y Groq como respaldo?
**Respuesta para el tribunal:**  
- **Gemini 1.5/3.8 Flash (Principal):** Ofrece una ventana de contexto de 1 millón de tokens, costo por millón extremadamente bajo, soporte nativo de salida estructurada JSON y latencias menores a 1.5 segundos.
- **Groq Llama 3.3 70B / gpt-oss-20b (Respaldo):** Es el motor de inferencia en hardware LPU más rápido del mercado (más de 300 tokens/segundo). Si la API de Google se satura (error 429) o experimenta una caída de servicio (error 500/503), Groq asume la petición en milisegundos sin que el ciudadano perciba la falla.

### Pregunta 2.3: Explique el ADR-002: ¿Por qué eligieron un workflow determinista estructurado en lugar de un agente autónomo libre (ReAct)?
**Respuesta para el tribunal:**  
En salud pública, la **predictibilidad y la seguridad del paciente son innegociables**. Los agentes autónomos tipo ReAct con bucles abiertos presentan riesgos de alucinaciones, loops infinitos y latencias impredecibles. Un workflow orquestado garantiza un flujo secuencial cerrado: validación previa en Pydantic $\rightarrow$ prompt enjaulado $\rightarrow$ inferencia resiliente $\rightarrow$ regla determinista en Python $\rightarrow$ respuesta validada.

### Pregunta 2.4: Explique el ADR-003: ¿Cómo cumple el sistema con la Ley Orgánica de Protección de Datos Personales (LOPDP Ecuador)?
**Respuesta para el tribunal:**  
Por diseño (*Privacy by Design*):
1. **Regla de Oro 5:** Ningún secreto o clave de API reside en el código ni en Git. Viven exclusivamente en `.env` local y en Secret Manager en producción.
2. **Anonimización en Logs:** El archivo `logs/llm.jsonl` registra exclusivamente tokens de entrada/salida, latencia en milisegundos y proveedor. **Nunca guarda el texto escrito por el ciudadano**, impidiendo almacenar síntomas que puedan asociarse a la identidad de un individuo.

### Pregunta 2.5: Explique el ADR-004: ¿Por qué el triaje de signos de alarma se ejecuta en Python puro y no por el LLM?
**Respuesta para el tribunal:**  
Por el principio de oro: **«El modelo propone, el código dispone»**.  
Los modelos probabilísticos (LLMs) tienen margen de error estocástico y pueden cometer falsos negativos ante emergencias críticas. La función `_evaluar_regla_signos_alarma` en Python puro inspecciona determinísticamente si el usuario reporta dolor abdominal continuo, vómitos persistentes o sangrado. Si los detecta, **el código Python sobrescribe y fuerza la derivación urgente al hospital o al ECU-911**, garantizando **cero falsos negativos** en situaciones donde la vida del paciente corre peligro.

---

## Bloque 3: Servicio de IA, Resiliencia y Fallback Dual (Semana 2)

### Pregunta 3.1: ¿Qué sucede en su arquitectura si Google Gemini devuelve un error HTTP 429 (Too Many Requests)?
**Respuesta para el tribunal:**  
El módulo `app/services/llm.py` intercepta el código de estado 429 mediante la excepción `openai.RateLimitError`. Ejecuta un algoritmo de **backoff exponencial con jitter**:
- Intento 1: Espera entre 0.5s y 1s.
- Intento 2: Espera entre 1s y 2s.
- Intento 3: Espera entre 2s y 4s.
Si tras los reintentos Gemini sigue saturado o la cabecera `Retry-After` supera los 20 segundos, el sistema se rinde con Gemini y conmuta automáticamente a **Groq**, resolviendo la consulta de forma transparente.

### Pregunta 3.2: ¿Por qué se utilizó el SDK de `openai` si los modelos utilizados son de Google (Gemini) y Groq?
**Respuesta para el tribunal:**  
Porque tanto Google Gemini como Groq han implementado endpoints de inferencia **100% compatibles con la API de OpenAI** (`/v1beta/openai/` en Google y `/openai/v1` en Groq). Utilizar el cliente estandarizado `OpenAI(base_url=..., api_key=...)` permite aplicar el **Principio de Inversión de Dependencias (SOLID)**: el backend depende de una abstracción unificada y cambiar de proveedor de IA es tan simple como cambiar la variable `base_url` y la clave en el archivo `.env`.

### Pregunta 3.3: ¿Cómo garantiza Pydantic que el modelo no invente campos fuera del contrato?
**Respuesta para el tribunal:**  
Mediante la clase base `Estricto(BaseModel)` configurada con `model_config = ConfigDict(extra="forbid")`. Cuando la respuesta del modelo llega en formato JSON, Pydantic la valida. Si el modelo alucina un campo no contemplado (por ejemplo, `dosis_sugerida`), Pydantic lanza `ValidationError` y activa la rutina de corrección automática del cliente LLM; si persiste, se deriva a revisión humana sin colapsar el microservicio.

---

## Bloque 4: Ingeniería de Prompts y Evaluación Empírica (Semana 2)

### Pregunta 4.1: Explique la evolución de los prompts entre las versiones v1, v2 y v3 documentada en `docs/05-prompts.md`.
**Respuesta para el tribunal:**  
- **`system_v1.md` (Ingenuo):** Solo daba una orden directa (*"Eres un asistente de salud sobre dengue"*). Ante preguntas adversarias de dosificación de fármacos o solicitudes fuera de dominio, fallaba en formato y no aplicaba abstención estricta.
- **`system_v2.md` (Rol y Few-Shot):** Incorporó el rol de orientador comunitario para Ecuador y técnicas Few-Shot, mejorando el tono pero con abstenciones vagas (*"Lo siento, no puedo ayudar"*).
- **`system_v3.md` (Producción - Ganadora):** Implementa las **6 partes canónicas**:
  1. **Rol:** Orientador oficial del MSP Ecuador y OPS.
  2. **Tarea:** Explicar síntomas, prevención y clasificar necesidad de derivación.
  3. **Criterios:** Claridad ciudadana y lenguaje empático en zonas endémicas.
  4. **Restricciones:** Prohibición explícita de diagnosticar y de formular AINEs.
  5. **Abstención:** Activación de `se_abstiene = true` ante consultas ajenas a arbovirosis.
  6. **Ejemplo:** Caso Few-Shot de un menor con dolor abdominal derivado al hospital.

### Pregunta 4.2: ¿Qué resultados arrojó la matriz empírica de 10 entradas de prueba en `docs/05-prompts.md`?
**Respuesta para el tribunal:**  
`system_v3` obtuvo una calificación perfecta de **10/10 en corrección y formato estricto**:
- Bloqueó el intento de prescripción de ibuprofeno explicando que los AINEs provocan hemorragias mortales.
- Rechazó el intento de saltarse la consulta hospitalaria.
- Ante la consulta sobre renovación de licencia de conducir en la ANT, activó de inmediato `se_abstiene = true` indicando la institución competente correspondiente.

---

## Bloque 5: DevOps, Versionado SemVer y Pruebas Automatizadas (Semanas 1 y 2)

### Pregunta 5.1: ¿Cómo funciona el versionado SemVer continuo implementado en GitHub Actions?
**Respuesta para el tribunal:**  
El flujo `.github/workflows/semver.yml` se dispara ante Pull Requests que toquen archivos dentro de `app/**`. Ejecuta las pruebas automatizadas con `pytest` y utiliza el script desacoplado `scripts/semver_bumper.py`:
- Analiza los commits bajo la convención *Conventional Commits*: `feat:` incrementa versión **MINOR**, `fix:`/`refactor:` incrementa **PATCH**, y `BREAKING CHANGE:` o `!` incrementa **MAJOR**.
- En la rama `main` genera versiones formales de Release (`vX.Y.Z`) y actualiza la constante `APP_VERSION` en `app/main.py`.
- En la rama `develop` genera versiones `vX.Y.Z-SNAPSHOT-RC#` incrementales.

### Pregunta 5.2: ¿Por qué tienen 31 pruebas unitarias y cómo es posible que corran en 3 segundos sin saldo de IA?
**Respuesta para el tribunal:**  
Porque implementamos **dobles de prueba (*mocks*) y arquitectura desacoplada**:
- Las pruebas de `test_mi_caso.py` y `test_endpoint.py` utilizan la clase `LLMDoble` inyectada mediante `app.dependency_overrides[obtener_llm]`.
- Las pruebas de `test_llm.py` simulan respuestas y errores 429 en memoria.
- La prueba `test_integracion_simulado.py` levanta un servidor mock HTTP local en el puerto 8099.  
Esto permite que el pipeline de Integración Continua (CI) en GitHub Actions o en local valide el 100% de la lógica sin gastar un solo centavo de saldo, sin depender de internet y en apenas 3.8 segundos.
