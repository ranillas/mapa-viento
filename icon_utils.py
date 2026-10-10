"""Utilidades puras para los ficheros GRIB2 de ICON-EU (DWD).

Sin dependencias externas: sólo `re`. Así la lógica se puede probar sin
descargar nada y sin instalar xarray/cfgrib.

Nombre de fichero real:

    icon-eu_europe_regular-lat-lon_single-level_2026101000_000_U_10M.grib2.bz2
                                     └── sello ──┘ └paso┘
"""

import re

# ..._YYYYMMDDHH_SSS_<LETRA>_10M.grib2.bz2
#   1+2 → fecha+hora de la corrida    3 → paso de predicción
# Va anclado al final, así sirve para la malla regular y para otras mallas
# de DWD, y para los componentes U y V.
PATRON_GRIB2 = re.compile(
    r"(\d{8})(\d{2})_(\d{3})_[a-z]_10m\.grib2\.bz2$",
    re.IGNORECASE,
)


def run_stamp(nombre):
    """Devuelve el sello 'YYYYMMDDHH' de la corrida, o None."""
    if not nombre:
        return None
    encontrado = PATRON_GRIB2.search(str(nombre))
    return encontrado.group(1) + encontrado.group(2) if encontrado else None


def paso(nombre):
    """Devuelve el paso de predicción (000, 001, ...) como entero, o None."""
    if not nombre:
        return None
    encontrado = PATRON_GRIB2.search(str(nombre))
    return int(encontrado.group(3)) if encontrado else None


def elegir_archivo_mas_reciente(archivos):
    """Elige el análisis (paso 000) de la corrida más reciente.

    Mirar sólo la hora de la carpeta no basta: DWD guarda una corrida por
    hora, pero la carpeta '21' puede seguir teniendo la corrida de ayer
    mientras la '00' ya tiene la de hoy. Por eso se compara el sello
    fecha+hora que lleva el nombre del fichero.

    Medido el 2026-10-10 contra el servidor real:

        carpeta 21 → ..._2026100921_000_...   (datos de 17,2 h)
        carpeta 00 → ..._2026101000_000_...   (datos de 14,2 h)  ← más reciente

    El código antiguo se quedaba con la carpeta 21 porque la recorría
    primero. Si ninguna corrida tiene todavía el paso 000, se cae al paso
    más bajo de la corrida más reciente en lugar de quedarse sin datos.
    """
    candidatos = []
    for nombre in archivos or []:
        sello = run_stamp(nombre)
        numero = paso(nombre)
        if sello is None or numero is None:
            continue
        candidatos.append((sello, numero, nombre))

    if not candidatos:
        return None

    con_paso_cero = [c for c in candidatos if c[1] == 0]
    if con_paso_cero:
        return max(con_paso_cero, key=lambda c: c[0])[2]

    sello_reciente = max(c[0] for c in candidatos)
    paso_minimo = min(c[1] for c in candidatos if c[0] == sello_reciente)
    return next(c[2] for c in candidatos if c[0] == sello_reciente and c[1] == paso_minimo)
