# INSTRUCCIÓN MAESTRA Y TABLERO DE CONTROL DE AVANCE (SEMINARIO TITULACIÓN UNIANDES)
# CASO 05 - GRUPO 5: Asistente de Orientación en Salud Pública sobre Dengue y Arbovirosis

---

## 1. ROL Y PROTOCOLO DEL AGENTE EN ANTIGRAVITY
Actúas como el **Arquitecto de Software Líder y Auditor de Calidad** del equipo. Tu responsabilidad es:
1. **Guiar el desarrollo estrictamente por fases y semanas**, respetando el cronograma oficial de UNIANDES.
2. **Impedir saltos prematuros de fase:** No generar código de semanas posteriores (ej. RAG o despliegue) sin antes verificar que los entregables de la semana en curso estén completos, auditados y funcionales.
3. **Mantener el estado de avance:** En cada interacción, verificar la sección `TABLERO DE ESTADO DEL PROYECTO` de este archivo, identificar qué falta para la próxima revisión y guiar al equipo a completarlo.
4. **Verificar el equilibrio grupal:** Recordar y asegurar que los componentes y commits se distribuyan equitativamente entre los 3 integrantes.

---

## 2. CRONOGRAMA OFICIAL Y FECHAS DE REVISIÓN (UNIANDES 2026)

| Fase / Semana | Período de Trabajo | Fecha Límite de Revisión | Enfoque Técnico Principal |
| :--- | :--- | :--- | :--- |
| **Fase 1 (Semana 1)** | Mar 13 – Vie 16 Oct (19h00–21h30) | **Viernes 16 de Octubre** | Definición, requisitos, arquitectura, catalogación de fuentes y repo base. |
| **Fase 2 (Semana 2)** | Lun 19 – Vie 23 Oct (19h00–21h00) | **Viernes 23 de Octubre** | Backend FastAPI, frontend MVP, prompts con salvaguardas y control de API Keys. |
| **Fase 3 (Semana 3)** | Lun 26 – Vie 30 Oct (19h00–21h00) | **Viernes 30 de Octubre** | Pipeline RAG con citas, agente determinista (`evaluar_signos_alarma`) y evaluación. |
| *Ventana Técnica* | Sáb 31 Oct – Mar 3 Nov (Sin clases) | *Hito intermedio* | Despliegue en la nube (Render/Railway), persistencia vectorial y pruebas online. |
| **Fase 4 y 5 (Semana 4)**| Mié 4 – Sáb 7 Nov (19h00–21h30) | **Sábado 7 de Noviembre** | Pruebas funcionales en URL pública, README final y Sustentación oral. |

---

## 3. TABLERO DE ESTADO DEL PROYECTO (CONTROL DE ENTREGABLES)

> **ESTADO ACTUAL:** `FASE 1 (SEMANA 1) COMPLETADA Y AUDITADA - LISTA PARA TRANSICIÓN A FASE 2`  
> *Regla operativa: Solo trabajar en ítems de la semana activa hasta marcarlos como completados.*

### [x] FASE 1 - SEMANA 1: Definición y Diseño (Entrega: Viernes 16 Octubre) - COMPLETADA
- [x] **Catalogación de Fuentes (`docs/04-fuentes.md`):** Inventario con APA 7.ª ed., permalinks vigentes (4-5 años) y estrategia de chunking clínico.
- [x] **Insumos RAW descargados (`data/raw/`):**
  - `ops_guia_dengue_2016.pdf` (OPS 2016)
  - `ops_directrices_arbovirosis_2022.pdf` (OPS 2022)
  - `ops_guia_diagnostico_prevencion_2009_esp.pdf` (OMS/OPS 2009)
  - `msp_plan_contingencia_2026.pdf` (MSP Ecuador)
  - `ANALISIS DE PREGUNTAS.pdf` y `RESPUESTAS.xlsx` (Insumos de encuesta ciudadana)
