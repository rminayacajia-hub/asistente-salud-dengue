"""
Módulo de Configuración Centralizada (Regla de Oro 4: Lo que cambia en el tiempo, vive en configuración)
Carga variables de entorno desde .env mediante python-dotenv.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Directorio base del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent

# Carga de variables de entorno desde .env
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    load_dotenv(dotenv_path=ENV_FILE)
else:
    load_dotenv()


class Settings:
    # Entorno
    APP_ENV: str = os.getenv("APP_ENV", "development")
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "t")

    # Proveedor LLM (Regla de Oro 5: Secreto inyectado desde entorno)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-1.5-flash")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    LLM_MAX_OUTPUT_TOKENS: int = int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "1024"))

    # Vector Store & Embeddings (RAG)
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "models/text-embedding-004")
    CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", str(BASE_DIR / "data" / "chroma"))
    CHROMA_COLLECTION_NAME: str = os.getenv("CHROMA_COLLECTION_NAME", "dengue_msp_ops_knowledge")

    # Umbrales
    RELEVANCE_THRESHOLD: float = float(os.getenv("RELEVANCE_THRESHOLD", "0.65"))
    TOP_K_RESULTS: int = int(os.getenv("TOP_K_RESULTS", "4"))

    # Rutas de Datos Locales
    GEOSALUD_DATA_PATH: str = os.getenv("GEOSALUD_DATA_PATH", str(BASE_DIR / "data" / "geosalud_ecuador.json"))
    RAW_DATA_DIR: str = os.getenv("RAW_DATA_DIR", str(BASE_DIR / "data" / "raw"))

    # Emergencias (Ecuador)
    EMERGENCY_PHONE: str = os.getenv("EMERGENCY_PHONE", "911")
    MSP_CITAS_PHONE: str = os.getenv("MSP_CITAS_PHONE", "171")
    MSP_OFFICIAL_URL: str = os.getenv("MSP_OFFICIAL_URL", "https://www.salud.gob.ec")


settings = Settings()
