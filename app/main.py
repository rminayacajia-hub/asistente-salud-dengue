"""
Backend API - Asistente de Orientación en Salud Pública sobre Dengue y Arbovirosis.
Seminario de Titulación UNIANDES 2026 - Caso 05 (Grupo 5).
"""
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.settings import settings
from app.schemas import HealthResponse

# Inicialización de la aplicación FastAPI
app = FastAPI(
    title="Asistente de Orientación en Salud Pública (Dengue Ecuador)",
    description=(
        "API REST para la orientación ciudadana en dengue basada en guías oficiales "
        "del MSP y la OPS, con triaje determinista de signos de alarma y geolocalización de salud."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configuración de CORS para integración con Frontend (Streamlit / Web)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Chequeo de salud del servicio",
    tags=["Monitoreo"]
)
def get_health() -> HealthResponse:
    """
    Endpoint de monitoreo de salud (Liveness / Readiness probe).
    Verifica que el servicio esté arriba y devuelve metadatos del entorno.
    """
    return HealthResponse(
        status="ok",
        environment=settings.APP_ENV,
        service="asistente-dengue-backend",
        version="1.0.0",
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@app.get(
    "/",
    summary="Información raíz del servicio",
    tags=["General"]
)
def root():
    """Ruta raíz informativa con accesos directos a documentación."""
    return {
        "sistema": "Asistente de Orientación en Dengue y Arbovirosis (Ecuador)",
        "instituciones_fuente": ["MSP Ecuador", "OPS / OMS"],
        "estado": "operativo",
        "documentacion": "/docs",
        "salud": "/health",
        "regla_oro_3": "Triaje evaluado exclusivamente mediante código determinista en Python"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG
    )
