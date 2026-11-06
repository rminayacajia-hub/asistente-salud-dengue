# ==============================================================================
# Dockerfile Oficial - Asistente de Orientación en Salud Pública (Dengue Ecuador)
# Seminario de Titulación Complexivo UNIANDES 2026 - Caso 05 (Grupo 5)
# ==============================================================================
# Cumple con la Lista de Verificación de Despliegue (Semana 4):
# 1. Imagen ligera Python 3.12-slim.
# 2. Construcción automática del índice vectorial ChromaDB (scripts/ingest.py)
#    durante el build y verificación al arranque (sobrevive a reinicios).
# 3. Arranque con --host 0.0.0.0 --port ${PORT:-8000}.
# 4. Cero secretos embebidos (las claves se inyectan como variables de entorno).
# ==============================================================================

FROM python:3.12-slim

# Evitar archivos .pyc y habilitar salida en tiempo real en logs de plataforma
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# Instalar dependencias del sistema mínimas requeridas por librerías nativas
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias de Python primero para aprovechar caché de capas
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente y datos estructurados del proyecto
COPY app/ ./app/
COPY config/ ./config/
COPY data/ ./data/
COPY scripts/ ./scripts/
COPY eval/ ./eval/
COPY frontend/ ./frontend/

# Pre-construir el índice vectorial ChromaDB (all-MiniLM-L6-v2 ONNX local)
# Garantiza que el contenedor arranque con el índice RAG listo en disco
RUN python scripts/ingest.py

# Exponer puerto dinámico de plataformas cloud (Render / Railway / Cloud Run)
EXPOSE 8000

# Chequeo de salud nativo contra el endpoint /health
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Comando de inicio: reconstruye el índice si el volumen fue limpiado y levanta Uvicorn
CMD ["sh", "-c", "python -c 'from pathlib import Path; import scripts.ingest as ing; (not Path(\"data/index\").exists()) and ing.ejecutar_ingesta()' && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
