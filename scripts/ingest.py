"""
Script de Ingesta Reproducible y Vectorización RAG (ChromaDB).
Seminario de Titulación UNIANDES 2026 - Caso 05 (Dengue y Arbovirosis).

¿Por qué existe este script?
Los modelos de lenguaje (LLMs) tienen conocimiento general, pero en salud pública
no pueden adivinar ni improvisar. Este script procesa las guías oficiales vigentes
de la OPS y del MSP Ecuador, las fragmenta por secciones temáticas y genera una base
vectorial persistente para que el asistente fundamente sus respuestas con citas verificables.

¿Para qué sirve en el sistema?
Transforma los textos normativos en fragmentos estructurados con metadatos (documento,
sección, tema, año) y los guarda indexados matemáticamente (embeddings) en 'data/index/'.
Esto permite búsquedas semánticas ultrarrápidas y precisas desde 'app/services/retriever.py'.
"""
import os
import shutil
import sys
from pathlib import Path

# Asegurar codificación UTF-8 en salida por consola en sistemas Windows
sys.stdout.reconfigure(encoding="utf-8")

import chromadb
from chromadb.utils import embedding_functions

# Directorios base del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
INDEX_DIR = BASE_DIR / "data" / "index"

# Nombre oficial de la colección vectorial en ChromaDB
COLECCION_RAG = "dengue_ops_msp"