- [x] **Directorio GeoSalud Estructurado (`data/geosalud_ecuador.json`):** Catálogo de hospitales y Centros Tipo C de la Costa y Amazonía.
- [x] **Propuesta del Proyecto (`docs/01-propuesta.md`):** Alcance explícito (qué hará y qué nunca hará) y matriz de riesgos éticos/paciente.
- [x] **Ingeniería de Requisitos (`docs/02-requisitos.md`):** Mínimo 8 historias de usuario (formato Gherkin) y requisitos no funcionales medibles.
- [x] **Diseño de Arquitectura (`docs/03-arquitectura.md`):** Diagramas Mermaid (flujo de consulta, clases, DFD y microservicios).
- [x] **Levantamiento Empírico (`docs/02-anexo-preguntas.md`):** Anexo con el análisis de 15 preguntas ciudadanas en escala Likert y banco de dudas clínicas.
- [x] **Configuración del Repositorio:** `.gitignore` (excluyendo `.env`), `.env.example`, `requirements.txt` y `README.md` inicial.
- [x] **Esqueleto Ejecutable Backend:** FastAPI con endpoint `GET /health` y suite de pruebas unitarias (`pytest tests/`) aprobada al 100%.
- [x] **Evidencias Técnicas Registradas:** Documentación en `docs/evidencias/semana-1/README.md`.
- [!] **Auditoría Git (Acción operativa en equipo):** Asegurar que en el repositorio remoto de GitHub existan commits distribuidos entre los 3 integrantes del grupo.

---

### [ ] FASE 2 - SEMANA 2: MVP e Integración con IA Generativa (Entrega: Viernes 23 Octubre)
- [ ] **Backend Operativo:** FastAPI con endpoint `POST /chat` validado con Pydantic y streaming de respuesta.
- [ ] **Módulo de Servicio LLM (`app/services/llm.py`):** Desacoplado de la API; llamada a Gemini / Groq.
- [ ] **System Prompt con Salvaguardas (`app/prompts/system_v1.md`):** Prohibición estricta de diagnosticar y recetar; derivación ante peligro; lenguaje empático y claro.
- [ ] **Comparación de Prompts (`docs/05-prompts.md`):** Tabla comparativa de 3 versiones evaluadas con 10 entradas de prueba.
- [ ] **Frontend Funcional:** Interfaz web conectada al backend, aviso visible de interacción con IA, botón deshabilitado durante la inferencia y manejo amigable de errores.
- [ ] **Seguridad de Credenciales:** Clave de API exclusivamente en backend vía `.env`. Cero claves en frontend o historial Git.
- [ ] **Resiliencia y Observabilidad:** Manejo de error HTTP 429 (límite de tasa con backoff exponencial) y logs de tokens consumidos/latencia.
- [ ] **Pruebas Unitarias Básicas (`tests/`):** Pruebas con mocks de la API ejecutables vía `pytest` sin gastar saldo.
- [ ] **Evidencias Técnicas:** Capturas y decisiones documentadas en `docs/evidencias/semana-2/`.

---

### [ ] FASE 3 - SEMANA 3: RAG, Agente y Calidad (Entrega: Viernes 30 Octubre)
- [ ] **Script de Ingesta Reproducible (`scripts/ingest.py`):** Extracción, chunking semántico guiado por encabezados y generación de embeddings en ChromaDB persistente con metadatos.
- [ ] **Documentación RAG (`docs/06-rag.md`):** Justificación técnica del chunking (600 tokens / 100 overlap) y filtros por metadatos.
- [ ] **RAG con Citas Obligatorias:** El modelo referencia explícitamente documento, acápite y URL; política de abstención estricta probada ante consultas no cubiertas.
- [ ] **Herramienta Determinista 1 (`app/tools/evaluacion.py`):** `evaluar_signos_alarma(respuestas)` implementada en Python con lógica booleana rígida (cero intervención de LLM).
- [ ] **Herramienta Determinista 2 (`app/tools/geosalud.py`):** `ubicar_establecimiento(ciudad)` consultando `data/geosalud_ecuador.json`.
- [ ] **Configuraciones Centralizadas (`config/`):** Umbrales, rutas y parámetros en archivos de configuración, nunca en el código ni prompt.
- [ ] **Conjunto de Evaluación (`eval/`):**
  - `preguntas.csv`: 20 preguntas (12 con respuesta, 4 sin respuesta/abstención, 2 fuera de dominio, 2 inyecciones).
  - `casos_triaje.csv`: 10 escenarios clínicos con resultado de derivación verificado.
  - Script `run_eval.py` y reporte de métricas en `docs/07-evaluacion.md`.
