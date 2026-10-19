# Asistente de Orientación en Salud Pública sobre Dengue y Arbovirosis
**Seminario de Titulación Complexivo – Carrera de Software (UNIANDES 2026)**  
**Caso N.º 05 – Grupo 5**

---

## 1. Problema que Resuelve y Población Objetivo
El dengue es una afección endémica crítica en la Costa y Amazonía ecuatorianas, donde los brotes saturan periódicamente las unidades de salud pública. Gran parte de las complicaciones graves y muertes derivan de la **consulta tardía** al presentarse signos de alarma y de la **automedicación con AINEs**.  
Este sistema proporciona a la ciudadanía y cuidadores un canal digital de orientación preventiva estricta basado en guías oficiales del MSP y la OPS, incorporando un **agente determinista de triaje de signos de alarma** y geolocalización de centros de salud, **sin emitir diagnósticos médicos ni recomendar medicamentos**.

---

## 2. Seis Reglas de Oro Inquebrantables del Sistema
1. **Lo que afirma, lo cita:** Respuestas informativas con cita de documento, sección y enlace oficial.
2. **Lo que no sabe, lo dice:** Abstención estricta ante consultas fuera de la base documental del MSP/OPS.
3. **Lo que se calcula o triajea, va en código determinista:** Triaje booleano en Python puro (`evaluar_signos_alarma`) y búsqueda en `geosalud_ecuador.json`; el LLM jamás infiere gravedad.
4. **Lo que cambia en el tiempo, vive en configuración:** Modelos, umbrales y rutas centralizados en `config/settings.py` y `.env`.
5. **Lo que es secreto, nunca toca el repositorio:** Credenciales (`GEMINI_API_KEY`) exclusivas en backend; `.env` ignorado por Git.
6. **Lo que tiene consecuencias, requiere confirmación:** Derivación inmediata a emergencias o al ECU-911 (`tel:911`) ante cualquier signo de alarma.

---

## 3. Estado del Proyecto (Semana 1 - Definición y Diseño)
- **Entrega oficial:** Viernes 16 de Octubre de 2026.
- **Entregables de la fase:**
  - `docs/01-propuesta.md`: Problema, usuarios, alcance positivo/negativo y riesgos del paciente.
  - `docs/02-requisitos.md`: 8 historias de usuario en formato Gherkin y 5 RNF medibles.
  - `docs/03-arquitectura.md`: Diagramas Mermaid (modular, clases, DFD niveles 0 y 1) y especificación de servicios.
  - `docs/04-fuentes.md`: Inventario de 6 fuentes oficiales (APA 7.ª ed.) y estrategia de chunking jerárquico.
  - `data/geosalud_ecuador.json`: Directorio estructurado de hospitales y Centros Tipo C en provincias endémicas.
  - `data/raw/`: Guías normativas descargadas de la OPS y el MSP.
  - **Esqueleto de Backend:** FastAPI operativo con endpoint de salud `GET /health` y modelos Pydantic en `app/schemas.py`.

---

## 4. Estructura del Repositorio

```text
├── app/
│   ├── main.py              # API FastAPI y rutas base (/health)
│   ├── schemas.py           # Modelos de validación Pydantic
│   ├── services/            # Orquestador, RAG retriever y cliente LLM
│   ├── tools/               # Herramientas deterministas (triaje y GeoSalud)
│   └── prompts/             # System prompts versionados con guardrails
├── config/
│   ├── __init__.py
│   └── settings.py          # Configuración centralizada vía variables de entorno
├── data/
│   ├── raw/                 # Guías oficiales canónicas (PDF)
│   ├── processed/           # Datos procesados / fragmentos
│   └── geosalud_ecuador.json # Directorio oficial de centros de salud
├── docs/
│   ├── 01-propuesta.md
│   ├── 02-requisitos.md
│   ├── 03-arquitectura.md
│   ├── 04-fuentes.md
│   └── evidencias/semana-1/
├── eval/                    # Preguntas de evaluación y casos de triaje
├── scripts/                 # Ingesta reproducible y pipelines
├── tests/
│   └── test_health.py       # Pruebas unitarias automatizadas con pytest
├── .env.example             # Plantilla de variables de entorno (sin credenciales)
├── .gitignore               # Exclusión estricta de .env, venv y datos temporales
├── requirements.txt         # Dependencias Python
└── README.md
```

---

## 5. Instalación y Ejecución Local

### Prerrequisitos
- Python 3.11 o superior.
- Git.

### Paso a Paso
1. **Clonar el repositorio:**
   ```bash
   git clone <url-del-repositorio>
   cd Proyecto
   ```

2. **Crear y activar entorno virtual:**
   ```bash
   python -m venv .venv
   # En Windows PowerShell:
   .venv\Scripts\Activate.ps1
   # En Linux / macOS:
   source .venv/bin/activate
   ```

3. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar variables de entorno:**
   ```bash
   cp .env.example .env
   # Editar .env para asignar GEMINI_API_KEY
   ```

5. **Ejecutar pruebas unitarias:**
   ```bash
   pytest tests/
   ```

6. **Iniciar el servidor de backend:**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
   - Verificación de salud: `http://localhost:8000/health`
   - Documentación interactiva (Swagger UI): `http://localhost:8000/docs`

---

## 6. Autores y Licencia
- **Carrera de Software – UNIANDES 2026**
- Proyecto académico desarrollado bajo principios éticos de IA en salud pública y la Ley Orgánica de Protección de Datos Personales (LOPDP) del Ecuador.