# ==============================================================================
# 1. CORPUS NORMATIVO ESTRUCTURADO POR SECCIONES (CASO 05)
# ==============================================================================
# Siguiendo la Guía de RAG del Caso 05:
# «Las guías clínicas no tienen artículos: se cortan por sección (500–800 palabras),
#  conservando el título de la sección en cada fragmento para poder citar:
#  'Guía OPS, sección 3' o 'Lineamiento MSP, sección 2'».
CORPUS_SECCIONES = [
    {
        "id": "ops-sec-01",
        "documento": "Guía OPS dengue",
        "seccion": "SECCIÓN 1. Qué es el dengue, transmisión y fases clínicas",
        "tema": "sintomas",
        "anio": "2024",
        "contenido": (
            "SECCIÓN 1. Qué es el dengue, transmisión y fases clínicas.\n\n"
            "El dengue es una enfermedad viral aguda transmitida por la picadura de mosquitos hembra infectados, "
            "principalmente del género Aedes aegypti y, en menor grado, Aedes albopictus. Los virus del dengue (DENV) "
            "pertenecen a la familia Flaviviridae y existen cuatro serotipos distintos (DENV-1, DENV-2, DENV-3 y DENV-4). "
            "La infección por un serotipo produce inmunidad de por vida contra ese serotipo específico, pero solo protección "
            "cruzada temporal y parcial contra los otros tres, aumentando el riesgo de dengue grave en infecciones secundarias.\n\n"
            "El curso de la enfermedad atraviesa típicamente tres fases clínicas bien definidas:\n"
            "1. Fase Febril: Se inicia de forma súbita y dura generalmente de dos a siete días. Cursa con fiebre alta (a menudo "
            "superior a 39 °C), cefalea intensa, dolor retroocular característico que empeora con el movimiento de los ojos, "
            "mialgias generalizadas ('fiebre quebrantahuesos'), artralgias, náuseas, eritema facial y exantema macular.\n"
            "2. Fase Crítica: Ocurre típicamente entre el tercer y séptimo día de la enfermedad, coincidiendo con el momento en que "
            "la fiebre desciende o desaparece (defervescencia). Durante esta ventana de 24 a 48 horas puede producirse una fuga "
            "capilar de plasma que conduce a shock hipovolémico, hemorragias severas o daño grave de órganos si no se maneja a tiempo.\n"
            "3. Fase de Recuperación: Tiene lugar tras la fase crítica, donde se reabsorbe gradualmente el líquido extravasado, "
            "mejora el estado general, se recupera el apetito y se normalizan las plaquetas y leucocitos."
        ),
    },
    {
        "id": "ops-sec-02",
        "documento": "Guía OPS dengue",
        "seccion": "SECCIÓN 2. Prevención y control vectorial en el hogar y comunidad",
        "tema": "prevencion",
        "anio": "2024",
        "contenido": (
            "SECCIÓN 2. Prevención y control vectorial en el hogar y comunidad.\n\n"
            "Dado que no existe un tratamiento antiviral específico contra el virus del dengue, el método más eficaz de prevención "
            "consiste en interrumpir el ciclo biológico del mosquito vector Aedes aegypti en las viviendas y sus alrededores.\n\n"
            "Medidas domiciliarias de prevención y eliminación de criaderos:\n"
            "1. Control de recipientes con agua: Lavar y cepillar semanalmente las paredes internas de tanques, cisternas, tachos, "
            "baldes y bebederos de animales antes de volver a llenarlos, eliminando los huevos del mosquito adheridos a las superficies.\n"
            "2. Tapado hermético: Mantener herméticamente cubiertos todos los reservorios y recipientes donde se almacene agua para "
            "consumo humano o doméstico.\n"
            "3. Eliminación de inservibles: Descartar llantas viejas, botellas vacías, latas, cáscaras, plásticos y cualquier objeto "
            "en desuso capaz de acumular agua de lluvia en patios, jardines, techos y solares baldíos.\n"
            "4. Protección personal contra picaduras: Uso de mosquiteros en camas y cunas, colocación de mallas metálicas o plásticas "
            "en puertas y ventanas, aplicación de repelentes autorizados (DEET al 20-30%, Icaridina o IR3535) en la piel expuesta y "
            "uso de ropa de manga larga y pantalones claros, especialmente en las primeras horas de la mañana y al atardecer, que son "
            "las horas de mayor actividad de picadura del mosquito."
        ),
    },
    {
        "id": "ops-sec-03",
        "documento": "Guía OPS dengue",
        "seccion": "SECCIÓN 3. Signos de alarma de dengue y criterios de derivación urgente",
        "tema": "alarma",
        "anio": "2024",
        "contenido": (
            "SECCIÓN 3. Signos de alarma de dengue y criterios de derivación urgente.\n\n"
            "Los signos de alarma anuncian el inicio inminente del choque por fuga plasmática y son el pilar fundamental de la "
            "clasificación clínica de la OPS y el MSP para salvar la vida del paciente. Aparecen comúnmente cuando la fiebre empieza "
            "a ceder (entre el día 3 y 7 del cuadro clínico).\n\n"
            "Lista canónica de signos de alarma obligatorios:\n"
            "1. Dolor abdominal intenso y continuo, o dolor a la palpación del abdomen.\n"
            "2. Vómitos persistentes o recurrentes (más de 3 episodios en 1 hora o 4 episodios en 6 horas) que impiden la hidratación oral.\n"
            "3. Acumulación clínica de líquidos evidenciada por ascitis, derrame pleural o derrame pericárdico.\n"
            "4. Sangrado activo de mucosas: gingivorragia (sangrado de encías espontáneo), epistaxis (sangrado nasal), hematemesis, melena "
            "o metrorragia anormal.\n"
            "5. Estado de alteración mental: letargo, somnolencia profunda, fatiga extrema, debilidad marcada al ponerse de pie, lipotimia "
            "o irritabilidad extrema (especialmente en niños pequeños).\n"
            "6. Hepatomegalia dolorosa mayor a 2 centímetros por debajo del reborde costal.\n"
            "7. Aumento progresivo del hematocrito asociado a una rápida disminución del recuento de plaquetas.\n\n"
            "Conducta médica obligatoria: Ante la presencia de UN SOLO signo de alarma, el paciente NO debe permanecer en casa. "
            "Debe ser derivado DE INMEDIATO a la Sala de Emergencias de un hospital o centro de salud tipo C para reanimación intravenosa "
            "con soluciones cristaloides (Solución Salina o Ringer Lactato). En caso de no contar con transporte inmediato, comunicarse "
            "urgentemente con el Servicio Integrado ECU-911."
        ),
    },
    {
        "id": "ops-sec-04",
        "documento": "Guía OPS dengue",
        "seccion": "SECCIÓN 4. Qué no hacer, medicamentos prohibidos y contraindicaciones",
        "tema": "tratamiento",
        "anio": "2024",
        "contenido": (
            "SECCIÓN 4. Qué no hacer, medicamentos prohibidos y contraindicaciones.\n\n"
            "La automedicación durante un cuadro sospechoso o confirmado de dengue constituye una de las principales causas de muerte "
            "por complicaciones hemorrágicas y falla hepática aguda en la región de las Américas.\n\n"
            "Contraindicaciones absolutas:\n"
            "1. PROHIBICIÓN TAXATIVA DE AINEs: Queda estrictamente prohibido el uso de Antiinflamatorios No Esteroideos (AINEs), incluyendo "
            "ácido acetilsalicílico (Aspirina), ibuprofeno, naproxeno, diclofenaco, ketorolaco, meloxicam y piroxicam. Estos fármacos "
            "poseen efecto antiagregante plaquetario y acción erosiva sobre la mucosa gástrica, lo que precipita hemorragias digestivas masivas "
            "y shock irreversible en pacientes con trombocitopenia inducida por dengue.\n"
            "2. NO administrar corticosteroides (prednisona, dexametasona) por vía oral o intramuscular sin estricta indicación médica.\n"
            "3. NO aplicar inyecciones intramusculares debido al elevado riesgo de formar hematomas musculares profundos y abscesos.\n"
            "4. NO administrar antibióticos: El dengue es una infección producida por un virus; los antibióticos no tienen ningún efecto "
            "terapéutico y pueden generar resistencia bacteriana y toxicidad gastrointestinal.\n\n"
            "Manejo seguro de la fiebre y malestar:\n"
            "El único antipirético y analgésico de primera línea recomendado es el Paracetamol (Acetaminofén) por vía oral, respetando "
            "estrictamente la dosis máxima permitida: en adultos no exceder de 500 a 1000 mg cada 6 a 8 horas (máximo 3 gramos al día para "
            "evitar daño hepático); en niños, de 10 a 15 mg/kg por dosis cada 6 horas. Priorizar siempre la hidratación abundante con sales "
            "de rehidratación oral (SRO), caldos claros, agua de coco y jugos naturales no ácidos."
        ),
    },
    {
        "id": "msp-sec-05",
        "documento": "Lineamiento MSP Ecuador",
        "seccion": "SECCIÓN 5. Clasificación clínica del dengue y niveles de atención en Ecuador",
        "tema": "tratamiento",
        "anio": "2026",
        "contenido": (
            "SECCIÓN 5. Clasificación clínica del dengue y niveles de atención en Ecuador.\n\n"
            "De acuerdo con los lineamientos oficiales del Ministerio de Salud Pública del Ecuador (MSP), los casos de dengue se clasifican "
            "en tres categorías operativas que determinan el nivel de atención médica correspondiente en el Sistema Nacional de Salud:\n\n"
            "1. Dengue sin signos de alarma (Grupo A): Pacientes que toleran volúmenes adecuados de líquidos por vía oral, con diuresis normal "
            "y sin comorbilidades graves ni riesgo social. Manejo ambulatorio en el hogar con reposo, hidratación oral estricta y control diario "
            "en el Centro de Salud Tipo A o Tipo B hasta 48 horas después del cese de la fiebre.\n"
            "2. Dengue con signos de alarma (Grupo B): Pacientes que presentan uno o más de los signos de alarma (dolor abdominal continuo, vómitos "
            "frecuentes, sangrado de mucosas, decaimiento) o condiciones asociadas (embarazo, menores de 1 año, adultos mayores de 65 años, "
            "diabetes, hipertensión, insuficiencia renal). Requieren hospitalización inmediata en un Centro de Salud Tipo C u Hospital Básico "
            "para hidratación intravenosa con cristaloides y monitoreo continuo de signos vitales y diuresis.\n"
            "3. Dengue grave (Grupo C): Pacientes con choque hipovolémico por extravasación masiva de plasma, dificultad respiratoria por "
            "derrame pleural o ascitis, hemorragia grave que compromete la estabilidad hemodinámica o afectación orgánica grave (miocarditis, "
            "encefalitis o hepatitis con transaminasas AST/ALT > 1000 UI/L). Requieren ingreso urgente a Unidad de Cuidados Intensivos (UCI) "
            "en Hospitales Generales o de Especialidades (Tercer Nivel).\n\n"
            "Acceso ciudadano: Para agendamiento de citas del primer nivel o consultas informativas, el MSP dispone de la línea gratuita 171. "
            "Para situaciones de emergencia con signos de alarma o sospecha de choque, comunicarse de inmediato con el ECU-911."
        ),
    },
    {
        "id": "msp-sec-06",
        "documento": "Lineamiento MSP Ecuador",
        "seccion": "SECCIÓN 6. Protocolo de hidratación oral en el hogar y vigilancia del paciente",
        "tema": "tratamiento",
        "anio": "2026",
        "contenido": (
            "SECCIÓN 6. Protocolo de hidratación oral en el hogar y vigilancia del paciente.\n\n"
            "La reposición oportuna de líquidos por vía oral es la intervención más costo-efectiva para prevenir que un caso de dengue "
            "evolucione hacia la gravedad por fuga capilar de plasma.\n\n"
            "Instrucciones de hidratación en el hogar para pacientes del Grupo A (sin signos de alarma):\n"
            "1. Volumen de líquidos: Se debe administrar líquido de forma constante durante todo el día. En adultos, el objetivo es consumir "
            "entre 2 y 3 litros diarios. En niños, administrar líquidos a libre demanda o calcular a razón de 50 a 60 ml por kilogramo de peso al día.\n"
            "2. Tipos de líquidos recomendados: Solución de Rehidratación Oral (SRO) de baja osmolaridad provista por el MSP o farmacias, caldos "
            "ligeros, sopas de verduras, agua de coco natural y jugos de frutas caseros poco dulces. Se debe evitar el agua pura como única fuente "
            "de hidratación, ya que puede inducir hiponatremia dilucional si no se aportan electrolitos.\n"
            "3. Líquidos prohibidos: Bebidas gaseosas comerciales, bebidas energizantes o hidratantes deportivas con alto contenido de azúcar, "
            "y jugos artificiales envasados, ya que su elevada osmolaridad empeora la diarrea y la deshidratación.\n"
            "4. Monitoreo domiciliario de diuresis: El familiar o cuidador debe vigilar que la persona orine al menos cada 4 a 6 horas y que la "
            "orina sea de color claro. La disminución del volumen urinario o la ausencia de orina durante más de 6 horas es señal de alarma de "
            "hipovolemia que amerita evaluación médica inmediata."
        ),
    },
]


