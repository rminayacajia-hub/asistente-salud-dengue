"""
Servicio Retriever (Recuperador RAG) para el Asistente de Dengue (Semana 3).

Principio SOLID - Responsabilidad Única (SRP):
Este módulo tiene como única responsabilidad interactuar con la base de datos
vectorial ChromaDB, recuperar los fragmentos normativos más relevantes a la
consulta del usuario y entregar el contexto formateado junto a sus fuentes.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.schemas import Fuente

# Configuración del logger para trazabilidad de eventos del RAG
logger = logging.getLogger("asistente.retriever")

# Rutas predeterminadas del proyecto
RUTA_BASE = Path(__file__).resolve().parent.parent.parent
RUTA_CONFIG_UMBRALES = RUTA_BASE / "config" / "umbrales.json"
RUTA_INDICE_DEFECTO = RUTA_BASE / "data" / "index"


# Términos clínicos y de salud para contextualización semántica en español
TERMINOS_CLINICOS_SALUD = (
    "dolor", "cabeza", "estomago", "estómago", "barriga", "fiebre",
    "vomit", "vomito", "vómito", "sangre", "sangrad", "nausea",
    "náusea", "mareo", "desmay", "somnolen", "letargo", "irritab",
    "sarpullido", "mancha", "ojo", "retroocular", "picadura",
    "mosquito", "paracetamol", "ibuprofeno", "aspirina", "aine",
    "hidrat", "suero", "sro", "plaqueta", "dengue", "zika",
    "chikungunya", "sintoma", "síntoma", "alarma", "gravedad",
    "medicamento", "pastilla", "remedio", "hospital", "atencion",
    "atención", "medico", "médico", "centro", "salud"
)


def _cargar_configuracion_rag() -> dict[str, Any]:
    """
    Carga los parámetros del RAG desde config/umbrales.json de forma desacoplada.
    Si el archivo no existe o está corrupto, usa valores seguros por defecto.
    
    ¿Para qué sirve?
    Evita quemar valores fijos (números mágicos) en el código, permitiendo
    ajustar el top_k o el umbral de distancia sin recompilar ni alterar lógica.
    """
    defaults = {
        "coleccion": "dengue_ops_msp",
        "top_k": 2,
        "distancia_maxima": 1.38,
        "ruta_indice": str(RUTA_INDICE_DEFECTO),
    }
    if not RUTA_CONFIG_UMBRALES.exists():
        logger.warning("No se encontró %s; utilizando parámetros RAG por defecto.", RUTA_CONFIG_UMBRALES)
        return defaults

    try:
        with open(RUTA_CONFIG_UMBRALES, "r", encoding="utf-8") as f:
            datos = json.load(f)
            rag_cfg = datos.get("rag", {})
            return {
                "coleccion": rag_cfg.get("coleccion", defaults["coleccion"]),
                "top_k": int(rag_cfg.get("top_k", defaults["top_k"])),
                "distancia_maxima": float(rag_cfg.get("distancia_maxima", defaults["distancia_maxima"])),
                "ruta_indice": str(RUTA_BASE / rag_cfg.get("ruta_indice", "data/index")),
            }
    except Exception as e:
        logger.error("Error al leer %s (%s); usando valores por defecto.", RUTA_CONFIG_UMBRALES, e)
        return defaults


@dataclass
class ResultadoRecuperacion:
    """
    Estructura de datos con el resultado de la búsqueda semántica.
    
    Atributos:
        texto_contexto: Cadena formateada lista para inyectarse en el prompt del LLM.
        fuentes: Lista de modelos Fuente (documento y sección oficial) para la API.
        fragmentos: Lista textual de cada fragmento recuperado.
        relevante: Booleano que indica si se encontraron documentos dentro del umbral.
    """
    texto_contexto: str
    fuentes: list[Fuente]
    fragmentos: list[str]
    relevante: bool


class RecuperadorDengue:
    """
    Clase encargada de la conexión persistente con ChromaDB y de la búsqueda semántica.
    
    ¿Por qué la creamos?
    Porque encapsula todas las dependencias de ChromaDB y el modelo de embeddings.
    Si el cliente LLM o la API FastAPI necesitan información oficial, solo interactúan
    con esta clase sin conocer los detalles de indexación vectorial.
    """

    def __init__(self, ruta_indice: str | None = None, nombre_coleccion: str | None = None):
        """
        Inicializa el cliente de ChromaDB en modo persistente.
        
        ¿Para qué sirve?
        Abre el directorio de base vectorial data/index y enlaza la colección
        de fragmentos normativos del dengue.
        """
        config = _cargar_configuracion_rag()
        self.ruta_indice = Path(ruta_indice or config["ruta_indice"])
        self.nombre_coleccion = nombre_coleccion or config["coleccion"]
        self.top_k = config["top_k"]
        self.distancia_maxima = config["distancia_maxima"]
        self._cliente = None
        self._coleccion = None
        self._disponible = False

        self._conectar()

    def _conectar(self) -> None:
        """
        Conecta de forma segura a ChromaDB manejando contingencias.
        Si la base vectorial aún no fue creada con scripts/ingest.py, no lanza excepción;
        simplemente marca el servicio como no disponible para fallback graceful.
        """
        try:
            import chromadb

            if not self.ruta_indice.exists():
                logger.warning(
                    "El directorio de base vectorial %s no existe. "
                    "Ejecuta 'py scripts/ingest.py' para inicializarlo.",
                    self.ruta_indice,
                )
                self._disponible = False
                return

            self._cliente = chromadb.PersistentClient(path=str(self.ruta_indice))
            # Obtenemos la colección existente (no la recreamos en tiempo de consulta)
            self._coleccion = self._cliente.get_collection(name=self.nombre_coleccion)
            self._disponible = True
            logger.info(
                "Retriever conectado con éxito a ChromaDB (Colección: '%s', Path: '%s').",
                self.nombre_coleccion,
                self.ruta_indice,
            )
        except Exception as e:
            logger.warning("No se pudo conectar a ChromaDB (%s). Operando en modo degradado sin RAG.", e)
            self._disponible = False

    @property
    def esta_disponible(self) -> bool:
        """Indica si la base de datos vectorial está activa y lista para responder."""
        return self._disponible

    def recuperar(self, consulta: str, top_k: int | None = None) -> ResultadoRecuperacion:
        """
        Realiza la búsqueda de los fragmentos normativos más cercanos semánticamente.
        
        ¿Por qué lo hacemos así?
        1. Convierte la consulta del ciudadano a un vector de embedding.
        2. Mide la distancia semántica con los fragmentos de la guía OPS/MSP.
        3. Descarta fragmentos cuya distancia supere el umbral (consultas irrelevantes).
        4. Construye las citas oficiales verificables para prevenir alucinaciones.
        
        Retorna:
            ResultadoRecuperacion con el texto de contexto y las fuentes estructuradas.
        """
        k = top_k or self.top_k

        # Caso degradado: si ChromaDB no está disponible o la consulta está vacía
        if not self._disponible or not self._coleccion or not consulta.strip():
            return ResultadoRecuperacion(
                texto_contexto="",
                fuentes=[],
                fragmentos=[],
                relevante=False,
            )

        try:
            # Contextualización de dominio para lenguaje coloquial en español si menciona síntomas
            consulta_lower = consulta.lower()
            es_consulta_salud = any(t in consulta_lower for t in TERMINOS_CLINICOS_SALUD)
            texto_busqueda = f"dengue salud {consulta}" if es_consulta_salud else consulta

            resultados = self._coleccion.query(
                query_texts=[texto_busqueda],
                n_results=k,
            )

            ids_docs = resultados.get("ids", [[]])[0]
            documentos = resultados.get("documents", [[]])[0]
            metadatos = resultados.get("metadatas", [[]])[0]
            distancias = resultados.get("distances", [[]])[0]

            fragmentos_validos: list[str] = []
            fuentes_validas: list[Fuente] = []

            for doc_id, doc, meta, dist in zip(ids_docs, documentos, metadatos, distancias):
                # Filtro de distancia máxima para evitar ruido o alucinaciones
                if dist <= self.distancia_maxima:
                    fragmentos_validos.append(doc)
                    fuentes_validas.append(
                        Fuente(
                            id=str(doc_id),
                            documento=str(meta.get("documento", "Guía Oficial OPS/MSP")),
                            seccion=str(meta.get("seccion", "Normativa Oficial")),
                            tema=str(meta.get("tema", "sintomas")),
                            anio=str(meta.get("anio", "2024")),
                        )
                    )

            if not fragmentos_validos:
                return ResultadoRecuperacion(
                    texto_contexto="",
                    fuentes=[],
                    fragmentos=[],
                    relevante=False,
                )

            # Formateo pedagógico del contexto para inyectarlo limpiamente en el prompt
            bloques = []
            for i, frag in enumerate(fragmentos_validos, 1):
                bloques.append(f"--- FRAGMENTO OFICIAL #{i} ---\n{frag}")

            texto_contexto = "\n\n".join(bloques)

            return ResultadoRecuperacion(
                texto_contexto=texto_contexto,
                fuentes=fuentes_validas,
                fragmentos=fragmentos_validos,
                relevante=True,
            )

        except Exception as e:
            logger.error("Error al consultar ChromaDB (%s). Retornando contexto vacío.", e)
            return ResultadoRecuperacion(
                texto_contexto="",
                fuentes=[],
                fragmentos=[],
                relevante=False,
            )
