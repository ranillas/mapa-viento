"""Verificación en vivo contra el servidor DWD.

Descarga el listado de las ocho carpetas de corrida y comprueba qué fichero
elige la lógica nueva frente a la que tenía el script antes.

    python verificar_dwd.py
"""

import re
import sys
import urllib.request

from icon_utils import elegir_archivo_mas_reciente, run_stamp

URL_BASE = "https://opendata.dwd.de/weather/nwp/icon-eu/grib"
CORRIDAS = ["00", "03", "06", "09", "12", "15", "18", "21"]
PATRON = re.compile(r'href=["\']([^"\']+\.grib2\.bz2)["\']', re.IGNORECASE)


def listar(corrida, var):
    url = f"{URL_BASE}/{corrida}/{var}/"
    with urllib.request.urlopen(url, timeout=20) as r:
        html = r.read().decode("utf-8", "replace")
    return url, PATRON.findall(html)


def main():
    var = sys.argv[1] if len(sys.argv) > 1 else "u_10m"
    todos = []
    print(f"Variable: {var}\n")
    for corrida in reversed(CORRIDAS):
        try:
            url, archivos = listar(corrida, var)
        except Exception as e:
            print(f"  {corrida}: error ({e})")
            continue
        if not archivos:
            print(f"  {corrida}: vacía")
            continue
        sellos = sorted({run_stamp(a) for a in archivos if run_stamp(a)})
        print(f"  {corrida}: {len(archivos):3d} ficheros · corridas {', '.join(sellos)}")
        todos.extend(archivos)

    if not todos:
        print("\nNo se ha podido listar ningún fichero.")
        return 1

    elegido = elegir_archivo_mas_reciente(todos)
    print(f"\nLógica nueva  → {elegido}  (corrida {run_stamp(elegido)})")

    # Lógica antigua: primera carpeta con ficheros, paso 000 si existe.
    for corrida in reversed(CORRIDAS):
        try:
            _, archivos = listar(corrida, var)
        except Exception:
            continue
        if not archivos:
            continue
        paso0 = [f for f in archivos if "_000_" in f]
        viejo = paso0[0] if paso0 else archivos[0]
        print(f"Lógica antigua → {viejo}  (corrida {run_stamp(viejo)})")
        print("\n" + ("CORRECTO: la lógica nueva sirve datos más recientes."
                      if run_stamp(elegido) > run_stamp(viejo)
                      else "IGUAL: ambas eligen la misma corrida."))
        break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
