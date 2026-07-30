"""
Mapeo de los codigos de tipo de hecho de importancia de la SMV a tiers de
materialidad. Los codigos L01-L40 son los que aplican a emisores del mercado
principal (renta variable), que es la cobertura de equity.

TIER 1 = accionable, va arriba del digest.
TIER 2 = relevante pero no urgente.
TIER 3 = informativo / rutina, va al fondo.

Este mapeo es un PRIMER BORRADOR. Es exactamente lo que hay que sentarse a
afinar con Karely y el equipo: es una decision de research, no de codigo.
El codigo L37 ("Otros Hechos de Importancia") se deja como None a proposito
para forzar que el modelo lo clasifique caso por caso, porque ahi es donde se
esconden cosas importantes mal etiquetadas.
"""

TIER_POR_CODIGO = {
    # --- TIER 1: alta materialidad -------------------------------------------
    "L02": 1,  # Fusion, escision, reorganizacion societaria
    "L04": 1,  # Cambios en directorio y gerencia general
    "L07": 1,  # Cambio en unidad de control / participacion significativa
    "L08": 1,  # Cambios en la unidad de control del emisor
    "L10": 1,  # Informacion financiera y memoria anual
    "L12": 1,  # Cambios relevantes en resultados o patrimonio neto
    "L13": 1,  # Politica de dividendos
    "L14": 1,  # Distribucion o aplicacion de utilidades
    "L16": 1,  # Adquisicion / enajenacion / reestructuracion de activos-pasivos
    "L19": 1,  # Postergacion o incumplimiento de obligaciones de pago
    "L21": 1,  # Emisiones de valores por oferta publica o privada
    "L22": 1,  # Informes de clasificacion de riesgo
    "L34": 1,  # Proceso concursal, intervencion o quiebra

    # --- TIER 2: relevante ----------------------------------------------------
    "L01": 2,  # Convocatoria a junta y acuerdos adoptados
    "L05": 2,  # Politicas de remuneracion de directores y gerencia
    "L06": 2,  # Transferencias de acciones representativas del capital
    "L09": 2,  # Transacciones, prestamos, garantias significativas
    "L11": 2,  # Designacion / resolucion de sociedad de auditoria
    "L15": 2,  # Planes y operaciones de inversion o financiamiento
    "L20": 2,  # Revocacion de lineas de credito / ejecucion de garantias
    "L23": 2,  # Designacion / cese del representante de obligacionistas
    "L24": 2,  # Informes de valorizacion
    "L25": 2,  # Deterioro de garantias
    "L26": 2,  # Inscripcion, suspension o exclusion de valores
    "L27": 2,  # Recompra / redencion / amortizacion de valores
    "L28": 2,  # Contratos importantes con Estado, clientes o proveedores
    "L29": 2,  # Inicio de due diligence o similar
    "L31": 2,  # Huelgas, ceses imprevistos de actividad productiva
    "L33": 2,  # Procesos judiciales / arbitrales / administrativos
    "L39": 2,  # Impactos socioambientales que afecten sostenibilidad

    # --- TIER 3: informativo / rutina ----------------------------------------
    "L03": 3,  # Modificacion de la cuenta de acciones de inversion
    "L17": 3,  # Marcas, patentes, licencias
    "L18": 3,  # Adquisiciones/desinversiones en activos financieros; derivados
    "L30": 3,  # Descubrimiento de recursos / nuevas tecnologias
    "L32": 3,  # Resoluciones firmes de sanciones
    "L35": 3,  # Difusion SMV Art. 27 del Reglamento
    "L40": 3,  # Posicion mensual en instrumentos derivados

    # --- Sin tier fijo: el modelo decide -------------------------------------
    "L37": None,  # Otros Hechos de Importancia -> clasificar caso por caso
}

CATEGORIA_POR_CODIGO = {
    "L01": "Junta de accionistas",
    "L02": "Reorganizacion societaria",
    "L04": "Directorio / gerencia",
    "L10": "Resultados / EEFF",
    "L12": "Resultados / patrimonio",
    "L13": "Dividendos",
    "L14": "Dividendos",
    "L16": "M&A / activos",
    "L19": "Incumplimiento de pago",
    "L21": "Emision de valores",
    "L22": "Clasificacion de riesgo",
    "L28": "Contratos relevantes",
    "L33": "Litigios",
    "L34": "Concurso / quiebra",
    "L37": "Otros",
    "L40": "Derivados",
}


def tier_base(codigo: str):
    """Devuelve el tier sugerido por el codigo, o None si hay que dejarselo al modelo."""
    if not codigo:
        return None
    return TIER_POR_CODIGO.get(codigo.strip().upper(), None)


def categoria_base(codigo: str) -> str:
    if not codigo:
        return "Sin clasificar"
    return CATEGORIA_POR_CODIGO.get(codigo.strip().upper(), "Otros")