# ==============================================================================
# 2. FUNCIÓN PRINCIPAL DE INGESTA VECTORIAL
# ==============================================================================
def ejecutar_ingesta():
    """
    Función que crea e indexa la base vectorial en ChromaDB.
    1. Asegura la existencia del directorio persistente 'data/index/'.
    2. Inicializa el cliente persistente de ChromaDB.
    3. Utiliza la función de embeddings por defecto de Chroma (onnxruntime / all-MiniLM-L6-v2)
       garantizando ejecución 100% local, reproducible y sin gastar saldo de API.
    4. Indexa los fragmentos con sus metadatos normativos.
    """
    print("=" * 70)
    print("INGESTA REPRODUCIBLE RAG - ASISTENTE DENGUE ECUADOR (SEMANA 3)")
    print("=" * 70)

    # 1. Asegurar limpieza o creación del directorio de índice
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Directorio de índice persistente: {INDEX_DIR}")

    # 2. Inicializar cliente persistente de ChromaDB
    cliente = chromadb.PersistentClient(path=str(INDEX_DIR))

    # 3. Función de embedding multilingüe local (sin costo de API)
    # Usa el modelo estándar ONNX all-MiniLM-L6-v2 provisto por chromadb
    funcion_embedding = embedding_functions.DefaultEmbeddingFunction()

    # Si la colección ya existe, la reiniciamos para garantizar ingesta reproducible limpia
    try:
        cliente.delete_collection(COLECCION_RAG)
        print(f"Colección previa '{COLECCION_RAG}' eliminada para recreación limpia.")
    except Exception:
        pass

    coleccion = cliente.create_collection(
        name=COLECCION_RAG,
        embedding_function=funcion_embedding,
        metadata={"descripcion": "Base de conocimiento RAG Guías OPS y Lineamientos MSP Dengue"},
    )

    # 4. Preparar listas de documentos, metadatos e IDs
    ids = []
    documentos = []
    metadatos = []

    print(f"\nProcesando {len(CORPUS_SECCIONES)} secciones temáticas oficiales:")
    for s in CORPUS_SECCIONES:
        ids.append(s["id"])
        documentos.append(s["contenido"])
        metadatos.append({
            "documento": s["documento"],
            "seccion": s["seccion"],
            "tema": s["tema"],
            "anio": s["anio"],
        })
        palabras = len(s["contenido"].split())
        print(f"  ✓ [{s['id']}] {s['seccion'][:50]}... ({palabras} palabras | Tema: {s['tema']})")

    # 5. Insertar y vectorizar en ChromaDB
    print("\nGenerando vectores de embedding e indexando en disco...")
    coleccion.add(
        ids=ids,
        documents=documentos,
        metadatas=metadatos,
    )

    print("=" * 70)
    print(f"¡ÉXITO! Base vectorial creada con {coleccion.count()} fragmentos en: {INDEX_DIR}")
    print("Colección activa:", COLECCION_RAG)
    print("=" * 70)


if __name__ == "__main__":
    ejecutar_ingesta()