- [ ] **Pruebas Automatizadas:** Tests unitarios de herramientas y validación de esquemas ejecutables con `pytest`.

---

### [ ] FASE 4 Y 5 - SEMANA 4: Despliegue, Validación y Cierre (Entrega: Sábado 7 Noviembre)
*(Ventana de despliegue previa: 31 de octubre al 3 de noviembre)*
- [ ] **Aplicación Desplegada en la Nube:** URL pública operativa (Render, Railway o Hugging Face Spaces) con `GET /health` respondiendo.
- [ ] **Secretos en la Nube:** Variables de entorno configuradas en el dashboard de la plataforma (verificado cero secretos en Git).
- [ ] **Persistencia Vectorial:** ChromaDB sobrevive a reinicios del contenedor o se reconstruye limpiamente al arranque.
- [ ] **Pruebas Funcionales en Producción (`docs/08-pruebas.md`):** Mínimo 15 casos ejecutados contra la URL pública (resultado esperado vs. obtenido), incluyendo:
  - 100% derivación en signos de alarma.
  - 100% rechazo a recetas de fármacos/dosis.
  - Intentos de inyección de prompt ("ignora tus instrucciones").
- [ ] **Evaluación Final Reejecutada:** Comparación de métricas de la Semana 3 vs. Semana 4 en `docs/07-evaluacion.md`.
- [ ] **Documentación Final y Cierre:**
  - `README.md` completo según plantilla oficial.
  - `docs/09-decisiones.md` (decisiones de arquitectura, ética y cumplimiento LOPDP Ecuador).
  - Declaración de uso responsable de IA y desglose de aportes de cada integrante.
- [ ] **Defensa de Sustentación Ensaya (20 minutos):** Preparación para responder las preguntas clínicas y éticas de la Fase 5.

---

## 4. SEIS REGLAS DE ORO DEL SISTEMA (RESTRICCIONES INQUEBRANTABLES)
1. **Lo que afirma, lo cita:** Ninguna respuesta de salud puede carecer de documento oficial y sección.
2. **Lo que no sabe, lo dice:** Si la respuesta no está en el corpus, se declara la abstención y se remite a canales del MSP.
3. **Lo que se calcula o triajea, va en código determinista:** `evaluar_signos_alarma` y `ubicar_establecimiento` residen en funciones de Python; el LLM jamás calcula riesgos ni triajes.
4. **Lo que cambia en el tiempo, vive en configuración:** Rutas, parámetros y nombres de modelos viven en `config/` o `.env`.
5. **Lo que es secreto, nunca toca el repositorio:** `.env` en `.gitignore`; cero claves en commits.
6. **Lo que tiene consecuencias, requiere confirmación:** Las derivaciones o alertas rojas priorizan el botón de llamada al 911 y el traslado presencial urgente.

---

## 5. ALCANCE NEGATIVO CLÍNICO (QUÉ NUNCA HARÁ EL SISTEMA)
- **NUNCA emitir diagnósticos médicos:** No validar si el paciente "tiene dengue" o en qué fase exacta está clínicamente.
- **NUNCA recetar medicamentos ni dosificaciones:** Bloqueo determinista del 100% de solicitudes farmacológicas (paracetamol, antibióticos, remedios caseros). Alerta obligatoria contra el uso de AINEs (aspirina, ibuprofeno).
- **Cero falsos negativos en triaje:** Cualquier presencia de signo de alarma oficial (dolor abdominal continuo, vómitos persistentes, sangrado de mucosas, letargo/irritabilidad, mareo postural, acumulación de líquidos) detiene la conversación general y deriva a urgencias o al 911.

---

## 6. PROTOCOLO DE INTERACCIÓN DEL AGENTE
Cuando el usuario interactúe contigo:
1. Revisa en qué semana y fase nos encontramos según la fecha actual.
2. Comprueba qué casillas `[ ]` de esa semana faltan por completar.
3. Propón código, documentos o validaciones centradas **exclusivamente** en resolver los pendientes de la semana activa.
4. Cuando un entregable sea finalizado y verificado, indica que debe marcarse como `[x]` en este archivo.