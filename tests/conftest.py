import sys
from pathlib import Path
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))


@pytest.fixture(scope="session", autouse=True)
def asegurar_indice_vectorial():
    """Garantiza la existencia del índice RAG para pruebas reproducibles en entornos limpios o CI."""
    ruta_indice = BASE_DIR / "data" / "index" / "chroma.sqlite3"
    if not ruta_indice.exists():
        from scripts.ingest import ejecutar_ingesta
        ejecutar_ingesta()

